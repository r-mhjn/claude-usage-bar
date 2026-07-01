#!/bin/bash
# Play a notification sound for Claude Code hook events.
#
#   claude-notify-sound.sh stop     # Claude finished a turn
#   claude-notify-sound.sh notify   # Claude needs your input / permission
#
# Configure the sounds by editing  ~/.claude/notify-sound.conf :
#
#   STOP_SOUND=/System/Library/Sounds/Submarine.aiff
#   NOTIFY_SOUND=/System/Library/Sounds/Glass.aiff
#
# Any audio file afplay can play works (.aiff/.wav/.mp3/.m4a) — including your
# own custom sound. Built-in macOS sounds live in /System/Library/Sounds/
# (Basso Blow Bottle Frog Funk Glass Hero Morse Ping Pop Purr Sosumi
#  Submarine Tink). Set a value to empty ("") to silence that event.

CONF="$HOME/.claude/notify-sound.conf"

# Defaults (overridden by the conf file if present).
STOP_SOUND="/System/Library/Sounds/Submarine.aiff"
NOTIFY_SOUND="/System/Library/Sounds/Glass.aiff"

[ -f "$CONF" ] && . "$CONF"

case "$1" in
  notify) SOUND="$NOTIFY_SOUND" ;;
  *)      SOUND="$STOP_SOUND" ;;
esac

# Play in the background so the hook never blocks Claude Code.
if [ -n "$SOUND" ] && [ -f "$SOUND" ]; then
  afplay "$SOUND" >/dev/null 2>&1 &
fi
exit 0
