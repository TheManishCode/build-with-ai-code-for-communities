"""Materialize the single village-level fact table for Bagalkot district.

Joins:
  - lgd_village (spine, district_code=524)
  - census_village_amenities: direct integer join on census2011_code == village_code
  - census_pca_village: already fuzzy-matched to lgd_village_code by app.ingestion.census_pca
  - know_your_school: aggregated by COALESCE(lgd_village_id, matched_lgd_village_code)
  - mplads_work: aggregated by matched_lgd_village_code, both Lok Sabha terms combined
  - pmgsy_habitation + pmgsy_road_drrp: village name is fuzzy-matched to a habitation point
    (scoped to Bagalkot's ~1000 ingested habitations) since no dataset carries a village<->
    habitation key; a matched habitation's point is then spatial-tested (ST_DWithin, 500m)
    against Road_DRRP village/other-district-road categories to derive pmgsy_connected.
    Villages with no confident habitation match get pmgsy_connected=NULL (unknown), not
    False -- absence of a match is not evidence of no connectivity.

This script reports real coverage numbers (non-null counts per column) rather than
assuming completeness -- run it and read the printed report before trusting the table.
"""

from __future__ import annotations

from geoalchemy2.shape import from_shape
from rapidfuzz import fuzz, process, utils
from shapely import wkb
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import VillageFact

BAGALKOT_DISTRICT_CODE = 524
HAB_MATCH_THRESHOLD = 85
CONNECTIVITY_BUFFER_M = 500
CONNECTED_ROAD_CATEGORIES = ("RR(VR)", "RR(ODR)", "MDR")


def _match_habitations(db: Session) -> dict[int, dict]:
    """Fuzzy-match each Bagalkot LGD village to its best PMGSY habitation, scoped to
    habitations already spatially clipped to Bagalkot (see app.ingestion.pmgsy).
    Returns {village_code: {"hab_id": int, "score": float}}.
    """
    villages = db.execute(
        text("SELECT village_code, village_name FROM lgd_village WHERE district_code = :d"),
        {"d": BAGALKOT_DISTRICT_CODE},
    ).all()
    habitations = db.execute(text("SELECT hab_id, hab_name FROM pmgsy_habitation")).all()
    hab_names = [h.hab_name for h in habitations]
    hab_id_by_name: dict[str, int] = {}
    for h in habitations:
        hab_id_by_name.setdefault(h.hab_name, h.hab_id)

    matches: dict[int, dict] = {}
    for v in villages:
        result = process.extractOne(v.village_name, hab_names, scorer=fuzz.WRatio, processor=utils.default_process)
        if result is not None:
            name, score, _ = result
            if score >= HAB_MATCH_THRESHOLD:
                matches[v.village_code] = {"hab_id": hab_id_by_name[name], "score": float(score)}
    return matches


def _connectivity_and_geom(db: Session, hab_matches: dict[int, dict]) -> dict[int, dict]:
    """For each matched habitation, fetch its point geom and test proximity to a
    village/other-district road. Returns {village_code: {"geom": wkb_hex, "connected": bool}}.
    """
    if not hab_matches:
        return {}
    hab_ids = [m["hab_id"] for m in hab_matches.values()]
    rows = db.execute(
        text(
            """
            SELECT h.hab_id,
                   ST_AsEWKB(h.geom) AS geom,
                   EXISTS (
                       SELECT 1 FROM pmgsy_road_drrp r
                       WHERE r.road_category = ANY(:cats)
                         AND ST_DWithin(h.geom::geography, r.geom::geography, :buf)
                   ) AS connected
            FROM pmgsy_habitation h
            WHERE h.hab_id = ANY(:ids)
            """
        ),
        {"cats": list(CONNECTED_ROAD_CATEGORIES), "buf": CONNECTIVITY_BUFFER_M, "ids": hab_ids},
    ).all()
    by_hab = {r.hab_id: {"geom": from_shape(wkb.loads(bytes(r.geom)), srid=4326), "connected": r.connected} for r in rows}

    out: dict[int, dict] = {}
    for village_code, m in hab_matches.items():
        info = by_hab.get(m["hab_id"])
        if info:
            out[village_code] = info
    return out


def _census_amenities_rows(db: Session) -> dict[int, dict]:
    rows = db.execute(
        text(
            """
            SELECT c.*
            FROM census_village_amenities c
            JOIN lgd_village v ON v.census2011_code = c.village_code::text
            WHERE v.district_code = :d
            """
        ),
        {"d": BAGALKOT_DISTRICT_CODE},
    ).mappings().all()
    # Keyed by the LGD village_code, resolved via the same join
    resolved = db.execute(
        text(
            """
            SELECT v.village_code AS lgd_code, c.village_code AS census_code
            FROM census_village_amenities c
            JOIN lgd_village v ON v.census2011_code = c.village_code::text
            WHERE v.district_code = :d
            """
        ),
        {"d": BAGALKOT_DISTRICT_CODE},
    ).all()
    census_to_lgd = {r.census_code: r.lgd_code for r in resolved}
    return {census_to_lgd[r["village_code"]]: dict(r) for r in rows if r["village_code"] in census_to_lgd}


def _pca_rows(db: Session) -> dict[int, dict]:
    rows = db.execute(
        text(
            """
            SELECT lgd_village_code, literate_population, illiterate_population, match_score
            FROM census_pca_village
            WHERE level = 'VILLAGE' AND lgd_village_code IS NOT NULL
            """
        )
    ).all()
    return {r.lgd_village_code: {"literate": r.literate_population, "illiterate": r.illiterate_population, "score": r.match_score} for r in rows}


def _kys_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        text(
            """
            SELECT COALESCE(lgd_village_id, matched_lgd_village_code) AS vc, count(*) AS n
            FROM know_your_school
            WHERE COALESCE(lgd_village_id, matched_lgd_village_code) IS NOT NULL
            GROUP BY vc
            """
        )
    ).all()
    return {r.vc: r.n for r in rows}


def _mplads_agg(db: Session) -> dict[int, dict]:
    rows = db.execute(
        text(
            """
            SELECT matched_lgd_village_code AS vc,
                   sum(completed_amount) FILTER (WHERE completed_amount IS NOT NULL) AS completed_total,
                   count(*) FILTER (WHERE completed_amount IS NOT NULL) AS completed_count,
                   sum(recommended_amount) FILTER (WHERE recommended_amount IS NOT NULL) AS recommended_total
            FROM mplads_work
            WHERE matched_lgd_village_code IS NOT NULL
            GROUP BY vc
            """
        )
    ).all()
    return {
        r.vc: {"completed_total": r.completed_total, "completed_count": r.completed_count, "recommended_total": r.recommended_total}
        for r in rows
    }


def run() -> None:
    with SessionLocal() as db:
        villages = db.execute(
            text(
                """
                SELECT v.village_code, v.village_name, s.subdistrict_name, v.district_code, d.district_name
                FROM lgd_village v
                JOIN lgd_district d ON d.district_code = v.district_code
                LEFT JOIN lgd_subdistrict s ON s.subdistrict_code = v.subdistrict_code
                WHERE v.district_code = :d
                """
            ),
            {"d": BAGALKOT_DISTRICT_CODE},
        ).all()
        gp_by_village = {
            r.village_code: r.localbody_name
            for r in db.execute(
                text(
                    """
                    SELECT m.village_code, l.localbody_name
                    FROM lgd_village_gp_mapping m
                    JOIN lgd_local_body l ON l.localbody_code = m.local_body_code
                    JOIN lgd_village v ON v.village_code = m.village_code
                    WHERE v.district_code = :d
                    """
                ),
                {"d": BAGALKOT_DISTRICT_CODE},
            ).all()
        }

        amenities = _census_amenities_rows(db)
        pca = _pca_rows(db)
        kys_counts = _kys_counts(db)
        mplads = _mplads_agg(db)

        print(f"villages in Bagalkot: {len(villages)}")
        print(f"census_village_amenities matched: {len(amenities)}")
        print(f"census_pca_village matched: {len(pca)}")
        print(f"know_your_school village coverage: {len(kys_counts)}")
        print(f"mplads_work village coverage: {len(mplads)}")

        print("matching PMGSY habitations to villages (fuzzy, this may take a moment)...")
        hab_matches = _match_habitations(db)
        conn_info = _connectivity_and_geom(db, hab_matches)
        n_connected = sum(1 for v in conn_info.values() if v["connected"])
        print(f"habitation match: {len(hab_matches)}/{len(villages)} villages matched a PMGSY habitation")
        print(f"pmgsy_connected: {n_connected} True / {len(conn_info) - n_connected} False / {len(villages) - len(conn_info)} unknown (no habitation match)")

        records = []
        for v in villages:
            a = amenities.get(v.village_code, {})
            p = pca.get(v.village_code, {})
            conn = conn_info.get(v.village_code, {})

            literate = p.get("literate")
            illiterate = p.get("illiterate")
            literacy_rate = None
            if literate is not None and illiterate is not None and (literate + illiterate) > 0:
                literacy_rate = literate / (literate + illiterate)

            safe_water = None
            if a:
                safe_water = bool(
                    a.get("has_treated_tap_water") or a.get("has_hand_pump") or a.get("has_tube_well") or a.get("has_covered_well")
                )

            census_school_count = None
            if a:
                census_school_count = sum(
                    a.get(col) or 0
                    for col in [
                        "govt_primary_schools",
                        "pvt_primary_schools",
                        "govt_middle_schools",
                        "pvt_middle_schools",
                        "govt_secondary_schools",
                        "pvt_secondary_schools",
                        "govt_sr_secondary_schools",
                        "pvt_sr_secondary_schools",
                    ]
                )

            health_count = None
            if a:
                health_count = sum(
                    a.get(col) or 0
                    for col in ["primary_health_centre_count", "primary_health_subcentre_count", "community_health_centre_count"]
                )

            m = mplads.get(v.village_code, {})

            records.append(
                {
                    "village_code": v.village_code,
                    "village_name": v.village_name,
                    "subdistrict_name": v.subdistrict_name,
                    "gram_panchayat_name": gp_by_village.get(v.village_code),
                    "district_name": v.district_name,
                    "total_population": a.get("total_population"),
                    "total_households": a.get("total_households"),
                    "sc_population": a.get("sc_population"),
                    "st_population": a.get("st_population"),
                    "literate_population": literate,
                    "illiterate_population": illiterate,
                    "literacy_rate": literacy_rate,
                    "pca_match_score": p.get("score"),
                    "census_school_count": census_school_count,
                    "kys_school_count": kys_counts.get(v.village_code),
                    "health_facility_count": health_count,
                    "has_closed_drainage": a.get("has_closed_drainage"),
                    "has_no_drainage": a.get("has_no_drainage"),
                    "has_treated_tap_water": a.get("has_treated_tap_water"),
                    "has_safe_water_source": safe_water,
                    "has_pucca_road": a.get("has_pucca_road"),
                    "has_all_weather_road": a.get("has_all_weather_road"),
                    "pmgsy_connected": conn.get("connected"),
                    "domestic_power_hours_summer": a.get("domestic_power_hours_summer"),
                    "domestic_power_hours_winter": a.get("domestic_power_hours_winter"),
                    "mplads_completed_amount_total": m.get("completed_total"),
                    "mplads_completed_work_count": m.get("completed_count"),
                    "mplads_recommended_amount_total": m.get("recommended_total"),
                    "geom": conn.get("geom"),
                    "geom_source": "pmgsy_habitation" if conn.get("geom") is not None else None,
                }
            )

        stmt = insert(VillageFact).values(records)
        update_cols = {c: getattr(stmt.excluded, c) for c in records[0].keys() if c != "village_code"}
        stmt = stmt.on_conflict_do_update(index_elements=["village_code"], set_=update_cols)
        db.execute(stmt)
        db.commit()

        print(f"\nmaterialized {len(records)} village_fact rows")
        # Real non-null coverage report -- per the project's non-negotiable, don't silently
        # proceed with gaps.
        for col in [
            "total_population",
            "literacy_rate",
            "census_school_count",
            "kys_school_count",
            "has_safe_water_source",
            "has_closed_drainage",
            "has_all_weather_road",
            "pmgsy_connected",
            "mplads_completed_amount_total",
            "geom",
        ]:
            non_null = sum(1 for r in records if r[col] is not None)
            print(f"  {col}: {non_null}/{len(records)} non-null ({non_null / len(records):.1%})")


if __name__ == "__main__":
    run()
