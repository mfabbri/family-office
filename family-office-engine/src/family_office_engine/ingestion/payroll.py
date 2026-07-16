import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "payroll/v1"
DIAGNOSTICS_SCHEMA_VERSION = "payroll-diagnostics/v1"
IGNORED_FILENAMES = {".gitkeep"}


class PayrollImportError(ValueError):
    pass


def import_payroll(input_dir: Path, output_path: Path) -> dict[str, Any]:
    documents = load_payroll_documents(input_dir)
    records = [record for document in documents for record in document.get("records", [])]
    data_gaps = [gap for document in documents for gap in document.get("data_gaps", [])]
    if not documents:
        data_gaps.append(
            {
                "code": "no_payroll_documents",
                "message": "No payroll documents found.",
                "path": str(input_dir),
            }
        )

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "PayrollSnapshot",
        "source": {
            "type": "classified-payroll-documents",
            "path": str(input_dir),
        },
        "extraction_status": _extraction_status(records, data_gaps),
        "documents": documents,
        "records": records,
        "summary": _summary(records),
        "data_gaps": data_gaps,
        "notes": "Payroll import records values explicitly present in documents; no tax is calculated.",
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise PayrollImportError(f"Cannot write payroll snapshot: {output_path}") from exc
    return snapshot


def diagnose_payroll_input(input_dir: Path) -> dict[str, Any]:
    documents = load_payroll_documents(input_dir)
    records = [record for document in documents for record in document.get("records", [])]
    data_gaps = [gap for document in documents for gap in document.get("data_gaps", [])]
    if not documents:
        data_gaps.append(
            {
                "code": "no_payroll_documents",
                "message": "No payroll documents found.",
                "path": str(input_dir),
            }
        )

    return {
        "schema_version": DIAGNOSTICS_SCHEMA_VERSION,
        "record_type": "PayrollDiagnostics",
        "input": {
            "path": str(input_dir),
            "exists": input_dir.exists(),
            "is_dir": input_dir.is_dir(),
        },
        "status": _extraction_status(records, data_gaps),
        "summary": {
            "document_count": len(documents),
            "record_count": len(records),
            "data_gap_count": len(data_gaps),
            "document_statuses": _count_values(
                document.get("status", "unknown") for document in documents
            ),
            "gap_codes": _count_values(gap.get("code", "unknown") for gap in data_gaps),
        },
        "documents": [
            {
                "filename": document.get("filename"),
                "status": document.get("status"),
                "record_count": len(document.get("records", [])),
                "gap_codes": [
                    gap.get("code", "unknown")
                    for gap in document.get("data_gaps", [])
                ],
            }
            for document in documents
        ],
        "next_actions": _diagnostic_next_actions(documents, data_gaps),
    }


def load_payroll_documents(input_dir: Path) -> list[dict[str, Any]]:
    if not input_dir.exists():
        raise PayrollImportError(f"Payroll input directory not found: {input_dir}")
    if not input_dir.is_dir():
        raise PayrollImportError(f"Payroll input path is not a directory: {input_dir}")

    documents: list[dict[str, Any]] = []
    for path in sorted(input_dir.iterdir()):
        if not path.is_file() or path.name in IGNORED_FILENAMES:
            continue
        documents.append(_load_document(path))
    return documents


def parse_payroll_text(text: str, filename: str) -> dict[str, Any]:
    normalized = _normalize_text(text)
    if not _looks_like_payroll(normalized):
        return {
            "status": "unsupported_format",
            "records": [],
            "data_gaps": [
                {
                    "code": "unsupported_payroll_document",
                    "message": "No deterministic payroll parser matched this document.",
                    "filename": filename,
                }
            ],
        }

    record = {
        "period_label": _period_label(normalized),
        "period_year": _period_year(normalized),
        "employer": _employer(normalized),
        "net_pay": _net_pay(normalized),
        "taxable_irpef": _decimal_after_label(normalized, r"Imp\.\s*IRPEF"),
        "irpef_withheld": _decimal_after_label(normalized, r"IRPEF\s+pagata"),
        "currency": "EUR",
        "withholding_items": _withholding_items(normalized),
        "confidence": "parsed_from_payslip_text",
    }
    missing = [
        field
        for field in ("period_label", "net_pay")
        if record.get(field) is None
    ]
    data_gaps = [
        {
            "code": "missing_payroll_field",
            "message": f"Payroll field not found: {field}",
            "filename": filename,
        }
        for field in missing
    ]
    status = "extracted" if not missing else "partial_extracted"
    return {
        "status": status,
        "records": [record],
        "data_gaps": data_gaps,
    }


def _load_document(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".pdf":
        parsed = {
            "status": "unsupported_file_type",
            "records": [],
            "data_gaps": [
                {
                    "code": "unsupported_file_type",
                    "message": f"Unsupported payroll file type: {path.suffix}",
                    "filename": path.name,
                }
            ],
        }
    else:
        try:
            text = _extract_pdf_text(path)
            if not text.strip():
                parsed = {
                    "status": "pdf_text_empty",
                    "records": [],
                    "data_gaps": [
                        {
                            "code": "pdf_text_empty",
                            "message": "PDF text extraction returned no text.",
                            "filename": path.name,
                        }
                    ],
                }
            else:
                parsed = parse_payroll_text(text, path.name)
        except PayrollImportError as exc:
            parsed = {
                "status": "pdf_text_error",
                "records": [],
                "data_gaps": [
                    {
                        "code": "pdf_text_error",
                        "message": str(exc),
                        "filename": path.name,
                    }
                ],
            }

    parsed.update(
        {
            "filename": path.name,
            "path": str(path),
        }
    )
    for record in parsed.get("records", []):
        record["source"] = {
            "filename": path.name,
            "path": str(path),
        }
    return parsed


def _extract_pdf_text(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise PayrollImportError("PyPDF2 is required to extract payroll PDF text") from exc

    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise PayrollImportError(f"Cannot extract text from payroll PDF: {path}") from exc


def _normalize_text(text: str) -> str:
    return text.replace("\xa0", " ").replace("€", "EUR").replace("�", "EUR")


def _looks_like_payroll(text: str) -> bool:
    lower = text.lower()
    markers = ("netto", "irpef", "periodo", "retribuzione", "busta")
    return sum(marker in lower for marker in markers) >= 3


def _period_label(text: str) -> str | None:
    match = re.search(
        r"\b(Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|Settembre|Ottobre|Novembre|Dicembre)\s+(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    month = match.group(1).capitalize()
    return f"{month} {match.group(2)}"


def _period_year(text: str) -> int | None:
    label = _period_label(text)
    if label is None:
        return None
    return int(label.split()[-1])


def _employer(text: str) -> str | None:
    company_match = re.search(
        r"(?:^|\n)(?:Detrazioni)?\s*\d{6}\s+([A-Z][A-Z0-9 .,&'/-]+(?:SRL|S\.R\.L\.|SPA|S\.P\.A\.|COOP|SOCIETA)[^\n]*)",
        text,
    )
    if company_match:
        return company_match.group(1).strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if re.fullmatch(r"\d{6}\s+.+", line):
            candidate = re.sub(r"^\d{6}\s+", "", line).strip()
            if candidate and not re.search(r"\d{4}", candidate):
                return candidate
        if line.lower().startswith("ragiones") and index + 1 < len(lines):
            candidate = lines[index + 1].strip()
            if candidate:
                return re.sub(r"^\d{6}\s+", "", candidate)
    return None


def _net_pay(text: str) -> str | None:
    candidates = re.findall(r"(\d[\d.]*,\d{2})\s*(?:EUR)?\s*$", text, flags=re.MULTILINE)
    if not candidates:
        return None
    return _to_decimal(candidates[-1])


def _decimal_after_label(text: str, label_pattern: str) -> str | None:
    match = re.search(rf"{label_pattern}\s+(\d[\d.]*,\d{{2}})", text, flags=re.IGNORECASE)
    if not match:
        return None
    return _to_decimal(match.group(1))


def _withholding_items(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    patterns = (
        ("irpef_withheld", r"IRPEF\s+pagata\s+(\d[\d.]*,\d{2})"),
        ("taxable_irpef", r"Imp\.\s*IRPEF\s+(\d[\d.]*,\d{2})"),
        ("gross_irpef", r"IRPEF\s+lorda\s+(\d[\d.]*,\d{2})"),
        ("employee_deduction", r"Detrazioni\s+lav\.dip\.\s+(\d[\d.]*,\d{2})"),
    )
    for code, pattern in patterns:
        value = _search_decimal(text, pattern)
        if value is not None:
            items.append(
                {
                    "code": code,
                    "amount": value,
                    "currency": "EUR",
                }
            )

    for match in re.finditer(
        r"\*?Z\d{5}\s+(Contributo [^\n]+?)\s+(?:\d[\d.]*,\d{2}\s+%\s+[\d,]+\s+)?(\d[\d.]*,\d{2})",
        text,
        flags=re.IGNORECASE,
    ):
        description = match.group(1).strip()
        if "c/ditta" in description.lower():
            continue
        items.append(
            {
                "code": "social_security_contribution",
                "description": description,
                "amount": _to_decimal(match.group(2)),
                "currency": "EUR",
            }
        )
    return items


def _search_decimal(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return _to_decimal(match.group(1))


def _to_decimal(value: str) -> str:
    return value.replace(".", "").replace(",", ".")


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    net_pays = [record.get("net_pay") for record in records if record.get("net_pay") is not None]
    return {
        "record_count": len(records),
        "periods": [record.get("period_label") for record in records if record.get("period_label")],
        "net_pay_total": _sum_decimal_strings(net_pays),
    }


def _sum_decimal_strings(values: list[str]) -> str | None:
    if not values:
        return None
    cents = 0
    for value in values:
        whole, _, decimal = value.partition(".")
        cents += int(whole) * 100 + int((decimal + "00")[:2])
    return f"{cents // 100}.{cents % 100:02d}"


def _count_values(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _extraction_status(records: list[dict[str, Any]], data_gaps: list[dict[str, Any]]) -> str:
    if not records:
        return "no_documents" if any(gap.get("code") == "no_payroll_documents" for gap in data_gaps) else "not_extracted"
    if data_gaps:
        return "partial_extracted"
    return "extracted"


def _diagnostic_next_actions(
    documents: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
) -> list[str]:
    gap_codes = {gap.get("code") for gap in data_gaps}
    actions: list[str] = []
    if not documents or "no_payroll_documents" in gap_codes:
        actions.append("Verify the payroll input directory or pass --input-dir explicitly.")
    if "unsupported_file_type" in gap_codes:
        actions.append("Keep only PDF payslips in the payroll input directory.")
    if "pdf_text_empty" in gap_codes:
        actions.append("The PDF may be scanned; add OCR support before importing it.")
    if "pdf_text_error" in gap_codes:
        actions.append("Verify PyPDF2 availability in the active Python environment.")
    if "unsupported_payroll_document" in gap_codes:
        actions.append("Add a deterministic parser for this payslip layout.")
    if "missing_payroll_field" in gap_codes:
        actions.append("Inspect parser coverage for missing required payroll fields.")
    if not actions:
        actions.append("Payroll input is ready for import.")
    return actions
