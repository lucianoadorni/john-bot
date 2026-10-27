"""John Bot — welcome messages, autorole, and live-stream links."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from .config import Config
from .storage import GuildConfig, GuildStore

log = logging.getLogger(__name__)

INITIAL_EXTENSIONS = (
    "johnbot.cogs.welcome",
    "johnbot.cogs.streams",
    "johnbot.cogs.setup",
)


class JohnBot(commands.Bot):
    def __init__(self, config: Config) -> None:
        intents = discord.Intents.default()
        intents.members = True  # required for on_member_join + role edits
        intents.presences = True  # required for stream detection
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
            allowed_mentions=discord.AllowedMentions(
                everyone=False, roles=False, users=True
            ),
        )
        self.config = config
        self.store = GuildStore(
            config.data_dir / "guilds.json",
            defaults=GuildConfig(
                welcome_channel_id=config.welcome_channel_id,
                member_role_id=config.member_role_id,
                stream_channel_id=config.stream_channel_id,
                welcome_message=config.welcome_message,
            ),
        )

    async def setup_hook(self) -> None:
        self.tree.on_error = self.on_app_command_error
        for extension in INITIAL_EXTENSIONS:
            await self.load_extension(extension)
            log.debug("Loaded %s", extension)

        if self.config.guild_id:
            # Guild-scoped sync: commands appear instantly in that one server.
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Synced %d commands to guild %s", len(synced), self.config.guild_id)
        else:
            synced = await self.tree.sync()
            log.info("Synced %d global commands (may take up to an hour to appear)", len(synced))

    async def on_ready(self) -> None:
        assert self.user is not None
        log.info(
            "Logged in as %s (id %s) — in %d guild(s)",
            self.user,
            self.user.id,
            len(self.guilds),
        )
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="for new members"
            ),
            status=discord.Status.online,
        )

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original  # type: ignore[assignment]
        if isinstance(error, app_commands.MissingPermissions):
            message = "You need the **Manage Server** permission for that."
        elif isinstance(error, app_commands.CheckFailure):
            message = "You can't use that command here."
        else:
            log.exception("Command %s failed", interaction.command, exc_info=error)
            message = "Something went wrong — check the bot console."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
