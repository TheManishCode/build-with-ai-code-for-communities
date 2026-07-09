"""Budget justification tests -- mirrors test_explain.py's structure since
app.services.budget_evidence follows the same provider-fallback-with-verification shape.
"""

from app.services.budget_evidence import (
    BudgetEvidenceInput,
    Comparable,
    build_template_narrative,
    extract_numbers,
    get_budget_evidence,
    verify_grounded,
)


def _data(**overrides):
    base = dict(
        theme="road",
        village_name="Testpur",
        estimate=2_500_000,
        comparables=[Comparable(work_title="Construction of a road", amount=499_079)],
    )
    base.update(overrides)
    return BudgetEvidenceInput(**base)


def test_extract_numbers_handles_commas_and_decimals():
    assert extract_numbers("Rs. 4,99,079 and 2,500,000.5") == [499079.0, 2500000.5]


def test_verify_grounded_accepts_real_comparable_and_estimate_amounts():
    text = "The comparable work cost Rs. 499,079 against an estimate of Rs. 2,500,000."
    ok, bad = verify_grounded(text, _data())
    assert ok, f"unexpected ungrounded numbers: {bad}"


def test_verify_grounded_catches_a_fabricated_amount():
    text = "This work should cost around Rs. 12,00,000 based on similar projects."
    ok, bad = verify_grounded(text, _data())
    assert not ok
    assert 1200000.0 in bad


def test_small_integers_are_not_treated_as_data_citations():
    ok, bad = verify_grounded("2 of the 3 comparable works support this.", _data())
    assert ok
    assert bad == []


def test_template_narrative_with_comparables_cites_median_and_range():
    data = _data(comparables=[
        Comparable(work_title="Road A", amount=400_000),
        Comparable(work_title="Road B", amount=600_000),
    ])
    narrative = build_template_narrative(data)
    ok, bad = verify_grounded(narrative, data)
    assert ok, f"template produced an ungrounded number: {bad}"
    assert "500,000" in narrative  # median of 400k/600k

    assert build_template_narrative(data) == narrative


def test_template_narrative_with_no_comparables_says_so_plainly():
    data = _data(comparables=[])
    narrative = build_template_narrative(data)
    assert "No comparable" in narrative
    ok, bad = verify_grounded(narrative, data)
    assert ok, f"unexpected ungrounded numbers: {bad}"


def test_get_budget_evidence_returns_none_for_unknown_work_id(db):
    assert get_budget_evidence(db, "issue-999999999") is None


def test_get_budget_evidence_is_grounded_for_a_real_work(db):
    from app.services.ranking import build_ranked_works

    works = build_ranked_works(db)
    assert works, "expected at least one ranked work in seed data"
    result = get_budget_evidence(db, works[0].work_id)
    assert result is not None
    assert result["theme"] == works[0].theme
    data = BudgetEvidenceInput(
        theme=result["theme"],
        village_name=None,
        estimate=result["estimate"],
        comparables=[Comparable(work_title=c["work_title"], amount=c["amount"]) for c in result["comparables"]],
    )
    ok, bad = verify_grounded(result["narrative"], data)
    assert ok, f"shipped narrative has ungrounded numbers: {bad}"
