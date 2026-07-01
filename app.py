"""Claude Code usage menu bar app (macOS, rumps).

Menu bar shows a live status emoji + spend; click it for a colorful dropdown
with per-category cost breakdown (input / output / cache write / cache read),
plus rolling 5-hour "session" and 7-day "weekly" usage windows. Refreshes
every few seconds (see config.REFRESH_SECONDS).

Run:  python3 app.py
"""

import rumps

import config
import pricing
import usage_reader

# --- Optional AppKit styling (colored/attributed menu titles) -------------
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


# Emoji + label per cost category (order follows pricing.CATEGORIES).
CAT_META = {
    "input": ("⌨️", "Input"),
    "output": ("📤", "Output"),
    "cache_write": ("📝", "Cache write"),
    "cache_read": ("⚡", "Cache read"),
}


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


def _cost_tier(cost):
    if cost < 5:
        return "🟢"
    if cost < 20:
        return "🟡"
    if cost < 50:
        return "🟠"
    return "🔴"


def _pct_tier(pct):
    if pct < 50:
        return "🟢"
    if pct < 75:
        return "🟡"
    if pct < 90:
        return "🟠"
    return "🔴"


def _bar(pct, width=10):
    filled = max(0, min(width, round(pct / 100 * width)))
    return "▓" * filled + "░" * (width - filled)


# --- Styling ---------------------------------------------------------------
def _label_color():
    return NSColor.labelColor() if HAVE_APPKIT else None


def _style(item, text, bold=False):
    """High-contrast title (system labelColor) with optional bold; color is
    carried by emoji so text stays legible on the translucent menu."""
    item.title = text
    if not HAVE_APPKIT:
        return
    try:
        size = 14.0
        font = NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size)
        attrs = {NSFontAttributeName: font, NSForegroundColorAttributeName: NSColor.labelColor()}
        astr = NSAttributedString.alloc().initWithString_attributes_(text, attrs)
        item._menuitem.setAttributedTitle_(astr)
    except Exception:
        pass


class UsageBarApp(rumps.App):
    def __init__(self):
        super().__init__("✨", quit_button=None)

        self.session_header = rumps.MenuItem("🎯  Current Session")
        self.session_tokens = rumps.MenuItem("")
        self.session_cost = rumps.MenuItem("")
        self.session_bd = {c: rumps.MenuItem("") for c in pricing.CATEGORIES}

        self.total_header = rumps.MenuItem("🌍  All Time")
        self.total_tokens = rumps.MenuItem("")
        self.total_cost = rumps.MenuItem("")
        self.total_bd = {c: rumps.MenuItem("") for c in pricing.CATEGORIES}

        self.limits_header = rumps.MenuItem("📊  Usage Windows")
        self.win_session = rumps.MenuItem("")
        self.win_session_bar = rumps.MenuItem("")
        self.win_weekly = rumps.MenuItem("")
        self.win_weekly_bar = rumps.MenuItem("")

        self.updated = rumps.MenuItem("")
        self.refresh_item = rumps.MenuItem("🔄  Refresh now", callback=self._on_refresh_now)
        self.quit_item = rumps.MenuItem("🚪  Quit", callback=rumps.quit_application)

        self.menu = [
            self.session_header,
            self.session_tokens,
            self.session_cost,
            *[self.session_bd[c] for c in pricing.CATEGORIES],
            None,
            self.total_header,
            self.total_tokens,
            self.total_cost,
            *[self.total_bd[c] for c in pricing.CATEGORIES],
            None,
            self.limits_header,
            self.win_session,
            self.win_session_bar,
            self.win_weekly,
            self.win_weekly_bar,
            None,
            self.updated,
            self.refresh_item,
            self.quit_item,
        ]

        _style(self.session_header, "🎯  Current Session", bold=True)
        _style(self.total_header, "🌍  All Time", bold=True)
        _style(self.limits_header, "📊  Usage Windows", bold=True)
        _style(self.refresh_item, "🔄  Refresh now")
        _style(self.quit_item, "🚪  Quit")

        self.refresh(None)
        self._timer = rumps.Timer(self.refresh, config.REFRESH_SECONDS)
        self._timer.start()

    def _on_refresh_now(self, _):
        self.refresh(None)

    def _render_breakdown(self, items, breakdown):
        for cat in pricing.CATEGORIES:
            emoji, label = CAT_META[cat]
            vals = breakdown[cat]
            text = (
                f"        {emoji}  {label:<11} "
                f"{_fmt_tokens(vals['tokens'])}  ·  {_fmt_cost(vals['cost'])}"
            )
            _style(items[cat], text)

    def refresh(self, _):
        try:
            data = usage_reader.collect()
        except Exception as exc:  # never let the timer die
            _style(self.updated, f"⚠️  Error: {exc}")
            self.title = "⚠️"
            return

        session = data["session"]
        total = data["total"]
        win = data["windows"]

        # Menu bar: prefer the weekly window % if a limit is set; else the
        # session-window %; else the session (conversation) spend + tier.
        if win["weekly"]["pct"] is not None:
            p = win["weekly"]["pct"]
            self.title = f"{_pct_tier(p)} {p:.0f}%wk"
        elif win["session"]["pct"] is not None:
            p = win["session"]["pct"]
            self.title = f"{_pct_tier(p)} {p:.0f}%"
        else:
            self.title = f"{_cost_tier(session['cost'])} {_fmt_cost(session['cost'])}"

        # Current session (the active conversation) + cost breakdown.
        _style(self.session_tokens, f"     🪙  Tokens   {_fmt_tokens(session['tokens'])}")
        _style(self.session_cost, f"     💰  Cost     {_fmt_cost(session['cost'])}", bold=True)
        self._render_breakdown(self.session_bd, session["breakdown"])

        # All-time + cost breakdown.
        _style(self.total_tokens, f"     🪙  Tokens   {_fmt_tokens(total['tokens'])}")
        _style(self.total_cost, f"     💸  Cost     {_fmt_cost(total['cost'])}", bold=True)
        self._render_breakdown(self.total_bd, total["breakdown"])

        # Rolling usage windows.
        self._render_window(self.win_session, self.win_session_bar, "⏳", "Session",
                            f"{win['session']['hours']}h", win["session"])
        self._render_window(self.win_weekly, self.win_weekly_bar, "📅", "Weekly",
                            f"{win['weekly']['days']}d", win["weekly"])

        _style(self.updated, "⏱  Updated just now")

    def _render_window(self, row, bar_row, emoji, label, span, w):
        _style(
            row,
            f"     {emoji}  {label} ({span})   "
            f"{_fmt_tokens(w['tokens'])}  ·  {_fmt_cost(w['cost'])}",
            bold=True,
        )
        if w["pct"] is not None:
            _style(bar_row, f"        {_pct_tier(w['pct'])} {_bar(w['pct'])} {w['pct']:.1f}%")
        else:
            _style(bar_row, "        (set limit in config.py for %)")


if __name__ == "__main__":
    UsageBarApp().run()
