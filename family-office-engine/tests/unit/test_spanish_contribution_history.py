import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.ingestion.spanish_contribution_history import (
    SpanishContributionHistoryImportError,
    import_spanish_contribution_history,
    parse_spanish_contribution_csv,
    parse_spanish_contribution_text,
)


VIDA_LABORAL_TEXT = """
TESORERIA GENERAL DE LA SEGURIDAD SOCIAL
INFORME DE VIDA LABORAL
SITUACION/ES
REGIMEN GENERAL ACME SL 01/01/2024 31/03/2024 91
"""

BASES_TEXT = """
TESORERIA GENERAL DE LA SEGURIDAD SOCIAL
INFORME DE BASES DE COTIZACION
01/2024 Base de cotizacion 2.500,00
02/2024 Base de cotizacion 2.600,00
03/2024 Base de cotizacion 2.700,00
"""

NOMINA_TEXT = """
NOMINA
Periodo ENERO 2024
Base de cotizacion contingencias comunes 2.450,00
"""

OLD_PAYROLL_TEXT = """
EMPRESA (razon social)
SYNTHETIC EMPLOYER SA
PERIODO DEVENGADO
31-03-2017
DETERMINACION DE LAS BASES DE COTIZACION AL REG.GEN.DE LA SEG.SOC.
BASE TOTAL DE COTIZACION 3.840,01
3.945,73 CONTINGENCIAS COMUNES IMPORTE REMUNERACION MENSUAL
LIQUIDO TOTAL A PERCIBIR
"""

BASES_TABLE_TEXT = """
INFORME INTEGRAL DE BASES DE COTIZACION
Regimen: GENERAL Empresa/Razon Social: SYNTHETIC EMPLOYER S.A. CCC: 12345678901
Enero Febrero Marzo Abril Mayo Junio Julio Agosto Septiembre Octubre Noviembre Diciembre
2024 2.500,00 2.600,00 --- --- --- --- --- --- --- --- --- ---
"""

VIDA_LABORAL_MULTILINE_TEXT = """
INFORME DE VIDA LABORAL - SITUACIONES
SITUACION/ES
REGIMENEMPRESA
GENERAL 12345678901 SYNTHETIC EMPLOYER
SERVICES S01.07.2016 01.07.2016 15.05.2017 100 --- 02 319
"""


class SpanishContributionHistoryTest(unittest.TestCase):
    def test_parse_vida_laboral_extracts_periods(self):
        result = parse_spanish_contribution_text(VIDA_LABORAL_TEXT, "vida_laboral.txt")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["document_type"], "vida_laboral")
        self.assertEqual(result["periods"][0]["start_date"], "2024-01-01")
        self.assertEqual(result["periods"][0]["end_date"], "2024-03-31")
        self.assertEqual(result["periods"][0]["regime"], "REGIMEN GENERAL")
        self.assertEqual(result["periods"][0]["employer"], "ACME SL")
        self.assertEqual(result["periods"][0]["contribution_days"], 91)

    def test_parse_official_bases_text_extracts_monthly_bases(self):
        result = parse_spanish_contribution_text(BASES_TEXT, "bases.txt")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["document_type"], "official_bases")
        self.assertEqual(result["monthly_bases"][0]["month"], "2024-01")
        self.assertEqual(result["monthly_bases"][0]["base_amount"], "2500.00")
        self.assertEqual(result["monthly_bases"][0]["source_type"], "official_bases")
        self.assertEqual(result["monthly_bases"][0]["confidence"], "high")

    def test_parse_official_bases_table_extracts_monthly_bases(self):
        result = parse_spanish_contribution_text(BASES_TABLE_TEXT, "bases.pdf")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["document_type"], "official_bases")
        self.assertEqual(len(result["monthly_bases"]), 2)
        self.assertEqual(result["monthly_bases"][0]["month"], "2024-01")
        self.assertEqual(result["monthly_bases"][0]["employer"], "SYNTHETIC EMPLOYER S.A.")
        self.assertEqual(result["monthly_bases"][1]["base_amount"], "2600.00")

    def test_parse_vida_laboral_multiline_extracts_period(self):
        result = parse_spanish_contribution_text(VIDA_LABORAL_MULTILINE_TEXT, "vida_laboral.pdf")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["periods"][0]["start_date"], "2016-07-01")
        self.assertEqual(result["periods"][0]["end_date"], "2017-05-15")
        self.assertEqual(result["periods"][0]["contribution_days"], 319)

    def test_parse_official_bases_csv_extracts_monthly_bases(self):
        result = parse_spanish_contribution_csv(
            "year,month,base\n2024,1,\"2500,00\"\n",
            "bases.csv",
        )

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["monthly_bases"][0]["month"], "2024-01")
        self.assertEqual(result["monthly_bases"][0]["base_amount"], "2500.00")

    def test_parse_payroll_base_as_integrative_source(self):
        result = parse_spanish_contribution_text(NOMINA_TEXT, "nomina.txt")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["document_type"], "payroll")
        self.assertEqual(result["monthly_bases"][0]["month"], "2024-01")
        self.assertEqual(result["monthly_bases"][0]["base_amount"], "2450.00")
        self.assertEqual(result["monthly_bases"][0]["source_type"], "payroll")
        self.assertEqual(result["monthly_bases"][0]["confidence"], "medium")

    def test_parse_old_payroll_layout_as_integrative_source(self):
        result = parse_spanish_contribution_text(OLD_PAYROLL_TEXT, "old-payroll.pdf")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["document_type"], "payroll")
        self.assertEqual(result["monthly_bases"][0]["month"], "2017-03")
        self.assertEqual(result["monthly_bases"][0]["base_amount"], "3945.73")
        self.assertEqual(result["monthly_bases"][0]["source_type"], "payroll")

    def test_import_marks_missing_monthly_base_for_covered_period(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "pensione" / "spagna"
            input_dir.mkdir(parents=True)
            (input_dir / "vida_laboral.txt").write_text(VIDA_LABORAL_TEXT, encoding="utf-8")
            (input_dir / "bases.csv").write_text(
                "year,month,base\n2024,1,\"2500,00\"\n2024,3,\"2700,00\"\n",
                encoding="utf-8",
            )
            output_path = root / "snapshots" / "spanish-contribution-history.snapshot.json"

            result = import_spanish_contribution_history(input_dir, output_path)

            self.assertEqual(result["schema_version"], "spanish-contribution-history/v1")
            self.assertEqual(result["record_type"], "SpanishContributionHistorySnapshot")
            self.assertEqual(result["extraction_status"], "partial_extracted")
            self.assertIn(
                {"code": "missing_monthly_base", "month": "2024-02", "message": "No documented contribution base for 2024-02."},
                result["data_gaps"],
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["summary"]["period_count"], 1)

    def test_import_marks_duplicate_document(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "pensione" / "spagna"
            input_dir.mkdir(parents=True)
            (input_dir / "vida_laboral.txt").write_text(VIDA_LABORAL_TEXT, encoding="utf-8")
            (input_dir / "vida_laboral_copy.txt").write_text(VIDA_LABORAL_TEXT, encoding="utf-8")

            result = import_spanish_contribution_history(input_dir, root / "snapshot.json")

            duplicate = [document for document in result["documents"] if document["status"] == "duplicate_document"]
            self.assertEqual(len(duplicate), 1)
            self.assertEqual(duplicate[0]["duplicate_of"], "vida_laboral.txt")

    def test_import_marks_unreadable_pdf(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "pensione" / "spagna"
            input_dir.mkdir(parents=True)
            (input_dir / "scan.pdf").write_bytes(b"not a real pdf")

            with patch(
                "family_office_engine.ingestion.spanish_contribution_history._extract_pdf_text",
                side_effect=SpanishContributionHistoryImportError("Cannot extract text"),
            ):
                result = import_spanish_contribution_history(input_dir, root / "snapshot.json")

            self.assertEqual(result["extraction_status"], "not_extracted")
            self.assertEqual(result["documents"][0]["status"], "unreadable_document")
            self.assertIn("unreadable_document", {gap["code"] for gap in result["data_gaps"]})


if __name__ == "__main__":
    unittest.main()
