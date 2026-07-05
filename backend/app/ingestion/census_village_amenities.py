"""Ingest the Census 2011 District Census Handbook 'Village Amenities' table
(sheet Village_Data_2900), scoped to Bagalkot district.

The source workbook covers all 30 Karnataka districts (29,340 rows / 396 cols
statewide) — we filter down to Bagalkot on ingest. Column names in the source
have inconsistent whitespace (extra/leading/trailing/double spaces), so columns
are resolved defensively via a stripped-name lookup map rather than assumed to
match byte-for-byte.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import CensusVillageAmenities

XLSX_PATH = (
    settings.dataset_dir
    / "Census of India 2011 - Karnataka - Series 30 - Part XII B - District Census Handbook, Bangalore Rural"
    / "Karnataka - Village Amenities.xlsx"
)
SHEET_NAME = "Village_Data_2900"
TARGET_DISTRICT_PREFIX = "bagalkot"  # Census "Bagalkot" (LGD spells it "Bagalkote") — matched case-insensitively/stripped

# canonical (whitespace-collapsed) source column name -> model field, for direct passthrough fields.
# NOTE: keys here are the CANONICAL form (all whitespace runs collapsed to a single space, stripped)
# — they are looked up via the same _canon() transform applied to the source columns, so exact
# source spacing (double spaces, trailing spaces, etc.) does not matter here.
DIRECT_MAP: dict[str, str] = {
    "Village Code": "village_code",
    "District Name": "district_name",
    "Sub District Name": "subdistrict_name",
    "Village Name": "village_name",
    "CD Block Name": "cd_block_name",
    "Gram Panchayat Name": "gram_panchayat_name",
    "Total Geographical Area (in Hectares)": "total_geographical_area_ha",
    "Total Households": "total_households",
    "Total Population of Village": "total_population",
    "Total Male Population of Village": "male_population",
    "Total Female Population of Village": "female_population",
    "Total Scheduled Castes Population of Village": "sc_population",
    "Total Scheduled Tribes Population of Village": "st_population",
    "Govt Primary School (Numbers)": "govt_primary_schools",
    "Private Primary School (Numbers)": "pvt_primary_schools",
    "Govt Middle School (Numbers)": "govt_middle_schools",
    "Private Middle School (Numbers)": "pvt_middle_schools",
    "Govt Secondary School (Numbers)": "govt_secondary_schools",
    "Private Secondary School (Numbers)": "pvt_secondary_schools",
    "Govt Senior Secondary School (Numbers)": "govt_sr_secondary_schools",
    "Private Senior Secondary School (Numbers)": "pvt_sr_secondary_schools",
    "Primary Health Centre (Numbers)": "primary_health_centre_count",
    "Primary Heallth Sub Centre (Numbers)": "primary_health_subcentre_count",
    "Community Health Centre (Numbers)": "community_health_centre_count",
    "Power Supply For Domestic Use Summer (April-Sept.) per day (in Hours)": "domestic_power_hours_summer",
    "Power Supply For Domestic Use Winter (Oct.-March) per day (in Hours)": "domestic_power_hours_winter",
    "Nearest Town Name": "nearest_town_name",
    "Nearest Town Distance from Village (in Km.)": "nearest_town_distance_km",
}

# canonical (whitespace-collapsed) source column name -> model boolean field, for Status A(1)/NA(2) columns.
STATUS_MAP: dict[str, str] = {
    "Tap Water-Treated (Status A(1)/NA(2))": "has_treated_tap_water",
    "Hand Pump (Status A(1)/NA(2))": "has_hand_pump",
    "Tube Wells/Borehole (Status A(1)/NA(2))": "has_tube_well",
    "Covered Well (Status A(1)/NA(2))": "has_covered_well",
    "Closed Drainage (Status A(1)/NA(2))": "has_closed_drainage",
    "Open Drainage (Status A(1)/NA(2))": "has_open_drainage",
    "No Drainage (Status A(1)/NA(2))": "has_no_drainage",
    "Black Topped (pucca) Road (Status A(1)/NA(2))": "has_pucca_road",
    "All Weather Road (Status A(1)/NA(2))": "has_all_weather_road",
    "Gravel (kuchha) Roads (Status A(1)/NA(2))": "has_kuchha_road",
    "National Highway (Status A(1)/NA(2))": "has_national_highway",
    "State Highway (Status A(1)/NA(2))": "has_state_highway",
    "Power Supply For Domestic Use (Status A(1)/NA(2))": "domestic_power_supply",
    "Commercial Bank (Status A(1)/NA(2))": "has_commercial_bank",
    "Cooperative Bank (Status A(1)/NA(2))": "has_cooperative_bank",
    "ATM (Status A(1)/NA(2))": "has_atm",
    "Self - Help Group (SHG) (Status A(1)/NA(2))": "has_shg",
}


def _canon(col: str) -> str:
    """Collapse all whitespace runs to single spaces and strip ends."""
    return " ".join(str(col).split())


def _json_safe(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        f = float(val)
        return None if math.isnan(f) else f
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if isinstance(val, pd.Timestamp):
        return val.isoformat()
    if pd.isna(val) if not isinstance(val, (list, dict)) else False:
        return None
    return val


def _to_int(val: Any) -> int | None:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _to_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _to_str(val: Any) -> str | None:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    return s or None


def _status_to_bool(val: Any) -> bool:
    """1 = Available -> True; 2, blank, or anything else -> False."""
    i = _to_int(val)
    return i == 1


def _build_column_lookup(columns: list[str]) -> dict[str, str]:
    """canonical (whitespace-collapsed) name -> actual source column name."""
    lookup: dict[str, str] = {}
    for c in columns:
        lookup[_canon(c)] = c
    return lookup


def ingest(db: Session) -> int:
    print(f"reading {XLSX_PATH} sheet={SHEET_NAME} ...")
    df = pd.read_excel(XLSX_PATH, sheet_name=SHEET_NAME)
    print(f"loaded {len(df)} rows x {len(df.columns)} cols statewide")

    lookup = _build_column_lookup(list(df.columns))

    missing = [name for name in list(DIRECT_MAP) + list(STATUS_MAP) if name not in lookup]
    if missing:
        print(f"  [census_village_amenities] WARNING: {len(missing)} expected column(s) not found, will be left null:")
        for m in missing:
            print(f"    - {m!r}")

    district_col = lookup.get("District Name")
    if district_col is None:
        raise RuntimeError("'District Name' column not found in source — cannot filter to Bagalkot")

    normalized = df[district_col].astype(str).str.strip().str.lower()
    mask = normalized.str.startswith(TARGET_DISTRICT_PREFIX)
    sub = df[mask].copy()
    matched_names = sorted(df.loc[mask, district_col].unique().tolist())
    print(f"district_name values matched for prefix {TARGET_DISTRICT_PREFIX!r}: {matched_names}")
    print(f"rows filtered to Bagalkot: {len(sub)} (of {len(df)} statewide)")

    records: list[dict[str, Any]] = []
    skipped_no_village_code = 0
    for _, row in sub.iterrows():
        village_code_col = lookup.get("Village Code")
        village_code = _to_int(row[village_code_col]) if village_code_col else None
        if village_code is None:
            skipped_no_village_code += 1
            continue

        rec: dict[str, Any] = {"village_code": village_code}

        # direct passthrough fields
        for canon_name, field in DIRECT_MAP.items():
            if field == "village_code":
                continue
            src_col = lookup.get(canon_name)
            if src_col is None:
                rec.setdefault(field, None)
                continue
            raw_val = row[src_col]
            if field in ("district_name", "subdistrict_name", "village_name", "cd_block_name",
                         "gram_panchayat_name", "nearest_town_name"):
                rec[field] = _to_str(raw_val)
            elif field in ("total_geographical_area_ha", "nearest_town_distance_km",
                           "domestic_power_hours_summer", "domestic_power_hours_winter"):
                rec[field] = _to_float(raw_val)
            else:
                rec[field] = _to_int(raw_val)

        # status (Available/NotAvailable) -> boolean fields
        for canon_name, field in STATUS_MAP.items():
            src_col = lookup.get(canon_name)
            rec[field] = _status_to_bool(row[src_col]) if src_col else False

        # full original row, JSON-safe, for provenance
        raw_dict = {}
        for col in df.columns:
            raw_dict[str(col)] = _json_safe(row[col])
        rec["raw"] = raw_dict

        # district_name/village_name are NOT NULL on the model — guard against blanks
        if not rec.get("district_name"):
            rec["district_name"] = _to_str(row[district_col]) or "Bagalkot"
        if not rec.get("village_name"):
            rec["village_name"] = f"UNKNOWN-{village_code}"

        records.append(rec)

    if skipped_no_village_code:
        print(f"  [census_village_amenities] skipped {skipped_no_village_code} rows with no Village Code")

    if not records:
        print("  [census_village_amenities] no records to insert")
        return 0

    all_fields = [f for f in records[0] if f != "village_code"]
    chunk = 500
    for i in range(0, len(records), chunk):
        batch = records[i : i + chunk]
        stmt = insert(CensusVillageAmenities).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["village_code"],
            set_={f: getattr(stmt.excluded, f) for f in all_fields},
        )
        db.execute(stmt)
    db.commit()
    return len(records)


def run() -> None:
    with SessionLocal() as db:
        n = ingest(db)
        print(f"census_village_amenities: {n} rows upserted")


if __name__ == "__main__":
    run()
