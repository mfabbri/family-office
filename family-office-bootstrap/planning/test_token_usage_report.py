from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("report-token-usage.py")
spec = importlib.util.spec_from_file_location("fo_token_report", MODULE)
report = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(report)


class TokenUsageReportTests(unittest.TestCase):
    def test_counts_only_completed_turn_usage_and_cache_as_subset(self):
        records = [
            {"type": "thread.started", "thread_id": "abc"},
            {"type": "turn.completed", "model": "gpt-6-luna", "usage": {"input_tokens": 1000, "cached_input_tokens": 700, "output_tokens": 120, "reasoning_output_tokens": 40}},
            {"type": "item.completed", "usage": {"input_tokens": 10000}},
            {"type": "turn.completed", "model": "gpt-6-luna", "usage": {"input_tokens": 200, "cached_input_tokens": 0, "output_tokens": 30}},
        ]
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "codex.ndjson"
            p.write_text("\n".join(json.dumps(e) for e in records), encoding="utf-8")
            totals, models, turns = report.extract_usage(p)
        self.assertEqual(turns, 2)
        self.assertEqual((totals["input_tokens"], totals["cached_input_tokens"], totals["output_tokens"]), (1200, 700, 150))
        self.assertEqual(models["gpt-6-luna"]["reasoning_output_tokens"], 40)

    def test_negative_tokens_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "invalid.ndjson"
            p.write_text(json.dumps({"type":"turn.completed", "usage":{"input_tokens":-1}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                report.extract_usage(p)


if __name__ == "__main__":
    unittest.main()
