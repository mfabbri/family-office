import csv
import hashlib
import json
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "spanish-contribution-history/v1"
RECORD_TYPE = "SpanishContributionHistorySnapshot"


class SpanishContributionHistoryImportError(ValueError):
    pass


def import_spanish_contribution_history(input_dir: Path, output_path: Path) -> dict[str, Any]:
    documents = load_spanish_contribution_documents(input_dir)
    periods = _dedupe_periods(_flatten(document.get("periods", []) for document in documents))
    monthly_bases = _dedupe_monthly_bases(_flatten(document.get("monthly_bases", []) for document in documents))
    data_gaps = _snapshot_data_gaps(documents, periods, monthly_bases)

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "source": {
            "type": "spanish-pension-document-directory",
            "path": str(input_dir),
        },
        "extraction_status": _extraction_status(documents, periods, monthly_bases, data_gaps),
        "documents": documents,
        "periods": periods,
        "monthly_bases": monthly_bases,
        "summary": {
            "period_count": len(periods),
            "monthly_base_count": len(monthly_bases),
            "document_count": len(documents),
            "data_gap_count": len(data_gaps),
        },
        "data_gaps": data_gaps,
        "notes": (
            "Spanish contribution documents parsed deterministically; no pension, entitlement, "
            "tax, base reguladora or reconciliation calculation performed."
        ),
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise SpanishContributionHistoryImportError(
            f"Cannot write Spanish contribution history snapshot: {output_path}"
        ) from exc
    return snapshot


def load_spanish_contribution_documents(input_dir: Path) -> list[dict[str, Any]]:
    if not input_dir.exists():
        raise SpanishContributionHistoryImportError(f"Spanish contribution input directory not found: {input_dir}")
    if not input_dir.is_dir():
        raise SpanishContributionHistoryImportError(f"Spanish contribution input path is not a directory: {input_dir}")

    paths = sorted(
        path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in {".pdf", ".txt", ".csv"}
    )
    if not paths:
        raise SpanishContributionHistoryImportError(
            f"No supported Spanish contribution files found in directory: {input_dir}"
        )

    seen_hashes: dict[str, Path] = {}
    documents: list[dict[str, Any]] = []
    for path in paths:
        digest = _sha256(path)
        if digest in seen_hashes:
            documents.append(
                {
                    "filename": path.name,
                    "path": str(path),
                    "sha256": digest,
                    "status": "duplicate_document",
                    "document_type": "duplicate",
                    "duplicate_of": seen_hashes[digest].name,
                    "periods": [],
                    "monthly_bases": [],
                    "data_gaps": [
                        {
                            "code": "duplicate_document",
                            "message": f"Document duplicates {seen_hashes[digest].name}.",
                        }
                    ],
                }
            )
            continue
        seen_hashes[digest] = path
        documents.append(_load_spanish_contribution_document(path, digest))
    return documents


def parse_spanish_contribution_text(text: str, filename: str = "document.txt") -> dict[str, Any]:
    normalized = _normalize_text(text)
    searchable = _ascii_fold(normalized)
    document_type = _document_type(searchable, filename)
    if document_type == "unknown":
        return _parsed_document(
            filename,
            "not_spanish_contribution_document",
            "unknown",
            [],
            [],
            [{"code": "unsupported_document", "message": "Document is not recognized as a supported Spanish contribution source."}],
        )

    periods = _parse_vida_laboral_periods(searchable, filename) if document_type == "vida_laboral" else []
    monthly_bases = _parse_text_monthly_bases(searchable, filename, document_type)
    gaps = _document_data_gaps(document_type, periods, monthly_bases)
    status = "extracted" if (periods or monthly_bases) and not gaps else "partial_extracted"
    if not periods and not monthly_bases:
        status = "not_extracted"
    return _parsed_document(filename, status, document_type, periods, monthly_bases, gaps)


def parse_spanish_contribution_csv(text: str, filename: str = "bases.csv") -> dict[str, Any]:
    rows = csv.DictReader(text.splitlines())
    monthly_bases: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    for row_number, row in enumerate(rows, start=2):
        normalized_row = {_normalize_header(key): value for key, value in row.items() if key is not None}
        year = (normalized_row.get("year") or normalized_row.get("anio") or "").strip()
        month = (normalized_row.get("month") or normalized_row.get("mes") or "").strip()
        period = (normalized_row.get("period") or normalized_row.get("periodo") or "").strip()
        amount = (
            normalized_row.get("base")
            or normalized_row.get("base_cotizacion")
            or normalized_row.get("base_de_cotizacion")
            or ""
        ).strip()
        parsed_month = _parse_month(year, month, period)
        parsed_amount = _parse_decimal(amount)
        if parsed_month is None or parsed_amount is None:
            gaps.append(
                {
                    "code": "invalid_base_row",
                    "message": f"Cannot parse contribution base row {row_number} in {filename}.",
                }
            )
            continue
        monthly_bases.append(_monthly_base(parsed_month, parsed_amount, filename, "official_bases", "high"))

    status = "extracted" if monthly_bases and not gaps else "partial_extracted"
    if not monthly_bases:
        status = "not_extracted"
    return _parsed_document(filename, status, "official_bases", [], monthly_bases, gaps)


def _load_spanish_contribution_document(path: Path, digest: str) -> dict[str, Any]:
    try:
        if path.suffix.lower() == ".pdf":
            text = _extract_pdf_text(path)
            if not text.strip():
                raise SpanishContributionHistoryImportError("PDF text extraction returned no text")
            parsed = parse_spanish_contribution_text(text, path.name)
        elif path.suffix.lower() == ".csv":
            parsed = parse_spanish_contribution_csv(path.read_text(encoding="utf-8-sig"), path.name)
        else:
            parsed = parse_spanish_contribution_text(path.read_text(encoding="utf-8-sig"), path.name)
    except (OSError, UnicodeError, SpanishContributionHistoryImportError) as exc:
        parsed = _parsed_document(
            path.name,
            "unreadable_document",
            "unknown",
            [],
            [],
            [{"code": "unreadable_document", "message": str(exc)}],
        )
    parsed.update({"filename": path.name, "path": str(path), "sha256": digest})
    return parsed


def _extract_pdf_text(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise SpanishContributionHistoryImportError("PyPDF2 is required to extract Spanish contribution PDF text") from exc

    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise SpanishContributionHistoryImportError(f"Cannot extract text from Spanish contribution PDF: {path}") from exc


def _document_type(text: str, filename: str) -> str:
    upper = text.upper()
    lower_name = filename.lower()
    if "INFORME DE VIDA LABORAL" in upper or "VIDA LABORAL" in lower_name:
        return "vida_laboral"
    if (
        "NOMINA" in upper
        or "RECIBO DE SALARIOS" in upper
        or "PERIODO DEVENGADO" in upper
        or "LIQUIDO TOTAL A PERCIBIR" in upper
        or "nomina" in lower_name
    ):
        return "payroll"
    if "BASES DE COTIZACION" in upper or "BASE DE COTIZACION" in upper or "BASES_COTIZACION" in lower_name:
        return "official_bases"
    return "unknown"


def _parse_vida_laboral_periods(text: str, filename: str) -> list[dict[str, Any]]:
    periods: list[dict[str, Any]] = []
    for row in _vida_laboral_rows(text):
        match = re.match(r"^(?P<regime>GENERAL|AUTONOMOS|AGRARIO|MAR|HOGAR)\s+(?P<account>\d+)\s+(?P<rest>.+)$", row)
        if not match:
            continue
        rest = _space_embedded_dates(match.group("rest"))
        date_matches = list(re.finditer(r"\d{2}[./]\d{2}[./]\d{4}", rest))
        if len(date_matches) < 3:
            continue
        employer = rest[: date_matches[0].start()].strip(" ,")
        tail = rest[date_matches[2].end() :]
        day_values = re.findall(r"\d[\d.]*", tail)
        if not day_values:
            continue
        contribution_days = int(day_values[-1].replace(".", ""))
        periods.append(
            {
                "start_date": _date_from_spanish(date_matches[0].group(0)),
                "end_date": _date_from_spanish(date_matches[2].group(0)),
                "regime": _squash_spaces(match.group("regime")).upper(),
                "employer": _squash_spaces(employer),
                "contribution_days": contribution_days,
                "source_document": filename,
                "source_type": "vida_laboral",
                "confidence": "high",
            }
        )
    periods.extend(_parse_simple_vida_laboral_periods(text, filename))
    return periods


def _parse_simple_vida_laboral_periods(text: str, filename: str) -> list[dict[str, Any]]:
    periods: list[dict[str, Any]] = []
    pattern = re.compile(
        r"(?P<regime>REG(?:IMEN)?\.?\s+[A-Z ]+|SISTEMA\s+ESPECIAL\s+[A-Z ]+)\s+"
        r"(?P<employer>[A-Z0-9 .,&/-]{3,80}?)\s+"
        r"(?P<start>\d{2}[./]\d{2}[./]\d{4})\s+"
        r"(?P<end>\d{2}[./]\d{2}[./]\d{4}|ACTUALIDAD|ALTA)\s+"
        r"(?P<days>\d{1,5})\b",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        end_value = match.group("end")
        periods.append(
            {
                "start_date": _date_from_spanish(match.group("start")),
                "end_date": None if end_value.upper() in {"ACTUALIDAD", "ALTA"} else _date_from_spanish(end_value),
                "regime": _squash_spaces(match.group("regime")).upper(),
                "employer": _squash_spaces(match.group("employer")),
                "contribution_days": int(match.group("days")),
                "source_document": filename,
                "source_type": "vida_laboral",
                "confidence": "high",
            }
        )
    return periods


def _parse_text_monthly_bases(text: str, filename: str, document_type: str) -> list[dict[str, Any]]:
    if document_type == "official_bases":
        tabular_bases = _parse_official_bases_table(text, filename)
        if tabular_bases:
            return tabular_bases
    if document_type == "payroll":
        payroll_bases = _parse_payroll_monthly_bases(text, filename)
        if payroll_bases:
            return payroll_bases

    source_type = "payroll" if document_type == "payroll" else "official_bases"
    confidence = "medium" if document_type == "payroll" else "high"
    bases: list[dict[str, Any]] = []
    for match in re.finditer(
        r"(?P<period>\b(?:\d{2}/\d{4}|\d{4}-\d{2}|[A-Z]+(?:\s+DE)?\s+\d{4})\b)"
        r".{0,120}?"
        r"(?:BASE(?:S)?(?:\s+DE)?\s+COTIZACION|BASE\s+CC|CONTINGENCIAS\s+COMUNES)"
        r".{0,80}?"
        r"(?P<amount>\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:\.\d{2})?)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        parsed_month = _parse_month("", "", match.group("period"))
        parsed_amount = _parse_decimal(match.group("amount"))
        if parsed_month and parsed_amount is not None:
            bases.append(_monthly_base(parsed_month, parsed_amount, filename, source_type, confidence))
    return bases


def _vida_laboral_rows(text: str) -> list[str]:
    rows: list[str] = []
    current: list[str] = []
    for line in (_squash_spaces(item) for item in text.splitlines()):
        if not line:
            continue
        if re.match(r"^(GENERAL|AUTONOMOS|AGRARIO|MAR|HOGAR)\s+\d+\b", line):
            if current:
                rows.append(_squash_spaces(" ".join(current)))
            current = [line]
            continue
        if current and not line.startswith(("REFERENCIAS ", "TVLCEAIM", "Notas ", "Los informes ")):
            current.append(line)
            if re.search(r"\d[\d.]*$", line) and len(re.findall(r"\d{2}[./]\d{2}[./]\d{4}", _space_embedded_dates(" ".join(current)))) >= 3:
                rows.append(_squash_spaces(" ".join(current)))
                current = []
    if current:
        rows.append(_squash_spaces(" ".join(current)))
    return rows


def _parse_official_bases_table(text: str, filename: str) -> list[dict[str, Any]]:
    bases: list[dict[str, Any]] = []
    current_employer: str | None = None
    for line in (_squash_spaces(item) for item in text.splitlines()):
        if line.startswith("Regimen:"):
            current_employer = _parse_official_bases_employer(line)
            continue
        match = re.match(r"^(?P<year>\d{4})\s+(?P<values>.+)$", line)
        if not match:
            continue
        tokens = match.group("values").split()
        if len(tokens) < 12:
            continue
        for month_index, token in enumerate(tokens[:12], start=1):
            if token == "---" or token == "*":
                continue
            provisional = token.endswith("*")
            amount = _parse_decimal(token.rstrip("*"))
            if amount is None:
                continue
            bases.append(
                _monthly_base(
                    f"{int(match.group('year')):04d}-{month_index:02d}",
                    amount,
                    filename,
                    "official_bases",
                    "medium" if provisional else "high",
                    current_employer,
                )
            )
    return bases


def _parse_official_bases_employer(line: str) -> str | None:
    match = re.search(r"Empresa/Razon Social:\s*(?P<employer>.+?)\s+CCC:\s*\d+", line)
    if not match:
        return None
    return _squash_spaces(match.group("employer"))


def _parse_payroll_monthly_bases(text: str, filename: str) -> list[dict[str, Any]]:
    month = _parse_payroll_month(text)
    if month is None:
        return []
    amount = _parse_payroll_contribution_base(text)
    if amount is None:
        return []
    return [_monthly_base(month, amount, filename, "payroll", "medium")]


def _parse_payroll_month(text: str) -> str | None:
    dates = re.findall(r"\b\d{2}[-/.]\d{2}[-/.]\d{4}\b", text)
    if not dates:
        return None
    separator = "-" if "-" in dates[-1] else "/" if "/" in dates[-1] else "."
    day, month, year = dates[-1].split(separator)
    return f"{int(year):04d}-{int(month):02d}"


def _parse_payroll_contribution_base(text: str) -> Decimal | None:
    match = re.search(
        r"(?P<amount>\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:\.\d{2})?)\s+CONTINGENCIAS\s+COMUNES",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return _parse_decimal(match.group("amount"))
    match = re.search(
        r"BASE\s+TOTAL\s+DE\s+COTIZACION\s+(?P<amount>\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:\.\d{2})?)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return _parse_decimal(match.group("amount"))
    return None


def _document_data_gaps(
    document_type: str,
    periods: list[dict[str, Any]],
    monthly_bases: list[dict[str, Any]],
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    if document_type == "vida_laboral" and not periods:
        gaps.append({"code": "missing_vida_laboral_periods", "message": "No contribution periods found in Vida Laboral."})
    if document_type == "official_bases" and not monthly_bases:
        gaps.append({"code": "missing_official_monthly_bases", "message": "No monthly contribution bases found."})
    if document_type == "payroll" and not monthly_bases:
        gaps.append({"code": "missing_payroll_contribution_base", "message": "No payroll contribution base found."})
    return gaps


def _snapshot_data_gaps(
    documents: list[dict[str, Any]],
    periods: list[dict[str, Any]],
    monthly_bases: list[dict[str, Any]],
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    for document in documents:
        for gap in document.get("data_gaps", []):
            item = dict(gap)
            item.setdefault("document", document["filename"])
            gaps.append(item)
    if not periods:
        gaps.append({"code": "missing_vida_laboral", "message": "No Vida Laboral contribution periods available."})
    if not monthly_bases:
        gaps.append({"code": "missing_monthly_bases", "message": "No monthly contribution bases available."})
    gaps.extend(_missing_monthly_base_gaps(periods, monthly_bases))
    return _dedupe_gaps(gaps)


def _missing_monthly_base_gaps(
    periods: list[dict[str, Any]],
    monthly_bases: list[dict[str, Any]],
) -> list[dict[str, str]]:
    available = {base["month"] for base in monthly_bases}
    gaps: list[dict[str, str]] = []
    for period in periods:
        start = _date_from_iso(period["start_date"])
        end = _date_from_iso(period["end_date"]) if period.get("end_date") else start
        for month in _month_range(start, end):
            if month not in available:
                gaps.append(
                    {
                        "code": "missing_monthly_base",
                        "month": month,
                        "message": f"No documented contribution base for {month}.",
                    }
                )
    return gaps


def _extraction_status(
    documents: list[dict[str, Any]],
    periods: list[dict[str, Any]],
    monthly_bases: list[dict[str, Any]],
    data_gaps: list[dict[str, str]],
) -> str:
    if not any(document["status"] in {"extracted", "partial_extracted"} for document in documents):
        return "not_extracted"
    if periods and monthly_bases and not data_gaps:
        return "extracted"
    return "partial_extracted"


def _parsed_document(
    filename: str,
    status: str,
    document_type: str,
    periods: list[dict[str, Any]],
    monthly_bases: list[dict[str, Any]],
    data_gaps: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "filename": filename,
        "status": status,
        "document_type": document_type,
        "periods": periods,
        "monthly_bases": monthly_bases,
        "data_gaps": data_gaps,
    }


def _monthly_base(
    month: str,
    amount: Decimal,
    filename: str,
    source_type: str,
    confidence: str,
    employer: str | None = None,
) -> dict[str, Any]:
    record = {
        "month": month,
        "base_amount": f"{amount:.2f}",
        "currency": "EUR",
        "source_document": filename,
        "source_type": source_type,
        "confidence": confidence,
    }
    if employer:
        record["employer"] = employer
    return record


def _parse_month(year: str, month: str, period: str) -> str | None:
    if year and month:
        try:
            return f"{int(year):04d}-{int(month):02d}"
        except ValueError:
            return None
    value = period.strip().upper()
    match = re.match(r"(?P<month>\d{2})/(?P<year>\d{4})$", value)
    if match:
        return f"{match.group('year')}-{match.group('month')}"
    match = re.match(r"(?P<year>\d{4})-(?P<month>\d{2})$", value)
    if match:
        return value
    match = re.match(r"(?P<name>[A-Z]+)(?:\s+DE)?\s+(?P<year>\d{4})$", value)
    if match:
        month_number = _SPANISH_MONTHS.get(match.group("name"))
        if month_number:
            return f"{match.group('year')}-{month_number:02d}"
    return None


def _parse_decimal(value: str) -> Decimal | None:
    cleaned = value.strip().replace(" ", "")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _date_from_spanish(value: str) -> str:
    separator = "/" if "/" in value else "."
    day, month, year = value.split(separator)
    return f"{year}-{month}-{day}"


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


def _dedupe_periods(periods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _dedupe_records(periods, ("start_date", "end_date", "regime", "employer", "contribution_days"))


def _dedupe_monthly_bases(monthly_bases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _dedupe_records(monthly_bases, ("month", "base_amount", "source_type"))


def _dedupe_records(records: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    output: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: tuple(str(item.get(key, "")) for key in keys)):
        identity = tuple(record.get(key) for key in keys)
        if identity in seen:
            continue
        seen.add(identity)
        output.append(record)
    return output


def _dedupe_gaps(gaps: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[tuple[str, str], ...]] = set()
    output: list[dict[str, str]] = []
    for gap in gaps:
        identity = tuple(sorted((key, str(value)) for key, value in gap.items()))
        if identity in seen:
            continue
        seen.add(identity)
        output.append(gap)
    return output


def _flatten(groups: Any) -> list[Any]:
    output: list[Any] = []
    for group in groups:
        output.extend(group)
    return output


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\xa0", " "))


def _ascii_fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _ascii_fold(value).strip().lower()).strip("_")


def _squash_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _space_embedded_dates(value: str) -> str:
    return re.sub(r"([A-Z,])(\d{2}[./]\d{2}[./]\d{4})", r"\1 \2", value)


_SPANISH_MONTHS = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "SETIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}
