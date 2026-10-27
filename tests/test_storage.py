"""Tests for the per-guild JSON store."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from johnbot.storage import GuildConfig, GuildStore


class GuildStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "nested" / "guilds.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_returns_defaults(self):
        defaults = GuildConfig(member_role_id=99)
        store = GuildStore(self.path, defaults=defaults)
        self.assertIs(store.get(1), defaults)
        self.assertFalse(self.path.exists())

    def test_set_persists_across_instances(self):
        store = GuildStore(self.path)
        store.set(1, GuildConfig(welcome_channel_id=10, member_role_id=20))
        store.set(2, GuildConfig(stream_channel_id=30))

        reloaded = GuildStore(self.path)
        self.assertEqual(reloaded.get(1).welcome_channel_id, 10)
        self.assertEqual(reloaded.get(1).member_role_id, 20)
        self.assertEqual(reloaded.get(2).stream_channel_id, 30)
        self.assertIsNone(reloaded.get(2).welcome_channel_id)

    def test_saved_file_is_json_with_string_keys(self):
        store = GuildStore(self.path)
        store.set(123456789, GuildConfig(welcome_channel_id=1))
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(list(raw), ["123456789"])

    def test_corrupt_file_falls_back_to_defaults(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{oops", encoding="utf-8")
        store = GuildStore(self.path, defaults=GuildConfig(member_role_id=7))
        self.assertEqual(store.get(1).member_role_id, 7)

    def test_unknown_fields_are_ignored(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(
            json.dumps({"5": {"member_role_id": 8, "legacy_key": True}}),
            encoding="utf-8",
        )
        self.assertEqual(GuildStore(self.path).get(5).member_role_id, 8)


if __name__ == "__main__":
    unittest.main()
