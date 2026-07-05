"""Phase 8 (Rejection Explainer) tests. The core requirement from the ground rules is the
numeric-verification guardrail: generated text is only shipped if every number it cites
exists in the real structured input; otherwise a template fallback is used. These tests
exercise that guardrail directly (both the "should pass" and "should catch fabrication"
cases), the knapsack-cutoff/comparison logic against real data, and the actual behavior of
this environment (no ANTHROPIC_API_KEY configured -> always falls back to template).
"""

from unittest.mock import patch

from app.core.config import settings
from app.services.allocator import run_allocation
from app.services.explain import (
    ComparisonWork,
    ExplanationInput,
    build_explanation,
    build_template_explanation,
    explain_work,
    extract_numbers,
    find_comparisons,
    verify_grounded,
)
from app.services.ranking import CandidateWork, build_ranked_works


def _work(**overrides):
    base = dict(
        work_id="issue-999", source="issue", theme="water", village_code=1, village_name="Testpur",
        representative_text="", corroboration_count=4, demand_raw=1.0, demand_percentile=0.81,
        gap_percentile=0.62, population_affected=3000, composite_score=0.715,
    )
    base.update(overrides)
    return CandidateWork(**base)


def test_extract_numbers_handles_commas_decimals_percent():
    assert extract_numbers("score 73%, cost Rs. 5,00,000 and 0.62 gap") == [73.0, 500000.0, 0.62]


def test_small_integers_are_not_treated_as_data_citations():
    """'2 of the 3 works' shouldn't force verification failure -- these are counting words,
    not data citations. This is the case the UNCHECKED_SMALL_INT_MAX threshold is FOR."""
    data = ExplanationInput(work=_work(), cost=500_000, cutoff_score=0.9, comparisons=[])
    ok, bad = verify_grounded("Comparing 2 of the 3 works that beat this one.", data)
    assert ok
    assert bad == []


def test_structural_100_in_out_of_100_phrasing_is_not_flagged():
    """Real false-positive caught while building this: 'scored 72 out of 100' contains the
    literal 100, which is a scale reference, not a data citation. Locks in the fix."""
    data = ExplanationInput(work=_work(), cost=500_000, cutoff_score=0.9, comparisons=[])
    ok, bad = verify_grounded("This work scored 72 out of 100 on the priority index.", data)
    assert ok, f"unexpected ungrounded numbers: {bad}"


def test_verify_grounded_catches_a_fabricated_number():
    data = ExplanationInput(work=_work(), cost=500_000, cutoff_score=0.9, comparisons=[])
    # 42% appears nowhere in the real data (composite_score=0.715->71.5%, cutoff=0.9->90%)
    ok, bad = verify_grounded("This work scored 42% which is well below average.", data)
    assert not ok
    assert 42.0 in bad


def test_verify_grounded_accepts_real_numbers_in_multiple_representations():
    work = _work(composite_score=0.715, demand_percentile=0.81, gap_percentile=0.62, corroboration_count=4)
    data = ExplanationInput(work=work, cost=500_000, cutoff_score=0.9, comparisons=[])
    text = (
        "This work scored 71.5% (composite_score 0.715), with demand percentile 81% and gap "
        "percentile 62%. Its estimated cost is Rs. 500,000, i.e. 5 lakh. It had 4 citizen reports. "
        "The funding cutoff was 90%."
    )
    ok, bad = verify_grounded(text, data)
    assert ok, f"unexpected ungrounded numbers: {bad}"


def test_template_explanation_is_always_grounded():
    """The template path builds text directly from the same real values -- verify_grounded
    must always pass on its own output, by construction."""
    work = _work()
    comparisons = [ComparisonWork(village_name="Other Village", theme="water", composite_score=0.82, cost=500_000)]
    data = ExplanationInput(work=work, cost=500_000, cutoff_score=0.78, comparisons=comparisons)
    mp_text, citizen_text = build_template_explanation(data)
    ok_mp, bad_mp = verify_grounded(mp_text, data)
    ok_citizen, bad_citizen = verify_grounded(citizen_text, data)
    assert ok_mp, f"template MP text had ungrounded numbers: {bad_mp}"
    assert ok_citizen, f"template citizen text had ungrounded numbers: {bad_citizen}"


def test_build_explanation_falls_back_to_template_when_no_keys_configured():
    """Explicitly patches both keys to None rather than relying on ambient environment
    state, since real keys ARE configured in this environment now (NVIDIA base model +
    Claude backup) -- this test still needs to exercise the no-key path deterministically."""
    data = ExplanationInput(work=_work(), cost=500_000, cutoff_score=0.9, comparisons=[])
    with patch.object(settings, "nvidia_nim_api_key", None), patch.object(settings, "anthropic_api_key", None):
        result = build_explanation(data)
    assert result.source == "template"
    assert result.fallback_reason == "no_api_key_configured"
    assert result.mp_explanation and result.citizen_message


def test_nvidia_tried_first_claude_not_called_when_nvidia_succeeds():
    """NVIDIA is the base model per user instruction -- Claude (the backup) must not even
    be invoked when NVIDIA already produced a grounded result."""
    work = _work(composite_score=0.715)
    data = ExplanationInput(work=work, cost=500_000, cutoff_score=0.9, comparisons=[])
    good_text = ("NVIDIA text citing 71.5%.", "Citizen text, no numbers here.")
    with patch.object(settings, "nvidia_nim_api_key", "dummy-nvidia-key"):
        with patch("app.services.explain._try_nvidia_explanation", return_value=good_text) as mock_nvidia:
            with patch("app.services.explain._try_claude_explanation") as mock_claude:
                result = build_explanation(data)
    mock_nvidia.assert_called_once()
    mock_claude.assert_not_called()
    assert result.source == "nvidia"
    assert result.fallback_reason is None


def test_generation_error_is_not_misreported_as_no_api_key():
    """Real bug caught while live-testing against the actual NVIDIA API: the first model ID
    tried was listed in NVIDIA's catalog but returned 404 'Function not found for account'
    when actually called -- a genuine generation_error with a key configured, but the
    original (buggy) logic inferred "attempted" from the return value, which is None in
    both the no-key and call-failed cases, so it reported 'no_api_key_configured' even
    though a key WAS present. This asserts the fix: a configured key whose call fails is
    classified as generation_error, and 'no_api_key_configured' is reserved for when
    neither key is configured at all."""
    data = ExplanationInput(work=_work(), cost=500_000, cutoff_score=0.9, comparisons=[])
    with patch.object(settings, "nvidia_nim_api_key", "dummy-nvidia-key"), patch.object(settings, "anthropic_api_key", None):
        with patch("app.services.explain._try_nvidia_explanation", return_value=None):
            result = build_explanation(data)
    assert result.source == "template"
    assert result.fallback_reason == "generation_error"


def test_falls_back_to_claude_when_nvidia_unavailable():
    work = _work(composite_score=0.715)
    data = ExplanationInput(work=work, cost=500_000, cutoff_score=0.9, comparisons=[])
    good_text = ("Claude text citing 71.5%.", "Citizen text, no numbers here.")
    with patch.object(settings, "nvidia_nim_api_key", None), patch.object(settings, "anthropic_api_key", "dummy-key"):
        with patch("app.services.explain._try_claude_explanation", return_value=good_text):
            result = build_explanation(data)
    assert result.source == "claude"
    assert result.fallback_reason is None


def test_falls_back_to_template_when_both_providers_fail_verification():
    """Simulates both configured models fabricating a number -- verification must catch
    it for EACH candidate and force the template fallback, without ever shipping bad text."""
    data = ExplanationInput(work=_work(), cost=500_000, cutoff_score=0.9, comparisons=[])
    bad_text = ("Scored 42% overall.", "Sorry, not funded.")
    with patch.object(settings, "nvidia_nim_api_key", "dummy-nvidia-key"), patch.object(settings, "anthropic_api_key", "dummy-key"):
        with patch("app.services.explain._try_nvidia_explanation", return_value=bad_text):
            with patch("app.services.explain._try_claude_explanation", return_value=bad_text):
                result = build_explanation(data)
    assert result.source == "template"
    assert result.fallback_reason == "verification_failed"


def test_build_explanation_ships_llm_output_when_grounded():
    work = _work(composite_score=0.715, demand_percentile=0.81, gap_percentile=0.62)
    data = ExplanationInput(work=work, cost=500_000, cutoff_score=0.9, comparisons=[])
    good_text = ("MP text citing 71.5% and cutoff 90%.", "Citizen text, no numbers here.")
    with patch.object(settings, "nvidia_nim_api_key", None), patch.object(settings, "anthropic_api_key", "dummy-key-for-test"):
        with patch("app.services.explain._try_claude_explanation", return_value=good_text):
            result = build_explanation(data)
    assert result.source == "claude"
    assert result.fallback_reason is None
    assert result.mp_explanation == good_text[0]
    assert result.citizen_message == good_text[1]


def test_find_comparisons_only_returns_higher_scoring_funded_works(db):
    works = build_ranked_works(db)
    allocation = run_allocation(db, budget=167_541_747)  # Bagalkot's real 18th-LS limit
    unfunded = [w for w in works if w.work_id not in {it.work.work_id for it in allocation.selected}]
    assert unfunded, "expected at least one unfunded work at the real default budget"

    target = unfunded[0]
    comparisons = find_comparisons(target, allocation, limit=3)
    assert len(comparisons) <= 3
    for c in comparisons:
        assert c.composite_score > target.composite_score


def test_explain_work_funded_case_has_no_explanation_fields(db):
    works = build_ranked_works(db)
    allocation = run_allocation(db, budget=167_541_747)
    assert allocation.selected, "expected at least one funded work"
    funded_id = allocation.selected[0].work.work_id

    result = explain_work(db, funded_id, budget=167_541_747)
    assert result is not None
    assert result["is_funded"] is True
    assert "mp_explanation" not in result


def test_explain_work_unfunded_case_cutoff_matches_real_allocation(db):
    """Patches out both real providers so this stays a fast, deterministic, network-free
    test like the rest of this project's suite -- the real NVIDIA/Claude integration is
    verified separately via a live manual check, not inside the automated pytest run."""
    works = build_ranked_works(db)
    allocation = run_allocation(db, budget=167_541_747)
    funded_ids = {it.work.work_id for it in allocation.selected}
    unfunded = [w for w in works if w.work_id not in funded_ids]
    assert unfunded

    with patch.object(settings, "nvidia_nim_api_key", None), patch.object(settings, "anthropic_api_key", None):
        result = explain_work(db, unfunded[0].work_id, budget=167_541_747)
    assert result is not None
    assert result["is_funded"] is False
    expected_cutoff = round(min(it.work.composite_score for it in allocation.selected), 4)
    assert result["cutoff_score"] == expected_cutoff
    assert result["generation_source"] == "template"
    assert result["fallback_reason"] == "no_api_key_configured"


def test_explain_work_returns_none_for_unknown_work_id(db):
    assert explain_work(db, "issue-99999999", budget=167_541_747) is None
