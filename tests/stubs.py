"""Minimal stand-ins for discord objects, so event handlers can be tested
without a gateway connection. Only the attributes John Bot actually touches
are implemented.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace


class FakePermissions:
    def __init__(self, **values: bool) -> None:
        self._values = {
            "view_channel": True,
            "send_messages": True,
            "embed_links": True,
            "manage_roles": True,
        }
        self._values.update(values)

    def __getattr__(self, name: str) -> bool:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._values.get(name, False)


@dataclass(frozen=True)
class FakeRole:
    id: int
    name: str = "Member"
    position: int = 1
    managed: bool = False
    default: bool = False

    def is_default(self) -> bool:
        return self.default

    def __ge__(self, other: "FakeRole") -> bool:  # noqa: D105
        return self.position >= other.position

    def __le__(self, other: "FakeRole") -> bool:  # noqa: D105
        return self.position <= other.position

    def __gt__(self, other: "FakeRole") -> bool:  # noqa: D105
        return self.position > other.position

    def __lt__(self, other: "FakeRole") -> bool:  # noqa: D105
        return self.position < other.position


class FakeChannel:
    def __init__(
        self, channel_id: int = 500, name: str = "welcome", **perms: bool
    ) -> None:
        self.id = channel_id
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.sent: list[dict] = []
        self.permissions = FakePermissions(**perms)

    async def send(self, **kwargs) -> SimpleNamespace:
        self.sent.append(kwargs)
        return SimpleNamespace(id=len(self.sent))

    def permissions_for(self, member) -> FakePermissions:
        return self.permissions


class FakeMember:
    def __init__(self, member_id: int = 100, name: str = "Newbie") -> None:
        self.id = member_id
        self.bot = False
        self.display_name = name
        self.mention = f"<@{member_id}>"
        self.display_avatar = SimpleNamespace(url="https://cdn.example/avatar.png")
        self.activities: list = []
        self.added_roles: list[FakeRole] = []
        self.removed_roles: list[FakeRole] = []
        self.guild_permissions = FakePermissions(manage_roles=True)
        self.top_role = FakeRole(999, "John Bot", position=50)
        self.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.guild = None

    async def add_roles(self, role: FakeRole, reason: str | None = None) -> None:
        self.added_roles.append(role)

    async def remove_roles(self, role: FakeRole, reason: str | None = None) -> None:
        self.removed_roles.append(role)


class FakeGuild:
    def __init__(self, guild_id: int = 1, name: str = "Test Server") -> None:
        self.id = guild_id
        self.name = name
        self.member_count = 5
        self.icon = None
        self.system_channel: FakeChannel | None = None
        self.channels: dict[int, FakeChannel] = {}
        self.roles: dict[int, FakeRole] = {}
        self.me = FakeMember(999, "John Bot")

    def add_channel(self, channel: FakeChannel) -> FakeChannel:
        self.channels[channel.id] = channel
        return channel

    def add_role(self, role: FakeRole) -> FakeRole:
        self.roles[role.id] = role
        return role

    def get_channel(self, channel_id: int | None):
        if channel_id is None:
            return None
        return self.channels.get(channel_id)

    def get_role(self, role_id: int | None):
        if role_id is None:
            return None
        return self.roles.get(role_id)


class FakeBot:
    """Enough of a bot for cog __init__ methods and their settings lookups."""

    def __init__(self, store, config) -> None:
        self.store = store
        self.config = config
