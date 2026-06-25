"""Model pricing table and cost computation.

Rates are USD per 1,000,000 tokens, sourced from Anthropic public pricing.
Cache multipliers (relative to the input rate):
  - cache write, 5-minute TTL : 1.25x
  - cache write, 1-hour TTL   : 2.00x
  - cache read                : 0.10x
"""

CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.00
CACHE_READ_MULT = 0.10

# (input_per_mtok, output_per_mtok) keyed by a substring of the model id.
# Matched longest-prefix-ish via _match() below, so order is not significant.
PRICING = {
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-opus-4-5": (5.0, 25.0),
    "claude-opus-4-1": (15.0, 75.0),
    "claude-opus-4-0": (15.0, 75.0),
    "claude-opus-4": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-3-5-haiku": (0.80, 4.0),
    "claude-3-5-sonnet": (3.0, 15.0),
    "claude-3-opus": (15.0, 75.0),
    "claude-3-haiku": (0.25, 1.25),
}

_MILLION = 1_000_000.0


def _match(model):
    """Return (input_rate, output_rate) for a model id, or None if unknown."""
    if not model:
        return None
    # Prefer the most specific (longest) key that the model id contains.
    best = None
    for key in sorted(PRICING, key=len, reverse=True):
        if key in model:
            best = PRICING[key]
            break
    return best


def cost_for(model, usage):
    """Cost in USD for one assistant message's token usage.

    `usage` is the raw dict from message.usage. Unknown models cost $0
    (tokens are still counted elsewhere) so a new model never crashes the app.
    """
    rates = _match(model)
    if rates is None:
        return 0.0
    input_rate, output_rate = rates

    input_tokens = usage.get("input_tokens", 0) or 0
    output_tokens = usage.get("output_tokens", 0) or 0
    cache_read = usage.get("cache_read_input_tokens", 0) or 0

    # Split cache creation into 5m / 1h when the breakdown is present;
    # otherwise treat the whole amount as 5m writes.
    breakdown = usage.get("cache_creation") or {}
    write_5m = breakdown.get("ephemeral_5m_input_tokens")
    write_1h = breakdown.get("ephemeral_1h_input_tokens")
    if write_5m is None and write_1h is None:
        write_5m = usage.get("cache_creation_input_tokens", 0) or 0
        write_1h = 0
    else:
        write_5m = write_5m or 0
        write_1h = write_1h or 0

    cost = (
        input_tokens * input_rate
        + output_tokens * output_rate
        + write_5m * input_rate * CACHE_WRITE_5M_MULT
        + write_1h * input_rate * CACHE_WRITE_1H_MULT
        + cache_read * input_rate * CACHE_READ_MULT
    )
    return cost / _MILLION


def tokens_for(usage):
    """Total token count for one message (all four token classes)."""
    return (
        (usage.get("input_tokens", 0) or 0)
        + (usage.get("output_tokens", 0) or 0)
        + (usage.get("cache_creation_input_tokens", 0) or 0)
        + (usage.get("cache_read_input_tokens", 0) or 0)
    )
