import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.ingestion.payroll import (
    diagnose_payroll_input,
    import_payroll,
    parse_payroll_text,
)


PAYSLIP_TEXT = """
PERIODO DI RETRIBUZIONE
Gennaio 2026
000001 ACME SRL
Imp. IRPEF
3.000,00
IRPEF pagata
750,00
IRPEF lorda 800,00
Detrazioni lav.dip. 50,00
*Z00000 Contributo IVS 4.000,00 % 9,19000 367,60
NETTO DEL MESE
2.500,00 EUR
"""


class PayrollIngestionTest(unittest.TestCase):
    def test_parse_payroll_text_extracts_core_fields(self):
        result = parse_payroll_text(PAYSLIP_TEXT, "synthetic-payslip.pdf")

        self.assertEqual(result["status"], "extracted")
        record = result["records"][0]
        self.assertEqual(record["period_label"], "Gennaio 2026")
        self.assertEqual(record["period_year"], 2026)
        self.assertEqual(record["employer"], "ACME SRL")
        self.assertEqual(record["net_pay"], "2500.00")
        self.assertEqual(record["taxable_irpef"], "3000.00")
        self.assertEqual(record["irpef_withheld"], "750.00")
        self.assertIn(
            {
                "code": "irpef_withheld",
                "amount": "750.00",
                "currency": "EUR",
            },
            record["withholding_items"],
        )

    def test_import_payroll_writes_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "buste-paga"
            output_path = root / "payroll.snapshot.json"
            input_dir.mkdir()
            (input_dir / "synthetic-payslip.pdf").write_text("placeholder", encoding="utf-8")

            with patch(
                "family_office_engine.ingestion.payroll._extract_pdf_text",
                return_value=PAYSLIP_TEXT,
            ):
                result = import_payroll(input_dir, output_path)

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(result["schema_version"], "payroll/v1")
            self.assertEqual(written["record_type"], "PayrollSnapshot")
            self.assertEqual(written["extraction_status"], "extracted")
            self.assertEqual(written["summary"]["record_count"], 1)
            self.assertEqual(written["summary"]["net_pay_total"], "2500.00")

    def test_diagnose_payroll_input_reports_counts_without_amounts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "buste-paga"
            input_dir.mkdir()
            (input_dir / "synthetic-payslip.pdf").write_text("placeholder", encoding="utf-8")

            with patch(
                "family_office_engine.ingestion.payroll._extract_pdf_text",
                return_value=PAYSLIP_TEXT,
            ):
                result = diagnose_payroll_input(input_dir)

            self.assertEqual(result["schema_version"], "payroll-diagnostics/v1")
            self.assertEqual(result["status"], "extracted")
            self.assertEqual(result["summary"]["document_count"], 1)
            self.assertEqual(result["summary"]["record_count"], 1)
            self.assertEqual(result["summary"]["data_gap_count"], 0)
            self.assertEqual(result["documents"][0]["filename"], "synthetic-payslip.pdf")
            self.assertNotIn("2500.00", json.dumps(result))

    def test_diagnose_payroll_input_reports_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = Path(tmp_dir) / "buste-paga"
            input_dir.mkdir()

            result = diagnose_payroll_input(input_dir)

            self.assertEqual(result["status"], "no_documents")
            self.assertEqual(result["summary"]["document_count"], 0)
            self.assertEqual(result["summary"]["gap_codes"], {"no_payroll_documents": 1})

    def test_parse_payroll_text_reports_unsupported_document(self):
        result = parse_payroll_text("unrelated document", "note.pdf")

        self.assertEqual(result["status"], "unsupported_format")
        self.assertEqual(result["records"], [])
        self.assertEqual(result["data_gaps"][0]["code"], "unsupported_payroll_document")


if __name__ == "__main__":
    unittest.main()
