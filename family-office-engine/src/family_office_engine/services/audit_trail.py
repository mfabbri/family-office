"""Local append-only audit events and approval replay.

The log stores references and hashes, never document contents or free-form
personal data.  Every line is chained to the previous one so verification can
detect edits, deletion, insertion and reordering.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "audit-event/v1"
GENESIS = "0" * 64
MAX_CLOCK_SKEW_SECONDS = 300
ALLOWED_TYPES = {"import", "assumption_change", "recommendation", "approval", "revocation"}


class AuditTrailError(ValueError):
    """Raised for invalid, unsafe or tampered audit data."""


def _inside(path: Path, workspace: Path) -> Path:
    resolved, root = path.resolve(), workspace.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AuditTrailError("audit log must remain inside the workspace") from exc
    return resolved


def _timestamp(value: str | None, now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    if value is None:
        return current.isoformat().replace("+00:00", "Z")
    if not isinstance(value, str):
        raise AuditTrailError("occurred_at must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuditTrailError("occurred_at must be an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise AuditTrailError("occurred_at must include a timezone")
    if (parsed - current).total_seconds() > MAX_CLOCK_SKEW_SECONDS:
        raise AuditTrailError("occurred_at exceeds allowed clock skew")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\n" in value or "\r" in value:
        raise AuditTrailError(f"{field} must be a non-empty single-line string")
    return value.strip()


def _hash(event: Mapping[str, Any]) -> str:
    encoded = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AuditTrailError("cannot read audit log") from exc
    events: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AuditTrailError("audit log contains invalid JSON") from exc
        if not isinstance(item, dict):
            raise AuditTrailError("audit log event must be an object")
        events.append(item)
    return events


def verify_audit_log(path: Path, workspace: Path) -> dict[str, Any]:
    destination = _inside(path, workspace)
    events = _read(destination)
    previous = GENESIS
    for expected_sequence, event in enumerate(events, 1):
        if event.get("schema_version") != SCHEMA_VERSION or event.get("sequence") != expected_sequence:
            raise AuditTrailError("audit log sequence or schema is invalid")
        if event.get("previous_hash") != previous:
            raise AuditTrailError("audit log chain is tampered")
        stored = event.get("event_hash")
        unsigned = {key: value for key, value in event.items() if key != "event_hash"}
        if not isinstance(stored, str) or stored != _hash(unsigned):
            raise AuditTrailError("audit event hash is invalid")
        previous = stored
    return {"schema_version": "audit-verification/v1", "status": "valid", "event_count": len(events), "last_hash": previous, "path": str(destination)}


def append_audit_event(
    path: Path,
    workspace: Path,
    *,
    event_type: str,
    actor: str,
    subject_id: str,
    action: str,
    reference: str,
    occurred_at: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    destination = _inside(path, workspace)
    if event_type not in ALLOWED_TYPES:
        raise AuditTrailError("unsupported event_type")
    event = {
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "sequence": 0,
        "event_type": event_type,
        "actor": _text(actor, "actor"),
        "subject_id": _text(subject_id, "subject_id"),
        "action": _text(action, "action"),
        "reference": _text(reference, "reference"),
        "occurred_at": _timestamp(occurred_at, now),
    }
    verify = verify_audit_log(destination, workspace)
    event["sequence"] = verify["event_count"] + 1
    event["previous_hash"] = verify["last_hash"]
    event["event_hash"] = _hash(event)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, sort_keys=True, ensure_ascii=True) + "\n")
    except OSError as exc:
        raise AuditTrailError("cannot append audit event") from exc
    return event


def replay_audit(path: Path, workspace: Path) -> dict[str, Any]:
    verification = verify_audit_log(path, workspace)
    events = _read(_inside(path, workspace))
    approvals: dict[str, dict[str, Any]] = {}
    for event in events:
        subject = event["subject_id"]
        if event["event_type"] == "approval" and event["action"] == "approve":
            approvals[subject] = {"status": "approved", "event_id": event["event_id"], "actor": event["actor"]}
        elif event["event_type"] == "revocation" and event["action"] == "revoke" and subject in approvals:
            approvals[subject] = {"status": "revoked", "event_id": event["event_id"], "actor": event["actor"]}
    return {"schema_version": "audit-replay/v1", "status": "replayed", "event_count": verification["event_count"], "approvals": approvals, "path": verification["path"]}
