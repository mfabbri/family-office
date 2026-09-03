"""Validate the operational guardrails recorded in current-work.json.

This is a deterministic close gate for the controller process. It cannot control
the host's agent runtime, but it prevents a session from being reported complete
without concrete evidence or from silently exceeding the delegation budget.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLANNER = ROOT / "family-office-bootstrap" / "planning" / "current-work.json"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> int:
    try:
        planner = json.loads(PLANNER.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read planner: {exc}")

    status = planner.get("status")
    if status not in {"selected", "in_progress", "blocked", "completed", "superseded"}:
        fail(f"unsupported planner status: {status!r}")

    routing = planner.get("routing") or {}
    trace = routing.get("trace") or []
    if not isinstance(trace, list):
        fail("routing.trace must be an array")
    substantial_events = [item for item in trace if item.get("event") in {"delegated", "escalated"}]
    if len(substantial_events) > 2:
        fail("delegation budget exceeded: at most two delegated/escalated events")

    if status in {"selected", "in_progress", "blocked"}:
        next_action = planner.get("next_action") or {}
        if not next_action.get("description"):
            fail("active planner has no concrete next_action description")
        if next_action.get("mode") == "select":
            fail("active planner cannot remain in select mode")

    if status == "completed":
        verification = planner.get("verification") or {}
        if verification.get("result") != "passed":
            fail("completed planner requires verification.result=passed")
        if not verification.get("tests"):
            fail("completed planner requires test evidence")
        review = planner.get("review") or {}
        task_class = (planner.get("routing") or {}).get("task_class", "")
        if task_class in {"cross-module", "cross-repository", "cross-repository-architecture"} and review.get("status") != "approved":
            fail("cross-module completed planner requires approved review")
        if planner.get("blockers"):
            fail("completed planner cannot retain unresolved blockers")

    print(f"OK: execution guardrails status={status}, substantial_events={len(substantial_events)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
