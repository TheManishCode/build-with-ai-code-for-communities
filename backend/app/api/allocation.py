from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.ranking_config import ranking_config
from app.services.allocator import run_allocation

router = APIRouter(prefix="/allocation", tags=["allocation"])


def _default_budget(db: Session) -> int:
    row = db.execute(
        text(
            "SELECT allocated_amount FROM mplads_allocated_limit "
            "WHERE lok_sabha_term = '18th' ORDER BY id LIMIT 1"
        )
    ).first()
    return int(row.allocated_amount) if row else 0


@router.get("")
def get_allocation(db: Session = Depends(get_db), budget: int | None = Query(None, ge=0)) -> dict:
    """Budget slider endpoint: pass ?budget=<rupees> to simulate a different MPLADs limit.
    Defaults to Bagalkot's real current (18th Lok Sabha) allocated limit."""
    effective_budget = budget if budget is not None else _default_budget(db)
    result = run_allocation(db, effective_budget)
    return {
        "budget": result.budget,
        "is_default_budget": budget is None,
        "total_cost": result.total_cost,
        "budget_used_pct": round(result.budget_used_pct, 4),
        "total_value": round(result.total_value, 4),
        "n_works_selected": len(result.selected),
        "n_candidates_considered": result.n_candidates_considered,
        "cost_heuristic_note": (
            "Per-work costs are a flat per-theme heuristic (config/ranking_weights.yaml "
            "theme_cost_heuristic) since no real per-work cost estimate exists in any "
            "source dataset -- these are rough MPLADs-scale planning figures, not "
            "engineering estimates."
        ),
        "theme_cost_heuristic": ranking_config.theme_cost_heuristic,
        "selected_works": [
            {
                "work_id": it.work.work_id,
                "source": it.work.source,
                "theme": it.work.theme,
                "village_code": it.work.village_code,
                "village_name": it.work.village_name,
                "cost": it.cost,
                "composite_score": round(it.work.composite_score, 4),
                "reasoning": it.work.reasoning,
            }
            for it in result.selected
        ],
    }
