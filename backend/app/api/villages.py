from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import VillageFact

router = APIRouter(prefix="/villages", tags=["villages"])


@router.get("")
def list_villages(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(VillageFact)).scalars().all()
    return [
        {
            "village_code": r.village_code,
            "village_name": r.village_name,
            "subdistrict_name": r.subdistrict_name,
            "gram_panchayat_name": r.gram_panchayat_name,
            "total_population": r.total_population,
            "literacy_rate": r.literacy_rate,
            "has_safe_water_source": r.has_safe_water_source,
            "has_all_weather_road": r.has_all_weather_road,
            "pmgsy_connected": r.pmgsy_connected,
            "census_school_count": r.census_school_count,
            "kys_school_count": r.kys_school_count,
        }
        for r in rows
    ]
