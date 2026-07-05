"""Real tests for the Phase 4 MPLADs backtest -- verifying the precision/recall
ARITHMETIC is correct, not that the resulting numbers look impressive. See
app/services/backtest.py's module docstring for the methodology and disclosed caveats.
"""

from sqlalchemy import text

from app.services.backtest import _ground_truth_villages, run_backtest


def test_ground_truth_matches_raw_query(db):
    """Sanity-check the helper against a hand-written equivalent query."""
    villages = _ground_truth_villages(db, "17th")
    expected = db.execute(
        text(
            """
            SELECT DISTINCT matched_lgd_village_code FROM mplads_work
            WHERE lok_sabha_term='17th' AND completed_amount IS NOT NULL
              AND matched_lgd_village_code IS NOT NULL
            """
        )
    ).all()
    assert villages == {r.matched_lgd_village_code for r in expected}
    assert len(villages) > 0


def test_precision_recall_arithmetic(db):
    result = run_backtest(db)
    assert result.total_villages > 0
    assert result.ground_truth_villages > 0

    for c in result.cutoffs:
        # true_positives can never exceed either the cutoff size or the total ground truth
        assert 0 <= c.true_positives <= min(c.k, result.ground_truth_villages)
        assert c.precision == c.true_positives / c.k
        assert c.recall == c.true_positives / result.ground_truth_villages
        assert 0.0 <= c.precision <= 1.0
        assert 0.0 <= c.recall <= 1.0
        # random baseline must equal ground_truth/total exactly, not an approximation
        assert c.random_baseline_precision == result.ground_truth_villages / result.total_villages


def test_recall_is_monotonically_non_decreasing_with_k(db):
    result = run_backtest(db)
    recalls = [(c.k, c.recall) for c in result.cutoffs]
    recalls.sort()
    for i in range(1, len(recalls)):
        assert recalls[i][1] >= recalls[i - 1][1] - 1e-9, "recall must not decrease as K grows"


def test_never_addressed_villages_are_genuinely_unfunded_and_high_gap(db):
    result = run_backtest(db)
    assert len(result.never_addressed) > 0, "expect at least some high-gap villages to have no MPLADs history"

    funded_any = {
        r.matched_lgd_village_code
        for r in db.execute(
            text(
                "SELECT DISTINCT matched_lgd_village_code FROM mplads_work "
                "WHERE completed_amount IS NOT NULL AND matched_lgd_village_code IS NOT NULL"
            )
        ).all()
    }
    for v in result.never_addressed:
        assert v["village_code"] not in funded_any
        assert v["overall_gap_percentile"] >= 0.75  # matches config.silent_need_gap_percentile
