import copy
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "sensitivity-analysis/v1"
INPUT_RECORD_TYPE = "SensitivityAnalysisInput"
SNAPSHOT_RECORD_TYPE = "SensitivityAnalysisSnapshot"
DECISION_SCENARIO_SCHEMA_VERSION = "decision-scenario/v2"


class SensitivityAnalysisError(ValueError):
    pass


def build_sensitivity_analysis(
    decision_scenario_snapshot_path: Path,
    sensitivity_input_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    decision_scenario = _read_decision_scenario(decision_scenario_snapshot_path)
    sensitivity_input = _read_sensitivity_input(sensitivity_input_path)
    seed = sensitivity_input.get("seed", 0)
    if not isinstance(seed, int):
        raise SensitivityAnalysisError("seed must be an integer")

    data_gaps: list[dict[str, Any]] = []
    sensitivity_cases = [
        _build_case(decision_scenario, sensitivity, data_gaps)
        for sensitivity in _sorted_items(sensitivity_input.get("sensitivities", []))
    ]
    stress_matrix = [
        _build_stress_case(decision_scenario, stress, sensitivity_cases, data_gaps)
        for stress in _sorted_items(sensitivity_input.get("stress_scenarios", []))
    ]
    source_gaps = _source_gaps(decision_scenario)
    data_gaps.extend(source_gaps)

    analysis_core = {
        "analysis_id": sensitivity_input["analysis_id"],
        "label": sensitivity_input["label"],
        "as_of_date": sensitivity_input["as_of_date"],
        "seed": seed,
        "sources": {
            "decision_scenario": {
                "path": str(decision_scenario_snapshot_path),
                "schema_version": decision_scenario.get("schema_version"),
                "record_type": decision_scenario.get("record_type"),
                "status": decision_scenario.get("status"),
                "content_hash": _nested_or_none(
                    decision_scenario,
                    ("reproducibility", "content_hash"),
                ),
            }
        },
        "base_scenario": {
            "scenario_id": decision_scenario.get("scenario_id"),
            "label": decision_scenario.get("label"),
            "as_of_date": decision_scenario.get("as_of_date"),
            "status": decision_scenario.get("status"),
        },
        "sensitivity_cases": sensitivity_cases,
        "tornado_data": _tornado_data(sensitivity_cases),
        "stress_matrix": stress_matrix,
        "data_gaps": data_gaps,
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "complete" if not data_gaps else "partial",
        **analysis_core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(analysis_core),
        },
        "notes": (
            "Sensitivity analysis V1 applies explicit deterministic perturbations to decision-scenario/v2 "
            "assumptions. It does not run simulations, calculate taxes, returns, pension entitlements, "
            "scores or recommendations."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise SensitivityAnalysisError(f"Cannot write sensitivity analysis snapshot: {output_path}") from exc
    return snapshot


def _read_decision_scenario(path: Path) -> dict[str, Any]:
    snapshot = _read_json(path, "decision scenario snapshot")
    if snapshot.get("schema_version") != DECISION_SCENARIO_SCHEMA_VERSION:
        raise SensitivityAnalysisError(
            "Unsupported decision scenario schema: "
            f"{snapshot.get('schema_version')}; expected {DECISION_SCENARIO_SCHEMA_VERSION}"
        )
    return snapshot


def _read_sensitivity_input(path: Path) -> dict[str, Any]:
    data = _read_json(path, "sensitivity analysis input")
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported sensitivity analysis input schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported sensitivity analysis input record type: {data.get('record_type')}")
    for field in ("analysis_id", "label", "as_of_date"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            errors.append(f"{field} is required")
    if not isinstance(data.get("sensitivities"), list) or not data["sensitivities"]:
        errors.append("sensitivities must be a non-empty list")
    if not isinstance(data.get("stress_scenarios", []), list):
        errors.append("stress_scenarios must be a list")
    if errors:
        raise SensitivityAnalysisError("; ".join(errors))
    return data


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SensitivityAnalysisError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SensitivityAnalysisError(f"Invalid JSON in {label}: {path}") from exc
    if not isinstance(data, dict):
        raise SensitivityAnalysisError(f"{label} must contain a JSON object: {path}")
    return data


def _build_case(
    decision_scenario: dict[str, Any],
    sensitivity: dict[str, Any],
    data_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    sensitivity_id = _required_text(sensitivity, "id", "sensitivity")
    path = _path(sensitivity)
    operation = _required_text(sensitivity, "operation", sensitivity_id)
    variant = copy.deepcopy(decision_scenario)
    gap_count_before = len(data_gaps)
    try:
        base_value = _get_path(variant, path)
        changed_value, delta_summary = _changed_value(base_value, sensitivity, operation)
        _set_path(variant, path, changed_value)
    except SensitivityAnalysisError as exc:
        data_gaps.append(
            {
                "code": "sensitivity_not_applied",
                "sensitivity_id": sensitivity_id,
                "path": ".".join(path),
                "message": str(exc),
            }
        )
        base_value = None
        changed_value = None
        delta_summary = {"delta_kind": "unavailable", "magnitude": None}

    return {
        "id": sensitivity_id,
        "label": sensitivity.get("label", sensitivity_id),
        "domain": sensitivity.get("domain", "unspecified"),
        "path": ".".join(path),
        "operation": operation,
        "status": "complete" if len(data_gaps) == gap_count_before else "partial",
        "base_value": _json_value(base_value),
        "changed_value": _json_value(changed_value),
        "delta": delta_summary,
        "variant_assumptions": variant.get("assumptions", {}),
    }


def _build_stress_case(
    decision_scenario: dict[str, Any],
    stress: dict[str, Any],
    sensitivity_cases: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    stress_id = _required_text(stress, "id", "stress scenario")
    requested_ids = stress.get("sensitivity_ids")
    if not isinstance(requested_ids, list) or not requested_ids:
        raise SensitivityAnalysisError(f"stress scenario {stress_id} requires sensitivity_ids")

    cases_by_id = {case["id"]: case for case in sensitivity_cases}
    variant_assumptions = copy.deepcopy(decision_scenario.get("assumptions", {}))
    applied: list[str] = []
    missing: list[str] = []
    for sensitivity_id in sorted(str(item) for item in requested_ids):
        case = cases_by_id.get(sensitivity_id)
        if case is None or case["status"] != "complete":
            missing.append(sensitivity_id)
            continue
        applied.append(sensitivity_id)
        _set_path({"assumptions": variant_assumptions}, tuple(case["path"].split(".")), case["changed_value"])

    if missing:
        data_gaps.append(
            {
                "code": "stress_sensitivity_missing",
                "stress_id": stress_id,
                "sensitivity_ids": missing,
                "message": "Stress scenario references missing or incomplete sensitivities.",
            }
        )
    return {
        "id": stress_id,
        "label": stress.get("label", stress_id),
        "status": "complete" if not missing else "partial",
        "sensitivity_ids": applied + missing,
        "applied_sensitivity_ids": applied,
        "missing_sensitivity_ids": missing,
        "variant_assumptions": variant_assumptions,
    }


def _changed_value(base_value: Any, sensitivity: dict[str, Any], operation: str) -> tuple[Any, dict[str, Any]]:
    if operation == "set":
        changed_value = sensitivity.get("value")
        return changed_value, {
            "delta_kind": "set",
            "magnitude": _magnitude(base_value, changed_value),
            "value": _json_value(changed_value),
        }
    if operation in {"absolute", "relative"}:
        delta = _decimal(sensitivity.get("delta"), "delta")
        base_decimal = _decimal(base_value, "base_value")
        changed_decimal = base_decimal + delta if operation == "absolute" else base_decimal * (Decimal("1") + delta)
        return _format_decimal_like(base_value, changed_decimal), {
            "delta_kind": operation,
            "delta": str(delta),
            "magnitude": str(abs(delta)),
        }
    raise SensitivityAnalysisError(f"Unsupported sensitivity operation: {operation}")


def _tornado_data(sensitivity_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    complete = [case for case in sensitivity_cases if case["status"] == "complete"]
    ranked = sorted(
        complete,
        key=lambda case: (-_decimal(case["delta"]["magnitude"] or "0", "magnitude"), case["id"]),
    )
    return [
        {
            "rank": index,
            "sensitivity_id": case["id"],
            "label": case["label"],
            "domain": case["domain"],
            "path": case["path"],
            "magnitude": case["delta"]["magnitude"],
            "operation": case["operation"],
        }
        for index, case in enumerate(ranked, start=1)
    ]


def _source_gaps(decision_scenario: dict[str, Any]) -> list[dict[str, Any]]:
    raw_gaps = decision_scenario.get("data_gaps", [])
    if not isinstance(raw_gaps, list):
        return []
    gaps: list[dict[str, Any]] = []
    for gap in raw_gaps:
        if isinstance(gap, dict):
            copied = dict(gap)
            copied["source"] = "decision_scenario"
            gaps.append(copied)
        else:
            gaps.append({"source": "decision_scenario", "code": "source_gap", "message": str(gap)})
    return gaps


def _sorted_items(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized = [item for item in items if isinstance(item, dict)]
    return sorted(normalized, key=lambda item: str(item.get("id", "")))


def _path(item: dict[str, Any]) -> tuple[str, ...]:
    raw_path = item.get("path")
    if not isinstance(raw_path, list) or not raw_path:
        raise SensitivityAnalysisError(f"{item.get('id', 'sensitivity')} path must be a non-empty list")
    path = tuple(str(part) for part in raw_path)
    if path[0] != "assumptions":
        raise SensitivityAnalysisError("sensitivity path must start with assumptions")
    return path


def _get_path(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            raise SensitivityAnalysisError(f"Missing path: {'.'.join(path)}")
        current = current[part]
    return current


def _set_path(data: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    current: Any = data
    for part in path[:-1]:
        if not isinstance(current, dict) or part not in current:
            raise SensitivityAnalysisError(f"Missing path: {'.'.join(path)}")
        current = current[part]
    if not isinstance(current, dict):
        raise SensitivityAnalysisError(f"Cannot set path: {'.'.join(path)}")
    current[path[-1]] = value


def _required_text(data: dict[str, Any], field: str, label: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SensitivityAnalysisError(f"{label} {field} is required")
    return value


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SensitivityAnalysisError(f"Invalid decimal for {field_name}: {value}") from exc


def _format_decimal_like(base_value: Any, value: Decimal) -> Any:
    if isinstance(base_value, int):
        return int(value)
    return str(value.normalize())


def _magnitude(base_value: Any, changed_value: Any) -> str | None:
    try:
        return str(abs(_decimal(changed_value, "changed_value") - _decimal(base_value, "base_value")))
    except SensitivityAnalysisError:
        return None


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return value


def _nested_or_none(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
