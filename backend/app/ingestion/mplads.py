"""Ingest MPLADs (Members of Parliament Local Area Development Scheme) data for the
BAGALKOT constituency: allocated fund limits per MP, the recommended/sanctioned/completed
works lifecycle (merged one row per work_code), and per-disbursement expenditure records.

Source CSVs cover all 28 Karnataka constituencies; every file is filtered down to
Constituency == "BAGALKOT" only. Two Lok Sabha terms are ingested:
  - 18th (current)    -> files named "...{KA}.csv"
  - 17th (historical)  -> files named "(KA)17th Lok Sabha MPs_...csv" (no Sanctioned file exists
    for this term in the source data -- confirmed by directory listing).

The "Work" column in the Recommended/Sanctioned/Completed files embeds a work code as a
prefix, e.g. "WS/MP618/2024-2025/156002-Construction of community centers and community
halls". A handful of not-yet-sanctioned rows use "NA" instead of a real code (e.g.
"NA-Construction of community centers and community halls") -- since "NA" is not a unique
key, those get a synthesized fallback code (NA-<term>-<Sr. No.>) so distinct works don't
collide in the work_code upsert.

The free-text "Work Description" column (not persisted as its own DB column -- the schema
only stores work_title, the generic category text after the code prefix) is used
transiently to extract a candidate village/place name, which is then fuzzy-matched via
rapidfuzz against lgd_village.village_name for district_code=524 (Bagalkot).
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process, utils
from sqlalchemy import bindparam, delete, func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import LGDVillage, MPLADsAllocatedLimit, MPLADsExpenditure, MPLADsWork

MPLADS_DIR = settings.dataset_dir / "MPLADs"
CONSTITUENCY = settings.constituency_name  # "BAGALKOT"
BAGALKOT_DISTRICT_CODE = 524

WORK_CODE_RE = re.compile(r"^(WS/MP\d+/\d{4}-\d{4}/\d+)-(.*)$", re.S)

# Matches the free-text "in <PLACE> Village" / "in <PLACE>," pattern in Work Description.
PLACE_RE = re.compile(r"\bin\s+(.+?)(?:\s+village\b|,|$)", re.IGNORECASE)
PAREN_RE = re.compile(r"\(([^)]+)\)")

MATCH_THRESHOLD = 80.0


def _clean_amount(val: str | float | None) -> int | None:
    """'14,70,00,000' / '5,23,44,136.63' -> int. Strips commas, the ₹ symbol, whitespace."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if not s:
        return None
    s = s.replace("₹", "").replace(",", "").strip()
    if not s:
        return None
    return int(round(float(s)))


def _clean_str(val) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    return s or None


def _clean_date(val) -> date | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    ts = pd.to_datetime(val, format="%d-%b-%Y", errors="coerce")
    if pd.isna(ts):
        ts = pd.to_datetime(val, dayfirst=True, errors="coerce")
    return None if pd.isna(ts) else ts.date()


def _read_bagalkot_csv(path: Path) -> tuple[pd.DataFrame, int, int]:
    """Read a CSV and filter to Constituency == BAGALKOT (case-insensitive, stripped).
    Returns (filtered_df, total_rows, filtered_rows)."""
    df = pd.read_csv(path, dtype=str, encoding="utf-8")
    df.columns = [c.strip() for c in df.columns]
    total = len(df)
    df["Constituency"] = df["Constituency"].astype(str).str.strip()
    mask = df["Constituency"].str.upper() == CONSTITUENCY.upper()
    filtered = df[mask].copy()
    return filtered, total, len(filtered)


def parse_work_code_title(raw: str, term: str, sr_no: str) -> tuple[str, str]:
    raw = (raw or "").strip()
    m = WORK_CODE_RE.match(raw)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    # Fallback: split on the first hyphen (covers "NA-..." and any unexpected prefix shape).
    if "-" in raw:
        code, title = raw.split("-", 1)
        code = code.strip()
        title = title.strip()
    else:
        code, title = raw, raw
    if code.upper() == "NA":
        # "NA" is not a unique key -- disambiguate per-row so distinct not-yet-sanctioned
        # works don't collide on upsert.
        code = f"NA-{term}-{sr_no}"
    return code, title


# ---------------------------------------------------------------------------
# Allocated Limit
# ---------------------------------------------------------------------------


def ingest_allocated_limit(db: Session, filename: str, term: str) -> tuple[int, int, int]:
    path = MPLADS_DIR / filename
    df, total, filtered_n = _read_bagalkot_csv(path)

    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "constituency": row["Constituency"],
                "mp_name": _clean_str(row["Hon'ble Member Of Parliament"]),
                "allocated_amount": _clean_amount(row["Allocated Amount ( ₹ )"]),
                "lok_sabha_term": term,
            }
        )

    # No natural unique key on this table (autoincrement id) -- delete-then-insert for this
    # term/constituency scope so reruns don't accumulate duplicates.
    db.execute(
        delete(MPLADsAllocatedLimit).where(
            MPLADsAllocatedLimit.constituency == CONSTITUENCY,
            MPLADsAllocatedLimit.lok_sabha_term == term,
        )
    )
    if records:
        db.execute(insert(MPLADsAllocatedLimit).values(records))
    db.commit()
    return total, filtered_n, len(records)


# ---------------------------------------------------------------------------
# Works Recommended / Sanctioned / Completed -- merged into MPLADsWork
# ---------------------------------------------------------------------------


def _upsert_work_rows(db: Session, records: list[dict]) -> None:
    if not records:
        return
    stmt = insert(MPLADsWork).values(records)
    settable = [c for c in records[0].keys() if c != "work_code"]
    stmt = stmt.on_conflict_do_update(
        index_elements=["work_code"],
        set_={col: func.coalesce(getattr(stmt.excluded, col), getattr(MPLADsWork, col)) for col in settable},
    )
    db.execute(stmt)
    db.commit()


def ingest_works_recommended(db: Session, filename: str, term: str, description_by_code: dict[str, str]) -> tuple[int, int, int]:
    path = MPLADS_DIR / filename
    df, total, filtered_n = _read_bagalkot_csv(path)

    records = []
    for _, row in df.iterrows():
        code, title = parse_work_code_title(row["Work"], term, row["Sr. No."])
        desc = _clean_str(row.get("Work Description"))
        if desc:
            description_by_code[code] = desc
        records.append(
            {
                "work_code": code,
                "category": _clean_str(row.get("Work Category")),
                "work_title": title,
                "ida": _clean_str(row.get("IDA")),
                "mp_name": _clean_str(row["Hon'ble Member Of Parliament"]),
                "constituency": row["Constituency"],
                "lok_sabha_term": term,
                "recommended_date": _clean_date(row.get("Recommendation Date")),
                "recommended_amount": _clean_amount(row.get("RECOMMENDED AMOUNT ( ₹ )")),
            }
        )
    _upsert_work_rows(db, records)
    return total, filtered_n, len(records)


def ingest_works_sanctioned(db: Session, filename: str, term: str, description_by_code: dict[str, str]) -> tuple[int, int, int]:
    path = MPLADS_DIR / filename
    df, total, filtered_n = _read_bagalkot_csv(path)

    records = []
    for _, row in df.iterrows():
        code, title = parse_work_code_title(row["Work"], term, row["Sr. No."])
        desc = _clean_str(row.get("Work Description"))
        if desc:
            description_by_code[code] = desc
        records.append(
            {
                "work_code": code,
                "category": _clean_str(row.get("Work Category")),
                "work_title": title,
                "ida": _clean_str(row.get("IDA")),
                "mp_name": _clean_str(row["Hon'ble Member Of Parliament"]),
                "constituency": row["Constituency"],
                "lok_sabha_term": term,
                "sanction_date": _clean_date(row.get("Sanction Date")),
                "sanction_stage": _clean_str(row.get("Work Stages")),
                "sanction_amount": _clean_amount(row.get("Sanction Amount ( ₹ )")),
            }
        )
    _upsert_work_rows(db, records)
    return total, filtered_n, len(records)


def ingest_works_completed(db: Session, filename: str, term: str, description_by_code: dict[str, str]) -> tuple[int, int, int]:
    path = MPLADS_DIR / filename
    df, total, filtered_n = _read_bagalkot_csv(path)

    records = []
    for _, row in df.iterrows():
        code, title = parse_work_code_title(row["Work"], term, row["Sr. No."])
        desc = _clean_str(row.get("Work Description"))
        if desc:
            description_by_code[code] = desc
        records.append(
            {
                "work_code": code,
                "category": _clean_str(row.get("Work Category")),
                "work_title": title,
                "ida": _clean_str(row.get("IDA")),
                "mp_name": _clean_str(row["Hon'ble Member Of Parliament"]),
                "constituency": row["Constituency"],
                "lok_sabha_term": term,
                "completed_date": _clean_date(row.get("Completed Date")),
                "completed_rating": _clean_str(row.get("Average Rating")),
                "completed_amount": _clean_amount(row.get("FINAL AMOUNT ( ₹ )")),
            }
        )
    _upsert_work_rows(db, records)
    return total, filtered_n, len(records)


# ---------------------------------------------------------------------------
# Expenditure -- append-only, no FK to mplads_work
# ---------------------------------------------------------------------------


def ingest_expenditure(db: Session, filename: str, term: str) -> tuple[int, int, int]:
    path = MPLADS_DIR / filename
    df, total, filtered_n = _read_bagalkot_csv(path)

    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "work_id": _clean_str(row.get("Work Id")) or "",
                "work_title": _clean_str(row.get("Work")) or "",
                "vendor_name": _clean_str(row.get("Vendor Name")),
                "ida": _clean_str(row.get("IDA")),
                "mp_name": _clean_str(row["Hon'ble Member Of Parliament"]),
                "constituency": row["Constituency"],
                "lok_sabha_term": term,
                "expenditure_date": _clean_date(row.get("Expenditure Date")),
                "work_status": _clean_str(row.get("Work Status")),
                "amount": _clean_amount(row.get("Fund Disbursed Amount ( ₹ )")),
            }
        )

    # Append-only table with no natural unique key -- delete-then-insert per term/constituency
    # scope so reruns don't accumulate duplicate transaction rows.
    db.execute(
        delete(MPLADsExpenditure).where(
            MPLADsExpenditure.constituency == CONSTITUENCY,
            MPLADsExpenditure.lok_sabha_term == term,
        )
    )
    if records:
        db.execute(insert(MPLADsExpenditure).values(records))
    db.commit()
    return total, filtered_n, len(records)


# ---------------------------------------------------------------------------
# Fuzzy village matching
# ---------------------------------------------------------------------------


def extract_place_candidates(text: str) -> list[str]:
    """Pull likely village/place name candidate(s) out of messy free text like
    'Construction of Community Hall in Rabakavi-Banahatti (RAMPUR), Property No.CTSNO.3427,3428'.
    Returns candidates ordered best-guess-first; caller tries all and keeps the best fuzzy score.
    """
    m = PLACE_RE.search(text)
    if not m:
        return []
    chunk = m.group(1).strip()
    candidates = []
    paren = PAREN_RE.search(chunk)
    if paren:
        candidates.append(paren.group(1).strip())
        outer = PAREN_RE.sub("", chunk).strip()
        if outer:
            candidates.append(outer)
    else:
        candidates.append(chunk)
    return [c for c in candidates if c]


def run_village_matching(db: Session, description_by_code: dict[str, str]) -> tuple[int, int, list[tuple[str, str, str, float]], list[tuple[str, str]]]:
    """Fuzzy-match each MPLADsWork row's extracted place candidate against LGDVillage names
    in district_code=524. Returns (matched_count, total_count, example_matches, example_misses).
    """
    villages = db.query(LGDVillage.village_code, LGDVillage.village_name).filter(
        LGDVillage.district_code == BAGALKOT_DISTRICT_CODE
    ).all()
    village_names = [v.village_name for v in villages if v.village_name]
    code_by_name: dict[str, int] = {}
    for v in villages:
        if v.village_name:
            code_by_name.setdefault(v.village_name, v.village_code)

    works = db.query(MPLADsWork.work_code, MPLADsWork.work_title).all()

    updates = []
    example_matches: list[tuple[str, str, str, float]] = []
    example_misses: list[tuple[str, str]] = []
    matched_n = 0

    for w in works:
        text = description_by_code.get(w.work_code) or w.work_title or ""
        candidates = extract_place_candidates(text)
        best_name, best_score = None, 0.0
        for cand in candidates:
            result = process.extractOne(cand, village_names, scorer=fuzz.WRatio, processor=utils.default_process)
            if result is not None:
                name, score, _ = result
                if score > best_score:
                    best_name, best_score = name, score
        if best_name is not None and best_score >= MATCH_THRESHOLD:
            village_code = code_by_name[best_name]
            updates.append({"wc": w.work_code, "vc": village_code, "sc": float(best_score)})
            matched_n += 1
            if len(example_matches) < 8:
                example_matches.append((w.work_code, text[:80], best_name, best_score))
        else:
            if len(example_misses) < 8:
                example_misses.append((w.work_code, text[:80]))

    if updates:
        # Use the Core Table (not the ORM-mapped class) for the bulk parameterized UPDATE --
        # the ORM-enabled Update construct requires bindparam names to match PK attribute names
        # for its bulk-by-PK shortcut, which isn't what we want here.
        table = MPLADsWork.__table__
        stmt = (
            update(table)
            .where(table.c.work_code == bindparam("wc"))
            .values(matched_lgd_village_code=bindparam("vc"), match_score=bindparam("sc"))
        )
        db.execute(stmt, updates)
        db.commit()

    return matched_n, len(works), example_matches, example_misses


# ---------------------------------------------------------------------------


def run() -> None:
    description_by_code: dict[str, str] = {}

    with SessionLocal() as db:
        print("=== Allocated Limit ===")
        total, filt, n = ingest_allocated_limit(db, "Allocated Limit for Honble MPs{KA}.csv", "18th")
        print(f"  18th: source={total} bagalkot_filtered={filt} inserted={n}")
        total, filt, n = ingest_allocated_limit(
            db, "(KA)17th Lok Sabha MPs_Allocated Limit for Honble MPs.csv", "17th"
        )
        print(f"  17th: source={total} bagalkot_filtered={filt} inserted={n}")

        print("=== Works Recommended ===")
        total, filt, n = ingest_works_recommended(db, "Works Recommended{KA}.csv", "18th", description_by_code)
        print(f"  18th: source={total} bagalkot_filtered={filt} upserted={n}")
        total, filt, n = ingest_works_recommended(
            db, "(KA)17th Lok Sabha MPs_Works Recommended.csv", "17th", description_by_code
        )
        print(f"  17th: source={total} bagalkot_filtered={filt} upserted={n}")

        print("=== Works Sanctioned ===")
        total, filt, n = ingest_works_sanctioned(db, "Works Sanctioned{KA}.csv", "18th", description_by_code)
        print(f"  18th: source={total} bagalkot_filtered={filt} upserted={n}")
        print("  17th: no Sanctioned file exists for this term in source data -- skipped")

        print("=== Works Completed ===")
        total, filt, n = ingest_works_completed(db, "Works Completed{KA}.csv", "18th", description_by_code)
        print(f"  18th: source={total} bagalkot_filtered={filt} upserted={n}")
        total, filt, n = ingest_works_completed(
            db, "(KA)17th Lok Sabha MPs_Works Completed.csv", "17th", description_by_code
        )
        print(f"  17th: source={total} bagalkot_filtered={filt} upserted={n}")

        print("=== Expenditure ===")
        total, filt, n = ingest_expenditure(
            db, "Expenditure on Completed and On-going Works as on Date{KA}.csv", "18th"
        )
        print(f"  18th: source={total} bagalkot_filtered={filt} inserted={n}")
        total, filt, n = ingest_expenditure(
            db,
            "(KA)17th Lok Sabha MPs_Expenditure on Completed and On-going Works as on Date.csv",
            "17th",
        )
        print(f"  17th: source={total} bagalkot_filtered={filt} inserted={n}")

        print("=== Village fuzzy matching ===")
        matched_n, total_n, examples, misses = run_village_matching(db, description_by_code)
        rate = (matched_n / total_n * 100) if total_n else 0.0
        print(f"  matched {matched_n}/{total_n} ({rate:.1f}%) work rows to an LGD village (score >= {MATCH_THRESHOLD})")
        print("  example matches:")
        for wc, text, name, score in examples:
            print(f"    {wc}: '{text}' -> '{name}' (score={score:.1f})")
        print("  example non-matches:")
        for wc, text in misses:
            print(f"    {wc}: '{text}'")

        print("=== Final table counts ===")
        print(f"  mplads_allocated_limit: {db.query(MPLADsAllocatedLimit).count()}")
        print(f"  mplads_work: {db.query(MPLADsWork).count()}")
        print(f"  mplads_expenditure: {db.query(MPLADsExpenditure).count()}")


if __name__ == "__main__":
    run()
