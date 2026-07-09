"""Tool registry for the citizen assistant chatbot (app.services.chatbot).

Each tool wraps an *existing*, already-tested service rather than adding new query logic
-- the chatbot's grounding comes from only ever seeing real tool output, the same
philosophy as app.services.explain's numeric-verification guardrail applied to a
different (free-form, multi-turn) shape: a model that can only cite what a tool actually
returned can't fabricate a village, a score, or a rupee amount.

Schemas are provider-agnostic dicts; app.services.chatbot adapts them to each provider's
tool-calling format (Anthropic's `tools` vs. NVIDIA/OpenAI's `tools` function-calling
shape) since the two are structurally different but describe the same tools.
"""

from __future__ import annotations

from dataclasses import asdict

from rapidfuzz import fuzz, process, utils
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.submission import Channel
from app.services.allocator import run_allocation
from app.services.budget_evidence import get_budget_evidence
from app.services.citizen_status import get_citizen_status as _citizen_status_lookup
from app.services.intake import process_submission
from app.services.ranking import build_ranked_works
from app.services.transparency import build_transparency_summary

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "search_villages",
        "description": "Fuzzy-search villages in Bagalkot constituency by name. Returns up to 5 matches with key infrastructure facts.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Village name or partial name, in English."}},
            "required": ["query"],
        },
    },
    {
        "name": "get_village_detail",
        "description": "Get full facts for one village by its village_code: demographics, infrastructure gaps, its citizen-reported issues, and its ranked development works.",
        "parameters": {
            "type": "object",
            "properties": {"village_code": {"type": "integer"}},
            "required": ["village_code"],
        },
    },
    {
        "name": "get_ranked_works",
        "description": "Get the top-ranked candidate development works for the constituency, optionally filtered by theme (water/road/school/health/electricity/sanitation) or village_code.",
        "parameters": {
            "type": "object",
            "properties": {
                "theme": {"type": "string"},
                "village_code": {"type": "integer"},
                "limit": {"type": "integer", "description": "Max results, default 10."},
            },
        },
    },
    {
        "name": "get_work_detail",
        "description": "Get full detail for one candidate development work by its work_id: its priority score, the reasoning behind that score, its estimated cost, and whether it's currently funded.",
        "parameters": {
            "type": "object",
            "properties": {"work_id": {"type": "string"}},
            "required": ["work_id"],
        },
    },
    {
        "name": "get_citizen_status",
        "description": "Look up what happened to a specific citizen's report by its submission_id: which issue it was grouped into, its rank, and its funding status.",
        "parameters": {
            "type": "object",
            "properties": {"submission_id": {"type": "integer"}},
            "required": ["submission_id"],
        },
    },
    {
        "name": "get_transparency_summary",
        "description": "Get an overall public summary of the constituency: total citizen submissions, unique issues, villages with no citizen voice, works funded, budget used, and backtest precision.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_budget_justification",
        "description": "Get real historical cost evidence for a work's budget estimate: comparable completed MPLADS works of the same theme in this constituency, with their actual final costs.",
        "parameters": {
            "type": "object",
            "properties": {"work_id": {"type": "string"}},
            "required": ["work_id"],
        },
    },
    {
        "name": "file_grievance",
        "description": (
            "File a new citizen report/grievance on the citizen's behalf. Only call this after the "
            "citizen has clearly described their issue in their own words AND explicitly confirmed "
            "they want it submitted -- never file on a vague or unconfirmed description."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "raw_text": {
                    "type": "string",
                    "description": "The citizen's issue, in their own words, ideally naming the village/place.",
                },
                "language": {"type": "string", "description": "ISO language code, e.g. 'en' or 'kn'. Default 'en'."},
            },
            "required": ["raw_text"],
        },
    },
]


def _default_mplads_budget(db: Session) -> int:
    row = db.execute(
        text("SELECT allocated_amount FROM mplads_allocated_limit WHERE lok_sabha_term = '18th' ORDER BY id LIMIT 1")
    ).first()
    return int(row.allocated_amount) if row else 0


def _search_villages(db: Session, query: str) -> dict:
    rows = db.execute(
        text("SELECT village_code, village_name, subdistrict_name, total_population, has_safe_water_source, has_all_weather_road FROM village_fact")
    ).all()
    names = [r.village_name for r in rows]
    matches = process.extract(query, names, scorer=fuzz.WRatio, processor=utils.default_process, limit=5)
    by_name = {r.village_name: r for r in rows}
    results = []
    for name, score, _ in matches:
        if score < 70:
            continue
        r = by_name[name]
        results.append({
            "village_code": r.village_code,
            "village_name": r.village_name,
            "subdistrict_name": r.subdistrict_name,
            "total_population": r.total_population,
            "has_safe_water_source": r.has_safe_water_source,
            "has_all_weather_road": r.has_all_weather_road,
            "match_score": round(score, 1),
        })
    return {"matches": results}


def _get_village_detail(db: Session, village_code: int) -> dict:
    row = db.execute(text("SELECT * FROM village_fact WHERE village_code = :vc"), {"vc": village_code}).mappings().first()
    if row is None:
        return {"found": False}
    issues = db.execute(
        text("SELECT id, theme, representative_text, corroboration_count FROM issue WHERE village_code = :vc"),
        {"vc": village_code},
    ).all()
    works = [w for w in build_ranked_works(db) if w.village_code == village_code]
    return {
        "found": True,
        "village_fact": {k: v for k, v in row.items() if k != "geom"},
        "issues": [
            {"id": i.id, "theme": i.theme, "representative_text": i.representative_text, "corroboration_count": i.corroboration_count}
            for i in issues
        ],
        "works": [
            {"work_id": w.work_id, "theme": w.theme, "composite_score": round(w.composite_score, 4), "reasoning": w.reasoning}
            for w in works[:10]
        ],
    }


def _get_ranked_works(db: Session, theme: str | None = None, village_code: int | None = None, limit: int = 10) -> dict:
    works = build_ranked_works(db)
    if theme:
        works = [w for w in works if w.theme == theme]
    if village_code is not None:
        works = [w for w in works if w.village_code == village_code]
    return {
        "works": [
            {
                "work_id": w.work_id,
                "theme": w.theme,
                "village_name": w.village_name,
                "composite_score": round(w.composite_score, 4),
                "corroboration_count": w.corroboration_count,
                "reasoning": w.reasoning,
            }
            for w in works[:limit]
        ]
    }


def _get_work_detail(db: Session, work_id: str) -> dict:
    works = build_ranked_works(db)
    work = next((w for w in works if w.work_id == work_id), None)
    if work is None:
        return {"found": False}
    budget = _default_mplads_budget(db)
    allocation = run_allocation(db, budget, candidates=works)
    is_funded = any(it.work.work_id == work_id for it in allocation.selected)
    return {
        "found": True,
        "work_id": work.work_id,
        "theme": work.theme,
        "village_name": work.village_name,
        "composite_score": round(work.composite_score, 4),
        "demand_percentile": round(work.demand_percentile, 4),
        "gap_percentile": round(work.gap_percentile, 4) if work.gap_percentile is not None else None,
        "corroboration_count": work.corroboration_count,
        "population_affected": work.population_affected,
        "reasoning": work.reasoning,
        "is_funded_this_cycle": is_funded,
    }


def _get_citizen_status(db: Session, submission_id: int) -> dict:
    budget = _default_mplads_budget(db)
    status = _citizen_status_lookup(db, submission_id, budget)
    return asdict(status)


def _get_transparency_summary(db: Session) -> dict:
    return asdict(build_transparency_summary(db))


def _get_budget_justification(db: Session, work_id: str) -> dict:
    result = get_budget_evidence(db, work_id)
    return result if result is not None else {"found": False}


def _file_grievance(db: Session, raw_text: str, language: str = "en") -> dict:
    result = process_submission(db, channel=Channel.text, raw_text=raw_text, language=language or "en")
    s = result.submission
    return {
        "submission_id": s.id,
        "theme": s.theme.value,
        "village_name": result.village_name,
        "issue_id": s.issue_id,
    }


def execute_tool(db: Session, name: str, tool_input: dict) -> dict:
    """Dispatches a tool call by name. Any exception (bad input, DB error) is caught and
    returned as a structured error rather than raised -- the model sees "this tool call
    failed" and can recover (ask for clarification, try a different tool) instead of the
    whole chat turn crashing."""
    try:
        if name == "search_villages":
            return _search_villages(db, tool_input["query"])
        if name == "get_village_detail":
            return _get_village_detail(db, int(tool_input["village_code"]))
        if name == "get_ranked_works":
            return _get_ranked_works(
                db,
                theme=tool_input.get("theme"),
                village_code=tool_input.get("village_code"),
                limit=int(tool_input.get("limit", 10)),
            )
        if name == "get_work_detail":
            return _get_work_detail(db, tool_input["work_id"])
        if name == "get_citizen_status":
            return _get_citizen_status(db, int(tool_input["submission_id"]))
        if name == "get_transparency_summary":
            return _get_transparency_summary(db)
        if name == "get_budget_justification":
            return _get_budget_justification(db, tool_input["work_id"])
        if name == "file_grievance":
            return _file_grievance(db, tool_input["raw_text"], tool_input.get("language", "en"))
        return {"error": f"Unknown tool {name!r}"}
    except Exception as e:  # noqa: BLE001 -- deliberately broad, see docstring
        return {"error": str(e)}
