"""A public-facing constituency transparency summary -- a capstone tying the rest of the
platform together into one "what has this system actually done" view.

Pure aggregation over already-tested services -- no new scoring logic, no LLM calls, no
schema changes. Every number is read directly from the DB or from the same
build_ranked_works/run_allocation/run_backtest/compute_village_divergence functions
already verified elsewhere in this project, not re-derived.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.allocator import run_allocation
from app.services.backtest import run_backtest
from app.services.divergence import compute_village_divergence
from app.services.ranking import build_ranked_works


@dataclass
class TransparencySummary:
    total_submissions: int
    total_issues: int
    dedup_rate: float
    theme_breakdown: dict[str, int]
    total_villages: int
    villages_with_submissions: int
    voice_coverage_pct: float
    silent_need_village_count: int
    total_candidate_works: int
    issue_based_works: int
    gap_only_works: int
    budget: int
    works_funded: int
    budget_used_pct: float
    backtest_ground_truth_villages: int
    backtest_precision_at_100: float | None
    backtest_never_addressed_count: int


def _theme_breakdown(db: Session) -> dict[str, int]:
    rows = db.execute(text("SELECT theme, count(*) AS n FROM issue GROUP BY theme ORDER BY n DESC")).all()
    return {r.theme: r.n for r in rows}


def _default_budget(db: Session) -> int:
    row = db.execute(
        text("SELECT allocated_amount FROM mplads_allocated_limit WHERE lok_sabha_term = '18th' ORDER BY id LIMIT 1")
    ).first()
    return int(row.allocated_amount) if row else 0


def build_transparency_summary(db: Session, budget: int | None = None) -> TransparencySummary:
    total_submissions = db.execute(text("SELECT count(*) FROM submission")).scalar_one()
    total_issues = db.execute(text("SELECT count(*) FROM issue")).scalar_one()
    dedup_rate = (1 - total_issues / total_submissions) if total_submissions else 0.0

    villages_with_submissions = db.execute(
        text("SELECT count(DISTINCT resolved_lgd_code) FROM submission WHERE resolved_lgd_code IS NOT NULL")
    ).scalar_one()
    total_villages = db.execute(text("SELECT count(*) FROM village_fact")).scalar_one()
    voice_coverage_pct = (villages_with_submissions / total_villages) if total_villages else 0.0

    divergence = compute_village_divergence(db)
    silent_need_count = sum(1 for v in divergence.values() if v.silent_need)

    works = build_ranked_works(db)
    issue_based = sum(1 for w in works if w.source == "issue")
    gap_only = sum(1 for w in works if w.source == "gap")

    effective_budget = budget if budget is not None else _default_budget(db)
    allocation = run_allocation(db, effective_budget, candidates=works)

    backtest = run_backtest(db)
    precision_100 = next((c.precision for c in backtest.cutoffs if c.k == 100), None)

    return TransparencySummary(
        total_submissions=total_submissions,
        total_issues=total_issues,
        dedup_rate=dedup_rate,
        theme_breakdown=_theme_breakdown(db),
        total_villages=total_villages,
        villages_with_submissions=villages_with_submissions,
        voice_coverage_pct=voice_coverage_pct,
        silent_need_village_count=silent_need_count,
        total_candidate_works=len(works),
        issue_based_works=issue_based,
        gap_only_works=gap_only,
        budget=effective_budget,
        works_funded=len(allocation.selected),
        budget_used_pct=allocation.budget_used_pct,
        backtest_ground_truth_villages=backtest.ground_truth_villages,
        backtest_precision_at_100=precision_100,
        backtest_never_addressed_count=len(backtest.never_addressed),
    )
