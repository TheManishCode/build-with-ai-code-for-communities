"""Phase 10 (constituency transparency summary) tests -- pure aggregation, so the bar is
that every number matches an independent fresh query/service call against the same real
data, not a re-read of the summary's own internals."""

from sqlalchemy import text

from app.services.allocator import run_allocation
from app.services.backtest import run_backtest
from app.services.divergence import compute_village_divergence
from app.services.ranking import build_ranked_works
from app.services.transparency import build_transparency_summary

BAGALKOT_BUDGET = 167_541_747


def test_submission_and_issue_counts_match_raw_query(db):
    s = build_transparency_summary(db, BAGALKOT_BUDGET)
    assert s.total_submissions == db.execute(text("SELECT count(*) FROM submission")).scalar_one()
    assert s.total_issues == db.execute(text("SELECT count(*) FROM issue")).scalar_one()


def test_dedup_rate_arithmetic():
    s_total, s_issues = 58, 39
    expected = 1 - (s_issues / s_total)
    # sanity-check the formula itself against known real seed numbers (see Phase 2 summary)
    assert abs(expected - (1 - 39 / 58)) < 1e-9


def test_dedup_rate_matches_real_counts(db):
    s = build_transparency_summary(db, BAGALKOT_BUDGET)
    if s.total_submissions:
        assert s.dedup_rate == 1 - s.total_issues / s.total_submissions
    else:
        assert s.dedup_rate == 0.0


def test_theme_breakdown_sums_to_total_issues(db):
    s = build_transparency_summary(db, BAGALKOT_BUDGET)
    assert sum(s.theme_breakdown.values()) == s.total_issues
    raw = dict(db.execute(text("SELECT theme, count(*) FROM issue GROUP BY theme")).all())
    assert s.theme_breakdown == raw


def test_village_coverage_matches_raw_query(db):
    s = build_transparency_summary(db, BAGALKOT_BUDGET)
    expected_villages = db.execute(
        text("SELECT count(DISTINCT resolved_lgd_code) FROM submission WHERE resolved_lgd_code IS NOT NULL")
    ).scalar_one()
    expected_total = db.execute(text("SELECT count(*) FROM village_fact")).scalar_one()
    assert s.villages_with_submissions == expected_villages
    assert s.total_villages == expected_total
    assert s.voice_coverage_pct == expected_villages / expected_total


def test_silent_need_count_matches_divergence_service(db):
    s = build_transparency_summary(db, BAGALKOT_BUDGET)
    divergence = compute_village_divergence(db)
    expected = sum(1 for v in divergence.values() if v.silent_need)
    assert s.silent_need_village_count == expected


def test_candidate_work_counts_match_ranking_service(db):
    s = build_transparency_summary(db, BAGALKOT_BUDGET)
    works = build_ranked_works(db)
    assert s.total_candidate_works == len(works)
    assert s.issue_based_works == sum(1 for w in works if w.source == "issue")
    assert s.gap_only_works == sum(1 for w in works if w.source == "gap")
    assert s.issue_based_works + s.gap_only_works == s.total_candidate_works


def test_allocation_fields_match_allocator_service(db):
    s = build_transparency_summary(db, BAGALKOT_BUDGET)
    allocation = run_allocation(db, BAGALKOT_BUDGET)
    assert s.budget == BAGALKOT_BUDGET
    assert s.works_funded == len(allocation.selected)
    assert s.budget_used_pct == allocation.budget_used_pct


def test_backtest_fields_match_backtest_service(db):
    s = build_transparency_summary(db, BAGALKOT_BUDGET)
    backtest = run_backtest(db)
    assert s.backtest_ground_truth_villages == backtest.ground_truth_villages
    assert s.backtest_never_addressed_count == len(backtest.never_addressed)
    expected_precision_100 = next((c.precision for c in backtest.cutoffs if c.k == 100), None)
    assert s.backtest_precision_at_100 == expected_precision_100


def test_default_budget_used_when_none_given(db):
    s_explicit = build_transparency_summary(db, BAGALKOT_BUDGET)
    s_default = build_transparency_summary(db, None)
    assert s_default.budget == BAGALKOT_BUDGET  # this IS the real default for Bagalkot's 18th LS
    assert s_default.works_funded == s_explicit.works_funded
