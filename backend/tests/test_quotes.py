"""Phase 7 ("In Their Words") tests -- this is a pure data join, so the bar is byte-identical
equality with the stored submission row, not "looks plausible"."""

from sqlalchemy import text

from app.services.quotes import MAX_QUOTES, get_source_quotes, parse_issue_id
from app.services.ranking import build_ranked_works


def test_parse_issue_id():
    assert parse_issue_id("issue-42") == 42
    assert parse_issue_id("gap-598748-water") is None
    assert parse_issue_id("issue-not-a-number") is None


def test_gap_sourced_works_have_no_quotes(db):
    works = build_ranked_works(db)
    gap_works = [w for w in works if w.source == "gap"]
    assert gap_works, "expected at least one gap-only silent-need candidate in real data"
    for w in gap_works[:20]:
        assert get_source_quotes(db, w) == []


def test_quotes_are_byte_identical_to_stored_submission(db):
    works = build_ranked_works(db)
    issue_works = [w for w in works if w.source == "issue"]
    assert issue_works

    checked = 0
    for w in issue_works:
        quotes = get_source_quotes(db, w)
        if not quotes:
            continue
        assert len(quotes) <= MAX_QUOTES
        for q in quotes:
            row = db.execute(
                text("SELECT raw_text, language, translated_text, resolved_lgd_code FROM submission WHERE id = :id"),
                {"id": q["submission_id"]},
            ).first()
            assert row is not None
            # byte-identical, not paraphrased/altered/truncated
            assert q["original_text"] == row.raw_text
            assert q["original_language"] == row.language
            assert q["translated_text"] == row.translated_text
            checked += 1
    assert checked > 0, "no issue-sourced quotes were found to check against the DB"


def test_quotes_belong_to_the_works_issue(db):
    """Every returned submission must actually be a member of the SAME issue the work
    represents -- not just any submission for that village/theme."""
    works = build_ranked_works(db)
    issue_works = [w for w in works if w.source == "issue"]

    checked = 0
    for w in issue_works[:30]:
        issue_id = parse_issue_id(w.work_id)
        quotes = get_source_quotes(db, w)
        for q in quotes:
            row = db.execute(
                text("SELECT issue_id FROM submission WHERE id = :id"), {"id": q["submission_id"]}
            ).first()
            assert row.issue_id == issue_id
            checked += 1
    assert checked > 0
