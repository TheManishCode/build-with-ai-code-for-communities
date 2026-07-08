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

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
