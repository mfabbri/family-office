import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "retirement-simulation/v1"
DEFAULT_TARGET_AGES = (62, 64, 67)
DEFAULT_END_AGE = 95


class RetirementSimulationError(ValueError):
    pass


def simulate_retirement(
    net_worth_snapshot_path: Path,
    assumptions_snapshot_path: Path,
    tax_events_snapshot_path: Path | None,
    output_path: Path,
    target_ages: tuple[int, ...] = DEFAULT_TARGET_AGES,
    end_age: int = DEFAULT_END_AGE,
    pension_income_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    data_gaps: list[str] = []
    sources: dict[str, str] = {}

    net_worth = _read_optional_json(net_worth_snapshot_path, data_gaps, "net worth")
    assumptions = _read_optional_json(assumptions_snapshot_path, data_gaps, "manual assumptions")
    tax_events = (
        _read_optional_json(tax_events_snapshot_path, data_gaps, "tax events")
        if tax_events_snapshot_path is not None
        else None
    )
    pension_income = (
        _read_optional_json(pension_income_snapshot_path, data_gaps, "pension income")
        if pension_income_snapshot_path is not None
        else None
    )

    if net_worth is not None:
        sources["net_worth"] = str(net_worth_snapshot_path)
    if assumptions is not None:
        sources["manual_assumptions"] = str(assumptions_snapshot_path)
    if tax_events is not None and tax_events_snapshot_path is not None:
        sources["tax_events"] = str(tax_events_snapshot_path)
    if pension_income is not None and pension_income_snapshot_path is not None:
        sources["pension_income"] = str(pension_income_snapshot_path)

    scenarios: list[dict[str, Any]] = []
    if net_worth is not None and assumptions is not None:
        scenarios = _simulate_scenarios(net_worth, assumptions, target_ages, end_age, pension_income)

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "RetirementSimulationSnapshot",
        "status": "complete" if scenarios else "blocked_missing_inputs",
        "sources": sources,
        "target_ages": list(target_ages),
        "end_age": end_age,
        "scenarios": scenarios,
        "data_gaps": data_gaps,
        "notes": "Deterministic planning simulation. No tax or financial advice.",
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise RetirementSimulationError(f"Cannot write retirement simulation: {output_path}") from exc
    return snapshot


def _simulate_scenarios(
    net_worth: dict[str, Any],
    assumptions_snapshot: dict[str, Any],
    target_ages: tuple[int, ...],
    end_age: int,
    pension_income_snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    current_age = int(_nested(assumptions_snapshot, ("assumptions", "personal", "current_age")))
    expenses = _decimal(_nested(assumptions_snapshot, ("assumptions", "cashflow", "family_expenses_yearly")), "expenses")
    nominal_return = _decimal(_nested(assumptions_snapshot, ("assumptions", "returns", "nominal_return")), "nominal_return")
    starting_net_worth = _decimal(_nested(net_worth, ("totals", "net_worth")), "net_worth")
    pension_income_gross = _gross_annual_recurring_pension_income(pension_income_snapshot)

    scenarios: list[dict[str, Any]] = []
    for target_age in target_ages:
        if target_age < current_age:
            scenarios.append(
                {
                    "target_retirement_age": target_age,
                    "status": "invalid_target_before_current_age",
                    "cashflows": [],
                }
            )
            continue
        balance = starting_net_worth
        cashflows: list[dict[str, str | int]] = []
        for age in range(current_age, end_age + 1):
            retired = age >= target_age
            pension_offset = pension_income_gross if retired else Decimal("0.00")
            withdrawal = max(expenses - pension_offset, Decimal("0.00")) if retired else Decimal("0.00")
            start_balance = balance
            balance = (balance - withdrawal) * (Decimal("1") + nominal_return)
            cashflows.append(
                {
                    "age": age,
                    "retired": str(retired).lower(),
                    "start_balance": _money(start_balance),
                    "pension_income_gross": _money(pension_offset),
                    "withdrawal": _money(withdrawal),
                    "end_balance": _money(balance),
                }
            )
        scenarios.append(
            {
                "target_retirement_age": target_age,
                "status": "complete",
                "cashflows": cashflows,
                "final_balance": _money(balance),
            }
        )
    return scenarios


def _gross_annual_recurring_pension_income(snapshot: dict[str, Any] | None) -> Decimal:
    if snapshot is None:
        return Decimal("0.00")
    if snapshot.get("schema_version") != "pension-income/v1":
        raise RetirementSimulationError(f"Unsupported pension income schema: {snapshot.get('schema_version')}")
    summary = snapshot.get("summary") if isinstance(snapshot.get("summary"), dict) else {}
    total = summary.get("gross_annual_recurring_total")
    if total in (None, ""):
        return Decimal("0.00")
    return _decimal(total, "gross_annual_recurring_total")


def _read_optional_json(path: Path | None, data_gaps: list[str], label: str) -> dict[str, Any] | None:
    if path is None or not path.exists():
        data_gaps.append(f"Missing {label} snapshot: {path}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RetirementSimulationError(f"Cannot read {label} snapshot: {path}") from exc
    if not isinstance(data, dict):
        raise RetirementSimulationError(f"{label} snapshot must be a JSON object: {path}")
    return data


def _nested(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            raise RetirementSimulationError(f"Missing required field: {'.'.join(path)}")
        current = current[part]
    return current


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise RetirementSimulationError(f"Invalid decimal for {field_name}: {value}") from exc


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))
