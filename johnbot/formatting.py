"""Stream-link parsing and welcome-text rendering.

Kept free of discord.py imports so it can be unit tested without a gateway.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

# Discord sends this placeholder when someone is "streaming" without a real URL.
PLACEHOLDER_PATHS = {"/directory", "/", ""}

PLATFORM_NAMES = {
    "twitch.tv": "Twitch",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "kick.com": "Kick",
    "trovo.live": "Trovo",
}


@dataclass(frozen=True)
class StreamLink:
    url: str
    platform: str
    title: str | None = None


def _platform_for(host: str) -> str:
    for domain, name in PLATFORM_NAMES.items():
        if host == domain or host.endswith("." + domain):
            return name
    return host


def parse_stream_url(raw: str | None, title: str | None = None) -> StreamLink | None:
    """Turn a presence activity URL into a StreamLink, or None if useless."""
    if not raw or not isinstance(raw, str):
        return None

    url = raw.strip()
    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None

    host = parsed.hostname.lower()
    path = parsed.path.rstrip("/")

    # twitch.tv/directory (and bare homepages) are not a person's stream.
    if path in PLACEHOLDER_PATHS:
        return None
    if host in ("twitch.tv", "www.twitch.tv") and path in ("/directory", "/videos"):
        return None

    return StreamLink(url=url, platform=_platform_for(host), title=title)


def render_welcome(template: str, *, member: str, guild: str, count: int) -> str:
    """Replace the supported {member}/{guild}/{count} tokens.

    str.format is deliberately avoided: a stray brace in a custom welcome
    message would otherwise crash every join.
    """
    out = template
    for token, value in (
        ("{member}", member),
        ("{guild}", guild),
        ("{count}", str(count)),
    ):
        out = out.replace(token, value)
    return out
