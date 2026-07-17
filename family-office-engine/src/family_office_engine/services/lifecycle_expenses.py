import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "lifecycle-expenses/v1"
INPUT_RECORD_TYPE = "LifecycleExpensePlan"
SNAPSHOT_RECORD_TYPE = "LifecycleExpensesSnapshot"
CENT = Decimal("0.01")
ALLOWED_FREQUENCIES = {"annual", "one_time"}
ALLOWED_OWNERS = {"household", "person"}


class LifecycleExpensesError(ValueError):
    pass


def build_lifecycle_expenses(
    input_path: Path,
    output_path: Path,
    *,
    household_snapshot_path: Path | None = None,
    timeline_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    plan = load_lifecycle_expense_plan(input_path)
    household_snapshot = _load_optional_snapshot(household_snapshot_path, "household", "household-facts/v1")
    timeline_snapshot = _load_optional_snapshot(timeline_snapshot_path, "timeline", "timeline-events/v1")
    person_ids = _person_ids_from_household(household_snapshot)
    event_years = _event_years_from_timeline(timeline_snapshot)

    data_gaps: list[dict[str, Any]] = []
    entries = _validate_entries(plan, person_ids, event_years, data_gaps)
    yearly_cashflow = _build_yearly_cashflow(entries)
    summary = _summary(entries, yearly_cashflow, data_gaps)
    status = "complete" if entries and not data_gaps else "partial" if entries else "blocked_missing_inputs"

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": status,
        "source": {
            "type": "lifecycle-expense-plan-json",
            "path": str(input_path),
        },
        "household": {
            "household_id": plan.get("household_id"),
            "as_of_date": plan.get("as_of_date"),
            "household_snapshot_path": str(household_snapshot_path) if household_snapshot_path else None,
            "timeline_snapshot_path": str(timeline_snapshot_path) if timeline_snapshot_path else None,
        },
        "expense_entries": entries,
        "yearly_cashflow": yearly_cashflow,
        "summary": summary,
        "data_gaps": data_gaps,
        "notes": (
            "Lifecycle expenses V1 uses only explicit EUR amounts from the expense plan. It does not estimate "
            "missing household expenses, taxes, health costs, currency conversion or investment returns."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise LifecycleExpensesError(f"Cannot write lifecycle expenses snapshot: {output_path}") from exc
    return snapshot


def load_lifecycle_expense_plan(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LifecycleExpensesError(f"Lifecycle expense plan file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LifecycleExpensesError(f"Invalid JSON in lifecycle expense plan file: {exc}") from exc
    if not isinstance(data, dict):
        raise LifecycleExpensesError("Lifecycle expense plan must contain a JSON object")
    return data


def _load_optional_snapshot(path: Path | None, label: str, expected_schema: str) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LifecycleExpensesError(f"Invalid JSON in {label} snapshot: {exc}") from exc
    if not isinstance(data, dict):
        raise LifecycleExpensesError(f"{label.title()} snapshot must contain a JSON object")
    if data.get("schema_version") != expected_schema:
        raise LifecycleExpensesError(
            f"Unsupported {label} snapshot schema: {data.get('schema_version')}; expected {expected_schema}"
        )
    return data


def _person_ids_from_household(household_snapshot: dict[str, Any] | None) -> set[str] | None:
    if household_snapshot is None:
        return None
    person_ids: set[str] = set()
    for person in household_snapshot.get("persons", []):
        if isinstance(person, dict) and isinstance(person.get("person_id"), str):
            person_ids.add(person["person_id"])
    return person_ids


def _event_years_from_timeline(timeline_snapshot: dict[str, Any] | None) -> dict[str, int]:
    if timeline_snapshot is None:
        return {}
    event_years: dict[str, int] = {}
    for occurrence in timeline_snapshot.get("occurrences", []):
        if not isinstance(occurrence, dict):
            continue
        event_id = occurrence.get("event_id")
        occurrence_date = occurrence.get("occurrence_date")
        if isinstance(event_id, str) and isinstance(occurrence_date, str) and len(occurrence_date) >= 4:
            try:
                event_years.setdefault(event_id, int(occurrence_date[:4]))
            except ValueError:
                continue
    return event_years


def _validate_entries(
    plan: dict[str, Any],
    person_ids: set[str] | None,
    event_years: dict[str, int],
    data_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    errors: list[str] = []
    if plan.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported lifecycle expenses schema: {plan.get('schema_version')}")
    if plan.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported lifecycle expenses record type: {plan.get('record_type')}")
    _required_string(plan, "household_id", errors)
    _required_string(plan, "as_of_date", errors)

    raw_entries = plan.get("expense_entries")
    if not isinstance(raw_entries, list):
        errors.append("expense_entries must be a list")
        raw_entries = []

    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_entry in enumerate(raw_entries):
        if not isinstance(raw_entry, dict):
            errors.append(f"expense_entries[{index}] must be an object")
            continue
        entry = _normalize_entry(raw_entry, index, person_ids, event_years, seen_ids, errors, data_gaps)
        if entry is not None:
            entries.append(entry)

    _validate_declared_gaps(plan.get("data_gaps", []), errors, data_gaps)
    if errors:
        raise LifecycleExpensesError("; ".join(errors))
    return entries


def _normalize_entry(
    raw_entry: dict[str, Any],
    index: int,
    person_ids: set[str] | None,
    event_years: dict[str, int],
    seen_ids: set[str],
    errors: list[str],
    data_gaps: list[dict[str, Any]],
) -> dict[str, Any] | None:
    label = f"expense_entries[{index}]"
    entry_id = _required_string(raw_entry, "entry_id", errors, label)
    if entry_id:
        if entry_id in seen_ids:
            errors.append(f"Duplicate expense entry_id: {entry_id}")
        seen_ids.add(entry_id)
    category = _required_string(raw_entry, "category", errors, label)
    phase = _required_string(raw_entry, "phase", errors, label)
    owner_type = raw_entry.get("owner_type", "household")
    if owner_type not in ALLOWED_OWNERS:
        errors.append(f"{label}.owner_type is invalid")
    person_id = raw_entry.get("person_id")
    if owner_type == "person":
        if not isinstance(person_id, str) or not person_id.strip():
            errors.append(f"{label}.person_id is required for person-owned expenses")
        elif person_ids is not None and person_id not in person_ids:
            errors.append(f"{label}.person_id references unknown person: {person_id}")
    elif person_id not in (None, ""):
        errors.append(f"{label}.person_id must be empty for household-owned expenses")

    frequency = raw_entry.get("frequency")
    if frequency not in ALLOWED_FREQUENCIES:
        errors.append(f"{label}.frequency is invalid")
    currency = raw_entry.get("currency", "EUR")
    if currency != "EUR":
        errors.append(f"{label}.currency must be EUR")
    amount = _decimal(raw_entry.get("amount"), f"{label}.amount", errors)
    if amount is not None and amount < Decimal("0"):
        errors.append(f"{label}.amount must be non-negative")
    inflation_rate = _decimal(raw_entry.get("annual_inflation_rate", "0"), f"{label}.annual_inflation_rate", errors)
    if inflation_rate is not None and inflation_rate < Decimal("0"):
        errors.append(f"{label}.annual_inflation_rate must be non-negative")

    start_year = _year(raw_entry.get("start_year"), f"{label}.start_year", errors)
    end_year = _year(raw_entry.get("end_year"), f"{label}.end_year", errors)
    event_id = raw_entry.get("event_id")
    if frequency == "one_time":
        if event_id not in (None, ""):
            if not isinstance(event_id, str):
                errors.append(f"{label}.event_id must be a string")
            elif event_id in event_years:
                start_year = event_years[event_id]
                end_year = event_years[event_id]
            else:
                data_gaps.append(
                    {
                        "code": "timeline_event_not_found",
                        "entry_id": entry_id,
                        "event_id": event_id,
                        "message": "Expense references a timeline event that is not available.",
                    }
                )
        if start_year is not None and end_year is None:
            end_year = start_year
        if end_year is not None and start_year is None:
            start_year = end_year
    if start_year is None:
        data_gaps.append(
            {
                "code": "missing_expense_start_year",
                "entry_id": entry_id,
                "message": "Expense start_year is missing.",
            }
        )
    if frequency == "annual" and end_year is None:
        data_gaps.append(
            {
                "code": "missing_expense_end_year",
                "entry_id": entry_id,
                "message": "Annual expense end_year is missing.",
            }
        )
    if start_year is not None and end_year is not None and end_year < start_year:
        errors.append(f"{label}.end_year must be greater than or equal to start_year")
    provenance = _required_string(raw_entry, "provenance", errors, label)

    if entry_id is None or category is None or phase is None or amount is None or inflation_rate is None:
        return None
    return {
        "entry_id": entry_id,
        "category": category,
        "phase": phase,
        "owner_type": owner_type,
        "person_id": person_id if owner_type == "person" else None,
        "frequency": frequency,
        "start_year": start_year,
        "end_year": end_year,
        "amount": _format_money(amount),
        "currency": currency,
        "annual_inflation_rate": str(inflation_rate),
        "event_id": event_id if event_id not in (None, "") else None,
        "provenance": provenance,
    }


def _build_yearly_cashflow(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_year: dict[int, dict[str, Any]] = {}
    for entry in entries:
        if entry["start_year"] is None or entry["end_year"] is None:
            continue
        amount = _decimal_required(entry["amount"], "entry.amount")
        inflation_rate = _decimal_required(entry["annual_inflation_rate"], "entry.annual_inflation_rate")
        for year in range(entry["start_year"], entry["end_year"] + 1):
            if entry["frequency"] == "one_time" and year != entry["start_year"]:
                continue
            inflated = amount * ((Decimal("1") + inflation_rate) ** (year - entry["start_year"]))
            bucket = by_year.setdefault(year, {"year": year, "total_expenses": Decimal("0.00"), "categories": {}, "items": []})
            bucket["total_expenses"] += inflated
            category_total = bucket["categories"].get(entry["category"], Decimal("0.00"))
            bucket["categories"][entry["category"]] = category_total + inflated
            bucket["items"].append(
                {
                    "entry_id": entry["entry_id"],
                    "category": entry["category"],
                    "phase": entry["phase"],
                    "amount": _format_money(inflated),
                    "currency": "EUR",
                }
            )
    cashflow: list[dict[str, Any]] = []
    for year in sorted(by_year):
        bucket = by_year[year]
        cashflow.append(
            {
                "year": year,
                "total_expenses": _format_money(bucket["total_expenses"]),
                "currency": "EUR",
                "categories": {
                    category: _format_money(total)
                    for category, total in sorted(bucket["categories"].items())
                },
                "items": bucket["items"],
            }
        )
    return cashflow


def _summary(
    entries: list[dict[str, Any]],
    yearly_cashflow: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    totals = [_decimal_required(year["total_expenses"], "year.total_expenses") for year in yearly_cashflow]
    return {
        "entry_count": len(entries),
        "year_count": len(yearly_cashflow),
        "first_year": yearly_cashflow[0]["year"] if yearly_cashflow else None,
        "last_year": yearly_cashflow[-1]["year"] if yearly_cashflow else None,
        "min_yearly_expenses": _format_money(min(totals)) if totals else None,
        "max_yearly_expenses": _format_money(max(totals)) if totals else None,
        "data_gap_count": len(data_gaps),
    }


def _validate_declared_gaps(raw_gaps: Any, errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if raw_gaps in (None, ""):
        return
    if not isinstance(raw_gaps, list):
        errors.append("data_gaps must be a list")
        return
    for index, gap in enumerate(raw_gaps):
        if not isinstance(gap, dict):
            errors.append(f"data_gaps[{index}] must be an object")
            continue
        if not gap.get("code"):
            errors.append(f"data_gaps[{index}].code is required")
            continue
        data_gaps.append(gap)


def _required_string(data: dict[str, Any], field: str, errors: list[str], prefix: str | None = None) -> str | None:
    label = field if prefix is None else f"{prefix}.{field}"
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} is required")
        return None
    return value


def _year(value: Any, label: str, errors: list[str]) -> int | None:
    if value in (None, ""):
        return None
    if not isinstance(value, int) or value < 1900 or value > 2200:
        errors.append(f"{label} must be a valid year")
        return None
    return value


def _decimal(value: Any, label: str, errors: list[str]) -> Decimal | None:
    if value in (None, ""):
        errors.append(f"{label} is required")
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        errors.append(f"{label} must be a decimal")
        return None


def _decimal_required(value: Any, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise LifecycleExpensesError(f"Invalid decimal for {label}: {value}") from exc


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT))
