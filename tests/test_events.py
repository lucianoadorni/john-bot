"""End-to-end (offline) tests for the three features, driven by fake objects.

These call the real listeners with fake guild/member/channel objects, so the
embed construction, permission checks and role calls are exercised for real.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import discord

from johnbot.cogs.streams import StreamAlerts
from johnbot.cogs.welcome import Welcome
from johnbot.config import Config
from johnbot.storage import GuildConfig, GuildStore
from tests.stubs import FakeBot, FakeChannel, FakeGuild, FakeMember, FakeRole

WELCOME_CHANNEL = 500
STREAM_CHANNEL = 501
MEMBER_ROLE = 700


class EventTestBase(unittest.IsolatedAsyncioTestCase):
    def build(self, *, with_role: bool = True, stream: bool = True) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

        self.guild = FakeGuild()
        self.welcome_channel = self.guild.add_channel(FakeChannel(WELCOME_CHANNEL))
        self.stream_channel = self.guild.add_channel(FakeChannel(STREAM_CHANNEL, "streams"))
        self.role = self.guild.add_role(FakeRole(MEMBER_ROLE, "Member", position=5))

        defaults = GuildConfig(
            welcome_channel_id=WELCOME_CHANNEL,
            member_role_id=MEMBER_ROLE if with_role else None,
            stream_channel_id=STREAM_CHANNEL if stream else None,
        )
        config = Config(
            token="fake",
            data_dir=Path(self._tmp.name),
            stream_alert_cooldown=3600,
        )
        self.store = GuildStore(Path(self._tmp.name) / "guilds.json", defaults=defaults)
        self.bot = FakeBot(self.store, config)

    def member(self, member_id: int = 100, name: str = "Newbie") -> FakeMember:
        member = FakeMember(member_id, name)
        member.guild = self.guild
        return member


class WelcomeEventTests(EventTestBase):
    async def test_join_posts_welcome_and_adds_role(self):
        self.build()
        member = self.member()

        await Welcome(self.bot).on_member_join(member)

        self.assertEqual(len(self.welcome_channel.sent), 1)
        embed = self.welcome_channel.sent[0]["embed"]
        self.assertEqual(embed.title, "Welcome to Test Server!")
        self.assertIn(member.mention, embed.description)
        self.assertIn("Test Server", embed.description)
        self.assertIn("#5", embed.description)
        self.assertTrue(embed.thumbnail.url.endswith("avatar.png"))
        self.assertEqual([role.id for role in member.added_roles], [MEMBER_ROLE])
        # No failure field when everything worked.
        self.assertNotIn("Autorole failed", [field.name for field in embed.fields])

    async def test_role_above_bot_role_is_reported_not_raised(self):
        self.build()
        high_role = self.guild.add_role(FakeRole(MEMBER_ROLE, "Admin", position=99))
        self.guild.roles[MEMBER_ROLE] = high_role
        member = self.member()

        await Welcome(self.bot).on_member_join(member)

        self.assertEqual(member.added_roles, [])
        embed = self.welcome_channel.sent[0]["embed"]
        fields = {field.name.removeprefix("⚠️ "): field.value for field in embed.fields}
        self.assertIn("Autorole failed", fields)
        self.assertIn("higher than my top role", fields["Autorole failed"])

    async def test_missing_manage_roles_permission_is_reported(self):
        self.build()
        self.guild.me.guild_permissions = type("Perms", (), {"manage_roles": False})()
        member = self.member()

        await Welcome(self.bot).on_member_join(member)

        self.assertEqual(member.added_roles, [])
        fields = {
            f.name.removeprefix("⚠️ "): f.value for f in self.welcome_channel.sent[0]["embed"].fields
        }
        self.assertIn("Manage Roles", fields["Autorole failed"])

    async def test_bots_are_ignored(self):
        self.build()
        member = self.member()
        member.bot = True

        await Welcome(self.bot).on_member_join(member)

        self.assertEqual(self.welcome_channel.sent, [])
        self.assertEqual(member.added_roles, [])

    async def test_falls_back_to_system_channel(self):
        self.build()
        self.store.set(
            1,
            GuildConfig(
                welcome_channel_id=None,
                member_role_id=MEMBER_ROLE,
                stream_channel_id=STREAM_CHANNEL,
            ),
        )
        self.guild.system_channel = self.welcome_channel
        member = self.member()

        await Welcome(self.bot).on_member_join(member)

        self.assertEqual(len(self.welcome_channel.sent), 1)

    async def test_custom_message_tokens_are_rendered(self):
        self.build()
        self.store.set(
            1,
            GuildConfig(
                welcome_channel_id=WELCOME_CHANNEL,
                member_role_id=MEMBER_ROLE,
                stream_channel_id=STREAM_CHANNEL,
                welcome_message="Yo {member} — {guild} now has {count} humans",
            ),
        )
        member = self.member()

        await Welcome(self.bot).on_member_join(member)

        description = self.welcome_channel.sent[0]["embed"].description
        self.assertEqual(description, "Yo <@100> — Test Server now has 5 humans")


class StreamEventTests(EventTestBase):
    def streaming_activity(self, url: str, title: str = "Ranked grind"):
        return SimpleNamespace(
            type=discord.ActivityType.streaming, url=url, name=title, details=title
        )

    async def test_new_stream_is_announced_with_link(self):
        self.build()
        cog = StreamAlerts(self.bot)
        member = self.member()
        before = self.member()
        before.activities = []
        member.activities = [self.streaming_activity("https://twitch.tv/lucia")]

        await cog.on_presence_update(before, member)

        self.assertEqual(len(self.stream_channel.sent), 1)
        embed = self.stream_channel.sent[0]["embed"]
        self.assertEqual(embed.url, "https://twitch.tv/lucia")
        self.assertIn(member.display_name, embed.title)
        self.assertEqual([field.name for field in embed.fields], ["Watch"])
        self.assertFalse(self.stream_channel.sent[0]["allowed_mentions"].everyone)

    async def test_already_streaming_is_not_re_announced(self):
        self.build()
        cog = StreamAlerts(self.bot)
        before = self.member()
        before.activities = [self.streaming_activity("https://twitch.tv/lucia")]
        member = self.member()
        member.activities = [self.streaming_activity("https://twitch.tv/lucia")]

        await cog.on_presence_update(before, member)

        self.assertEqual(self.stream_channel.sent, [])

    async def test_cooldown_suppresses_stop_start_flapping(self):
        self.build()
        cog = StreamAlerts(self.bot)
        url = "https://twitch.tv/lucia"

        live = self.member()
        live.activities = [self.streaming_activity(url)]
        offline = self.member()
        offline.activities = []

        await cog.on_presence_update(offline, live)  # first: announced
        await cog.on_presence_update(live, offline)  # stop: nothing
        await cog.on_presence_update(offline, live)  # restart: cooldown

        self.assertEqual(len(self.stream_channel.sent), 1)

    async def test_placeholder_url_is_ignored(self):
        self.build()
        cog = StreamAlerts(self.bot)
        before = self.member()
        before.activities = []
        member = self.member()
        member.activities = [self.streaming_activity("https://www.twitch.tv/directory")]

        await cog.on_presence_update(before, member)

        self.assertEqual(self.stream_channel.sent, [])

    async def test_no_stream_channel_means_silence(self):
        self.build(stream=False)
        cog = StreamAlerts(self.bot)
        before = self.member()
        before.activities = []
        member = self.member()
        member.activities = [self.streaming_activity("https://twitch.tv/lucia")]

        await cog.on_presence_update(before, member)

        self.assertEqual(self.stream_channel.sent, [])


if __name__ == "__main__":
    unittest.main()
