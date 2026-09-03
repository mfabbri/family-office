"""Workspace-local, explicit source bindings for Work Transition readiness.

This module creates metadata adapters; it never calculates, normalizes or changes the
selected snapshot.  The adapter supplies the binding object required by the readiness
contract while retaining an immutable reference and hash for the original snapshot.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

from family_office_engine.services.work_transition_readiness import INPUT_SCHEMA_VERSION


BINDING_SCHEMA_VERSION = "work-transition-source-binding/v1"
_ADAPTER_DIRECTORY = Path("planning") / "work-transition-source-bindings"
_CATEGORIES = {"employment_income", "spouse_income", "expenses", "net_worth", "liquidity", "rita_complementary_pension", "inps_pension", "spain_eu_pension", "other_income"}
_VALUE_BASES = {"gross", "net", "mixed", "not_applicable"}
_SOURCE_KINDS = {"documentary", "normalized", "derived", "manual"}
_LIQUIDITY_TIERS = {"immediate", "short_term", "notice_required", "locked_until_date", "illiquid", "unknown"}
_SCHEMA_OPTIONS = {
    "payroll/v1": (("employment_income", "net", "documentary"), ("spouse_income", "net", "documentary")),
    "lifecycle-expenses/v1": (("expenses", "net", "normalized"),),
    "net-worth/v1": (("net_worth", "not_applicable", "normalized"),),
    "liquidity-plan/v1": (("liquidity", "not_applicable", "derived"),),
    "rita-options/v1": (("rita_complementary_pension", "gross", "derived"),),
    "inps-pension/v1": (("inps_pension", "gross", "documentary"),),
    "it-es-eu-pension-pro-rata/v1": (("spain_eu_pension", "gross", "derived"),),
}


class WorkTransitionSourceBindingError(ValueError):
    pass


def discover_work_transition_sources(workspace: Path, required_inputs: list[dict[str, Any]]) -> dict[str, Any]:
    """Find recognized workspace-local snapshots and compatible requirement bindings."""
    snapshots_dir = workspace / "snapshots"
    snapshots: list[dict[str, Any]] = []
    if snapshots_dir.is_dir():
        for path in sorted(snapshots_dir.rglob("*.json")):
            candidate = _read_snapshot(path, workspace)
            if candidate is not None:
                snapshots.append(candidate)
    candidates: dict[str, list[dict[str, Any]]] = {}
    gaps: list[dict[str, Any]] = []
    for requirement in required_inputs:
        input_id = _text(requirement.get("input_id"), "required input id")
        compatible = [
            _candidate(snapshot, requirement)
            for snapshot in snapshots
            if _compatible(snapshot, requirement)
        ]
        candidates[input_id] = compatible
        if not compatible:
            gaps.append({"code": "missing_compatible_workspace_snapshot", "input_id": input_id, "blocking": bool(requirement.get("required", True)), "message": "No recognized workspace-local snapshot is compatible with this required input."})
        elif len(compatible) > 1:
            gaps.append({"code": "multiple_compatible_workspace_snapshots", "input_id": input_id, "blocking": False, "message": "Choose a source explicitly; no candidate was selected automatically.", "candidate_ids": [item["candidate_id"] for item in compatible]})
        for candidate in compatible:
            gaps.extend(candidate["metadata_gaps"])
    return {"snapshots": snapshots, "candidates_by_input": candidates, "data_gaps": gaps}


def bind_work_transition_source(
    manifest_path: Path,
    workspace: Path,
    *,
    input_id: str,
    candidate: dict[str, Any],
    overwrite: bool = False,
) -> dict[str, Any]:
    """Persist one explicit binding, allowing progressive wizard saves."""
    _inside_workspace(manifest_path, workspace, "Readiness manifest")
    manifest = _read_json(manifest_path, "work-transition readiness manifest")
    validate_work_transition_readiness_manifest(manifest)
    requirement = next((item for item in manifest.get("required_inputs", []) if item.get("input_id") == input_id), None)
    if not isinstance(requirement, dict):
        raise WorkTransitionSourceBindingError(f"Unknown readiness input: {input_id}")
    if candidate.get("input_id") != input_id:
        raise WorkTransitionSourceBindingError("Candidate does not belong to the selected readiness input")
    source_path = workspace / candidate["workspace_path"]
    _inside_workspace(source_path, workspace, "Selected snapshot")
    try:
        source = _read_json(source_path, "selected source snapshot")
    except WorkTransitionSourceBindingError as exc:
        raise WorkTransitionSourceBindingError("missing_source_snapshot: selected snapshot was deleted; run setup again") from exc
    if source.get("schema_version") != candidate.get("schema_version"):
        raise WorkTransitionSourceBindingError("Selected snapshot changed after discovery; run setup again")
    if _hash(source) != candidate.get("content_hash"):
        raise WorkTransitionSourceBindingError("source_snapshot_hash_mismatch: selected snapshot changed or was replaced; run setup again")
    source_id = _source_id(input_id, candidate["content_hash"])
    adapter_path = workspace / _ADAPTER_DIRECTORY / f"{source_id}.json"
    _inside_workspace(adapter_path, workspace, "Binding adapter")
    binding = {"category": candidate["category"], "member_id": candidate.get("member_id"), "value_basis": candidate["value_basis"]}
    adapter = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "record_type": "WorkTransitionSourceBinding",
        "as_of_date": source.get("as_of_date"),
        "source_snapshot": {"path": candidate["workspace_path"], "schema_version": candidate["schema_version"], "content_hash": candidate["content_hash"]},
        "bindings": {source_id: binding},
    }
    existing = [item for item in manifest.get("sources", []) if item.get("input_id") == input_id]
    if existing and not overwrite:
        raise WorkTransitionSourceBindingError(f"Input {input_id} already has a binding; use --overwrite to replace it")
    _write_json(adapter_path, adapter, "work-transition source binding adapter")
    relative_adapter = _relative(adapter_path, manifest_path.parent)
    source_entry = {
        "source_id": source_id,
        "input_id": input_id,
        "category": candidate["category"],
        "source_kind": candidate["source_kind"],
        "path": relative_adapter,
        "expected_schema_versions": [BINDING_SCHEMA_VERSION],
        "value_basis": candidate["value_basis"],
        "binding_pointer": f"/bindings/{source_id}",
        "provenance": {"origin": "workspace-local explicit source binding", "source_snapshot_path": candidate["workspace_path"], "source_schema_version": candidate["schema_version"], "source_content_hash": candidate["content_hash"]},
    }
    if candidate.get("member_id") is not None:
        source_entry["member_id"] = candidate["member_id"]
    for key in ("period", "stream_start_date", "stream_end_date", "liquidity_tier", "coverage_keys"):
        if key in candidate["metadata"]:
            source_entry[key] = candidate["metadata"][key]
    manifest["sources"] = [item for item in manifest.get("sources", []) if item.get("input_id") != input_id] + [source_entry]
    _write_json(manifest_path, manifest, "work-transition readiness manifest")
    return source_entry


def _read_snapshot(path: Path, workspace: Path) -> dict[str, Any] | None:
    try:
        data = _read_json(path, "workspace snapshot")
    except WorkTransitionSourceBindingError:
        return None
    schema_version = data.get("schema_version")
    if schema_version not in _SCHEMA_OPTIONS or not isinstance(data.get("as_of_date"), str):
        return None
    return {"workspace_path": _relative(path, workspace), "schema_version": schema_version, "as_of_date": data["as_of_date"], "content_hash": _hash(data), "metadata": _snapshot_metadata(data)}


def _compatible(snapshot: dict[str, Any], requirement: dict[str, Any]) -> bool:
    category = requirement.get("category")
    accepted = requirement.get("accepted_value_basis", ["gross", "net", "not_applicable"])
    return any(option_category == category and basis in accepted for option_category, basis, _ in _SCHEMA_OPTIONS[snapshot["schema_version"]])


def _candidate(snapshot: dict[str, Any], requirement: dict[str, Any]) -> dict[str, Any]:
    category = requirement["category"]
    value_basis, source_kind = next((basis, kind) for option_category, basis, kind in _SCHEMA_OPTIONS[snapshot["schema_version"]] if option_category == category and basis in requirement.get("accepted_value_basis", ["gross", "net", "not_applicable"]))
    member_id = requirement.get("member_id")
    metadata_gaps = _metadata_gaps(requirement, snapshot["metadata"])
    return {**snapshot, "candidate_id": f"{requirement['input_id']}:{snapshot['workspace_path']}", "input_id": requirement["input_id"], "category": category, "member_id": member_id, "value_basis": value_basis, "source_kind": source_kind, "metadata_gaps": metadata_gaps}


def _source_id(input_id: str, content_hash: str) -> str:
    label = re.sub(r"[^A-Za-z0-9._-]+", "_", input_id).strip("._-") or "input"
    input_hash = hashlib.sha256(input_id.encode("utf-8")).hexdigest()[:12]
    return f"{label[:48]}_{input_hash}_{content_hash[:12]}"


def validate_work_transition_readiness_manifest(manifest: dict[str, Any]) -> None:
    """Deterministic equivalent of the readiness-input JSON schema for setup input."""
    _exact_keys(manifest, {"schema_version", "record_type", "household_id", "as_of_date", "household_members", "freshness_policy", "required_inputs", "sources"}, {"schema_version", "record_type", "household_id", "as_of_date", "household_members", "required_inputs", "sources"}, "manifest")
    if manifest["schema_version"] != INPUT_SCHEMA_VERSION or manifest["record_type"] != "WorkTransitionReadinessInput":
        raise WorkTransitionSourceBindingError("Manifest must be work-transition-readiness-input/v1")
    _text(manifest["household_id"], "household_id"); _date_text(manifest["as_of_date"], "as_of_date")
    members = manifest["household_members"]
    if not isinstance(members, list) or not members or any(not isinstance(value, str) or not value for value in members) or len(members) != len(set(members)):
        raise WorkTransitionSourceBindingError("household_members must be a non-empty unique string array")
    if "freshness_policy" in manifest:
        policy = manifest["freshness_policy"]
        _exact_keys(policy, {"default_max_age_days", "max_age_days_by_category"}, set(), "freshness_policy")
        if "default_max_age_days" in policy and (not isinstance(policy["default_max_age_days"], int) or isinstance(policy["default_max_age_days"], bool) or policy["default_max_age_days"] < 0):
            raise WorkTransitionSourceBindingError("freshness_policy.default_max_age_days must be a non-negative integer")
        if "max_age_days_by_category" in policy and (not isinstance(policy["max_age_days_by_category"], dict) or any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in policy["max_age_days_by_category"].values())):
            raise WorkTransitionSourceBindingError("freshness_policy.max_age_days_by_category must contain non-negative integers")
    requirements = manifest["required_inputs"]
    if not isinstance(requirements, list) or not requirements:
        raise WorkTransitionSourceBindingError("required_inputs must be a non-empty array")
    seen = set()
    for item in requirements:
        _validate_requirement(item, members)
        if item["input_id"] in seen:
            raise WorkTransitionSourceBindingError(f"Duplicate required input id: {item['input_id']}")
        seen.add(item["input_id"])
    if not isinstance(manifest["sources"], list):
        raise WorkTransitionSourceBindingError("sources must be an array")
    for item in manifest["sources"]:
        _validate_source_entry(item)


def _snapshot_metadata(data: dict[str, Any]) -> dict[str, Any]:
    metadata = {}
    if isinstance(data.get("period"), dict) and _valid_period(data["period"]):
        metadata["period"] = {"start_date": data["period"]["start_date"], "end_date": data["period"]["end_date"]}
    for key in ("stream_start_date", "stream_end_date"):
        if isinstance(data.get(key), str) and _is_date(data[key]):
            metadata[key] = data[key]
    if data.get("liquidity_tier") in _LIQUIDITY_TIERS:
        metadata["liquidity_tier"] = data["liquidity_tier"]
    if isinstance(data.get("coverage_keys"), list) and all(isinstance(key, str) and key for key in data["coverage_keys"]):
        metadata["coverage_keys"] = sorted(set(data["coverage_keys"]))
    return metadata


def _metadata_gaps(requirement: dict[str, Any], metadata: dict[str, Any]) -> list[dict[str, Any]]:
    input_id = requirement["input_id"]
    gaps = []
    if requirement.get("required_period") and "period" not in metadata:
        gaps.append({"code": "missing_period_from_selected_snapshot", "input_id": input_id, "blocking": bool(requirement.get("required", True)), "message": "The snapshot does not declare its covered period; use a source with period metadata."})
    if requirement.get("requires_stream_bounds") and not {"stream_start_date", "stream_end_date"} <= metadata.keys():
        gaps.append({"code": "missing_stream_bounds_from_selected_snapshot", "input_id": input_id, "blocking": bool(requirement.get("required", True)), "message": "The snapshot does not declare stream_start_date and stream_end_date; regenerate it with explicit bounds."})
    if requirement.get("requires_liquid_asset") and "liquidity_tier" not in metadata:
        gaps.append({"code": "missing_liquidity_tier_from_selected_snapshot", "input_id": input_id, "blocking": bool(requirement.get("required", True)), "message": "The snapshot does not declare liquidity_tier; document whether the asset is available for the bridge."})
    return gaps


def _validate_requirement(item: Any, members: list[str]) -> None:
    _exact_keys(item, {"input_id", "category", "member_id", "required", "accepted_value_basis", "required_period", "requires_stream_bounds", "requires_liquid_asset"}, {"input_id", "category"}, "required_inputs item")
    _text(item["input_id"], "input_id")
    if item["category"] not in _CATEGORIES or ("member_id" in item and (not isinstance(item["member_id"], str) or item["member_id"] not in members)):
        raise WorkTransitionSourceBindingError("required input category or member_id is invalid")
    if "accepted_value_basis" in item and (not isinstance(item["accepted_value_basis"], list) or not item["accepted_value_basis"] or any(value not in _VALUE_BASES for value in item["accepted_value_basis"]) or len(item["accepted_value_basis"]) != len(set(item["accepted_value_basis"]))):
        raise WorkTransitionSourceBindingError("accepted_value_basis must contain supported values")
    if "required_period" in item and not _valid_period(item["required_period"]):
        raise WorkTransitionSourceBindingError("required_period must contain valid start_date and end_date")
    for key in ("required", "requires_stream_bounds", "requires_liquid_asset"):
        if key in item and not isinstance(item[key], bool):
            raise WorkTransitionSourceBindingError(f"{key} must be boolean")


def _validate_source_entry(item: Any) -> None:
    required = {"source_id", "input_id", "category", "source_kind", "path", "expected_schema_versions", "value_basis", "binding_pointer", "provenance"}
    allowed = required | {"member_id", "as_of_date", "period", "stream_start_date", "stream_end_date", "liquidity_tier", "coverage_keys"}
    _exact_keys(item, allowed, required, "sources item")
    _text(item["source_id"], "source_id"); _text(item["input_id"], "input_id")
    if item["category"] not in _CATEGORIES or item["source_kind"] not in _SOURCE_KINDS or item["value_basis"] not in _VALUE_BASES or not isinstance(item["path"], str) or not item["path"] or not isinstance(item["binding_pointer"], str) or not item["binding_pointer"].startswith("/"):
        raise WorkTransitionSourceBindingError("source entry has invalid category, kind, basis, path or binding_pointer")
    if not isinstance(item["expected_schema_versions"], list) or not item["expected_schema_versions"] or any(not isinstance(value, str) or not value for value in item["expected_schema_versions"]):
        raise WorkTransitionSourceBindingError("expected_schema_versions must be a non-empty string array")
    if not isinstance(item["provenance"], dict) or not isinstance(item["provenance"].get("origin"), str) or not item["provenance"]["origin"]:
        raise WorkTransitionSourceBindingError("source provenance.origin is required")
    if "member_id" in item and not isinstance(item["member_id"], str):
        raise WorkTransitionSourceBindingError("source member_id must be a string")
    if "as_of_date" in item:
        _date_text(item["as_of_date"], "source as_of_date")
    if "period" in item and not _valid_period(item["period"]):
        raise WorkTransitionSourceBindingError("source period must contain valid start_date and end_date")
    for key in ("stream_start_date", "stream_end_date"):
        if key in item:
            _date_text(item[key], f"source {key}")
    if "liquidity_tier" in item and item["liquidity_tier"] not in _LIQUIDITY_TIERS:
        raise WorkTransitionSourceBindingError("source liquidity_tier is invalid")
    if "coverage_keys" in item and (not isinstance(item["coverage_keys"], list) or any(not isinstance(key, str) for key in item["coverage_keys"]) or len(item["coverage_keys"]) != len(set(item["coverage_keys"]))):
        raise WorkTransitionSourceBindingError("source coverage_keys must be a unique string array")


def _exact_keys(value: Any, allowed: set[str], required: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) - allowed or required - set(value):
        raise WorkTransitionSourceBindingError(f"{label} does not match work-transition-readiness-input schema")


def _valid_period(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {"start_date", "end_date"} and _is_date(value["start_date"]) and _is_date(value["end_date"]) and value["start_date"] <= value["end_date"]


def _is_date(value: Any) -> bool:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def _date_text(value: Any, label: str) -> None:
    if not _is_date(value):
        raise WorkTransitionSourceBindingError(f"{label} must be an ISO date")


def _hash(data: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _relative(path: Path, base: Path) -> str:
    return Path(os.path.relpath(path, base)).as_posix()


def _inside_workspace(path: Path, workspace: Path, label: str) -> None:
    try:
        path.resolve().relative_to(workspace.resolve())
    except ValueError as exc:
        raise WorkTransitionSourceBindingError(f"{label} must stay inside the workspace.") from exc


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkTransitionSourceBindingError(f"Cannot read {label}: {path}") from exc
    if not isinstance(data, dict):
        raise WorkTransitionSourceBindingError(f"{label} must be a JSON object")
    return data


def _write_json(path: Path, data: dict[str, Any], label: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise WorkTransitionSourceBindingError(f"Cannot write {label}: {path}") from exc


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise WorkTransitionSourceBindingError(f"{label} must be a non-empty string")
    return value
