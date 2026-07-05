"""Real tests for the ranking engine's reasoning-string generator and composite scorer --
per the project's non-negotiable, these check that generated strings actually trace to
real queried values, not just that a template renders without error.

Requires the live peoples_priorities DB (same one ingestion writes to) -- no separate test
fixture DB was set up for this hackathon-scope project; these are read-only queries.
"""

import re

import pytest

from app.core.ranking_config import ranking_config
from app.services.divergence import compute_village_divergence
from app.services.gap import THEMES_WITH_GAP_SIGNAL, compute_village_gaps
from app.services.ranking import _compute_theme_medians, build_ranked_works


@pytest.fixture(scope="module")
def works(db):
    return build_ranked_works(db)


@pytest.fixture(scope="module")
def gaps(db):
    return compute_village_gaps(db, ranking_config.gap_sub_weights)


def test_gap_percentiles_are_bounded(gaps):
    for gap in gaps.values():
        for theme in THEMES_WITH_GAP_SIGNAL:
            pct = gap.percentile.get(theme)
            if pct is not None:
                assert 0.0 <= pct <= 1.0
        if gap.overall_gap_percentile is not None:
            assert 0.0 <= gap.overall_gap_percentile <= 1.0


def test_worse_raw_metric_has_higher_or_equal_percentile(gaps):
    """A village with NO safe water source must not rank at a lower gap-percentile than
    one that has a safe water source (the whole point of the signal)."""
    with_water = [g for g in gaps.values() if g.raw.get("water") == 0.0]
    without_water = [g for g in gaps.values() if g.raw.get("water") == 1.0]
    assert with_water and without_water, "test needs both cases present in real data"

    avg_pct_with = sum(g.percentile["water"] for g in with_water) / len(with_water)
    avg_pct_without = sum(g.percentile["water"] for g in without_water) / len(without_water)
    assert avg_pct_without > avg_pct_with


def test_composite_score_matches_formula(works):
    assert works, "no candidate works produced -- check that seed_submissions/build_issues ran"
    sample = works[:15] + works[len(works) // 2 : len(works) // 2 + 5]
    for w in sample:
        gap_component = w.gap_percentile if w.gap_percentile is not None else 0.0
        expected = ranking_config.demand_weight * w.demand_percentile + ranking_config.gap_weight * gap_component
        assert w.composite_score == pytest.approx(expected, abs=1e-9)


def test_reasoning_corroboration_count_matches(works):
    """The reasoning string's cited submission count must equal the work's real
    corroboration_count field -- not a hallucinated or template-default number."""
    issue_works = [w for w in works if w.source == "issue"]
    assert issue_works
    for w in issue_works[:20]:
        m = re.search(r"^(\d+) submission\(s\)", w.reasoning)
        assert m, f"reasoning string missing submission-count clause: {w.reasoning!r}"
        assert int(m.group(1)) == w.corroboration_count


def test_reasoning_demand_percentile_matches(works):
    issue_works = [w for w in works if w.source == "issue"]
    for w in issue_works[:20]:
        m = re.search(r"demand percentile (\d+)%", w.reasoning)
        assert m
        cited_pct = int(m.group(1)) / 100.0
        assert abs(cited_pct - w.demand_percentile) < 0.01  # rounding to whole percent


def test_reasoning_school_health_ratio_matches_raw_gap(works, gaps):
    """For school/health themed works, the population-per-facility number cited in the
    reasoning string must equal the actual raw gap metric computed from village_fact --
    this is the crux of "no hallucinated numbers"."""
    checked = 0
    for w in works:
        if w.theme not in ("school", "health") or w.village_code is None:
            continue
        gap = gaps.get(w.village_code)
        raw = gap.raw.get(w.theme) if gap else None
        if raw is None:
            continue
        m = re.search(r"(\d+) population per (school|health facility)", w.reasoning)
        assert m, f"expected a population-per-facility clause in: {w.reasoning!r}"
        assert int(m.group(1)) == round(raw)
        checked += 1
    assert checked > 0, "no school/health works with a raw gap metric were found to check"


def test_reasoning_mplads_amount_matches_village_fact(db, works):
    row_by_village = {
        r.village_code: r.mplads_completed_amount_total
        for r in db.execute(
            __import__("sqlalchemy").text("SELECT village_code, mplads_completed_amount_total FROM village_fact")
        ).all()
    }
    checked = 0
    for w in works:
        if w.village_code is None:
            continue
        amount = row_by_village.get(w.village_code)
        if not amount:
            assert "no completed MPLADs-funded work recorded" in w.reasoning
            continue
        m = re.search(r"₹([\d,]+) already spent", w.reasoning)
        assert m, f"expected an MPLADs amount clause since village_fact has {amount}: {w.reasoning!r}"
        cited = int(m.group(1).replace(",", ""))
        assert cited == amount
        checked += 1
    assert checked > 0, "no works with an actual MPLADs amount were found to check"


def test_electricity_gap_is_mostly_unavailable_not_fabricated(gaps):
    """Documents a real source-data limitation (see app/services/gap.py
    _raw_electricity_gap docstring): the census 'Power Supply For Domestic Use' column is
    filled for essentially 1 of 624 Bagalkot villages. This asserts the code's correct
    response -- returning None for the vast majority rather than defaulting blank-to-0-hours
    (which would fabricate a maximal false gap) or blank-to-24-hours (which would fabricate
    a false non-gap). If this ever starts returning real values for most villages, the
    source data has improved and this test (and the docstring) should be revisited."""
    non_null = sum(1 for g in gaps.values() if g.raw.get("electricity") is not None)
    assert non_null <= 5, (
        f"expected electricity gap data to be present for ~1 village (known source-data "
        f"gap), found {non_null} -- if the source file was updated, update the docstring "
        f"in app/services/gap.py::_raw_electricity_gap and this test's threshold"
    )


def test_theme_medians_computed_once_match_per_candidate_recomputation(gaps):
    """Efficiency fix (code-quality audit): the school/health/electricity constituency
    median used in reasoning strings used to be recomputed by re-scanning+sorting all ~627
    villages once per candidate work (hundreds of redundant sorts per request). Now computed
    once via _compute_theme_medians and threaded through. Assert the hoisted value matches
    an independent from-scratch computation -- this is a perf change, not a behavior change."""
    medians = _compute_theme_medians(gaps)
    for theme in ("school", "health"):
        values = sorted(g.raw[theme] for g in gaps.values() if g.raw.get(theme) is not None)
        if values:
            assert medians[theme] == values[len(values) // 2]
    hours = sorted(24.0 - g.raw["electricity"] for g in gaps.values() if g.raw.get("electricity") is not None)
    if hours:
        assert medians["electricity"] == hours[len(hours) // 2]


def test_silent_need_flag_requires_high_gap_and_low_voice(db):
    result = compute_village_divergence(db)
    for v in result.values():
        if v.silent_need:
            assert v.gap_percentile is not None and v.gap_percentile >= ranking_config.silent_need_gap_percentile
            assert v.voice_percentile <= 0.10
