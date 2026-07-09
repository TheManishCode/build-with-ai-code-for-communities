"""Photo storage for citizen submissions.

Uploads go to Cloudflare R2 (S3-compatible object storage) when configured -- required
for any real deployment, since app.core.config.settings.upload_dir (the fallback) is a
local/ephemeral disk that's wiped on every redeploy on platforms like Render. Falls back
to local disk when R2 isn't configured, so local dev and the test suite don't need real
R2 credentials -- same "optional key, degrade rather than crash" posture as the LLM keys
in app.core.config.

Callers get back either a bare filename (local disk -- served via the /uploads static
mount in app.main) or a full URL (R2 -- already publicly servable). The two are
distinguished by checking for a URL scheme, not by a separate flag -- see
app.api.submissions._to_photo_url.
"""

from __future__ import annotations

from app.core.config import settings


def save_photo(filename: str, contents: bytes, content_type: str) -> str:
    if settings.r2_configured:
        return _upload_to_r2(filename, contents, content_type)
    (settings.upload_dir / filename).write_bytes(contents)
    return filename


def _upload_to_r2(filename: str, contents: bytes, content_type: str) -> str:
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )
    client.put_object(Bucket=settings.r2_bucket_name, Key=filename, Body=contents, ContentType=content_type)
    return f"{settings.r2_public_base_url.rstrip('/')}/{filename}"
