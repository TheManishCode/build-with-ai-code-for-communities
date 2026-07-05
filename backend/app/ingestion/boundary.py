"""Ingest Karnataka's 28 Parliamentary Constituency boundaries from the 2024 KML."""

from __future__ import annotations

import geopandas as gpd
from geoalchemy2.shape import from_shape
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import PCBoundary

KML_PATH = settings.dataset_dir / "Parliamentary Constituencies Map" / "Parliamentary Constituencies Map 2024.kml"


def run() -> None:
    gdf = gpd.read_file(KML_PATH)
    karnataka = gdf[gdf["st_name"] == "KARNATAKA"]
    print(f"Karnataka PCs found: {len(karnataka)} (expected 28)")

    records = [
        {
            "pc_id": int(row.pc_id),
            "st_name": row.st_name,
            "pc_no": int(row.pc_no),
            "pc_name": row.pc_name,
            "geom": from_shape(row.geometry, srid=4326),
        }
        for row in karnataka.itertuples()
    ]

    with SessionLocal() as db:
        stmt = insert(PCBoundary).values(records)
        stmt = stmt.on_conflict_do_update(index_elements=["pc_id"], set_={"pc_name": stmt.excluded.pc_name})
        db.execute(stmt)
        db.commit()
    print(f"ingested {len(records)} PC boundaries")


if __name__ == "__main__":
    run()
