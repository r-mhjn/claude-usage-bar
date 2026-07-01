"""User-editable configuration.

The official Claude session/weekly usage percentages come from Claude Code's
`/usage` command (fetched live from the API). They are NOT stored on disk, so
this app estimates the same two rolling windows from your local logs and shows
usage against limits you set below.

Set the token limits to match your plan to get a % that tracks alongside
Claude's telemetry. Leave a limit as None to show raw totals without a %.
"""

# Rolling window sizes — match Claude's "session" (5-hour) and weekly windows.
SESSION_WINDOW_HOURS = 5
WEEKLY_WINDOW_DAYS = 7

# Your plan limits, in total tokens per window. None = show totals, no %.
# Example values (edit to your plan — run /usage in Claude Code to calibrate):
#   SESSION_TOKEN_LIMIT = 300_000_000
#   WEEKLY_TOKEN_LIMIT   = 2_000_000_000
SESSION_TOKEN_LIMIT = None
WEEKLY_TOKEN_LIMIT = None

# Menu bar refresh interval (seconds).
REFRESH_SECONDS = 5
