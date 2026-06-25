# Claude Code Usage — macOS menu bar app

A lightweight macOS menu bar app that shows your Claude Code token usage and
cost — for the current session and all-time — by reading the JSONL logs
Claude Code writes to `~/.claude/projects/`.

The menu bar shows an icon (`◐`); click it for the breakdown:

```
Current Session
  Tokens   1.8M
  Cost     $3.83
─────────────────
All Time
  Tokens   1.41B
  Cost     $1,522.58
─────────────────
Updated 3s ago
Refresh now
Quit
```

- **Current Session** = the conversation (sessionId) with the most recent
  activity, updated live as you work.
- **All Time** = every session across every project on this machine.

## Install as a macOS app (recommended)

Build a standalone, double-clickable **Claude Usage.app** — no Python or pip
needed to *run* it afterward. The build uses an isolated venv, so nothing is
installed into your system Python:

```sh
cd claude-usage-bar
./build_app.sh
cp -R "dist/Claude Usage.app" /Applications/
```

Then launch **Claude Usage** from Applications (or Spotlight). It runs as a
menu bar agent — an icon at the top-right, no Dock icon. The icon refreshes
every 5 seconds.

- **Start at login:** System Settings → General → Login Items → add
  *Claude Usage*.
- **First launch:** the app is unsigned, so macOS Gatekeeper may warn. Right-click
  the app → Open (once), or run
  `xattr -dr com.apple.quarantine "/Applications/Claude Usage.app"`.

## Run from source (for development)

```sh
cd claude-usage-bar
pip3 install -r requirements.txt   # installs rumps
python3 app.py
```

## How it works

| File | Responsibility |
|------|----------------|
| `pricing.py` | Per-model price table + cost math (input/output/cache tokens). Unknown models count tokens but cost $0, so a new model never crashes the app. |
| `usage_reader.py` | Pure data layer. Scans `~/.claude/projects/**/*.jsonl`, dedupes by `(message.id, requestId)`, groups by session, returns session + total aggregates. No UI. |
| `app.py` | The rumps menu bar app. Calls `usage_reader.collect()` on a timer and updates the dropdown. |

## Cost accuracy

Rates are USD per 1M tokens from Anthropic's public pricing:

| Model | Input | Output |
|-------|------:|-------:|
| Fable 5 | $10 | $50 |
| Opus 4.x | $5 | $25 |
| Sonnet 4.x | $3 | $15 |
| Haiku 4.5 | $1 | $5 |

Cache tokens: writes are 1.25× input (5-min TTL) / 2× (1-hour TTL); reads are
0.1× input. Update `pricing.py` if Anthropic changes pricing or adds models.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Covers cost math (incl. cache pricing), dedupe, malformed-line handling, and
session selection — all against synthetic fixtures, no real logs required.
