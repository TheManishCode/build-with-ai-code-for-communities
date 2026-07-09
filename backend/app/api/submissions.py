"""Live citizen intake: POST /submissions.

Accepts text directly, voice as browser-transcribed text (channel="voice", no server-side
ASR), and an optional photo attachment (stored and served back as a URL, not
vision-analyzed). Runs the submission through app.services.intake synchronously -- fine at
this dataset's scale (see that module's docstring) -- so the response reflects the
resolved theme/village and the newly-updated issue cluster immediately.

This is the API's only public write path, so it carries the API's only abuse-surface
hardening: per-IP rate limiting (app.core.rate_limit) and photo validation that checks the
file's actual magic bytes, not just the client-supplied Content-Type header (which is
trivially spoofable).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.submission import Channel
from app.services.intake import process_submission
from app.services.storage import save_photo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/submissions", tags=["submissions"])

UPLOAD_DIR = settings.upload_dir

# Local disk is only ever touched as the R2 fallback (see app.services.storage) -- still
# created eagerly so the fallback path works even when R2 IS configured but a given photo
# upload fails for some other reason before storage.save_photo is reached. A failure here
# (read-only filesystem, permission error) must not crash the whole app at import time --
# it should only disable the local-disk fallback. STORAGE_AVAILABLE gates both the
# StaticFiles mount in app.main and the photo-handling branch below.
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR_AVAILABLE = True
except OSError:
    logger.warning("Could not create upload directory %s -- local-disk photo storage unavailable.", UPLOAD_DIR, exc_info=True)
    UPLOAD_DIR_AVAILABLE = False

STORAGE_AVAILABLE = settings.r2_configured or UPLOAD_DIR_AVAILABLE


def _to_photo_url(photo_path: str | None) -> str | None:
    if not photo_path:
        return None
    return photo_path if photo_path.startswith(("http://", "https://")) else f"/uploads/{photo_path}"

MAX_TEXT_LENGTH = 2000
MAX_PHOTO_BYTES = 8 * 1024 * 1024  # 8 MB

# Extension keyed by claimed Content-Type, but never trusted alone -- see _sniff_image_type.
ALLOWED_PHOTO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

# Real file-signature ("magic bytes") checks -- a spoofed Content-Type header alone would
# otherwise let an arbitrary file get written to disk and served back under an image URL.
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_WEBP_RIFF = b"RIFF"
_WEBP_MAGIC = b"WEBP"


def _sniff_image_type(header: bytes) -> str | None:
    if header.startswith(_JPEG_MAGIC):
        return "image/jpeg"
    if header.startswith(_PNG_MAGIC):
        return "image/png"
    if header.startswith(_WEBP_RIFF) and header[8:12] == _WEBP_MAGIC:
        return "image/webp"
    return None


@router.post("", status_code=201)
@limiter.limit("10/minute")
async def submit_report(
    request: Request,  # required by @limiter.limit to key on the client's address
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
        if not STORAGE_AVAILABLE:
            raise HTTPException(status_code=503, detail="Photo uploads are temporarily unavailable; please submit without a photo.")
        if photo.content_type not in ALLOWED_PHOTO_TYPES:
            raise HTTPException(status_code=422, detail="photo must be JPEG, PNG, or WebP")
        contents = await photo.read(MAX_PHOTO_BYTES + 1)
        if len(contents) > MAX_PHOTO_BYTES:
            raise HTTPException(status_code=422, detail="photo must be at most 8MB")
        sniffed_type = _sniff_image_type(contents[:12])
        if sniffed_type is None or sniffed_type != photo.content_type:
            raise HTTPException(status_code=422, detail="photo content does not match a valid JPEG, PNG, or WebP file")
        # Server-generated filename -- never trust the client's original filename (path
        # traversal, collisions) -- extension is derived from the validated content_type.
        filename = f"{uuid.uuid4().hex}{ALLOWED_PHOTO_TYPES[photo.content_type]}"
        photo_path = save_photo(filename, contents, photo.content_type)

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
        "photo_url": _to_photo_url(s.photo_path),
        "issue_id": s.issue_id,
        "created_at": s.created_at.isoformat(),
    }
