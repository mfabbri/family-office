import json
import re
import unicodedata
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "spanish-pension/v1"


class SpanishPensionImportError(ValueError):
    pass


def import_spanish_pension(input_dir: Path, output_path: Path) -> dict[str, Any]:
    documents = load_spanish_pension_documents(input_dir)
    recognized = [document for document in documents if document["status"] == "spanish_pension_extracted"]
    contribution_history = _merge_first_present(
        document.get("contribution_history", {}) for document in recognized
    )
    data_gaps = _data_gaps(contribution_history, recognized)

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "SpanishPensionSnapshot",
        "source": {
            "type": "spanish-pension-pdf-directory",
            "path": str(input_dir),
        },
        "extraction_status": "extracted" if recognized and not data_gaps else "partial_extracted",
        "documents": documents,
        "contribution_history": contribution_history,
        "data_gaps": data_gaps,
        "notes": "Spanish pension documents parsed deterministically; no pension or tax calculation performed.",
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise SpanishPensionImportError(f"Cannot write Spanish pension snapshot: {output_path}") from exc
    return snapshot


def load_spanish_pension_documents(input_dir: Path) -> list[dict[str, Any]]:
    if not input_dir.exists():
        raise SpanishPensionImportError(f"Spanish pension input directory not found: {input_dir}")
    if not input_dir.is_dir():
        raise SpanishPensionImportError(f"Spanish pension input path is not a directory: {input_dir}")

    pdf_paths = sorted(input_dir.glob("*.pdf"))
    if not pdf_paths:
        raise SpanishPensionImportError(f"No PDF files found in Spanish pension directory: {input_dir}")

    return [_load_spanish_pension_pdf(path) for path in pdf_paths]


def parse_spanish_pension_text(text: str) -> dict[str, Any]:
    normalized = _normalize_text(text)
    searchable = _ascii_fold(normalized)
    if not _looks_like_spanish_pension(searchable):
        return {
            "status": "not_spanish_pension",
            "document_type": "unknown",
            "contribution_history": {},
            "data_gaps": [],
        }

    document_type = _document_type(searchable)
    contribution_history = _parse_contribution_history(searchable)

    return {
        "status": "spanish_pension_extracted",
        "document_type": document_type,
        "contribution_history": contribution_history,
        "data_gaps": _document_data_gaps(document_type, contribution_history),
    }


def _load_spanish_pension_pdf(path: Path) -> dict[str, Any]:
    try:
        text = _extract_pdf_text(path)
    except SpanishPensionImportError as exc:
        return {
            "filename": path.name,
            "path": str(path),
            "status": "pdf_text_error",
            "document_type": "unknown",
            "error": str(exc),
            "contribution_history": {},
            "data_gaps": [{"code": "pdf_text_error", "message": str(exc)}],
        }

    parsed = parse_spanish_pension_text(text)
    parsed.update(
        {
            "filename": path.name,
            "path": str(path),
        }
    )
    return parsed


def _extract_pdf_text(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise SpanishPensionImportError("PyPDF2 is required to extract Spanish pension PDF text") from exc

    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise SpanishPensionImportError(f"Cannot extract text from Spanish pension PDF: {path}") from exc


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\xa0", " "))


def _ascii_fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _looks_like_spanish_pension(text: str) -> bool:
    markers = (
        "INFORME DE VIDA LABORAL",
        "TESORERIA GENERAL DE LA SEGURIDAD SOCIAL",
        "Sistema de la Seguridad Social",
        "SITUACION/ES",
    )
    return sum(1 for marker in markers if marker.lower() in text.lower()) >= 2


def _document_type(text: str) -> str:
    if "INFORME DE VIDA LABORAL" in text.upper():
        return "vida_laboral"
    return "spanish_pension_related"


def _parse_contribution_history(text: str) -> dict[str, str]:
    history: dict[str, str] = {}
    report_date = _search_date(text, r"Id\.\s*CEA:\s*Fecha:\s*C\S*digo\s+CEA:\s*P\S*gina:\s*\S+\s+(\d{2}/\d{2}/\d{4})")
    if report_date is None:
        report_date = _search_date(text, r"\bFecha:\s*(\d{2}/\d{2}/\d{4})")
    total = re.search(
        r"durante\s+un\s+total\s+de\s*(\d+)\s*A\w*os\s+([\d.]+)\s*d\w*as\s+(\d+)\s*meses\s+(\d+)\s*d\w*as",
        text,
        flags=re.IGNORECASE,
    )

    _put_if_present(history, "report_date", report_date)
    if total:
        years, total_days, months, residual_days = total.groups()
        _put_if_present(history, "registered_years", years)
        _put_if_present(history, "registered_months", months)
        _put_if_present(history, "registered_residual_days", residual_days)
        _put_if_present(history, "registered_total_days", total_days.replace(".", ""))
    return history


def _document_data_gaps(document_type: str, contribution_history: dict[str, str]) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    if document_type == "vida_laboral":
        for field in ("report_date", "registered_total_days"):
            if field not in contribution_history:
                gaps.append(
                    {
                        "code": f"missing_{field}",
                        "message": f"Cannot find {field} in Spanish pension PDF.",
                    }
                )
    return gaps


def _data_gaps(
    contribution_history: dict[str, str],
    recognized: list[dict[str, Any]],
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    if not recognized:
        gaps.append({"code": "missing_spanish_pension_pdf", "message": "No recognizable Spanish pension PDF found."})
        return gaps
    for field in ("report_date", "registered_total_days"):
        if field not in contribution_history:
            gaps.append({"code": f"missing_contribution_{field}", "message": f"Missing contribution field: {field}."})
    return gaps


def _merge_first_present(sources: Any) -> dict[str, str]:
    merged: dict[str, str] = {}
    for source in sources:
        for key, value in source.items():
            if key not in merged and value not in (None, ""):
                merged[key] = value
    return merged


def _search_date(text: str, pattern: str) -> str | None:
    value = _search_value(text, pattern)
    if value is None:
        return None
    day, month, year = value.split("/")
    return f"{year}-{month}-{day}"


def _search_value(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _put_if_present(target: dict[str, str], key: str, value: str | None) -> None:
    if value not in (None, ""):
        target[key] = value
