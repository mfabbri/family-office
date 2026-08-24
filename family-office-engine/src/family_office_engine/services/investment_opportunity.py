"""Deterministic generic investment-opportunity core (no tax or market assumptions)."""

import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "investment-opportunity/v1"
INPUT_RECORD_TYPE = "InvestmentOpportunityInput"
SNAPSHOT_RECORD_TYPE = "InvestmentOpportunitySnapshot"
CENT = Decimal("0.01")


class InvestmentOpportunityError(ValueError):
    pass


def build_investment_opportunity(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Build a reproducible snapshot from explicitly supplied scenario inputs."""
    data = _read_json(input_path)
    _validate_top_level(data)
    gaps = _declared_gaps(data.get("data_gaps", []))
    scenarios = [_build_scenario(item, index, gaps) for index, item in enumerate(data["scenarios"])]
    core = {
        "source": {"type": "investment-opportunity-input-json", "path": str(input_path)},
        "opportunity_id": data["opportunity_id"],
        "label": data["label"],
        "asset_type": data["asset_type"],
        "as_of_date": data["as_of_date"],
        "base_currency": data["base_currency"],
        "horizon_years": data["horizon_years"],
        "assumptions": data["assumptions"],
        "provenance": data["provenance"],
        "scenarios": scenarios,
        "data_gaps": gaps,
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "complete" if not gaps else "partial",
        **core,
        "summary": {
            "scenario_count": len(scenarios),
            "complete_scenario_count": sum(item["status"] == "complete" for item in scenarios),
            "data_gap_count": len(gaps),
            "personal_use_benefit_is_not_cash_flow": True,
            "review_required": True,
        },
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": _content_hash(_semantic_core(core))},
        "notes": (
            "The core calculates only explicit arithmetic. Taxes, legal classification, financing, market "
            "returns, utilization and residual values are inputs or data gaps; personal-use benefit is excluded "
            "from operating and fiscal cash flow."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise InvestmentOpportunityError(f"Cannot write investment opportunity snapshot: {output_path}") from exc
    return snapshot


def _validate_top_level(data: dict[str, Any]) -> None:
    if data.get("schema_version") != SCHEMA_VERSION:
        raise InvestmentOpportunityError(f"Unsupported investment opportunity schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        raise InvestmentOpportunityError(f"Unsupported investment opportunity record type: {data.get('record_type')}")
    for field in ("opportunity_id", "label", "asset_type", "as_of_date", "base_currency"):
        _required_text(data.get(field), field)
    if len(data["base_currency"]) != 3 or data["base_currency"] != data["base_currency"].upper():
        raise InvestmentOpportunityError("base_currency must be an ISO-4217 uppercase code")
    if not isinstance(data.get("horizon_years"), int) or data["horizon_years"] < 1:
        raise InvestmentOpportunityError("horizon_years must be a positive integer")
    if not isinstance(data.get("provenance"), list) or not data["provenance"]:
        raise InvestmentOpportunityError("provenance must be a non-empty list")
    if not isinstance(data.get("assumptions"), list) or not data["assumptions"]:
        raise InvestmentOpportunityError("assumptions must be a non-empty list of explicit versioned inputs")
    for index, assumption in enumerate(data["assumptions"]):
        if not isinstance(assumption, dict):
            raise InvestmentOpportunityError(f"assumptions[{index}] must be an object")
        for field in ("assumption_id", "version", "source"):
            _required_text(assumption.get(field), f"assumptions[{index}].{field}")
    if not isinstance(data.get("scenarios"), list) or not data["scenarios"]:
        raise InvestmentOpportunityError("At least one scenario is required")


def _build_scenario(raw: Any, index: int, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise InvestmentOpportunityError(f"scenarios[{index}] must be an object")
    scenario_id = _required_text(raw.get("scenario_id"), f"scenarios[{index}].scenario_id")
    label = _required_text(raw.get("label"), f"scenarios[{index}].label")
    if not isinstance(raw.get("provenance"), list) or not raw["provenance"]:
        raise InvestmentOpportunityError(f"scenarios[{index}].provenance must be a non-empty list")
    acquisition = _component(raw.get("acquisition"), scenario_id, "acquisition", gaps, required=True)
    operations = _component(raw.get("operations"), scenario_id, "operations", gaps, required=True)
    exit_plan = _component(raw.get("exit"), scenario_id, "exit", gaps, required=False)
    owner_time = raw.get("owner_time")
    personal_use = raw.get("personal_use")
    acquisition_basis = _sum(acquisition["purchase_price"]) + _sum(acquisition["costs"]) + _sum(acquisition["initial_capex"])
    annual_revenue = _sum(operations["revenue"])
    annual_operating_costs = _sum(operations["costs"])
    annual_taxes_fees = _sum(operations["taxes_fees"])
    owner_time_cost = _owner_time_cost(owner_time, scenario_id, gaps)
    personal_use_benefit = _personal_use_benefit(personal_use, scenario_id, gaps)
    residual_value = _sum(exit_plan["residual_value"])
    exit_costs = _sum(exit_plan["costs"])
    noi = annual_revenue - annual_operating_costs
    annual_free_cash_flow = noi - annual_taxes_fees - owner_time_cost
    scenario_gaps = [gap["code"] for gap in gaps if gap.get("scenario_id") == scenario_id]
    return {
        "scenario_id": scenario_id,
        "label": label,
        "status": "partial" if scenario_gaps else "complete",
        "provenance": raw["provenance"],
        "financing_reference": _optional_text(raw.get("financing_reference"), f"scenarios[{index}].financing_reference"),
        "inputs": {"acquisition": acquisition, "operations": operations, "exit": exit_plan},
        "metrics": {
            "acquisition_basis": _money_text(acquisition_basis),
            "annual_revenue": _money_text(annual_revenue),
            "annual_operating_costs": _money_text(annual_operating_costs),
            "annual_taxes_and_fees": _money_text(annual_taxes_fees),
            "annual_owner_time_cost": _money_text(owner_time_cost),
            "net_operating_income": _money_text(noi),
            "annual_free_cash_flow": _money_text(annual_free_cash_flow),
            "residual_value": _money_text(residual_value),
            "exit_costs": _money_text(exit_costs),
            "personal_use_economic_benefit": _money_text(personal_use_benefit),
        },
        "gap_codes": scenario_gaps,
    }


def _component(raw: Any, scenario_id: str, name: str, gaps: list[dict[str, Any]], required: bool) -> dict[str, list[dict[str, str]]]:
    if raw is None:
        if required:
            _gap(gaps, scenario_id, f"missing_{name}_inputs", f"{name.capitalize()} inputs must be explicit.")
        raw = {}
    if not isinstance(raw, dict):
        raise InvestmentOpportunityError(f"{name} must be an object")
    fields = ("purchase_price", "costs", "initial_capex") if name == "acquisition" else (("revenue", "costs", "taxes_fees") if name == "operations" else ("residual_value", "costs"))
    result = {}
    for field in fields:
        value = raw.get(field)
        if value is None:
            if required:
                _gap(gaps, scenario_id, f"missing_{name}_{field}", f"{name}.{field} must be explicit; use an empty list for zero.")
            value = []
        result[field] = _money_items(value, f"{name}.{field}")
    return result


def _owner_time_cost(raw: Any, scenario_id: str, gaps: list[dict[str, Any]]) -> Decimal:
    if raw is None:
        _gap(gaps, scenario_id, "missing_owner_time_input", "Owner time and its value must be explicit; use annual_hours 0 when not applicable.")
        return Decimal("0")
    if not isinstance(raw, dict):
        raise InvestmentOpportunityError("owner_time must be an object")
    hours, value = raw.get("annual_hours"), raw.get("hourly_value")
    if hours is None or value is None:
        _gap(gaps, scenario_id, "missing_owner_time_input", "annual_hours and hourly_value must both be explicit.")
        return Decimal("0")
    hours_decimal = _decimal(hours, "owner_time.annual_hours")
    if hours_decimal < 0:
        raise InvestmentOpportunityError("owner_time.annual_hours must be non-negative")
    return hours_decimal * _decimal(value, "owner_time.hourly_value")


def _personal_use_benefit(raw: Any, scenario_id: str, gaps: list[dict[str, Any]]) -> Decimal:
    if raw is None or not isinstance(raw, dict) or raw.get("annual_economic_benefit") is None:
        _gap(gaps, scenario_id, "missing_personal_use_benefit", "Personal-use economic benefit must be explicit, including zero when absent.")
        return Decimal("0")
    return _decimal(raw["annual_economic_benefit"], "personal_use.annual_economic_benefit")


def _money_items(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise InvestmentOpportunityError(f"{label} must be a list")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise InvestmentOpportunityError(f"{label}[{index}] must be an object")
        result.append({"code": _required_text(item.get("code"), f"{label}[{index}].code"), "amount": _money_text(_decimal(item.get("amount"), f"{label}[{index}].amount"))})
    return result


def _sum(items: list[dict[str, str]]) -> Decimal:
    return sum((_decimal(item["amount"], "amount") for item in items), Decimal("0"))


def _declared_gaps(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) and item.get("code") for item in value):
        raise InvestmentOpportunityError("data_gaps must be a list of objects with code")
    return list(value)


def _gap(gaps: list[dict[str, Any]], scenario_id: str, code: str, message: str) -> None:
    if not any(item.get("scenario_id") == scenario_id and item.get("code") == code for item in gaps):
        gaps.append({"code": code, "scenario_id": scenario_id, "message": message})


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InvestmentOpportunityError(f"Missing investment opportunity input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InvestmentOpportunityError(f"Invalid JSON in investment opportunity input {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InvestmentOpportunityError("Investment opportunity input must contain a JSON object")
    return data


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvestmentOpportunityError(f"{label} is required")
    return value


def _optional_text(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, label)


def _decimal(value: Any, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise InvestmentOpportunityError(f"{label} must be a decimal") from exc


def _money_text(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _semantic_core(core: dict[str, Any]) -> dict[str, Any]:
    semantic = json.loads(json.dumps(core))
    semantic["source"].pop("path", None)
    return semantic


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
