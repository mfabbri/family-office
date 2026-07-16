import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.ingestion.bank_insurance import (
    BankInsuranceImportError,
    import_bank_insurance,
    parse_bank_insurance_text,
)


GENERALI_TEXT = """
Generali Italia S.p.A
V. Pensione (FIP3)
Deducibilita fiscale dei contributi 2025 per la dichiarazione dei redditi 2026
Dichiariamo che nel 2025 i contributi complessivi versati sono pari a EUR 2.802,58 cosi suddivisi:
Contributi versati dal Contraente EUR 2.802,58
"""


class BankInsuranceTest(unittest.TestCase):
    def test_parse_generali_contributions(self):
        result = parse_bank_insurance_text(GENERALI_TEXT, "insurance", "generali.pdf")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["provider"], "Generali")
        self.assertEqual(result["items"][0]["amount"], "2802.58")
        self.assertEqual(result["items"][0]["period_year"], "2025")

    def test_parse_unsupported_document_reports_gap(self):
        result = parse_bank_insurance_text("Documento non riconosciuto", "bank", "certificado.pdf")

        self.assertEqual(result["status"], "unsupported_format")
        self.assertEqual(result["data_gaps"][0]["code"], "unsupported_bank_insurance_document")

    def test_import_writes_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            bank_dir = root / "documents" / "banca"
            insurance_dir = root / "documents" / "polizze"
            bank_dir.mkdir(parents=True)
            insurance_dir.mkdir(parents=True)
            (bank_dir / "saldo.pdf").write_text("placeholder", encoding="utf-8")
            (insurance_dir / "generali.pdf").write_text("placeholder", encoding="utf-8")
            output_path = root / "snapshots" / "bank-insurance.snapshot.json"

            with patch(
                "family_office_engine.ingestion.bank_insurance._extract_pdf_text",
                side_effect=["", GENERALI_TEXT],
            ):
                result = import_bank_insurance(bank_dir, insurance_dir, output_path)

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(result["schema_version"], "bank-insurance/v1")
            self.assertEqual(written["record_type"], "BankInsuranceSnapshot")
            self.assertEqual(len(written["items"]), 1)
            self.assertEqual(len(written["data_gaps"]), 1)

    def test_import_rejects_missing_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            insurance_dir = root / "polizze"
            insurance_dir.mkdir()

            with self.assertRaisesRegex(BankInsuranceImportError, "directory not found"):
                import_bank_insurance(root / "missing", insurance_dir, root / "snapshot.json")


if __name__ == "__main__":
    unittest.main()
