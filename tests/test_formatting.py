"""Unit tests for pure helpers — no token or gateway needed."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import discord

from johnbot.cogs.streams import live_links
from johnbot.formatting import parse_stream_url, render_welcome


class ParseStreamUrlTests(unittest.TestCase):
    def test_twitch_channel(self):
        link = parse_stream_url("https://www.twitch.tv/somestreamer")
        self.assertIsNotNone(link)
        self.assertEqual(link.platform, "Twitch")
        self.assertEqual(link.url, "https://www.twitch.tv/somestreamer")

    def test_youtube_variants(self):
        for url in (
            "https://youtube.com/watch?v=abc",
            "https://m.youtube.com/watch?v=abc",
            "https://youtu.be/abc",
        ):
            with self.subTest(url=url):
                self.assertEqual(parse_stream_url(url).platform, "YouTube")

    def test_other_platform_falls_back_to_host(self):
        self.assertEqual(parse_stream_url("https://kick.com/foo").platform, "Kick")
        self.assertEqual(parse_stream_url("https://example.com/live").platform, "example.com")

    def test_rejects_placeholders_and_junk(self):
        for raw in (
            None,
            "",
            "   ",
            "not a url",
            "ftp://twitch.tv/foo",
            "https://www.twitch.tv/directory",
            "https://twitch.tv",
            "https://youtube.com/",
        ):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_stream_url(raw))

    def test_title_is_carried_through(self):
        self.assertEqual(
            parse_stream_url("https://twitch.tv/x", title="Ranked grind").title,
            "Ranked grind",
        )


class RenderWelcomeTests(unittest.TestCase):
    def test_replaces_all_tokens(self):
        out = render_welcome(
            "Hi {member}, welcome to {guild} (#{count})!",
            member="<@1>",
            guild="Cool Server",
            count=42,
        )
        self.assertEqual(out, "Hi <@1>, welcome to Cool Server (#42)!")

    def test_unknown_braces_do_not_raise(self):
        self.assertEqual(
            render_welcome("{not_a_token} {member}", member="<@1>", guild="G", count=1),
            "{not_a_token} <@1>",
        )


class LiveLinksTests(unittest.TestCase):
    def test_only_streaming_activities_with_real_urls(self):
        member = SimpleNamespace(
            activities=[
                SimpleNamespace(
                    type=discord.ActivityType.streaming,
                    url="https://twitch.tv/one",
                    name="Ranked",
                    details="Ranked grind",
                ),
                SimpleNamespace(
                    type=discord.ActivityType.playing,
                    url="https://twitch.tv/two",
                    name="Apex",
                    details=None,
                ),
                SimpleNamespace(
                    type=discord.ActivityType.streaming,
                    url="https://www.twitch.tv/directory",
                    name="",
                    details=None,
                ),
            ]
        )
        links = live_links(member)
        self.assertEqual([link.url for link in links], ["https://twitch.tv/one"])
        self.assertEqual(links[0].title, "Ranked grind")


if __name__ == "__main__":
    unittest.main()
