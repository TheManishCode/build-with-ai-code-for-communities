"""Live intake endpoint tests -- POST /submissions runs the real NLP pipeline (translate/
classify/place-match/embed) and rebuilds real issue clusters against the live database, same
no-mock-DB posture as every other test in this suite (see README's Testing section). Every
test that inserts a submission removes it (and rebuilds issues again) in a finally block so
the seed dataset stays pristine for other tests and for anyone re-running the suite against
the shared demo DB.
"""

from __future__ import annotations

import base64

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.submissions import UPLOAD_DIR
from app.ingestion import build_issues
from app.main import app

client = TestClient(app)

# Minimal valid 1x1 red JPEG.
TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/"
    "2wBDAQMDAwQDBAgEBAgQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/wAARCAABAAEDASIAAhEBAxEB/"
    "8QAFQABAQAAAAAAAAAAAAAAAAAAAAj/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/"
    "9oADAMBAAIRAxEAPwCdABmX/9k="
)


def _delete_submission_and_rebuild(db, submission_id: int) -> None:
    db.execute(text("DELETE FROM submission WHERE id = :id"), {"id": submission_id})
    db.commit()
    build_issues.run()


def test_text_submission_resolves_known_village_and_theme(db):
    raw_text = "No drinking water in Kaladgi village, the borewell has stopped working."
    resp = client.post("/submissions", data={"channel": "text", "language": "en", "raw_text": raw_text})
    assert resp.status_code == 201
    body = resp.json()
    try:
        assert body["theme"] == "water"
        assert body["village_name"] == "Kaladgi"
        assert body["resolved_village_code"] is not None
        assert body["issue_id"] is not None
        assert body["translated_text"] == raw_text  # unchanged for language == "en"
    finally:
        _delete_submission_and_rebuild(db, body["submission_id"])


def test_submission_merges_into_existing_issue_cluster(db):
    """A near-duplicate of an existing corroborated issue should join that issue's cluster,
    not start a new singleton -- exercises the same dedup clustering as the seed data."""
    row = db.execute(
        text("SELECT representative_text FROM issue WHERE corroboration_count >= 2 LIMIT 1")
    ).first()
    assert row is not None, "expected at least one corroborated issue in seed data"

    resp = client.post("/submissions", data={"channel": "text", "language": "en", "raw_text": row.representative_text})
    assert resp.status_code == 201
    body = resp.json()
    try:
        new_issue = db.execute(
            text("SELECT corroboration_count FROM issue WHERE id = :id"), {"id": body["issue_id"]}
        ).first()
        assert new_issue is not None
        assert new_issue.corroboration_count >= 3  # original 2+ plus this new duplicate
    finally:
        _delete_submission_and_rebuild(db, body["submission_id"])


def test_kannada_voice_submission_is_translated_and_resolved(db):
    resp = client.post(
        "/submissions",
        data={
            "channel": "voice",
            "language": "kn",
            "raw_text": "ಕಾಲಡಗಿ ಗ್ರಾಮದಲ್ಲಿ ಕುಡಿಯುವ ನೀರಿನ ಸಮಸ್ಯೆ ಇದೆ, ಕೊಳವೆ ಬಾವಿ ಕೆಟ್ಟಿದೆ.",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    try:
        assert body["theme"] == "water"
        assert body["village_name"] == "Kaladgi"
        assert body["translated_text"]  # non-empty
        assert "kaladgi" in body["translated_text"].lower() or "water" in body["translated_text"].lower()
    finally:
        _delete_submission_and_rebuild(db, body["submission_id"])


def test_photo_upload_is_stored_and_served(db):
    resp = client.post(
        "/submissions",
        data={"channel": "photo", "language": "en", "raw_text": "Photo evidence of a broken transformer near Khajagal village."},
        files={"photo": ("evidence.jpg", TINY_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 201
    body = resp.json()
    try:
        assert body["photo_url"] is not None
        served = client.get(body["photo_url"])
        assert served.status_code == 200
        assert served.content == TINY_JPEG
    finally:
        _delete_submission_and_rebuild(db, body["submission_id"])
        filename = body["photo_url"].rsplit("/", 1)[-1]
        (UPLOAD_DIR / filename).unlink(missing_ok=True)


def test_empty_text_rejected():
    resp = client.post("/submissions", data={"channel": "text", "raw_text": "   "})
    assert resp.status_code == 422


def test_oversized_text_rejected():
    resp = client.post("/submissions", data={"channel": "text", "raw_text": "a" * 2001})
    assert resp.status_code == 422


def test_invalid_channel_rejected():
    resp = client.post("/submissions", data={"channel": "carrier_pigeon", "raw_text": "test"})
    assert resp.status_code == 422


def test_non_image_photo_rejected():
    resp = client.post(
        "/submissions",
        data={"channel": "photo", "raw_text": "test"},
        files={"photo": ("evil.txt", b"not an image", "text/plain")},
    )
    assert resp.status_code == 422
