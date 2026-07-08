"""Live citizen intake: POST /submissions.

Accepts text directly, voice as browser-transcribed text (channel="voice", no server-side
ASR), and an optional photo attachment (stored and served back as a URL, not
vision-analyzed). Runs the submission through app.services.intake synchronously -- fine at
this dataset's scale (see that module's docstring) -- so the response reflects the
resolved theme/village and the newly-updated issue cluster immediately.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.submission import Channel
from app.services.intake import process_submission

router = APIRouter(prefix="/submissions", tags=["submissions"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_TEXT_LENGTH = 2000
MAX_PHOTO_BYTES = 8 * 1024 * 1024  # 8 MB
ALLOWED_PHOTO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@router.post("", status_code=201)
async def submit_report(
    db: Session = Depends(get_db),
    channel: str = Form(...),
    raw_text: str = Form(...),
    language: str = Form("en"),
    photo: UploadFile | None = File(None),
) -> dict:
    try:
        channel_enum = Channel(channel)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"channel must be one of {[c.value for c in Channel]}")

    text_value = raw_text.strip()
    if not text_value:
        raise HTTPException(status_code=422, detail="raw_text must not be empty")
    if len(text_value) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=422, detail=f"raw_text must be at most {MAX_TEXT_LENGTH} characters")

    # Not validated against a fixed language list -- nlp.translate() passes this straight
    # to deep-translator, which accepts "auto" plus a wide set of ISO codes; capped to the
    # submission.language column width rather than enumerated.
    language_value = (language or "en").strip().lower()[:16] or "en"

    photo_path: str | None = None
    if photo is not None and photo.filename:
        if photo.content_type not in ALLOWED_PHOTO_TYPES:
            raise HTTPException(status_code=422, detail="photo must be JPEG, PNG, or WebP")
        contents = await photo.read(MAX_PHOTO_BYTES + 1)
        if len(contents) > MAX_PHOTO_BYTES:
            raise HTTPException(status_code=422, detail="photo must be at most 8MB")
        # Server-generated filename -- never trust the client's original filename (path
        # traversal, collisions) -- extension is derived from the validated content_type.
        filename = f"{uuid.uuid4().hex}{ALLOWED_PHOTO_TYPES[photo.content_type]}"
        (UPLOAD_DIR / filename).write_bytes(contents)
        photo_path = filename

    result = process_submission(
        db,
        channel=channel_enum,
        raw_text=text_value,
        language=language_value,
        photo_path=photo_path,
    )
    s = result.submission
    return {
        "submission_id": s.id,
        "channel": s.channel.value,
        "language": s.language,
        "translated_text": s.translated_text,
        "theme": s.theme.value,
        "resolved_village_code": s.resolved_lgd_code,
        "village_name": result.village_name,
        "place_match_score": s.place_match_score,
        "photo_url": f"/uploads/{s.photo_path}" if s.photo_path else None,
        "issue_id": s.issue_id,
        "created_at": s.created_at.isoformat(),
    }
