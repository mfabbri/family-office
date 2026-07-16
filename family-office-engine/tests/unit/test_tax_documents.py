import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.ingestion.tax_documents import (
    diagnose_tax_documents,
    import_tax_documents,
    parse_tax_document_text,
)


CU_TEXT = """
CERTIFICAZIONE UNICA2026
RELATIVA ALL'ANNO 2025
CERTIFICAZIONE LAVORO DIPENDENTE, ASSIMILATI ED ASSISTENZA FISCALE
Redditi di lavoro dipendente e assimilati
45.000,00
Ritenute Irpef 9.500,00
Addizionale regionale all'Irpef 500,00
"""

DECLARATION_TEXT = """
PERSONE FISICHE2025
Periodo d'imposta 2024
RN1 REDDITO COMPLESSIVO 45.000,00
RN5 IMPOSTA LORDA 9.500,00
RN26 IMPOSTA NETTA 8.100,00
RV1 ADDIZIONALE REGIONALE ALL'IRPEF 500,00
"""


class TaxDocumentsIngestionTest(unittest.TestCase):
    def test_parse_cu_text_extracts_years_and_fields(self):
        result = parse_tax_document_text(CU_TEXT, "cu.pdf", "cu")

        self.assertEqual(result["status"], "extracted")
        record = result["records"][0]
        self.assertEqual(record["document_type"], "certificazione_unica")
        self.assertEqual(record["fields"]["model_year"], "2026")
        self.assertEqual(record["fields"]["tax_year"], "2025")
        self.assertEqual(record["fields"]["employment_income"], "45000.00")
        self.assertEqual(record["fields"]["irpef_withheld"], "9500.00")

    def test_parse_cu_text_uses_model_year_minus_one_when_tax_year_label_is_noisy(self):
        noisy = """
CERTIFICAZIONE UNICA2026
RELATIVA ALLANNO
numero prefisso
7000580/0000006
2025
"""

        result = parse_tax_document_text(noisy, "cu.pdf", "cu")

        self.assertEqual(result["records"][0]["fields"]["model_year"], "2026")
        self.assertEqual(result["records"][0]["fields"]["tax_year"], "2025")

    def test_parse_cu_text_rejects_implausible_tax_year_near_label(self):
        noisy = """
CERTIFICAZIONE UNICA2026
RELATIVA ALLANNO 7000
"""

        result = parse_tax_document_text(noisy, "cu.pdf", "cu")

        self.assertEqual(result["records"][0]["fields"]["model_year"], "2026")
        self.assertEqual(result["records"][0]["fields"]["tax_year"], "2025")

    def test_parse_declaration_text_extracts_years_and_fields(self):
        result = parse_tax_document_text(DECLARATION_TEXT, "redditi.pdf", "declaration")

        self.assertEqual(result["status"], "extracted")
        record = result["records"][0]
        self.assertEqual(record["document_type"], "dichiarazione_redditi_pf")
        self.assertEqual(record["fields"]["model_year"], "2025")
        self.assertEqual(record["fields"]["tax_year"], "2024")
        self.assertEqual(record["fields"]["total_income"], "45000.00")
        self.assertEqual(record["fields"]["net_tax"], "8100.00")

    def test_parse_tax_document_text_reports_unsupported_document(self):
        result = parse_tax_document_text("unrelated document", "note.pdf", "cu")

        self.assertEqual(result["status"], "unsupported_tax_document")
        self.assertEqual(result["records"], [])
        self.assertEqual(result["data_gaps"][0]["code"], "unsupported_tax_document")

    def test_import_tax_documents_writes_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            cu_dir = root / "cu"
            declarations_dir = root / "dichiarazioni"
            output_path = root / "tax-documents.snapshot.json"
            cu_dir.mkdir()
            declarations_dir.mkdir()
            (cu_dir / "cu.pdf").write_text("placeholder", encoding="utf-8")
            (declarations_dir / "redditi.pdf").write_text("placeholder", encoding="utf-8")

            def extract(path: Path) -> str:
                return CU_TEXT if path.name == "cu.pdf" else DECLARATION_TEXT

            with patch("family_office_engine.ingestion.tax_documents._extract_pdf_text", side_effect=extract):
                result = import_tax_documents(cu_dir, declarations_dir, output_path)

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(result["schema_version"], "tax-documents/v1")
            self.assertEqual(written["record_type"], "TaxDocumentsSnapshot")
            self.assertEqual(written["extraction_status"], "extracted")
            self.assertEqual(written["summary"]["record_count"], 2)
            self.assertEqual(written["summary"]["document_types"]["certificazione_unica"], 1)

    def test_diagnose_tax_documents_reports_missing_directories(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            result = diagnose_tax_documents(root / "missing-cu", root / "missing-declarations")

            self.assertEqual(result["status"], "not_extracted")
            self.assertEqual(result["summary"]["document_count"], 2)
            self.assertEqual(result["summary"]["gap_codes"]["missing_input_directory"], 2)


if __name__ == "__main__":
    unittest.main()
