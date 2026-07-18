import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "decision-scenario/v2"
INPUT_RECORD_TYPE = "DecisionScenarioInput"
SNAPSHOT_RECORD_TYPE = "DecisionScenarioSnapshot"

REQUIRED_SOURCES = {
    "household": ("household-facts/v1", "Household facts"),
    "ownership": ("ownership-beneficiary-graph/v1", "Ownership graph"),
    "asset_availability": ("asset-availability/v1", "Asset availability"),
    "timeline": ("timeline-events/v1", "Timeline events"),
}
OPTIONAL_SOURCES = {
    "pension_income": ("pension-income/v1", "Pension income"),
    "lifecycle_expenses": ("lifecycle-expenses/v1", "Lifecycle expenses"),
}


class DecisionScenarioError(ValueError):
    pass


def compose_decision_scenario(
    scenario_input_path: Path,
    output_path: Path,
    *,
    household_snapshot_path: Path,
    ownership_snapshot_path: Path,
    asset_availability_snapshot_path: Path,
    timeline_snapshot_path: Path,
    pension_income_snapshot_path: Path | None = None,
    lifecycle_expenses_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    scenario_input = _read_scenario_input(scenario_input_path)
    data_gaps: list[dict[str, Any]] = []
    sources: dict[str, dict[str, Any]] = {}
    source_summaries: dict[str, Any] = {}

    source_paths = {
        "household": household_snapshot_path,
        "ownership": ownership_snapshot_path,
        "asset_availability": asset_availability_snapshot_path,
        "timeline": timeline_snapshot_path,
        "pension_income": pension_income_snapshot_path,
        "lifecycle_expenses": lifecycle_expenses_snapshot_path,
    }
    for source_key, (expected_schema, label) in REQUIRED_SOURCES.items():
        snapshot = _read_required_snapshot(source_paths[source_key], source_key, expected_schema, label)
        sources[source_key] = _source_descriptor(source_paths[source_key], snapshot)
        source_summaries[source_key] = _source_summary(source_key, snapshot)
        data_gaps.extend(_source_gaps(source_key, snapshot))

    for source_key, (expected_schema, label) in OPTIONAL_SOURCES.items():
        snapshot = _read_optional_snapshot(source_paths[source_key], source_key, expected_schema, label, data_gaps)
        if snapshot is None:
            continue
        sources[source_key] = _source_descriptor(source_paths[source_key], snapshot)
        source_summaries[source_key] = _source_summary(source_key, snapshot)
        data_gaps.extend(_source_gaps(source_key, snapshot))

    assumptions, assumption_gaps = _validate_assumptions(scenario_input)
    data_gaps.extend(assumption_gaps)

    scenario_core = {
        "scenario_id": scenario_input["scenario_id"],
        "label": scenario_input["label"],
        "as_of_date": scenario_input["as_of_date"],
        "scenario_type": scenario_input.get("scenario_type", "planning"),
        "sources": sources,
        "source_summaries": source_summaries,
        "assumptions": assumptions,
        "objectives": _required_list(scenario_input, "objectives"),
        "constraints": _optional_list(scenario_input, "constraints"),
        "review": scenario_input.get("review", {}),
        "data_gaps": data_gaps,
    }
    content_hash = _content_hash(scenario_core)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "complete" if not data_gaps else "partial",
        **scenario_core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": content_hash,
        },
        "notes": (
            "Decision scenario V2 is a deterministic composition artifact. It does not run simulations, "
            "calculate taxes, returns, pension entitlements, scores or recommendations."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise DecisionScenarioError(f"Cannot write decision scenario snapshot: {output_path}") from exc
    return snapshot


def _read_scenario_input(path: Path) -> dict[str, Any]:
    data = _read_json(path, "decision scenario input")
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported decision scenario input schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported decision scenario input record type: {data.get('record_type')}")
    for field in ("scenario_id", "label", "as_of_date"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            errors.append(f"{field} is required")
    for field in ("objectives",):
        if not isinstance(data.get(field), list) or not data[field]:
            errors.append(f"{field} must be a non-empty list")
    if errors:
        raise DecisionScenarioError("; ".join(errors))
    return data


def _read_required_snapshot(path: Path, source_key: str, expected_schema: str, label: str) -> dict[str, Any]:
    snapshot = _read_json(path, label)
    _validate_snapshot_schema(snapshot, source_key, expected_schema, label)
    return snapshot


def _read_optional_snapshot(
    path: Path | None,
    source_key: str,
    expected_schema: str,
    label: str,
    data_gaps: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if path is None:
        data_gaps.append(_gap(f"missing_{source_key}_snapshot", f"{label} snapshot was not provided."))
        return None
    if not path.exists():
        data_gaps.append(
            _gap(f"missing_{source_key}_snapshot", f"{label} snapshot does not exist.", path=str(path))
        )
        return None
    snapshot = _read_json(path, label)
    _validate_snapshot_schema(snapshot, source_key, expected_schema, label)
    return snapshot


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DecisionScenarioError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DecisionScenarioError(f"Invalid JSON in {label}: {path}") from exc
    if not isinstance(data, dict):
        raise DecisionScenarioError(f"{label} must contain a JSON object: {path}")
    return data


def _validate_snapshot_schema(snapshot: dict[str, Any], source_key: str, expected_schema: str, label: str) -> None:
    if snapshot.get("schema_version") != expected_schema:
        raise DecisionScenarioError(
            f"Unsupported {label} schema for {source_key}: {snapshot.get('schema_version')}; expected {expected_schema}"
        )


def _validate_assumptions(scenario_input: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    assumptions = scenario_input.get("assumptions")
    if not isinstance(assumptions, dict):
        raise DecisionScenarioError("assumptions must be an object")
    gaps: list[dict[str, Any]] = []
    market = assumptions.get("market")
    withdrawal_policy = assumptions.get("withdrawal_policy")
    if not isinstance(market, dict):
        gaps.append(_gap("missing_market_assumptions", "Scenario market assumptions are missing."))
    if not isinstance(withdrawal_policy, dict):
        gaps.append(_gap("missing_withdrawal_policy", "Scenario withdrawal policy is missing."))
    return assumptions, gaps


def _source_descriptor(path: Path | None, snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": str(path) if path is not None else None,
        "schema_version": snapshot.get("schema_version"),
        "record_type": snapshot.get("record_type"),
        "status": snapshot.get("status"),
    }


def _source_summary(source_key: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    if source_key == "household":
        return {
            "person_count": len(snapshot.get("persons", [])) if isinstance(snapshot.get("persons"), list) else None,
            "relationship_count": (
                len(snapshot.get("relationships", [])) if isinstance(snapshot.get("relationships"), list) else None
            ),
        }
    if source_key == "ownership":
        return {
            "asset_count": len(snapshot.get("assets", [])) if isinstance(snapshot.get("assets"), list) else None,
            "debt_count": len(snapshot.get("debts", [])) if isinstance(snapshot.get("debts"), list) else None,
        }
    if source_key == "asset_availability":
        return {
            "classification_count": (
                len(snapshot.get("classifications", [])) if isinstance(snapshot.get("classifications"), list) else None
            )
        }
    if source_key == "timeline":
        return {
            "event_count": len(snapshot.get("events", [])) if isinstance(snapshot.get("events"), list) else None,
            "occurrence_count": (
                len(snapshot.get("occurrences", [])) if isinstance(snapshot.get("occurrences"), list) else None
            ),
        }
    if source_key == "pension_income":
        summary = snapshot.get("summary") if isinstance(snapshot.get("summary"), dict) else {}
        return {
            "stream_count": summary.get("stream_count"),
            "gross_annual_recurring_total": summary.get("gross_annual_recurring_total"),
            "gross_annual_recurring_total_currency": summary.get("gross_annual_recurring_total_currency"),
        }
    if source_key == "lifecycle_expenses":
        summary = snapshot.get("summary") if isinstance(snapshot.get("summary"), dict) else {}
        return {
            "entry_count": summary.get("entry_count"),
            "year_count": summary.get("year_count"),
            "first_year": summary.get("first_year"),
            "last_year": summary.get("last_year"),
        }
    return {}


def _source_gaps(source_key: str, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    raw_gaps = snapshot.get("data_gaps", [])
    if not isinstance(raw_gaps, list):
        return gaps
    for gap in raw_gaps:
        if isinstance(gap, dict):
            copied = dict(gap)
            copied["source"] = source_key
            gaps.append(copied)
        else:
            gaps.append({"source": source_key, "code": "source_gap", "message": str(gap)})
    return gaps


def _required_list(data: dict[str, Any], field: str) -> list[Any]:
    value = data.get(field)
    if not isinstance(value, list) or not value:
        raise DecisionScenarioError(f"{field} must be a non-empty list")
    return value


def _optional_list(data: dict[str, Any], field: str) -> list[Any]:
    value = data.get(field, [])
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise DecisionScenarioError(f"{field} must be a list")
    return value


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _gap(code: str, message: str, **extra: Any) -> dict[str, Any]:
    gap = {"code": code, "message": message}
    gap.update(extra)
    return gap
