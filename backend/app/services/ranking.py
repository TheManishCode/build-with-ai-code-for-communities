"""Composite ranking engine (Phase 3).

A "candidate work" is either:
  - an Issue (clustered citizen submissions) — has both a demand signal and, when its
    theme has a fact-table proxy, a gap signal; or
  - a "silent need" gap-only candidate — a village/theme combination with NO citizen
    submissions at all, but whose objective gap percentile is above
    config.silent_need_gap_percentile. Demand signal is 0 by construction.

Every number in a generated reasoning string is read directly from the gap/demand data
structures built here — see tests/test_ranking.py, which asserts this by construction
(walking the same underlying values the string cites) rather than just eyeballing output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.ranking_config import RankingConfig, ranking_config
from app.services.demand import compute_issue_demand, village_voice_raw
from app.services.gap import THEMES_WITH_GAP_SIGNAL, VillageGap, compute_village_gaps


@dataclass
class CandidateWork:
    work_id: str
    source: str  # "issue" | "gap"
    theme: str
    village_code: int | None
    village_name: str | None
    representative_text: str
    corroboration_count: int
    demand_raw: float
    demand_percentile: float
    gap_percentile: float | None
    population_affected: int | None
    composite_score: float
    reasoning: str = field(default="")


def _percentile_rank_of(value: float, all_values: list[float]) -> float:
    if not all_values:
        return 0.0
    n = len(all_values)
    if n == 1:
        return 0.5
    rank = sum(1 for v in all_values if v < value)
    ties = sum(1 for v in all_values if v == value)
    # mid-rank for ties, matches the percentile convention used in app.services.gap
    return (rank + ties / 2.0) / (n - 1) if n > 1 else 0.5


def _raw_metric_clause(theme: str, gap: VillageGap, all_gaps: dict[int, VillageGap]) -> str:
    raw = gap.raw.get(theme)
    if raw is None:
        return f"no {theme} data recorded for this village"

    if theme == "water":
        if raw == 0.0:
            return "has a treated/safe drinking water source recorded"
        if raw == 1.0:
            return "no safe drinking water source recorded in the 2011 census amenities survey"
        return "has only a partial/untreated water source recorded (no treated tap water)"

    if theme == "road":
        return "no pucca road, all-weather road, or PMGSY road connectivity recorded" if raw == 1.0 else "has road connectivity recorded (pucca/all-weather/PMGSY)"

    if theme == "sanitation":
        if raw == 1.0:
            return "no drainage system recorded"
        if raw == 0.0:
            return "closed/covered drainage recorded"
        return "only open or unspecified drainage recorded"

    if theme in ("school", "health"):
        others = [g.raw[theme] for g in all_gaps.values() if g.raw.get(theme) is not None]
        median = sorted(others)[len(others) // 2] if others else None
        label = "population per school" if theme == "school" else "population per health facility"
        med_txt = f" (constituency median ~{median:.0f})" if median else ""
        return f"{raw:.0f} {label}{med_txt}"

    if theme == "electricity":
        hours = 24.0 - raw
        others = [24.0 - g.raw["electricity"] for g in all_gaps.values() if g.raw.get("electricity") is not None]
        med = sorted(others)[len(others) // 2] if others else None
        med_txt = f" (constituency median ~{med:.1f}h)" if med else ""
        return f"only {hours:.1f} average daily hours of power supply recorded{med_txt}"

    return f"gap percentile {gap.percentile.get(theme, 0):.0%}"


def _mplads_clause(village_code: int | None, mplads_by_village: dict[int, dict]) -> str:
    if village_code is None or village_code not in mplads_by_village:
        return "no completed MPLADs-funded work recorded for this village to date"
    m = mplads_by_village[village_code]
    if not m.get("completed_total"):
        return "no completed MPLADs-funded work recorded for this village to date"
    return f"₹{m['completed_total']:,} already spent on {m['completed_count']} completed MPLADs work(s) here"


def build_reasoning(
    source: str,
    theme: str,
    village_name: str | None,
    corroboration_count: int,
    demand_percentile: float,
    gap: VillageGap | None,
    all_gaps: dict[int, VillageGap],
    mplads_by_village: dict[int, dict],
    village_code: int | None,
    representative_text: str = "",
) -> str:
    mplads_clause = _mplads_clause(village_code, mplads_by_village)
    place = village_name or "an unresolved location"

    if source == "gap":
        gap_pct = gap.percentile.get(theme) if gap else None
        metric_clause = _raw_metric_clause(theme, gap, all_gaps) if gap else "no data recorded"
        gap_txt = f"{gap_pct:.0%}" if gap_pct is not None else "unknown"
        return (
            f"No citizen submissions recorded for {theme} in {place}, but it ranks in the "
            f"{gap_txt} percentile for {theme} gap in the constituency ({metric_clause}); {mplads_clause}."
        )

    metric_clause = _raw_metric_clause(theme, gap, all_gaps) if gap else "no fact-table gap signal available for this theme"
    quote = f' Representative report: "{representative_text.strip()}"' if representative_text else ""
    return (
        f"{corroboration_count} submission(s) about {theme} in {place} "
        f"(recency-weighted demand percentile {demand_percentile:.0%}); {metric_clause}; {mplads_clause}.{quote}"
    )


def _mplads_by_village(db: Session) -> dict[int, dict]:
    rows = db.execute(
        text("SELECT village_code, mplads_completed_amount_total, mplads_completed_work_count FROM village_fact")
    ).all()
    return {
        r.village_code: {"completed_total": r.mplads_completed_amount_total, "completed_count": r.mplads_completed_work_count}
        for r in rows
        if r.mplads_completed_amount_total or r.mplads_completed_work_count
    }


def build_ranked_works(db: Session, config: RankingConfig = ranking_config, now: datetime | None = None) -> list[CandidateWork]:
    now = now or datetime.utcnow()  # naive UTC, matching submission/issue timestamp columns
    gaps = compute_village_gaps(db, config.gap_sub_weights)
    mplads_by_village = _mplads_by_village(db)
    issue_demands = compute_issue_demand(db, config.recency_half_life_days, now)

    candidates: list[CandidateWork] = []

    # Issue-based candidates
    covered: set[tuple[int, str]] = set()
    for d in issue_demands:
        gap = gaps.get(d.village_code) if d.village_code else None
        gap_pct = gap.percentile.get(d.theme) if gap and d.theme in THEMES_WITH_GAP_SIGNAL else None
        candidates.append(
            CandidateWork(
                work_id=f"issue-{d.issue_id}",
                source="issue",
                theme=d.theme,
                village_code=d.village_code,
                village_name=gap.village_name if gap else None,
                representative_text=d.representative_text,
                corroboration_count=d.corroboration_count,
                demand_raw=d.demand_raw,
                demand_percentile=0.0,  # filled in below once we have the full pool
                gap_percentile=gap_pct,
                population_affected=gap.total_population if gap else None,
                composite_score=0.0,
            )
        )
        if d.village_code is not None:
            covered.add((d.village_code, d.theme))

    # Gap-only "silent need" candidates: village/theme combos with no issue at all, whose
    # gap percentile clears the configured threshold.
    for village_code, gap in gaps.items():
        for theme in THEMES_WITH_GAP_SIGNAL:
            if (village_code, theme) in covered:
                continue
            pct = gap.percentile.get(theme)
            if pct is not None and pct >= config.silent_need_gap_percentile:
                candidates.append(
                    CandidateWork(
                        work_id=f"gap-{village_code}-{theme}",
                        source="gap",
                        theme=theme,
                        village_code=village_code,
                        village_name=gap.village_name,
                        representative_text="",
                        corroboration_count=0,
                        demand_raw=0.0,
                        demand_percentile=0.0,
                        gap_percentile=pct,
                        population_affected=gap.total_population,
                        composite_score=0.0,
                    )
                )

    all_demand_raw = [c.demand_raw for c in candidates]
    for c in candidates:
        c.demand_percentile = _percentile_rank_of(c.demand_raw, all_demand_raw)
        gap_component = c.gap_percentile if c.gap_percentile is not None else 0.0
        c.composite_score = config.demand_weight * c.demand_percentile + config.gap_weight * gap_component
        gap_obj = gaps.get(c.village_code) if c.village_code else None
        c.reasoning = build_reasoning(
            c.source, c.theme, c.village_name, c.corroboration_count, c.demand_percentile,
            gap_obj, gaps, mplads_by_village, c.village_code,
            representative_text=c.representative_text,
        )

    # Tie-break: scores within tie_break_epsilon of each other are treated as equal, and
    # population_affected is the deciding factor among them. Bucketing the score by epsilon
    # (rather than always sorting by population as an unconditional secondary key) means
    # population only matters for genuine near-ties, not for meaningfully different scores.
    def sort_key(c: CandidateWork) -> tuple[float, int]:
        bucket = round(c.composite_score / config.tie_break_epsilon)
        return (bucket, c.population_affected or 0)

    candidates.sort(key=sort_key, reverse=True)
    return candidates
