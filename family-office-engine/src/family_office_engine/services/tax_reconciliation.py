import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "tax-reconciliation/v1"


class TaxReconciliationError(ValueError):
    pass


def reconcile_tax_sources(
    payroll_snapshot_path: Path,
    tax_documents_snapshot_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    data_gaps: list[dict[str, Any]] = []
    payroll = _read_json(payroll_snapshot_path, "payroll")
    tax_documents = _read_json(tax_documents_snapshot_path, "tax documents")

    payroll_records = _payroll_records(payroll, data_gaps)
    tax_records = _tax_records(tax_documents, data_gaps)
    year_summaries = _year_summaries(payroll_records, tax_records, data_gaps)
    if not year_summaries:
        data_gaps.append(
            {
                "code": "missing_reconcilable_years",
                "message": "No payroll or tax document years are available for reconciliation.",
            }
        )

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "TaxReconciliationSnapshot",
        "status": "complete" if year_summaries and not data_gaps else "partial",
        "sources": {
            "payroll": str(payroll_snapshot_path),
            "tax_documents": str(tax_documents_snapshot_path),
        },
        "summary": {
            "years": [summary["year"] for summary in year_summaries],
            "payroll_record_count": len(payroll_records),
            "tax_document_record_count": len(tax_records),
            "data_gap_count": len(data_gaps),
        },
        "years": year_summaries,
        "data_gaps": data_gaps,
        "notes": "Tax reconciliation compares documentary sources; it does not calculate taxes.",
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise TaxReconciliationError(f"Cannot write tax reconciliation snapshot: {output_path}") from exc
    return snapshot


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TaxReconciliationError(f"Missing {label} snapshot: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TaxReconciliationError(f"Invalid {label} snapshot JSON: {path}") from exc


def _payroll_records(
    payroll: dict[str, Any],
    data_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = payroll.get("records", [])
    if not isinstance(records, list):
        data_gaps.append({"code": "invalid_payroll_records", "message": "Payroll records must be a list."})
        return []

    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str | None, str | None, str | None]] = set()
    duplicate_count = 0
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
            duplicate_count += 1
            continue
        seen.add(key)
        normalized.append(record)
    if duplicate_count:
        data_gaps.append(
            {
                "code": "duplicate_payroll_records_excluded",
                "message": f"Excluded {duplicate_count} duplicate payroll record(s) during reconciliation.",
                "duplicate_count": duplicate_count,
            }
        )
    return normalized


def _tax_records(
    tax_documents: dict[str, Any],
    data_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = tax_documents.get("records", [])
    if not isinstance(records, list):
        data_gaps.append({"code": "invalid_tax_document_records", "message": "Tax document records must be a list."})
        return []
    return [record for record in records if isinstance(record, dict)]


def _year_summaries(
    payroll_records: list[dict[str, Any]],
    tax_records: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    payroll_years = {int(record["period_year"]) for record in payroll_records if record.get("period_year") is not None}
    tax_years = {
        int(record.get("fields", {}).get("tax_year"))
        for record in tax_records
        if record.get("fields", {}).get("tax_year") is not None
    }
    for year in sorted(payroll_years - tax_years):
        data_gaps.append(
            {
                "code": "payroll_year_without_tax_document",
                "message": f"Payroll year {year} has no CU or declaration tax document.",
                "year": year,
            }
        )
    for year in sorted(tax_years - payroll_years):
        data_gaps.append(
            {
                "code": "tax_document_year_without_payroll",
                "message": f"Tax document year {year} has no payroll records.",
                "year": year,
            }
        )
    return [
        _year_summary(year, payroll_records, tax_records, data_gaps)
        for year in sorted(payroll_years | tax_years)
    ]


def _year_summary(
    year: int,
    payroll_records: list[dict[str, Any]],
    tax_records: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    payroll_for_year = [record for record in payroll_records if record.get("period_year") == year]
    tax_for_year = [
        record for record in tax_records if int(record.get("fields", {}).get("tax_year", -1)) == year
    ]
    cu_records = [record for record in tax_for_year if record.get("document_type") == "certificazione_unica"]
    declaration_records = [record for record in tax_for_year if record.get("document_type") == "dichiarazione_redditi_pf"]
    if not cu_records and payroll_for_year:
        data_gaps.append({"code": "missing_cu_for_payroll_year", "message": f"Missing CU for payroll year {year}.", "year": year})
    if not declaration_records and cu_records:
        data_gaps.append(
            {
                "code": "missing_declaration_for_cu_year",
                "message": f"Missing tax declaration for CU tax year {year}.",
                "year": year,
            }
        )

    payroll_taxable = _sum_field(payroll_for_year, "taxable_irpef")
    payroll_irpef = _sum_field(payroll_for_year, "irpef_withheld")
    return {
        "year": year,
        "payroll": {
            "record_count": len(payroll_for_year),
            "observed_months": sorted({record.get("period_label") for record in payroll_for_year if record.get("period_label")}),
            "taxable_irpef_observed": _money(payroll_taxable),
            "irpef_withheld_observed": _money(payroll_irpef),
        },
        "cu": [_tax_record_summary(record) for record in cu_records],
        "declaration": [_tax_record_summary(record) for record in declaration_records],
    }


def _tax_record_summary(record: dict[str, Any]) -> dict[str, Any]:
    fields = record.get("fields", {})
    return {
        "document_type": record.get("document_type"),
        "model_year": fields.get("model_year"),
        "tax_year": fields.get("tax_year"),
        "available_fields": sorted(fields),
        "source": record.get("source"),
    }


def _sum_field(records: list[dict[str, Any]], field: str) -> Decimal:
    total = Decimal("0.00")
    for record in records:
        if record.get(field) is not None:
            total += _decimal(record[field])
    return total


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise TaxReconciliationError(f"Invalid decimal value: {value}") from exc


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def _string(value: Any) -> str | None:
    return None if value is None else str(value)
