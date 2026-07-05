"""Need-vs-voice divergence per village. Surfaces villages with high gap but near-zero
voice as a distinct "silent need" category in the API response -- a first-class field,
not an afterthought.

divergence = objective_gap_percentile - citizen_voice_percentile, both in [0, 1] computed
across all 627 Bagalkot villages. A village with high gap and near-zero voice gets a large
positive divergence and is flagged silent_need=True.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.ranking_config import RankingConfig, ranking_config
from app.services.demand import compute_issue_demand, village_voice_raw
from app.services.gap import compute_village_gaps

SILENT_NEED_VOICE_PERCENTILE_MAX = 0.10  # "near-zero voice"


@dataclass
class VillageDivergence:
    village_code: int
    village_name: str
    gap_percentile: float | None
    voice_percentile: float
    divergence: float | None  # gap_percentile - voice_percentile
    silent_need: bool


def _percentile_ranks(values: dict[int, float]) -> dict[int, float]:
    if not values:
        return {}
    import numpy as np

    codes = list(values.keys())
    arr = np.array([values[c] for c in codes])
    order = np.argsort(np.argsort(arr))
    n = len(arr)
    return {code: float(order[i]) / (n - 1) if n > 1 else 0.5 for i, code in enumerate(codes)}


def compute_village_divergence(
    db: Session, config: RankingConfig = ranking_config, now: datetime | None = None
) -> dict[int, VillageDivergence]:
    now = now or datetime.utcnow()  # naive UTC, matching submission/issue timestamp columns
    gaps = compute_village_gaps(db, config.gap_sub_weights)
    all_codes = list(gaps.keys())

    issue_demands = compute_issue_demand(db, config.recency_half_life_days, now)
    voice_raw = village_voice_raw(issue_demands, all_codes)
    voice_pct = _percentile_ranks(voice_raw)

    out: dict[int, VillageDivergence] = {}
    for code in all_codes:
        gap = gaps[code]
        vpct = voice_pct.get(code, 0.0)
        gpct = gap.overall_gap_percentile
        divergence = (gpct - vpct) if gpct is not None else None
        silent_need = bool(
            gpct is not None
            and gpct >= config.silent_need_gap_percentile
            and vpct <= SILENT_NEED_VOICE_PERCENTILE_MAX
        )
        out[code] = VillageDivergence(
            village_code=code,
            village_name=gap.village_name,
            gap_percentile=gpct,
            voice_percentile=vpct,
            divergence=divergence,
            silent_need=silent_need,
        )
    return out
