import tempfile
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # Only read by the offline app/ingestion/* scripts (run locally against the Dataset/
    # folder, which isn't part of this repo) -- the deployed web service never touches
    # dataset_dir, so it must not be required to construct Settings() or every deploy
    # without it set crashes on import before serving a single request.
    dataset_dir: Path | None = None
    constituency_name: str = "BAGALKOT"
    constituency_district: str = "Bagalkot"
    anthropic_api_key: str | None = None  # Backup model -- explain() falls back to a template
    # explanation whenever no key succeeds, same as any other generation failure.
    nvidia_nim_api_key: str | None = None  # Primary/base model (NVIDIA NIM, OpenAI-compatible
    # API surface), tried before the Anthropic backup.
    nvidia_model: str = "nvidia/nemotron-3-ultra-550b-a55b"  # NVIDIA's flagship (550B) --
    # verified callable for this account; "nvidia/llama-3.1-nemotron-70b-instruct" is listed
    # in the catalog but returns 404 "Function not found for account" when actually called.

    # Comma-separated list, e.g. "http://localhost:5173,https://peoples-priorities.example.org"
    # -- configurable so a real deployment doesn't need a code change to add its own origin.
    cors_origins: str = "http://localhost:5173"

    # Where citizen-submitted photos (POST /submissions) are stored when R2 (below) isn't
    # configured. Defaults to the OS temp dir rather than inside the app source tree -- many
    # deploy platforms ship app source read-only, and the temp dir is reliably writable
    # (though ephemeral/non-persistent across redeploys). This is the local-dev/test path;
    # a real deployment should set the R2 variables below instead.
    upload_dir: Path = Path(tempfile.gettempdir()) / "peoples_priorities_uploads"

    # Cloudflare R2 (S3-compatible) -- persistent photo storage for a real deployment.
    # All optional, same "degrade rather than crash" posture as the LLM keys above:
    # app.services.storage falls back to local disk (upload_dir) when these aren't set.
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket_name: str | None = None
    r2_public_base_url: str | None = None  # public URL prefix the uploaded object is served from

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def r2_configured(self) -> bool:
        return bool(
            self.r2_account_id and self.r2_access_key_id and self.r2_secret_access_key
            and self.r2_bucket_name and self.r2_public_base_url
        )


settings = Settings()
