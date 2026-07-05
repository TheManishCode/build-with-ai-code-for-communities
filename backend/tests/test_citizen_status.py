"""Phase 9 (Citizen Status Loop) tests -- a template-filled status string, no model call,
so the bar here is that every field traces to real DB/ranking state, same rigor as the
other template-based generators in this project (build_reasoning, build_template_explanation).
"""

from sqlalchemy import text

from app.services.allocator import run_allocation
from app.services.citizen_status import get_citizen_status
from app.services.ranking import build_ranked_works

BAGALKOT_BUDGET = 167_541_747  # Bagalkot's real 18th-LS allocated limit, same as other tests


def test_unknown_submission_id_returns_not_found(db):
    status = get_citizen_status(db, 999_999_999, BAGALKOT_BUDGET)
    assert status.found is False


def test_status_fields_match_real_db_and_ranking(db):
    row = db.execute(text("SELECT id FROM submission WHERE issue_id IS NOT NULL ORDER BY id LIMIT 1")).first()
    assert row is not None, "expected at least one clustered submission in seed data"
    submission_id = row.id

    status = get_citizen_status(db, submission_id, BAGALKOT_BUDGET)
    assert status.found is True

    # dedup_group_id must equal the submission's real issue_id
    real = db.execute(text("SELECT issue_id FROM submission WHERE id = :id"), {"id": submission_id}).first()
    assert status.dedup_group_id == real.issue_id

    # corroboration_count must equal the real issue row's count
    issue_row = db.execute(
        text("SELECT corroboration_count FROM issue WHERE id = :id"), {"id": status.dedup_group_id}
    ).first()
    assert status.corroboration_count == issue_row.corroboration_count

    # current_rank must match this work's actual position in the real ranked list
    works = build_ranked_works(db)
    work_id = f"issue-{status.dedup_group_id}"
    expected_rank = next((i for i, w in enumerate(works, start=1) if w.work_id == work_id), None)
    assert status.current_rank == expected_rank
    assert status.total_works_ranked == len(works)

    # is_funded_this_cycle must match the real allocator result at the same budget
    allocation = run_allocation(db, BAGALKOT_BUDGET)
    expected_funded = any(it.work.work_id == work_id for it in allocation.selected)
    assert status.is_funded_this_cycle == expected_funded


def test_taluk_matches_real_lgd_subdistrict_join(db):
    row = db.execute(
        text(
            """
            SELECT s.id, sub.subdistrict_name AS taluk
            FROM submission s
            JOIN lgd_village v ON v.village_code = s.resolved_lgd_code
            JOIN lgd_subdistrict sub ON sub.subdistrict_code = v.subdistrict_code
            WHERE s.issue_id IS NOT NULL
            LIMIT 1
            """
        )
    ).first()
    assert row is not None, "expected at least one submission resolvable to a taluk"

    status = get_citizen_status(db, row.id, BAGALKOT_BUDGET)
    assert status.taluk == row.taluk


def test_funding_tier_is_funded_when_actually_funded(db):
    allocation = run_allocation(db, BAGALKOT_BUDGET)
    funded_issue_ids = {
        int(it.work.work_id.split("-", 1)[1]) for it in allocation.selected if it.work.source == "issue"
    }
    assert funded_issue_ids, "expected at least one funded issue-based work"

    row = db.execute(
        text("SELECT id FROM submission WHERE issue_id = :iid LIMIT 1"), {"iid": next(iter(funded_issue_ids))}
    ).first()
    status = get_citizen_status(db, row.id, BAGALKOT_BUDGET)
    assert status.is_funded_this_cycle is True
    assert "Funded" in status.funding_tier
    assert "IS funded" in status.status_message


def test_status_message_cites_real_corroboration_count(db):
    """The status_message string must cite the same corroboration_count as the structured
    field -- not a different or rounded number."""
    row = db.execute(
        text("SELECT s.id, i.corroboration_count FROM submission s JOIN issue i ON i.id = s.issue_id WHERE i.corroboration_count > 1 LIMIT 1")
    ).first()
    assert row is not None, "expected at least one corroborated (non-singleton) issue in seed data"

    status = get_citizen_status(db, row.id, BAGALKOT_BUDGET)
    assert str(row.corroboration_count) in status.status_message
    assert str(row.corroboration_count - 1) in status.status_message
