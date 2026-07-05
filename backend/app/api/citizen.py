from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.citizen_status import get_citizen_status

router = APIRouter(prefix="/citizen", tags=["citizen"])


def _default_mplads_budget(db: Session) -> int:
    """Duplicated from app.api.allocation._default_budget rather than imported -- see the
    same note in app.api.works._default_mplads_budget (Phase 8)."""
    row = db.execute(
        text("SELECT allocated_amount FROM mplads_allocated_limit WHERE lok_sabha_term = '18th' ORDER BY id LIMIT 1")
    ).first()
    return int(row.allocated_amount) if row else 0


@router.get("/status")
def get_status(
    submission_id: int = Query(...), db: Session = Depends(get_db), budget: int | None = Query(None, ge=0)
) -> dict:
    effective_budget = budget if budget is not None else _default_mplads_budget(db)
    status = get_citizen_status(db, submission_id, effective_budget)
    if not status.found:
        raise HTTPException(status_code=404, detail=f"No submission found with id {submission_id}")
    return {
        "submission_id": status.submission_id,
        "village": status.village,
        "taluk": status.taluk,
        "theme": status.theme,
        "dedup_group_id": status.dedup_group_id,
        "corroboration_count": status.corroboration_count,
        "current_rank": status.current_rank,
        "total_works_ranked": status.total_works_ranked,
        "is_funded_this_cycle": status.is_funded_this_cycle,
        "funding_tier": status.funding_tier,
        "status_message": status.status_message,
    }
