from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "LeadHunter"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    host: str = "0.0.0.0"
    port: int = 8000

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "leadhunter"
    postgres_password: str = "leadhunter_secret"
    postgres_db: str = "leadhunter"
    database_url: str | None = None

    dgis_api_key: str = ""

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "anthropic/claude-3.5-sonnet"

    playwright_headless: bool = True
    scoring_rules_path: Path = Field(default=PROJECT_ROOT / "app" / "config" / "scoring_rules.json")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        url = self.async_database_url
        return url.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
