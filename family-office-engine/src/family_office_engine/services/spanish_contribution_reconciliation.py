import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "spanish-contribution-reconciliation/v1"
RECORD_TYPE = "SpanishContributionReconciliationSnapshot"


class SpanishContributionReconciliationError(ValueError):
    pass


def reconcile_spanish_contributions(
    contribution_history_snapshot_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    history = _read_json(contribution_history_snapshot_path)
    if history.get("schema_version") != "spanish-contribution-history/v1":
        raise SpanishContributionReconciliationError(
            f"Unsupported Spanish contribution history schema: {history.get('schema_version')}"
        )

    periods = _periods(history)
    monthly_bases = _monthly_bases(history)
    covered_months = _covered_months(periods)
    reconciled_months, data_gaps, anomalies = _reconciled_months(covered_months, monthly_bases)

    usable_months = [month for month in reconciled_months if month["usable_for_estimator"]]
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "status": "complete" if usable_months and not data_gaps else "partial",
        "source": {
            "type": "spanish-contribution-history-snapshot",
            "path": str(contribution_history_snapshot_path),
            "schema_version": history.get("schema_version"),
        },
        "summary": {
            "covered_month_count": len(covered_months),
            "usable_month_count": len(usable_months),
            "official_base_month_count": sum(1 for month in reconciled_months if month["official_bases"]),
            "payroll_base_month_count": sum(1 for month in reconciled_months if month["payroll_bases"]),
            "data_gap_count": len(data_gaps),
            "anomaly_count": len(anomalies),
        },
        "months": reconciled_months,
        "data_gaps": data_gaps,
        "anomalies": anomalies,
        "notes": (
            "Spanish contribution reconciliation selects documentary monthly bases; official bases prevail "
            "over payroll. No pension, entitlement, tax, base reguladora or EU coordination calculation performed."
        ),
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise SpanishContributionReconciliationError(
            f"Cannot write Spanish contribution reconciliation snapshot: {output_path}"
        ) from exc
    return snapshot


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpanishContributionReconciliationError(f"Missing Spanish contribution history snapshot: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SpanishContributionReconciliationError(f"Invalid Spanish contribution history JSON: {path}") from exc


def _periods(history: dict[str, Any]) -> list[dict[str, Any]]:
    periods = history.get("periods", [])
    if not isinstance(periods, list):
        raise SpanishContributionReconciliationError("Spanish contribution history periods must be a list.")
    return [period for period in periods if isinstance(period, dict)]


def _monthly_bases(history: dict[str, Any]) -> list[dict[str, Any]]:
    monthly_bases = history.get("monthly_bases", [])
    if not isinstance(monthly_bases, list):
        raise SpanishContributionReconciliationError("Spanish contribution history monthly_bases must be a list.")
    return [base for base in monthly_bases if isinstance(base, dict)]


def _covered_months(periods: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    covered: dict[str, list[dict[str, Any]]] = {}
    for period in periods:
        start = _date_from_iso(_required_string(period, "start_date"))
        end_value = period.get("end_date") or period.get("start_date")
        end = _date_from_iso(_required_string({"end_date": end_value}, "end_date"))
        for month in _month_range(start, end):
            covered.setdefault(month, []).append(_period_summary(period))
    return covered


def _reconciled_months(
    covered_months: dict[str, list[dict[str, Any]]],
    monthly_bases: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    bases_by_month: dict[str, list[dict[str, Any]]] = {}
    for base in monthly_bases:
        month = _required_string(base, "month")
        bases_by_month.setdefault(month, []).append(_base_summary(base))

    all_months = sorted(set(covered_months) | set(bases_by_month))
    data_gaps: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    reconciled: list[dict[str, Any]] = []

    for month in all_months:
        periods = covered_months.get(month, [])
        bases = bases_by_month.get(month, [])
        official_bases = [base for base in bases if base["source_type"] == "official_bases"]
        payroll_bases = [base for base in bases if base["source_type"] == "payroll"]
        selected = _selected_base(month, official_bases, payroll_bases)

        month_anomalies = _month_anomalies(month, official_bases, payroll_bases)
        anomalies.extend(month_anomalies)
        month_gap_codes: list[str] = []
        if periods and not bases:
            gap = {
                "code": "covered_month_without_base",
                "month": month,
                "message": f"Vida Laboral covers {month}, but no contribution base is documented.",
            }
            data_gaps.append(gap)
            month_gap_codes.append(gap["code"])
        if bases and not periods:
            gap = {
                "code": "base_without_vida_laboral_period",
                "month": month,
                "message": f"Contribution base exists for {month}, but no Vida Laboral period covers the month.",
            }
            data_gaps.append(gap)
            month_gap_codes.append(gap["code"])
        if payroll_bases and not official_bases and periods:
            gap = {
                "code": "payroll_base_without_official_base",
                "month": month,
                "message": f"Only payroll contribution base is available for {month}; official base is missing.",
            }
            data_gaps.append(gap)
            month_gap_codes.append(gap["code"])

        reconciled.append(
            {
                "month": month,
                "covered_by_vida_laboral": bool(periods),
                "periods": periods,
                "official_bases": official_bases,
                "payroll_bases": payroll_bases,
                "selected_base": selected,
                "usable_for_estimator": bool(periods and selected and selected["source_type"] == "official_bases"),
                "data_gap_codes": month_gap_codes,
                "anomaly_codes": [anomaly["code"] for anomaly in month_anomalies],
            }
        )
    return reconciled, data_gaps, anomalies


def _selected_base(
    month: str,
    official_bases: list[dict[str, Any]],
    payroll_bases: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if official_bases:
        return _aggregate_base(month, official_bases, "official_bases", "high")
    if payroll_bases:
        return _aggregate_base(month, payroll_bases, "payroll", "medium")
    return None


def _aggregate_base(
    month: str,
    bases: list[dict[str, Any]],
    source_type: str,
    confidence: str,
) -> dict[str, Any]:
    total = sum((_decimal(base["base_amount"]) for base in bases), Decimal("0.00"))
    return {
        "month": month,
        "base_amount": _money(total),
        "currency": "EUR",
        "source_type": source_type,
        "confidence": confidence,
        "source_documents": sorted({base["source_document"] for base in bases if base.get("source_document")}),
        "component_count": len(bases),
    }


def _month_anomalies(
    month: str,
    official_bases: list[dict[str, Any]],
    payroll_bases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    if len(official_bases) > 1:
        anomalies.append(
            {
                "code": "multiple_official_bases_same_month",
                "month": month,
                "message": f"Multiple official contribution bases are documented for {month}.",
                "base_count": len(official_bases),
            }
        )
    if len(payroll_bases) > 1:
        anomalies.append(
            {
                "code": "multiple_payroll_bases_same_month",
                "month": month,
                "message": f"Multiple payroll contribution bases are documented for {month}.",
                "base_count": len(payroll_bases),
            }
        )
    if official_bases and payroll_bases:
        official_total = sum((_decimal(base["base_amount"]) for base in official_bases), Decimal("0.00"))
        payroll_total = sum((_decimal(base["base_amount"]) for base in payroll_bases), Decimal("0.00"))
        if official_total != payroll_total:
            anomalies.append(
                {
                    "code": "payroll_official_base_difference",
                    "month": month,
                    "message": f"Payroll and official contribution bases differ for {month}.",
                    "official_base_amount": _money(official_total),
                    "payroll_base_amount": _money(payroll_total),
                    "difference": _money(payroll_total - official_total),
                }
            )
    return anomalies


def _period_summary(period: dict[str, Any]) -> dict[str, Any]:
    return {
        "start_date": period.get("start_date"),
        "end_date": period.get("end_date"),
        "regime": period.get("regime"),
        "employer": period.get("employer"),
        "source_document": period.get("source_document"),
    }


def _base_summary(base: dict[str, Any]) -> dict[str, Any]:
    return {
        "month": base.get("month"),
        "base_amount": _money(_decimal(base.get("base_amount"))),
        "currency": base.get("currency", "EUR"),
        "source_type": base.get("source_type"),
        "confidence": base.get("confidence"),
        "source_document": base.get("source_document"),
        "employer": base.get("employer"),
    }


def _required_string(record: dict[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        raise SpanishContributionReconciliationError(f"Missing required field {field}.")
    return value


def _date_from_iso(value: str) -> date:
    year, month, day = value.split("-")
    return date(int(year), int(month), int(day))


def _month_range(start: date, end: date) -> list[str]:
    current_year = start.year
    current_month = start.month
    end_key = end.year * 12 + end.month
    months: list[str] = []
    while current_year * 12 + current_month <= end_key:
        months.append(f"{current_year:04d}-{current_month:02d}")
        if current_month == 12:
            current_year += 1
            current_month = 1
        else:
            current_month += 1
    return months


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise SpanishContributionReconciliationError(f"Invalid decimal value: {value}") from exc


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"
