import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.ingestion.spanish_pension import (
    SpanishPensionImportError,
    import_spanish_pension,
    parse_spanish_pension_text,
)


VIDA_LABORAL_TEXT = """
TESORERIA GENERAL DE LA SEGURIDAD SOCIAL
INFORME DE VIDA LABORAL
ha figurado en situacion de alta en el Sistema de la Seguridad Social durante un total de
10Anos
3.956 dias 10meses
0dias
REFERENCIAS ELECTRONICAS
Id. CEA: Fecha: Codigo CEA: Pagina:
ABC123 09/07/2026 XYZ 1
SITUACION/ES
"""


class SpanishPensionTest(unittest.TestCase):
    def test_parse_vida_laboral_extracts_contribution_history(self):
        result = parse_spanish_pension_text(VIDA_LABORAL_TEXT)

        self.assertEqual(result["status"], "spanish_pension_extracted")
        self.assertEqual(result["document_type"], "vida_laboral")
        self.assertEqual(result["contribution_history"]["report_date"], "2026-07-09")
        self.assertEqual(result["contribution_history"]["registered_years"], "10")
        self.assertEqual(result["contribution_history"]["registered_months"], "10")
        self.assertEqual(result["contribution_history"]["registered_residual_days"], "0")
        self.assertEqual(result["contribution_history"]["registered_total_days"], "3956")

    def test_parse_non_spanish_pension_text_is_not_recognized(self):
        result = parse_spanish_pension_text("Previsione della tua pensione INPS")

        self.assertEqual(result["status"], "not_spanish_pension")

    def test_import_writes_snapshot_from_pdf_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "pensione" / "spagna"
            input_dir.mkdir(parents=True)
            pdf_path = input_dir / "vida_laboral.pdf"
            pdf_path.write_text("placeholder", encoding="utf-8")
            output_path = root / "snapshots" / "spanish-pension.snapshot.json"

            with patch(
                "family_office_engine.ingestion.spanish_pension._extract_pdf_text",
                return_value=VIDA_LABORAL_TEXT,
            ):
                result = import_spanish_pension(input_dir, output_path)

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(result["schema_version"], "spanish-pension/v1")
            self.assertEqual(written["record_type"], "SpanishPensionSnapshot")
            self.assertEqual(written["extraction_status"], "extracted")
            self.assertEqual(written["contribution_history"]["registered_total_days"], "3956")

    def test_import_rejects_missing_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            with self.assertRaisesRegex(SpanishPensionImportError, "directory not found"):
                import_spanish_pension(root / "missing", root / "snapshot.json")


if __name__ == "__main__":
    unittest.main()
