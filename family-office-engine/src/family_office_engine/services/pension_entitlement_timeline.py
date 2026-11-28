"""Fail-closed validator/builder for the candidate pension timeline v2 contract.

This module validates declared evidence metadata only.  It never derives a date,
amount, entitlement, effective date, or payment from other facts.
"""

import json
import hashlib
from datetime import date
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker, ValidationError


SCHEMA_VERSION = "pension-entitlement-timeline/v2"
EVENT_NAMES = (
    "eligibility_date",
    "requirements_met_date",
    "official_recognition_date",
    "economic_effective_date",
    "first_cash_payment_date",
)
SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "pension-entitlement-timeline-v2.schema.json"
_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


class PensionEntitlementTimelineError(ValueError):
    """Raised when a candidate timeline violates its fail-closed contract."""


def validate_pension_entitlement_timeline(
    value: dict[str, Any],
    *,
    workspace_root: Path | None = None,
    source_bytes: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Validate and return a v2 snapshot without changing its declared values."""
    if not isinstance(value, dict):
        raise PensionEntitlementTimelineError("Timeline snapshot must be a JSON object")
    try:
        Draft202012Validator(_SCHEMA, format_checker=FormatChecker()).validate(value)
    except ValidationError as exc:
        raise PensionEntitlementTimelineError(f"Invalid pension timeline v2 contract: {exc.message}") from exc

    if value.get("schema_version") != SCHEMA_VERSION:
        raise PensionEntitlementTimelineError("Unsupported pension timeline schema")
    workspace = _workspace_root() if workspace_root is None else workspace_root.resolve(strict=True)
    as_of = date.fromisoformat(value["as_of_date"])
    if value["status"] == "not_assessed" and not any(gap["severity"] == "blocking" for gap in value["data_gaps"]):
        raise PensionEntitlementTimelineError("not_assessed timeline requires a blocking data gap")
    for provenance in value["pension_amount_basis"]["source_evidence"]:
        _verify_provenance(provenance, workspace, as_of, source_bytes)
        _require_snapshot_coverage(
            provenance["coverage_assessment"], value["as_of_date"], "pension amount basis"
        )
    events = value["events"]
    for event_name in EVENT_NAMES:
        _validate_event(event_name, events[event_name], value["as_of_date"], as_of, workspace, source_bytes)
    return value


def build_pension_entitlement_timeline(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Read, validate and serialize a declared v2 snapshot; no inference is performed."""
    workspace = _workspace_root()
    _within_workspace(workspace, input_path, "input")
    _within_workspace(workspace, output_path, "output")
    try:
        value = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PensionEntitlementTimelineError(f"Cannot read timeline input: {exc}") from exc
    validated = validate_pension_entitlement_timeline(value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(validated, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return validated


def _validate_event(
    event_name: str, event: dict[str, Any], as_of_date: str, as_of: date,
    workspace: Path, source_bytes: Mapping[str, bytes] | None,
) -> None:
    if event.get("event_kind") != event_name:
        raise PensionEntitlementTimelineError(f"{event_name} event_kind must match its event key")
    status = event["status"]
    if status == "not_assessed":
        if event["date"] is not None or not any(gap["severity"] == "blocking" for gap in event["data_gaps"]):
            raise PensionEntitlementTimelineError(f"{event_name} not_assessed requires a null date and blocking data gap")
    elif status == "not_applicable":
        if event["date"] is not None or not event["evidence"]:
            raise PensionEntitlementTimelineError(f"{event_name} not_applicable requires scoped evidence and null date")
        for proof in event["evidence"]:
            provenance = proof["source_provenance"]
            _verify_provenance(provenance, workspace, as_of, source_bytes)
            _require_snapshot_coverage(
                provenance["coverage_assessment"], as_of_date, f"{event_name} non-applicability"
            )
            applicability = provenance["legal_applicability"]
            at_date = date.fromisoformat(as_of_date)
            valid_from = date.fromisoformat(applicability["valid_from"])
            valid_to = applicability["valid_to"]
            if at_date < valid_from or (valid_to is not None and at_date >= date.fromisoformat(valid_to)):
                raise PensionEntitlementTimelineError(f"{event_name} non-applicability evidence is not valid at as_of_date")
    else:
        if date.fromisoformat(event["date"]) > as_of:
            raise PensionEntitlementTimelineError(f"{event_name} future date cannot be represented as a supported fact")
        if any(gap["severity"] == "blocking" for gap in event["data_gaps"]):
            raise PensionEntitlementTimelineError(f"{event_name} supported event cannot retain a blocking data gap")
        for proof in event["evidence"]:
            provenance = proof["source_provenance"]
            coverage = provenance["coverage_assessment"]
            if not proof["evidence_ref"].startswith(f"{event_name}:"):
                raise PensionEntitlementTimelineError(f"{event_name} evidence_ref is bound to another event")
            if coverage["event_date"] != event["date"] or coverage["as_of_date"] != as_of_date:
                raise PensionEntitlementTimelineError(f"{event_name} evidence coverage is bound to another date")
            if coverage["coverage_status"] != "covered" or coverage["data_gaps"]:
                raise PensionEntitlementTimelineError(f"{event_name} supported evidence must be fully covered")
            applicability = provenance["legal_applicability"]
            event_date = date.fromisoformat(event["date"])
            valid_from = date.fromisoformat(applicability["valid_from"])
            valid_to = applicability["valid_to"]
            if event_date < valid_from or (valid_to is not None and event_date >= date.fromisoformat(valid_to)):
                raise PensionEntitlementTimelineError(f"{event_name} evidence is outside [valid_from, valid_to)")
    for proof in event["evidence"]:
        _verify_provenance(proof["source_provenance"], workspace, as_of, source_bytes)
        transition = proof["transition_scope"]
        inner_statuses = [item["scope"]["transition_status"] for item in transition["scope_evidence"]]
        gap_codes = {item["code"] for item in transition.get("data_gaps", [])}
        if transition["status"] == "unknown":
            if inner_statuses or not any(
                item["code"] == "transitional_branch_unknown" and item["severity"] == "blocking"
                for item in transition.get("data_gaps", [])
            ):
                raise PensionEntitlementTimelineError(f"{event_name} unknown transition scope requires a blocking gap and no resolved evidence")
        elif not inner_statuses or any(status != transition["status"] for status in inner_statuses) or "transitional_branch_unknown" in gap_codes:
            raise PensionEntitlementTimelineError(f"{event_name} resolved transition scope conflicts with its evidence")
        for scope_proof in transition["scope_evidence"]:
            _verify_provenance(scope_proof["source_provenance"], workspace, as_of, source_bytes)
            if scope_proof["scope"]["applies_to_event"] != event_name:
                raise PensionEntitlementTimelineError(f"{event_name} transition evidence is bound to another event")
            scope_coverage = scope_proof["source_provenance"]["coverage_assessment"]
            if scope_coverage["as_of_date"] != as_of_date:
                raise PensionEntitlementTimelineError(f"{event_name} transition evidence is bound to another as_of_date")
            if status in {"supported", "not_applicable"}:
                _require_snapshot_coverage(
                    scope_coverage, as_of_date, f"{event_name} transition evidence"
                )
            if status == "supported":
                if scope_coverage["event_date"] != event["date"] or scope_coverage["coverage_status"] != "covered":
                    raise PensionEntitlementTimelineError(f"{event_name} transition evidence is bound to another event date or is not covered")
            if status in {"supported", "not_applicable"}:
                applicability = scope_proof["source_provenance"]["legal_applicability"]
                coverage_date = date.fromisoformat(event["date"] if status == "supported" else as_of_date)
                valid_from = date.fromisoformat(applicability["valid_from"])
                valid_to = applicability["valid_to"]
                if coverage_date < valid_from or (valid_to is not None and coverage_date >= date.fromisoformat(valid_to)):
                    raise PensionEntitlementTimelineError(f"{event_name} transition evidence is outside [valid_from, valid_to) at the applicable date")


def _require_snapshot_coverage(coverage: dict[str, Any], as_of_date: str, label: str) -> None:
    if coverage["as_of_date"] != as_of_date:
        raise PensionEntitlementTimelineError(f"{label} coverage is not bound to snapshot as_of_date")
    status_fields = (
        "coverage_status",
        "event_date_coverage_status",
        "as_of_date_coverage_status",
    )
    if any(coverage[field] != "covered" for field in status_fields) or coverage["data_gaps"]:
        raise PensionEntitlementTimelineError(f"{label} evidence must be fully covered with no data gaps")


def _verify_provenance(
    provenance: dict[str, Any], workspace: Path, as_of: date, source_bytes: Mapping[str, bytes] | None = None,
) -> None:
    for field in ("retrieved_on", "reviewed_on"):
        if date.fromisoformat(provenance[field]) > as_of:
            raise PensionEntitlementTimelineError(f"source {field} cannot be later than as_of_date")
    coverage = provenance["coverage_assessment"]
    for field in ("event_date", "as_of_date", "assessed_on"):
        if date.fromisoformat(coverage[field]) > as_of:
            raise PensionEntitlementTimelineError(f"source coverage {field} cannot be later than as_of_date")
    source_path = _workspace_path(workspace, provenance["source_ref"])
    if source_bytes is None:
        if not source_path.is_file():
            raise PensionEntitlementTimelineError("source_ref does not resolve to a file inside family-office-workspace")
        payload = source_path.read_bytes()
    else:
        payload = source_bytes.get(provenance["source_ref"])
        if payload is None:
            raise PensionEntitlementTimelineError("source_ref has no captured workspace content")
    digest = hashlib.sha256(payload).hexdigest()
    if digest.lower() != provenance["digest_sha256"].lower():
        raise PensionEntitlementTimelineError("source_ref digest_sha256 does not match source content")


def _workspace_root() -> Path:
    root = Path(__file__).resolve().parents[4] / "family-office-workspace"
    resolved = root.resolve()
    if not resolved.is_dir():
        raise PensionEntitlementTimelineError("family-office-workspace root must exist")
    return resolved


def _workspace_path(workspace: Path, source_ref: str) -> Path:
    prefix = "workspace-ref:"
    if not isinstance(source_ref, str) or not source_ref.startswith(prefix):
        raise PensionEntitlementTimelineError("source_ref must use workspace-ref:<relative-path>")
    relative = source_ref[len(prefix):]
    if not relative or Path(relative).is_absolute() or PureWindowsPath(relative).is_absolute():
        raise PensionEntitlementTimelineError("source_ref must be a relative workspace path")
    candidate = (workspace / Path(relative.replace("\\", "/"))).resolve()
    _within_workspace(workspace, candidate, "source_ref")
    return candidate


def _within_workspace(workspace: Path, path: Path, label: str) -> None:
    try:
        path.resolve().relative_to(workspace)
    except ValueError as exc:
        raise PensionEntitlementTimelineError(f"timeline {label} must stay inside family-office-workspace") from exc
