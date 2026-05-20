"""Centralised settings loaded from .env via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    tg_api_id: int = Field(default=0)
    tg_api_hash: str = Field(default="")
    tg_phone: str = Field(default="")
    tg_session_name: str = Field(default="telegram_watcher")

    claude_model: str = Field(default="claude-haiku-4-5")

    db_path: str = Field(default="data/telegram_watcher.db")

    dashboard_host: str = Field(default="127.0.0.1")
    dashboard_port: int = Field(default=8000)

    digest_cron_hour: int = Field(default=8)
    local_tz: str = Field(default="Europe/Kyiv")

    watched_groups_init: str = Field(default="")

    max_msgs_per_group: int = Field(default=500)
    classify_concurrency: int = Field(default=4)

    realtime_ai_filter: bool = Field(default=True)

    min_group_text_len: int = Field(default=30)

    # Optional Bearer token for the dashboard. Required when dashboard_host is
    # not a loopback address (see Settings.validate_runtime + supervisor.py).
    dashboard_token: str = Field(default="")

    @property
    def db_absolute_path(self) -> Path:
        path = Path(self.db_path)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def sessions_dir(self) -> Path:
        return PROJECT_ROOT / "data" / "sessions"

    @property
    def session_file(self) -> Path:
        return self.sessions_dir / self.tg_session_name

    def validate_runtime(self) -> None:
        """Fail fast at process start with a friendly message.

        Pydantic field defaults stay permissive so unit tests and stand-alone
        Settings(...) construction keep working; instead we enforce required
        secrets at the supervisor / setup_session entrypoints.
        """
        problems: list[str] = []
        if not self.tg_api_id or self.tg_api_id <= 0:
            problems.append("TG_API_ID must be a positive integer")
        if not self.tg_api_hash or len(self.tg_api_hash) < 32:
            problems.append("TG_API_HASH must be the 32-char hex string from my.telegram.org")
        if not self.tg_phone or not self.tg_phone.startswith("+"):
            problems.append("TG_PHONE must be in international format, e.g. +380XXXXXXXXX")
        if problems:
            joined = "\n  - ".join(problems)
            raise RuntimeError(
                f"Invalid .env configuration:\n  - {joined}\n"
                f"See .env.example for the full list of required variables."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
