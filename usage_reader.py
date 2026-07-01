"""Pure data layer: read Claude Code JSONL logs and aggregate usage.

No UI knowledge here. `collect()` returns a plain dict so it can be tested
against synthetic fixtures independently of the menu bar app.
"""

import glob
import json
import os
from datetime import datetime, timedelta, timezone

import config
import pricing

DEFAULT_PROJECTS_DIR = os.path.expanduser("~/.claude/projects")


def _parse_ts(value):
    """Parse an ISO-8601 timestamp (with trailing 'Z') to an aware datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _iter_usage_records(projects_dir):
    """Yield (session_id, timestamp_str, model, usage) for every assistant
    message that carries token usage, deduped by (message.id, requestId)."""
    seen = set()
    pattern = os.path.join(projects_dir, "**", "*.jsonl")
    for path in glob.iglob(pattern, recursive=True):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except (ValueError, TypeError):
                        continue  # malformed line — skip, never crash

                    message = entry.get("message")
                    if not isinstance(message, dict):
                        continue
                    usage = message.get("usage")
                    if not isinstance(usage, dict):
                        continue  # user msgs, tool results, etc.

                    dedupe_key = (message.get("id"), entry.get("requestId"))
                    if dedupe_key != (None, None):
                        if dedupe_key in seen:
                            continue
                        seen.add(dedupe_key)

                    yield (
                        entry.get("sessionId"),
                        entry.get("timestamp"),
                        message.get("model"),
                        usage,
                    )
        except OSError:
            continue  # file vanished / unreadable — skip


def _empty_breakdown():
    return {cat: {"tokens": 0, "cost": 0.0} for cat in pricing.CATEGORIES}


def _add_breakdown(acc, bd):
    for cat, vals in bd.items():
        acc[cat]["tokens"] += vals["tokens"]
        acc[cat]["cost"] += vals["cost"]


def _pct(used, limit):
    if not limit:
        return None
    return 100.0 * used / limit


def collect(projects_dir=DEFAULT_PROJECTS_DIR, now=None):
    """Aggregate usage into session, all-time, and rolling-window views.

    Returns:
        {
          "session": {"id", "tokens", "cost", "breakdown"},
          "total":   {"tokens", "cost", "breakdown"},
          "windows": {
              "session": {"tokens","cost","limit","pct","hours"},
              "weekly":  {"tokens","cost","limit","pct","days"},
          },
        }
    "session" is the conversation (sessionId) with the most recent timestamp;
    the two windows are rolling 5-hour / 7-day spans ending at `now`.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    session_cutoff = now - timedelta(hours=config.SESSION_WINDOW_HOURS)
    weekly_cutoff = now - timedelta(days=config.WEEKLY_WINDOW_DAYS)

    total_bd = _empty_breakdown()
    sess_bd = {}          # session_id -> breakdown
    sess_latest = {}      # session_id -> latest timestamp string
    win_session = {"tokens": 0, "cost": 0.0}
    win_weekly = {"tokens": 0, "cost": 0.0}

    for session_id, ts_str, model, usage in _iter_usage_records(projects_dir):
        bd = pricing.breakdown_for(model, usage)
        tokens = pricing.tokens_for(usage)
        cost = sum(c["cost"] for c in bd.values())

        _add_breakdown(total_bd, bd)

        acc = sess_bd.get(session_id)
        if acc is None:
            acc = sess_bd[session_id] = _empty_breakdown()
        _add_breakdown(acc, bd)

        if ts_str is not None:
            prev = sess_latest.get(session_id)
            if prev is None or ts_str > prev:
                sess_latest[session_id] = ts_str

        ts = _parse_ts(ts_str)
        if ts is not None:
            if ts >= session_cutoff:
                win_session["tokens"] += tokens
                win_session["cost"] += cost
            if ts >= weekly_cutoff:
                win_weekly["tokens"] += tokens
                win_weekly["cost"] += cost

    def _summarize(bd):
        tokens = sum(c["tokens"] for c in bd.values())
        cost = sum(c["cost"] for c in bd.values())
        return tokens, cost

    # Pick the current session: latest by timestamp, else heaviest.
    current_id = None
    if sess_latest:
        current_id = max(sess_latest, key=sess_latest.get)
    elif sess_bd:
        current_id = max(sess_bd, key=lambda s: _summarize(sess_bd[s])[0])

    cur_bd = sess_bd.get(current_id, _empty_breakdown())
    cur_tokens, cur_cost = _summarize(cur_bd)
    tot_tokens, tot_cost = _summarize(total_bd)

    return {
        "session": {
            "id": current_id,
            "tokens": cur_tokens,
            "cost": cur_cost,
            "breakdown": cur_bd,
        },
        "total": {
            "tokens": tot_tokens,
            "cost": tot_cost,
            "breakdown": total_bd,
        },
        "windows": {
            "session": {
                "tokens": win_session["tokens"],
                "cost": win_session["cost"],
                "limit": config.SESSION_TOKEN_LIMIT,
                "pct": _pct(win_session["tokens"], config.SESSION_TOKEN_LIMIT),
                "hours": config.SESSION_WINDOW_HOURS,
            },
            "weekly": {
                "tokens": win_weekly["tokens"],
                "cost": win_weekly["cost"],
                "limit": config.WEEKLY_TOKEN_LIMIT,
                "pct": _pct(win_weekly["tokens"], config.WEEKLY_TOKEN_LIMIT),
                "days": config.WEEKLY_WINDOW_DAYS,
            },
        },
    }
