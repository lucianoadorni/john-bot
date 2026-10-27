# John Bot

A small Discord bot in Python that does three things:

1. **Welcomes new members** — an embed in your welcome channel with their avatar,
   account age and member number.
2. **Gives them a role** on join (autorole), with clear warnings when Discord
   refuses because of role hierarchy or missing permissions.
3. **Posts a link when someone in the server starts streaming** — reads streaming
   presences and announces the Twitch/YouTube/Kick link in a channel you choose.

Built on [discord.py](https://github.com/Rapptz/discord.py) 2.x with slash commands.
No database, no web server, no extra services: one JSON file for per-server settings.

## Requirements

- Python 3.10+
- A Discord application ([Developer Portal](https://discord.com/developers/applications))
- Two privileged intents enabled: **Server Members** and **Presence**

## Setup

### 1. Create the application

1. Developer Portal → **New Application** → name it `John Bot`.
2. **Bot** tab → **Reset Token** → copy the token (this is the only secret you need).
3. **Bot** tab → **Privileged Gateway Intents** → enable
   **Server Members Intent** and **Presence Intent** → Save.
4. **OAuth2 → General** → copy the **Application ID** (needed for the invite link).

### 2. Invite the bot

Replace `YOUR_APP_ID` and open:

```
https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot%20applications.commands&permissions=268520448
```

`268520448` = View Channels, Send Messages, Embed Links, Read Message History,
Manage Roles. The bot also needs its **own role dragged above the member role** it
hands out, otherwise Discord will not let it assign that role.

### 3. Configure and run

```bash
git clone <your-fork-url> john-bot
cd john-bot
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then edit .env
```

Fill in `.env`:

```ini
DISCORD_TOKEN=your-bot-token
GUILD_ID=123456789012345678        # your server id: slash commands sync instantly
WELCOME_CHANNEL_ID=123...
MEMBER_ROLE_ID=123...
STREAM_CHANNEL_ID=123...
```

Then:

```bash
python -m johnbot
```

Expected console output:

```
Loaded johnbot.cogs.welcome
Synced 3 commands to guild 123456789012345678
Logged in as John Bot#1234 (id ...) — in 1 guild(s)
```

### 4. Fine-tune in Discord

The `.env` values are defaults; `/setup` overrides them per server (needs
**Manage Server**):

| Command | What it does |
| --- | --- |
| `/setup welcome channel:#welcome role:@Member` | Welcome channel + autorole |
| `/setup welcome message:Hey {member}, welcome to {guild}!` | Custom greeting (`{member}`, `{guild}`, `{count}`) |
| `/setup streams channel:#streams` | Where live links are posted |
| `/setup status` | Show current settings |

The commands validate themselves before saving: missing permissions, a role above
the bot's top role, or a managed/integration role are reported instead of silently
failing later.

## How the stream alert works

Discord exposes a member's streaming activity in the presence, including the stream
URL. On every presence update the bot diffs the URLs against the previous presence
and announces a genuinely new one, ignoring the `twitch.tv/directory` placeholder
Discord sends when no real URL is attached.

To test it: start a stream on Twitch with "Share activity status" / Discord
integration on, or join a voice channel on the Discord client with Go Live —
the link is posted in the configured channel.

The same member + URL pair is announced at most once per
`STREAM_ALERT_COOLDOWN` seconds (default 3600) so short reconnects don't spam.

## Project layout

```
johnbot/
  __main__.py     entry point, logging, friendly startup errors
  bot.py          JohnBot subclass: intents, cog loading, command sync
  config.py       .env -> Config dataclass
  storage.py      per-guild settings in data/guilds.json (atomic writes)
  formatting.py   stream-URL parsing + welcome templating (no discord import)
  cogs/
    welcome.py    on_member_join -> autorole + welcome embed
    streams.py    on_presence_update -> stream announcement
    setup.py      /setup welcome | streams | status
tests/            unittest suite, no token needed
```

## Tests

```bash
python -m unittest discover -s tests -t . -v
```

14 tests cover URL parsing (Twitch/YouTube/Kick, placeholder rejection), welcome
templating, JSON persistence and a smoke test that loads every cog and checks the
slash commands register — no bot token or network needed.

The event tests drive the real listeners with fake guild/member/channel objects, so
the welcome embed, autorole permission checks, stream announcements and the
stop-start cooldown are all exercised without connecting to Discord.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `PrivilegedIntentsRequired` at startup | Enable Server Members + Presence intents in the portal |
| `discord.LoginFailure` | Wrong/regenerated token in `.env` |
| Slash commands missing | No `GUILD_ID` set → global sync can take up to an hour; set `GUILD_ID` and restart |
| "Autorole failed" in the welcome embed | Bot's role sits below the target role, or **Manage Roles** is missing |
| No stream alerts | Presence intent off, no stream channel configured, or the member isn't sharing streaming activity |
| `data/guilds.json` is corrupt | The bot logs a warning and falls back to `.env` defaults; delete the file to reset |

## License

MIT — see [LICENSE](LICENSE).
