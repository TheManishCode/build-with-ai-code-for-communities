from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.transparency import build_transparency_summary

router = APIRouter(prefix="/transparency", tags=["transparency"])


@router.get("/summary")
def get_transparency_summary(db: Session = Depends(get_db), budget: int | None = Query(None, ge=0)) -> dict:
    """Public-facing constituency summary -- pure aggregation over already-tested
    services (build_ranked_works, run_allocation, run_backtest, compute_village_divergence),
    no new scoring logic."""
    s = build_transparency_summary(db, budget)
    return {
        "total_submissions": s.total_submissions,
        "total_issues": s.total_issues,
        "dedup_rate": round(s.dedup_rate, 4),
        "theme_breakdown": s.theme_breakdown,
        "total_villages": s.total_villages,
        "villages_with_submissions": s.villages_with_submissions,
        "voice_coverage_pct": round(s.voice_coverage_pct, 4),
        "silent_need_village_count": s.silent_need_village_count,
        "total_candidate_works": s.total_candidate_works,
        "issue_based_works": s.issue_based_works,
        "gap_only_works": s.gap_only_works,
        "budget": s.budget,
        "works_funded": s.works_funded,
        "budget_used_pct": round(s.budget_used_pct, 4),
        "backtest_ground_truth_villages": s.backtest_ground_truth_villages,
        "backtest_precision_at_100": round(s.backtest_precision_at_100, 4) if s.backtest_precision_at_100 is not None else None,
        "backtest_never_addressed_count": s.backtest_never_addressed_count,
    }
