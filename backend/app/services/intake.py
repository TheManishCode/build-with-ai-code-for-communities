"""Live citizen submission intake.

Runs a single submission through the same NLP pipeline used by
app.ingestion.seed_submissions (translate -> classify -> extract place -> resolve village ->
geocode -> embed), persists it, then rebuilds issue clusters so the new report is reflected
in ranking immediately. The rebuild is a full re-cluster (app.ingestion.build_issues.run())
rather than an incremental update -- cheap at this dataset's scale (embeddings are already
computed and stored, so no model calls happen during the rebuild) and guarantees the live
path never drifts from the batch/seed clustering logic.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ingestion import build_issues
from app.models.lgd import LGDVillage
from app.models.submission import Channel, Submission
from app.services import nlp
from app.services.embeddings import embed


@dataclass
class IntakeResult:
    submission: Submission
    village_name: str | None


def process_submission(
    db: Session,
    *,
    channel: Channel,
    raw_text: str,
    language: str,
    photo_path: str | None = None,
) -> IntakeResult:
    translated_text = nlp.translate(raw_text, language)
    theme = nlp.classify_theme(translated_text)

    place_text = nlp.extract_place_mention(translated_text)
    village_code, match_score = nlp.match_place_to_village(db, place_text)
    if village_code is None:
        place_text, village_code, match_score = nlp.gazetteer_match(db, translated_text)
    lat, lng = nlp.village_lat_lng(db, village_code)
    embedding = embed(translated_text)

    submission = Submission(
        channel=channel,
        raw_text=raw_text,
        language=language,
        translated_text=translated_text,
        theme=theme,
        place_text=place_text,
        resolved_lgd_code=village_code,
        place_match_score=match_score,
        lat=lat,
        lng=lng,
        embedding=embedding,
        photo_path=photo_path,
    )
    db.add(submission)
    db.commit()

    # Runs in its own session/transaction; committed there, so the refresh below (same
    # connection, READ COMMITTED) picks up the issue_id it assigned to this submission.
    build_issues.run()
    db.refresh(submission)

    village_name = db.get(LGDVillage, village_code).village_name if village_code is not None else None
    return IntakeResult(submission=submission, village_name=village_name)
