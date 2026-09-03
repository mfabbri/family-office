"""Deterministic annual review over workspace-local snapshot metadata."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "annual-review/v1"
DEFAULT_REQUIRED_SOURCES = (
    "planning-goals/v1",
    "net-worth/v1",
    "lifecycle-expenses/v1",
    "pension-income/v1",
    "compliance-calendar/v1",
)


class AnnualReviewError(ValueError):
    """Raised when an annual review cannot be built safely."""


def build_annual_review(
    workspace_root: Path,
    review_year: int,
    as_of_date: str,
    output_path: Path | None = None,
    required_sources: Iterable[str] = DEFAULT_REQUIRED_SOURCES,
    freshness_days: int = 365,
) -> dict[str, Any]:
    workspace = _workspace(workspace_root)
    current = _date(as_of_date, "as_of_date")
    if review_year < 2000 or review_year > 9999:
        raise AnnualReviewError("review_year must be a four-digit year")
    if freshness_days < 0:
        raise AnnualReviewError("freshness_days must be non-negative")
    required = sorted(set(required_sources or DEFAULT_REQUIRED_SOURCES))
    if not required or any(not isinstance(item, str) or not item for item in required):
        raise AnnualReviewError("required_sources must contain non-empty schema versions")

    sources = _discover_sources(workspace, current, review_year, freshness_days)
    by_schema: dict[str, list[dict[str, Any]]] = {}
    for source in sources:
        by_schema.setdefault(source["schema_version"], []).append(source)
    gaps: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for schema in required:
        matches = by_schema.get(schema, [])
        if not matches:
            gaps.append({"code": "missing_annual_source", "source": schema, "action": f"Add or import {schema} before closing the annual review."})
            findings.append(_finding("missing_source", "high", schema, f"Required annual source {schema} is missing."))
            continue
        freshest = max(matches, key=lambda item: item.get("observed_date") or "")
        if freshest["freshness_status"] == "stale":
            gaps.append({"code": "stale_annual_source", "source": schema, "path": freshest["path"], "action": "Refresh the source and rerun the annual review."})
            findings.append(_finding("stale_source", "high", schema, f"Annual source {schema} is older than the declared freshness window."))
        if freshest["review_year_status"] == "outside_year":
            gaps.append({"code": "source_outside_review_year", "source": schema, "path": freshest["path"], "action": "Confirm the source period or add a source covering the review year."})
            findings.append(_finding("period_mismatch", "medium", schema, f"Annual source {schema} does not declare the review year."))
        if freshest["data_gap_count"]:
            gaps.append({"code": "source_has_data_gaps", "source": schema, "path": freshest["path"], "action": "Resolve or explicitly review the source data gaps."})
            findings.append(_finding("source_data_gaps", "medium", schema, f"Annual source {schema} reports unresolved data gaps."))

    events = _discover_events(workspace, review_year)
    for event in events:
        if event["kind"] == "residence_change":
            findings.append(_finding("residence_change", "high", event["path"], "A declared residence change requires a coordinated review of affected sources and obligations."))
        elif event["kind"] == "extraordinary_event":
            findings.append(_finding("extraordinary_event", "high", event["path"], "An extraordinary event requires an explicit contingency review."))
    if events:
        gaps.append({"code": "events_require_human_review", "event_count": len(events), "action": "Review the declared events with the appropriate human professional."})

    findings = sorted(findings, key=lambda item: (item["priority"], item["code"], item["reference"]))
    contingency = _contingency_actions(findings)
    status = "ready" if not gaps else "needs_review"
    kpis = [
        {"code": "required_source_coverage", "label": "Required source coverage", "value": sum(1 for schema in required if schema in by_schema), "target": len(required), "status": "complete" if not [g for g in gaps if g["code"] == "missing_annual_source"] else "incomplete"},
        {"code": "fresh_source_count", "label": "Fresh annual sources", "value": sum(1 for source in sources if source["freshness_status"] == "fresh"), "status": "observed"},
        {"code": "declared_event_count", "label": "Declared review events", "value": len(events), "status": "review_required" if events else "none_observed"},
        {"code": "data_gap_count", "label": "Actionable data gaps", "value": len(gaps), "status": "review_required" if gaps else "none"},
    ]
    metadata = {"review_year": review_year, "as_of_date": current.isoformat(), "required_sources": required, "freshness_days": freshness_days, "source_inventory": sources, "events": events}
    result = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "AnnualReview",
        "review_year": review_year,
        "as_of_date": current.isoformat(),
        "status": status,
        "question": "What should the family review this year, and with what priority?",
        "kpis": kpis,
        "source_inventory": sources,
        "events": events,
        "findings": findings,
        "risks": [{"code": item["code"], "priority": item["priority"], "description": item["message"]} for item in findings],
        "contingency_actions": contingency,
        "data_gaps": sorted(gaps, key=lambda item: (item["code"], item.get("source", ""))),
        "limitations": ["The review assesses metadata, freshness and declared events; it does not calculate tax, pension or financial values.", "Human review is required for material legal, tax, pension, financial or residence decisions."],
        "provenance": {"workspace_relative": True, "metadata_only": True, "hash_algorithm": "sha256", "content_hash": _hash(metadata)},
        "next_action": "Review the prioritized findings and refresh missing or stale sources." if gaps else "Schedule the next annual review and confirm the evidence with the household reviewer.",
    }
    output = (output_path or workspace / "snapshots" / "annual-review.snapshot.json").resolve()
    _within(workspace, output, "output")
    _write_atomic(output, result)
    return result


def _discover_sources(workspace: Path, current: date, review_year: int, freshness_days: int) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    snapshots = workspace / "snapshots"
    if not snapshots.is_dir():
        return sources
    for path in sorted(snapshots.rglob("*.json")):
        try:
            path.resolve().relative_to(workspace)
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if not isinstance(value, dict) or not isinstance(value.get("schema_version"), str):
            continue
        observed = _observed_date(value)
        age = (current - observed).days if observed else None
        gaps = value.get("data_gaps")
        sources.append({"path": path.resolve().relative_to(workspace).as_posix(), "schema_version": value["schema_version"], "observed_date": observed.isoformat() if observed else None, "review_year_status": "in_year" if observed and observed.year == review_year else "outside_year", "freshness_status": "fresh" if age is not None and age <= freshness_days else "stale", "data_gap_count": len(gaps) if isinstance(gaps, list) else 0, "status": value.get("status") if isinstance(value.get("status"), str) else "unknown"})
    return sources


def _discover_events(workspace: Path, review_year: int) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    snapshots = workspace / "snapshots"
    if not snapshots.is_dir():
        return events
    for path in sorted(snapshots.rglob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if not isinstance(value, dict) or not isinstance(value.get("events"), list):
            continue
        for item in value["events"]:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("event_type") or item.get("type") or item.get("category") or "").lower()
            event_date = _first_date(item.get("occurred_at") or item.get("date") or item.get("event_date"))
            if event_date and event_date.year == review_year and ("residen" in kind or "extraordinary" in kind or "straordin" in kind):
                events.append({"path": path.resolve().relative_to(workspace).as_posix(), "kind": "residence_change" if "residen" in kind else "extraordinary_event", "event_date": event_date.isoformat()})
    return events


def _observed_date(value: dict[str, Any]) -> date | None:
    for key in ("as_of_date", "observed_at", "generated_at", "verified_at"):
        candidate = _first_date(value.get(key))
        if candidate:
            return candidate
    return None


def _first_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _finding(code: str, priority: str, reference: str, message: str) -> dict[str, str]:
    return {"code": code, "priority": priority, "reference": reference, "message": message}


def _contingency_actions(findings: list[dict[str, str]]) -> list[dict[str, str]]:
    actions = []
    for finding in findings:
        action = {"action_id": f"review_{finding['code']}", "priority": finding["priority"], "trigger": finding["message"], "owner": "household_reviewer", "status": "open"}
        if action["action_id"] not in {item["action_id"] for item in actions}:
            actions.append(action)
    return actions


def _workspace(path: Path) -> Path:
    result = path.resolve()
    if not result.is_dir():
        raise AnnualReviewError(f"workspace path is not a directory: {path}")
    return result


def _within(root: Path, path: Path, label: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise AnnualReviewError(f"{label} path is outside workspace") from exc


def _date(value: Any, label: str) -> date:
    if not isinstance(value, str):
        raise AnnualReviewError(f"{label} must be ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise AnnualReviewError(f"{label} must be ISO date") from exc


def _hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _write_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    except OSError as exc:
        raise AnnualReviewError(f"cannot write annual review: {path}") from exc
