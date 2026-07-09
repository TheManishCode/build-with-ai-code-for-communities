"""Ingest PMGSY Rural Roads (GIS) data, clipped to Bagalkot's PC boundary.

None of the PMGSY layers carry a district/LGD code that's usable for a clean
attribute-only filter at habitation granularity (Habitation has no code at
all; the Proposal_* layers only carry a *district*-level LGD code, and PC
boundaries can cross district lines even though Bagalkot's happens to line
up with LGD district 524 "Bagalkote"). So every layer here is spatially
clipped against the pc_boundary polygon for pc_id=2903 (BAGALKOT), which
app.ingestion.boundary must have already loaded.

Upsert notes:
- PMGSYHabitation has a real primary key (hab_id) -> on_conflict_do_update,
  same pattern as app.ingestion.boundary.
- PMGSYRoadProposal and PMGSYRoadDRRP only have autoincrement surrogate PKs
  (confirmed against the alembic migration: mrl_id/er_id are NOT unique --
  PMGSY-III even has exact-duplicate MRL_IDs). There is no natural key to
  upsert against, so instead each run deletes the Bagalkot-scoped rows it's
  about to reinsert (all of PMGSYRoadDRRP; PMGSYRoadProposal by phase) and
  re-inserts fresh. Both tables only ever hold Bagalkot data in this app, so
  that's a safe, idempotent "upsert" for tables without a natural key.
"""

from __future__ import annotations

import geopandas as gpd
from geoalchemy2.shape import from_shape
from shapely import wkb
from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import PMGSYHabitation, PMGSYRoadDRRP, PMGSYRoadProposal

DATA_DIR = settings.dataset_dir / "PMGSY Rural Roads (GIS)"
BAGALKOT_PC_ID = 2903
# Bagalkot PC bounding box (from pc_boundary.geom envelope) -- used as a cheap
# pre-filter for the large statewide DRRP layer before the precise polygon clip.
BAGALKOT_BBOX = (74.9861126, 15.331243, 76.3322355, 16.7678101)
HABITATION_BUFFER_M = 2000  # keep habitation points within 2km of the boundary, not just strictly inside it

# Karnataka's real bounding box -- points outside this are known-corrupt coordinates
# (lat duplicated into lon, or otherwise wildly out of range), per prior inspection.
KA_LON_MIN, KA_LON_MAX = 74.0, 78.6
KA_LAT_MIN, KA_LAT_MAX = 11.5, 18.5

PROPOSAL_ZIPS = {
    "PM-JANMAN": "Proposal_PM-JANMAN_Karnataka.zip",
    "PMGSY-I": "Proposal_PMGSY-I_Karnataka.zip",
    "PMGSY-II": "Proposal_PMGSY-II_Karnataka.zip",
    "PMGSY-III": "Proposal_PMGSY-III_Karnataka.zip",
    "PMGSY-IV": "Proposal_PMGSY-IV_Karnataka.zip",
}


def _bagalkot_geoms(db: Session):
    """Return (raw_polygon, buffered_polygon) for Bagalkot's PC boundary, both in EPSG:4326."""
    row = db.execute(
        text("SELECT ST_AsBinary(geom) FROM pc_boundary WHERE pc_id = :pc_id"), {"pc_id": BAGALKOT_PC_ID}
    ).fetchone()
    if row is None:
        raise RuntimeError(f"pc_boundary row for pc_id={BAGALKOT_PC_ID} not found -- run app.ingestion.boundary first")
    raw = wkb.loads(bytes(row[0]))
    # Buffer in a metric CRS (UTM 43N covers Karnataka) so HABITATION_BUFFER_M is a real 2km, not degrees.
    buffered = gpd.GeoSeries([raw], crs=4326).to_crs(32643).buffer(HABITATION_BUFFER_M).to_crs(4326).iloc[0]
    return raw, buffered


def ingest_habitation(db: Session, bagalkot_buffered) -> None:
    path = DATA_DIR / "Habitation_Karnataka.zip"
    gdf = gpd.read_file("zip://" + str(path))
    n_read = len(gdf)

    in_bbox = gdf.geometry.x.between(KA_LON_MIN, KA_LON_MAX) & gdf.geometry.y.between(KA_LAT_MIN, KA_LAT_MAX)
    n_invalid = int((~in_bbox).sum())
    gdf["is_coord_valid"] = in_bbox
    print(f"[habitation] read {n_read} rows; {n_invalid} flagged coordinate-invalid (outside Karnataka bbox), excluded from spatial filter")

    valid = gdf[in_bbox].copy()
    clipped = valid[valid.intersects(bagalkot_buffered)]
    print(f"[habitation] {len(clipped)} of {len(valid)} valid points fall within {HABITATION_BUFFER_M}m of Bagalkot PC boundary")

    records = [
        {
            "hab_id": int(row.HAB_ID),
            "district_id": int(row.DISTRICT_I),
            "block_id": int(row.BLOCK_ID),
            "hab_name": row.HAB_NAME,
            "population": int(row.TOT_POPULA) if row.TOT_POPULA is not None else None,
            "is_coord_valid": bool(row.is_coord_valid),
            "geom": from_shape(row.geometry, srid=4326),
        }
        for row in clipped.itertuples()
    ]

    if records:
        stmt = insert(PMGSYHabitation).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["hab_id"],
            set_={
                "district_id": stmt.excluded.district_id,
                "block_id": stmt.excluded.block_id,
                "hab_name": stmt.excluded.hab_name,
                "population": stmt.excluded.population,
                "is_coord_valid": stmt.excluded.is_coord_valid,
                "geom": stmt.excluded.geom,
            },
        )
        db.execute(stmt)
        db.commit()
    print(f"[habitation] inserted/updated {len(records)} rows")


def ingest_road_proposals(db: Session, bagalkot_raw) -> None:
    db.execute(delete(PMGSYRoadProposal).where(PMGSYRoadProposal.phase.in_(PROPOSAL_ZIPS.keys())))
    db.commit()

    total_read = total_clipped = total_inserted = 0
    for phase, filename in PROPOSAL_ZIPS.items():
        path = DATA_DIR / filename
        gdf = gpd.read_file("zip://" + str(path))
        n_read = len(gdf)

        # Row counts here are small (tens to a few thousand, Karnataka-only extracts), so a
        # coarse LGD_DISTRI==524 pre-filter buys nothing meaningful -- go straight to the
        # precise spatial clip against the actual PC polygon, per the task's guidance that
        # the end result must be genuinely Bagalkot-scoped rather than district-code-scoped.
        clipped = gdf[gdf.intersects(bagalkot_raw)].copy()
        n_clipped = len(clipped)

        records = [
            {
                "mrl_id": int(row.MRL_ID) if row.MRL_ID is not None else None,
                "phase": phase,
                "lgd_district_code": int(row.LGD_DISTRI) if row.LGD_DISTRI == row.LGD_DISTRI else None,  # NaN check
                "block_id": int(row.BLOCK_ID) if row.BLOCK_ID is not None else None,
                "cn_code": float(row.CN_CODE) if row.CN_CODE is not None else None,
                "proposed_length_km": float(row.PROPOSED_L) if row.PROPOSED_L is not None else None,
                "work_name": row.WORK_NAME,
                "ims_year": str(row.IMS_YEAR) if row.IMS_YEAR is not None else None,
                "proposal_type": row.Proposal_T,
                "geom": from_shape(row.geometry, srid=4326),
            }
            for row in clipped.itertuples()
        ]
        # PMGSY-III has some exact-duplicate MRL_ID rows -- no natural key exists to dedupe
        # against safely (duplicates may be genuinely distinct road segments sharing an MRL_ID),
        # so they're kept and inserted as separate autoincrement rows.
        chunk = 500
        for i in range(0, len(records), chunk):
            db.execute(insert(PMGSYRoadProposal).values(records[i : i + chunk]))
        if records:
            db.commit()

        print(f"[road_proposal:{phase}] read {n_read} -> clipped {n_clipped} -> inserted {len(records)}")
        total_read += n_read
        total_clipped += n_clipped
        total_inserted += len(records)

    print(f"[road_proposal] TOTAL read {total_read} -> clipped {total_clipped} -> inserted {total_inserted}")


def ingest_road_drrp(db: Session, bagalkot_raw) -> None:
    path = DATA_DIR / "Road_DRRP_Karnataka.zip"
    # bbox pre-filter avoids loading all 225,902 statewide LineStrings into memory.
    gdf = gpd.read_file(path, bbox=BAGALKOT_BBOX)
    n_read = len(gdf)

    clipped = gdf[gdf.intersects(bagalkot_raw)].copy()
    n_clipped = len(clipped)

    records = [
        {
            "er_id": int(row.ER_ID),
            "district_id": int(row.DISTRICT_I),
            "block_id": int(row.BLOCK_ID) if row.BLOCK_ID is not None else None,
            "road_code": row.DRRP_ROAD_,
            "road_category": row.RoadCatego,
            "road_name": row.RoadName,
            "road_owner": row.RoadOwner,
            "geom": from_shape(row.geometry, srid=4326),
        }
        for row in clipped.itertuples()
    ]

    db.execute(delete(PMGSYRoadDRRP))
    # Chunked rather than one INSERT for all ~7.6k rows -- a single statement carrying
    # every LineString geometry as inline parameters is large enough that it dropped the
    # SSL connection to a remote (high-latency) Postgres host mid-transfer.
    chunk = 500
    for i in range(0, len(records), chunk):
        db.execute(insert(PMGSYRoadDRRP).values(records[i : i + chunk]))
    db.commit()

    print(f"[road_drrp] read (post-bbox) {n_read} -> clipped {n_clipped} -> inserted {len(records)}")


def run() -> None:
    with SessionLocal() as db:
        bagalkot_raw, bagalkot_buffered = _bagalkot_geoms(db)
        ingest_habitation(db, bagalkot_buffered)
        ingest_road_proposals(db, bagalkot_raw)
        ingest_road_drrp(db, bagalkot_raw)

    with SessionLocal() as db:
        hab_n = db.execute(text("SELECT count(*) FROM pmgsy_habitation")).scalar_one()
        prop_n = db.execute(text("SELECT count(*) FROM pmgsy_road_proposal")).scalar_one()
        drrp_n = db.execute(text("SELECT count(*) FROM pmgsy_road_drrp")).scalar_one()
        print(f"final counts -- habitation: {hab_n}, road_proposal: {prop_n}, road_drrp: {drrp_n}")


if __name__ == "__main__":
    run()
