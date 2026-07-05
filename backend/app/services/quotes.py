""""In Their Words" -- pure data join, no model call. For a ranked work backed by
a clustered Issue, return up to 3 of the original citizen submissions that fed it, so the
MP's office can see the actual voice behind a score rather than just a paraphrase.

Deliberately NOT a text-generation step: original_text/translated_text are read verbatim
from the submission table (see test_quotes.py, which asserts byte-identical equality with
the stored row), and gap-only "silent need" candidates (source="gap") correctly return an
empty list -- they have no issue and therefore no submissions to quote, by construction.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.ranking import CandidateWork

MAX_QUOTES = 3


def parse_issue_id(work_id: str) -> int | None:
    """work_id for issue-backed candidates is always formatted "issue-{issue.id}" by
    app.services.ranking.build_ranked_works -- this is the one place that coupling is
    made explicit, so if that format ever changes, this is the only place to update."""
    if not work_id.startswith("issue-"):
        return None
    try:
        return int(work_id.split("-", 1)[1])
    except ValueError:
        return None


def get_source_quotes(db: Session, work: CandidateWork, limit: int = MAX_QUOTES) -> list[dict]:
    if work.source != "issue":
        return []  # gap-only candidates have no backing issue/submissions to quote

    issue_id = parse_issue_id(work.work_id)
    if issue_id is None:
        return []

    rows = db.execute(
        text(
            """
            SELECT s.id AS submission_id, v.village_name, s.raw_text, s.language, s.translated_text
            FROM submission s
            LEFT JOIN lgd_village v ON v.village_code = s.resolved_lgd_code
            WHERE s.issue_id = :issue_id
            ORDER BY s.id
            LIMIT :limit
            """
        ),
        {"issue_id": issue_id, "limit": limit},
    ).all()

    return [
        {
            "submission_id": r.submission_id,
            "village": r.village_name,
            "original_text": r.raw_text,
            "original_language": r.language,
            "translated_text": r.translated_text,
        }
        for r in rows
    ]
