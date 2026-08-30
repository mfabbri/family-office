"""Deterministic workspace-local compliance calendar and alerts."""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

POLICY_SCHEMA_VERSION = "compliance-calendar-policy/v1"
CALENDAR_SCHEMA_VERSION = "compliance-calendar/v1"
LOCAL_SCHEMA_VERSION = "compliance-calendar-local-events/v1"


class ComplianceCalendarError(ValueError):
    pass


def build_compliance_calendar(
    policy_path: Path, workspace_root: Path, as_of_date: str, output_path: Path | None = None
) -> dict[str, Any]:
    workspace = _workspace(workspace_root)
    policy = _read_json(policy_path, "compliance policy")
    _validate_policy(policy)
    current = _date(as_of_date, "as_of_date")
    output = (output_path or workspace / "snapshots" / "compliance-calendar.snapshot.json").resolve()
    _within(workspace, output, "output")
    local = _read_local_events(workspace)
    events = list(policy["events"]) + local["events"]
    _validate_unique_event_ids(events)
    entries, gaps = [], []
    for event in events:
        entry, event_gaps = _entry(event, current)
        entries.append(entry)
        gaps.extend(event_gaps)
    entries.sort(key=lambda item: (item["due_at"], item["event_id"]))
    alerts = _alerts(entries, current)
    result = {
        "schema_version": CALENDAR_SCHEMA_VERSION,
        "record_type": "ComplianceCalendar",
        "status": "ready" if not gaps else "needs_review",
        "as_of_date": current.isoformat(),
        "policy": {key: policy[key] for key in ("policy_id", "jurisdictions", "valid_from", "valid_to", "verified_at", "source_refs")},
        "entries": entries,
        "alerts": alerts,
        "data_gaps": sorted(gaps, key=lambda item: (item["code"], item["event_id"])),
        "summary": {"event_count": len(entries), "alert_count": len(alerts), "data_gap_count": len(gaps)},
    }
    _write_atomic(output, result)
    return result


def setup_workspace_compliance_event(workspace_root: Path, ask: Any) -> dict[str, Any]:
    """Save one user-confirmed local event; repeated setup adds further events."""
    workspace = _workspace(workspace_root)
    local = _read_local_events(workspace)
    title = ask("What review, renewal, or document deadline should be tracked? ").strip()
    if not title:
        return {"status": "unchanged", "event_count": len(local["events"]), "path": _local_path(workspace)}
    due_date = ask("Due date (YYYY-MM-DD): ").strip()
    _date(due_date, "due date")
    owner = ask("Responsible person or role [household]: ").strip() or "household"
    action = ask("Required action: ").strip()
    if not action:
        raise ComplianceCalendarError("required action cannot be empty")
    source = ask("Source or issuer (leave blank when not verified): ").strip() or None
    event_id = f"local-{len(local['events']) + 1:03d}"
    event = {
        "event_id": event_id, "title": title, "category": "workspace", "schedule": {"kind": "once", "date": due_date},
        "timezone": "Europe/Rome", "owner": owner, "required_action": action, "source_refs": [] if source is None else [source],
        "alert_offsets_days": [30, 7, 0],
    }
    local["events"].append(event)
    _write_atomic(_local_path(workspace), local)
    return {"status": "saved", "event_count": len(local["events"]), "path": _local_path(workspace)}


def _entry(event: dict[str, Any], current: date) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    zone = _zone(event.get("timezone"))
    due = _next_due(event["schedule"], current)
    due_at = datetime(due.year, due.month, due.day, 9, tzinfo=zone)
    gaps = []
    if not event["source_refs"]:
        gaps.append({"code": "source_not_verified", "event_id": event["event_id"], "action": "Record an authoritative source or explicitly waive this local reminder."})
    return ({
        "event_id": event["event_id"], "title": event["title"], "category": event["category"], "due_at": due_at.isoformat(),
        "timezone": event["timezone"], "owner": event["owner"], "required_action": event["required_action"],
        "source_refs": event["source_refs"], "alert_offsets_days": sorted(set(event["alert_offsets_days"])),
    }, gaps)


def _alerts(entries: list[dict[str, Any]], current: date) -> list[dict[str, Any]]:
    alerts, seen = [], set()
    for entry in entries:
        due = datetime.fromisoformat(entry["due_at"]).date()
        for offset in entry["alert_offsets_days"]:
            alert_date = due - timedelta(days=offset)
            if alert_date < current:
                continue
            key = (entry["event_id"], alert_date)
            if key in seen:
                continue
            seen.add(key)
            alerts.append({"alert_id": f"{entry['event_id']}@{alert_date.isoformat()}", "event_id": entry["event_id"], "alert_date": alert_date.isoformat(), "due_at": entry["due_at"], "owner": entry["owner"], "required_action": entry["required_action"], "source_refs": entry["source_refs"]})
    return sorted(alerts, key=lambda item: (item["alert_date"], item["event_id"]))


def _next_due(schedule: dict[str, Any], current: date) -> date:
    kind = schedule.get("kind")
    if kind == "once":
        return _date(schedule.get("date"), "schedule date")
    if kind == "annual":
        month, day = schedule.get("month"), schedule.get("day")
        try: candidate = date(current.year, month, day)
        except (TypeError, ValueError) as exc: raise ComplianceCalendarError("annual schedule requires a valid month and day") from exc
        return candidate if candidate >= current else date(current.year + 1, month, day)
    if kind == "last_business_day":
        month = schedule.get("month")
        if not isinstance(month, int) or not 1 <= month <= 12: raise ComplianceCalendarError("last_business_day schedule requires month 1..12")
        year = current.year
        for _ in range(2):
            candidate = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
            while candidate.weekday() >= 5: candidate -= timedelta(days=1)
            if candidate >= current: return candidate
            year += 1
    raise ComplianceCalendarError(f"unsupported schedule kind: {kind}")


def _validate_policy(policy: dict[str, Any]) -> None:
    if policy.get("schema_version") != POLICY_SCHEMA_VERSION: raise ComplianceCalendarError(f"policy schema_version must be {POLICY_SCHEMA_VERSION}")
    for field in ("policy_id", "valid_from", "verified_at"):
        if not isinstance(policy.get(field), str) or not policy[field]: raise ComplianceCalendarError(f"policy {field} is required")
    if not isinstance(policy.get("jurisdictions"), list) or not isinstance(policy.get("source_refs"), list) or not isinstance(policy.get("events"), list): raise ComplianceCalendarError("policy requires jurisdictions, source_refs and events lists")
    for event in policy["events"]:
        _validate_event(event)
    _validate_unique_event_ids(policy["events"])


def _validate_event(event: Any) -> None:
    if not isinstance(event, dict): raise ComplianceCalendarError("policy event must be an object")
    for field in ("event_id", "title", "category", "timezone", "owner", "required_action"):
        if not isinstance(event.get(field), str) or not event[field]: raise ComplianceCalendarError(f"event {field} is required")
    if not isinstance(event.get("schedule"), dict) or not isinstance(event.get("source_refs"), list): raise ComplianceCalendarError("event requires schedule and source_refs")
    offsets = event.get("alert_offsets_days")
    if not isinstance(offsets, list) or not all(isinstance(value, int) and value >= 0 for value in offsets): raise ComplianceCalendarError("event alert_offsets_days must be non-negative integers")
    _zone(event["timezone"])


def _validate_unique_event_ids(events: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    for event in events:
        event_id = event["event_id"]
        if event_id in ids:
            raise ComplianceCalendarError(f"duplicate event_id: {event_id}")
        ids.add(event_id)


def _read_local_events(workspace: Path) -> dict[str, Any]:
    path = _local_path(workspace)
    if not path.exists(): return {"schema_version": LOCAL_SCHEMA_VERSION, "record_type": "ComplianceCalendarLocalEvents", "events": []}
    data = _read_json(path, "local compliance events")
    if data.get("schema_version") != LOCAL_SCHEMA_VERSION or not isinstance(data.get("events"), list): raise ComplianceCalendarError(f"local events must be {LOCAL_SCHEMA_VERSION}")
    for event in data["events"]: _validate_event(event)
    _validate_unique_event_ids(data["events"])
    return data


def _local_path(workspace: Path) -> Path: return workspace / "snapshots" / "compliance-calendar.local-events.json"
def _workspace(path: Path) -> Path:
    result = path.resolve()
    if not result.is_dir(): raise ComplianceCalendarError(f"workspace path is not a directory: {path}")
    return result
def _within(root: Path, path: Path, label: str) -> None:
    try: path.relative_to(root)
    except ValueError as exc: raise ComplianceCalendarError(f"{label} path is outside workspace") from exc
def _read_json(path: Path, label: str) -> dict[str, Any]:
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise ComplianceCalendarError(f"cannot read {label}: {path}") from exc
    if not isinstance(data, dict): raise ComplianceCalendarError(f"{label} must be an object")
    return data
def _write_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(path.suffix + ".tmp")
    try: temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"); os.replace(temporary, path)
    except OSError as exc: raise ComplianceCalendarError(f"cannot write compliance calendar: {path}") from exc
def _date(value: Any, label: str) -> date:
    if not isinstance(value, str): raise ComplianceCalendarError(f"{label} must be ISO date")
    try: return date.fromisoformat(value)
    except ValueError as exc: raise ComplianceCalendarError(f"{label} must be ISO date") from exc
def _zone(value: Any) -> ZoneInfo:
    if not isinstance(value, str) or not value: raise ComplianceCalendarError("event timezone is required")
    try: return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc: raise ComplianceCalendarError(f"unknown timezone: {value}") from exc
