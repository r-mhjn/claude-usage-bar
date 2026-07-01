"""Claude Code usage menu bar app (macOS, rumps).

Menu bar shows a live status emoji that changes color with session spend;
click it for a colorful dropdown with session + all-time tokens and cost.
Refreshes every 5 seconds.

Run:  python3 app.py
"""

import time

import rumps

import usage_reader

# --- Optional AppKit styling (colored/attributed menu titles) -------------
# Degrade gracefully to plain (still emoji-rich) titles if unavailable.
try:
    from AppKit import (
        NSColor,
        NSFont,
        NSFontAttributeName,
        NSForegroundColorAttributeName,
    )
    from Foundation import NSAttributedString

    HAVE_APPKIT = True
except Exception:  # pragma: no cover
    HAVE_APPKIT = False


REFRESH_SECONDS = 5


# --- Formatting helpers ----------------------------------------------------
def _fmt_tokens(n):
    if n < 10_000:
        return f"{n:,}"
    if n < 1_000_000:
        return f"{n / 1_000:.1f}K"
    if n < 1_000_000_000:
        return f"{n / 1_000_000:.2f}M"
    return f"{n / 1_000_000_000:.2f}B"


def _fmt_cost(c):
    return f"${c:,.2f}"


def _fmt_age(seconds):
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    return f"{int(seconds // 3600)}h ago"


def _cost_tier(cost):
    """(emoji, color-name) for a spend level — drives the live menu bar icon
    and the cost text color."""
    if cost < 5:
        return "🟢", "green"
    if cost < 20:
        return "🟡", "yellow"
    if cost < 50:
        return "🟠", "orange"
    return "🔴", "red"


# --- Color palette ---------------------------------------------------------
def _colors():
    if not HAVE_APPKIT:
        return {}
    # `label` is the system primary label color — the OS keeps it legible on
    # the translucent (vibrancy) menu background regardless of what shows
    # through. We use it for all text and let emoji carry the color.
    return {"label": NSColor.labelColor()}


def _style(item, text, color_name="label", bold=False):
    """Set a menu item's title, using a high-contrast system color + optional
    bold via NSAttributedString. Falls back to plain text without AppKit."""
    item.title = text
    if not HAVE_APPKIT:
        return
    try:
        size = 14.0
        font = NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size)
        attrs = {NSFontAttributeName: font}
        palette = _style._palette
        color = palette.get(color_name) or palette.get("label")
        if color is not None:
            attrs[NSForegroundColorAttributeName] = color
        astr = NSAttributedString.alloc().initWithString_attributes_(text, attrs)
        item._menuitem.setAttributedTitle_(astr)
    except Exception:
        pass


_style._palette = _colors()


class UsageBarApp(rumps.App):
    def __init__(self):
        super().__init__("✨", quit_button=None)

        self.session_header = rumps.MenuItem("🎯  Current Session")
        self.session_tokens = rumps.MenuItem("")
        self.session_cost = rumps.MenuItem("")
        self.total_header = rumps.MenuItem("🌍  All Time")
        self.total_tokens = rumps.MenuItem("")
        self.total_cost = rumps.MenuItem("")
        self.updated = rumps.MenuItem("")
        self.refresh_item = rumps.MenuItem("🔄  Refresh now", callback=self._on_refresh_now)
        self.quit_item = rumps.MenuItem("🚪  Quit", callback=rumps.quit_application)

        self.menu = [
            self.session_header,
            self.session_tokens,
            self.session_cost,
            None,
            self.total_header,
            self.total_tokens,
            self.total_cost,
            None,
            self.updated,
            self.refresh_item,
            self.quit_item,
        ]

        # Static styling for headers and controls (high-contrast, bold).
        _style(self.session_header, "🎯  Current Session", bold=True)
        _style(self.total_header, "🌍  All Time", bold=True)
        _style(self.refresh_item, "🔄  Refresh now")
        _style(self.quit_item, "🚪  Quit")

        self.refresh(None)
        self._timer = rumps.Timer(self.refresh, REFRESH_SECONDS)
        self._timer.start()

    def _on_refresh_now(self, _):
        self.refresh(None)

    def refresh(self, _):
        try:
            data = usage_reader.collect()
        except Exception as exc:  # never let the timer die
            _style(self.updated, f"⚠️  Error: {exc}", "red")
            self.title = "⚠️"
            return

        session = data["session"]
        total = data["total"]

        sess_emoji, _ = _cost_tier(session["cost"])
        total_emoji, _ = _cost_tier(total["cost"])

        # Live menu bar icon: status emoji + session cost.
        self.title = f"{sess_emoji} {_fmt_cost(session['cost'])}"

        # Text stays high-contrast (labelColor); the tier emoji carries the
        # green/yellow/orange/red spend signal so nothing depends on hard-to-
        # read colored text over the translucent menu background.
        _style(self.session_tokens, f"     🪙  Tokens   {_fmt_tokens(session['tokens'])}")
        _style(self.session_cost, f"     {sess_emoji}  Cost     {_fmt_cost(session['cost'])}", bold=True)

        _style(self.total_tokens, f"     🪙  Tokens   {_fmt_tokens(total['tokens'])}")
        _style(self.total_cost, f"     {total_emoji}  Cost     {_fmt_cost(total['cost'])}", bold=True)

        _style(self.updated, f"⏱  Updated {_fmt_age(0)}")


if __name__ == "__main__":
    UsageBarApp().run()
