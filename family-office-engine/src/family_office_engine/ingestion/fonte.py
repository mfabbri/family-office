import csv
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

SCHEMA_VERSION = "fonte-statement/v1"
SOURCE_BUNDLE_SCHEMA_VERSION = "fonte-source-bundle/v1"

REQUIRED_COLUMNS = ("date", "description", "amount", "category")
XLSX_REQUIRED_COLUMNS = ("periodo", "anno", "totale", "aderente", "azienda", "tfr")

XLSX_COLUMN_MAP = {
    "Periodo": "periodo",
    "Anno": "anno",
    "Totale": "totale",
    "Ragione sociale": "ragione_sociale",
    "Aderente": "aderente",
    "Azienda": "azienda",
    "TFR": "tfr",
    "Volontario Aderente": "volontario_aderente",
    "Iscrizione aderente": "iscrizione_aderente",
    "Iscrizione azienda": "iscrizione_azienda",
    "TFR Silente": "tfr_silente",
    "Welfare": "welfare",
    "Premio di Produzione": "premio_di_produzione",
    "Trasf./Reintegro": "trasf_reintegro",
    "Stato Contributo": "stato_contributo",
    "Tipologia": "tipologia",
}

DECIMAL_XLSX_COLUMNS = {
    "totale",
    "aderente",
    "azienda",
    "tfr",
    "volontario_aderente",
    "iscrizione_aderente",
    "iscrizione_azienda",
    "tfr_silente",
    "welfare",
    "premio_di_produzione",
    "trasf_reintegro",
}

XML_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

SUPPORTED_CATEGORIES = {
    "employee_contribution",
    "employer_contribution",
    "tfr_contribution",
    "fee",
    "return",
    "balance",
}


class FonteImportError(ValueError):
    pass


@dataclass(frozen=True)
class FonteEntry:
    date: str
    description: str
    amount: str
    category: str

    def to_record(self) -> dict[str, str]:
        return {
            "date": self.date,
            "description": self.description,
            "amount": self.amount,
            "category": self.category,
        }


def import_fonte(input_path: Path, output_path: Path) -> dict[str, Any]:
    entries = load_fonte(input_path)
    normalized = normalize_fonte(entries, input_path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(normalized, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise FonteImportError(f"Cannot write output snapshot: {output_path}") from exc
    return normalized


def import_fonte_source_bundle(
    position_pdf_path: Path,
    contributions_xlsx_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    _validate_source_file(position_pdf_path, ".pdf", "position_pdf")
    _validate_source_file(contributions_xlsx_path, ".xlsx", "contributions_xlsx")
    contributions = load_fonte_contributions_xlsx(contributions_xlsx_path)
    position = load_fonte_position_pdf(position_pdf_path)
    normalized = {
        "schema_version": SOURCE_BUNDLE_SCHEMA_VERSION,
        "record_type": "FonTeSourceBundle",
        "source": {
            "type": "fonte-pdf-xlsx",
            "documents": {
                "position_pdf": str(position_pdf_path),
                "contributions_xlsx": str(contributions_xlsx_path),
            },
        },
        "extraction_status": "pdf_xlsx_extracted",
        "pdf_extraction_status": "extracted",
        "position": position,
        "contributions": contributions,
        "notes": "Fon.Te PDF position and XLSX contributions extracted.",
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(normalized, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise FonteImportError(f"Cannot write output snapshot: {output_path}") from exc
    return normalized


def load_fonte_contributions_xlsx(input_path: Path) -> list[dict[str, str]]:
    _validate_source_file(input_path, ".xlsx", "contributions_xlsx")
    rows = _read_first_xlsx_sheet(input_path)
    if not rows:
        raise FonteImportError("Fon.Te XLSX contains no rows")

    headers = [_normalize_xlsx_header(value) for value in rows[0]]
    missing_columns = [name for name in XLSX_REQUIRED_COLUMNS if name not in headers]
    if missing_columns:
        raise FonteImportError(f"Missing required XLSX columns: {', '.join(missing_columns)}")

    entries: list[dict[str, str]] = []
    for index, row in enumerate(rows[1:], start=2):
        if not any(value.strip() for value in row):
            continue
        padded = row + [""] * (len(headers) - len(row))
        raw_entry = dict(zip(headers, padded))
        entries.append(_normalize_xlsx_entry(raw_entry, index))

    if not entries:
        raise FonteImportError("Fon.Te XLSX contains no contribution rows")
    return entries


def load_fonte_position_pdf(input_path: Path) -> dict[str, Any]:
    _validate_source_file(input_path, ".pdf", "position_pdf")
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise FonteImportError("PyPDF2 is required to extract Fon.Te PDF text") from exc

    try:
        reader = PdfReader(str(input_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # PyPDF2 exposes several parser-specific exceptions.
        raise FonteImportError(f"Cannot extract text from Fon.Te PDF: {input_path}") from exc

    return parse_fonte_position_text(text)


def parse_fonte_position_text(text: str) -> dict[str, Any]:
    position_match = re.search(
        r"Posizione individuale al\s+(\d{2}/\d{2}/\d{4})\s+([\d.]+,\d{2})",
        text,
        flags=re.IGNORECASE,
    )
    if not position_match:
        raise FonteImportError("Cannot find Fon.Te position value in PDF text")

    pending_match = re.search(
        r"Importo in attesa di investimento\s+([\d.]+,\d{2})",
        text,
        flags=re.IGNORECASE,
    )

    holdings = _parse_position_holdings(text)
    return {
        "statement_date": _normalize_italian_date(position_match.group(1)),
        "position_value": _normalize_italian_decimal(position_match.group(2), "0.01"),
        "pending_investment": (
            _normalize_italian_decimal(pending_match.group(1), "0.01")
            if pending_match
            else "0.00"
        ),
        "holdings": holdings,
    }


def load_fonte(input_path: Path) -> list[FonteEntry]:
    if not input_path.exists():
        raise FonteImportError(f"Fon.Te file not found: {input_path}")
    if input_path.suffix.lower() == ".pdf":
        raise FonteImportError("Fon.Te PDF import is not supported yet; provide CSV")
    if input_path.suffix.lower() != ".csv":
        raise FonteImportError("Fon.Te import supports CSV input only")

    text = input_path.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;")
    except csv.Error:
        dialect = csv.excel

    rows = list(csv.DictReader(text.splitlines(), dialect=dialect))
    if not rows:
        raise FonteImportError("Fon.Te CSV contains no data rows")

    fieldnames = rows[0].keys()
    missing_columns = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
    if missing_columns:
        raise FonteImportError(f"Missing required columns: {', '.join(missing_columns)}")

    entries = [_parse_row(row, index + 2) for index, row in enumerate(rows)]
    return entries


def normalize_fonte(entries: list[FonteEntry], source_path: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "FonTeStatement",
        "source": {
            "type": "fonte-csv",
            "path": str(source_path),
        },
        "entries": [entry.to_record() for entry in entries],
    }


def _parse_row(row: dict[str, str], line_number: int) -> FonteEntry:
    row_date = _require(row, "date", line_number)
    try:
        date.fromisoformat(row_date)
    except ValueError as exc:
        raise FonteImportError(f"Invalid date at line {line_number}: {row_date}") from exc

    description = _require(row, "description", line_number)
    category = _require(row, "category", line_number)
    if category not in SUPPORTED_CATEGORIES:
        raise FonteImportError(f"Unsupported category at line {line_number}: {category}")

    amount = _normalize_amount(_require(row, "amount", line_number), line_number)
    return FonteEntry(
        date=row_date,
        description=description,
        amount=amount,
        category=category,
    )


def _require(row: dict[str, str], field: str, line_number: int) -> str:
    value = row.get(field, "")
    if value is None or not value.strip():
        raise FonteImportError(f"Missing value for {field} at line {line_number}")
    return value.strip()


def _normalize_amount(value: str, line_number: int) -> str:
    normalized = value.strip().replace(" ", "")
    if "," in normalized and "." not in normalized:
        normalized = normalized.replace(",", ".")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise FonteImportError(f"Invalid amount at line {line_number}: {value}") from exc
    return str(amount.quantize(Decimal("0.01")))


def _normalize_italian_decimal(value: str, quantize: str) -> str:
    normalized = value.strip().replace(".", "").replace(",", ".")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise FonteImportError(f"Invalid Italian decimal value: {value}") from exc
    return str(amount.quantize(Decimal(quantize)))


def _normalize_italian_date(value: str) -> str:
    day, month, year = value.split("/")
    return f"{year}-{month}-{day}"


def _parse_position_holdings(text: str) -> list[dict[str, str]]:
    holdings: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        match = re.match(
            r"^([A-Z][A-Z ]+)\s+([\d.]+,\d{3})\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})",
            line,
        )
        if not match:
            continue
        holdings.append(
            {
                "comparto": match.group(1).strip(),
                "quote": _normalize_italian_decimal(match.group(2), "0.001"),
                "valore_quota": _normalize_italian_decimal(match.group(3), "0.01"),
                "controvalore": _normalize_italian_decimal(match.group(4), "0.01"),
            }
        )
    return holdings


def _validate_source_file(path: Path, expected_suffix: str, source_name: str) -> None:
    if not path.exists():
        raise FonteImportError(f"Fon.Te {source_name} not found: {path}")
    if path.suffix.lower() != expected_suffix:
        raise FonteImportError(
            f"Fon.Te {source_name} must be {expected_suffix}: {path}"
        )


def _read_first_xlsx_sheet(path: Path) -> list[list[str]]:
    try:
        with zipfile.ZipFile(path) as workbook:
            sheet_name = _first_sheet_name(workbook)
            shared_strings = _shared_strings(workbook)
            root = ElementTree.fromstring(workbook.read(sheet_name))
    except (KeyError, OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise FonteImportError(f"Invalid XLSX file: {path}") from exc

    rows: list[list[str]] = []
    for row in root.findall(".//x:sheetData/x:row", XML_NS):
        values: list[str] = []
        for cell in row.findall("x:c", XML_NS):
            column_index = _column_index(cell.attrib.get("r", ""))
            while len(values) < column_index:
                values.append("")
            values.append(_cell_value(cell, shared_strings))
        rows.append(values)
    return rows


def _first_sheet_name(workbook: zipfile.ZipFile) -> str:
    sheets = sorted(name for name in workbook.namelist() if name.startswith("xl/worksheets/sheet"))
    if not sheets:
        raise FonteImportError("XLSX workbook contains no worksheets")
    return sheets[0]


def _shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("x:si", XML_NS):
        parts = [text.text or "" for text in item.findall(".//x:t", XML_NS)]
        values.append("".join(parts))
    return values


def _cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        text = cell.find("x:is/x:t", XML_NS)
        return "" if text is None or text.text is None else text.text.strip()

    value = cell.find("x:v", XML_NS)
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        try:
            return shared_strings[int(value.text)].strip()
        except (IndexError, ValueError) as exc:
            raise FonteImportError("Invalid shared string reference in XLSX") from exc
    return value.text.strip()


def _column_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha()).upper()
    if not letters:
        return 0
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _normalize_xlsx_header(value: str) -> str:
    if value in XLSX_COLUMN_MAP:
        return XLSX_COLUMN_MAP[value]
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


def _normalize_xlsx_entry(entry: dict[str, str], line_number: int) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in entry.items():
        if key in DECIMAL_XLSX_COLUMNS:
            normalized[key] = _normalize_amount(value or "0", line_number)
        else:
            normalized[key] = value.strip()

    for key in XLSX_REQUIRED_COLUMNS:
        if not normalized.get(key):
            raise FonteImportError(f"Missing value for {key} at XLSX row {line_number}")

    try:
        int(normalized["periodo"])
        int(normalized["anno"])
    except ValueError as exc:
        raise FonteImportError(f"Invalid period/year at XLSX row {line_number}") from exc

    return normalized
