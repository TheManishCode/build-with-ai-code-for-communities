"""Citizen-voice (demand) signal, recency-weighted."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class IssueDemand:
    issue_id: int
    theme: str
    village_code: int | None
    representative_text: str
    corroboration_count: int
    last_seen_at: datetime
    demand_raw: float  # recency-weighted corroboration count


def recency_weight(last_seen_at: datetime, now: datetime, half_life_days: float) -> float:
    age_days = max((now - last_seen_at).total_seconds() / 86400.0, 0.0)
    return 0.5 ** (age_days / half_life_days)


def compute_issue_demand(db: Session, half_life_days: float, now: datetime) -> list[IssueDemand]:
    rows = db.execute(
        text(
            """
            SELECT id, theme, village_code, representative_text, corroboration_count, last_seen_at
            FROM issue
            """
        )
    ).all()
    out = []
    for r in rows:
        w = recency_weight(r.last_seen_at, now, half_life_days)
        out.append(
            IssueDemand(
                issue_id=r.id,
                theme=r.theme,
                village_code=r.village_code,
                representative_text=r.representative_text,
                corroboration_count=r.corroboration_count,
                last_seen_at=r.last_seen_at,
                demand_raw=r.corroboration_count * w,
            )
        )
    return out


def village_voice_raw(issue_demands: list[IssueDemand], all_village_codes: list[int]) -> dict[int, float]:
    """Sum of recency-weighted corroboration across ALL themes, per village. Villages with
    no issues get 0.0 explicitly (not omitted) so they participate in the percentile rank
    used by the need-vs-voice divergence calculation."""
    totals: dict[int, float] = {code: 0.0 for code in all_village_codes}
    for d in issue_demands:
        if d.village_code is not None and d.village_code in totals:
            totals[d.village_code] += d.demand_raw
    return totals
