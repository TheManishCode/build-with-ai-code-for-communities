"""Real tests for the knapsack budget allocator -- verify the optimization is actually
correct (budget constraint respected, value-maximizing, deterministic), not just that it
returns something plausible-looking."""

from app.core.ranking_config import ranking_config
from app.services.allocator import knapsack_allocate
from app.services.ranking import CandidateWork


def _work(work_id, theme, score, village_code=1):
    return CandidateWork(
        work_id=work_id, source="issue", theme=theme, village_code=village_code, village_name="X",
        representative_text="", corroboration_count=1, demand_raw=1.0, demand_percentile=1.0,
        gap_percentile=0.5, population_affected=100, composite_score=score,
    )


def test_never_exceeds_budget():
    items = [_work(f"w{i}", "water", score=0.1 * i) for i in range(1, 20)]
    result = knapsack_allocate(items, budget=2_000_000, cost_heuristic={"water": 500_000})
    assert result.total_cost <= 2_000_000


def test_picks_optimal_value_small_case():
    """Hand-verifiable case: 3 items, only 2 fit by cost, DP must pick the higher-value pair."""
    items = [
        _work("a", "water", score=0.9),  # cost 500k
        _work("b", "sanitation", score=0.5),  # cost 400k
        _work("c", "school", score=0.4),  # cost 1,000,000 -- too expensive to combine with both
    ]
    cost_heuristic = {"water": 500_000, "sanitation": 400_000, "school": 1_000_000}
    result = knapsack_allocate(items, budget=900_000, cost_heuristic=cost_heuristic)
    selected_ids = {it.work.work_id for it in result.selected}
    # a+b = 900k, value 1.4; c alone = 1,000,000 > budget. a+b is the only valid combo using both.
    assert selected_ids == {"a", "b"}
    assert result.total_value == 0.9 + 0.5
    assert result.total_cost == 900_000


def test_zero_budget_selects_nothing():
    items = [_work("a", "water", score=0.9)]
    result = knapsack_allocate(items, budget=0, cost_heuristic={"water": 500_000})
    assert result.selected == []
    assert result.total_cost == 0


def test_unaffordable_single_item_excluded():
    items = [_work("a", "school", score=0.9)]  # costs 1,000,000
    result = knapsack_allocate(items, budget=500_000, cost_heuristic={"school": 1_000_000})
    assert result.selected == []


def test_items_with_no_cost_heuristic_entry_are_excluded_not_free():
    items = [_work("a", "mystery_theme", score=0.9)]
    result = knapsack_allocate(items, budget=10_000_000, cost_heuristic={"water": 500_000})
    assert result.selected == []
    assert result.n_candidates_considered == 0


def test_real_bagalkot_allocation_uses_real_ranked_works(db):
    from app.services.allocator import run_allocation

    result = run_allocation(db, budget=167_541_747)  # Bagalkot's real 18th-LS allocated limit
    assert result.total_cost <= 167_541_747
    assert len(result.selected) > 0
    # every selected item's cost must match the configured heuristic for its theme exactly
    for it in result.selected:
        assert it.cost == ranking_config.theme_cost_heuristic[it.work.theme]
    # value should be non-decreasing as budget increases (monotonicity sanity check)
    smaller = run_allocation(db, budget=50_000_000)
    assert result.total_value >= smaller.total_value


def test_run_allocation_with_precomputed_candidates_matches_recomputing_them(db):
    """Callers that already have build_ranked_works(db) can pass it in via candidates= to
    avoid a redundant second full rebuild in the same request (used by /works/{id}/explain,
    /citizen/status, /transparency/summary). The result must be identical either way --
    this isn't just a perf optimization, it must be behavior-preserving."""
    from app.services.allocator import run_allocation
    from app.services.ranking import build_ranked_works

    budget = 167_541_747
    precomputed = build_ranked_works(db)
    result_with_candidates = run_allocation(db, budget, candidates=precomputed)
    result_recomputed = run_allocation(db, budget)

    assert result_with_candidates.total_cost == result_recomputed.total_cost
    assert result_with_candidates.total_value == result_recomputed.total_value
    assert {it.work.work_id for it in result_with_candidates.selected} == {
        it.work.work_id for it in result_recomputed.selected
    }
