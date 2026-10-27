"""Environment-driven configuration for John Bot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = BASE_DIR / "data"

DEFAULT_WELCOME_MESSAGE = (
    "Hey {member}, welcome to **{guild}**! You're member #{count} — say hi 👋"
)


def _int_or_none(name: str) -> int | None:
    """Read an optional Discord snowflake from the environment."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"{name} must be a Discord ID (digits only), got {raw!r}. "
            "Enable Developer Mode in Discord, right-click the item, Copy ID."
        ) from exc


def _int_or(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a whole number, got {raw!r}") from exc


@dataclass(frozen=True)
class Config:
    """Everything the bot needs before it connects."""

    token: str
    guild_id: int | None = None
    data_dir: Path = DEFAULT_DATA_DIR
    welcome_channel_id: int | None = None
    member_role_id: int | None = None
    stream_channel_id: int | None = None
    welcome_message: str = DEFAULT_WELCOME_MESSAGE
    stream_alert_cooldown: int = 3600
    log_level: str = "INFO"


def load_config(env_file: Path | None = None) -> Config:
    """Load .env (if present) and environment variables into a Config."""
    load_dotenv(env_file or BASE_DIR / ".env")

    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN is not set. Copy .env.example to .env and paste the bot "
            "token from https://discord.com/developers/applications -> your app -> Bot."
        )

    data_dir = Path(os.getenv("DATA_DIR", "").strip() or DEFAULT_DATA_DIR).expanduser()
    if not data_dir.is_absolute():
        data_dir = BASE_DIR / data_dir

    return Config(
        token=token,
        guild_id=_int_or_none("GUILD_ID"),
        data_dir=data_dir,
        welcome_channel_id=_int_or_none("WELCOME_CHANNEL_ID"),
        member_role_id=_int_or_none("MEMBER_ROLE_ID"),
        stream_channel_id=_int_or_none("STREAM_CHANNEL_ID"),
        welcome_message=(
            os.getenv("WELCOME_MESSAGE", "").strip() or DEFAULT_WELCOME_MESSAGE
        ),
        stream_alert_cooldown=max(0, _int_or("STREAM_ALERT_COOLDOWN", 3600)),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
    )
