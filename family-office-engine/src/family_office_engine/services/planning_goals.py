import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "planning-goals/v1"
INPUT_RECORD_TYPE = "PlanningGoals"
SNAPSHOT_RECORD_TYPE = "PlanningGoalsSnapshot"
TIMELINE_SCHEMA_VERSION = "timeline-events/v1"

OBJECTIVE_CATEGORIES = {
    "retirement_income",
    "capital_preservation",
    "liquidity",
    "family_protection",
    "tax_efficiency",
    "estate",
    "education",
    "real_estate",
    "other",
}
CONSTRAINT_TYPES = {
    "legal",
    "liquidity",
    "risk",
    "tax",
    "family",
    "timing",
    "asset",
    "other",
}
SEVERITIES = {"hard", "soft"}
OPERATORS = {"min", "max", "target", "range"}
RISK_LEVELS = {"low", "medium", "high", "unknown"}
LIQUIDITY_BUCKETS = {"emergency_reserve", "short_term", "medium_term", "long_term", "unknown"}


class PlanningGoalsError(ValueError):
    pass


def import_planning_goals(
    input_path: Path,
    output_path: Path,
    timeline_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    data = load_planning_goals(input_path)
    timeline_snapshot = _load_optional_timeline_snapshot(timeline_snapshot_path)
    gaps = validate_planning_goals(data, timeline_snapshot)
    goals_core = {
        "source": {
            "type": "planning-goals-json",
            "path": str(input_path),
        },
        "household": {
            "household_id": data["household_id"],
            "as_of_date": data["as_of_date"],
            "timeline_snapshot_path": str(timeline_snapshot_path) if timeline_snapshot_path else None,
        },
        "planning_horizon": data["planning_horizon"],
        "risk_profile": data.get("risk_profile"),
        "liquidity_policy": data.get("liquidity_policy"),
        "objectives": data["objectives"],
        "constraints": data["constraints"],
        "data_gaps": gaps,
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "complete" if not gaps else "partial",
        **goals_core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(_semantic_goals_core(goals_core)),
        },
        "notes": (
            "Planning goals are declared objectives and constraints. The service validates structure and "
            "references, but does not optimize, score, calculate taxes, returns or recommendations."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise PlanningGoalsError(f"Cannot write planning goals snapshot: {output_path}") from exc
    return snapshot


def validate_planning_goals(
    data: dict[str, Any],
    timeline_snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    errors: list[str] = []
    gaps: list[dict[str, Any]] = []

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported planning goals schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported planning goals record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_date(data, "as_of_date", errors)

    _validate_planning_horizon(data.get("planning_horizon"), errors)
    _validate_risk_profile(data.get("risk_profile"), errors, gaps)
    _validate_liquidity_policy(data.get("liquidity_policy"), errors, gaps)
    objective_ids = _validate_objectives(_required_list(data, "objectives", errors), errors, gaps)
    timeline_event_ids = _timeline_event_ids(timeline_snapshot, errors)
    _validate_constraints(
        _required_list(data, "constraints", errors),
        objective_ids,
        timeline_event_ids,
        errors,
        gaps,
    )
    _validate_declared_gaps(data.get("data_gaps", []), errors, gaps)

    if errors:
        raise PlanningGoalsError("; ".join(errors))
    return gaps


def load_planning_goals(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PlanningGoalsError(f"Planning goals file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PlanningGoalsError(f"Invalid JSON in planning goals file: {exc}") from exc
    if not isinstance(data, dict):
        raise PlanningGoalsError("Planning goals file must contain a JSON object")
    return data


def _load_optional_timeline_snapshot(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PlanningGoalsError(f"Invalid JSON in timeline snapshot: {exc}") from exc
    if not isinstance(data, dict):
        raise PlanningGoalsError("Timeline snapshot must contain a JSON object")
    return data


def _validate_planning_horizon(raw: Any, errors: list[str]) -> None:
    if not isinstance(raw, dict):
        errors.append("planning_horizon must be an object")
        return
    start_year = raw.get("start_year")
    end_year = raw.get("end_year")
    if not isinstance(start_year, int) or start_year < 1900 or start_year > 2200:
        errors.append("planning_horizon.start_year must be a year between 1900 and 2200")
    if not isinstance(end_year, int) or end_year < 1900 or end_year > 2200:
        errors.append("planning_horizon.end_year must be a year between 1900 and 2200")
    if isinstance(start_year, int) and isinstance(end_year, int) and end_year < start_year:
        errors.append("planning_horizon.end_year must be greater than or equal to start_year")


def _validate_risk_profile(raw: Any, errors: list[str], gaps: list[dict[str, Any]]) -> None:
    if raw in (None, ""):
        gaps.append(_gap("missing_risk_profile", "Risk profile is not declared."))
        return
    if not isinstance(raw, dict):
        errors.append("risk_profile must be an object")
        return
    for field in ("capacity", "tolerance"):
        value = raw.get(field)
        if value not in RISK_LEVELS:
            errors.append(f"risk_profile.{field} must be one of: {', '.join(sorted(RISK_LEVELS))}")
        if value == "unknown":
            gaps.append(_gap(f"unknown_risk_{field}", f"Risk {field} is unknown."))
    max_loss = raw.get("max_loss_ratio")
    if max_loss not in (None, ""):
        ratio = _number(max_loss, "risk_profile.max_loss_ratio", errors)
        if ratio is not None and (ratio < 0 or ratio > 1):
            errors.append("risk_profile.max_loss_ratio must be between 0 and 1")


def _validate_liquidity_policy(raw: Any, errors: list[str], gaps: list[dict[str, Any]]) -> None:
    if raw in (None, ""):
        gaps.append(_gap("missing_liquidity_policy", "Liquidity policy is not declared."))
        return
    if not isinstance(raw, dict):
        errors.append("liquidity_policy must be an object")
        return
    reserve_months = raw.get("minimum_reserve_months")
    if not isinstance(reserve_months, int) or reserve_months < 0:
        errors.append("liquidity_policy.minimum_reserve_months must be a non-negative integer")
    bucket = raw.get("preferred_bucket")
    if bucket not in LIQUIDITY_BUCKETS:
        errors.append(f"liquidity_policy.preferred_bucket must be one of: {', '.join(sorted(LIQUIDITY_BUCKETS))}")
    if bucket == "unknown":
        gaps.append(_gap("unknown_liquidity_bucket", "Preferred liquidity bucket is unknown."))


def _validate_objectives(
    objectives: list[Any],
    errors: list[str],
    gaps: list[dict[str, Any]],
) -> set[str]:
    objective_ids: set[str] = set()
    priorities: set[int] = set()
    for index, objective in enumerate(objectives):
        label = f"objectives[{index}]"
        if not isinstance(objective, dict):
            errors.append(f"{label} must be an object")
            continue
        objective_id = _required_string(objective, "objective_id", errors, label)
        if objective_id:
            if objective_id in objective_ids:
                errors.append(f"Duplicate objective_id: {objective_id}")
            objective_ids.add(objective_id)
        _required_string(objective, "label", errors, label)
        if objective.get("category") not in OBJECTIVE_CATEGORIES:
            errors.append(f"{label}.category is invalid")
        priority = objective.get("priority")
        if not isinstance(priority, int) or priority < 1:
            errors.append(f"{label}.priority must be a positive integer")
        elif priority in priorities:
            errors.append(f"Duplicate objective priority: {priority}")
        else:
            priorities.add(priority)
        target = objective.get("target")
        if target in (None, ""):
            gaps.append(_gap("missing_objective_target", "Objective target is not declared.", objective_id=objective_id))
        else:
            _validate_target(target, f"{label}.target", errors)
        if objective.get("time_horizon_year") not in (None, ""):
            year = objective.get("time_horizon_year")
            if not isinstance(year, int) or year < 1900 or year > 2200:
                errors.append(f"{label}.time_horizon_year must be a year between 1900 and 2200")
    return objective_ids


def _validate_constraints(
    constraints: list[Any],
    objective_ids: set[str],
    timeline_event_ids: set[str] | None,
    errors: list[str],
    gaps: list[dict[str, Any]],
) -> None:
    constraint_ids: set[str] = set()
    if not constraints:
        gaps.append(_gap("missing_constraints", "No planning constraints declared."))
    for index, constraint in enumerate(constraints):
        label = f"constraints[{index}]"
        if not isinstance(constraint, dict):
            errors.append(f"{label} must be an object")
            continue
        constraint_id = _required_string(constraint, "constraint_id", errors, label)
        if constraint_id:
            if constraint_id in constraint_ids:
                errors.append(f"Duplicate constraint_id: {constraint_id}")
            constraint_ids.add(constraint_id)
        _required_string(constraint, "label", errors, label)
        if constraint.get("constraint_type") not in CONSTRAINT_TYPES:
            errors.append(f"{label}.constraint_type is invalid")
        if constraint.get("severity") not in SEVERITIES:
            errors.append(f"{label}.severity must be hard or soft")
        priority = constraint.get("priority")
        if not isinstance(priority, int) or priority < 1:
            errors.append(f"{label}.priority must be a positive integer")
        _validate_objective_refs(constraint.get("applies_to_objective_ids", []), objective_ids, errors, label)
        _validate_timeline_refs(constraint.get("timeline_event_ids", []), timeline_event_ids, errors, gaps, label)
        threshold = constraint.get("threshold")
        if threshold in (None, ""):
            gaps.append(_gap("missing_constraint_threshold", "Constraint threshold is not declared.", constraint_id=constraint_id))
        else:
            _validate_target(threshold, f"{label}.threshold", errors)


def _validate_target(raw: Any, label: str, errors: list[str]) -> None:
    if not isinstance(raw, dict):
        errors.append(f"{label} must be an object")
        return
    operator = raw.get("operator")
    if operator not in OPERATORS:
        errors.append(f"{label}.operator is invalid")
    _required_string(raw, "metric", errors, label)
    _required_string(raw, "unit", errors, label)
    if operator == "range":
        min_value = _number(raw.get("min_value"), f"{label}.min_value", errors)
        max_value = _number(raw.get("max_value"), f"{label}.max_value", errors)
        if min_value is not None and max_value is not None and max_value < min_value:
            errors.append(f"{label}.max_value must be greater than or equal to min_value")
    else:
        _number(raw.get("value"), f"{label}.value", errors)


def _validate_objective_refs(raw: Any, objective_ids: set[str], errors: list[str], label: str) -> None:
    if raw in (None, ""):
        return
    if not isinstance(raw, list):
        errors.append(f"{label}.applies_to_objective_ids must be a list")
        return
    for objective_id in raw:
        if objective_id not in objective_ids:
            errors.append(f"{label}.applies_to_objective_ids references unknown objective: {objective_id}")


def _validate_timeline_refs(
    raw: Any,
    timeline_event_ids: set[str] | None,
    errors: list[str],
    gaps: list[dict[str, Any]],
    label: str,
) -> None:
    if raw in (None, ""):
        return
    if not isinstance(raw, list):
        errors.append(f"{label}.timeline_event_ids must be a list")
        return
    if timeline_event_ids is None:
        if raw:
            gaps.append(_gap("timeline_snapshot_not_available", "Timeline refs cannot be verified without a timeline snapshot."))
        return
    for event_id in raw:
        if event_id not in timeline_event_ids:
            gaps.append(_gap("timeline_event_reference_missing", "Constraint references a missing timeline event.", event_id=event_id))


def _timeline_event_ids(timeline_snapshot: dict[str, Any] | None, errors: list[str]) -> set[str] | None:
    if timeline_snapshot is None:
        return None
    if timeline_snapshot.get("schema_version") != TIMELINE_SCHEMA_VERSION:
        errors.append(f"Unsupported timeline snapshot schema: {timeline_snapshot.get('schema_version')}")
    events = timeline_snapshot.get("events")
    if not isinstance(events, list):
        errors.append("Timeline snapshot events must be a list")
        return set()
    event_ids: set[str] = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"timeline.events[{index}] must be an object")
            continue
        event_id = event.get("event_id")
        if isinstance(event_id, str) and event_id:
            event_ids.add(event_id)
    return event_ids


def _validate_declared_gaps(raw_gaps: Any, errors: list[str], gaps: list[dict[str, Any]]) -> None:
    if raw_gaps in (None, ""):
        return
    if not isinstance(raw_gaps, list):
        errors.append("data_gaps must be a list")
        return
    for index, gap in enumerate(raw_gaps):
        if not isinstance(gap, dict):
            errors.append(f"data_gaps[{index}] must be an object")
            continue
        if not gap.get("code"):
            errors.append(f"data_gaps[{index}].code is required")
            continue
        gaps.append(gap)


def _required_list(data: dict[str, Any], field: str, errors: list[str]) -> list[Any]:
    value = data.get(field)
    if not isinstance(value, list):
        errors.append(f"{field} must be a list")
        return []
    return value


def _required_string(
    data: dict[str, Any],
    field: str,
    errors: list[str],
    prefix: str | None = None,
) -> str | None:
    label = field if prefix is None else f"{prefix}.{field}"
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} is required")
        return None
    return value


def _required_date(
    data: dict[str, Any],
    field: str,
    errors: list[str],
    prefix: str | None = None,
) -> date | None:
    label = field if prefix is None else f"{prefix}.{field}"
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} is required")
        return None
    return _parse_date(value, label, errors)


def _parse_date(value: Any, label: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{label} must be an ISO date string")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label} must be a valid ISO date")
        return None


def _number(value: Any, label: str, errors: list[str]) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        errors.append(f"{label} must be a number")
        return None
    try:
        return float(value)
    except ValueError:
        errors.append(f"{label} must be a number")
        return None


def _gap(code: str, message: str, **extra: Any) -> dict[str, Any]:
    gap = {"code": code, "message": message}
    gap.update(extra)
    return gap


def _semantic_goals_core(goals_core: dict[str, Any]) -> dict[str, Any]:
    semantic = json.loads(json.dumps(goals_core))
    source = semantic.get("source")
    if isinstance(source, dict):
        source.pop("path", None)
    household = semantic.get("household")
    if isinstance(household, dict):
        household.pop("timeline_snapshot_path", None)
    return semantic


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
