from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    dataset_dir: Path
    constituency_name: str = "BAGALKOT"
    constituency_district: str = "Bagalkot"


settings = Settings()
