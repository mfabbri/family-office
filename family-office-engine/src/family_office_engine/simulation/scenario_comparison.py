import copy
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from family_office_engine.simulation.monte_carlo import (
    DEFAULT_END_AGE,
    DEFAULT_SEED,
    DEFAULT_SIMULATIONS,
    MonteCarloSimulationError,
    simulate_monte_carlo_result,
)

SCHEMA_VERSION = "scenario-comparison/v1"
DEFAULT_TARGET_AGES = (62, 64, 67)


class ScenarioComparisonError(ValueError):
    pass


def compare_retirement_scenarios(
    net_worth_snapshot_path: Path,
    assumptions_snapshot_path: Path,
    output_path: Path,
    target_ages: list[int] | tuple[int, ...] = DEFAULT_TARGET_AGES,
    simulations: int = DEFAULT_SIMULATIONS,
    seed: int = DEFAULT_SEED,
    end_age: int = DEFAULT_END_AGE,
) -> dict[str, Any]:
    data_gaps: list[str] = []
    sources: dict[str, str] = {}

    net_worth = _read_optional_json(net_worth_snapshot_path, data_gaps, "net worth")
    assumptions = _read_optional_json(assumptions_snapshot_path, data_gaps, "manual assumptions")
    if net_worth is not None:
        sources["net_worth"] = str(net_worth_snapshot_path)
    if assumptions is not None:
        sources["manual_assumptions"] = str(assumptions_snapshot_path)

    scenarios: list[dict[str, Any]] = []
    if net_worth is not None and assumptions is not None:
        for target_age in _normalized_target_ages(target_ages):
            scenario_gaps: list[str] = []
            scenario_assumptions = _with_target_age(assumptions, target_age)
            result = simulate_monte_carlo_result(
                net_worth,
                scenario_assumptions,
                scenario_gaps,
                simulations,
                seed,
                end_age,
            )
            scenarios.append(
                {
                    "id": f"retire_at_{target_age}",
                    "label": f"Retire at {target_age}",
                    "target_retirement_age": target_age,
                    "status": "complete" if result is not None else "blocked_missing_inputs",
                    "result": result,
                    "data_gaps": scenario_gaps,
                }
            )

    ranking = _rank_scenarios(scenarios)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "ScenarioComparisonSnapshot",
        "status": "complete" if scenarios and all(s["status"] == "complete" for s in scenarios) else "blocked_missing_inputs",
        "scenario_type": "retirement_target_age",
        "sources": sources,
        "simulations": simulations,
        "seed": seed,
        "end_age": end_age,
        "scenarios": scenarios,
        "ranking": ranking,
        "data_gaps": data_gaps,
        "notes": (
            "Deterministic comparison of planning scenarios. "
            "Ranking is descriptive, not financial, tax or pension advice."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise ScenarioComparisonError(f"Cannot write scenario comparison: {output_path}") from exc
    return snapshot


def _read_optional_json(path: Path, data_gaps: list[str], label: str) -> dict[str, Any] | None:
    if not path.exists():
        data_gaps.append(f"Missing {label} snapshot: {path}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScenarioComparisonError(f"Cannot read {label} snapshot: {path}") from exc
    if not isinstance(data, dict):
        raise ScenarioComparisonError(f"{label} snapshot must be a JSON object: {path}")
    return data


def _normalized_target_ages(target_ages: list[int] | tuple[int, ...]) -> list[int]:
    if not target_ages:
        raise ScenarioComparisonError("At least one target age is required")
    normalized: list[int] = []
    for age in target_ages:
        if age < 0 or age > 120:
            raise ScenarioComparisonError(f"Invalid target age: {age}")
        if age not in normalized:
            normalized.append(age)
    return normalized


def _with_target_age(assumptions_snapshot: dict[str, Any], target_age: int) -> dict[str, Any]:
    scenario = copy.deepcopy(assumptions_snapshot)
    assumptions = scenario.setdefault("assumptions", {})
    if not isinstance(assumptions, dict):
        raise MonteCarloSimulationError("Missing required field: assumptions")
    personal = assumptions.setdefault("personal", {})
    if not isinstance(personal, dict):
        raise MonteCarloSimulationError("Missing required field: assumptions.personal")
    personal["target_retirement_age"] = target_age
    return scenario


def _rank_scenarios(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    complete = [scenario for scenario in scenarios if scenario["status"] == "complete" and scenario["result"]]
    ranked = sorted(
        complete,
        key=lambda scenario: (
            _decimal(scenario["result"]["success_rate"], "success_rate"),
            _decimal(scenario["result"]["final_balance_p50"], "final_balance_p50"),
        ),
        reverse=True,
    )
    return [
        {
            "rank": index,
            "scenario_id": scenario["id"],
            "target_retirement_age": scenario["target_retirement_age"],
            "success_rate": scenario["result"]["success_rate"],
            "final_balance_p50": scenario["result"]["final_balance_p50"],
        }
        for index, scenario in enumerate(ranked, start=1)
    ]


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ScenarioComparisonError(f"Invalid decimal for {field_name}: {value}") from exc
