"""Smoke test: every cog loads and the slash commands are registered."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from johnbot.bot import INITIAL_EXTENSIONS, JohnBot
from johnbot.config import Config


class CogLoadingTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_cogs_load_and_commands_register(self):
        with TemporaryDirectory() as tmp:
            bot = JohnBot(Config(token="fake-token", data_dir=Path(tmp)))
            try:
                for extension in INITIAL_EXTENSIONS:
                    await bot.load_extension(extension)

                names = {command.name for command in bot.tree.get_commands()}
                self.assertIn("setup", names)

                setup = next(c for c in bot.tree.get_commands() if c.name == "setup")
                subcommands = {child.name for child in setup.commands}
                self.assertEqual(subcommands, {"welcome", "streams", "status"})

                self.assertIsNotNone(bot.get_cog("Welcome"))
                self.assertIsNotNone(bot.get_cog("StreamAlerts"))
                self.assertTrue(bot.intents.members)
                self.assertTrue(bot.intents.presences)
            finally:
                await bot.close()


if __name__ == "__main__":
    unittest.main()
