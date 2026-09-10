"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

REQUIRED_VARS = (
    "TG_TOKEN",
    "TG_ADMIN_ID",
    "RDS_HOST",
    "RDS_PASSWORD",
    "TXI_USERNAME",
    "TXI_PASSWORD",
)


class ConfigError(ValueError):
    """Raised when the environment is incomplete or malformed."""


@dataclass(frozen=True, slots=True)
class Config:
    """Immutable application settings."""

    tg_token: str
    tg_admin_id: int
    redis_host: str
    redis_password: str
    taxi_username: str
    taxi_password: str
    update_period: int = 25 * 60  # seconds between taxi cabinet polls
    tg_log_path: str | None = None
    redis_port: int = 6379
    redis_db: int = 0
    debug_html_dir: str = "/tmp/taxi_debug"
    bot_secret_code: str | None = None
    log_level: str = "INFO"
    timezone: str = "Europe/Moscow"

    @property
    def is_private(self) -> bool:
        """Whether new users must enter a secret code before getting access."""
        return bool(self.bot_secret_code)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        """Build the configuration from ``env`` (defaults to ``os.environ``)."""
        env = os.environ if env is None else env

        missing = [name for name in REQUIRED_VARS if not env.get(name)]
        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

        try:
            return cls(
                tg_token=env["TG_TOKEN"],
                tg_admin_id=int(env["TG_ADMIN_ID"]),
                redis_host=env["RDS_HOST"],
                redis_password=env["RDS_PASSWORD"],
                taxi_username=env["TXI_USERNAME"],
                taxi_password=env["TXI_PASSWORD"],
                update_period=int(env.get("TXI_UPDATE_PERIOD") or 25) * 60,
                tg_log_path=env.get("TG_LOG") or None,
                redis_port=int(env.get("RDS_PORT") or 6379),
                redis_db=int(env.get("RDS_DB") or 0),
                debug_html_dir=env.get("DEBUG_HTML_DIR") or "/tmp/taxi_debug",
                bot_secret_code=env.get("BOT_SECRET_CODE") or None,
                log_level=(env.get("LOG_LEVEL") or "INFO").upper(),
                timezone=env.get("BOT_TIMEZONE") or "Europe/Moscow",
            )
        except ValueError as exc:
            raise ConfigError(f"Invalid environment value: {exc}") from exc
