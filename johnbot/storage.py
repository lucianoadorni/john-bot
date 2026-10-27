"""Per-guild settings, persisted to a small JSON file.

The values in .env are the *defaults* every server inherits until an admin
changes them with /setup. Anything saved here wins.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import DEFAULT_WELCOME_MESSAGE

log = logging.getLogger(__name__)


@dataclass
class GuildConfig:
    welcome_channel_id: int | None = None
    member_role_id: int | None = None
    stream_channel_id: int | None = None
    welcome_message: str = DEFAULT_WELCOME_MESSAGE

    @classmethod
    def from_dict(cls, data: dict) -> GuildConfig:
        known = {key: data[key] for key in cls.__dataclass_fields__ if key in data}
        return cls(**known)

    def to_dict(self) -> dict:
        return asdict(self)


class GuildStore:
    """Tiny JSON store: one file, one entry per guild, atomic writes."""

    def __init__(self, path: Path, defaults: GuildConfig | None = None) -> None:
        self.path = path
        self.defaults = defaults or GuildConfig()
        self._data: dict[int, GuildConfig] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("Could not read %s (%s) — starting from defaults", self.path, exc)
            return
        if not isinstance(raw, dict):
            log.warning("%s does not contain an object — ignoring", self.path)
            return
        for key, value in raw.items():
            try:
                self._data[int(key)] = GuildConfig.from_dict(value)
            except (TypeError, ValueError, AttributeError):
                log.warning("Skipping malformed entry for guild %r", key)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {str(guild_id): cfg.to_dict() for guild_id, cfg in self._data.items()},
            indent=2,
            ensure_ascii=False,
        )
        handle, tmp_name = tempfile.mkstemp(dir=self.path.parent, prefix=".guilds-", suffix=".json")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as fh:
                fh.write(payload + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, self.path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise

    def get(self, guild_id: int) -> GuildConfig:
        """Saved settings for a guild, or the .env defaults."""
        return self._data.get(guild_id, self.defaults)

    def set(self, guild_id: int, config: GuildConfig) -> None:
        self._data[guild_id] = config
        self._save()
