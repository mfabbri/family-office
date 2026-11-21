"""Monthly cash-flow and return-sequence scenarios from declared assumptions."""

from __future__ import annotations

import random
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from typing import Any

SCHEMA_VERSION = "work-transition-simulation/v1"
BUCKET_ORDER = ("emergency_reserve", "short_term", "medium_term", "long_term", "restricted")
SPENDABLE = set(BUCKET_ORDER[:-1])
CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("1000000000000.00")
CALCULATION_PRECISION = 256


class WorkTransitionSimulationError(ValueError):
    pass


def build_work_transition_simulation(data: dict[str, Any]) -> dict[str, Any]:
    """Return one deterministic baseline and optional seeded path-permutation stress.

    The stress distribution is conditional on the user-supplied return path; it is
    not a forecast or a probability of a real-world outcome.
    """
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise WorkTransitionSimulationError(f"schema_version must be {SCHEMA_VERSION}")
    question = data.get("decision_question")
    if not isinstance(question, str) or not question.strip():
        raise WorkTransitionSimulationError("decision_question is required")
    months = data.get("months")
    if not isinstance(months, int) or isinstance(months, bool) or not 1 <= months <= 600:
        raise WorkTransitionSimulationError("months must be an integer from 1 through 600")
    assumptions = data.get("assumptions")
    if not isinstance(assumptions, dict):
        raise WorkTransitionSimulationError("assumptions object is required")
    provenance = assumptions.get("provenance")
    if not isinstance(provenance, str) or not provenance.strip():
        raise WorkTransitionSimulationError("assumptions provenance is required")
    inflation = _decimal(assumptions, "annual_inflation_rate")
    base_return = _decimal(assumptions, "annual_return_rate")
    monthly_income = _currency(assumptions, "monthly_net_income")
    monthly_spending = _currency(assumptions, "monthly_household_spending")
    monthly_tax = _currency(assumptions, "monthly_declared_tax")
    monthly_cost = _currency(assumptions, "monthly_declared_costs")
    emergency_floor_months = _decimal(assumptions, "emergency_floor_months", default="0")
    if monthly_income < 0 or monthly_spending < 0 or monthly_tax < 0 or monthly_cost < 0 or emergency_floor_months < 0:
        raise WorkTransitionSimulationError("income, spending, declared taxes/costs and reserve floor must be non-negative")
    if not Decimal("-1") < inflation < Decimal("1") or not Decimal("-1") < base_return < Decimal("1"):
        raise WorkTransitionSimulationError("annual inflation and return rates must be between -1 and 1")

    raw_buckets = assumptions.get("buckets")
    if not isinstance(raw_buckets, list) or not raw_buckets:
        raise WorkTransitionSimulationError("buckets must be a non-empty array")
    balances: dict[str, Decimal] = {}
    for item in raw_buckets:
        if not isinstance(item, dict) or item.get("bucket") not in BUCKET_ORDER:
            raise WorkTransitionSimulationError("each bucket must use a supported liquidity bucket name")
        name = item["bucket"]
        if name in balances:
            raise WorkTransitionSimulationError(f"duplicate bucket: {name}")
        amount = _currency(item, "opening_balance")
        if amount < 0:
            raise WorkTransitionSimulationError("bucket opening balances must be non-negative")
        balances[name] = amount
    draw_order = assumptions.get("draw_order")
    if (not isinstance(draw_order, list) or not draw_order or any(not isinstance(name, str) for name in draw_order)
            or len(set(draw_order)) != len(draw_order)
            or any(name not in SPENDABLE or name not in balances for name in draw_order)):
        raise WorkTransitionSimulationError("draw_order must list unique available spendable buckets")
    if any(name in SPENDABLE and name not in draw_order for name in balances):
        raise WorkTransitionSimulationError("every available spendable bucket must appear in draw_order")

    streams = _income_streams(assumptions.get("income_streams", []), months)
    stress = assumptions.get("stress")
    baseline_path = assumptions.get("deterministic_monthly_return_path")
    if baseline_path is not None:
        if not isinstance(baseline_path, list) or len(baseline_path) != months:
            raise WorkTransitionSimulationError("deterministic_monthly_return_path must contain one return per month")
        baseline_path = [_decimal_value(value, "deterministic_monthly_return_path") for value in baseline_path]
        if any(not Decimal("-1") < value <= Decimal("1") for value in baseline_path):
            raise WorkTransitionSimulationError("deterministic monthly returns must be greater than -1 and at most 1")
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        baseline = _run_path(balances, months, base_return if baseline_path is None else None, baseline_path, draw_order, assumptions, streams,
                             inflation, monthly_income, monthly_spending, monthly_tax, monthly_cost,
                             emergency_floor_months)
    stress_result = None
    if stress is not None:
        if not isinstance(stress, dict):
            raise WorkTransitionSimulationError("stress must be an object")
        raw_path = stress.get("monthly_return_path")
        if not isinstance(raw_path, list) or len(raw_path) != months:
            raise WorkTransitionSimulationError("stress monthly_return_path must contain one return per month")
        return_path = [_decimal_value(value, "monthly_return_path") for value in raw_path]
        if any(not Decimal("-1") < value <= Decimal("1") for value in return_path):
            raise WorkTransitionSimulationError("stress monthly returns must be greater than -1 and at most 1")
        trials = stress.get("trials")
        seed = stress.get("seed")
        if not isinstance(trials, int) or isinstance(trials, bool) or not 1 <= trials <= 10000:
            raise WorkTransitionSimulationError("stress trials must be an integer from 1 through 10000")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise WorkTransitionSimulationError("stress seed must be an integer")
        rng = random.Random(seed)
        terminal = []
        successful = 0
        reserve_breach_trials = 0
        with localcontext() as context:
            context.prec = CALCULATION_PRECISION
            for _ in range(trials):
                shuffled = list(return_path)
                rng.shuffle(shuffled)
                result = _run_path(balances, months, None, shuffled, draw_order, assumptions, streams,
                                   inflation, monthly_income, monthly_spending, monthly_tax, monthly_cost,
                                   emergency_floor_months, include_monthly=False)
                terminal.append(Decimal(result["summary"]["terminal_wealth"]))
                successful += Decimal(result["summary"]["total_shortfall"]) == 0
                reserve_breach_trials += result["summary"]["reserve_breach_months"] > 0
        terminal.sort()
        stress_result = {
            "status": "scenario_projection",
            "model": "seeded_permutation_of_declared_common_monthly_return_path",
            "seed": seed,
            "trials": trials,
            "declared_monthly_return_path": [str(value) for value in return_path],
            "success_definition": "no monthly spending shortfall in the simulated path",
            "success_probability_conditional_on_model": _ratio(successful, trials),
            "reserve_breach_trials": reserve_breach_trials,
            "terminal_wealth": {f"p{pct}": _money(_percentile(terminal, Decimal(pct) / 100)) for pct in (5, 50, 95)},
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "WorkTransitionSimulation",
        "status": "scenario_projection",
        "decision_question": question,
        "assumptions": {
            "provenance": provenance,
            "months": months,
            "annual_inflation_rate": str(inflation),
            "annual_return_rate": str(base_return),
            "monthly_net_income": _money(monthly_income),
            "monthly_household_spending": _money(monthly_spending),
            "monthly_declared_tax": _money(monthly_tax),
            "monthly_declared_costs": _money(monthly_cost),
            "emergency_floor_months": str(emergency_floor_months),
            "reserve_floor_policy": "advisory_breach_metric; withdrawals are not blocked by the floor",
            "draw_order": draw_order,
            "income_streams": streams,
            "restricted_assets_spendable": False,
        },
        "deterministic_baseline": baseline,
        "stress": stress_result,
        "pension_entitlement": {"status": "not_assessed", "verified_monthly_amount": None, "verified_start_month": None},
        "data_gaps": [
            {"code": "pension_entitlement_not_assessed", "message": "Scenario income streams are assumptions, not verified pension entitlement."},
            {"code": "stress_frequency_is_model_conditional", "message": "Stress frequencies describe only permutations of the declared return path."},
            {"code": "taxes_are_declared_inputs", "message": "Declared tax cashflows are user inputs; no tax calculation or determination is performed."},
        ],
        "notes": "Scenario projections from declared assumptions only; not a forecast, tax calculation, pension determination or recommendation.",
    }


def _run_path(opening: dict[str, Decimal], months: int, annual_return: Decimal | None,
              return_path: list[Decimal] | None, draw_order: list[str], assumptions: dict[str, Any],
              streams: list[dict[str, Any]], inflation: Decimal, income: Decimal, spending: Decimal,
              tax: Decimal, cost: Decimal, floor_months: Decimal, *, include_monthly: bool = True) -> dict[str, Any]:
    balances = dict(opening)
    monthly = []
    cumulative_shortfall = Decimal("0")
    total_withdrawal = Decimal("0")
    total_tax = Decimal("0")
    total_cost = Decimal("0")
    first_depleted = first_shortfall = None
    breach_months = 0
    for index in range(1, months + 1):
        rate = annual_return / 12 if return_path is None else return_path[index - 1]
        opening_total = sum(balances.values(), Decimal("0"))
        growth = Decimal("0")
        for name in balances:
            bucket_open = balances[name]
            bucket_growth = balances[name] * rate
            balances[name] = (balances[name] + bucket_growth).quantize(CENT, rounding=ROUND_HALF_UP)
            growth += balances[name] - bucket_open
        expenses = (spending * (Decimal("1") + inflation / 12) ** (index - 1)).quantize(CENT, rounding=ROUND_HALF_UP)
        stream_income = sum((Decimal(s["monthly_net_amount"]) for s in streams
                             if s["start_month"] <= index <= s["end_month"]), Decimal("0"))
        net_cash = (income + stream_income - expenses - tax - cost).quantize(CENT, rounding=ROUND_HALF_UP)
        requested = max(Decimal("0"), -net_cash)
        withdrawal = min(requested, sum((balances.get(name, Decimal("0")) for name in draw_order), Decimal("0")))
        remaining = withdrawal
        for name in draw_order:
            take = min(remaining, balances[name])
            balances[name] -= take
            remaining -= take
        shortfall = (requested - withdrawal).quantize(CENT, rounding=ROUND_HALF_UP)
        if net_cash > 0 and draw_order:
            balances[draw_order[0]] = (balances[draw_order[0]] + net_cash).quantize(CENT, rounding=ROUND_HALF_UP)
        cumulative_shortfall += shortfall
        total_withdrawal += withdrawal
        total_tax += tax
        total_cost += cost
        if shortfall > 0 and first_shortfall is None:
            first_shortfall = index
        spendable_total = sum((balances.get(name, Decimal("0")) for name in SPENDABLE), Decimal("0"))
        if spendable_total == 0 and first_depleted is None:
            first_depleted = index
        emergency = balances.get("emergency_reserve", Decimal("0"))
        floor = floor_months * expenses
        reserve_breach = emergency < floor
        if reserve_breach:
            breach_months += 1
        if include_monthly:
            monthly.append({
            "month_index": index, "opening_assets": _money(opening_total), "return_rate": str(rate),
            "investment_growth": _money(growth), "net_income": _money(income + stream_income),
            "inflation_adjusted_spending": _money(expenses), "declared_tax": _money(tax),
            "declared_costs": _money(cost), "asset_withdrawal": _money(withdrawal),
            "shortfall": _money(shortfall), "closing_buckets": {k: _money(v) for k, v in balances.items()},
            "reserve_months": None if expenses == 0 else str((emergency / expenses).quantize(Decimal("0.01"))),
            "reserve_breach": reserve_breach,
            })
    terminal = sum(balances.values(), Decimal("0"))
    return {"status": "scenario_projection", "months": monthly, "summary": {
        "terminal_wealth": _money(terminal), "terminal_spendable_assets": _money(sum((balances.get(k, Decimal("0")) for k in SPENDABLE), Decimal("0"))),
        "total_withdrawal": _money(total_withdrawal), "total_shortfall": _money(cumulative_shortfall),
        "total_declared_tax": _money(total_tax), "total_declared_costs": _money(total_cost),
        "first_depleted_month": first_depleted, "first_shortfall_month": first_shortfall,
        "reserve_breach_months": breach_months, "terminal_buckets": {k: _money(v) for k, v in balances.items()},
    }}


def _income_streams(raw: Any, months: int) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise WorkTransitionSimulationError("income_streams must be an array")
    result = []
    for stream in raw:
        if not isinstance(stream, dict) or stream.get("assumption_status") != "scenario_assumption":
            raise WorkTransitionSimulationError("each income stream must be tagged scenario_assumption")
        amount = _currency(stream, "monthly_net_amount")
        start, end = stream.get("start_month"), stream.get("end_month")
        if amount < 0 or not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool) or not 1 <= start <= end <= months:
            raise WorkTransitionSimulationError("income stream amount and inclusive month range are invalid")
        if not isinstance(stream.get("provenance"), str) or not stream["provenance"].strip():
            raise WorkTransitionSimulationError("income stream provenance is required")
        result.append({"monthly_net_amount": _money(amount), "start_month": start, "end_month": end,
                       "assumption_status": "scenario_assumption", "provenance": stream["provenance"]})
    return result


def _decimal(source: dict[str, Any], key: str, *, default: str | None = None) -> Decimal:
    if key not in source and default is not None:
        return Decimal(default)
    return _decimal_value(source.get(key), key)


def _currency(source: dict[str, Any], key: str) -> Decimal:
    value = _decimal(source, key)
    if value < 0:
        raise WorkTransitionSimulationError(f"{key} must be non-negative")
    if abs(value) > MAX_AMOUNT:
        raise WorkTransitionSimulationError(f"{key} exceeds the supported amount bound")
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _decimal_value(value: Any, label: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise WorkTransitionSimulationError(f"{label} must be a finite decimal") from exc
    if not parsed.is_finite():
        raise WorkTransitionSimulationError(f"{label} must be a finite decimal")
    return parsed


def _money(value: Decimal) -> str:
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _percentile(values: list[Decimal], percentile: Decimal) -> Decimal:
    index = int((Decimal(len(values) - 1) * percentile).to_integral_value(rounding=ROUND_HALF_UP))
    return values[index]


def _ratio(numerator: int, denominator: int) -> str:
    return str((Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0001")))
