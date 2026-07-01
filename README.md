# Claude Code Usage — macOS menu bar app

A lightweight macOS menu bar app that shows your Claude Code token usage and
cost — for the current session and all-time — by reading the JSONL logs
Claude Code writes to `~/.claude/projects/`.

The menu bar shows a live status emoji + spend (e.g. `🟡 $22.08`); click it
for the full breakdown:

```
🎯  Current Session
     🪙  Tokens   15.8M
     💰  Cost     $22.08
        ⌨️  Input        25,063  ·  $0.13
        📤  Output       72,448  ·  $1.81
        📝  Cache write  1.29M   ·  $12.95
        ⚡  Cache read   14.40M  ·  $7.20
─────────────────
🌍  All Time
     🪙  Tokens   678.5M
     💰  Cost     $832.83
        ⌨️  Input        975,985 ·  $4.87
        📤  Output       3.24M   ·  $79.70
        📝  Cache write  48.81M  ·  $449.76
        ⚡  Cache read   625.51M ·  $298.50
─────────────────
📊  Usage Windows
     ⏳  Session (5h)   31.3M  ·  $50.00
        (set limit in config.py for %)
     📅  Weekly (7d)    204.2M ·  $243.50
        🟢 ▓▓▓░░░░░░░ 34.0%
─────────────────
⏱  Updated just now
🔄  Refresh now
🚪  Quit
```

- **Current Session** = the conversation (sessionId) with the most recent
  activity, updated live as you work.
- **All Time** = every session across every project on this machine.
- **Cost breakdown** splits each total into input / output / **cache write**
  (1.25× input for 5-min, 2× for 1-hour) / **cache read** (0.1× input). For a
  typical Claude Code session, cache reads/writes are the bulk of the cost.
- **Usage Windows** = rolling **5-hour** ("session") and **7-day** ("weekly")
  spans, mirroring the windows Claude's own limits use.

### Usage-% caveat & config

The **official** session/weekly utilization percentages come from Claude
Code's `/usage` command — Claude fetches those live from the API and they are
**not stored on disk**, so this app cannot read them directly. Instead it
computes the same rolling windows from your logs and shows `usage ÷ limit`
against limits **you set** in `config.py`:

```python
SESSION_TOKEN_LIMIT = 300_000_000   # your plan's 5-hour token allowance
WEEKLY_TOKEN_LIMIT  = 2_000_000_000 # your plan's weekly token allowance
```

Leave a limit as `None` to show raw window totals without a %. Run `/usage` in
Claude Code to calibrate these to your plan; the menu bar then shows the % (and
its progress bar) for whichever window has a limit set.

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
