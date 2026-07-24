import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "pension-scenario/v1"
RECORD_TYPE = "PensionScenarioSet"
SNAPSHOT_RECORD_TYPE = "PensionScenarioSnapshot"
SYNTHETIC_SOURCE_TYPES = {"synthetic", "synthetic_fixture", "demo_fixture"}


class PensionScenarioError(ValueError):
    pass


def build_pension_scenario(input_path: Path, output_path: Path) -> dict[str, Any]:
    data = _read_json(input_path, "pension scenario input")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise PensionScenarioError(f"Unsupported pension scenario schema: {data.get('schema_version')}")
    if data.get("record_type") not in (None, RECORD_TYPE):
        raise PensionScenarioError(f"Unsupported pension scenario record type: {data.get('record_type')}")

    household_id = data.get("household_id")
    if not isinstance(household_id, str) or not household_id.strip():
        raise PensionScenarioError("Pension scenario requires household_id.")
    _reject_personal_synthetic_sources(data, household_id)

    scenarios = _normalize_scenarios(data.get("scenarios"))
    selected = _selected_scenario(data.get("selected_scenario_id"), scenarios)
    input_gaps = data.get("data_gaps", []) if isinstance(data.get("data_gaps"), list) else []
    scenario_gaps = [gap for scenario in scenarios for gap in scenario["data_gaps"]]
    status = "partial" if input_gaps or scenario_gaps or selected["data_gaps"] else "complete"

    core = {
        "input": {
            "household_id": household_id,
            "as_of_date": data.get("as_of_date"),
            "confirmed_at": data.get("confirmed_at"),
        },
        "selected_scenario_id": selected["scenario_id"],
        "selected_scenario": selected,
        "scenarios": scenarios,
        "sources": data.get("sources", []),
        "data_gaps": input_gaps + scenario_gaps,
        "summary": {
            "scenario_count": len(scenarios),
            "data_gap_count": len(input_gaps) + len(scenario_gaps),
            "selected_fiscal_residence": _effective_fiscal_residence(selected),
            "selected_retirement_country": selected["retirement"]["country"],
            "review_required": True,
        },
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": status,
        **core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(_semantic_core(core)),
        },
        "notes": (
            "This snapshot records explicit retirement assumptions only. It does not calculate pension entitlement, "
            "tax, withholding, contribution bases, recommendations or filings."
        ),
    }
    _assert_output_scope(output_path, household_id, data)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise PensionScenarioError(f"Cannot write pension scenario snapshot: {output_path}") from exc
    return snapshot


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PensionScenarioError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PensionScenarioError(f"Invalid JSON in {label} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PensionScenarioError(f"{label} must contain a JSON object.")
    return data


def _normalize_scenarios(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise PensionScenarioError("At least one pension scenario is required.")
    seen: set[str] = set()
    scenarios = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise PensionScenarioError(f"Pension scenario at index {index} must be an object.")
        scenario_id = _required_text(item, "scenario_id", index)
        if scenario_id in seen:
            raise PensionScenarioError(f"Duplicate pension scenario id: {scenario_id}")
        seen.add(scenario_id)
        retirement = item.get("retirement")
        if not isinstance(retirement, dict):
            raise PensionScenarioError(f"Pension scenario {scenario_id} requires retirement.")
        normalized = {
            "scenario_id": scenario_id,
            "label": item.get("label", scenario_id),
            "assumption_status": item.get("assumption_status", "explicit"),
            "retirement": {
                "date": retirement.get("date"),
                "country": retirement.get("country"),
                "source": retirement.get("source"),
            },
            "initial_fiscal_residence": item.get("initial_fiscal_residence"),
            "future_contributions": _normalize_future_contributions(item.get("future_contributions"), scenario_id),
            "post_retirement_residence_changes": _normalize_residence_changes(
                item.get("post_retirement_residence_changes"),
                scenario_id,
            ),
            "provenance": item.get("provenance", []),
            "data_gaps": [],
        }
        normalized["data_gaps"] = _scenario_gaps(normalized)
        scenarios.append(normalized)
    return scenarios


def _required_text(item: dict[str, Any], field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PensionScenarioError(f"Pension scenario at index {index} missing {field}.")
    return value


def _normalize_future_contributions(value: Any, scenario_id: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        return []
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise PensionScenarioError(f"Future contribution at index {index} in {scenario_id} must be an object.")
        result.append(
            {
                "country": item.get("country"),
                "from_date": item.get("from_date"),
                "to_date": item.get("to_date"),
                "status": item.get("status"),
                "basis": item.get("basis"),
                "amount": item.get("amount"),
                "source": item.get("source"),
            }
        )
    return result


def _normalize_residence_changes(value: Any, scenario_id: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise PensionScenarioError(f"Residence changes in {scenario_id} must be a list.")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise PensionScenarioError(f"Residence change at index {index} in {scenario_id} must be an object.")
        result.append(
            {
                "effective_date": item.get("effective_date"),
                "fiscal_residence": item.get("fiscal_residence"),
                "source": item.get("source"),
            }
        )
    return result


def _scenario_gaps(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = []
    scenario_id = scenario["scenario_id"]
    retirement = scenario["retirement"]
    if not retirement.get("date"):
        gaps.append({"code": "missing_retirement_date", "message": "Retirement date must be explicit.", "scenario_id": scenario_id})
    if retirement.get("country") not in {"IT", "ES"}:
        gaps.append({"code": "missing_retirement_country", "message": "Retirement country must be IT or ES.", "scenario_id": scenario_id})
    if scenario.get("initial_fiscal_residence") not in {"IT", "ES"}:
        gaps.append({"code": "missing_initial_fiscal_residence", "message": "Initial fiscal residence must be IT or ES.", "scenario_id": scenario_id})
    if not isinstance(scenario.get("provenance"), list) or not scenario["provenance"]:
        gaps.append({"code": "missing_scenario_provenance", "message": "Scenario provenance is required.", "scenario_id": scenario_id})
    if scenario.get("assumption_status") != "explicit":
        gaps.append({"code": "future_assumptions_not_explicit", "message": "Future assumptions cannot be inferred.", "scenario_id": scenario_id})

    contributions = scenario["future_contributions"]
    if not contributions:
        gaps.append(
            {
                "code": "missing_future_contribution_assumptions",
                "message": "Future contribution assumptions must be explicit for each scenario.",
                "scenario_id": scenario_id,
            }
        )
    else:
        countries = [item.get("country") for item in contributions if isinstance(item, dict)]
        if "IT" not in countries:
            gaps.append({"code": "missing_future_it_contributions", "message": "Future Italian contribution assumption is required.", "scenario_id": scenario_id})
        if "ES" not in countries:
            gaps.append({"code": "missing_future_es_contributions", "message": "Future Spanish contribution assumption is required.", "scenario_id": scenario_id})
        for index, item in enumerate(contributions):
            if item.get("country") not in {"IT", "ES"}:
                gaps.append({"code": "unsupported_future_contribution_country", "message": "Future contribution country must be IT or ES.", "scenario_id": scenario_id, "index": index})
            if item.get("status") not in {"none", "continues", "planned", "unknown"}:
                gaps.append({"code": "missing_future_contribution_status", "message": "Future contribution status must be explicit.", "scenario_id": scenario_id, "index": index})
            if item.get("country") == "ES" and item.get("status") != "none" and item.get("basis") == "italian_periods":
                gaps.append({"code": "spanish_future_contribution_uses_italian_periods", "message": "Italian periods cannot be used as Spanish contribution bases.", "scenario_id": scenario_id, "index": index})

    for index, change in enumerate(scenario["post_retirement_residence_changes"]):
        if not change.get("effective_date"):
            gaps.append({"code": "missing_residence_change_effective_date", "message": "Residence change date must be explicit.", "scenario_id": scenario_id, "index": index})
        if change.get("fiscal_residence") not in {"IT", "ES"}:
            gaps.append({"code": "missing_residence_change_country", "message": "Residence change country must be IT or ES.", "scenario_id": scenario_id, "index": index})
    return gaps


def _selected_scenario(selected_id: Any, scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(selected_id, str) or not selected_id:
        raise PensionScenarioError("selected_scenario_id is required.")
    for scenario in scenarios:
        if scenario["scenario_id"] == selected_id:
            return scenario
    raise PensionScenarioError(f"selected_scenario_id not found: {selected_id}")


def _effective_fiscal_residence(scenario: dict[str, Any]) -> str | None:
    changes = [item for item in scenario["post_retirement_residence_changes"] if item.get("effective_date")]
    if changes:
        return sorted(changes, key=lambda item: item["effective_date"])[-1].get("fiscal_residence")
    return scenario.get("initial_fiscal_residence")


def _reject_personal_synthetic_sources(data: dict[str, Any], household_id: str) -> None:
    if household_id.lower().startswith("synthetic"):
        return
    for source in data.get("sources", []):
        if isinstance(source, dict) and source.get("type") in SYNTHETIC_SOURCE_TYPES:
            raise PensionScenarioError("Synthetic or demo sources cannot be used for personal pension scenarios.")
    for scenario in data.get("scenarios", []):
        if not isinstance(scenario, dict):
            continue
        for source in scenario.get("provenance", []):
            if isinstance(source, dict) and source.get("type") in SYNTHETIC_SOURCE_TYPES:
                raise PensionScenarioError("Synthetic or demo sources cannot be used for personal pension scenarios.")


def _assert_output_scope(output_path: Path, household_id: str, data: dict[str, Any]) -> None:
    workspace_root = Path(__file__).resolve().parents[4] / "family-office-workspace"
    if household_id.lower().startswith("synthetic") or _has_only_synthetic_sources(data):
        return
    try:
        output_path.resolve().relative_to(workspace_root.resolve())
    except ValueError as exc:
        raise PensionScenarioError("Personal pension scenario output must stay inside family-office-workspace.") from exc


def _has_only_synthetic_sources(data: dict[str, Any]) -> bool:
    sources = [source for source in data.get("sources", []) if isinstance(source, dict)]
    return bool(sources) and all(source.get("type") in SYNTHETIC_SOURCE_TYPES for source in sources)


def _content_hash(data: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _semantic_core(core: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(core))
