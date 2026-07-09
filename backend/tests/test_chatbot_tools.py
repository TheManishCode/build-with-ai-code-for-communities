"""Chatbot tool-execution tests -- exercised directly against the live database,
independent of any LLM provider (see app.services.chatbot's docstring: grounding comes
from the model only ever seeing real tool output, so this layer being correct is what
actually matters for correctness -- which provider is calling it is a separate concern).
"""

from sqlalchemy import text

from app.services.chatbot_tools import execute_tool
from app.services.ranking import build_ranked_works


def test_search_villages_finds_a_known_village(db):
    result = execute_tool(db, "search_villages", {"query": "Chikkur"})
    assert "matches" in result
    assert any(m["village_name"] == "Chikkur" for m in result["matches"])


def test_search_villages_returns_empty_for_nonsense_query(db):
    result = execute_tool(db, "search_villages", {"query": "zzzznotarealvillagezzzz"})
    assert result["matches"] == []


def test_get_village_detail_for_known_village(db):
    row = db.execute(text("SELECT village_code FROM village_fact WHERE village_name = 'Chikkur' LIMIT 1")).first()
    assert row is not None
    result = execute_tool(db, "get_village_detail", {"village_code": row.village_code})
    assert result["found"] is True
    assert result["village_fact"]["village_name"] == "Chikkur"
    assert "issues" in result and "works" in result


def test_get_village_detail_for_unknown_code_reports_not_found(db):
    result = execute_tool(db, "get_village_detail", {"village_code": 999999999})
    assert result["found"] is False


def test_get_ranked_works_filters_by_theme(db):
    result = execute_tool(db, "get_ranked_works", {"theme": "water", "limit": 5})
    assert result["works"]
    assert all(w["theme"] == "water" for w in result["works"])


def test_get_work_detail_matches_real_ranking(db):
    works = build_ranked_works(db)
    target = works[0]
    result = execute_tool(db, "get_work_detail", {"work_id": target.work_id})
    assert result["found"] is True
    assert result["composite_score"] == round(target.composite_score, 4)
    assert "is_funded_this_cycle" in result


def test_get_work_detail_unknown_id_reports_not_found(db):
    result = execute_tool(db, "get_work_detail", {"work_id": "issue-999999999"})
    assert result["found"] is False


def test_get_citizen_status_unknown_submission(db):
    result = execute_tool(db, "get_citizen_status", {"submission_id": 999999999})
    assert result["found"] is False


def test_get_transparency_summary_returns_real_aggregates(db):
    result = execute_tool(db, "get_transparency_summary", {})
    assert result["total_submissions"] > 0
    assert result["total_issues"] > 0


def test_get_budget_justification_matches_endpoint_shape(db):
    works = build_ranked_works(db)
    result = execute_tool(db, "get_budget_justification", {"work_id": works[0].work_id})
    assert result["theme"] == works[0].theme
    assert "narrative" in result


def test_unknown_tool_name_returns_error_not_exception(db):
    result = execute_tool(db, "not_a_real_tool", {})
    assert "error" in result


def test_bad_input_returns_error_not_exception(db):
    # village_code is required and not int-coercible -- should be caught, not raised
    result = execute_tool(db, "get_village_detail", {"village_code": "not-a-number"})
    assert "error" in result
