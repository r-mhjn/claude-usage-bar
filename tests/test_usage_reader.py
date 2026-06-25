import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pricing
import usage_reader


def _assistant_line(session, ts, model, usage, msg_id="m1", req_id="r1"):
    return json.dumps(
        {
            "sessionId": session,
            "timestamp": ts,
            "requestId": req_id,
            "type": "assistant",
            "message": {"id": msg_id, "model": model, "usage": usage},
        }
    )


def _write(dirpath, name, lines):
    path = os.path.join(dirpath, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


class PricingTest(unittest.TestCase):
    def test_basic_input_output_cost(self):
        usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
        # Opus: $5 input + $25 output per 1M
        self.assertAlmostEqual(pricing.cost_for("claude-opus-4-6", usage), 30.0)

    def test_cache_tokens_priced(self):
        usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_input_tokens": 1_000_000,  # 0.1x * $5 = $0.50
            "cache_creation": {
                "ephemeral_5m_input_tokens": 1_000_000,  # 1.25x * $5 = $6.25
                "ephemeral_1h_input_tokens": 0,
            },
        }
        self.assertAlmostEqual(pricing.cost_for("claude-opus-4-6", usage), 6.75)

    def test_cache_creation_without_breakdown(self):
        usage = {"cache_creation_input_tokens": 1_000_000}  # treated as 5m
        self.assertAlmostEqual(pricing.cost_for("claude-sonnet-4-6", usage), 3.0 * 1.25)

    def test_unknown_model_costs_zero(self):
        usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
        self.assertEqual(pricing.cost_for("some-future-model", usage), 0.0)

    def test_tokens_for_sums_all_classes(self):
        usage = {
            "input_tokens": 1,
            "output_tokens": 2,
            "cache_creation_input_tokens": 4,
            "cache_read_input_tokens": 8,
        }
        self.assertEqual(pricing.tokens_for(usage), 15)


class CollectTest(unittest.TestCase):
    def test_empty_dir_returns_zeros(self):
        with tempfile.TemporaryDirectory() as d:
            data = usage_reader.collect(d)
        self.assertEqual(data["total"]["tokens"], 0)
        self.assertEqual(data["total"]["cost"], 0.0)
        self.assertIsNone(data["session"]["id"])

    def test_dedupe_by_message_and_request_id(self):
        with tempfile.TemporaryDirectory() as d:
            usage = {"input_tokens": 1_000_000}
            line = _assistant_line("s1", "2026-01-01T00:00:00Z", "claude-opus-4-6", usage)
            # Same (msg_id, req_id) written twice -> counted once.
            _write(d, "a.jsonl", [line, line])
            data = usage_reader.collect(d)
        self.assertEqual(data["total"]["tokens"], 1_000_000)
        self.assertAlmostEqual(data["total"]["cost"], 5.0)

    def test_malformed_lines_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            good = _assistant_line("s1", "2026-01-01T00:00:00Z", "claude-haiku-4-5",
                                   {"input_tokens": 1_000_000})
            _write(d, "a.jsonl", ["{not json", "", good, '{"no":"message"}'])
            data = usage_reader.collect(d)
        self.assertEqual(data["total"]["tokens"], 1_000_000)

    def test_session_is_latest_by_timestamp(self):
        with tempfile.TemporaryDirectory() as d:
            old = _assistant_line("old", "2026-01-01T00:00:00Z", "claude-opus-4-6",
                                  {"input_tokens": 5_000_000}, msg_id="mo", req_id="ro")
            new = _assistant_line("new", "2026-06-01T00:00:00Z", "claude-opus-4-6",
                                  {"input_tokens": 1_000_000}, msg_id="mn", req_id="rn")
            _write(d, "a.jsonl", [old, new])
            data = usage_reader.collect(d)
        self.assertEqual(data["session"]["id"], "new")
        self.assertEqual(data["session"]["tokens"], 1_000_000)
        # Total spans both sessions.
        self.assertEqual(data["total"]["tokens"], 6_000_000)

    def test_session_sums_multiple_messages(self):
        with tempfile.TemporaryDirectory() as d:
            m1 = _assistant_line("s1", "2026-06-01T00:00:00Z", "claude-haiku-4-5",
                                 {"input_tokens": 1_000_000}, msg_id="m1", req_id="r1")
            m2 = _assistant_line("s1", "2026-06-01T00:01:00Z", "claude-haiku-4-5",
                                 {"output_tokens": 1_000_000}, msg_id="m2", req_id="r2")
            _write(d, "a.jsonl", [m1, m2])
            data = usage_reader.collect(d)
        self.assertEqual(data["session"]["id"], "s1")
        self.assertEqual(data["session"]["tokens"], 2_000_000)
        # Haiku: $1 input + $5 output
        self.assertAlmostEqual(data["session"]["cost"], 6.0)


if __name__ == "__main__":
    unittest.main()
