import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.ingestion.inps_pension import (
    InpsPensionImportError,
    import_inps_pension,
    parse_inps_pension_text,
)


SIMULATION_TEXT = """
Codice Fiscale: SYNTHETIC_TEST_ID
Data elaborazione: 09/07/2026
Previsione della tua pensione nel sistema contributivo
Pensione di vecchiaia
Data di pensionamento 01/05/2039
Importo pensione mensile lordo EUR 3.562,00
Ultima retribuzione/reddito lorda/o stimata1 EUR 8.583,00
Tasso di sostituzione lordo2 41.50 %
All'importo della pensione e' stata aggiunta la quota relativa alla contribuzione versata nella Gestione Separata di EUR 446,00
Gli importi sono espressi in prezzi 2026
Fondo proiezione: Lavoro dipendente (FPLD)
"""

CURRENT_POSITION_TEXT = """
Codice Fiscale: SYNTHETIC_TEST_ID
Data elaborazione: 09/07/2026
367 settimane Contributi utili ai fini della pensione:
533 settimane Contributi utili in Gestione Separata:
Estratto Conto
"""


class InpsPensionTest(unittest.TestCase):
    def test_parse_simulation_text_extracts_projection(self):
        result = parse_inps_pension_text(SIMULATION_TEXT)

        self.assertEqual(result["status"], "inps_extracted")
        self.assertEqual(result["document_type"], "pension_simulation_summary")
        self.assertEqual(result["projection"]["retirement_date"], "2039-05-01")
        self.assertEqual(result["projection"]["monthly_gross_pension"], "3562.00")
        self.assertEqual(result["projection"]["gross_replacement_rate"], "41.50")
        self.assertEqual(result["projection"]["prices_year"], "2026")

    def test_parse_current_position_extracts_weeks(self):
        result = parse_inps_pension_text(CURRENT_POSITION_TEXT)

        self.assertEqual(result["status"], "inps_extracted")
        self.assertEqual(result["document_type"], "current_contribution_position")
        self.assertEqual(result["contribution_position"]["pension_contribution_weeks"], "367")
        self.assertEqual(result["contribution_position"]["separate_management_weeks"], "533")

    def test_parse_non_inps_text_is_not_recognized(self):
        result = parse_inps_pension_text("Sintesi Posizione Individuale Fon.Te")

        self.assertEqual(result["status"], "not_inps_pension")

    def test_import_writes_snapshot_from_pdf_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "pensione"
            input_dir.mkdir()
            simulation_pdf = input_dir / "riepilogo.pdf"
            current_pdf = input_dir / "situazione.pdf"
            simulation_pdf.write_text("placeholder", encoding="utf-8")
            current_pdf.write_text("placeholder", encoding="utf-8")
            output_path = root / "snapshots" / "inps-pension.snapshot.json"

            with patch(
                "family_office_engine.ingestion.inps_pension._extract_pdf_text",
                side_effect=[SIMULATION_TEXT, CURRENT_POSITION_TEXT],
            ):
                result = import_inps_pension(input_dir, output_path)

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(result["schema_version"], "inps-pension/v1")
            self.assertEqual(written["record_type"], "InpsPensionSnapshot")
            self.assertEqual(written["extraction_status"], "extracted")
            self.assertEqual(written["projection"]["monthly_gross_pension"], "3562.00")
            self.assertEqual(written["contribution_position"]["pension_contribution_weeks"], "367")

    def test_import_rejects_missing_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            with self.assertRaisesRegex(InpsPensionImportError, "directory not found"):
                import_inps_pension(root / "missing", root / "snapshot.json")


if __name__ == "__main__":
    unittest.main()
