"""Claude Code usage menu bar app (macOS, rumps).

Shows an icon in the menu bar; click it for a dropdown with the current
session's tokens/cost and all-time totals. Refreshes every 5 seconds.

Run:  python3 app.py
"""

import time

import rumps

import usage_reader

REFRESH_SECONDS = 5
ICON_TITLE = "◐"  # always-visible menu bar title (icon only, per design)


def _fmt_tokens(n):
    """Human-readable token count: 1234 -> '1,234', 156284 -> '156.3K'."""
    if n < 10_000:
        return f"{n:,}"
    if n < 1_000_000:
        return f"{n / 1_000:.1f}K"
    return f"{n / 1_000_000:.2f}M"


def _fmt_cost(c):
    return f"${c:,.2f}"


def _fmt_age(seconds):
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    return f"{int(seconds // 3600)}h ago"


class UsageBarApp(rumps.App):
    def __init__(self):
        super().__init__(ICON_TITLE, quit_button=None)

        # Build the dropdown once; update item titles in place on refresh.
        self.session_header = rumps.MenuItem("Current Session")
        self.session_tokens = rumps.MenuItem("  Tokens   —")
        self.session_cost = rumps.MenuItem("  Cost     —")
        self.total_header = rumps.MenuItem("All Time")
        self.total_tokens = rumps.MenuItem("  Tokens   —")
        self.total_cost = rumps.MenuItem("  Cost     —")
        self.updated = rumps.MenuItem("Updated —")

        self.menu = [
            self.session_header,
            self.session_tokens,
            self.session_cost,
            None,  # separator
            self.total_header,
            self.total_tokens,
            self.total_cost,
            None,
            self.updated,
            rumps.MenuItem("Refresh now", callback=self._on_refresh_now),
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]

        self._last_update = None
        self.refresh(None)
        self._timer = rumps.Timer(self.refresh, REFRESH_SECONDS)
        self._timer.start()

    def _on_refresh_now(self, _):
        self.refresh(None)

    def refresh(self, _):
        try:
            data = usage_reader.collect()
        except Exception as exc:  # never let the timer die
            self.updated.title = f"Error: {exc}"
            return

        session = data["session"]
        total = data["total"]

        self.session_tokens.title = f"  Tokens   {_fmt_tokens(session['tokens'])}"
        self.session_cost.title = f"  Cost     {_fmt_cost(session['cost'])}"
        self.total_tokens.title = f"  Tokens   {_fmt_tokens(total['tokens'])}"
        self.total_cost.title = f"  Cost     {_fmt_cost(total['cost'])}"

        self._last_update = time.time()
        self.updated.title = f"Updated {_fmt_age(0)}"


if __name__ == "__main__":
    UsageBarApp().run()
