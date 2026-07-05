import json
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.divergence import compute_village_divergence
from app.services.ranking import build_ranked_works

router = APIRouter(prefix="/boundary", tags=["boundary"])

BAGALKOT_PC_ID = 2903


@router.get("")
def get_boundary(db: Session = Depends(get_db)) -> dict:
    """GeoJSON for the map view: the Bagalkot PC polygon, plus one point feature per
    village that has a resolved location (88.2% of villages, per Phase 1 coverage --
    villages without a matched PMGSY habitation point have no marker, not a guessed one).
    Each village's `composite_score` is the MAX composite_score among its candidate works
    (i.e. "how urgent is this village's top issue"); divergence/silent_need come from
    Phase 3's need-vs-voice signal for the divergence overlay toggle.
    """
    pc_row = db.execute(
        text("SELECT pc_name, ST_AsGeoJSON(geom) AS geojson FROM pc_boundary WHERE pc_id = :id"),
        {"id": BAGALKOT_PC_ID},
    ).first()
    constituency_feature = None
    if pc_row:
        constituency_feature = {
            "type": "Feature",
            "geometry": json.loads(pc_row.geojson),
            "properties": {"pc_name": pc_row.pc_name},
        }

    village_geo = db.execute(
        text(
            "SELECT village_code, village_name, ST_AsGeoJSON(geom) AS geojson "
            "FROM village_fact WHERE geom IS NOT NULL"
        )
    ).all()

    works = build_ranked_works(db)
    best_score_by_village: dict[int, float] = defaultdict(float)
    for w in works:
        if w.village_code is not None:
            best_score_by_village[w.village_code] = max(best_score_by_village[w.village_code], w.composite_score)

    divergence = compute_village_divergence(db)

    village_features = []
    for row in village_geo:
        d = divergence.get(row.village_code)
        village_features.append(
            {
                "type": "Feature",
                "geometry": json.loads(row.geojson),
                "properties": {
                    "village_code": row.village_code,
                    "village_name": row.village_name,
                    "composite_score": round(best_score_by_village.get(row.village_code, 0.0), 4),
                    "gap_percentile": round(d.gap_percentile, 4) if d and d.gap_percentile is not None else None,
                    "voice_percentile": round(d.voice_percentile, 4) if d else None,
                    "divergence": round(d.divergence, 4) if d and d.divergence is not None else None,
                    "silent_need": d.silent_need if d else False,
                },
            }
        )

    return {
        "constituency": constituency_feature,
        "villages": {"type": "FeatureCollection", "features": village_features},
        "village_coverage_note": (
            f"{len(village_features)} of 627 Bagalkot villages have a map location "
            "(matched to a PMGSY habitation point) -- the rest have no confident location "
            "match and are omitted rather than plotted with a guessed position."
        ),
    }
