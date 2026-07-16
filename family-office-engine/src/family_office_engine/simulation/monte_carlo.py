import json
import random
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "monte-carlo/v1"
DEFAULT_END_AGE = 95
DEFAULT_SIMULATIONS = 1000
DEFAULT_SEED = 20260711


class MonteCarloSimulationError(ValueError):
    pass


def simulate_monte_carlo(
    net_worth_snapshot_path: Path,
    assumptions_snapshot_path: Path,
    output_path: Path,
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

    result: dict[str, Any] | None = None
    if net_worth is not None and assumptions is not None:
        result = simulate_monte_carlo_result(
            net_worth,
            assumptions,
            data_gaps,
            simulations,
            seed,
            end_age,
        )

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "MonteCarloSimulationSnapshot",
        "status": "complete" if result is not None else "blocked_missing_inputs",
        "sources": sources,
        "simulations": simulations,
        "seed": seed,
        "end_age": end_age,
        "result": result,
        "data_gaps": data_gaps,
        "notes": "Deterministic Monte Carlo planning simulation. No tax, pension or financial advice.",
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise MonteCarloSimulationError(f"Cannot write Monte Carlo simulation: {output_path}") from exc
    return snapshot


def simulate_monte_carlo_result(
    net_worth: dict[str, Any],
    assumptions_snapshot: dict[str, Any],
    data_gaps: list[str],
    simulations: int = DEFAULT_SIMULATIONS,
    seed: int = DEFAULT_SEED,
    end_age: int = DEFAULT_END_AGE,
) -> dict[str, Any] | None:
    inputs = _monte_carlo_inputs(net_worth, assumptions_snapshot, data_gaps)
    if inputs is None:
        return None
    return _run_simulation(inputs, simulations, seed, end_age)


def _monte_carlo_inputs(
    net_worth: dict[str, Any],
    assumptions_snapshot: dict[str, Any],
    data_gaps: list[str],
) -> dict[str, Any] | None:
    required = {
        "current_age": ("assumptions", "personal", "current_age"),
        "target_retirement_age": ("assumptions", "personal", "target_retirement_age"),
        "expenses": ("assumptions", "cashflow", "family_expenses_yearly"),
        "net_salary_monthly": ("assumptions", "cashflow", "net_salary_monthly"),
        "salary_months": ("assumptions", "cashflow", "salary_months"),
        "nominal_return": ("assumptions", "returns", "nominal_return"),
        "nominal_volatility": ("assumptions", "returns", "nominal_volatility"),
        "net_worth": ("totals", "net_worth"),
    }
    values: dict[str, Any] = {}
    for key, path in required.items():
        source = assumptions_snapshot if key != "net_worth" else net_worth
        try:
            values[key] = _nested(source, path)
        except MonteCarloSimulationError:
            data_gaps.append(f"Missing Monte Carlo input: {'.'.join(path)}")
    if data_gaps:
        return None

    self_salary_yearly = _decimal(values["net_salary_monthly"], "net_salary_monthly") * _decimal(
        values["salary_months"],
        "salary_months",
    )
    spouse_salary_yearly = _optional_decimal(
        assumptions_snapshot,
        ("assumptions", "cashflow", "spouse_net_salary_monthly"),
        "spouse_net_salary_monthly",
    ) * _optional_decimal(
        assumptions_snapshot,
        ("assumptions", "cashflow", "spouse_salary_months"),
        "spouse_salary_months",
    )
    rental_income_yearly = _optional_decimal(
        assumptions_snapshot,
        ("assumptions", "cashflow", "rental_income_monthly_net"),
        "rental_income_monthly_net",
    ) * Decimal("12")
    expenses = _decimal(values["expenses"], "family_expenses_yearly")
    retirement_income = _optional_decimal(
        assumptions_snapshot,
        ("assumptions", "cashflow", "retirement_income_yearly"),
        "retirement_income_yearly",
    )

    return {
        "current_age": int(values["current_age"]),
        "target_retirement_age": int(values["target_retirement_age"]),
        "expenses": expenses,
        "self_salary_yearly": self_salary_yearly,
        "spouse_salary_yearly": spouse_salary_yearly,
        "rental_income_yearly": rental_income_yearly,
        "pre_retirement_income_yearly": self_salary_yearly + spouse_salary_yearly + rental_income_yearly,
        "retirement_income": retirement_income,
        "post_retirement_income_yearly": retirement_income + rental_income_yearly,
        "nominal_return": float(_decimal(values["nominal_return"], "nominal_return")),
        "nominal_volatility": float(_decimal(values["nominal_volatility"], "nominal_volatility")),
        "net_worth": _decimal(values["net_worth"], "net_worth"),
    }


def _run_simulation(
    inputs: dict[str, Any],
    simulations: int,
    seed: int,
    end_age: int,
) -> dict[str, Any]:
    if simulations <= 0:
        raise MonteCarloSimulationError("simulations must be greater than zero")
    rng = random.Random(seed)
    final_balances: list[Decimal] = []
    ruin_count = 0

    for _ in range(simulations):
        balance = Decimal(inputs["net_worth"])
        depleted = False
        for age in range(inputs["current_age"], end_age + 1):
            retired = age >= inputs["target_retirement_age"]
            if retired:
                balance -= inputs["expenses"]
                balance += inputs["post_retirement_income_yearly"]
            else:
                balance += inputs["pre_retirement_income_yearly"] - inputs["expenses"]
            yearly_return = Decimal(str(rng.gauss(inputs["nominal_return"], inputs["nominal_volatility"])))
            balance *= Decimal("1") + yearly_return
            if balance < 0:
                depleted = True
        final_balances.append(balance)
        if depleted:
            ruin_count += 1

    sorted_balances = sorted(final_balances)
    return {
        "target_retirement_age": inputs["target_retirement_age"],
        "family_expenses_yearly": _money(inputs["expenses"]),
        "self_salary_yearly": _money(inputs["self_salary_yearly"]),
        "spouse_salary_yearly": _money(inputs["spouse_salary_yearly"]),
        "rental_income_yearly": _money(inputs["rental_income_yearly"]),
        "pre_retirement_income_yearly": _money(inputs["pre_retirement_income_yearly"]),
        "pre_retirement_net_cashflow_yearly": _money(
            inputs["pre_retirement_income_yearly"] - inputs["expenses"]
        ),
        "retirement_income_yearly": _money(inputs["retirement_income"]),
        "post_retirement_income_yearly": _money(inputs["post_retirement_income_yearly"]),
        "net_retirement_drawdown_yearly": _money(inputs["expenses"] - inputs["post_retirement_income_yearly"]),
        "success_rate": _ratio(simulations - ruin_count, simulations),
        "final_balance_p05": _money(_percentile(sorted_balances, Decimal("0.05"))),
        "final_balance_p50": _money(_percentile(sorted_balances, Decimal("0.50"))),
        "final_balance_p95": _money(_percentile(sorted_balances, Decimal("0.95"))),
    }


def _read_optional_json(path: Path, data_gaps: list[str], label: str) -> dict[str, Any] | None:
    if not path.exists():
        data_gaps.append(f"Missing {label} snapshot: {path}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MonteCarloSimulationError(f"Cannot read {label} snapshot: {path}") from exc
    if not isinstance(data, dict):
        raise MonteCarloSimulationError(f"{label} snapshot must be a JSON object: {path}")
    return data


def _nested(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            raise MonteCarloSimulationError(f"Missing required field: {'.'.join(path)}")
        current = current[part]
    return current


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise MonteCarloSimulationError(f"Invalid decimal for {field_name}: {value}") from exc


def _optional_decimal(data: dict[str, Any], path: tuple[str, ...], field_name: str) -> Decimal:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return Decimal("0")
        current = current[part]
    if current is None:
        return Decimal("0")
    return _decimal(current, field_name)


def _percentile(sorted_values: list[Decimal], percentile: Decimal) -> Decimal:
    if not sorted_values:
        raise MonteCarloSimulationError("Cannot calculate percentile for empty results")
    index = int((Decimal(len(sorted_values) - 1) * percentile).to_integral_value(rounding="ROUND_HALF_UP"))
    return sorted_values[index]


def _ratio(numerator: int, denominator: int) -> str:
    return str((Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0001")))


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))
