"""Cluster all submissions into deduplicated Issues (Phase 2 step 4) and link each
submission back to its issue via submission.issue_id.

Re-runnable: clears existing issues/links first so reruns don't accumulate duplicates.
"""

from __future__ import annotations

from sqlalchemy import update

from app.core.db import SessionLocal
from app.models.submission import Issue, Submission
from app.services.dedup import cluster_submissions


def run() -> None:
    with SessionLocal() as db:
        rows = db.query(Submission).filter(Submission.embedding.is_not(None)).all()
        submissions = [
            {
                "id": s.id,
                "theme": s.theme,
                "resolved_lgd_code": s.resolved_lgd_code,
                "text": s.translated_text or s.raw_text,
                "embedding": s.embedding,
            }
            for s in rows
        ]
        print(f"clustering {len(submissions)} submissions...")

        clusters = cluster_submissions(submissions)
        print(f"formed {len(clusters)} issues")

        # Reset: unlink submissions and clear issues so this script is idempotent.
        db.execute(update(Submission).values(issue_id=None))
        db.query(Issue).delete()
        db.commit()

        singleton_count = 0
        corroborated_count = 0
        for c in clusters:
            issue = Issue(
                theme=c["theme"],
                village_code=c["village_code"],
                representative_text=c["representative_text"],
                corroboration_count=len(c["member_ids"]),
            )
            db.add(issue)
            db.flush()  # get issue.id
            db.execute(
                update(Submission).where(Submission.id.in_(c["member_ids"])).values(issue_id=issue.id)
            )
            if len(c["member_ids"]) == 1:
                singleton_count += 1
            else:
                corroborated_count += 1
        db.commit()

        print(f"issues with corroboration_count == 1 (singleton reports): {singleton_count}")
        print(f"issues with corroboration_count >= 2 (corroborated): {corroborated_count}")

        top = (
            db.query(Issue)
            .order_by(Issue.corroboration_count.desc())
            .limit(5)
            .all()
        )
        print("\ntop issues by corroboration:")
        for i in top:
            print(f"  [{i.theme.value}] village={i.village_code} corroboration={i.corroboration_count}: {i.representative_text[:90]}")


if __name__ == "__main__":
    run()
