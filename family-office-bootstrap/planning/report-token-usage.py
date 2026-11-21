"""Offline token aggregation for Codex CLI `exec --json` NDJSON (never stores prompts).

Not an invoice, not a Work/Codex quota estimate, not a historical rollout parser.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")


def extract_usage(path: Path) -> tuple[dict[str, int], dict[str, dict[str, int]], int]:
    totals = defaultdict(int)
    models = defaultdict(lambda: defaultdict(int))
    turns = 0
    with path.open(encoding="utf-8-sig") as stream:
        for lineno, raw in enumerate(stream, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at line {lineno}: {error.msg}") from error
            if record.get("type") != "turn.completed":
                continue
            usage = record.get("usage")
            if not isinstance(usage, dict):
                continue
            model = record.get("model") or (record.get("metadata") or {}).get("model") or "unknown"
            if not isinstance(model, str):
                model = "unknown"
            turns += 1
            for field in FIELDS:
                value = usage.get(field, 0)
                if value is None:
                    value = 0
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(f"Bad {field} at line {lineno}")
                totals[field] += value
                models[model][field] += value
    return dict(totals), {k: dict(v) for k, v in models.items()}, turns


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="A captured `codex exec --json` NDJSON output, not full session rollout")
    parser.add_argument("--budget-tokens", type=int, default=None, help="Optional alert threshold on input+output")
    args = parser.parse_args()
    if args.budget_tokens is not None and args.budget_tokens <= 0:
        parser.error("budget must be positive")
    try:
        totals, models, turns = extract_usage(args.file)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if turns == 0:
        print("No turn.completed.usage events; no token totals available")
        return 2
    print(f"completed_turns={turns}")
    for field in FIELDS:
        print(f"{field}={totals.get(field, 0)}")
    print(f"uncached_input_tokens={totals.get('input_tokens', 0) - totals.get('cached_input_tokens', 0)}")
    combined = totals.get("input_tokens", 0) + totals.get("output_tokens", 0)
    print(f"processed_tokens={combined}")
    for model in sorted(models):
        vals = models[model]
        print(f"model={model} turns_usage={vals.get('input_tokens',0)+vals.get('output_tokens',0)}")
    if args.budget_tokens is not None:
        print("budget_status=" + ("OVER" if combined > args.budget_tokens else "WITHIN"))
    print("Note: cached is included in input; reasoning is included in output. Not money/cost or remaining Work quota.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
