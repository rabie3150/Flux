"""Flux application configuration."""

import secrets
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All Flux configuration loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    flux_env: str = Field(default="development", alias="FLUX_ENV")
    flux_master_key: str = Field(default="", alias="FLUX_MASTER_KEY")

    # Database
    database_url: str = Field(
        default="sqlite:///~/flux/app.db",
        alias="DATABASE_URL",
    )
    quran_text_db_url: str = Field(
        default="sqlite:///~/flux/quran_text.db",
        alias="QURAN_TEXT_DB_URL",
    )

    # Storage
    storage_path: Path = Field(
        default=Path("/storage/emulated/0/Flux"),
        alias="STORAGE_PATH",
    )
    storage_budget_gb: int = Field(default=5, alias="STORAGE_BUDGET_GB")

    # Notifications
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")

    # Remote access
    flux_remote_key: str = Field(default="", alias="FLUX_REMOTE_KEY")
    flux_public_url: str = Field(default="", alias="FLUX_PUBLIC_URL")

    # APIs
    pexels_api_key: str = Field(default="", alias="PEXELS_API_KEY")
    unsplash_access_key: str = Field(default="", alias="UNSPLASH_ACCESS_KEY")
    youtube_client_secrets_path: Path = Field(
        default=Path("~/flux/secrets/youtube_client_secret.json"),
        alias="YOUTUBE_CLIENT_SECRETS_PATH",
    )

    @field_validator("storage_path", "youtube_client_secrets_path", mode="before")
    @classmethod
    def expand_user_path(cls, v: str) -> Path:
        return Path(v).expanduser()

    @property
    def is_production(self) -> bool:
        return self.flux_env.lower() == "production"


def generate_master_key() -> str:
    """Generate a new Fernet-compatible master key."""
    return secrets.token_urlsafe(32)


settings = Settings()
