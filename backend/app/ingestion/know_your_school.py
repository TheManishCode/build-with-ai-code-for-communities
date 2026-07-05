"""Ingest the Know Your School (UDISE) directory for Bagalkot district.

Source is a single district-scoped JSON export (KYS (KA_BAGALKOT).json) whose
`data.content` is a flat list of school records. Most records don't carry a
populated `lgdvillageId` (source-side LGD linkage is sparse/inconsistent — see
the "0" sentinel handled below), so we fuzzy-match `villageName` against
`lgd_village.village_name` scoped to Bagalkot's LGD district_code (524) via
rapidfuzz. Urban schools' "village" is usually actually a town/ward name and
is expected to genuinely not match any LGD village — that's reported
separately from rural non-matches, which are a real data-quality signal.
"""

from __future__ import annotations

import json

from rapidfuzz import fuzz, process, utils
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import KnowYourSchool, LGDVillage

SOURCE_PATH = settings.dataset_dir / "Know Your School" / "KYS (KA_BAGALKOT).json"
BAGALKOT_LGD_DISTRICT_CODE = 524
MATCH_THRESHOLD = 85


def _clean_lgd_village_id(raw: object) -> int | None:
    """Source uses null, "-1", and "0" all as "not populated" sentinels."""
    if raw in (None, "", "-1", "0", -1, 0):
        return None
    try:
        val = int(raw)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def load_records() -> list[dict]:
    with SOURCE_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return data["data"]["content"]


def build_village_choices(db: Session) -> dict[int, str]:
    rows = (
        db.query(LGDVillage.village_code, LGDVillage.village_name)
        .filter(LGDVillage.district_code == BAGALKOT_LGD_DISTRICT_CODE)
        .all()
    )
    return {code: name for code, name in rows}


def ingest(db: Session) -> None:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(SOURCE_PATH)

    records = load_records()
    village_choices = build_village_choices(db)
    print(f"lgd_village candidates in district {BAGALKOT_LGD_DISTRICT_CODE}: {len(village_choices)}")

    upsert_rows: list[dict] = []
    had_source_lgd = 0
    needed_fuzzy = 0
    needed_fuzzy_rural = 0
    needed_fuzzy_urban = 0
    matched = 0
    matched_rural = 0
    matched_urban = 0
    non_matches: list[tuple] = []

    for rec in records:
        lgd_village_id = _clean_lgd_village_id(rec.get("lgdvillageId"))
        loc_desc = (rec.get("schLocDesc") or "").strip().lower()
        is_rural = loc_desc == "rural"
        is_urban = loc_desc == "urban"

        matched_code = None
        match_score = None

        if lgd_village_id is not None:
            had_source_lgd += 1
        else:
            needed_fuzzy += 1
            if is_rural:
                needed_fuzzy_rural += 1
            elif is_urban:
                needed_fuzzy_urban += 1

            village_name = rec.get("villageName")
            result = (
                process.extractOne(village_name, village_choices, scorer=fuzz.WRatio, processor=utils.default_process)
                if village_name
                else None
            )

            if result is not None:
                cand_name, cand_score, cand_code = result
                if cand_score >= MATCH_THRESHOLD:
                    matched_code = cand_code
                    match_score = cand_score
                    matched += 1
                    if is_rural:
                        matched_rural += 1
                    elif is_urban:
                        matched_urban += 1
                elif len(non_matches) < 15:
                    non_matches.append((rec.get("schoolName"), village_name, cand_name, round(cand_score, 1), rec.get("schLocDesc")))
            elif len(non_matches) < 15:
                non_matches.append((rec.get("schoolName"), village_name, None, None, rec.get("schLocDesc")))

        is_operational = (rec.get("schoolStatus") == 0) or (rec.get("schoolStatusName") == "Operational")

        upsert_rows.append(
            {
                "school_id": rec["schoolId"],
                "udise_code": rec.get("udiseschCode"),
                "school_name": rec.get("schoolName"),
                "district_name": rec.get("districtName"),
                "block_name": rec.get("blockName"),
                "village_name": rec.get("villageName"),
                "village_cd": rec.get("villWardCd"),
                "mgmt_desc": rec.get("schMgmtDesc"),
                "category_desc": rec.get("schCatDesc"),
                "is_operational": is_operational,
                "lgd_village_id": lgd_village_id,
                "lgd_village_name": rec.get("lgdvillName"),
                "matched_lgd_village_code": matched_code,
                "match_score": match_score,
            }
        )

    print(f"\ntotal schools loaded: {len(records)}")
    print(f"lgd_village_id already populated in source: {had_source_lgd}")
    print(f"needed fuzzy matching: {needed_fuzzy} (rural: {needed_fuzzy_rural}, urban: {needed_fuzzy_urban}, other/unknown: {needed_fuzzy - needed_fuzzy_rural - needed_fuzzy_urban})")

    if needed_fuzzy:
        print(f"fuzzy matched >= {MATCH_THRESHOLD}: {matched} / {needed_fuzzy} ({matched / needed_fuzzy:.1%})")
    if needed_fuzzy_rural:
        print(f"  rural-only match rate: {matched_rural} / {needed_fuzzy_rural} ({matched_rural / needed_fuzzy_rural:.1%})")
    if needed_fuzzy_urban:
        print(f"  urban-only match rate: {matched_urban} / {needed_fuzzy_urban} ({matched_urban / needed_fuzzy_urban:.1%})")

    print("\nSample non-matches (school_name, village_name, best_candidate, score, schLocDesc):")
    for row in non_matches:
        print(f"  {row}")

    chunk = 1000
    for i in range(0, len(upsert_rows), chunk):
        stmt = insert(KnowYourSchool).values(upsert_rows[i : i + chunk])
        stmt = stmt.on_conflict_do_update(
            index_elements=["school_id"],
            set_={
                "udise_code": stmt.excluded.udise_code,
                "school_name": stmt.excluded.school_name,
                "district_name": stmt.excluded.district_name,
                "block_name": stmt.excluded.block_name,
                "village_name": stmt.excluded.village_name,
                "village_cd": stmt.excluded.village_cd,
                "mgmt_desc": stmt.excluded.mgmt_desc,
                "category_desc": stmt.excluded.category_desc,
                "is_operational": stmt.excluded.is_operational,
                "lgd_village_id": stmt.excluded.lgd_village_id,
                "lgd_village_name": stmt.excluded.lgd_village_name,
                "matched_lgd_village_code": stmt.excluded.matched_lgd_village_code,
                "match_score": stmt.excluded.match_score,
            },
        )
        db.execute(stmt)
    db.commit()
    print(f"\nupserted {len(upsert_rows)} rows into know_your_school")


def run() -> None:
    with SessionLocal() as db:
        ingest(db)


if __name__ == "__main__":
    run()
