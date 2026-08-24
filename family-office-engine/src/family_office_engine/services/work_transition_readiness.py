import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


INPUT_SCHEMA_VERSION = "work-transition-readiness-input/v1"
SCHEMA_VERSION = "work-transition-readiness/v1"
POLICY_VERSION = "work-transition-source-selection/v1"

SOURCE_PRECEDENCE = {
    "documentary": 400,
    "normalized": 300,
    "derived": 200,
    "manual": 100,
}
LIQUID_TIERS = {"immediate", "short_term"}
CATEGORIES = {
    "employment_income",
    "spouse_income",
    "expenses",
    "net_worth",
    "liquidity",
    "rita_complementary_pension",
    "inps_pension",
    "spain_eu_pension",
    "other_income",
}
VALUE_BASES = {"gross", "net", "mixed", "not_applicable"}


class WorkTransitionReadinessError(ValueError):
    pass


def build_work_transition_readiness(input_path: Path, output_path: Path) -> dict[str, Any]:
    manifest = _read_json(input_path, "work-transition readiness input")
    if manifest.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise WorkTransitionReadinessError(
            f"Unsupported work-transition readiness input schema: {manifest.get('schema_version')}"
        )
    if manifest.get("record_type") != "WorkTransitionReadinessInput":
        raise WorkTransitionReadinessError(f"Unsupported work-transition readiness record type: {manifest.get('record_type')}")

    as_of_date = _required_date(manifest.get("as_of_date"), "as_of_date")
    household_id = _required_string(manifest, "household_id")
    members = _household_members(manifest.get("household_members"))
    requirements = _requirements(manifest.get("required_inputs"), members)
    candidates = _candidates(manifest.get("sources"), input_path.parent)
    if "freshness_policy" in manifest and not isinstance(manifest["freshness_policy"], dict):
        raise WorkTransitionReadinessError("freshness_policy must be an object")
    freshness_policy = _freshness_policy(manifest.get("freshness_policy"))

    evaluated = [
        _evaluate_source(candidate, requirement, as_of_date, freshness_policy)
        for requirement in requirements
        for candidate in candidates
        if candidate["input_id"] == requirement["input_id"]
    ]

    selections: list[dict[str, Any]] = []
    data_gaps: list[dict[str, Any]] = []
    selected_by_id: dict[str, dict[str, Any]] = {}
    evaluated_ids: set[str] = set()

    for requirement in requirements:
        matching = [item for item in evaluated if item["input_id"] == requirement["input_id"]]
        evaluated_ids.update(item["source_id"] for item in matching)
        eligible = sorted(
            (item for item in matching if not item["exclusion_reasons"]),
            key=lambda item: (-item["precedence_rank"], -item["as_of_ordinal"], item["source_id"]),
        )
        selected = eligible[0] if eligible else None
        if selected is not None:
            selected["selection_status"] = "selected"
            selected_by_id[selected["source_id"]] = selected
            for alternative in eligible[1:]:
                alternative["exclusion_reasons"].append(
                    "lower_precedence" if alternative["precedence_rank"] < selected["precedence_rank"] else "older_or_tie_break"
                )
                if alternative["content_hash"] != selected["content_hash"]:
                    data_gaps.append(
                        _gap(
                            "conflicting_candidate_sources",
                            requirement["input_id"],
                            False,
                            f"Selected {selected['source_id']} and retained {alternative['source_id']} as an explicit conflict.",
                            source_ids=[selected["source_id"], alternative["source_id"]],
                        )
                    )
        elif requirement["required"]:
            reasons = sorted({reason for item in matching for reason in item["exclusion_reasons"]})
            data_gaps.append(
                _gap(
                    "missing_usable_required_input",
                    requirement["input_id"],
                    True,
                    "No candidate source satisfies the required input contract.",
                    reasons=reasons or ["no_candidate_source"],
                )
            )

        selections.append(
            {
                "input_id": requirement["input_id"],
                "category": requirement["category"],
                "member_id": requirement.get("member_id"),
                "required": requirement["required"],
                "status": "selected" if selected else "missing" if requirement["required"] else "not_available",
                "selected_source_id": selected["source_id"] if selected else None,
                "candidate_source_ids": [item["source_id"] for item in matching],
            }
        )

    for candidate in candidates:
        if candidate["source_id"] not in evaluated_ids:
            candidate["exclusion_reasons"] = ["unknown_input_id"]
            evaluated.append(candidate)
            data_gaps.append(
                _gap(
                    "source_without_requirement",
                    candidate["input_id"],
                    False,
                    f"Source {candidate['source_id']} does not map to a declared input requirement.",
                    source_ids=[candidate["source_id"]],
                )
            )

    _append_duplicate_coverage_gaps(selected_by_id.values(), data_gaps)
    blocking_count = sum(1 for gap in data_gaps if gap["blocking"])
    status = "blocked" if blocking_count else "partial" if data_gaps else "ready"
    public_sources = [_public_source(item) for item in sorted(evaluated, key=lambda item: item["source_id"])]
    core = {
        "household_id": household_id,
        "as_of_date": as_of_date.isoformat(),
        "status": status,
        "optimization_allowed": status != "blocked",
        "policy": {
            "policy_version": POLICY_VERSION,
            "precedence": list(SOURCE_PRECEDENCE),
            "default_max_age_days": freshness_policy["default_max_age_days"],
            "max_age_days_by_category": freshness_policy["max_age_days_by_category"],
            "conflicts_are_preserved": True,
        },
        "household_members": sorted(members),
        "input_selections": selections,
        "sources": public_sources,
        "data_gaps": sorted(data_gaps, key=lambda gap: (not gap["blocking"], gap["code"], gap["input_id"])),
        "summary": {
            "required_input_count": sum(1 for item in requirements if item["required"]),
            "selected_input_count": sum(1 for item in selections if item["status"] == "selected"),
            "source_count": len(candidates),
            "blocking_gap_count": blocking_count,
            "warning_count": len(data_gaps) - blocking_count,
        },
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "WorkTransitionReadinessSnapshot",
        **core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(core),
        },
        "notes": (
            "Readiness selects source snapshots and records lineage only. It performs no tax, pension, RITA, "
            "investment, work-exit date or LLM calculation."
        ),
    }
    _assert_output_scope(output_path)
    return _write_snapshot(snapshot, output_path)


def _household_members(value: Any) -> set[str]:
    if not isinstance(value, list) or not value:
        raise WorkTransitionReadinessError("household_members must contain at least one member id")
    members = {_required_text(item, f"household_members[{index}]") for index, item in enumerate(value)}
    if len(members) != len(value):
        raise WorkTransitionReadinessError("household_members must not contain duplicates")
    return members


def _requirements(value: Any, members: set[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise WorkTransitionReadinessError("required_inputs must contain at least one input")
    result = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise WorkTransitionReadinessError(f"required_inputs[{index}] must be an object")
        input_id = _required_string(item, "input_id", f"required_inputs[{index}]")
        if input_id in seen:
            raise WorkTransitionReadinessError(f"Duplicate required input id: {input_id}")
        seen.add(input_id)
        member_id = item.get("member_id")
        if member_id is not None and member_id not in members:
            raise WorkTransitionReadinessError(f"Unknown household member in {input_id}: {member_id}")
        accepted = item.get("accepted_value_basis", ["gross", "net", "not_applicable"])
        if not isinstance(accepted, list) or not accepted or any(basis not in VALUE_BASES for basis in accepted):
            raise WorkTransitionReadinessError(f"{input_id}.accepted_value_basis must not be empty")
        category = _required_string(item, "category", f"required_inputs[{index}]")
        if category not in CATEGORIES:
            raise WorkTransitionReadinessError(f"Unsupported category for {input_id}: {category}")
        for flag in ("required", "requires_stream_bounds", "requires_liquid_asset"):
            if flag in item and not isinstance(item[flag], bool):
                raise WorkTransitionReadinessError(f"{input_id}.{flag} must be boolean")
        period = _optional_period(item.get("required_period"), f"{input_id}.required_period")
        result.append(
            {
                "input_id": input_id,
                "category": category,
                "member_id": member_id,
                "required": item.get("required", True) is True,
                "accepted_value_basis": set(accepted),
                "required_period": period,
                "requires_stream_bounds": item.get("requires_stream_bounds", False) is True,
                "requires_liquid_asset": item.get("requires_liquid_asset", False) is True,
            }
        )
    return result


def _candidates(value: Any, manifest_dir: Path) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise WorkTransitionReadinessError("sources must be an array")
    result = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise WorkTransitionReadinessError(f"sources[{index}] must be an object")
        source_id = _required_string(item, "source_id", f"sources[{index}]")
        if source_id in seen:
            raise WorkTransitionReadinessError(f"Duplicate source id: {source_id}")
        seen.add(source_id)
        source_kind = _required_string(item, "source_kind", source_id)
        if source_kind not in SOURCE_PRECEDENCE:
            raise WorkTransitionReadinessError(f"Unsupported source_kind for {source_id}: {source_kind}")
        raw_path = _required_string(item, "path", source_id)
        normalized_path = Path(raw_path.replace("\\", "/"))
        resolved_path = normalized_path if normalized_path.is_absolute() else manifest_dir / normalized_path
        provenance = item.get("provenance")
        if not isinstance(provenance, dict):
            raise WorkTransitionReadinessError(f"{source_id}.provenance.origin is required")
        provenance = dict(provenance)
        provenance["origin"] = _required_text(provenance.get("origin"), f"{source_id}.provenance.origin")
        expected_schema_versions = item.get("expected_schema_versions", [])
        if not isinstance(expected_schema_versions, list) or not expected_schema_versions or any(
            not isinstance(version, str) or not version for version in expected_schema_versions
        ):
            raise WorkTransitionReadinessError(f"{source_id}.expected_schema_versions must be a non-empty array of strings")
        coverage_keys = item.get("coverage_keys", [])
        if not isinstance(coverage_keys, list) or any(not isinstance(key, str) or not key for key in coverage_keys):
            raise WorkTransitionReadinessError(f"{source_id}.coverage_keys must be an array of strings")
        category = _required_string(item, "category", source_id)
        if category not in CATEGORIES:
            raise WorkTransitionReadinessError(f"Unsupported category for {source_id}: {category}")
        value_basis = _required_string(item, "value_basis", source_id)
        if value_basis not in VALUE_BASES:
            raise WorkTransitionReadinessError(f"Unsupported value_basis for {source_id}: {value_basis}")
        result.append(
            {
                "source_id": source_id,
                "input_id": _required_string(item, "input_id", source_id),
                "category": category,
                "member_id": item.get("member_id"),
                "source_kind": source_kind,
                "precedence_rank": SOURCE_PRECEDENCE[source_kind],
                "path": raw_path.replace("\\", "/"),
                "resolved_path": resolved_path,
                "declared_as_of_date": item.get("as_of_date"),
                "expected_schema_versions": expected_schema_versions,
                "value_basis": value_basis,
                "binding_pointer": _required_string(item, "binding_pointer", source_id),
                "period": _optional_period(item.get("period"), f"{source_id}.period"),
                "stream_start_date": item.get("stream_start_date"),
                "stream_end_date": item.get("stream_end_date"),
                "liquidity_tier": item.get("liquidity_tier"),
                "coverage_keys": sorted(set(coverage_keys)),
                "provenance": provenance,
                "exclusion_reasons": [],
            }
        )
    return result


def _evaluate_source(
    candidate: dict[str, Any],
    requirement: dict[str, Any],
    as_of_date: date,
    freshness_policy: dict[str, Any],
) -> dict[str, Any]:
    item = dict(candidate)
    path = item["resolved_path"]
    try:
        source = _read_json(path, f"source {item['source_id']}")
    except WorkTransitionReadinessError:
        item.update({"schema_version": None, "content_hash": None, "as_of_date": None, "as_of_ordinal": 0, "age_days": None})
        item["exclusion_reasons"].append("missing_or_invalid_source_file")
        return item

    schema_version = source.get("schema_version")
    expected = item["expected_schema_versions"]
    if expected and schema_version not in expected:
        item["exclusion_reasons"].append("unexpected_schema_version")
    if item["category"] != requirement["category"]:
        item["exclusion_reasons"].append("manifest_category_mismatch")
    if item["member_id"] != requirement.get("member_id"):
        item["exclusion_reasons"].append("manifest_member_mismatch")
    binding = _json_pointer(source, item["binding_pointer"])
    if not isinstance(binding, dict):
        item["exclusion_reasons"].append("missing_source_binding")
    else:
        if binding.get("category") != requirement["category"]:
            item["exclusion_reasons"].append("source_binding_category_mismatch")
        if binding.get("member_id") != requirement.get("member_id"):
            item["exclusion_reasons"].append("source_binding_member_mismatch")
        if binding.get("value_basis") != item["value_basis"]:
            item["exclusion_reasons"].append("source_binding_value_basis_mismatch")
    embedded_as_of = source.get("as_of_date")
    declared_as_of = item["declared_as_of_date"]
    source_as_of = embedded_as_of or declared_as_of
    if embedded_as_of is not None and declared_as_of is not None and embedded_as_of != declared_as_of:
        item["exclusion_reasons"].append("as_of_date_mismatch")
    try:
        source_date = _required_date(source_as_of, f"{item['source_id']}.as_of_date")
        age_days = (as_of_date - source_date).days
        if age_days < 0:
            item["exclusion_reasons"].append("future_as_of_date")
        max_age = freshness_policy["max_age_days_by_category"].get(
            requirement["category"], freshness_policy["default_max_age_days"]
        )
        if age_days > max_age:
            item["exclusion_reasons"].append("stale_source")
    except WorkTransitionReadinessError:
        source_date = None
        age_days = None
        item["exclusion_reasons"].append("missing_or_invalid_as_of_date")

    if item["value_basis"] not in requirement["accepted_value_basis"]:
        item["exclusion_reasons"].append("incompatible_value_basis")
    if requirement["required_period"] and not _covers(item["period"], requirement["required_period"]):
        item["exclusion_reasons"].append("missing_required_period")
    if requirement["requires_stream_bounds"]:
        if not _valid_optional_date(item["stream_start_date"]) or not _valid_optional_date(item["stream_end_date"]):
            item["exclusion_reasons"].append("missing_stream_bounds")
        elif item["stream_start_date"] > item["stream_end_date"]:
            item["exclusion_reasons"].append("invalid_stream_bounds")
    if requirement["requires_liquid_asset"] and item["liquidity_tier"] not in LIQUID_TIERS:
        item["exclusion_reasons"].append("asset_not_liquid_for_bridge")

    canonical = json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    item.update(
        {
            "schema_version": schema_version,
            "content_hash": hashlib.sha256(canonical).hexdigest(),
            "as_of_date": source_date.isoformat() if source_date else None,
            "as_of_ordinal": source_date.toordinal() if source_date else 0,
            "age_days": age_days,
        }
    )
    item["exclusion_reasons"] = sorted(set(item["exclusion_reasons"]))
    return item


def _freshness_policy(value: Any) -> dict[str, Any]:
    value = value if isinstance(value, dict) else {}
    default = value.get("default_max_age_days", 365)
    by_category = value.get("max_age_days_by_category", {})
    if not isinstance(default, int) or isinstance(default, bool) or default < 0:
        raise WorkTransitionReadinessError("default_max_age_days must be a non-negative integer")
    if not isinstance(by_category, dict) or any(
        not isinstance(days, int) or isinstance(days, bool) or days < 0 for days in by_category.values()
    ):
        raise WorkTransitionReadinessError("max_age_days_by_category values must be non-negative integers")
    return {"default_max_age_days": default, "max_age_days_by_category": dict(sorted(by_category.items()))}


def _append_duplicate_coverage_gaps(selected: Any, gaps: list[dict[str, Any]]) -> None:
    owners: dict[str, list[str]] = {}
    for source in selected:
        for key in source["coverage_keys"]:
            owners.setdefault(key, []).append(source["source_id"])
    for key, source_ids in sorted(owners.items()):
        if len(source_ids) > 1:
            gaps.append(
                _gap(
                    "duplicate_selected_coverage",
                    key,
                    True,
                    f"Coverage key {key} is selected by multiple inputs and could be double counted.",
                    source_ids=sorted(source_ids),
                )
            )


def _public_source(item: dict[str, Any]) -> dict[str, Any]:
    selected = item.get("selection_status") == "selected"
    return {
        "source_id": item["source_id"],
        "input_id": item["input_id"],
        "selection_status": "selected" if selected else "excluded",
        "exclusion_reasons": [] if selected else sorted(set(item.get("exclusion_reasons", []))),
        "source_kind": item["source_kind"],
        "category": item["category"],
        "member_id": item["member_id"],
        "path": item["path"],
        "schema_version": item.get("schema_version"),
        "as_of_date": item.get("as_of_date"),
        "age_days": item.get("age_days"),
        "value_basis": item["value_basis"],
        "binding_pointer": item["binding_pointer"],
        "period": item["period"],
        "stream_start_date": item["stream_start_date"],
        "stream_end_date": item["stream_end_date"],
        "liquidity_tier": item["liquidity_tier"],
        "coverage_keys": item["coverage_keys"],
        "provenance": item["provenance"],
        "content_hash": item.get("content_hash"),
    }


def _gap(code: str, input_id: str, blocking: bool, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "input_id": input_id, "blocking": blocking, "message": message, **details}


def _optional_period(value: Any, label: str) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise WorkTransitionReadinessError(f"{label} must be an object")
    start = _required_date(value.get("start_date"), f"{label}.start_date")
    end = _required_date(value.get("end_date"), f"{label}.end_date")
    if start > end:
        raise WorkTransitionReadinessError(f"{label}.start_date must not be after end_date")
    return {"start_date": start.isoformat(), "end_date": end.isoformat()}


def _covers(actual: dict[str, str] | None, required: dict[str, str]) -> bool:
    return actual is not None and actual["start_date"] <= required["start_date"] and actual["end_date"] >= required["end_date"]


def _valid_optional_date(value: Any) -> bool:
    try:
        _required_date(value, "date")
    except WorkTransitionReadinessError:
        return False
    return True


def _json_pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        return None
    current = value
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return None
    return current


def _required_date(value: Any, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise WorkTransitionReadinessError(f"{label} must be an ISO date") from exc


def _required_string(data: dict[str, Any], key: str, label: str | None = None) -> str:
    return _required_text(data.get(key), f"{label + '.' if label else ''}{key}")


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkTransitionReadinessError(f"{label} must be a non-empty string")
    return value.strip()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkTransitionReadinessError(f"Cannot read {label}: {path}") from exc
    if not isinstance(data, dict):
        raise WorkTransitionReadinessError(f"{label} must be a JSON object")
    return data


def _write_snapshot(snapshot: dict[str, Any], output_path: Path) -> dict[str, Any]:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise WorkTransitionReadinessError(f"Cannot write work-transition readiness snapshot: {output_path}") from exc
    return snapshot


def _assert_output_scope(output_path: Path) -> None:
    workspace_root = _workspace_root()
    try:
        output_path.resolve().relative_to(workspace_root.resolve())
    except ValueError as exc:
        raise WorkTransitionReadinessError(
            "Work-transition readiness output must stay inside family-office-workspace."
        ) from exc


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[4] / "family-office-workspace"


def _content_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
