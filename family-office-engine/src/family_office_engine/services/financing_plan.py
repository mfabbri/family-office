"""Deterministic financing-plan/v1 schedules from declared debt assumptions."""

import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "financing-plan/v1"
INPUT_RECORD_TYPE = "FinancingPlanInput"
SNAPSHOT_RECORD_TYPE = "FinancingPlanSnapshot"
CENT = Decimal("0.01")
RATE = Decimal("0.0001")


class FinancingPlanError(ValueError):
    pass


def build_financing_plan(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Build a reproducible annual debt schedule without inferring rates or fees."""
    data = _read_json(input_path)
    snapshot = build_financing_plan_data(data, source_path=input_path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise FinancingPlanError(f"Cannot write financing plan snapshot: {output_path}") from exc
    return snapshot


def build_financing_plan_data(data: dict[str, Any], *, source_path: Path | None = None) -> dict[str, Any]:
    _validate_top_level(data)
    gaps = _declared_gaps(data.get("data_gaps", []))
    terms = _terms(data["terms"])
    asset = _asset_cash_flow(data["asset_cash_flow"], gaps)
    collateral_value = _money(data["collateral_value"], "collateral_value")
    equity_contribution = _money(data["equity_contribution"], "equity_contribution")
    if collateral_value <= 0:
        raise FinancingPlanError("collateral_value must be greater than zero")
    if equity_contribution < 0:
        raise FinancingPlanError("equity_contribution must be non-negative")
    if terms["loan_amount"] == 0:
        schedule: list[dict[str, Any]] = []
        _gap(gaps, "dscr_not_applicable_zero_debt", "DSCR is not applicable when no debt service exists.")
    else:
        schedule = _schedule(terms)
    ltv = terms["loan_amount"] / collateral_value
    total_interest = sum((item["interest"] for item in schedule), Decimal("0"))
    total_principal = sum((item["principal"] + item["early_repayment_principal"] for item in schedule), Decimal("0"))
    total_debt_service = sum((item["debt_service"] for item in schedule), Decimal("0"))
    total_fees = terms["origination_fee"] + sum((item["early_repayment_fee"] for item in schedule), Decimal("0"))
    periods = []
    for item in schedule:
        dscr = None
        if asset["annual_net_operating_income"] is not None and item["debt_service"] > 0:
            dscr = asset["annual_net_operating_income"] / item["debt_service"]
        elif item["debt_service"] > 0:
            _gap(gaps, "missing_noi_for_dscr", "Annual net operating income is required to calculate DSCR.")
        periods.append({
            "year": item["year"],
            "opening_debt": _money_text(item["opening_debt"]),
            "interest": _money_text(item["interest"]),
            "scheduled_principal": _money_text(item["principal"]),
            "early_repayment_principal": _money_text(item["early_repayment_principal"]),
            "early_repayment_fee": _money_text(item["early_repayment_fee"]),
            "debt_service": _money_text(item["debt_service"]),
            "remaining_debt": _money_text(item["remaining_debt"]),
            "dscr": _rate_text(dscr) if dscr is not None else None,
            "asset_cash_flow_before_financing": _money_text(asset["annual_free_cash_flow"]),
            "equity_cash_flow_after_financing": _money_text(asset["annual_free_cash_flow"] - item["debt_service"]),
        })
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "complete" if not gaps else "partial",
        "source": {"type": "financing-plan-input-json", "path": str(source_path) if source_path else None},
        "plan_id": data["plan_id"], "label": data["label"], "as_of_date": data["as_of_date"],
        "base_currency": data["base_currency"], "asset_reference": data["asset_reference"],
        "assumptions": data["assumptions"], "provenance": data["provenance"],
        "terms": _public_terms(terms), "asset_cash_flow": _public_asset(asset), "annual_schedule": periods,
        "metrics": {
            "loan_to_value": _rate_text(ltv), "initial_equity_contribution": _money_text(equity_contribution),
            "origination_fee": _money_text(terms["origination_fee"]), "total_interest": _money_text(total_interest),
            "total_principal_repaid": _money_text(total_principal), "total_financing_fees": _money_text(total_fees),
            "total_debt_service": _money_text(total_debt_service),
            "asset_cash_flow_before_financing": _money_text(asset["annual_free_cash_flow"]),
            "equity_cash_flow_after_financing": _money_text(asset["annual_free_cash_flow"] * len(schedule) - total_debt_service - terms["origination_fee"]),
            "remaining_debt": _money_text(schedule[-1]["remaining_debt"] if schedule else Decimal("0")),
        },
        "data_gaps": gaps,
        "summary": {"schedule_years": len(schedule), "data_gap_count": len(gaps), "review_required": True,
                    "asset_and_equity_cash_flow_are_separate": True, "rates_and_fees_are_declared": True},
        "notes": "Financing arithmetic uses only declared rates, fees, repayments and asset cash flow. It does not infer taxes, market returns, collateral values, rate paths or asset performance.",
    }
    semantic = json.loads(json.dumps(snapshot)); semantic["source"].pop("path", None)
    snapshot["reproducibility"] = {"hash_algorithm": "sha256", "content_hash": _hash(semantic)}
    return snapshot


def _validate_top_level(data: dict[str, Any]) -> None:
    _reject_unknown(data, {"schema_version", "record_type", "plan_id", "label", "as_of_date", "base_currency", "asset_reference", "collateral_value", "equity_contribution", "asset_cash_flow", "terms", "assumptions", "provenance", "data_gaps"}, "financing plan input")
    if data.get("schema_version") != SCHEMA_VERSION or data.get("record_type") != INPUT_RECORD_TYPE:
        raise FinancingPlanError("Unsupported financing plan schema or record type")
    for field in ("plan_id", "label", "as_of_date", "base_currency", "asset_reference"):
        _text(data.get(field), field)
    if len(data["base_currency"]) != 3 or data["base_currency"] != data["base_currency"].upper():
        raise FinancingPlanError("base_currency must be an ISO-4217 uppercase code")
    if not isinstance(data.get("assumptions"), list) or not data["assumptions"] or not isinstance(data.get("provenance"), list) or not data["provenance"]:
        raise FinancingPlanError("assumptions and provenance must be non-empty lists")


def _terms(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict): raise FinancingPlanError("terms must be an object")
    _reject_unknown(raw, {"loan_amount", "term_years", "repayment_method", "rate_type", "fixed_annual_rate", "variable_annual_rates", "origination_fee", "early_repayments"}, "terms")
    loan = _money(raw.get("loan_amount"), "terms.loan_amount")
    years = raw.get("term_years")
    if loan < 0 or not isinstance(years, int) or years < 1: raise FinancingPlanError("terms.loan_amount must be non-negative and term_years must be a positive integer")
    method = raw.get("repayment_method")
    if method not in {"amortizing", "interest_only"}: raise FinancingPlanError("terms.repayment_method must be amortizing or interest_only")
    rate_type = raw.get("rate_type")
    if rate_type not in {"fixed", "variable"}: raise FinancingPlanError("terms.rate_type must be fixed or variable")
    if rate_type == "fixed":
        if raw.get("variable_annual_rates") is not None: raise FinancingPlanError("terms.variable_annual_rates is only allowed for variable rates")
        rates = [_rate(raw.get("fixed_annual_rate"), "terms.fixed_annual_rate")] * years
    else:
        if raw.get("fixed_annual_rate") is not None: raise FinancingPlanError("terms.fixed_annual_rate is only allowed for fixed rates")
        values = raw.get("variable_annual_rates")
        if not isinstance(values, list) or len(values) != years: raise FinancingPlanError("terms.variable_annual_rates must declare one rate for each term year")
        rates = [_rate(value, f"terms.variable_annual_rates[{index}]") for index, value in enumerate(values)]
    if any(rate < 0 for rate in rates): raise FinancingPlanError("declared annual rates must be non-negative")
    repayments = _early_repayments(raw.get("early_repayments", []), years)
    return {"loan_amount": loan, "term_years": years, "repayment_method": method, "rate_type": rate_type, "annual_rates": rates,
            "origination_fee": _money(raw.get("origination_fee", "0"), "terms.origination_fee"), "early_repayments": repayments}


def _asset_cash_flow(raw: Any, gaps: list[dict[str, Any]]) -> dict[str, Decimal | None]:
    if not isinstance(raw, dict): raise FinancingPlanError("asset_cash_flow must be an object")
    _reject_unknown(raw, {"annual_free_cash_flow", "annual_net_operating_income"}, "asset_cash_flow")
    free_cash_flow = _money(raw.get("annual_free_cash_flow"), "asset_cash_flow.annual_free_cash_flow")
    noi = raw.get("annual_net_operating_income")
    if noi is None:
        _gap(gaps, "missing_noi_for_dscr", "Annual net operating income is required to calculate DSCR.")
        parsed_noi = None
    else: parsed_noi = _money(noi, "asset_cash_flow.annual_net_operating_income")
    return {"annual_free_cash_flow": free_cash_flow, "annual_net_operating_income": parsed_noi}


def _early_repayments(raw: Any, years: int) -> dict[int, tuple[Decimal, Decimal]]:
    if not isinstance(raw, list): raise FinancingPlanError("terms.early_repayments must be a list")
    result: dict[int, tuple[Decimal, Decimal]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict): raise FinancingPlanError(f"terms.early_repayments[{index}] must be an object")
        _reject_unknown(item, {"year", "principal_amount", "fee_amount"}, f"terms.early_repayments[{index}]")
        year = item.get("year")
        if not isinstance(year, int) or not 1 <= year <= years or year in result: raise FinancingPlanError("early repayment years must be unique values within the term")
        principal = _money(item.get("principal_amount"), f"terms.early_repayments[{index}].principal_amount")
        fee = _money(item.get("fee_amount", "0"), f"terms.early_repayments[{index}].fee_amount")
        if principal <= 0 or fee < 0: raise FinancingPlanError("early repayment principal must be positive and fee non-negative")
        result[year] = (principal, fee)
    return result


def _schedule(terms: dict[str, Any]) -> list[dict[str, Decimal | int]]:
    remaining = terms["loan_amount"]; schedule = []
    for year, annual_rate in enumerate(terms["annual_rates"], start=1):
        opening = remaining; interest = opening * annual_rate
        years_left = terms["term_years"] - year + 1
        if terms["repayment_method"] == "amortizing":
            payment = _annuity_payment(opening, annual_rate, years_left)
            principal = min(opening, payment - interest)
        else:
            principal = opening if year == terms["term_years"] else Decimal("0")
        remaining = opening - principal
        early_principal, early_fee = terms["early_repayments"].get(year, (Decimal("0"), Decimal("0")))
        if early_principal > remaining: raise FinancingPlanError(f"early repayment in year {year} exceeds remaining debt")
        remaining -= early_principal
        debt_service = interest + principal + early_principal + early_fee
        schedule.append({"year": year, "opening_debt": opening, "interest": interest, "principal": principal,
                         "early_repayment_principal": early_principal, "early_repayment_fee": early_fee,
                         "debt_service": debt_service, "remaining_debt": remaining})
        if remaining == 0: break
    return schedule


def _annuity_payment(balance: Decimal, annual_rate: Decimal, years: int) -> Decimal:
    if annual_rate == 0: return balance / Decimal(years)
    factor = (Decimal("1") + annual_rate) ** years
    return balance * annual_rate * factor / (factor - Decimal("1"))


def _public_terms(terms: dict[str, Any]) -> dict[str, Any]:
    return {"loan_amount": _money_text(terms["loan_amount"]), "term_years": terms["term_years"], "repayment_method": terms["repayment_method"], "rate_type": terms["rate_type"], "annual_rates": [_rate_text(rate) for rate in terms["annual_rates"]], "origination_fee": _money_text(terms["origination_fee"]), "early_repayments": [{"year": year, "principal_amount": _money_text(principal), "fee_amount": _money_text(fee)} for year, (principal, fee) in sorted(terms["early_repayments"].items())]}


def _public_asset(asset: dict[str, Decimal | None]) -> dict[str, str | None]:
    return {key: _money_text(value) if value is not None else None for key, value in asset.items()}


def _read_json(path: Path) -> dict[str, Any]:
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc: raise FinancingPlanError(f"Missing financing plan input: {path}") from exc
    except json.JSONDecodeError as exc: raise FinancingPlanError(f"Invalid JSON in financing plan input {path}: {exc}") from exc
    if not isinstance(data, dict): raise FinancingPlanError("Financing plan input must contain a JSON object")
    return data


def _declared_gaps(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""): return []
    if not isinstance(value, list) or not all(isinstance(item, dict) and item.get("code") for item in value): raise FinancingPlanError("data_gaps must be a list of objects with code")
    return list(value)
def _gap(gaps: list[dict[str, Any]], code: str, message: str) -> None:
    if not any(item.get("code") == code for item in gaps): gaps.append({"code": code, "message": message})
def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip(): raise FinancingPlanError(f"{label} is required")
    return value
def _decimal(value: Any, label: str) -> Decimal:
    try: result = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc: raise FinancingPlanError(f"{label} must be a decimal") from exc
    if not result.is_finite(): raise FinancingPlanError(f"{label} must be a finite decimal")
    return result
def _money(value: Any, label: str) -> Decimal: return _decimal(value, label)
def _rate(value: Any, label: str) -> Decimal: return _decimal(value, label)
def _money_text(value: Decimal) -> str: return str(value.quantize(CENT, rounding=ROUND_HALF_UP))
def _rate_text(value: Decimal) -> str: return str(value.quantize(RATE, rounding=ROUND_HALF_UP))
def _reject_unknown(data: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown: raise FinancingPlanError(f"{label} has unknown fields: {', '.join(unknown)}")
def _hash(value: dict[str, Any]) -> str: return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
