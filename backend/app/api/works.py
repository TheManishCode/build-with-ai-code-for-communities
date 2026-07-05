from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.ranking_config import ranking_config
from app.services.letter import generate_draft_letter
from app.services.ranking import build_ranked_works

router = APIRouter(prefix="/works", tags=["works"])


def _current_mp_name(db: Session) -> str:
    row = db.execute(
        text("SELECT mp_name FROM mplads_allocated_limit WHERE lok_sabha_term='18th' ORDER BY id LIMIT 1")
    ).first()
    return row.mp_name if row else "Member of Parliament"


@router.get("")
def list_ranked_works(db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=500)) -> list[dict]:
    works = build_ranked_works(db)
    return [
        {
            "work_id": w.work_id,
            "source": w.source,
            "theme": w.theme,
            "village_code": w.village_code,
            "village_name": w.village_name,
            "corroboration_count": w.corroboration_count,
            "demand_percentile": round(w.demand_percentile, 4),
            "gap_percentile": round(w.gap_percentile, 4) if w.gap_percentile is not None else None,
            "population_affected": w.population_affected,
            "composite_score": round(w.composite_score, 4),
            "reasoning": w.reasoning,
        }
        for w in works[:limit]
    ]


@router.get("/{work_id}/letter")
def get_draft_letter(work_id: str, db: Session = Depends(get_db)) -> dict:
    works = build_ranked_works(db)
    work = next((w for w in works if w.work_id == work_id), None)
    if work is None:
        raise HTTPException(status_code=404, detail=f"work_id {work_id!r} not found in current ranking")

    mp_name = _current_mp_name(db)
    from app.core.config import settings

    cost_estimate = ranking_config.theme_cost_heuristic.get(work.theme)
    letter = generate_draft_letter(work, mp_name, settings.constituency_name, cost_estimate)
    return {"work_id": work_id, **letter}
