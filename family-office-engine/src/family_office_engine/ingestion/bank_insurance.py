import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "bank-insurance/v1"


class BankInsuranceImportError(ValueError):
    pass


def import_bank_insurance(bank_dir: Path, insurance_dir: Path, output_path: Path) -> dict[str, Any]:
    documents = load_bank_insurance_documents(bank_dir, "bank") + load_bank_insurance_documents(
        insurance_dir,
        "insurance",
    )
    items = [item for document in documents for item in document.get("items", [])]
    data_gaps = [gap for document in documents for gap in document.get("data_gaps", [])]

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "BankInsuranceSnapshot",
        "source": {
            "type": "classified-bank-insurance-documents",
            "bank_path": str(bank_dir),
            "insurance_path": str(insurance_dir),
        },
        "extraction_status": "extracted" if items and not data_gaps else "partial_extracted",
        "documents": documents,
        "items": items,
        "data_gaps": data_gaps,
        "notes": "Bank and insurance documents parsed deterministically; no value is estimated.",
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise BankInsuranceImportError(f"Cannot write bank-insurance snapshot: {output_path}") from exc
    return snapshot


def load_bank_insurance_documents(input_dir: Path, document_group: str) -> list[dict[str, Any]]:
    if not input_dir.exists():
        raise BankInsuranceImportError(f"{document_group} input directory not found: {input_dir}")
    if not input_dir.is_dir():
        raise BankInsuranceImportError(f"{document_group} input path is not a directory: {input_dir}")

    documents: list[dict[str, Any]] = []
    for path in sorted(input_dir.iterdir()):
        if not path.is_file():
            continue
        documents.append(_load_document(path, document_group))
    return documents


def parse_bank_insurance_text(text: str, document_group: str, filename: str) -> dict[str, Any]:
    normalized = _normalize_text(text)
    generali_items = _parse_generali_contributions(normalized, filename)
    if generali_items:
        return {
            "status": "extracted",
            "provider": "Generali",
            "items": generali_items,
            "data_gaps": [],
        }

    return {
        "status": "unsupported_format",
        "provider": _guess_provider(normalized, filename),
        "items": [],
        "data_gaps": [
            {
                "code": "unsupported_bank_insurance_document",
                "message": "No deterministic parser matched this bank/insurance document.",
                "filename": filename,
                "document_group": document_group,
            }
        ],
    }


def _load_document(path: Path, document_group: str) -> dict[str, Any]:
    if path.suffix.lower() != ".pdf":
        parsed = {
            "status": "unsupported_file_type",
            "provider": _guess_provider("", path.name),
            "items": [],
            "data_gaps": [
                {
                    "code": "unsupported_file_type",
                    "message": f"Unsupported file type for first bank-insurance import: {path.suffix}",
                    "filename": path.name,
                    "document_group": document_group,
                }
            ],
        }
    else:
        try:
            text = _extract_pdf_text(path)
            if not text.strip():
                parsed = {
                    "status": "pdf_text_empty",
                    "provider": _guess_provider("", path.name),
                    "items": [],
                    "data_gaps": [
                        {
                            "code": "pdf_text_empty",
                            "message": "PDF text extraction returned no text.",
                            "filename": path.name,
                            "document_group": document_group,
                        }
                    ],
                }
            else:
                parsed = parse_bank_insurance_text(text, document_group, path.name)
        except BankInsuranceImportError as exc:
            parsed = {
                "status": "pdf_text_error",
                "provider": _guess_provider("", path.name),
                "items": [],
                "data_gaps": [
                    {
                        "code": "pdf_text_error",
                        "message": str(exc),
                        "filename": path.name,
                        "document_group": document_group,
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
    for item in parsed.get("items", []):
        item["source"] = {
            "filename": path.name,
            "path": str(path),
        }
    return parsed


def _extract_pdf_text(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise BankInsuranceImportError("PyPDF2 is required to extract bank/insurance PDF text") from exc

    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise BankInsuranceImportError(f"Cannot extract text from bank/insurance PDF: {path}") from exc


def _parse_generali_contributions(text: str, filename: str) -> list[dict[str, Any]]:
    if "Generali" not in text and "V. Pensione" not in text:
        return []

    amount = _search_decimal(
        text,
        r"contributi complessivi versati sono pari a\s*[^\d]*(\d[\d.]*,\d{2})",
    )
    if amount is None:
        amount = _search_decimal(text, r"Contributi versati dal Contraente\s*[^\d]*(\d[\d.]*,\d{2})")
    if amount is None:
        return []

    year = _search_value(text, r"contributi versati nel\s+(\d{4})")
    if year is None:
        year = _search_value(text, r"nel\s+(\d{4})\s+i contributi")
    return [
        {
            "provider": "Generali",
            "document_group": "insurance",
            "instrument_type": "pension_policy",
            "description": "V. Pensione annual contributions",
            "amount_type": "annual_contributions",
            "period_year": year,
            "amount": amount,
            "currency": "EUR",
            "confidence": "parsed_from_statement",
        }
    ]


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\xa0", " "))


def _search_decimal(text: str, pattern: str) -> str | None:
    value = _search_value(text, pattern)
    if value is None:
        return None
    return value.replace(".", "").replace(",", ".")


def _search_value(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _guess_provider(text: str, filename: str) -> str:
    haystack = f"{filename}\n{text}".lower()
    if "generali" in haystack:
        return "Generali"
    if "plan universal" in haystack:
        return "Plan Universal"
    if "kutxabank" in haystack or "movimientos" in haystack or "certificado" in haystack:
        return "Kutxabank"
    return "unknown"
