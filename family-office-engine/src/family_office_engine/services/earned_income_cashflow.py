import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "earned-income-cashflow/v1"
CURRENT_PERIODS_PER_YEAR = 12


class EarnedIncomeCashflowError(ValueError):
    pass


def build_earned_income_cashflow(
    payroll_snapshot_path: Path,
    output_path: Path,
    assumptions_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    data_gaps: list[dict[str, Any]] = []
    sources: dict[str, str] = {}

    payroll = _read_optional_json(payroll_snapshot_path, data_gaps, "payroll")
    assumptions = None
    if assumptions_snapshot_path is not None:
        assumptions = _read_optional_json(assumptions_snapshot_path, data_gaps, "manual assumptions")

    if payroll is not None:
        sources["payroll"] = str(payroll_snapshot_path)
    if assumptions is not None and assumptions_snapshot_path is not None:
        sources["manual_assumptions"] = str(assumptions_snapshot_path)

    result = _build_result(payroll, assumptions, data_gaps) if payroll is not None else None
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "EarnedIncomeCashflowSnapshot",
        "status": "complete" if result is not None else "blocked_missing_inputs",
        "sources": sources,
        "records": result["records"] if result else [],
        "summary": result["summary"] if result else None,
        "data_gaps": data_gaps,
        "notes": (
            "Earned income cashflow uses net payroll values already present in documents; "
            "no gross-to-net tax or contribution calculation is performed."
        ),
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise EarnedIncomeCashflowError(f"Cannot write earned income cashflow: {output_path}") from exc
    return snapshot


def _build_result(
    payroll: dict[str, Any],
    assumptions: dict[str, Any] | None,
    data_gaps: list[dict[str, Any]],
) -> dict[str, Any] | None:
    records = _dedupe_records(payroll.get("records", []), data_gaps)
    observed_records = [record for record in records if record.get("net_pay") is not None]
    if not observed_records:
        data_gaps.append(
            {
                "code": "missing_payroll_net_pay_records",
                "message": "No payroll records with net pay are available.",
            }
        )
        return None

    years = sorted({int(record["period_year"]) for record in observed_records if record.get("period_year")})
    if not years:
        data_gaps.append(
            {
                "code": "missing_payroll_period_year",
                "message": "Payroll records do not include a period year for annual aggregation.",
            }
        )
        return None

    annual_summaries = [_annual_summary(year, observed_records, data_gaps) for year in years]
    latest = annual_summaries[-1]
    _compare_manual_salary(latest, assumptions, data_gaps)
    return {
        "records": [_cashflow_record(record) for record in observed_records],
        "summary": {
            "currency": "EUR",
            "latest_year": latest["year"],
            "latest_year_observed_net_pay": latest["observed_net_pay"],
            "latest_year_observed_periods": latest["observed_periods"],
            "latest_year_annualized_net_pay": latest["annualized_net_pay"],
            "latest_year_annualization_method": latest["annualization_method"],
            "years": annual_summaries,
            "confidence": latest["confidence"],
        },
    }


def _dedupe_records(
    records: Any,
    data_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        data_gaps.append(
            {
                "code": "invalid_payroll_records",
                "message": "Payroll snapshot records must be a list.",
            }
        )
        return []

    unique: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str | None, str | None, str | None]] = set()
    duplicates = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        key = (
            _string(record.get("period_label")),
            _string(record.get("period_year")),
            _string(record.get("employer")),
            _string(record.get("net_pay")),
        )
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        unique.append(record)

    if duplicates:
        data_gaps.append(
            {
                "code": "duplicate_payroll_records_excluded",
                "message": f"Excluded {duplicates} duplicate payroll record(s).",
                "duplicate_count": duplicates,
            }
        )
    return unique


def _annual_summary(
    year: int,
    records: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    year_records = [record for record in records if record.get("period_year") == year]
    observed_net_pay = sum((_decimal(record["net_pay"], "net_pay") for record in year_records), Decimal("0"))
    observed_periods = len(year_records)
    annualized_net_pay = observed_net_pay
    annualization_method = "observed_full_year"
    confidence = "observed"

    if observed_periods < CURRENT_PERIODS_PER_YEAR:
        average = observed_net_pay / Decimal(observed_periods)
        annualized_net_pay = average * Decimal(CURRENT_PERIODS_PER_YEAR)
        annualization_method = "average_observed_month_12x"
        confidence = "annualized_from_partial_year"
        data_gaps.append(
            {
                "code": "missing_payroll_periods",
                "message": f"Payroll year {year} has {observed_periods} observed period(s), expected 12.",
                "year": year,
                "observed_periods": observed_periods,
                "expected_periods": CURRENT_PERIODS_PER_YEAR,
            }
        )
    elif observed_periods > CURRENT_PERIODS_PER_YEAR:
        annualization_method = "observed_extra_periods"
        confidence = "observed_with_extra_periods"
        data_gaps.append(
            {
                "code": "extra_payroll_periods",
                "message": f"Payroll year {year} has {observed_periods} observed period(s), above 12.",
                "year": year,
                "observed_periods": observed_periods,
                "expected_periods": CURRENT_PERIODS_PER_YEAR,
            }
        )

    employers = sorted({_string(record.get("employer")) or "unknown" for record in year_records})
    if len(employers) > 1:
        data_gaps.append(
            {
                "code": "multiple_payroll_employers",
                "message": f"Payroll year {year} includes multiple employers.",
                "year": year,
                "employers": employers,
            }
        )

    return {
        "year": year,
        "observed_periods": observed_periods,
        "observed_net_pay": _money(observed_net_pay),
        "annualized_net_pay": _money(annualized_net_pay),
        "annualization_method": annualization_method,
        "employers": employers,
        "confidence": confidence,
    }


def _compare_manual_salary(
    latest: dict[str, Any],
    assumptions: dict[str, Any] | None,
    data_gaps: list[dict[str, Any]],
) -> None:
    if assumptions is None:
        return
    manual_cashflow = assumptions.get("assumptions", {}).get("cashflow", {})
    if not isinstance(manual_cashflow, dict):
        return
    monthly = manual_cashflow.get("net_salary_monthly")
    months = manual_cashflow.get("salary_months")
    if monthly is None or months is None:
        return
    manual_yearly = _decimal(monthly, "net_salary_monthly") * _decimal(months, "salary_months")
    latest_yearly = _decimal(latest["annualized_net_pay"], "annualized_net_pay")
    if manual_yearly != latest_yearly:
        data_gaps.append(
            {
                "code": "manual_salary_superseded_by_payroll",
                "message": (
                    "Manual self salary cashflow differs from payroll-derived annualized net pay; "
                    "documentary payroll should be used to avoid duplication."
                ),
                "manual_salary_yearly": _money(manual_yearly),
                "payroll_annualized_net_pay": _money(latest_yearly),
                "year": latest["year"],
            }
        )


def _cashflow_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "period_label": record.get("period_label"),
        "period_year": record.get("period_year"),
        "employer": record.get("employer"),
        "net_pay": _money(_decimal(record["net_pay"], "net_pay")),
        "currency": record.get("currency", "EUR"),
        "confidence": record.get("confidence", "parsed_from_payroll_snapshot"),
        "source": record.get("source"),
    }


def _read_optional_json(
    path: Path,
    data_gaps: list[dict[str, Any]],
    label: str,
) -> dict[str, Any] | None:
    if not path.exists():
        data_gaps.append(
            {
                "code": f"missing_{label.replace(' ', '_')}_snapshot",
                "message": f"Missing {label} snapshot: {path}",
                "path": str(path),
            }
        )
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EarnedIncomeCashflowError(f"Cannot read {label} snapshot: {path}") from exc
    if not isinstance(data, dict):
        raise EarnedIncomeCashflowError(f"{label} snapshot must be a JSON object: {path}")
    return data


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise EarnedIncomeCashflowError(f"Invalid decimal for {field_name}: {value}") from exc


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
