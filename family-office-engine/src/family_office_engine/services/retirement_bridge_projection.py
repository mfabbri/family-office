"""Deterministic retirement-bridge projections from explicitly declared assumptions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

SCHEMA_VERSION = "retirement-bridge-projection/v1"
WORK_SCENARIOS = (("work_100", Decimal("1.00")), ("work_60", Decimal("0.60")), ("work_0", Decimal("0.00")))
CENT = Decimal("0.01")


class RetirementBridgeProjectionError(ValueError):
    pass


def build_retirement_bridge_projection(data: dict[str, Any]) -> dict[str, Any]:
    """Project monthly assets for 100%, 60%, and 0% work under declared assumptions.

    Annual inflation and returns are prorated as simple monthly rates (annual / 12).
    This assumption is stated in each output; tax and statutory pension calculations
    are deliberately outside this first projection slice.
    """
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise RetirementBridgeProjectionError(f"schema_version must be {SCHEMA_VERSION}")
    household_id = data.get("household_id")
    if not isinstance(household_id, str) or not household_id.strip():
        raise RetirementBridgeProjectionError("household_id is required")
    as_of_month = data.get("as_of_month")
    if not isinstance(as_of_month, str) or len(as_of_month) != 7 or as_of_month[4] != "-":
        raise RetirementBridgeProjectionError("as_of_month must use YYYY-MM")
    try:
        datetime.strptime(as_of_month, "%Y-%m")
    except ValueError as exc:
        raise RetirementBridgeProjectionError("as_of_month must be a valid calendar month") from exc
    months = data.get("months")
    if not isinstance(months, int) or isinstance(months, bool) or not 1 <= months <= 600:
        raise RetirementBridgeProjectionError("months must be an integer from 1 through 600")

    assumptions = data.get("assumptions")
    if not isinstance(assumptions, dict):
        raise RetirementBridgeProjectionError("assumptions object is required")
    opening = _decimal(assumptions, "opening_available_assets")
    spending = _decimal(assumptions, "monthly_household_spending")
    full_time_income = _decimal(assumptions, "monthly_full_time_net_income")
    inflation = _decimal(assumptions, "annual_inflation_rate")
    annual_return = _decimal(assumptions, "annual_return_rate")
    provenance = assumptions.get("provenance")
    if not isinstance(provenance, str) or not provenance.strip():
        raise RetirementBridgeProjectionError("assumptions provenance is required")
    if min(opening, spending, full_time_income) < 0:
        raise RetirementBridgeProjectionError("assets, spending and income must be non-negative")
    if not Decimal("-1") < inflation < Decimal("1") or not Decimal("-1") < annual_return < Decimal("1"):
        raise RetirementBridgeProjectionError("annual rates must be between -1 and 1")

    pension = assumptions.get("hypothetical_pension")
    pension_assumption = None
    if pension is not None:
        if not isinstance(pension, dict) or pension.get("assumption_status") != "scenario_assumption":
            raise RetirementBridgeProjectionError("hypothetical_pension must be tagged scenario_assumption")
        pension_amount = _decimal(pension, "monthly_net_amount")
        start_month = pension.get("start_month")
        if pension_amount < 0 or not isinstance(start_month, int) or isinstance(start_month, bool) or start_month < 1:
            raise RetirementBridgeProjectionError("hypothetical pension requires non-negative amount and start_month >= 1")
        if not isinstance(pension.get("provenance"), str) or not pension["provenance"].strip():
            raise RetirementBridgeProjectionError("hypothetical pension provenance is required")
        pension_assumption = {
            "monthly_net_amount": _money(pension_amount),
            "start_month": start_month,
            "assumption_status": "scenario_assumption",
            "provenance": pension["provenance"],
        }

    scenario_results = []
    for scenario_id, fte in WORK_SCENARIOS:
        balance = opening
        cashflows = []
        unfunded_need = Decimal("0")
        for month_index in range(1, months + 1):
            monthly_spending = spending * (Decimal("1") + inflation / Decimal("12")) ** (month_index - 1)
            work_income = full_time_income * fte
            hypothetical_pension = (
                Decimal(pension_assumption["monthly_net_amount"])
                if pension_assumption and month_index >= pension_assumption["start_month"]
                else Decimal("0")
            )
            month_open = balance
            investment_growth = month_open * annual_return / Decimal("12")
            available_before_cashflow = month_open + investment_growth
            net_cashflow = work_income + hypothetical_pension - monthly_spending
            requested_withdrawal = max(Decimal("0"), -net_cashflow)
            actual_withdrawal = min(available_before_cashflow, requested_withdrawal)
            balance_before_floor = available_before_cashflow + net_cashflow
            shortfall = max(Decimal("0"), -balance_before_floor)
            balance = max(Decimal("0"), balance_before_floor)
            if fte == 0 and work_income == 0:
                unfunded_need += max(Decimal("0"), monthly_spending - hypothetical_pension)
            cashflows.append({
                "month_index": month_index,
                "opening_available_assets": _money(month_open),
                "net_work_income": _money(work_income),
                "hypothetical_pension_net_income": _money(hypothetical_pension),
                "net_income_total": _money(work_income + hypothetical_pension),
                "monthly_expenses": _money(monthly_spending),
                "net_cashflow": _money(net_cashflow),
                "requested_asset_withdrawal": _money(requested_withdrawal),
                "asset_withdrawal": _money(actual_withdrawal),
                "investment_growth": _money(investment_growth),
                "shortfall": _money(shortfall),
                "closing_available_assets": _money(balance),
            })
        scenario_results.append({
            "scenario_id": scenario_id,
            "work_fraction": str(fte),
            "status": "scenario_projection",
            "cashflows": cashflows,
            "summary": {
                "opening_available_assets": _money(opening),
                "ending_available_assets": _money(balance),
                "total_no_work_funding_need": _money(unfunded_need),
                "total_asset_withdrawal": _money(sum((Decimal(row["asset_withdrawal"]) for row in cashflows), Decimal("0"))),
                "total_net_cashflow": _money(sum((Decimal(row["net_cashflow"]) for row in cashflows), Decimal("0"))),
                "total_shortfall": _money(sum((Decimal(row["shortfall"]) for row in cashflows), Decimal("0"))),
            },
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "RetirementBridgeProjection",
        "status": "scenario_projection",
        "input": {"household_id": household_id, "as_of_month": as_of_month, "months": months},
        "assumptions": {
            "opening_available_assets": _money(opening),
            "monthly_household_spending": _money(spending),
            "monthly_full_time_net_income": _money(full_time_income),
            "income_basis": "net household assumption supplied by the user; no tax calculation performed",
            "work_income_scaling_method": "linear scaling of declared net full-time income by work fraction",
            "annual_inflation_rate": str(inflation),
            "annual_return_rate": str(annual_return),
            "monthly_rate_method": "simple annual rate divided by 12",
            "provenance": provenance,
            "hypothetical_pension": pension_assumption,
        },
        "scenarios": scenario_results,
        "pension_entitlement": {
            "status": "not_assessed",
            "verified_monthly_amount": None,
            "verified_start_month": None,
        },
        "data_gaps": [{
            "code": "future_pension_entitlement_not_verified",
            "message": "Future pension assumptions in this projection are not verified entitlement facts.",
        }, {
            "code": "tax_and_other_household_flows_not_modeled",
            "message": "Taxes and household income/expense streams beyond the declared inputs are outside this projection slice.",
        }],
        "notes": "Synthetic/declared assumptions only. No statutory tax, pension entitlement, recognition, effective date or payment is calculated.",
    }


def _decimal(source: dict[str, Any], key: str) -> Decimal:
    try:
        value = Decimal(str(source[key]))
    except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
        raise RetirementBridgeProjectionError(f"{key} must be a finite decimal") from exc
    if not value.is_finite():
        raise RetirementBridgeProjectionError(f"{key} must be a finite decimal")
    return value


def _money(value: Decimal) -> str:
    return str(value.quantize(CENT))
