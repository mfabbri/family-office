import csv
import html
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from family_office_engine.ingestion.fonte import (
    FonteImportError,
    import_fonte,
    import_fonte_source_bundle,
    load_fonte,
    load_fonte_contributions_xlsx,
    parse_fonte_position_text,
)


VALID_ROWS = [
    {
        "date": "2026-01-31",
        "description": "Employee monthly contribution",
        "amount": "250.00",
        "category": "employee_contribution",
    },
    {
        "date": "2026-01-31",
        "description": "Statement balance",
        "amount": "10000.00",
        "category": "balance",
    },
]


class FonteImportTest(unittest.TestCase):
    def test_load_fonte_accepts_valid_csv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = _write_csv(Path(tmp_dir) / "fonte.csv", VALID_ROWS)

            entries = load_fonte(input_path)

            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0].amount, "250.00")

    def test_load_fonte_rejects_missing_columns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "fonte.csv"
            input_path.write_text("date,amount\n2026-01-31,10.00\n", encoding="utf-8")

            with self.assertRaisesRegex(FonteImportError, "Missing required columns"):
                load_fonte(input_path)

    def test_load_fonte_rejects_invalid_amount(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            rows = [dict(VALID_ROWS[0], amount="not-a-number")]
            input_path = _write_csv(Path(tmp_dir) / "fonte.csv", rows)

            with self.assertRaisesRegex(FonteImportError, "Invalid amount"):
                load_fonte(input_path)

    def test_load_fonte_rejects_pdf(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "fonte.pdf"
            input_path.write_text("fake pdf", encoding="utf-8")

            with self.assertRaisesRegex(FonteImportError, "PDF import is not supported"):
                load_fonte(input_path)

    def test_import_fonte_writes_normalized_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = _write_csv(root / "fonte.csv", VALID_ROWS)
            output_path = root / "snapshots" / "fonte.snapshot.json"

            result = import_fonte(input_path, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "fonte-statement/v1")
            self.assertEqual(written["record_type"], "FonTeStatement")
            self.assertEqual(written["entries"][1]["category"], "balance")

    def test_import_fonte_source_bundle_registers_pdf_and_xlsx(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            position_pdf = root / "posizione-generale.pdf"
            contributions_xlsx = root / "importi-versati.xlsx"
            output_path = root / "snapshots" / "fonte-source.snapshot.json"
            position_pdf.write_text("synthetic pdf placeholder", encoding="utf-8")
            _write_xlsx(contributions_xlsx, _xlsx_rows())

            with patch(
                "family_office_engine.ingestion.fonte.load_fonte_position_pdf",
                return_value=_position_record(),
            ):
                result = import_fonte_source_bundle(position_pdf, contributions_xlsx, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "fonte-source-bundle/v1")
            self.assertEqual(written["record_type"], "FonTeSourceBundle")
            self.assertEqual(written["extraction_status"], "pdf_xlsx_extracted")
            self.assertEqual(written["pdf_extraction_status"], "extracted")
            self.assertEqual(written["position"]["position_value"], "44243.42")
            self.assertEqual(written["contributions"][0]["totale"], "2049.16")

    def test_import_fonte_source_bundle_requires_xlsx(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            position_pdf = root / "posizione-generale.pdf"
            contributions_csv = root / "importi-versati.csv"
            output_path = root / "fonte-source.snapshot.json"
            position_pdf.write_text("synthetic pdf placeholder", encoding="utf-8")
            contributions_csv.write_text("not xlsx", encoding="utf-8")

            with self.assertRaisesRegex(FonteImportError, "contributions_xlsx must be .xlsx"):
                import_fonte_source_bundle(position_pdf, contributions_csv, output_path)

    def test_load_fonte_contributions_xlsx_accepts_valid_workbook(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = _write_xlsx(Path(tmp_dir) / "importi-versati.xlsx", _xlsx_rows())

            entries = load_fonte_contributions_xlsx(input_path)

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["periodo"], "1")
            self.assertEqual(entries[0]["tfr"], "1351.48")

    def test_load_fonte_contributions_xlsx_rejects_missing_columns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = _write_xlsx(
                Path(tmp_dir) / "importi-versati.xlsx",
                [["Periodo", "Anno", "Totale"], ["1", "2026", "10.00"]],
            )

            with self.assertRaisesRegex(FonteImportError, "Missing required XLSX columns"):
                load_fonte_contributions_xlsx(input_path)

    def test_parse_fonte_position_text_extracts_position(self):
        text = "\n".join(
            [
                "Sintesi Posizione Individuale",
                "Comparto Quote in essere Valore quota Controvalore Composizione per strumenti finanziari",
                "CRESCITA 2.060,133 21,48 44.243,42 EUR",
                "Importo in attesa di investimento 0,00 EUR",
                "Posizione individuale al 08/07/2026 44.243,42 EUR",
            ]
        )

        result = parse_fonte_position_text(text)

        self.assertEqual(result["statement_date"], "2026-07-08")
        self.assertEqual(result["position_value"], "44243.42")
        self.assertEqual(result["pending_investment"], "0.00")
        self.assertEqual(result["holdings"][0]["quote"], "2060.133")

    def test_parse_fonte_position_text_rejects_missing_position(self):
        with self.assertRaisesRegex(FonteImportError, "position value"):
            parse_fonte_position_text("Sintesi Posizione Individuale")


def _write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["date", "description", "amount", "category"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def _xlsx_rows() -> list[list[str]]:
    return [
        [
            "Periodo",
            "Anno",
            "Totale",
            "Ragione sociale",
            "Aderente",
            "Azienda",
            "TFR",
            "Volontario Aderente",
            "Iscrizione aderente",
            "Iscrizione azienda",
            "TFR Silente",
            "Welfare",
            "Premio di Produzione",
            "Trasf./Reintegro",
            "Stato Contributo",
            "Tipologia",
        ],
        [
            "1",
            "2026",
            "2049.16",
            "SYNTHETIC SRL",
            "393.06",
            "304.62",
            "1351.48",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "Quotato",
            "Contributo",
        ],
    ]


def _write_xlsx(path: Path, rows: list[list[str]]) -> Path:
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row):
            cell_ref = f"{_column_name(column_index)}{row_index}"
            cells.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t>{html.escape(value)}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        "</worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
        "</sheets></workbook>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return path


def _position_record() -> dict[str, object]:
    return {
        "statement_date": "2026-07-08",
        "position_value": "44243.42",
        "pending_investment": "0.00",
        "holdings": [
            {
                "comparto": "CRESCITA",
                "quote": "2060.133",
                "valore_quota": "21.48",
                "controvalore": "44243.42",
            }
        ],
    }


def _column_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name


if __name__ == "__main__":
    unittest.main()
