from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.submission import Issue

router = APIRouter(prefix="/issues", tags=["issues"])


@router.get("")
def list_issues(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(Issue).order_by(Issue.corroboration_count.desc())).scalars().all()
    return [
        {
            "id": i.id,
            "theme": i.theme.value,
            "village_code": i.village_code,
            "representative_text": i.representative_text,
            "corroboration_count": i.corroboration_count,
        }
        for i in rows
    ]
