import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "inps-pension/v1"


class InpsPensionImportError(ValueError):
    pass


def import_inps_pension(input_dir: Path, output_path: Path) -> dict[str, Any]:
    documents = load_inps_pension_documents(input_dir)
    recognized = [document for document in documents if document["status"] == "inps_extracted"]
    projection = _merge_first_present(document.get("projection", {}) for document in recognized)
    contribution_position = _merge_first_present(
        document.get("contribution_position", {}) for document in recognized
    )
    contribution_periods = _merge_contribution_periods(recognized)
    data_gaps = _data_gaps(projection, contribution_position, recognized)

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "InpsPensionSnapshot",
        "source": {
            "type": "inps-pension-pdf-directory",
            "path": str(input_dir),
        },
        "extraction_status": "extracted" if recognized and not data_gaps else "partial_extracted",
        "documents": documents,
        "projection": projection,
        "contribution_position": contribution_position,
        "contribution_periods": contribution_periods,
        "data_gaps": data_gaps,
        "notes": "INPS pension PDFs parsed deterministically; no pension or tax calculation performed.",
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise InpsPensionImportError(f"Cannot write INPS pension snapshot: {output_path}") from exc
    return snapshot


def load_inps_pension_documents(input_dir: Path) -> list[dict[str, Any]]:
    if not input_dir.exists():
        raise InpsPensionImportError(f"INPS pension input directory not found: {input_dir}")
    if not input_dir.is_dir():
        raise InpsPensionImportError(f"INPS pension input path is not a directory: {input_dir}")

    pdf_paths = sorted(input_dir.glob("*.pdf"))
    if not pdf_paths:
        raise InpsPensionImportError(f"No PDF files found in INPS pension directory: {input_dir}")

    return [_load_inps_pension_pdf(path) for path in pdf_paths]


def parse_inps_pension_text(text: str) -> dict[str, Any]:
    normalized = _normalize_text(text)
    if not _looks_like_inps_pension(normalized):
        return {
            "status": "not_inps_pension",
            "document_type": "unknown",
            "projection": {},
            "contribution_position": {},
            "contribution_periods": [],
            "data_gaps": [],
        }

    projection = _parse_projection(normalized)
    contribution_position = _parse_contribution_position(normalized)
    contribution_periods = _parse_contribution_periods(normalized)
    document_type = _document_type(normalized)

    return {
        "status": "inps_extracted",
        "document_type": document_type,
        "projection": projection,
        "contribution_position": contribution_position,
        "contribution_periods": contribution_periods,
        "data_gaps": _document_data_gaps(document_type, projection, contribution_position),
    }


def _load_inps_pension_pdf(path: Path) -> dict[str, Any]:
    try:
        text = _extract_pdf_text(path)
    except InpsPensionImportError as exc:
        return {
            "filename": path.name,
            "path": str(path),
            "status": "pdf_text_error",
            "document_type": "unknown",
            "error": str(exc),
            "projection": {},
            "contribution_position": {},
            "contribution_periods": [],
            "data_gaps": [{"code": "pdf_text_error", "message": str(exc)}],
        }

    parsed = parse_inps_pension_text(text)
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
        raise InpsPensionImportError("PyPDF2 is required to extract INPS PDF text") from exc

    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise InpsPensionImportError(f"Cannot extract text from INPS PDF: {path}") from exc


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\xa0", " "))


def _looks_like_inps_pension(text: str) -> bool:
    markers = (
        "Data elaborazione",
        "Codice Fiscale",
        "Pensione di vecchiaia",
        "Contributi utili",
        "Estratto Conto",
    )
    return "INPS" in text or sum(1 for marker in markers if marker in text) >= 3


def _document_type(text: str) -> str:
    has_projection = "Pensione di vecchiaia" in text or "Previsione della tua pensione" in text
    has_current_position = "Contributi utili ai fini della pensione" in text
    if has_projection and "Composizione della pensione simulata" in text:
        return "pension_detail"
    if has_projection:
        return "pension_simulation_summary"
    if has_current_position:
        return "current_contribution_position"
    return "inps_pension_related"


def _parse_projection(text: str) -> dict[str, str]:
    projection: dict[str, str] = {}
    extraction_date = _search_date(text, r"Data elaborazione:\s*(\d{2}/\d{2}/\d{4})")
    retirement_date = _search_date(text, r"Data di pensionamento\s*(\d{2}/\d{2}/\d{4})")
    monthly_gross_pension = _search_decimal(text, r"Importo pensione mensile lordo\s*[^\d]*(\d[\d.]*,\d{2})")
    estimated_last_gross_income = _search_decimal(
        text,
        r"Ultima retribuzione/reddito lorda/o stimata\d*\s*[^\d]*(\d[\d.]*,\d{2})",
    )
    gross_replacement_rate = _search_decimal(text, r"Tasso di sostituzione lordo\d*\s*(\d+(?:[,.]\d+)?)\s*%")
    separate_management_quota = _search_decimal(
        text,
        r"Gestione Separata di\s*[^\d]*(\d[\d.]*,\d{2})",
    )
    prices_year = _search_value(text, r"prezzi\s+(\d{4})")
    projection_fund = _search_value(text, r"Fondo proiezione:\s*([^\n]+)")

    _put_if_present(projection, "extraction_date", extraction_date)
    _put_if_present(projection, "retirement_date", retirement_date)
    _put_if_present(projection, "monthly_gross_pension", monthly_gross_pension)
    _put_if_present(projection, "estimated_last_gross_income", estimated_last_gross_income)
    _put_if_present(projection, "gross_replacement_rate", gross_replacement_rate)
    _put_if_present(projection, "separate_management_quota", separate_management_quota)
    _put_if_present(projection, "prices_year", prices_year)
    _put_if_present(projection, "projection_fund", projection_fund)
    return projection


def _parse_contribution_position(text: str) -> dict[str, str]:
    position: dict[str, str] = {}
    extraction_date = _search_date(text, r"Data elaborazione:\s*(\d{2}/\d{2}/\d{4})")
    pension_weeks = _search_value(text, r"(\d+)\s+settimane\s+Contributi utili ai fini della pensione")
    separate_management_weeks = _search_value(
        text,
        r"(\d+)\s+settimane\s+Contributi utili in Gestione Separata",
    )

    _put_if_present(position, "extraction_date", extraction_date)
    _put_if_present(position, "pension_contribution_weeks", pension_weeks)
    _put_if_present(position, "separate_management_weeks", separate_management_weeks)
    return position


def _parse_contribution_periods(text: str) -> list[dict[str, Any]]:
    periods: list[dict[str, Any]] = []
    periods.extend(_parse_ordinary_contribution_periods(text))
    periods.extend(_parse_separate_management_periods(text))
    return periods


def _parse_ordinary_contribution_periods(text: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"(?P<start>\d{2}/\d{2}/\d{4})\s+"
        r"(?P<right_weeks>\d+)\s+settimane\s+"
        r"(?P<calc_weeks>\d+)\s+settimane\s+"
        r"€\s*(?P<income>[\d.]+,\d{2})\s+"
        r"(?P<contribution_type>.+?)\s+"
        r"(?P<end>\d{2}/\d{2}/\d{4})",
        flags=re.IGNORECASE,
    )
    periods: list[dict[str, Any]] = []
    for match in pattern.finditer(text):
        contribution_type = match.group("contribution_type").strip()
        right_weeks = int(match.group("right_weeks"))
        period_status = _period_status(contribution_type, right_weeks)
        periods.append(
            {
                "country": "IT",
                "scheme": "FPLD",
                "source_section": "Estratto Conto",
                "start_date": _italian_date_to_iso(match.group("start")),
                "end_date": _italian_date_to_iso(match.group("end")),
                "contribution_type": contribution_type,
                "weeks_for_right": right_weeks,
                "weeks_for_calculation": int(match.group("calc_weeks")),
                "income_amount": _italian_money_to_decimal(match.group("income")),
                "currency": "EUR",
                "period_status": period_status,
            }
        )
    return periods


def _parse_separate_management_periods(text: str) -> list[dict[str, Any]]:
    section = text.split("Estratto Conto Gestione Separata", 1)
    if len(section) < 2:
        return []
    pattern = re.compile(
        r"(?P<year>\d{4})\s+"
        r"(?P<weeks>\d+)\s+settimane\s+"
        r"€\s*(?P<income>[\d.]+,\d{2})\s+"
        r"(?P<contribution_type>[^\n]+)",
        flags=re.IGNORECASE,
    )
    periods: list[dict[str, Any]] = []
    for match in pattern.finditer(section[1]):
        year = int(match.group("year"))
        weeks = int(match.group("weeks"))
        periods.append(
            {
                "country": "IT",
                "scheme": "GESTIONE_SEPARATA",
                "source_section": "Estratto Conto Gestione Separata",
                "start_date": f"{year:04d}-01-01",
                "end_date": f"{year:04d}-12-31",
                "contribution_type": match.group("contribution_type").strip(),
                "weeks_for_right": weeks,
                "weeks_for_calculation": weeks,
                "income_amount": _italian_money_to_decimal(match.group("income")),
                "currency": "EUR",
                "period_status": "usable" if weeks > 0 else "zero_weeks",
            }
        )
    return periods


def _document_data_gaps(
    document_type: str,
    projection: dict[str, str],
    contribution_position: dict[str, str],
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    if document_type in {"pension_detail", "pension_simulation_summary"}:
        for field in ("retirement_date", "monthly_gross_pension"):
            if field not in projection:
                gaps.append({"code": f"missing_{field}", "message": f"Cannot find {field} in INPS PDF."})
    if document_type == "current_contribution_position":
        for field in ("pension_contribution_weeks", "separate_management_weeks"):
            if field not in contribution_position:
                gaps.append({"code": f"missing_{field}", "message": f"Cannot find {field} in INPS PDF."})
    return gaps


def _data_gaps(
    projection: dict[str, str],
    contribution_position: dict[str, str],
    recognized: list[dict[str, Any]],
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    if not recognized:
        gaps.append({"code": "missing_inps_pension_pdf", "message": "No recognizable INPS pension PDF found."})
        return gaps
    for field in ("retirement_date", "monthly_gross_pension"):
        if field not in projection:
            gaps.append({"code": f"missing_projection_{field}", "message": f"Missing projection field: {field}."})
    for field in ("pension_contribution_weeks", "separate_management_weeks"):
        if field not in contribution_position:
            gaps.append(
                {
                    "code": f"missing_contribution_{field}",
                    "message": f"Missing contribution position field: {field}.",
                }
            )
    return gaps


def _merge_first_present(sources: Any) -> dict[str, str]:
    merged: dict[str, str] = {}
    for source in sources:
        for key, value in source.items():
            if key not in merged and value not in (None, ""):
                merged[key] = value
    return merged


def _merge_contribution_periods(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for document in documents:
        source_document = document.get("filename")
        for period in document.get("contribution_periods", []):
            item = dict(period)
            if source_document:
                item["source_document"] = source_document
            key = (
                item.get("scheme"),
                item.get("start_date"),
                item.get("end_date"),
                item.get("contribution_type"),
                item.get("weeks_for_right"),
                item.get("income_amount"),
            )
            by_key.setdefault(key, item)
    return sorted(by_key.values(), key=lambda item: (item["start_date"], item["scheme"], item["contribution_type"]))


def _period_status(contribution_type: str, weeks: int) -> str:
    if weeks == 0:
        return "zero_weeks"
    if "teoric" in contribution_type.lower():
        return "projected"
    return "usable"


def _search_date(text: str, pattern: str) -> str | None:
    value = _search_value(text, pattern)
    if value is None:
        return None
    day, month, year = value.split("/")
    return f"{year}-{month}-{day}"


def _italian_date_to_iso(value: str) -> str:
    day, month, year = value.split("/")
    return f"{year}-{month}-{day}"


def _italian_money_to_decimal(value: str) -> str:
    return value.replace(".", "").replace(",", ".")


def _search_decimal(text: str, pattern: str) -> str | None:
    value = _search_value(text, pattern)
    if value is None:
        return None
    if "," in value:
        return value.replace(".", "").replace(",", ".")
    return value


def _search_value(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _put_if_present(target: dict[str, str], key: str, value: str | None) -> None:
    if value not in (None, ""):
        target[key] = value
