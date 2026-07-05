from pathlib import Path

import yaml
from pydantic import BaseModel

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "ranking_weights.yaml"


class RankingConfig(BaseModel):
    demand_weight: float
    gap_weight: float
    recency_half_life_days: float
    gap_sub_weights: dict[str, float]
    tie_break_epsilon: float
    theme_cost_heuristic: dict[str, int]
    silent_need_gap_percentile: float


def load_ranking_config(path: Path = CONFIG_PATH) -> RankingConfig:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return RankingConfig(**data)


ranking_config = load_ranking_config()
