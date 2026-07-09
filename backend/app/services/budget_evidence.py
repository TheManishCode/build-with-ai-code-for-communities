"""Budget justification -- real comparable evidence for a work's cost estimate.

`theme_cost_heuristic` (config/ranking_weights.yaml) is a flat per-theme figure used by
the allocator's knapsack DP -- deliberately kept simple and already disclosed as a
heuristic, not an engineering estimate (see app.services.allocator's docstring). This
module doesn't replace that number; it surfaces real historical evidence alongside it:
comparable completed MPLADs works of the same theme, mined by keyword-matching their
free-text `work_title` (the `category` column is too coarse -- only 3 values across the
whole dataset -- so the actual per-work-type descriptor lives in the title text, not a
clean field).

PMGSY per-km road-cost data was checked during design and is NOT included here: the
ingested PMGSY tables (`pmgsy_habitation`, `pmgsy_road_proposal`, `pmgsy_road_drrp`) carry
geometry and a coarse `road_category`, but no cost field -- so a "PMGSY benchmark" would
have to be fabricated. Omitted rather than invented; the `note` field says so plainly.

Follows the same LLM provider shape as app.services.explain: NVIDIA NIM first, Claude
backup, a deterministic template if both fail or produce an ungrounded number. The
"allowed values" for grounding are the comparable amounts themselves plus the heuristic
estimate -- same numeric-citation-matching approach as explain.py, applied to this
different data shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.ranking_config import ranking_config
from app.services.ranking import build_ranked_works

NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")
UNCHECKED_SMALL_INT_MAX = 3

# Theme -> keywords matched against mplads_work.work_title (free text). Same
# keyword-matching style as app.services.nlp.THEME_KEYWORDS, applied to a different
# corpus (historical MPLADs work titles rather than citizen submission text).
THEME_KEYWORDS: dict[str, list[str]] = {
    "water": ["water", "borewell", "bore well", "tap", "pipeline", "overhead tank", "hand pump", "handpump"],
    "road": ["road", "cc road", "c.c road", "culvert", "footpath", "pathway"],
    "school": ["school", "anganwadi", "furniture", "classroom"],
    "health": ["hospital", "health", "phc", "ambulance", "medical"],
    "electricity": ["street light", "streetlight", "solar light", "electric", "transformer"],
    "sanitation": ["toilet", "drainage", "sanitation", "sewage"],
    "other": ["community hall"],
}

PMGSY_NOTE = (
    "PMGSY per-km road-cost benchmarks were checked and are not included: the ingested "
    "PMGSY tables carry road geometry and a coarse category, but no cost field -- adding "
    "one here would mean inventing a number, which this project doesn't do."
)


@dataclass
class Comparable:
    work_title: str
    amount: int


@dataclass
class BudgetEvidenceInput:
    theme: str
    village_name: str | None
    estimate: int | None
    comparables: list[Comparable]


@dataclass
class BudgetEvidenceResult:
    narrative: str
    source: str  # "nvidia" | "claude" | "template"
    fallback_reason: str | None


def _find_comparables(db: Session, theme: str, limit: int = 5) -> list[Comparable]:
    keywords = THEME_KEYWORDS.get(theme, [])
    if not keywords:
        return []
    conditions = " OR ".join(f"work_title ILIKE :kw{i}" for i in range(len(keywords)))
    params = {f"kw{i}": f"%{kw}%" for i, kw in enumerate(keywords)}
    rows = db.execute(
        text(
            f"""
            SELECT work_title, completed_amount FROM mplads_work
            WHERE completed_amount IS NOT NULL AND ({conditions})
            ORDER BY completed_date DESC NULLS LAST
            LIMIT :limit
            """
        ),
        {**params, "limit": limit},
    ).all()
    return [Comparable(work_title=r.work_title, amount=int(r.completed_amount)) for r in rows]


def _median(values: list[int]) -> int | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) // 2


def extract_numbers(t: str) -> list[float]:
    out = []
    for m in NUMBER_RE.finditer(t):
        raw = m.group().replace(",", "")
        try:
            out.append(float(raw))
        except ValueError:
            continue
    return out


def _allowed_values(data: BudgetEvidenceInput) -> set[float]:
    allowed: set[float] = set()
    if data.estimate is not None:
        allowed.add(float(data.estimate))
        allowed.add(round(data.estimate / 100_000, 2))
        allowed.add(round(data.estimate / 100_000))
    for c in data.comparables:
        allowed.add(float(c.amount))
        allowed.add(round(c.amount / 100_000, 2))
        allowed.add(round(c.amount / 100_000))
    amounts = [c.amount for c in data.comparables]
    med = _median(amounts)
    if med is not None:
        allowed.add(float(med))
        allowed.add(round(med / 100_000, 2))
        allowed.add(round(med / 100_000))
    return allowed


def verify_grounded(t: str, data: BudgetEvidenceInput, tolerance: float = 0.6) -> tuple[bool, list[float]]:
    allowed = _allowed_values(data)
    ungrounded = []
    for n in extract_numbers(t):
        if abs(n) <= UNCHECKED_SMALL_INT_MAX and n == int(n):
            continue
        if any(abs(n - a) <= tolerance for a in allowed):
            continue
        ungrounded.append(n)
    return (len(ungrounded) == 0, ungrounded)


def build_template_narrative(data: BudgetEvidenceInput) -> str:
    if not data.comparables:
        est_txt = f"Rs. {data.estimate:,}" if data.estimate is not None else "no estimate available"
        return (
            f"No comparable completed {data.theme} works were found in this constituency's MPLADs "
            f"history to benchmark against. The planning estimate of {est_txt} is the flat "
            f"per-theme heuristic used across all {data.theme} works, not derived from a specific "
            f"comparable."
        )
    amounts = [c.amount for c in data.comparables]
    med = _median(amounts)
    est_txt = f"Rs. {data.estimate:,}" if data.estimate is not None else "no estimate"
    comp_txt = "; ".join(f'"{c.work_title}" (Rs. {c.amount:,})' for c in data.comparables[:3])
    relation = "within" if data.estimate is not None and min(amounts) <= data.estimate <= max(amounts) else "outside"
    return (
        f"{len(data.comparables)} comparable completed {data.theme} works in this constituency's "
        f"MPLADs history: {comp_txt}. Median completed cost: Rs. {med:,}. The planning estimate of "
        f"{est_txt} sits {relation} this historical range (Rs. {min(amounts):,}-Rs. {max(amounts):,})."
    )


def _build_prompt(data: BudgetEvidenceInput) -> str:
    comp_desc = "\n".join(f'- "{c.work_title}": Rs. {c.amount:,}' for c in data.comparables)
    place = data.village_name or "this location"
    est_txt = f"Rs. {data.estimate:,}" if data.estimate is not None else "not available"
    return f"""You are writing a short justification for a constituency development work's cost estimate, for an MP's office reviewing budget allocations.

REAL DATA (use ONLY these numbers -- do not invent, round loosely, or estimate any other number):
- Work theme: {data.theme}
- Location: {place}
- Current planning estimate: {est_txt}
- Comparable completed MPLADs works in this constituency (same theme), most recent first:
{comp_desc or "(none found)"}

Write one short paragraph (2-4 sentences) explaining whether the planning estimate is reasonable, citing the comparable amounts directly. Do not use any number not listed above. Do not invent additional statistics or comparables."""


def _try_nvidia_narrative(data: BudgetEvidenceInput) -> str | None:
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
        return response.choices[0].message.content or None
    except Exception:
        return None


def _try_claude_narrative(data: BudgetEvidenceInput) -> str | None:
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
        return response.content[0].text or None
    except Exception:
        return None


def _attempt(source_name: str, raw: str | None, data: BudgetEvidenceInput) -> BudgetEvidenceResult | None:
    if raw is None:
        return None
    ok, _ = verify_grounded(raw, data)
    if ok:
        return BudgetEvidenceResult(narrative=raw.strip(), source=source_name, fallback_reason=None)
    return None


def build_narrative(data: BudgetEvidenceInput) -> BudgetEvidenceResult:
    """Same fallback shape as app.services.explain.build_explanation: NVIDIA first, Claude
    second, each independently verified; a provider that fabricates a number is treated the
    same as one that didn't respond, and the next candidate is tried."""
    attempted_any = False
    verification_failed_any = False

    if settings.nvidia_nim_api_key:
        attempted_any = True
        raw = _try_nvidia_narrative(data)
        shipped = _attempt("nvidia", raw, data)
        if shipped:
            return shipped
        verification_failed_any = verification_failed_any or raw is not None

    if settings.anthropic_api_key:
        attempted_any = True
        raw = _try_claude_narrative(data)
        shipped = _attempt("claude", raw, data)
        if shipped:
            return shipped
        verification_failed_any = verification_failed_any or raw is not None

    narrative = build_template_narrative(data)
    if verification_failed_any:
        reason = "verification_failed"
    elif attempted_any:
        reason = "generation_error"
    else:
        reason = "no_api_key_configured"
    return BudgetEvidenceResult(narrative=narrative, source="template", fallback_reason=reason)


def get_budget_evidence(db: Session, work_id: str) -> dict | None:
    """Returns None if work_id doesn't exist in the current ranking."""
    works = build_ranked_works(db)
    work = next((w for w in works if w.work_id == work_id), None)
    if work is None:
        return None

    estimate = ranking_config.theme_cost_heuristic.get(work.theme)
    comparables = _find_comparables(db, work.theme)
    amounts = [c.amount for c in comparables]

    data = BudgetEvidenceInput(theme=work.theme, village_name=work.village_name, estimate=estimate, comparables=comparables)
    result = build_narrative(data)

    return {
        "work_id": work_id,
        "theme": work.theme,
        "estimate": estimate,
        "comparables": [{"work_title": c.work_title, "amount": c.amount} for c in comparables],
        "median_amount": _median(amounts),
        "min_amount": min(amounts) if amounts else None,
        "max_amount": max(amounts) if amounts else None,
        "note": PMGSY_NOTE,
        "narrative": result.narrative,
        "generation_source": result.source,
        "fallback_reason": result.fallback_reason,
    }
