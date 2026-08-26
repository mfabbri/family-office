"""Deterministic comparison of declared investment scenarios and opportunity cost."""

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "investment-opportunity-comparison/v1"
INPUT_RECORD_TYPE = "InvestmentOpportunityComparisonInput"
SNAPSHOT_RECORD_TYPE = "InvestmentOpportunityComparisonSnapshot"
CENT = Decimal("0.01")
SCENARIO_TYPES = {"base", "upside", "adverse"}


class InvestmentOpportunityComparisonError(ValueError):
    pass


def build_investment_opportunity_comparison(input_path: Path, output_path: Path) -> dict[str, Any]:
    data = _read_json(input_path)
    snapshot = build_investment_opportunity_comparison_data(data, source_path=input_path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise InvestmentOpportunityComparisonError(f"Cannot write investment opportunity comparison: {output_path}") from exc
    return snapshot


def build_investment_opportunity_comparison_data(data: dict[str, Any], *, source_path: Path | None = None) -> dict[str, Any]:
    _validate_top_level(data)
    gaps = list(data.get("data_gaps", []))
    primary = _alternative(data["primary"], "primary", data, gaps, required_scenarios=True)
    benchmark_raw = data.get("benchmark")
    benchmark = None
    if benchmark_raw is None:
        _gap(gaps, "missing_benchmark", "Opportunity cost cannot be calculated without a declared benchmark alternative.")
    else:
        benchmark = _alternative(benchmark_raw, "benchmark", data, gaps, required_scenarios=False)
    comparisons = [_comparison_row(item, benchmark, gaps) for item in primary["scenarios"]]
    all_gaps = _deduplicate_gaps(gaps)
    status = "complete" if not all_gaps else "partial"
    core = {
        "source": {"type": "investment-opportunity-comparison-input-json", "path": str(source_path) if source_path else None},
        "comparison_id": data["comparison_id"], "label": data["label"], "as_of_date": data["as_of_date"],
        "base_currency": data["base_currency"], "capital_amount": _money(data["capital_amount"]),
        "horizon_years": data["horizon_years"], "assumptions": data["assumptions"], "provenance": data["provenance"],
        "primary": primary, "benchmark": benchmark, "comparisons": comparisons, "data_gaps": all_gaps,
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION, "record_type": SNAPSHOT_RECORD_TYPE, "status": status, **core,
        "summary": {
            "scenario_count": len(primary["scenarios"]), "data_gap_count": len(all_gaps),
            "same_capital_and_horizon_declared": not any(gap["code"] in {"incomparable_capital", "incomparable_horizon"} for gap in all_gaps),
            "benchmark_available": benchmark is not None,
            "automatic_ranking_produced": False,
            "dimensions_kept_separate": ["return", "risk", "liquidity", "management_burden"],
            "review_required": True,
        },
        "notes": (
            "Scenario cash flows, exit values, financing effects, household constraints and stress factors are declared inputs. "
            "The service derives only transparent horizon totals and opportunity-cost differences; it does not infer a benchmark, "
            "tax treatment, market return, liquidity threshold or ranking."
        ),
    }
    semantic = json.loads(json.dumps(core))
    semantic["source"].pop("path", None)
    snapshot["reproducibility"] = {"hash_algorithm": "sha256", "content_hash": _hash(semantic)}
    return snapshot


def _alternative(raw: Any, label: str, top: dict[str, Any], gaps: list[dict[str, Any]], *, required_scenarios: bool) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise InvestmentOpportunityComparisonError(f"{label} must be an object")
    _reject_unknown(raw, {"alternative_id", "label", "capital_amount", "horizon_years", "provenance", "scenarios"}, label)
    for field in ("alternative_id", "label"):
        _text(raw.get(field), f"{label}.{field}")
    capital = _decimal(raw.get("capital_amount"), f"{label}.capital_amount")
    horizon = raw.get("horizon_years")
    if not isinstance(horizon, int) or horizon < 1:
        raise InvestmentOpportunityComparisonError(f"{label}.horizon_years must be a positive integer")
    if capital != _decimal(top["capital_amount"], "capital_amount"):
        _gap(gaps, "incomparable_capital", "All alternatives must use the same declared capital amount.", alternative_id=raw["alternative_id"])
    if horizon != top["horizon_years"]:
        _gap(gaps, "incomparable_horizon", "All alternatives must use the same declared horizon.", alternative_id=raw["alternative_id"])
    if not isinstance(raw.get("provenance"), list) or not raw["provenance"]:
        raise InvestmentOpportunityComparisonError(f"{label}.provenance must be a non-empty list")
    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise InvestmentOpportunityComparisonError(f"{label}.scenarios must be a non-empty list")
    built = [_scenario(item, label, raw["alternative_id"], horizon, gaps) for item in scenarios]
    types = {item["scenario_type"] for item in built}
    if len(types) != len(built):
        raise InvestmentOpportunityComparisonError(f"{label}.scenarios must not repeat scenario_type")
    if required_scenarios and types != SCENARIO_TYPES:
        raise InvestmentOpportunityComparisonError("primary.scenarios must declare exactly base, upside and adverse scenarios")
    return {"alternative_id": raw["alternative_id"], "label": raw["label"], "capital_amount": _money(capital), "horizon_years": horizon, "provenance": raw["provenance"], "scenarios": built}


def _scenario(raw: Any, alternative_label: str, alternative_id: str, horizon: int, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise InvestmentOpportunityComparisonError(f"{alternative_label}.scenarios items must be objects")
    allowed = {"scenario_type", "label", "provenance", "stress_factors", "annual_equity_cash_flow", "net_exit_value", "annual_owner_hours", "annual_owner_time_cost", "household_constraints"}
    _reject_unknown(raw, allowed, f"{alternative_label}.scenario")
    scenario_type = raw.get("scenario_type")
    if scenario_type not in SCENARIO_TYPES:
        raise InvestmentOpportunityComparisonError(f"{alternative_label}.scenario_type must be base, upside or adverse")
    if not isinstance(raw.get("provenance"), list) or not raw["provenance"]:
        raise InvestmentOpportunityComparisonError(f"{alternative_label}.{scenario_type}.provenance must be a non-empty list")
    factors = _stress_factors(raw.get("stress_factors"), alternative_label, scenario_type)
    if scenario_type != "base" and not factors:
        _gap(gaps, "missing_stress_factors", "Upside and adverse scenarios require explicit stress factors.", alternative_id=alternative_id, scenario_type=scenario_type)
    annual_cash_flow = _decimal(raw.get("annual_equity_cash_flow"), f"{alternative_label}.{scenario_type}.annual_equity_cash_flow")
    exit_value = _decimal(raw.get("net_exit_value"), f"{alternative_label}.{scenario_type}.net_exit_value")
    owner_hours = _decimal(raw.get("annual_owner_hours"), f"{alternative_label}.{scenario_type}.annual_owner_hours")
    owner_cost = _decimal(raw.get("annual_owner_time_cost"), f"{alternative_label}.{scenario_type}.annual_owner_time_cost")
    if owner_hours < 0 or owner_cost < 0:
        raise InvestmentOpportunityComparisonError("annual_owner_hours and annual_owner_time_cost must be non-negative")
    constraints = _household_constraints(raw.get("household_constraints"), alternative_id, scenario_type, gaps)
    # Owner time is exposed as a separate burden. Adapter/financing cash-flow outputs may
    # already include it, so subtracting it here would silently double count it.
    net_horizon_value = annual_cash_flow * horizon + exit_value
    return {
        "scenario_type": scenario_type, "label": _text(raw.get("label"), f"{alternative_label}.{scenario_type}.label"), "provenance": raw["provenance"],
        "stress_factors": factors,
        "return": {"annual_equity_cash_flow": _money(annual_cash_flow), "net_exit_value": _money(exit_value), "net_horizon_value_before_initial_capital": _money(net_horizon_value)},
        "risk": {"negative_annual_equity_cash_flow": annual_cash_flow < 0, "scenario_type": scenario_type},
        "liquidity": constraints,
        "management_burden": {"annual_owner_hours": _money(owner_hours), "annual_owner_time_cost": _money(owner_cost)},
    }


def _comparison_row(primary: dict[str, Any], benchmark: dict[str, Any] | None, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    row = {"scenario_type": primary["scenario_type"], "primary_net_horizon_value_before_initial_capital": primary["return"]["net_horizon_value_before_initial_capital"], "opportunity_cost": None}
    if benchmark is None:
        return row
    candidates = [item for item in benchmark["scenarios"] if item["scenario_type"] == primary["scenario_type"]]
    if not candidates:
        _gap(gaps, "missing_benchmark_scenario", "Benchmark must declare the same scenario type to calculate opportunity cost.", scenario_type=primary["scenario_type"])
        return row
    benchmark_value = _decimal(candidates[0]["return"]["net_horizon_value_before_initial_capital"], "benchmark net horizon value")
    primary_value = _decimal(primary["return"]["net_horizon_value_before_initial_capital"], "primary net horizon value")
    row["benchmark_net_horizon_value_before_initial_capital"] = _money(benchmark_value)
    row["opportunity_cost"] = _money(benchmark_value - primary_value)
    return row


def _household_constraints(raw: Any, alternative_id: str, scenario_type: str, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    if raw is None:
        _gap(gaps, "missing_household_constraints", "Liquidity, concentration, retirement impact and reversibility must be declared or remain data gaps.", alternative_id=alternative_id, scenario_type=scenario_type)
        return {"liquidity_breach": None, "concentration_breach": None, "retirement_work_exit_cash_flow_impact": None, "reversibility": None}
    if not isinstance(raw, dict):
        raise InvestmentOpportunityComparisonError("household_constraints must be an object")
    allowed = {"liquidity_reserve_required", "liquid_assets_after_commitment", "concentration_limit", "concentration_after_commitment", "retirement_work_exit_cash_flow_impact", "reversibility"}
    _reject_unknown(raw, allowed, "household_constraints")
    required = ("liquidity_reserve_required", "liquid_assets_after_commitment", "concentration_limit", "concentration_after_commitment", "retirement_work_exit_cash_flow_impact", "reversibility")
    missing = [field for field in required if raw.get(field) is None]
    if missing:
        _gap(gaps, "incomplete_household_constraints", f"Missing household constraints: {', '.join(missing)}.", alternative_id=alternative_id, scenario_type=scenario_type)
    reserve = _decimal_or_none(raw.get("liquidity_reserve_required"), "liquidity_reserve_required")
    liquid = _decimal_or_none(raw.get("liquid_assets_after_commitment"), "liquid_assets_after_commitment")
    limit = _decimal_or_none(raw.get("concentration_limit"), "concentration_limit")
    concentration = _decimal_or_none(raw.get("concentration_after_commitment"), "concentration_after_commitment")
    if limit is not None and not Decimal("0") <= limit <= Decimal("1"):
        raise InvestmentOpportunityComparisonError("concentration_limit must be between 0 and 1")
    if concentration is not None and not Decimal("0") <= concentration <= Decimal("1"):
        raise InvestmentOpportunityComparisonError("concentration_after_commitment must be between 0 and 1")
    return {"liquidity_reserve_required": _money(reserve) if reserve is not None else None, "liquid_assets_after_commitment": _money(liquid) if liquid is not None else None, "liquidity_breach": liquid < reserve if liquid is not None and reserve is not None else None, "concentration_limit": _rate(limit) if limit is not None else None, "concentration_after_commitment": _rate(concentration) if concentration is not None else None, "concentration_breach": concentration > limit if concentration is not None and limit is not None else None, "retirement_work_exit_cash_flow_impact": _money(_decimal_or_none(raw.get("retirement_work_exit_cash_flow_impact"), "retirement_work_exit_cash_flow_impact")) if raw.get("retirement_work_exit_cash_flow_impact") is not None else None, "reversibility": raw.get("reversibility")}


def _stress_factors(raw: Any, alternative_label: str, scenario_type: str) -> list[dict[str, str]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise InvestmentOpportunityComparisonError("stress_factors must be a list")
    result = []
    for index, factor in enumerate(raw):
        if not isinstance(factor, dict):
            raise InvestmentOpportunityComparisonError("stress_factors items must be objects")
        _reject_unknown(factor, {"factor", "direction", "value", "unit"}, f"stress_factors[{index}]")
        direction = factor.get("direction")
        if direction not in {"up", "down"}:
            raise InvestmentOpportunityComparisonError("stress factor direction must be up or down")
        result.append({"factor": _text(factor.get("factor"), "stress factor"), "direction": direction, "value": _money(_decimal(factor.get("value"), "stress factor value")), "unit": _text(factor.get("unit"), "stress factor unit")})
    return result


def _validate_top_level(data: dict[str, Any]) -> None:
    _reject_unknown(data, {"schema_version", "record_type", "comparison_id", "label", "as_of_date", "base_currency", "capital_amount", "horizon_years", "assumptions", "provenance", "primary", "benchmark", "data_gaps"}, "investment opportunity comparison input")
    if data.get("schema_version") != SCHEMA_VERSION or data.get("record_type") != INPUT_RECORD_TYPE:
        raise InvestmentOpportunityComparisonError("Unsupported investment opportunity comparison schema or record type")
    for field in ("comparison_id", "label", "as_of_date", "base_currency"):
        _text(data.get(field), field)
    try:
        date.fromisoformat(data["as_of_date"])
    except ValueError as exc:
        raise InvestmentOpportunityComparisonError("as_of_date must be an ISO date") from exc
    if len(data["base_currency"]) != 3 or data["base_currency"] != data["base_currency"].upper():
        raise InvestmentOpportunityComparisonError("base_currency must be an ISO-4217 uppercase code")
    if _decimal(data.get("capital_amount"), "capital_amount") < 0:
        raise InvestmentOpportunityComparisonError("capital_amount must be non-negative")
    if not isinstance(data.get("horizon_years"), int) or data["horizon_years"] < 1:
        raise InvestmentOpportunityComparisonError("horizon_years must be a positive integer")
    if not isinstance(data.get("assumptions"), list) or not data["assumptions"]:
        raise InvestmentOpportunityComparisonError("assumptions must be a non-empty list")
    for index, assumption in enumerate(data["assumptions"]):
        if not isinstance(assumption, dict):
            raise InvestmentOpportunityComparisonError(f"assumptions[{index}] must be an object")
        for field in ("assumption_id", "version", "source"):
            _text(assumption.get(field), f"assumptions[{index}].{field}")
    if not isinstance(data.get("provenance"), list) or not data["provenance"]:
        raise InvestmentOpportunityComparisonError("provenance must be a non-empty list")
    if not isinstance(data.get("data_gaps", []), list) or not all(isinstance(item, dict) and item.get("code") for item in data.get("data_gaps", [])):
        raise InvestmentOpportunityComparisonError("data_gaps must be a list of objects with code")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InvestmentOpportunityComparisonError(f"Missing comparison input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InvestmentOpportunityComparisonError(f"Invalid JSON in comparison input {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InvestmentOpportunityComparisonError("Comparison input must contain a JSON object")
    return data


def _gap(gaps: list[dict[str, Any]], code: str, message: str, **context: str) -> None:
    gaps.append({"code": code, "message": message, **context})


def _deduplicate_gaps(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list({json.dumps(item, sort_keys=True): item for item in gaps}.values())


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvestmentOpportunityComparisonError(f"{label} is required")
    return value


def _decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise InvestmentOpportunityComparisonError(f"{label} must be a decimal") from exc
    if not result.is_finite():
        raise InvestmentOpportunityComparisonError(f"{label} must be a finite decimal")
    return result


def _decimal_or_none(value: Any, label: str) -> Decimal | None:
    return None if value is None else _decimal(value, label)


def _money(value: Decimal | Any) -> str:
    return str(_decimal(value, "amount").quantize(CENT, rounding=ROUND_HALF_UP))


def _rate(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def _reject_unknown(data: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise InvestmentOpportunityComparisonError(f"{label} has unknown fields: {', '.join(unknown)}")


def _hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
