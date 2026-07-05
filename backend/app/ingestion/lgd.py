"""Ingest the LGD (Local Government Directory) backbone: district -> subdistrict -> block,
village master, PRI local-body hierarchy, and village-to-Gram-Panchayat mapping.

These files are the join spine every other dataset resolves to. The .xls files under
LGD/downloadDir*/ are actually Excel-2003 SpreadsheetML XML (see app.ingestion.msxml) —
NOT binary Excel, xlrd/openpyxl cannot open them.
"""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.ingestion.msxml import assert_header, find_data_rows, iter_rows
from app.models import LGDBlock, LGDDistrict, LGDLocalBody, LGDSubdistrict, LGDVillage, LGDVillageGPMapping

LGD_DIR = settings.dataset_dir / "LGD"
DOWNLOAD_DIR = LGD_DIR / "downloadDir2026_07_04_07_25_10_750"


def _s(row: dict[int, str | None], col: int) -> str | None:
    val = row.get(col)
    return val.strip() if val is not None else None


def _int(row: dict[int, str | None], col: int) -> int | None:
    val = _s(row, col)
    return int(float(val)) if val else None


def ingest_districts(db: Session) -> int:
    path = DOWNLOAD_DIR / "districtofSpecificState2026_07_04_07_25_10_798.xls"
    rows = iter_rows(path)
    header, data = find_data_rows(rows, "District Code")
    assert_header(header, {2: "District Code", 4: "District Name", 6: "  Census 2001 Code", 7: "Census 2011 Code"})

    records = []
    for row in data:
        code = _int(row, 2)
        if code is None:
            continue
        records.append(
            {
                "district_code": code,
                "district_name": _s(row, 4),
                "census2001_code": _s(row, 6),
                "census2011_code": _s(row, 7),
            }
        )
    stmt = insert(LGDDistrict).values(records)
    stmt = stmt.on_conflict_do_update(index_elements=["district_code"], set_={"district_name": stmt.excluded.district_name})
    db.execute(stmt)
    db.commit()
    return len(records)


def ingest_subdistricts(db: Session) -> int:
    path = DOWNLOAD_DIR / "subDistrictofSpecificState2026_07_04_07_25_10_842.xls"
    rows = iter_rows(path)
    header, data = find_data_rows(rows, "Subdistrict Code")
    assert_header(header, {2: "District code", 4: "Subdistrict Code", 6: "Subdistrict Name  ", 9: "Census 2011 Code"})

    known_districts = {d.district_code for d in db.query(LGDDistrict.district_code).all()}
    records, skipped = [], 0
    for row in data:
        code = _int(row, 4)
        district_code = _int(row, 2)
        if code is None:
            continue
        if district_code not in known_districts:
            skipped += 1
            continue
        records.append(
            {
                "subdistrict_code": code,
                "subdistrict_name": _s(row, 6),
                "district_code": district_code,
                "census2001_code": _s(row, 8),
                "census2011_code": _s(row, 9),
            }
        )
    if skipped:
        print(f"  [subdistricts] skipped {skipped} rows with unknown district_code")
    stmt = insert(LGDSubdistrict).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["subdistrict_code"], set_={"subdistrict_name": stmt.excluded.subdistrict_name}
    )
    db.execute(stmt)
    db.commit()
    return len(records)


def ingest_blocks(db: Session) -> int:
    path = DOWNLOAD_DIR / "blockofspecificState2026_07_04_07_25_19_367.xls"
    rows = iter_rows(path)
    header, data = find_data_rows(rows, "Block Code")
    assert_header(header, {2: "District Code", 4: "Block Code", 6: "Block Name"})

    known_districts = {d.district_code for d in db.query(LGDDistrict.district_code).all()}
    records, skipped = [], 0
    for row in data:
        code = _int(row, 4)
        district_code = _int(row, 2)
        if code is None:
            continue
        if district_code not in known_districts:
            skipped += 1
            continue
        records.append({"block_code": code, "block_name": _s(row, 6), "district_code": district_code})
    if skipped:
        print(f"  [blocks] skipped {skipped} rows with unknown district_code")
    stmt = insert(LGDBlock).values(records)
    stmt = stmt.on_conflict_do_update(index_elements=["block_code"], set_={"block_name": stmt.excluded.block_name})
    db.execute(stmt)
    db.commit()
    return len(records)


def ingest_villages(db: Session) -> int:
    path = DOWNLOAD_DIR / "villageofSpecificState2026_07_04_07_25_13_982.xls"
    rows = iter_rows(path)
    header, data = find_data_rows(rows, "Village Code")
    assert_header(
        header,
        {2: "District Code", 4: "Sub-District Code", 6: "Village Code", 10: "Village Status", 12: "Census 2011 Code"},
    )

    known_districts = {d.district_code for d in db.query(LGDDistrict.district_code).all()}
    known_subdistricts = {s.subdistrict_code for s in db.query(LGDSubdistrict.subdistrict_code).all()}
    records, skipped_district, skipped_subdistrict = [], 0, 0
    for row in data:
        code = _int(row, 6)
        if code is None:
            continue
        district_code = _int(row, 2)
        subdistrict_code = _int(row, 4)
        if district_code not in known_districts:
            skipped_district += 1
            continue
        if subdistrict_code is not None and subdistrict_code not in known_subdistricts:
            subdistrict_code = None
            skipped_subdistrict += 1
        records.append(
            {
                "village_code": code,
                "village_name": _s(row, 8),
                "village_name_local": _s(row, 9),
                "district_code": district_code,
                "subdistrict_code": subdistrict_code,
                "census2001_code": _s(row, 11),
                "census2011_code": _s(row, 12),
                "village_status": _s(row, 10),
            }
        )
    if skipped_district:
        print(f"  [villages] skipped {skipped_district} rows with unknown district_code")
    if skipped_subdistrict:
        print(f"  [villages] {skipped_subdistrict} rows had unknown subdistrict_code (nulled, kept row)")

    # Insert in chunks — ~30.7k rows in one statement is fine for Postgres but chunk for safety/logging.
    chunk = 5000
    for i in range(0, len(records), chunk):
        stmt = insert(LGDVillage).values(records[i : i + chunk])
        stmt = stmt.on_conflict_do_update(index_elements=["village_code"], set_={"village_name": stmt.excluded.village_name})
        db.execute(stmt)
    db.commit()
    return len(records)


def ingest_local_bodies(db: Session) -> int:
    path = DOWNLOAD_DIR / "priLbSpecificState2026_07_04_07_25_14_643.xls"
    rows = iter_rows(path)
    header, data = find_data_rows(rows, "Localbody Code")
    assert_header(header, {3: "Localbody Type Name", 4: "Localbody Code", 8: "Parent Localbody Code"})

    records = []
    for row in data:
        code = _int(row, 4)
        if code is None:
            continue
        records.append(
            {
                "localbody_code": code,
                "localbody_type_name": _s(row, 3),
                "localbody_name": _s(row, 6) or _s(row, 7) or "",
                "parent_localbody_code": _int(row, 8),
            }
        )
    # Insert without parent FK first (self-referencing — parents may appear after children in file order),
    # then a second pass to set parent_localbody_code once all rows exist.
    for rec in records:
        parent = rec.pop("parent_localbody_code")
        rec["_parent"] = parent
    stmt = insert(LGDLocalBody).values([{k: v for k, v in r.items() if k != "_parent"} for r in records])
    stmt = stmt.on_conflict_do_update(index_elements=["localbody_code"], set_={"localbody_name": stmt.excluded.localbody_name})
    db.execute(stmt)
    db.commit()

    known_codes = {c for c, in db.query(LGDLocalBody.localbody_code).all()}
    for rec in records:
        if rec["_parent"] is not None and rec["_parent"] in known_codes:
            db.query(LGDLocalBody).filter(LGDLocalBody.localbody_code == rec["localbody_code"]).update(
                {"parent_localbody_code": rec["_parent"]}
            )
    db.commit()
    return len(records)


def ingest_village_gp_mapping(db: Session) -> int:
    path = DOWNLOAD_DIR / "villageGramPanchayatMapping2026_07_04_07_25_19_033.xls"
    rows = iter_rows(path)
    header, data = find_data_rows(rows, "Village Code")
    assert_header(header, {10: "Village Code", 14: "Local Body Code"})

    known_villages = {v for v, in db.query(LGDVillage.village_code).all()}
    known_bodies = {b for b, in db.query(LGDLocalBody.localbody_code).all()}
    records, skipped = [], 0
    for row in data:
        village_code = _int(row, 10)
        local_body_code = _int(row, 14)
        if village_code is None or local_body_code is None:
            continue
        if village_code not in known_villages or local_body_code not in known_bodies:
            skipped += 1
            continue
        records.append({"village_code": village_code, "local_body_code": local_body_code})
    if skipped:
        print(f"  [gp_mapping] skipped {skipped} rows with unknown village/local-body code")

    before = len(records)
    dedup = {r["village_code"]: r for r in records}
    records = list(dedup.values())
    if before != len(records):
        print(f"  [gp_mapping] deduped {before - len(records)} rows with a repeated village_code (kept last)")

    chunk = 5000
    for i in range(0, len(records), chunk):
        stmt = insert(LGDVillageGPMapping).values(records[i : i + chunk])
        stmt = stmt.on_conflict_do_update(
            index_elements=["village_code"], set_={"local_body_code": stmt.excluded.local_body_code}
        )
        db.execute(stmt)
    db.commit()
    return len(records)


def run() -> None:
    with SessionLocal() as db:
        n = ingest_districts(db)
        print(f"districts: {n}")
        n = ingest_subdistricts(db)
        print(f"subdistricts: {n}")
        n = ingest_blocks(db)
        print(f"blocks: {n}")
        n = ingest_local_bodies(db)
        print(f"local bodies: {n}")
        n = ingest_villages(db)
        print(f"villages: {n}")
        n = ingest_village_gp_mapping(db)
        print(f"village-GP mappings: {n}")


if __name__ == "__main__":
    run()
