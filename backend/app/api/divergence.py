from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.divergence import compute_village_divergence

router = APIRouter(prefix="/divergence", tags=["divergence"])


@router.get("")
def list_divergence(db: Session = Depends(get_db)) -> list[dict]:
    """Need-vs-voice divergence per village -- first-class field per the project brief,
    not folded silently into /villages. Sorted by divergence descending so 'silent need'
    villages (high gap, near-zero citizen voice) surface first."""
    result = compute_village_divergence(db)
    rows = sorted(result.values(), key=lambda v: (v.divergence if v.divergence is not None else -1), reverse=True)
    return [
        {
            "village_code": v.village_code,
            "village_name": v.village_name,
            "gap_percentile": round(v.gap_percentile, 4) if v.gap_percentile is not None else None,
            "voice_percentile": round(v.voice_percentile, 4),
            "divergence": round(v.divergence, 4) if v.divergence is not None else None,
            "silent_need": v.silent_need,
        }
        for v in rows
    ]
