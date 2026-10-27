"""Slash commands that configure John Bot per server."""

from __future__ import annotations

import logging
from dataclasses import replace

import discord
from discord import app_commands
from discord.ext import commands

from ..storage import GuildConfig, GuildStore

log = logging.getLogger(__name__)


class Setup(commands.Cog):
    """`/setup welcome`, `/setup streams`, `/setup status`."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.store: GuildStore = bot.store  # type: ignore[attr-defined]

    setup = app_commands.Group(
        name="setup",
        description="Configure John Bot for this server",
        guild_only=True,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @setup.command(name="welcome", description="Where to greet members and which role to give them")
    @app_commands.describe(
        channel="Channel for the welcome message",
        role="Role new members receive automatically",
        message="Custom greeting — {member}, {guild} and {count} are replaced",
    )
    async def welcome(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
        role: discord.Role | None = None,
        message: str | None = None,
    ) -> None:
        guild = interaction.guild
        assert guild is not None

        if channel is None and role is None and message is None:
            await interaction.response.send_message(
                "Nothing to change — pass a channel, a role or a message.",
                ephemeral=True,
            )
            return

        current = self.store.get(guild.id)
        config = replace(
            current,
            welcome_channel_id=channel.id if channel else current.welcome_channel_id,
            member_role_id=role.id if role else current.member_role_id,
            welcome_message=(
                message.strip() if message and message.strip() else current.welcome_message
            ),
        )

        problems: list[str] = []
        if role is not None:
            problems.extend(self._role_problems(guild, role))
        if channel is not None:
            problems.extend(self._channel_problems(guild, channel))

        if problems:
            await interaction.response.send_message(
                "I didn't save that:\n" + "\n".join(f"• {problem}" for problem in problems),
                ephemeral=True,
            )
            return

        self.store.set(guild.id, config)
        await interaction.response.send_message(
            embed=self._status_embed(guild, config, title="Welcome settings saved"),
            ephemeral=True,
        )

    @setup.command(name="streams", description="Channel where live-stream links get posted")
    @app_commands.describe(channel="Channel for stream announcements")
    async def streams(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        guild = interaction.guild
        assert guild is not None

        problems = self._channel_problems(guild, channel)
        if problems:
            await interaction.response.send_message(
                "I didn't save that:\n" + "\n".join(f"• {problem}" for problem in problems),
                ephemeral=True,
            )
            return

        config = replace(self.store.get(guild.id), stream_channel_id=channel.id)
        self.store.set(guild.id, config)
        await interaction.response.send_message(
            embed=self._status_embed(guild, config, title="Stream alerts saved"),
            ephemeral=True,
        )

    @setup.command(name="status", description="Show the current configuration")
    async def status(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None
        await interaction.response.send_message(
            embed=self._status_embed(guild, self.store.get(guild.id)),
            ephemeral=True,
        )

    # -- helpers ---------------------------------------------------------

    def _role_problems(self, guild: discord.Guild, role: discord.Role) -> list[str]:
        problems: list[str] = []
        me = guild.me
        if me is None:
            return ["I couldn't resolve my own member object."]
        if not me.guild_permissions.manage_roles:
            problems.append("I need the **Manage Roles** permission.")
        if role.is_default():
            problems.append("@everyone can't be an autorole.")
        if role.managed:
            problems.append(f"**{role.name}** is managed by an integration.")
        if me.top_role <= role:
            problems.append(f"**{role.name}** must sit below my top role (**{me.top_role.name}**).")
        return problems

    def _channel_problems(self, guild: discord.Guild, channel: discord.TextChannel) -> list[str]:
        me = guild.me
        if me is None:
            return ["I couldn't resolve my own member object."]
        perms = channel.permissions_for(me)
        problems: list[str] = []
        if not perms.view_channel:
            problems.append(f"I can't view {channel.mention}.")
        if not perms.send_messages:
            problems.append(f"I can't send messages in {channel.mention}.")
        if not perms.embed_links:
            problems.append(f"I need **Embed Links** in {channel.mention}.")
        return problems

    def _status_embed(
        self,
        guild: discord.Guild,
        config: GuildConfig,
        *,
        title: str = "John Bot status",
    ) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            colour=discord.Colour.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Welcome channel",
            value=f"<#{config.welcome_channel_id}>"
            if config.welcome_channel_id
            else "not set — falls back to the server's system channel",
            inline=False,
        )
        embed.add_field(
            name="Member role",
            value=f"<@&{config.member_role_id}>" if config.member_role_id else "not set",
            inline=False,
        )
        embed.add_field(
            name="Stream channel",
            value=f"<#{config.stream_channel_id}>"
            if config.stream_channel_id
            else "not set — stream alerts are off",
            inline=False,
        )
        embed.add_field(name="Greeting", value=config.welcome_message[:1000], inline=False)
        embed.set_footer(text="Change these with /setup welcome and /setup streams")
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Setup(bot))
