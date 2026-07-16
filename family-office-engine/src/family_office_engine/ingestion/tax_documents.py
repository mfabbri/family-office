import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "tax-documents/v1"
DIAGNOSTICS_SCHEMA_VERSION = "tax-documents-diagnostics/v1"
IGNORED_FILENAMES = {".gitkeep"}


class TaxDocumentsImportError(ValueError):
    pass


def import_tax_documents(cu_dir: Path, declarations_dir: Path, output_path: Path) -> dict[str, Any]:
    documents = load_tax_documents(cu_dir, declarations_dir)
    records = [record for document in documents for record in document.get("records", [])]
    data_gaps = [gap for document in documents for gap in document.get("data_gaps", [])]
    if not documents:
        data_gaps.append(
            {
                "code": "no_tax_documents",
                "message": "No CU or tax declaration documents found.",
            }
        )

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "TaxDocumentsSnapshot",
        "source": {
            "type": "classified-tax-documents",
            "cu_path": str(cu_dir),
            "declarations_path": str(declarations_dir),
        },
        "extraction_status": _extraction_status(records, data_gaps),
        "documents": documents,
        "records": records,
        "summary": _summary(records, data_gaps),
        "data_gaps": data_gaps,
        "notes": "Tax documents import records values explicitly present in documents; no tax is calculated.",
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise TaxDocumentsImportError(f"Cannot write tax documents snapshot: {output_path}") from exc
    return snapshot


def diagnose_tax_documents(cu_dir: Path, declarations_dir: Path) -> dict[str, Any]:
    documents = load_tax_documents(cu_dir, declarations_dir)
    records = [record for document in documents for record in document.get("records", [])]
    data_gaps = [gap for document in documents for gap in document.get("data_gaps", [])]
    if not documents:
        data_gaps.append(
            {
                "code": "no_tax_documents",
                "message": "No CU or tax declaration documents found.",
            }
        )
    return {
        "schema_version": DIAGNOSTICS_SCHEMA_VERSION,
        "record_type": "TaxDocumentsDiagnostics",
        "status": _extraction_status(records, data_gaps),
        "input": {
            "cu_path": str(cu_dir),
            "cu_exists": cu_dir.exists(),
            "declarations_path": str(declarations_dir),
            "declarations_exists": declarations_dir.exists(),
        },
        "summary": _summary(records, data_gaps) | {
            "document_count": len(documents),
            "data_gap_count": len(data_gaps),
            "document_statuses": _count_values(document.get("status", "unknown") for document in documents),
            "gap_codes": _count_values(gap.get("code", "unknown") for gap in data_gaps),
        },
        "documents": [
            {
                "filename": document.get("filename"),
                "document_group": document.get("document_group"),
                "status": document.get("status"),
                "record_count": len(document.get("records", [])),
                "gap_codes": [gap.get("code", "unknown") for gap in document.get("data_gaps", [])],
            }
            for document in documents
        ],
        "next_actions": _diagnostic_next_actions(documents, data_gaps),
    }


def load_tax_documents(cu_dir: Path, declarations_dir: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    documents.extend(_load_directory(cu_dir, "cu"))
    documents.extend(_load_directory(declarations_dir, "declaration"))
    return documents


def parse_tax_document_text(text: str, filename: str, document_group: str) -> dict[str, Any]:
    normalized = _normalize_text(text)
    document_type = _document_type(normalized, document_group)
    if document_type == "unknown":
        return {
            "status": "unsupported_tax_document",
            "document_type": "unknown",
            "records": [],
            "data_gaps": [
                {
                    "code": "unsupported_tax_document",
                    "message": "No deterministic tax document parser matched this document.",
                    "filename": filename,
                }
            ],
        }

    fields = _extract_fields(normalized, document_type)
    missing = [
        field
        for field in _required_fields(document_type)
        if fields.get(field) is None
    ]
    data_gaps = [
        {
            "code": "missing_tax_document_field",
            "message": f"Tax document field not found: {field}",
            "field": field,
            "filename": filename,
        }
        for field in missing
    ]
    record = {
        "document_type": document_type,
        "document_group": document_group,
        "fields": {key: value for key, value in fields.items() if value is not None},
        "currency": "EUR",
        "confidence": "parsed_from_tax_document_text",
    }
    status = "extracted" if not data_gaps else "partial_extracted"
    return {
        "status": status,
        "document_type": document_type,
        "records": [record],
        "data_gaps": data_gaps,
    }


def _load_directory(input_dir: Path, document_group: str) -> list[dict[str, Any]]:
    if not input_dir.exists():
        return [
            {
                "filename": None,
                "path": str(input_dir),
                "document_group": document_group,
                "status": "missing_input_directory",
                "records": [],
                "data_gaps": [
                    {
                        "code": "missing_input_directory",
                        "message": f"Tax document input directory not found: {input_dir}",
                        "path": str(input_dir),
                    }
                ],
            }
        ]
    if not input_dir.is_dir():
        raise TaxDocumentsImportError(f"Tax document input path is not a directory: {input_dir}")

    documents = []
    for path in sorted(input_dir.iterdir()):
        if not path.is_file() or path.name in IGNORED_FILENAMES:
            continue
        documents.append(_load_document(path, document_group))
    return documents


def _load_document(path: Path, document_group: str) -> dict[str, Any]:
    if path.suffix.lower() != ".pdf":
        parsed = {
            "status": "unsupported_file_type",
            "document_type": "unknown",
            "records": [],
            "data_gaps": [
                {
                    "code": "unsupported_file_type",
                    "message": f"Unsupported tax document file type: {path.suffix}",
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
                    "document_type": "unknown",
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
                parsed = parse_tax_document_text(text, path.name, document_group)
        except TaxDocumentsImportError as exc:
            parsed = {
                "status": "pdf_text_error",
                "document_type": "unknown",
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
            "document_group": document_group,
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
        raise TaxDocumentsImportError("PyPDF2 is required to extract tax document PDF text") from exc
    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise TaxDocumentsImportError(f"Cannot extract text from tax document PDF: {path}") from exc


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\xa0", " ").replace("’", "'"))


def _document_type(text: str, document_group: str) -> str:
    lower = text.lower()
    if document_group == "cu" or "certificazione unica" in lower:
        if "certificazione unica" in lower or "certificazione lavoro dipendente" in lower:
            return "certificazione_unica"
    if document_group == "declaration" or "persone fisiche" in lower or "periodo d'imposta" in lower:
        if "persone fisiche" in lower or "periodo d'imposta" in lower or "periodo dimposta" in lower:
            return "dichiarazione_redditi_pf"
    return "unknown"


def _extract_fields(text: str, document_type: str) -> dict[str, str | None]:
    if document_type == "certificazione_unica":
        model_year = _search_year(text, r"CERTIFICAZIONE\s+UNICA\s*(\d{4})") or _search_year(
            text,
            r"CERTIFICAZIONE\s+UNICA(\d{4})",
        )
        return {
            "model_year": model_year,
            "tax_year": _cu_tax_year(text, model_year),
            "employment_income": _search_decimal(
                text,
                r"Redditi di lavoro dipendente[^\n]*\n\s*(\d[\d.]*,\d{2})",
            ),
            "irpef_withheld": _search_decimal(text, r"Ritenute\s+Irpef\s+(\d[\d.]*,\d{2})"),
            "regional_additional_irpef": _search_decimal(
                text,
                r"Addizionale\s+regionale\s+all'?Irpef\s+(\d[\d.]*,\d{2})",
            ),
            "municipal_additional_irpef_balance": _search_decimal(
                text,
                r"Saldo\s+\d{4}\s+(\d[\d.]*,\d{2})",
            ),
        }
    return {
        "model_year": _search_year(text, r"PERSONE\s+FISICHE\s*(\d{4})"),
        "tax_year": _search_year(text, r"Periodo\s+d'?imposta\s+(\d{4})")
        or _search_year(text, r"Periodo\s+dimposta\s+(\d{4})"),
        "total_income": _search_decimal(text, r"RN1\s+REDDITO\s+COMPLESSIVO\s+(\d[\d.]*,\d{2})"),
        "gross_tax": _search_decimal(text, r"RN5\s+IMPOSTA\s+LORDA\s+(\d[\d.]*,\d{2})"),
        "net_tax": _search_decimal(text, r"RN26\s+IMPOSTA\s+NETTA\s+(\d[\d.]*,\d{2})"),
        "regional_additional_irpef": _search_decimal(
            text,
            r"RV1\s+ADDIZIONALE\s+REGIONALE[^\d]*(\d[\d.]*,\d{2})",
        ),
    }


def _required_fields(document_type: str) -> tuple[str, ...]:
    if document_type == "certificazione_unica":
        return ("model_year", "tax_year")
    return ("model_year", "tax_year")


def _cu_tax_year(text: str, model_year: str | None) -> str | None:
    explicit = _search_year(text, r"RELATIVA\s+ALL'?ANNO\s+(\d{4})")
    if explicit is not None and _is_plausible_year(explicit):
        return explicit
    if model_year is None:
        return None
    return str(int(model_year) - 1)


def _search_year(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else None


def _is_plausible_year(value: str) -> bool:
    year = int(value)
    return 1900 <= year <= 2100


def _search_decimal(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return _to_decimal(match.group(1))


def _to_decimal(value: str) -> str:
    return value.replace(".", "").replace(",", ".")


def _summary(records: list[dict[str, Any]], data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    document_types = [record.get("document_type", "unknown") for record in records]
    return {
        "record_count": len(records),
        "document_types": _count_values(document_types),
        "tax_years": sorted(
            {
                str(record.get("fields", {}).get("tax_year"))
                for record in records
                if record.get("fields", {}).get("tax_year") is not None
            }
        ),
        "data_gap_count": len(data_gaps),
    }


def _count_values(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _extraction_status(records: list[dict[str, Any]], data_gaps: list[dict[str, Any]]) -> str:
    if not records:
        return "no_documents" if any(gap.get("code") == "no_tax_documents" for gap in data_gaps) else "not_extracted"
    if data_gaps:
        return "partial_extracted"
    return "extracted"


def _diagnostic_next_actions(
    documents: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
) -> list[str]:
    gap_codes = {gap.get("code") for gap in data_gaps}
    actions: list[str] = []
    if not documents or "no_tax_documents" in gap_codes:
        actions.append("Verify CU and declaration input directories.")
    if "missing_input_directory" in gap_codes:
        actions.append("Run documents organize --apply or pass explicit input directories.")
    if "pdf_text_empty" in gap_codes:
        actions.append("The PDF may be scanned; add OCR support before importing it.")
    if "unsupported_tax_document" in gap_codes:
        actions.append("Add a deterministic parser for this tax document layout.")
    if "missing_tax_document_field" in gap_codes:
        actions.append("Inspect parser coverage for missing fiscal fields.")
    if not actions:
        actions.append("Tax documents input is ready for import.")
    return actions
