"""Deterministic income-producing real-estate adapter over investment-opportunity/v1."""

import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from family_office_engine.services.investment_opportunity import (
    InvestmentOpportunityError,
    build_investment_opportunity_data,
)

SCHEMA_VERSION = "real-estate-investment/v2"
INPUT_RECORD_TYPE = "RealEstateInvestmentInput"
SNAPSHOT_RECORD_TYPE = "RealEstateInvestmentSnapshot"
CENT = Decimal("0.01")
STREAM_TYPES = {"long_term", "short_term"}


class RealEstateInvestmentError(ValueError):
    pass


def build_real_estate_investment(input_path: Path, output_path: Path) -> dict[str, Any]:
    data = _read_json(input_path)
    _validate_top_level(data)
    generic_data, adapter_scenarios, gaps = _to_generic_input(data)
    try:
        core = build_investment_opportunity_data(
            generic_data, source_type="real-estate-investment-input-json", source_path=input_path
        )
    except InvestmentOpportunityError as exc:
        raise RealEstateInvestmentError(str(exc)) from exc

    scenarios = []
    for generic, adapter in zip(core["scenarios"], adapter_scenarios, strict=True):
        metrics = generic["metrics"]
        scenarios.append(
            {
                "scenario_id": generic["scenario_id"],
                "label": generic["label"],
                "rental_model": adapter["rental_model"],
                "personal_use_days": adapter["personal_use_days"],
                "status": generic["status"],
                "provenance": generic["provenance"],
                "financing_reference": generic["financing_reference"],
                "metrics": {
                    **metrics,
                    "tax_drag": metrics["annual_taxes_and_fees"],
                    "net_exit_value": _money(_decimal(metrics["residual_value"], "residual_value") - _decimal(metrics["exit_costs"], "exit_costs")),
                },
                "rental_streams": adapter["rental_streams"],
                "gap_codes": generic["gap_codes"],
            }
        )
    all_gaps = core["data_gaps"] + gaps
    acquisition_bases = {item["metrics"]["acquisition_basis"] for item in scenarios}
    if len(acquisition_bases) > 1:
        for scenario in scenarios:
            _gap(
                all_gaps,
                scenario["scenario_id"],
                "incomparable_acquisition_basis",
                "Scenario acquisition basis differs; comparison requires the same declared capital and horizon.",
            )
    for scenario in scenarios:
        scenario_codes = {gap["code"] for gap in all_gaps if gap.get("scenario_id") == scenario["scenario_id"]}
        if scenario_codes:
            scenario["status"] = "partial"
            scenario["gap_codes"] = sorted(set(scenario["gap_codes"]) | scenario_codes)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "complete" if not all_gaps else "partial",
        "source": {"type": "real-estate-investment-input-json", "path": str(input_path)},
        "opportunity_id": data["opportunity_id"],
        "label": data["label"],
        "base_currency": data["base_currency"],
        "horizon_years": data["horizon_years"],
        "assumptions": data["assumptions"],
        "provenance": data["provenance"],
        "scenarios": scenarios,
        "data_gaps": all_gaps,
        "summary": {
            "scenario_count": len(scenarios),
            "data_gap_count": len(all_gaps),
            "same_capital_and_horizon_declared": len(acquisition_bases) == 1,
            "personal_use_is_not_taxable_cash_flow": True,
            "review_required": True,
        },
        "notes": (
            "Rental revenue, vacancy, management, maintenance, exit and tax inputs are declared. "
            "No tax rate or tax classification is inferred; financing is only a reference until financing-plan/v1."
        ),
    }
    semantic = json.loads(json.dumps(snapshot))
    semantic["source"].pop("path", None)
    snapshot["reproducibility"] = {"hash_algorithm": "sha256", "content_hash": _hash(semantic)}
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise RealEstateInvestmentError(f"Cannot write real estate investment snapshot: {output_path}") from exc
    return snapshot


def _to_generic_input(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    gaps: list[dict[str, Any]] = list(data.get("data_gaps", []))
    adapter_scenarios = []
    generic_scenarios = []
    for index, raw in enumerate(data["scenarios"]):
        prefix = f"scenarios[{index}]"
        _reject_unknown(raw, {"scenario_id", "label", "provenance", "rental_model", "rental_streams", "management_fee_rate", "operating_costs", "taxes_fees", "tax_classification", "acquisition", "exit", "owner_time", "personal_use", "personal_use_days", "financing_reference"}, prefix)
        scenario_id = _text(raw.get("scenario_id"), f"{prefix}.scenario_id")
        model = raw.get("rental_model")
        if model not in {"long_term", "short_term", "mixed_use"}:
            raise RealEstateInvestmentError(f"{prefix}.rental_model must be long_term, short_term or mixed_use")
        streams = _rental_streams(raw.get("rental_streams"), prefix, model)
        personal_days = raw.get("personal_use_days", 0)
        if not isinstance(personal_days, int) or not 0 <= personal_days <= 366:
            raise RealEstateInvestmentError(f"{prefix}.personal_use_days must be an integer from 0 to 366")
        if model != "mixed_use" and personal_days:
            raise RealEstateInvestmentError(f"{prefix}.personal_use_days is only allowed for mixed_use")
        if model == "mixed_use" and not personal_days:
            _gap(gaps, scenario_id, "missing_personal_use_days", "Mixed-use property requires explicit personal_use_days, including zero.")
        classification = raw.get("tax_classification")
        if not isinstance(classification, dict) or not _text_or_none(classification.get("classification")) or not _text_or_none(classification.get("source")):
            _gap(gaps, scenario_id, "missing_tax_classification", "Tax classification must be supplied by a versioned rule or declared input.")
        else:
            _reject_unknown(classification, {"classification", "source", "rule_reference"}, f"{prefix}.tax_classification")
        management_rate = _decimal(raw.get("management_fee_rate", 0), f"{prefix}.management_fee_rate")
        if management_rate < 0 or management_rate > 1:
            raise RealEstateInvestmentError(f"{prefix}.management_fee_rate must be between 0 and 1")
        revenue = sum((_decimal(item["annual_revenue"], "annual_revenue") for item in streams), Decimal("0"))
        management_fee = revenue * management_rate
        costs = _amounts(raw.get("operating_costs"), f"{prefix}.operating_costs")
        costs.append({"code": "management_fee", "amount": _money(management_fee)})
        taxes = _amounts(raw.get("taxes_fees"), f"{prefix}.taxes_fees")
        acquisition = _component(raw.get("acquisition"), f"{prefix}.acquisition", {"purchase_price", "costs", "initial_capex"})
        exit_plan = _component(raw.get("exit"), f"{prefix}.exit", {"residual_value", "costs"})
        generic_scenarios.append({
            "scenario_id": scenario_id, "label": _text(raw.get("label"), f"{prefix}.label"), "provenance": _provenance(raw.get("provenance"), prefix),
            "financing_reference": raw.get("financing_reference"), "acquisition": acquisition,
            "operations": {"revenue": [{"code": item["stream_id"], "amount": item["annual_revenue"]} for item in streams], "costs": costs, "taxes_fees": taxes},
            "exit": exit_plan, "owner_time": raw.get("owner_time", {"annual_hours": 0, "hourly_value": 0}),
            "personal_use": raw.get("personal_use", {"annual_economic_benefit": 0}),
        })
        adapter_scenarios.append({"rental_model": model, "personal_use_days": personal_days, "rental_streams": streams})
    return ({"schema_version": "investment-opportunity/v1", "record_type": "InvestmentOpportunityInput", "opportunity_id": data["opportunity_id"], "label": data["label"], "asset_type": "income_property", "as_of_date": data["as_of_date"], "base_currency": data["base_currency"], "horizon_years": data["horizon_years"], "assumptions": data["assumptions"], "provenance": data["provenance"], "scenarios": generic_scenarios}, adapter_scenarios, gaps)


def _rental_streams(value: Any, prefix: str, model: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise RealEstateInvestmentError(f"{prefix}.rental_streams must be a non-empty list")
    result = []
    kinds = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict): raise RealEstateInvestmentError(f"{prefix}.rental_streams[{index}] must be an object")
        kind = item.get("stream_type"); kinds.add(kind)
        if kind == "long_term":
            _reject_unknown(item, {"stream_id", "stream_type", "monthly_rent", "vacancy_months"}, f"{prefix}.rental_streams[{index}]")
            vacancy = item.get("vacancy_months")
            if not isinstance(vacancy, int) or not 0 <= vacancy <= 12: raise RealEstateInvestmentError(f"{prefix}.rental_streams[{index}].vacancy_months must be an integer from 0 to 12")
            annual = _decimal(item.get("monthly_rent"), "monthly_rent") * (12 - vacancy)
        elif kind == "short_term":
            _reject_unknown(item, {"stream_id", "stream_type", "nightly_rate", "booked_nights", "available_nights"}, f"{prefix}.rental_streams[{index}]")
            booked, available = item.get("booked_nights"), item.get("available_nights")
            if not isinstance(booked, int) or not isinstance(available, int) or not 0 <= booked <= available <= 366: raise RealEstateInvestmentError(f"{prefix}.rental_streams[{index}] booked_nights must be within available_nights (0..366)")
            annual = _decimal(item.get("nightly_rate"), "nightly_rate") * booked
        else: raise RealEstateInvestmentError(f"{prefix}.rental_streams[{index}].stream_type must be long_term or short_term")
        result.append({"stream_id": _text(item.get("stream_id"), "stream_id"), "stream_type": kind, "annual_revenue": _money(annual)})
    if model != "mixed_use" and kinds != {model}: raise RealEstateInvestmentError(f"{prefix}.rental_streams do not match rental_model")
    if model == "mixed_use" and not kinds: raise RealEstateInvestmentError(f"{prefix}.rental_streams are required for mixed_use")
    return result


def _validate_top_level(data: dict[str, Any]) -> None:
    _reject_unknown(data, {"schema_version", "record_type", "opportunity_id", "label", "as_of_date", "base_currency", "horizon_years", "assumptions", "provenance", "data_gaps", "scenarios"}, "real estate investment input")
    if data.get("schema_version") != SCHEMA_VERSION or data.get("record_type") != INPUT_RECORD_TYPE: raise RealEstateInvestmentError("Unsupported real estate investment schema or record type")
    for field in ("opportunity_id", "label", "as_of_date", "base_currency"): _text(data.get(field), field)
    if len(data["base_currency"]) != 3 or data["base_currency"] != data["base_currency"].upper(): raise RealEstateInvestmentError("base_currency must be an ISO-4217 uppercase code")
    if not isinstance(data.get("horizon_years"), int) or data["horizon_years"] < 1: raise RealEstateInvestmentError("horizon_years must be a positive integer")
    if not isinstance(data.get("assumptions"), list) or not data["assumptions"]: raise RealEstateInvestmentError("assumptions must be a non-empty list")
    if not isinstance(data.get("provenance"), list) or not data["provenance"]: raise RealEstateInvestmentError("provenance must be a non-empty list")
    if not isinstance(data.get("scenarios"), list) or not data["scenarios"]: raise RealEstateInvestmentError("At least one scenario is required")


def _component(value: Any, label: str, fields: set[str]) -> dict[str, list[dict[str, str]]]:
    if not isinstance(value, dict): raise RealEstateInvestmentError(f"{label} must be an object")
    _reject_unknown(value, fields, label)
    return {field: _amounts(value.get(field), f"{label}.{field}") for field in fields}

def _amounts(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list): raise RealEstateInvestmentError(f"{label} must be a list")
    result=[]
    for index, item in enumerate(value):
        if not isinstance(item, dict): raise RealEstateInvestmentError(f"{label}[{index}] must be an object")
        _reject_unknown(item, {"code", "amount"}, f"{label}[{index}]")
        result.append({"code": _text(item.get("code"), f"{label}[{index}].code"), "amount": _money(_decimal(item.get("amount"), f"{label}[{index}].amount"))})
    return result

def _provenance(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value: raise RealEstateInvestmentError(f"{label}.provenance must be a non-empty list")
    return value

def _read_json(path: Path) -> dict[str, Any]:
    try: data=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc: raise RealEstateInvestmentError(f"Missing real estate investment input: {path}") from exc
    except json.JSONDecodeError as exc: raise RealEstateInvestmentError(f"Invalid JSON in real estate investment input {path}: {exc}") from exc
    if not isinstance(data, dict): raise RealEstateInvestmentError("Real estate investment input must contain a JSON object")
    return data

def _decimal(value: Any, label: str) -> Decimal:
    try: result=Decimal(str(value))
    except (InvalidOperation, TypeError) as exc: raise RealEstateInvestmentError(f"{label} must be a decimal") from exc
    if not result.is_finite(): raise RealEstateInvestmentError(f"{label} must be a finite decimal")
    return result

def _money(value: Decimal) -> str: return str(value.quantize(CENT, rounding=ROUND_HALF_UP))
def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip(): raise RealEstateInvestmentError(f"{label} is required")
    return value
def _text_or_none(value: Any) -> str | None: return value if isinstance(value, str) and value.strip() else None
def _reject_unknown(data: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown=sorted(set(data)-allowed)
    if unknown: raise RealEstateInvestmentError(f"{label} has unknown fields: {', '.join(unknown)}")
def _gap(gaps: list[dict[str, Any]], scenario_id: str, code: str, message: str) -> None:
    gaps.append({"code": code, "scenario_id": scenario_id, "message": message})
def _hash(value: dict[str, Any]) -> str: return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
