"""Welcome new members and hand them the autorole."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from ..formatting import render_welcome
from ..storage import GuildConfig, GuildStore

log = logging.getLogger(__name__)


class Welcome(commands.Cog):
    """Greets joins in the welcome channel and applies the member role."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.store: GuildStore = bot.store  # type: ignore[attr-defined]

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return

        config = self.store.get(member.guild.id)
        role_problem = await self._grant_role(member, config)
        await self._send_welcome(member, config, role_problem)

    async def _grant_role(
        self, member: discord.Member, config: GuildConfig
    ) -> str | None:
        """Add the autorole. Returns a human-readable problem, or None."""
        if not config.member_role_id:
            return None

        guild = member.guild
        role = guild.get_role(config.member_role_id)
        if role is None:
            return "the configured role no longer exists in this server"
        if role.is_default():
            return "@everyone cannot be assigned as an autorole"
        if role.managed:
            return f"**{role.name}** is managed by an integration, so it can't be assigned"

        me = guild.me
        if me is None:
            return "I couldn't resolve my own member object"
        if not me.guild_permissions.manage_roles:
            return "I don't have the **Manage Roles** permission"
        if role >= me.top_role:
            return (
                f"**{role.name}** is higher than my top role (**{me.top_role.name}**), "
                "so Discord refuses the change — drag my role above it"
            )

        try:
            await member.add_roles(role, reason="John Bot: autorole on join")
        except discord.Forbidden:
            log.warning("Forbidden adding %s to %s in %s", role, member, guild)
            return "Discord refused the role change (permissions or hierarchy)"
        except discord.HTTPException:
            log.exception("HTTP error adding %s to %s", role, member)
            return "Discord returned an error while adding the role"
        return None

    async def _send_welcome(
        self, member: discord.Member, config: GuildConfig, role_problem: str | None
    ) -> None:
        guild = member.guild
        channel = None
        if config.welcome_channel_id:
            channel = guild.get_channel(config.welcome_channel_id)
            if channel is None:
                log.info(
                    "Welcome channel %s is gone in %s; falling back to the system channel",
                    config.welcome_channel_id,
                    guild,
                )
        if channel is None:
            channel = guild.system_channel
        if channel is None:
            log.info("No welcome channel configured for %s — skipping greeting", guild)
            return

        count = guild.member_count or len(guild.members)
        description = render_welcome(
            config.welcome_message,
            member=member.mention,
            guild=guild.name,
            count=count,
        )

        embed = discord.Embed(
            title=f"Welcome to {guild.name}!",
            description=description,
            colour=discord.Colour.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="Account created",
            value=discord.utils.format_dt(member.created_at, "R"),
            inline=True,
        )
        embed.set_footer(
            text=f"Member #{count} • {guild.name}",
            icon_url=guild.icon.url if guild.icon else None,
        )
        if role_problem:
            embed.add_field(
                name="⚠️ Autorole failed",
                value=role_problem,
                inline=False,
            )

        try:
            await channel.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, roles=False, users=True
                ),
            )
        except discord.Forbidden:
            log.warning("No permission to post the welcome message in %s", channel)
        except discord.HTTPException:
            log.exception("Failed to send the welcome message in %s", channel)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
