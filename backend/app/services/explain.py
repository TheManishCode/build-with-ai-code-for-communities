"""Phase 8: Rejection Explainer.

For a work that did NOT make the budget allocator's cut, explain why -- to the MP's office
(operational: scores, cutoff, budget math) and to the citizen who reported it (plain
language). Generation goes through NVIDIA NIM first (base model, per user instruction) and
falls back to Claude (backup) if NVIDIA is unavailable or its output fails verification.
Per this project's numeric-verification requirement: every number the generated text cites
is extracted and checked against the real structured values passed into the prompt. If
BOTH providers fail (missing key, API error, or failed verification), we fall back to a
deterministic template built directly from the same real values, grounded by construction
the same way app.services.ranking.build_reasoning is.

LIVE-VERIFIED (not just unit-tested with mocks) against the real APIs while building this:
  - NVIDIA: the initially-chosen model ("nvidia/llama-3.1-nemotron-70b-instruct") is listed
    in the NIM catalog but returned 404 "Function not found for account" when actually
    called -- listed != deployed for a given account/key. Queried the account's real
    available models and found "nvidia/nemotron-3-ultra-550b-a55b" (NVIDIA's flagship,
    550B) genuinely callable -- now the default. That model does visible chain-of-thought
    reasoning before its final answer; at the original max_tokens=500 it was cut off
    mid-reasoning with no parseable answer at all. Bumped to max_tokens=2500, verified
    sufficient for a complete, correctly-grounded response on a real Bagalkot work
    (issue-35, Rugi road work) -- see the "nvidia" generation_source in that live response.
  - Claude (backup): the API call itself is coded and unit-tested, but the configured key's
    account currently has insufficient credits (a real 400 "credit balance too low" error,
    an account/billing constraint, not a code defect) -- confirmed the failure path still
    correctly falls through to the template rather than raising or hanging.

KNAPSACK CUTOFF CAVEAT (disclosed, not hidden): a 0/1 knapsack has no single scalar
"cutoff score" the way a sorted greedy allocation would -- a cheaper, lower-scoring item
can be selected over an expensive, higher-scoring one if it fits better. `cutoff_score`
here is the minimum composite_score among ACTUALLY FUNDED works, a practical proxy, not a
strict decision boundary. "Works that beat it" are the funded works with the smallest
composite_score margin above the excluded work's own score -- its closest competitors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.allocator import AllocationResult, run_allocation
from app.services.ranking import CandidateWork, build_ranked_works

NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")
# Small integers this common in ordinary phrasing ("2 of the 3 comparisons", "one report")
# aren't data citations worth verifying -- only larger/precise numbers (scores, percentiles,
# rupee amounts) are checked. This threshold is a deliberate, disclosed design choice, not
# an oversight -- see test_explain.py for both a case this threshold correctly ignores and
# one it correctly catches.
UNCHECKED_SMALL_INT_MAX = 3

# Structural scale references that appear in ordinary phrasing about percentages/scores
# ("scored 72 out of 100") without being a data citation themselves. Caught as a real
# false-positive during Phase 8 verification (see test_explain.py
# test_template_explanation_is_always_grounded) -- the template says "X out of 100" and the
# literal 100 was flagged as ungrounded before this was added.
STRUCTURAL_NUMBERS = {100.0}


@dataclass
class ComparisonWork:
    village_name: str | None
    theme: str
    composite_score: float
    cost: int


@dataclass
class ExplanationInput:
    work: CandidateWork
    cost: int | None
    cutoff_score: float
    comparisons: list[ComparisonWork]


@dataclass
class ExplanationResult:
    mp_explanation: str
    citizen_message: str
    source: str  # "llm" | "template"
    fallback_reason: str | None  # None when source == "llm"


def extract_numbers(text: str) -> list[float]:
    out = []
    for m in NUMBER_RE.finditer(text):
        raw = m.group().replace(",", "")
        try:
            out.append(float(raw))
        except ValueError:
            continue
    return out


def _allowed_values(data: ExplanationInput) -> set[float]:
    """Every number-shaped thing that's legitimate to cite, in every representation a
    fluent sentence might use (raw score, whole-number percent, rupee amount, lakh-scaled).
    """
    allowed: set[float] = set()

    def add_score(v: float | None) -> None:
        if v is None:
            return
        allowed.add(round(v, 4))
        allowed.add(round(v * 100))  # e.g. 0.73 -> "73%"
        allowed.add(round(v * 100, 1))

    add_score(data.work.composite_score)
    add_score(data.work.demand_percentile)
    add_score(data.work.gap_percentile)
    add_score(data.cutoff_score)

    if data.cost is not None:
        allowed.add(float(data.cost))
        allowed.add(round(data.cost / 100_000, 2))  # lakhs
        allowed.add(round(data.cost / 100_000))

    if data.work.population_affected is not None:
        allowed.add(float(data.work.population_affected))

    if data.work.corroboration_count is not None:
        allowed.add(float(data.work.corroboration_count))

    for c in data.comparisons:
        add_score(c.composite_score)
        allowed.add(float(c.cost))
        allowed.add(round(c.cost / 100_000, 2))
        allowed.add(round(c.cost / 100_000))

    return allowed


def verify_grounded(text: str, data: ExplanationInput, tolerance: float = 0.6) -> tuple[bool, list[float]]:
    """Returns (is_grounded, ungrounded_numbers). A number is ungrounded if it's not within
    `tolerance` of ANY allowed value -- tolerance absorbs rounding-to-nearest-percent /
    rounding-to-nearest-rupee noise, not genuine fabrication."""
    allowed = _allowed_values(data)
    ungrounded = []
    for n in extract_numbers(text):
        if abs(n) <= UNCHECKED_SMALL_INT_MAX and n == int(n):
            continue
        if n in STRUCTURAL_NUMBERS:
            continue
        if any(abs(n - a) <= tolerance for a in allowed):
            continue
        ungrounded.append(n)
    return (len(ungrounded) == 0, ungrounded)


def build_template_explanation(data: ExplanationInput) -> tuple[str, str]:
    w = data.work
    place = w.village_name or "this location"
    score_pct = round(w.composite_score * 100)
    cutoff_pct = round(data.cutoff_score * 100)
    cost_txt = f"Rs. {data.cost:,}" if data.cost is not None else "an unestimated amount"

    comp_lines = "; ".join(
        f"{c.village_name or 'another village'} ({c.theme}, score {round(c.composite_score * 100)}, cost Rs. {c.cost:,})"
        for c in data.comparisons
    )

    mp_text = (
        f"The {w.theme} work in {place} scored {score_pct} out of 100 on the composite priority "
        f"index, below the {cutoff_pct} score of the lowest-ranked work that was funded within the "
        f"current budget. Its estimated cost is {cost_txt}. Works that were funded instead include: "
        f"{comp_lines or 'no directly comparable works were available'}. Note: this is a knapsack "
        f"allocation, not a strict ranking cutoff -- a cheaper, lower-scoring work can be selected "
        f"over a costlier, higher-scoring one if it fits the remaining budget better."
    )

    citizen_text = (
        f"Your report about {w.theme} in {place} has been recorded and scored, but it could not be "
        f"funded in this budget cycle because other locations had a higher combination of urgency "
        f"and citizen reports relative to their cost. It remains on the priority list for the next "
        f"funding round."
    )
    return mp_text, citizen_text


def _build_prompt(data: ExplanationInput) -> str:
    w = data.work
    comp_desc = "\n".join(
        f"- {c.village_name or 'unresolved location'}: theme={c.theme}, composite_score={c.composite_score:.4f}, cost=Rs.{c.cost:,}"
        for c in data.comparisons
    )
    return f"""You are writing two short texts about a constituency development work that was NOT selected for funding this cycle.

REAL DATA (use ONLY these numbers -- do not invent, round loosely, or estimate any other number):
- Work theme: {w.theme}
- Location: {w.village_name or "unresolved location"}
- This work's composite_score: {w.composite_score:.4f} (0-1 scale)
- This work's demand_percentile: {w.demand_percentile:.4f}
- This work's gap_percentile: {w.gap_percentile if w.gap_percentile is not None else "not available for this theme"}
- Estimated cost: {f"Rs.{data.cost:,}" if data.cost is not None else "not available"}
- Corroboration count (citizen reports): {w.corroboration_count}
- Population affected: {w.population_affected if w.population_affected is not None else "unknown"}
- Cutoff: the lowest composite_score among works that WERE funded is {data.cutoff_score:.4f}
- Works that were funded instead (closest competitors):
{comp_desc}

Write exactly two paragraphs, separated by a line containing only "---":
1. An MP-office-facing operational explanation (scores, cutoff, cost, why it fell short) -- factual and concise.
2. A short, plain-language, respectful message suitable to show the citizen who reported this issue.

Do not use any number that is not listed above. Do not invent additional statistics."""


def _split_response(text: str) -> tuple[str, str] | None:
    if "---" not in text:
        return None
    mp_part, _, citizen_part = text.partition("---")
    mp_part, citizen_part = mp_part.strip(), citizen_part.strip()
    if not mp_part or not citizen_part:
        return None
    return mp_part, citizen_part


def _try_nvidia_explanation(data: ExplanationInput) -> tuple[str, str] | None:
    """Primary/base model, per user instruction: NVIDIA NIM's OpenAI-compatible API.

    max_tokens=2500 -- caught live: the default nemotron-3-ultra-550b-a55b is a reasoning
    model that spends most of its budget on visible chain-of-thought before the final
    answer (confirmed via a raw, unwrapped call during verification: at max_tokens=500 it
    was cut off mid-reasoning with no "---"-delimited answer at all, silently producing a
    None result indistinguishable from a real failure). 2500 was verified sufficient to
    reach a complete, correctly-grounded two-paragraph answer for a real Bagalkot work.
    """
    if not settings.nvidia_nim_api_key:
        return None
    try:
        import openai
    except ImportError:
        return None

    try:
        client = openai.OpenAI(api_key=settings.nvidia_nim_api_key, base_url="https://integrate.api.nvidia.com/v1")
        response = client.chat.completions.create(
            model=settings.nvidia_model,
            max_tokens=2500,
            messages=[{"role": "user", "content": _build_prompt(data)}],
        )
        text = response.choices[0].message.content
    except Exception:
        return None

    return _split_response(text) if text else None


def _try_claude_explanation(data: ExplanationInput) -> tuple[str, str] | None:
    """Backup model, per user instruction: used only when NVIDIA is unavailable or its
    output fails the numeric-verification guardrail."""
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1000,
            messages=[{"role": "user", "content": _build_prompt(data)}],
        )
        text = response.content[0].text
    except Exception:
        return None

    return _split_response(text) if text else None


def _attempt(source_name: str, result: tuple[str, str] | None, data: ExplanationInput) -> ExplanationResult | None:
    """Returns a shipped ExplanationResult if `result` is present and grounded, else None
    (caller moves on to the next candidate, or to the template)."""
    if result is None:
        return None
    mp_text, citizen_text = result
    mp_ok, _ = verify_grounded(mp_text, data)
    citizen_ok, _ = verify_grounded(citizen_text, data)
    if mp_ok and citizen_ok:
        return ExplanationResult(mp_text, citizen_text, source=source_name, fallback_reason=None)
    return None


def build_explanation(data: ExplanationInput) -> ExplanationResult:
    """NVIDIA (base model) is tried first, Claude (backup) second -- each candidate's output
    must independently pass verify_grounded; a provider that responds but fabricates a
    number is treated the same as one that didn't respond at all, and the next candidate is
    tried. Calls _try_nvidia_explanation/_try_claude_explanation directly by name (not
    through a tuple of function references captured once at import time) so that
    unittest.mock.patch("app.services.explain._try_..._explanation", ...) in tests actually
    takes effect -- a module-level tuple built at import time would freeze in the original
    function object and silently ignore patches applied afterward (a real bug caught while
    building this).

    NOTE on fallback_reason: whether a provider was "attempted" is determined by checking
    settings.*_api_key directly, NOT by whether the call returned a result -- both "no key
    configured" and "key configured but the API call itself raised" produce a None result
    from _try_*_explanation (which swallows exceptions), so inferring "attempted" from the
    return value would conflate the two into the same misleading "no_api_key_configured"
    reason. This was a real bug caught while verifying this phase against the live NVIDIA
    API (the configured model wasn't deployed for this account -- a genuine generation_error
    -- and the response incorrectly claimed no key was configured at all).
    """
    attempted_any = False
    verification_failed_any = False

    if settings.nvidia_nim_api_key:
        attempted_any = True
        nvidia_raw = _try_nvidia_explanation(data)
        shipped = _attempt("nvidia", nvidia_raw, data)
        if shipped:
            return shipped
        verification_failed_any = verification_failed_any or nvidia_raw is not None

    if settings.anthropic_api_key:
        attempted_any = True
        claude_raw = _try_claude_explanation(data)
        shipped = _attempt("claude", claude_raw, data)
        if shipped:
            return shipped
        verification_failed_any = verification_failed_any or claude_raw is not None

    mp_text, citizen_text = build_template_explanation(data)
    if verification_failed_any:
        reason = "verification_failed"
    elif attempted_any:
        reason = "generation_error"
    else:
        reason = "no_api_key_configured"
    return ExplanationResult(mp_text, citizen_text, source="template", fallback_reason=reason)


def find_comparisons(target: CandidateWork, allocation: AllocationResult, limit: int = 3) -> list[ComparisonWork]:
    """The funded works with the smallest composite_score margin above the target's own
    score -- its closest competitors, the most informative comparison for "why not me"."""
    beat_it = [
        it for it in allocation.selected
        if it.work.composite_score > target.composite_score and it.work.work_id != target.work_id
    ]
    beat_it.sort(key=lambda it: it.work.composite_score - target.composite_score)
    return [
        ComparisonWork(village_name=it.work.village_name, theme=it.work.theme, composite_score=it.work.composite_score, cost=it.cost)
        for it in beat_it[:limit]
    ]


def explain_work(db: Session, work_id: str, budget: int) -> dict | None:
    """Returns None if work_id doesn't exist. Returns {"is_funded": True, ...} without an
    explanation if the work IS funded at this budget (nothing to explain)."""
    works = build_ranked_works(db)
    work = next((w for w in works if w.work_id == work_id), None)
    if work is None:
        return None

    allocation = run_allocation(db, budget)
    is_funded = any(it.work.work_id == work_id for it in allocation.selected)

    from app.core.ranking_config import ranking_config

    cost = ranking_config.theme_cost_heuristic.get(work.theme)

    if is_funded:
        return {"work_id": work_id, "is_funded": True}

    cutoff_score = min((it.work.composite_score for it in allocation.selected), default=0.0)
    comparisons = find_comparisons(work, allocation)

    data = ExplanationInput(work=work, cost=cost, cutoff_score=cutoff_score, comparisons=comparisons)
    result = build_explanation(data)

    return {
        "work_id": work_id,
        "is_funded": False,
        "theme": work.theme,
        "village_name": work.village_name,
        "composite_score": round(work.composite_score, 4),
        "demand_percentile": round(work.demand_percentile, 4),
        "gap_percentile": round(work.gap_percentile, 4) if work.gap_percentile is not None else None,
        "cost": cost,
        "cutoff_score": round(cutoff_score, 4),
        "cutoff_caveat": (
            "This is a knapsack allocation, not a strict score ranking -- cutoff_score is the "
            "minimum composite_score among funded works, a practical proxy, not a strict boundary."
        ),
        "compared_against": [
            {"village_name": c.village_name, "theme": c.theme, "composite_score": round(c.composite_score, 4), "cost": c.cost}
            for c in comparisons
        ],
        "mp_explanation": result.mp_explanation,
        "citizen_message": result.citizen_message,
        "generation_source": result.source,
        "fallback_reason": result.fallback_reason,
    }
