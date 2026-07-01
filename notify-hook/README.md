# Claude Code notification sound hook

Play a sound when Claude Code **finishes a turn** (`Stop`) or **needs your
input / a permission decision** (`Notification`) — with configurable, and
custom, sounds.

## What's here

| File | Purpose |
|------|---------|
| `claude-notify-sound.sh` | The player. Takes `stop` or `notify`, reads sounds from `~/.claude/notify-sound.conf`, plays via `afplay` in the background. |
| `notify-sound.conf.example` | Sample config — copy to `~/.claude/notify-sound.conf` and edit. |

## Install

```sh
mkdir -p ~/.claude/hooks
cp claude-notify-sound.sh ~/.claude/hooks/
chmod +x ~/.claude/hooks/claude-notify-sound.sh
cp notify-sound.conf.example ~/.claude/notify-sound.conf
```

Then add the hooks to `~/.claude/settings.json` (merge with any existing keys):

```json
{
  "hooks": {
    "Notification": [
      { "hooks": [ { "type": "command", "command": "$HOME/.claude/hooks/claude-notify-sound.sh notify", "async": true } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "$HOME/.claude/hooks/claude-notify-sound.sh stop", "async": true } ] }
    ]
  }
}
```

Open `/hooks` in Claude Code once (or restart) so it reloads the config.

## Configure the sounds

Edit `~/.claude/notify-sound.conf`:

```sh
STOP_SOUND=/System/Library/Sounds/Submarine.aiff   # Claude finished
NOTIFY_SOUND=/System/Library/Sounds/Glass.aiff      # Claude needs you
```

- **Presets** live in `/System/Library/Sounds/`: Basso, Blow, Bottle, Frog,
  Funk, Glass, Hero, Morse, Ping, Pop, Purr, Sosumi, Submarine, Tink.
- **Custom sound:** point at any file `afplay` can play (`.aiff/.wav/.mp3/.m4a`),
  e.g. `STOP_SOUND=$HOME/Sounds/done.wav`.
- **Silence an event:** set its value to `""`.

Changes take effect immediately — no restart needed (the conf is read each time
the hook fires).

## Test

```sh
~/.claude/hooks/claude-notify-sound.sh stop     # you should hear STOP_SOUND
~/.claude/hooks/claude-notify-sound.sh notify   # you should hear NOTIFY_SOUND
```
