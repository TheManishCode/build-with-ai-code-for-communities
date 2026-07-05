"""Phase 5: budget allocator. Solves a 0/1 knapsack over ranked candidate works --
maximize total composite_score subject to sum(cost) <= budget -- using a flat per-theme
cost heuristic (config/ranking_weights.yaml theme_cost_heuristic) since no real per-work
cost estimate exists in any source dataset. This heuristic is stated explicitly here and
in every API response, not hidden inside a black-box number.

DP is done in units of Rs. 1,00,000 (1 lakh) rather than raw rupees -- all heuristic costs
are exact multiples of 1 lakh, so this is a lossless rescaling that keeps the DP table
(items x budget_units) a few hundred thousand cells instead of hundreds of millions.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.ranking_config import RankingConfig, ranking_config
from app.services.ranking import CandidateWork, build_ranked_works

COST_UNIT = 100_000  # Rs. 1 lakh


@dataclass
class AllocationItem:
    work: CandidateWork
    cost: int


@dataclass
class AllocationResult:
    budget: int
    selected: list[AllocationItem]
    total_cost: int
    total_value: float
    budget_used_pct: float
    n_candidates_considered: int


def _cost_for(work: CandidateWork, cost_heuristic: dict[str, int]) -> int | None:
    return cost_heuristic.get(work.theme)


def knapsack_allocate(
    candidates: list[CandidateWork], budget: int, cost_heuristic: dict[str, int]
) -> AllocationResult:
    items: list[AllocationItem] = []
    for w in candidates:
        cost = _cost_for(w, cost_heuristic)
        if cost is None:
            continue  # theme has no cost heuristic entry -- can't be costed, can't be allocated
        items.append(AllocationItem(work=w, cost=cost))

    budget_units = budget // COST_UNIT
    n = len(items)

    # dp[i][b] = best total value using a subset of the first i items with total cost <= b
    # (units of COST_UNIT). keep[i][b] = whether item i-1 was taken to reach dp[i][b].
    dp = [[0.0] * (budget_units + 1) for _ in range(n + 1)]
    keep = [[False] * (budget_units + 1) for _ in range(n + 1)]

    for i, item in enumerate(items, start=1):
        cost_units = item.cost // COST_UNIT
        value = item.work.composite_score
        for b in range(budget_units + 1):
            without = dp[i - 1][b]
            if cost_units <= b:
                with_item = dp[i - 1][b - cost_units] + value
                if with_item > without:
                    dp[i][b] = with_item
                    keep[i][b] = True
                    continue
            dp[i][b] = without

    # backtrack
    selected: list[AllocationItem] = []
    b = budget_units
    for i in range(n, 0, -1):
        if keep[i][b]:
            item = items[i - 1]
            selected.append(item)
            b -= item.cost // COST_UNIT

    selected.reverse()
    total_cost = sum(it.cost for it in selected)
    total_value = sum(it.work.composite_score for it in selected)

    return AllocationResult(
        budget=budget,
        selected=selected,
        total_cost=total_cost,
        total_value=total_value,
        budget_used_pct=(total_cost / budget) if budget else 0.0,
        n_candidates_considered=n,
    )


def run_allocation(db: Session, budget: int, config: RankingConfig = ranking_config) -> AllocationResult:
    candidates = build_ranked_works(db)
    return knapsack_allocate(candidates, budget, config.theme_cost_heuristic)
