"""Objective infrastructure-gap signal, computed from village_fact (Phase 3).

For each theme with a fact-table proxy (water/road/school/health/electricity/sanitation),
compute a RAW gap metric per village (higher = worse), then convert to a percentile rank
in [0, 1] across all Bagalkot villages with a non-null value for that metric (1.0 = worst
gap in the constituency, 0.0 = best). "other" has no objective proxy and is intentionally
excluded — see config/ranking_weights.yaml.

Percentiles are computed only among villages with real data for that metric — a village
missing a signal gets gap_percentile=None for that theme, not a fabricated 0 or 1.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

THEMES_WITH_GAP_SIGNAL = ("water", "road", "school", "health", "electricity", "sanitation")


@dataclass
class VillageGap:
    village_code: int
    village_name: str
    total_population: int | None
    raw: dict[str, float | None]  # theme -> raw gap metric (higher = worse)
    percentile: dict[str, float | None]  # theme -> percentile rank in [0,1] (higher = worse)
    overall_gap_percentile: float | None  # gap_sub_weights-weighted blend across themes


def _raw_water_gap(row) -> float | None:
    if row.has_safe_water_source is None and row.has_treated_tap_water is None:
        return None
    parts = []
    if row.has_safe_water_source is not None:
        parts.append(0.0 if row.has_safe_water_source else 1.0)
    if row.has_treated_tap_water is not None:
        parts.append(0.0 if row.has_treated_tap_water else 1.0)
    return sum(parts) / len(parts)


def _raw_road_gap(row) -> float | None:
    signals = [row.has_pucca_road, row.has_all_weather_road, row.pmgsy_connected]
    known = [s for s in signals if s is not None]
    if not known:
        return None
    return 0.0 if any(known) else 1.0


def _raw_school_gap(row) -> float | None:
    count = row.census_school_count or row.kys_school_count
    if not count or not row.total_population:
        return None
    return row.total_population / count


def _raw_health_gap(row) -> float | None:
    if not row.health_facility_count or not row.total_population:
        return None
    return row.total_population / row.health_facility_count


def _raw_electricity_gap(row) -> float | None:
    hours = [h for h in (row.domestic_power_hours_summer, row.domestic_power_hours_winter) if h is not None]
    if not hours:
        return None
    return 24.0 - (sum(hours) / len(hours))


def _raw_sanitation_gap(row) -> float | None:
    if row.has_no_drainage is None and row.has_closed_drainage is None:
        return None
    if row.has_no_drainage:
        return 1.0
    if row.has_closed_drainage:
        return 0.0
    return 0.5  # some drainage exists but not the closed/covered kind


RAW_GAP_FUNCS = {
    "water": _raw_water_gap,
    "road": _raw_road_gap,
    "school": _raw_school_gap,
    "health": _raw_health_gap,
    "electricity": _raw_electricity_gap,
    "sanitation": _raw_sanitation_gap,
}


def _percentile_ranks(values: dict[int, float]) -> dict[int, float]:
    """village_code -> percentile rank in [0,1], higher raw value = higher percentile."""
    if not values:
        return {}
    codes = list(values.keys())
    arr = np.array([values[c] for c in codes])
    order = np.argsort(np.argsort(arr))  # rank, ties get distinct ranks (stable enough for this scale)
    n = len(arr)
    return {code: float(order[i]) / (n - 1) if n > 1 else 0.5 for i, code in enumerate(codes)}


def compute_village_gaps(db: Session, gap_sub_weights: dict[str, float]) -> dict[int, VillageGap]:
    rows = db.execute(
        text(
            """
            SELECT village_code, village_name, total_population, census_school_count, kys_school_count,
                   health_facility_count, has_safe_water_source, has_treated_tap_water,
                   has_pucca_road, has_all_weather_road, pmgsy_connected,
                   domestic_power_hours_summer, domestic_power_hours_winter,
                   has_closed_drainage, has_no_drainage
            FROM village_fact
            """
        )
    ).all()

    raw_by_theme: dict[str, dict[int, float]] = {theme: {} for theme in THEMES_WITH_GAP_SIGNAL}
    for row in rows:
        for theme, func in RAW_GAP_FUNCS.items():
            val = func(row)
            if val is not None:
                raw_by_theme[theme][row.village_code] = val

    percentile_by_theme = {theme: _percentile_ranks(vals) for theme, vals in raw_by_theme.items()}

    gaps: dict[int, VillageGap] = {}
    for row in rows:
        raw = {theme: raw_by_theme[theme].get(row.village_code) for theme in THEMES_WITH_GAP_SIGNAL}
        pct = {theme: percentile_by_theme[theme].get(row.village_code) for theme in THEMES_WITH_GAP_SIGNAL}

        weighted_sum, weight_total = 0.0, 0.0
        for theme, w in gap_sub_weights.items():
            p = pct.get(theme)
            if p is not None:
                weighted_sum += w * p
                weight_total += w
        overall = weighted_sum / weight_total if weight_total > 0 else None

        gaps[row.village_code] = VillageGap(
            village_code=row.village_code,
            village_name=row.village_name,
            total_population=row.total_population,
            raw=raw,
            percentile=pct,
            overall_gap_percentile=overall,
        )
    return gaps
