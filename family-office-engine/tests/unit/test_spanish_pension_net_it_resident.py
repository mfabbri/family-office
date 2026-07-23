import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.spanish_pension_net_it_resident import (
    SpanishPensionNetItResidentError,
    build_spanish_pension_net_it_resident,
    load_spanish_pension_net_it_resident_rule_pack,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "cross-border" / "spanish-pension-net-it-resident.json"
IRPEF_RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "italy" / "2026" / "irpef-national.json"
SAMPLE_INPUT = REPOSITORY_ROOT / "family-office-engine" / "examples" / "spanish-pension-net-it-resident-input-sample.json"
SAMPLE_PENSION_INCOME = REPOSITORY_ROOT / "family-office-engine" / "examples" / "it-es-pension-income-sample.json"
SAMPLE_CLASSIFICATION = REPOSITORY_ROOT / "family-office-engine" / "examples" / "spanish-pension-net-it-es-classification-sample.json"


class SpanishPensionNetItResidentTest(unittest.TestCase):
    def test_builds_net_private_spanish_pension_taxed_in_italy_without_spanish_withholding(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "spanish-pension-net.snapshot.json"

            result = build_spanish_pension_net_it_resident(
                SAMPLE_INPUT,
                SAMPLE_PENSION_INCOME,
                SAMPLE_CLASSIFICATION,
                RULE_PACK,
                IRPEF_RULE_PACK,
                output_path,
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "spanish-pension-net-it-resident/v1")
            self.assertEqual(written["status"], "complete")
            stream = next(item for item in written["streams"] if item["stream_id"] == "spanish_public_pension")
            self.assertTrue(stream["italian_tax"]["taxable_in_italy"])
            self.assertEqual(stream["italian_tax"]["gross_irpef_before_pension"], "7140.00")
            self.assertEqual(stream["italian_tax"]["gross_irpef_after_pension"], "14570.00")
            self.assertEqual(stream["italian_tax"]["incremental_tax_on_pension"], "7430.00")
            self.assertEqual(stream["foreign_tax_credit"]["amount"], "0.00")
            self.assertEqual(stream["net"]["annual_amount"], "13570.00")
            self.assertEqual(
                written["rule_pack"]["source_refs"][0]["source_id"],
                "agenziaentrate.precompilata.lavoro-pensioni-esteri-2026",
            )

    def test_keeps_source_state_public_pension_out_of_italian_tax(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "spanish-pension-net.snapshot.json"

            result = build_spanish_pension_net_it_resident(
                SAMPLE_INPUT,
                SAMPLE_PENSION_INCOME,
                SAMPLE_CLASSIFICATION,
                RULE_PACK,
                IRPEF_RULE_PACK,
                output_path,
            )
            stream = next(item for item in result["streams"] if item["stream_id"] == "spanish_civil_service_pension")

            self.assertFalse(stream["italian_tax"]["taxable_in_italy"])
            self.assertEqual(stream["italian_tax"]["incremental_tax_on_pension"], "0.00")
            self.assertEqual(stream["spanish_tax"]["withheld"], "1800.00")
            self.assertEqual(stream["net"]["annual_amount"], "10800.00")

    def test_applies_definitive_foreign_tax_credit_when_declared_and_capient(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "spanish-pension-net.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["streams"][0]["spanish_tax_withheld"] = "1000.00"
            data["streams"][0]["spanish_tax_definitive"] = True
            data["streams"][0]["foreign_tax_credit_applicable"] = True
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_spanish_pension_net_it_resident(
                input_path,
                SAMPLE_PENSION_INCOME,
                SAMPLE_CLASSIFICATION,
                RULE_PACK,
                IRPEF_RULE_PACK,
                output_path,
            )
            stream = next(item for item in result["streams"] if item["stream_id"] == "spanish_public_pension")

            self.assertEqual(stream["foreign_tax_credit"]["status"], "applied")
            self.assertEqual(stream["foreign_tax_credit"]["amount"], "1000.00")
            self.assertEqual(stream["net"]["annual_amount"], "13570.00")

    def test_limits_foreign_tax_credit_when_declared_capacity_is_lower(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "spanish-pension-net.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["streams"][0]["spanish_tax_withheld"] = "8000.00"
            data["streams"][0]["spanish_tax_definitive"] = True
            data["streams"][0]["foreign_tax_credit_applicable"] = True
            data["streams"][0]["declared_credit_capacity"] = "3000.00"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_spanish_pension_net_it_resident(
                input_path,
                SAMPLE_PENSION_INCOME,
                SAMPLE_CLASSIFICATION,
                RULE_PACK,
                IRPEF_RULE_PACK,
                output_path,
            )
            stream = next(item for item in result["streams"] if item["stream_id"] == "spanish_public_pension")

            self.assertEqual(stream["foreign_tax_credit"]["amount"], "3000.00")
            self.assertEqual(stream["net"]["annual_amount"], "8570.00")

    def test_blocks_credit_for_non_definitive_spanish_tax(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "spanish-pension-net.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["streams"][0]["spanish_tax_withheld"] = "1000.00"
            data["streams"][0]["spanish_tax_definitive"] = False
            data["streams"][0]["foreign_tax_credit_applicable"] = True
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_spanish_pension_net_it_resident(
                input_path,
                SAMPLE_PENSION_INCOME,
                SAMPLE_CLASSIFICATION,
                RULE_PACK,
                IRPEF_RULE_PACK,
                output_path,
            )
            stream = next(item for item in result["streams"] if item["stream_id"] == "spanish_public_pension")

            self.assertEqual(result["status"], "partial")
            self.assertEqual(stream["foreign_tax_credit"]["status"], "blocked_not_definitive_or_not_applicable")
            self.assertIn("foreign_tax_credit_not_supported_by_input", {gap["code"] for gap in stream["data_gaps"]})

    def test_blocks_when_classification_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            classification_path = root / "classification.json"
            output_path = root / "spanish-pension-net.snapshot.json"
            classification = json.loads(SAMPLE_CLASSIFICATION.read_text(encoding="utf-8"))
            classification["classifications"] = []
            classification_path.write_text(json.dumps(classification), encoding="utf-8")

            result = build_spanish_pension_net_it_resident(
                SAMPLE_INPUT,
                SAMPLE_PENSION_INCOME,
                classification_path,
                RULE_PACK,
                IRPEF_RULE_PACK,
                output_path,
            )

            self.assertEqual(result["status"], "partial")
            self.assertIn("missing_or_blocked_tax_classification", {gap["code"] for item in result["streams"] for gap in item["data_gaps"]})

    def test_blocks_when_rule_year_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "spanish-pension-net.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["tax_year"] = 2027
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_spanish_pension_net_it_resident(
                input_path,
                SAMPLE_PENSION_INCOME,
                SAMPLE_CLASSIFICATION,
                RULE_PACK,
                IRPEF_RULE_PACK,
                output_path,
            )

            self.assertEqual(result["status"], "blocked_missing_rule")
            self.assertEqual(result["streams"], [])
            self.assertIn("net_rule_year_not_covered", {gap["code"] for gap in result["data_gaps"]})

    def test_load_rule_pack_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            rule_path = Path(tmp_dir) / "rules.json"
            rule_path.write_text(json.dumps({"schema_version": "wrong", "rules": []}), encoding="utf-8")

            with self.assertRaisesRegex(SpanishPensionNetItResidentError, "missing field"):
                load_spanish_pension_net_it_resident_rule_pack(rule_path)


if __name__ == "__main__":
    unittest.main()
