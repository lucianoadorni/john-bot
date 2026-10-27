"""Post a link whenever someone in the server starts streaming."""

from __future__ import annotations

import logging
import time

import discord
from discord.ext import commands

from ..formatting import StreamLink, parse_stream_url
from ..storage import GuildStore

log = logging.getLogger(__name__)

PLATFORM_COLOURS = {
    "Twitch": 0x9146FF,
    "YouTube": 0xFF0000,
    "Kick": 0x53FC18,
    "Trovo": 0x1FB957,
}

MAX_TRACKED_KEYS = 5000


def live_links(member: discord.Member) -> list[StreamLink]:
    """Stream links currently advertised in this member's presence."""
    links: list[StreamLink] = []
    for activity in member.activities:
        if activity.type is not discord.ActivityType.streaming:
            continue
        title = getattr(activity, "details", None) or getattr(activity, "name", None)
        link = parse_stream_url(getattr(activity, "url", None), title=title)
        if link is not None:
            links.append(link)
    return links


class StreamAlerts(commands.Cog):
    """Watches presences and announces new stream URLs."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.store: GuildStore = bot.store  # type: ignore[attr-defined]
        self.cooldown: int = bot.config.stream_alert_cooldown  # type: ignore[attr-defined]
        self._last_alert: dict[tuple[int, int, str], float] = {}

    @commands.Cog.listener()
    async def on_presence_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        if after.bot or after.guild is None:
            return

        config = self.store.get(after.guild.id)
        if not config.stream_channel_id:
            return

        before_urls = {link.url for link in live_links(before)}
        new_links = [link for link in live_links(after) if link.url not in before_urls]
        if not new_links:
            return

        channel = after.guild.get_channel(config.stream_channel_id)
        if channel is None:
            log.info("Stream channel %s is gone in %s", config.stream_channel_id, after.guild)
            return

        now = time.monotonic()
        for link in new_links[:1]:  # one announcement per presence change
            key = (after.guild.id, after.id, link.url)
            if now - self._last_alert.get(key, float("-inf")) < self.cooldown:
                continue
            self._last_alert[key] = now
            self._prune(now)
            await self._announce(channel, after, link)

    def _prune(self, now: float) -> None:
        if len(self._last_alert) <= MAX_TRACKED_KEYS:
            return
        cutoff = now - self.cooldown
        self._last_alert = {
            key: seen for key, seen in self._last_alert.items() if seen > cutoff
        }

    async def _announce(
        self, channel: discord.abc.Messageable, member: discord.Member, link: StreamLink
    ) -> None:
        embed = discord.Embed(
            title=f"{member.display_name} is live!",
            url=link.url,
            description=link.title or f"Streaming on {link.platform}",
            colour=PLATFORM_COLOURS.get(link.platform, 0x2B2D31),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name=member.display_name,
            icon_url=member.display_avatar.url,
        )
        embed.add_field(name="Watch", value=f"[{link.platform}]({link.url})", inline=True)
        embed.set_footer(text=f"Stream alert • {link.platform}")

        try:
            await channel.send(
                content=f"🔴 {member.mention} just went live",
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, roles=False, users=True
                ),
            )
        except discord.Forbidden:
            log.warning("No permission to announce streams in %s", channel)
        except discord.HTTPException:
            log.exception("Failed to announce a stream in %s", channel)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StreamAlerts(bot))
