"""Citizen status lookup -- a plain template-filled status string, no model call.

Lets a citizen check what happened to their specific submission: which dedup group
("issue") it was merged into, how many other reports were merged with it, where that
issue currently ranks among all candidate works, and whether it's funded this cycle.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.allocator import run_allocation
from app.services.ranking import build_ranked_works

HIGH_PRIORITY_RANK_PERCENTILE = 0.25  # top quartile by rank, when not funded


@dataclass
class CitizenStatus:
    submission_id: int
    found: bool
    village: str | None = None
    taluk: str | None = None
    theme: str | None = None
    dedup_group_id: int | None = None
    corroboration_count: int | None = None
    current_rank: int | None = None
    total_works_ranked: int | None = None
    is_funded_this_cycle: bool | None = None
    funding_tier: str = "Unknown"
    status_message: str = ""


def _fetch_submission(db: Session, submission_id: int):
    return db.execute(
        text(
            """
            SELECT s.id, s.theme, s.issue_id, s.resolved_lgd_code,
                   v.village_name, sub.subdistrict_name AS taluk
            FROM submission s
            LEFT JOIN lgd_village v ON v.village_code = s.resolved_lgd_code
            LEFT JOIN lgd_subdistrict sub ON sub.subdistrict_code = v.subdistrict_code
            WHERE s.id = :id
            """
        ),
        {"id": submission_id},
    ).first()


def _fetch_issue(db: Session, issue_id: int):
    return db.execute(
        text("SELECT id, corroboration_count FROM issue WHERE id = :id"), {"id": issue_id}
    ).first()


def get_citizen_status(db: Session, submission_id: int, budget: int) -> CitizenStatus:
    row = _fetch_submission(db, submission_id)
    if row is None:
        return CitizenStatus(submission_id=submission_id, found=False, status_message="No submission found with this ID.")

    if row.issue_id is None:
        return CitizenStatus(
            submission_id=submission_id,
            found=True,
            village=row.village_name,
            taluk=row.taluk,
            theme=row.theme,
            funding_tier="Pending Review",
            status_message=(
                f"Your {row.theme} report has been received but has not yet been processed into the "
                f"constituency priority ranking. Please check back later."
            ),
        )

    issue = _fetch_issue(db, row.issue_id)
    corroboration_count = issue.corroboration_count if issue else None

    works = build_ranked_works(db)
    work_id = f"issue-{row.issue_id}"
    rank = None
    total = len(works)
    for i, w in enumerate(works, start=1):
        if w.work_id == work_id:
            rank = i
            break

    allocation = run_allocation(db, budget, candidates=works)
    is_funded = any(it.work.work_id == work_id for it in allocation.selected) if rank is not None else None

    if is_funded:
        tier = "Funded — approved for the current budget cycle"
    elif rank is not None and total and rank <= total * HIGH_PRIORITY_RANK_PERCENTILE:
        tier = "High Priority — ranked in the top quartile, awaiting budget allocation"
    elif rank is not None:
        tier = "Under Review — ranked, but not yet within the funded budget"
    else:
        tier = "Unknown"

    place = row.village_name or "your reported location"
    taluk_txt = f", {row.taluk} taluk" if row.taluk else ""
    rank_txt = f"#{rank} of {total}" if rank is not None else "not yet ranked"
    corrob_txt = (
        f"Your report was merged with {corroboration_count - 1} other report(s) about the same issue "
        f"(total {corroboration_count})."
        if corroboration_count and corroboration_count > 1
        else "Your report has not been corroborated by any other citizen reports yet."
    )
    funded_txt = (
        "This issue IS funded in the current budget cycle."
        if is_funded
        else "This issue is NOT funded in the current budget cycle."
        if is_funded is not None
        else ""
    )

    status_message = (
        f"Your {row.theme} report for {place}{taluk_txt} is part of dedup group #{row.issue_id}. "
        f"{corrob_txt} It currently ranks {rank_txt} among all constituency priority works. "
        f"{funded_txt} Status: {tier}."
    )

    return CitizenStatus(
        submission_id=submission_id,
        found=True,
        village=row.village_name,
        taluk=row.taluk,
        theme=row.theme,
        dedup_group_id=row.issue_id,
        corroboration_count=corroboration_count,
        current_rank=rank,
        total_works_ranked=total,
        is_funded_this_cycle=is_funded,
        funding_tier=tier,
        status_message=status_message,
    )
