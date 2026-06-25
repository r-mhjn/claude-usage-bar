"""Pure data layer: read Claude Code JSONL logs and aggregate usage.

No UI knowledge here. `collect()` returns a plain dict so it can be tested
against synthetic fixtures independently of the menu bar app.
"""

import glob
import json
import os

import pricing

DEFAULT_PROJECTS_DIR = os.path.expanduser("~/.claude/projects")


def _iter_usage_records(projects_dir):
    """Yield (session_id, timestamp, model, usage) for every assistant
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


def collect(projects_dir=DEFAULT_PROJECTS_DIR):
    """Aggregate usage into session + all-time totals.

    Returns:
        {
          "session": {"tokens": int, "cost": float, "id": str | None},
          "total":   {"tokens": int, "cost": float},
        }
    "session" is the conversation (sessionId) with the most recent timestamp.
    """
    total_tokens = 0
    total_cost = 0.0

    # Per-session accumulators.
    sess_tokens = {}
    sess_cost = {}
    sess_latest = {}

    for session_id, timestamp, model, usage in _iter_usage_records(projects_dir):
        tokens = pricing.tokens_for(usage)
        cost = pricing.cost_for(model, usage)

        total_tokens += tokens
        total_cost += cost

        sess_tokens[session_id] = sess_tokens.get(session_id, 0) + tokens
        sess_cost[session_id] = sess_cost.get(session_id, 0.0) + cost
        if timestamp is not None:
            prev = sess_latest.get(session_id)
            if prev is None or timestamp > prev:
                sess_latest[session_id] = timestamp

    current_id = None
    if sess_latest:
        current_id = max(sess_latest, key=sess_latest.get)
    elif sess_tokens:
        # No timestamps anywhere — fall back to the heaviest session.
        current_id = max(sess_tokens, key=sess_tokens.get)

    return {
        "session": {
            "tokens": sess_tokens.get(current_id, 0),
            "cost": sess_cost.get(current_id, 0.0),
            "id": current_id,
        },
        "total": {
            "tokens": total_tokens,
            "cost": total_cost,
        },
    }
