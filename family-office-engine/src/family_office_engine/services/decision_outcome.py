import hashlib
import json
from pathlib import Path
from typing import Any

from family_office_engine.simulation.monte_carlo import (
    DEFAULT_END_AGE,
    DEFAULT_SEED,
    DEFAULT_SIMULATIONS,
    MonteCarloSimulationError,
    simulate_monte_carlo_result,
)

SCHEMA_VERSION = "decision-outcome/v1"
INPUT_RECORD_TYPE = "DecisionOutcomeInput"
SNAPSHOT_RECORD_TYPE = "DecisionOutcomeSnapshot"
DECISION_SCENARIO_SCHEMA_VERSION = "decision-scenario/v2"
SUPPORTED_EVALUATOR = "retirement-monte-carlo/v1"


class DecisionOutcomeError(ValueError):
    pass


def build_decision_outcome(
    decision_scenario_snapshot_path: Path,
    outcome_input_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    scenario = _read_json(decision_scenario_snapshot_path, "decision scenario snapshot")
    outcome_input = _read_outcome_input(outcome_input_path)
    snapshot = evaluate_decision_outcome(
        scenario,
        outcome_input,
        decision_scenario_path=decision_scenario_snapshot_path,
        outcome_input_path=outcome_input_path,
    )
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise DecisionOutcomeError(f"Cannot write decision outcome snapshot: {output_path}") from exc
    return snapshot


def evaluate_decision_outcome(
    scenario: dict[str, Any],
    outcome_input: dict[str, Any],
    *,
    decision_scenario_path: Path | None = None,
    outcome_input_path: Path | None = None,
) -> dict[str, Any]:
    if scenario.get("schema_version") != DECISION_SCENARIO_SCHEMA_VERSION:
        raise DecisionOutcomeError(
            "Unsupported decision scenario snapshot schema: "
            f"{scenario.get('schema_version')}; expected {DECISION_SCENARIO_SCHEMA_VERSION}"
        )
    if scenario.get("record_type") != "DecisionScenarioSnapshot":
        raise DecisionOutcomeError(
            f"Unsupported decision scenario snapshot record type: {scenario.get('record_type')}"
        )
    _validate_outcome_input(outcome_input)
    evaluator_id = outcome_input["evaluator_id"]
    if evaluator_id != SUPPORTED_EVALUATOR:
        raise DecisionOutcomeError(f"Unsupported deterministic evaluator: {evaluator_id}")

    parameters = _evaluator_parameters(outcome_input.get("parameters", {}))
    data_gaps = _source_gaps(scenario)
    metrics, evaluator_gaps = _evaluate_retirement_monte_carlo(scenario, parameters)
    data_gaps.extend(evaluator_gaps)

    if not metrics:
        status = "blocked_missing_inputs"
    elif data_gaps:
        status = "partial"
    else:
        status = "complete"

    scenario_hash = _scenario_hash(scenario)
    metric_provenance = {
        "scenario_id": scenario.get("scenario_id"),
        "scenario_schema_version": scenario.get("schema_version"),
        "scenario_content_hash": scenario_hash,
        "evaluator_id": evaluator_id,
        "evaluator_version": "v1",
        "seed": parameters["seed"],
    }
    metric_rows = [
        {
            **metric,
            "provenance": dict(metric_provenance),
        }
        for metric in metrics
    ]
    outcome_core = {
        "outcome_id": outcome_input["outcome_id"],
        "label": outcome_input["label"],
        "scenario": {
            "path": str(decision_scenario_path) if decision_scenario_path is not None else None,
            "scenario_id": scenario.get("scenario_id"),
            "schema_version": scenario.get("schema_version"),
            "record_type": scenario.get("record_type"),
            "status": scenario.get("status"),
            "content_hash": scenario_hash,
        },
        "evaluator": {
            "evaluator_id": evaluator_id,
            "version": "v1",
            "parameters": parameters,
        },
        "metrics": metric_rows,
        "data_gaps": data_gaps,
        "provenance": {
            "outcome_input": {
                "path": str(outcome_input_path) if outcome_input_path is not None else None,
                "schema_version": outcome_input.get("schema_version"),
                "record_type": outcome_input.get("record_type"),
            },
            "decision_scenario": metric_provenance,
        },
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": status,
        **outcome_core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(_semantic_outcome_core(outcome_core)),
        },
        "notes": (
            "Decision outcome V1 runs a registered deterministic evaluator over explicit scenario inputs. "
            "It does not calculate taxes, pension entitlements or recommendations."
        ),
    }
    return snapshot


def _evaluate_retirement_monte_carlo(
    scenario: dict[str, Any],
    parameters: dict[str, int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assumptions = scenario.get("assumptions")
    if not isinstance(assumptions, dict):
        return [], [_gap("missing_evaluator_assumptions", "Scenario assumptions must be an object.")]

    required_paths = {
        "starting_net_worth": ("portfolio", "starting_net_worth"),
        "current_age": ("personal", "current_age"),
        "target_retirement_age": ("personal", "target_retirement_age"),
        "family_expenses_yearly": ("cashflow", "family_expenses_yearly"),
        "net_salary_monthly": ("cashflow", "net_salary_monthly"),
        "salary_months": ("cashflow", "salary_months"),
        "nominal_return": ("market", "nominal_return"),
        "nominal_volatility": ("market", "nominal_volatility"),
    }
    values = {field: _nested_or_none(assumptions, path) for field, path in required_paths.items()}
    missing = [field for field, value in values.items() if value is None]
    if missing:
        return [], [
            _gap(
                "missing_evaluator_input",
                f"Missing Monte Carlo input: assumptions.{'.'.join(required_paths[field])}",
                evaluator_id=SUPPORTED_EVALUATOR,
                field=field,
            )
            for field in missing
        ]

    net_worth = {
        "record_type": "NetWorthSnapshot",
        "totals": {"net_worth": values["starting_net_worth"]},
    }
    manual_assumptions = {
        "record_type": "ManualAssumptions",
        "assumptions": {
            "personal": {
                "current_age": values["current_age"],
                "target_retirement_age": values["target_retirement_age"],
            },
            "cashflow": _cashflow_inputs(assumptions),
            "returns": {
                "nominal_return": values["nominal_return"],
                "nominal_volatility": values["nominal_volatility"],
            },
        },
    }
    evaluator_gaps: list[str] = []
    try:
        result = simulate_monte_carlo_result(
            net_worth,
            manual_assumptions,
            evaluator_gaps,
            simulations=parameters["simulations"],
            seed=parameters["seed"],
            end_age=parameters["end_age"],
        )
    except (MonteCarloSimulationError, TypeError, ValueError) as exc:
        raise DecisionOutcomeError(f"Deterministic evaluator failed: {exc}") from exc
    if result is None:
        return [], [
            _gap("missing_evaluator_input", message, evaluator_id=SUPPORTED_EVALUATOR)
            for message in evaluator_gaps
        ]

    units = {
        "target_retirement_age": "years",
        "family_expenses_yearly": "EUR/year",
        "self_salary_yearly": "EUR/year",
        "spouse_salary_yearly": "EUR/year",
        "rental_income_yearly": "EUR/year",
        "pre_retirement_income_yearly": "EUR/year",
        "pre_retirement_net_cashflow_yearly": "EUR/year",
        "retirement_income_yearly": "EUR/year",
        "post_retirement_income_yearly": "EUR/year",
        "net_retirement_drawdown_yearly": "EUR/year",
        "success_rate": "ratio",
        "final_balance_p05": "EUR",
        "final_balance_p50": "EUR",
        "final_balance_p95": "EUR",
    }
    return [
        {"metric_id": metric_id, "value": result[metric_id], "unit": units[metric_id]}
        for metric_id in sorted(result)
    ], []


def _cashflow_inputs(assumptions: dict[str, Any]) -> dict[str, Any]:
    cashflow = assumptions.get("cashflow")
    source = cashflow if isinstance(cashflow, dict) else {}
    fields = (
        "family_expenses_yearly",
        "net_salary_monthly",
        "salary_months",
        "spouse_net_salary_monthly",
        "spouse_salary_months",
        "rental_income_monthly_net",
        "retirement_income_yearly",
    )
    return {field: source[field] for field in fields if field in source}


def _read_outcome_input(path: Path) -> dict[str, Any]:
    data = _read_json(path, "decision outcome input")
    _validate_outcome_input(data)
    return data


def _validate_outcome_input(data: dict[str, Any]) -> None:
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported decision outcome input schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported decision outcome input record type: {data.get('record_type')}")
    for field in ("outcome_id", "label", "evaluator_id"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            errors.append(f"{field} is required")
    parameters = data.get("parameters", {})
    if not isinstance(parameters, dict):
        errors.append("parameters must be an object")
    if errors:
        raise DecisionOutcomeError("; ".join(errors))


def _evaluator_parameters(raw: dict[str, Any]) -> dict[str, int]:
    defaults = {
        "simulations": DEFAULT_SIMULATIONS,
        "seed": DEFAULT_SEED,
        "end_age": DEFAULT_END_AGE,
    }
    parameters: dict[str, int] = {}
    for field, default in defaults.items():
        value = raw.get(field, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise DecisionOutcomeError(f"Evaluator parameter {field} must be an integer")
        parameters[field] = value
    if parameters["simulations"] <= 0:
        raise DecisionOutcomeError("Evaluator parameter simulations must be greater than zero")
    if parameters["end_age"] <= 0:
        raise DecisionOutcomeError("Evaluator parameter end_age must be greater than zero")
    unsupported = sorted(set(raw) - set(defaults))
    if unsupported:
        raise DecisionOutcomeError(f"Unsupported evaluator parameters: {', '.join(unsupported)}")
    return parameters


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DecisionOutcomeError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DecisionOutcomeError(f"Invalid JSON in {label}: {path}") from exc
    if not isinstance(data, dict):
        raise DecisionOutcomeError(f"{label} must contain a JSON object: {path}")
    return data


def _nested_or_none(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _source_gaps(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    raw_gaps = scenario.get("data_gaps", [])
    if not isinstance(raw_gaps, list):
        return []
    gaps: list[dict[str, Any]] = []
    for gap in raw_gaps:
        if isinstance(gap, dict):
            copied = dict(gap)
            copied["source"] = "decision_scenario"
            gaps.append(copied)
        else:
            gaps.append(_gap("source_gap", str(gap), source="decision_scenario"))
    return gaps


def _scenario_hash(scenario: dict[str, Any]) -> str:
    reproducibility = scenario.get("reproducibility")
    if isinstance(reproducibility, dict) and isinstance(reproducibility.get("content_hash"), str):
        return reproducibility["content_hash"]
    return _content_hash(scenario)


def _semantic_outcome_core(outcome_core: dict[str, Any]) -> dict[str, Any]:
    semantic = dict(outcome_core)
    semantic["scenario"] = {
        key: value for key, value in outcome_core["scenario"].items() if key != "path"
    }
    provenance = outcome_core["provenance"]
    semantic["provenance"] = {
        "outcome_input": {
            key: value for key, value in provenance["outcome_input"].items() if key != "path"
        },
        "decision_scenario": provenance["decision_scenario"],
    }
    return semantic


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _gap(code: str, message: str, **extra: Any) -> dict[str, Any]:
    gap = {"code": code, "message": message}
    gap.update(extra)
    return gap
