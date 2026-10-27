"""Allow `python -m johnbot`."""

from __future__ import annotations

import logging
import sys

import discord

from .bot import JohnBot
from .config import load_config


def main() -> int:
    try:
        config = load_config()
    except RuntimeError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    discord.utils.setup_logging(level=config.log_level, root=True)
    log = logging.getLogger("johnbot")
    log.info("Starting John Bot (data dir: %s)", config.data_dir)

    bot = JohnBot(config)
    try:
        bot.run(config.token, log_handler=None)
    except discord.LoginFailure:
        log.error("Discord rejected the token — check DISCORD_TOKEN in .env")
        return 1
    except discord.PrivilegedIntentsRequired:
        log.error(
            "A privileged intent is disabled. Developer Portal -> your app -> Bot -> "
            "Privileged Gateway Intents: enable SERVER MEMBERS INTENT and PRESENCE INTENT."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
