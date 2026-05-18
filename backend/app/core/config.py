"""Application configuration loaded from environment variables."""
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ----- App -----
    APP_PORT: int = 8000
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    TIMEZONE: str = "UTC"

    # ----- Paths -----
    DATA_DIR: Path = Path("/app/data")

    @property
    def DB_PATH(self) -> Path:
        return self.DATA_DIR / "tracker.db"

    @property
    def DB_URL(self) -> str:
        return f"sqlite+aiosqlite:///{self.DB_PATH}"

    @property
    def SESSIONS_DIR(self) -> Path:
        return self.DATA_DIR / "sessions"

    # ----- Security -----
    SECRET_KEY: str = "CHANGE_ME_GENERATE_A_FERNET_KEY"

    # ----- Home Assistant -----
    HA_WEBHOOK_URL: str = "http://homeassistant.local:8123"
    HA_WEBHOOK_ID: str = "instagram_unfollowers"
    HA_WEBHOOK_ENABLED: bool = True

    # ----- Retention -----
    SNAPSHOT_RETENTION_DAYS: int = 90

    # ----- Instagram API timing -----
    IG_TIME_BETWEEN_CYCLES_MS: int = 1000
    IG_TIME_AFTER_FIVE_CYCLES_MS: int = 10000

    # ----- CORS -----
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8000"]


settings = Settings()
