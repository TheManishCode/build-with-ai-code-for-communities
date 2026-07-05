"""Ingest the Census 2011 Primary Census Abstract Total (PCA-TOT) file for Bagalkot
district, keeping DISTRICT/TALUK/VILLAGE level rows (TOWN/WARD skipped — urban wards
out of scope for this MVP), and fuzzy-match VILLAGE-level rows to `lgd_village`.

`census_pca_village` has no natural business key in the migration-defined schema other
than the autoincrement `id`, so a plain on_conflict_do_update on `id` would not be
idempotent across reruns. Migration c2172e1c09fd adds a unique index over the natural key
(level, district_serial, subdistt_serial, town_vill_code, tru), substituting a sentinel
(-1) for the NULLs that occur at DISTRICT/TALUK level (SUB-DISTT/TOWN_VILL are 0 in the
source for those rows and are normalized to NULL here per the target schema), since
Postgres unique indexes never treat two NULLs as equal/conflicting — run migrations
before this script.
"""

from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd
from rapidfuzz import fuzz, process
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import CensusPCAVillage, LGDVillage

XLS_PATH = (
    settings.dataset_dir / "PCA-TOT Primary Census Abstract Total" / "PC01_PCA_TOT_29_02(KA_Bagalkot).xls"
)
SHEET_NAME = "Sheet1"
BAGALKOT_LGD_DISTRICT_CODE = 524
MATCH_THRESHOLD = 85.0

LEVELS_KEPT = {"DISTRICT", "TALUK", "VILLAGE"}

FIELD_MAP: dict[str, str] = {
    "LEVEL": "level",
    "DISTRICT": "district_serial",
    "SUB-DISTT": "subdistt_serial",
    "TOWN_VILL": "town_vill_code",
    "NAME": "name",
    "TRU": "tru",
    "No_HH": "total_households",
    "TOT_P": "total_population",
    "TOT_M": "male_population",
    "TOT_F": "female_population",
    "P_LIT": "literate_population",
    "P_ILL": "illiterate_population",
    "TOT_WORK_P": "total_workers",
    "MAINWORK_P": "main_workers",
    "MARGWORK_P": "marginal_workers",
    "NON_WORK_P": "non_workers",
}

INT_FIELDS = {
    "total_households", "total_population", "male_population", "female_population",
    "literate_population", "illiterate_population", "total_workers", "main_workers",
    "marginal_workers", "non_workers",
}

# Trailing qualifiers census village names carry (e.g. "Terdal (Rural)", "Badami (Rural) *")
_QUALIFIER_RE = re.compile(r"\s*\((?:Rural|CT|OG|Census Town|Out Growth)\)\s*$", re.IGNORECASE)
_TRAILING_STAR_RE = re.compile(r"\s*\*\s*$")


def _to_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def clean_name(name: str) -> str:
    """Strip trailing qualifiers like '(Rural)'/'(CT)'/'*' and collapse whitespace."""
    s = str(name).strip()
    # Qualifiers/asterisks can stack (e.g. "X (Rural) *") — strip repeatedly until stable.
    prev = None
    while prev != s:
        prev = s
        s = _TRAILING_STAR_RE.sub("", s)
        s = _QUALIFIER_RE.sub("", s)
        s = s.strip()
    return s


def _load_lgd_candidates(db: Session) -> tuple[list[int], list[str]]:
    rows = (
        db.query(LGDVillage.village_code, LGDVillage.village_name)
        .filter(LGDVillage.district_code == BAGALKOT_LGD_DISTRICT_CODE)
        .all()
    )
    codes = [r[0] for r in rows]
    cleaned_names = [clean_name(r[1]) for r in rows]
    return codes, cleaned_names


def ingest(db: Session) -> dict[str, Any]:
    print(f"reading {XLS_PATH} sheet={SHEET_NAME} (engine=xlrd) ...")
    df = pd.read_excel(XLS_PATH, engine="xlrd", sheet_name=SHEET_NAME)
    print(f"loaded {len(df)} rows total")

    missing_cols = [c for c in FIELD_MAP if c not in df.columns]
    if missing_cols:
        print(f"  [census_pca] WARNING: expected column(s) not found: {missing_cols}")

    level_col_present = "LEVEL" in df.columns
    if not level_col_present:
        raise RuntimeError("'LEVEL' column not found — cannot filter DISTRICT/TALUK/VILLAGE rows")

    sub = df[df["LEVEL"].isin(LEVELS_KEPT)].copy()
    level_counts = sub["LEVEL"].value_counts().to_dict()
    print(f"rows kept by level: {level_counts} (skipped TOWN/WARD and any other levels)")

    # Build fuzzy-match candidate pool from lgd_village for Bagalkot (LGD district_code=524).
    candidate_codes, candidate_names = _load_lgd_candidates(db)
    print(f"lgd_village candidates for district_code={BAGALKOT_LGD_DISTRICT_CODE}: {len(candidate_codes)}")

    records: list[dict[str, Any]] = []
    village_total = 0
    village_matched = 0
    unmatched_examples: list[tuple[str, str | None, float]] = []
    skipped_rows = 0

    for _, row in sub.iterrows():
        rec: dict[str, Any] = {}
        for src_col, field in FIELD_MAP.items():
            if src_col not in df.columns:
                rec[field] = None
                continue
            raw_val = row[src_col]
            if field in INT_FIELDS or field in ("district_serial",):
                rec[field] = _to_int(raw_val)
            elif field in ("subdistt_serial", "town_vill_code"):
                v = _to_int(raw_val)
                rec[field] = None if v in (None, 0) else v
            elif field in ("level", "name", "tru"):
                s = str(raw_val).strip() if raw_val is not None else None
                rec[field] = s if s else None
            else:
                rec[field] = raw_val

        if rec.get("level") is None or rec.get("district_serial") is None or rec.get("name") is None or rec.get("tru") is None:
            skipped_rows += 1
            continue

        rec["lgd_village_code"] = None
        rec["match_score"] = None

        if rec["level"] == "VILLAGE":
            village_total += 1
            query_name = clean_name(rec["name"])
            best = process.extractOne(query_name, candidate_names, scorer=fuzz.token_sort_ratio)
            if best is not None:
                matched_name, score, idx = best
                if score >= MATCH_THRESHOLD:
                    rec["lgd_village_code"] = candidate_codes[idx]
                    rec["match_score"] = float(score)
                    village_matched += 1
                else:
                    unmatched_examples.append((rec["name"], matched_name, float(score)))
            else:
                unmatched_examples.append((rec["name"], None, 0.0))

        records.append(rec)

    if skipped_rows:
        print(f"  [census_pca] skipped {skipped_rows} rows missing required key fields (level/district/name/tru)")

    if not records:
        print("  [census_pca] no records to insert")
        return {
            "total": 0, "village_total": 0, "village_matched": 0,
            "unmatched_examples": [],
        }


    all_fields = [f for f in records[0]]
    index_elements = [
        CensusPCAVillage.level,
        CensusPCAVillage.district_serial,
        func.coalesce(CensusPCAVillage.subdistt_serial, -1),
        func.coalesce(CensusPCAVillage.town_vill_code, -1),
        CensusPCAVillage.tru,
    ]
    chunk = 500
    for i in range(0, len(records), chunk):
        batch = records[i : i + chunk]
        stmt = insert(CensusPCAVillage).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=index_elements,
            set_={f: getattr(stmt.excluded, f) for f in all_fields},
        )
        db.execute(stmt)
    db.commit()

    return {
        "total": len(records),
        "village_total": village_total,
        "village_matched": village_matched,
        "unmatched_examples": unmatched_examples,
    }


def run() -> None:
    with SessionLocal() as db:
        result = ingest(db)

    total = result["total"]
    v_total = result["village_total"]
    v_matched = result["village_matched"]
    rate = (v_matched / v_total * 100.0) if v_total else 0.0

    print(f"census_pca_village: {total} rows upserted (DISTRICT+TALUK+VILLAGE)")
    print(f"village rows: {v_total}, matched >= {MATCH_THRESHOLD}: {v_matched}, match rate: {rate:.1f}%")

    examples = result["unmatched_examples"]
    if examples:
        print(f"unmatched examples ({min(len(examples), 10)} of {len(examples)} shown):")
        for name, best_candidate, score in examples[:10]:
            print(f"  - {name!r} -> best candidate {best_candidate!r} (score {score:.1f})")
    else:
        print("no unmatched village rows (all matched >= threshold)")


if __name__ == "__main__":
    run()
