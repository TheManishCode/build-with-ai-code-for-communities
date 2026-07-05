"""Phase 6 step 4: auto-draft letter generator. Produces an actual formatted letter the
MP's office could edit and send -- addressed to the real Karnataka department responsible
for the work's theme, citing the same reasoning string (and therefore the same
real-queried numbers) already verified in Phase 3, not a separate hallucination-prone
text generation path.
"""

from __future__ import annotations

from datetime import date

from app.services.ranking import CandidateWork

DEPARTMENT_BY_THEME = {
    "water": "The Executive Engineer, Rural Drinking Water Supply Division / Jal Jeevan Mission Cell, Zilla Panchayat, Bagalkot",
    "road": "The Executive Engineer, Rural Development & Panchayat Raj Engineering Division (PMGSY), Bagalkot",
    "school": "The Deputy Director of Public Instruction, Department of School Education, Bagalkot",
    "health": "The District Health & Family Welfare Officer, Bagalkot",
    "electricity": "The Superintending Engineer, Hubli Electricity Supply Company (HESCOM), Bagalkot Division",
    "sanitation": "The Assistant Executive Engineer, Swachh Bharat Mission (Gramin) Cell, Zilla Panchayat, Bagalkot",
    "other": "The Chief Executive Officer, Zilla Panchayat, Bagalkot",
}

SUBJECT_BY_THEME = {
    "water": "drinking water supply infrastructure",
    "road": "rural road connectivity and repair",
    "school": "school infrastructure",
    "health": "primary health facility",
    "electricity": "electricity supply infrastructure",
    "sanitation": "sanitation and drainage infrastructure",
    "other": "local community infrastructure",
}


def generate_draft_letter(work: CandidateWork, mp_name: str, constituency: str, cost_estimate: int | None) -> dict:
    department = DEPARTMENT_BY_THEME.get(work.theme, DEPARTMENT_BY_THEME["other"])
    subject_topic = SUBJECT_BY_THEME.get(work.theme, SUBJECT_BY_THEME["other"])
    place = work.village_name or "the affected locality"
    today = date.today().strftime("%d-%m-%Y")

    subject = f"Request for sanction of {subject_topic} works at {place}, {constituency} constituency"

    cost_line = (
        f"The estimated cost for this work is approximately Rs. {cost_estimate:,} "
        f"(planning-stage heuristic estimate, not a certified engineering costing)."
        if cost_estimate
        else "A detailed cost estimate is requested from your office/division."
    )

    corroboration_line = (
        f"This request is supported by {work.corroboration_count} citizen report(s) received "
        f"through the People's Priorities constituency feedback system."
        if work.corroboration_count
        else "No direct citizen reports have been received for this specific item, but it has been "
        "identified as a high-priority infrastructure gap through constituency-wide data analysis."
    )

    body = f"""To,
{department}

Subject: {subject}

Sir/Madam,

I am writing to bring to your attention an urgent infrastructure need in {place}, within the {constituency} Lok Sabha constituency, identified through a data-driven review of citizen reports and government infrastructure records.

{work.reasoning}

{corroboration_line} {cost_line}

I would request your office to examine this matter on priority and take necessary action to sanction and execute the required work at the earliest, under the appropriate scheme (MPLADs / departmental budget, as applicable to your division).

I would appreciate a status update on the action taken in this regard.

Thanking you,

Yours sincerely,

{mp_name}
Member of Parliament
{constituency} Constituency

Date: {today}
"""

    return {
        "to": department,
        "subject": subject,
        "body": body,
        "generated_at": today,
    }
