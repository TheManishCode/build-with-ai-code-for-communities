from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.ranking import build_ranked_works

router = APIRouter(prefix="/works", tags=["works"])


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
