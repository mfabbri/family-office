"""Deterministic adapter for rentable movable assets over investment-opportunity/v1."""

import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from family_office_engine.services.investment_opportunity import InvestmentOpportunityError, build_investment_opportunity_data

SCHEMA_VERSION = "rentable-movable-asset/v1"
INPUT_RECORD_TYPE = "RentableMovableAssetInput"
SNAPSHOT_RECORD_TYPE = "RentableMovableAssetSnapshot"
CENT = Decimal("0.01")
CLASSIFICATIONS = {"personal", "occasional_rental", "habitual_rental", "business"}
COST_FIELDS = ("insurance", "storage", "cleaning", "delivery_collection", "maintenance", "tyres", "mileage_wear", "major_repair")


class RentableMovableAssetError(ValueError):
    pass


def build_rentable_movable_asset(input_path: Path, output_path: Path) -> dict[str, Any]:
    data = _read_json(input_path)
    _validate_top_level(data)
    generic, adapter_scenarios, gaps = _to_generic_input(data)
    try:
        core = build_investment_opportunity_data(generic, source_type="rentable-movable-asset-input-json", source_path=input_path)
    except InvestmentOpportunityError as exc:
        raise RentableMovableAssetError(str(exc)) from exc
    scenarios = []
    for generic_scenario, adapter in zip(core["scenarios"], adapter_scenarios, strict=True):
        scenario_gaps = {gap["code"] for gap in gaps + core["data_gaps"] if gap.get("scenario_id") == generic_scenario["scenario_id"]}
        scenarios.append({
            "scenario_id": generic_scenario["scenario_id"], "label": generic_scenario["label"],
            "status": "partial" if scenario_gaps else generic_scenario["status"], "provenance": generic_scenario["provenance"],
            "financing_reference": generic_scenario["financing_reference"], "metrics": {
                **generic_scenario["metrics"], "rental_revenue": adapter["rental_revenue"],
                "platform_agency_fee": adapter["platform_agency_fee"], "rental_utilization_rate": adapter["rental_utilization_rate"],
                "net_exit_value": _money(_decimal(generic_scenario["metrics"]["residual_value"], "residual_value") - _decimal(generic_scenario["metrics"]["exit_costs"], "exit_costs")),
            }, "availability": adapter["availability"], "activity_classification": adapter["activity_classification"],
            "cost_drivers": adapter["cost_drivers"], "gap_codes": sorted(set(generic_scenario["gap_codes"]) | scenario_gaps),
        })
    acquisition_bases = {item["metrics"]["acquisition_basis"] for item in scenarios}
    all_gaps = core["data_gaps"] + gaps
    if len(acquisition_bases) > 1:
        for scenario in scenarios:
            _gap(all_gaps, scenario["scenario_id"], "incomparable_acquisition_basis", "Scenario acquisition basis differs; comparison requires the same declared capital and horizon.")
            scenario["status"] = "partial"; scenario["gap_codes"] = sorted(set(scenario["gap_codes"]) | {"incomparable_acquisition_basis"})
    snapshot = {
        "schema_version": SCHEMA_VERSION, "record_type": SNAPSHOT_RECORD_TYPE, "status": "complete" if not all_gaps else "partial",
        "source": {"type": "rentable-movable-asset-input-json", "path": str(input_path)}, "opportunity_id": data["opportunity_id"],
        "label": data["label"], "asset_kind": data["asset_kind"], "base_currency": data["base_currency"], "horizon_years": data["horizon_years"],
        "assumptions": data["assumptions"], "provenance": data["provenance"], "scenarios": scenarios, "data_gaps": all_gaps,
        "summary": {"scenario_count": len(scenarios), "data_gap_count": len(all_gaps), "same_capital_and_horizon_declared": len(acquisition_bases) == 1,
                    "personal_use_is_not_taxable_cash_flow": True, "activity_classification_is_not_inferred": True, "review_required": True},
        "notes": "Rental cash flow uses declared days, rate, fees and costs. Personal use is economic only; tax treatment and activity classification require a declared validated input or remain a gap.",
    }
    semantic = json.loads(json.dumps(snapshot)); semantic["source"].pop("path", None)
    snapshot["reproducibility"] = {"hash_algorithm": "sha256", "content_hash": _hash(semantic)}
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True); output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise RentableMovableAssetError(f"Cannot write rentable movable asset snapshot: {output_path}") from exc
    return snapshot


def _to_generic_input(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    gaps = list(data.get("data_gaps", [])); generic_scenarios = []; adapter_scenarios = []
    for index, raw in enumerate(data["scenarios"]):
        prefix = f"scenarios[{index}]"; _reject_unknown(raw, {"scenario_id", "label", "provenance", "availability", "daily_rate", "platform_agency_fee_rate", *COST_FIELDS, "taxes_fees", "activity_classification", "acquisition", "exit", "owner_time", "personal_use", "financing_reference"}, prefix)
        scenario_id = _text(raw.get("scenario_id"), f"{prefix}.scenario_id")
        availability = _availability(raw.get("availability"), prefix)
        rate = _decimal(raw.get("daily_rate"), f"{prefix}.daily_rate")
        if rate < 0: raise RentableMovableAssetError(f"{prefix}.daily_rate must be non-negative")
        fee_rate = _decimal(raw.get("platform_agency_fee_rate"), f"{prefix}.platform_agency_fee_rate")
        if not 0 <= fee_rate <= 1: raise RentableMovableAssetError(f"{prefix}.platform_agency_fee_rate must be between 0 and 1")
        rental_revenue = rate * availability["rental_days"]; platform_fee = rental_revenue * fee_rate
        costs = [{"code": name, "amount": item["amount"]} for name in COST_FIELDS for item in _amounts(raw.get(name), f"{prefix}.{name}")]
        costs.append({"code": "platform_agency_fee", "amount": _money(platform_fee)})
        classification = raw.get("activity_classification")
        if not isinstance(classification, dict) or classification.get("classification") not in CLASSIFICATIONS or not _text_or_none(classification.get("source")):
            _gap(gaps, scenario_id, "missing_activity_classification", "Activity classification must be a declared validated input or rule result; it is never inferred from rental frequency.")
            classification = None
        else: _reject_unknown(classification, {"classification", "source", "rule_reference"}, f"{prefix}.activity_classification")
        generic_scenarios.append({"scenario_id": scenario_id, "label": _text(raw.get("label"), f"{prefix}.label"), "provenance": _provenance(raw.get("provenance"), prefix), "financing_reference": raw.get("financing_reference"), "acquisition": _component(raw.get("acquisition"), f"{prefix}.acquisition", ("purchase_price", "costs", "initial_capex")), "operations": {"revenue": [{"code": "rental_revenue", "amount": _money(rental_revenue)}], "costs": costs, "taxes_fees": _amounts(raw.get("taxes_fees"), f"{prefix}.taxes_fees")}, "exit": _component(raw.get("exit"), f"{prefix}.exit", ("residual_value", "costs")), "owner_time": raw.get("owner_time", {"annual_hours": 0, "hourly_value": 0}), "personal_use": raw.get("personal_use", {"annual_economic_benefit": 0})})
        adapter_scenarios.append({"availability": availability, "rental_revenue": _money(rental_revenue), "platform_agency_fee": _money(platform_fee), "rental_utilization_rate": _rate(availability["rental_days"], availability["available_days"]), "activity_classification": classification, "cost_drivers": list(COST_FIELDS)})
    return ({"schema_version": "investment-opportunity/v1", "record_type": "InvestmentOpportunityInput", "opportunity_id": data["opportunity_id"], "label": data["label"], "asset_type": data["asset_kind"], "as_of_date": data["as_of_date"], "base_currency": data["base_currency"], "horizon_years": data["horizon_years"], "assumptions": data["assumptions"], "provenance": data["provenance"], "scenarios": generic_scenarios}, adapter_scenarios, gaps)


def _availability(value: Any, prefix: str) -> dict[str, int]:
    if not isinstance(value, dict): raise RentableMovableAssetError(f"{prefix}.availability must be an object")
    _reject_unknown(value, {"available_days", "personal_use_days", "rental_days", "downtime_days"}, f"{prefix}.availability")
    result = {key: value.get(key) for key in ("available_days", "personal_use_days", "rental_days", "downtime_days")}
    if not all(isinstance(item, int) and item >= 0 for item in result.values()): raise RentableMovableAssetError(f"{prefix}.availability days must be non-negative integers")
    if not 1 <= result["available_days"] <= 366: raise RentableMovableAssetError(f"{prefix}.availability.available_days must be 1..366")
    if result["personal_use_days"] + result["rental_days"] + result["downtime_days"] > result["available_days"]: raise RentableMovableAssetError(f"{prefix}.availability personal, rental and downtime days exceed available_days")
    return result


def _validate_top_level(data: dict[str, Any]) -> None:
    _reject_unknown(data, {"schema_version", "record_type", "opportunity_id", "label", "asset_kind", "as_of_date", "base_currency", "horizon_years", "assumptions", "provenance", "data_gaps", "scenarios"}, "rentable movable asset input")
    if data.get("schema_version") != SCHEMA_VERSION or data.get("record_type") != INPUT_RECORD_TYPE: raise RentableMovableAssetError("Unsupported rentable movable asset schema or record type")
    for field in ("opportunity_id", "label", "asset_kind", "as_of_date", "base_currency"): _text(data.get(field), field)
    if len(data["base_currency"]) != 3 or data["base_currency"] != data["base_currency"].upper(): raise RentableMovableAssetError("base_currency must be an ISO-4217 uppercase code")
    if not isinstance(data.get("horizon_years"), int) or data["horizon_years"] < 1: raise RentableMovableAssetError("horizon_years must be a positive integer")
    if not isinstance(data.get("assumptions"), list) or not data["assumptions"] or not isinstance(data.get("provenance"), list) or not data["provenance"] or not isinstance(data.get("scenarios"), list) or not data["scenarios"]: raise RentableMovableAssetError("assumptions, provenance and scenarios must be non-empty lists")


def _component(value: Any, label: str, fields: tuple[str, ...]) -> dict[str, list[dict[str, str]]]:
    if not isinstance(value, dict): raise RentableMovableAssetError(f"{label} must be an object")
    _reject_unknown(value, set(fields), label); return {field: _amounts(value.get(field), f"{label}.{field}") for field in fields}
def _amounts(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list): raise RentableMovableAssetError(f"{label} must be a list")
    result=[]
    for index, item in enumerate(value):
        if not isinstance(item, dict): raise RentableMovableAssetError(f"{label}[{index}] must be an object")
        _reject_unknown(item, {"code", "amount"}, f"{label}[{index}]"); result.append({"code": _text(item.get("code"), f"{label}[{index}].code"), "amount": _money(_decimal(item.get("amount"), f"{label}[{index}].amount"))})
    return result
def _provenance(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value: raise RentableMovableAssetError(f"{label}.provenance must be a non-empty list")
    return value
def _read_json(path: Path) -> dict[str, Any]:
    try: data=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc: raise RentableMovableAssetError(f"Missing rentable movable asset input: {path}") from exc
    except json.JSONDecodeError as exc: raise RentableMovableAssetError(f"Invalid JSON in rentable movable asset input {path}: {exc}") from exc
    if not isinstance(data, dict): raise RentableMovableAssetError("Rentable movable asset input must contain a JSON object")
    return data
def _decimal(value: Any, label: str) -> Decimal:
    try: result=Decimal(str(value))
    except (InvalidOperation, TypeError) as exc: raise RentableMovableAssetError(f"{label} must be a decimal") from exc
    if not result.is_finite(): raise RentableMovableAssetError(f"{label} must be a finite decimal")
    return result
def _money(value: Decimal) -> str: return str(value.quantize(CENT, rounding=ROUND_HALF_UP))
def _rate(numerator: int, denominator: int) -> str: return str((Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip(): raise RentableMovableAssetError(f"{label} is required")
    return value
def _text_or_none(value: Any) -> str | None: return value if isinstance(value, str) and value.strip() else None
def _reject_unknown(data: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown=sorted(set(data)-allowed)
    if unknown: raise RentableMovableAssetError(f"{label} has unknown fields: {', '.join(unknown)}")
def _gap(gaps: list[dict[str, Any]], scenario_id: str, code: str, message: str) -> None:
    if not any(item.get("scenario_id") == scenario_id and item.get("code") == code for item in gaps): gaps.append({"code": code, "scenario_id": scenario_id, "message": message})
def _hash(value: dict[str, Any]) -> str: return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
