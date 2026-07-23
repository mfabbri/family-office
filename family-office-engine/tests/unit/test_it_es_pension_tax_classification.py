import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.it_es_pension_tax_classification import (
    ItEsPensionTaxClassificationError,
    classify_it_es_pension_tax,
    load_it_es_pension_tax_classification_rule_pack,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "cross-border" / "it-es-pension-tax-classification.json"
SAMPLE_INPUT = REPOSITORY_ROOT / "family-office-engine" / "examples" / "it-es-pension-tax-classification-input-sample.json"
SAMPLE_PENSION_INCOME = REPOSITORY_ROOT / "family-office-engine" / "examples" / "it-es-pension-income-sample.json"


class ItEsPensionTaxClassificationTest(unittest.TestCase):
    def test_classifies_spanish_private_pension_for_italian_resident_under_article_18(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "it-es-pension-tax-classification.snapshot.json"

            result = classify_it_es_pension_tax(SAMPLE_INPUT, SAMPLE_PENSION_INCOME, RULE_PACK, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "it-es-pension-tax-classification/v1")
            self.assertEqual(written["status"], "complete")
            item = next(entry for entry in written["classifications"] if entry["stream_id"] == "spanish_public_pension")
            self.assertEqual(item["classification_status"], "classified")
            self.assertEqual(item["treaty_article"], "18")
            self.assertEqual(item["taxing_power"]["country"], "IT")
            self.assertFalse(item["withholding"]["expected"])
            self.assertIn("fiscal_residence_certificate", item["required_documents"])
            self.assertEqual(
                written["rule_pack"]["source_refs"][0]["source_id"],
                "mef.def.convenzione-it-es.art18",
            )

    def test_classifies_public_pension_to_payer_state_without_residence_nationality_exception(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-pension-tax-classification.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["recipient"]["nationalities"] = ["ES"]
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = classify_it_es_pension_tax(input_path, SAMPLE_PENSION_INCOME, RULE_PACK, output_path)
            item = next(entry for entry in result["classifications"] if entry["stream_id"] == "spanish_civil_service_pension")

            self.assertEqual(item["treaty_article"], "19.2")
            self.assertEqual(item["taxing_power"]["country"], "ES")
            self.assertTrue(item["withholding"]["expected"])

    def test_public_pension_uses_residence_state_when_resident_is_national(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-pension-tax-classification.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["recipient"]["fiscal_residence"] = "IT"
            data["recipient"]["nationalities"] = ["IT", "ES"]
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = classify_it_es_pension_tax(input_path, SAMPLE_PENSION_INCOME, RULE_PACK, output_path)
            item = next(entry for entry in result["classifications"] if entry["stream_id"] == "spanish_civil_service_pension")

            self.assertEqual(item["treaty_article"], "19.2.b")
            self.assertEqual(item["taxing_power"]["country"], "IT")
            self.assertFalse(item["withholding"]["expected"])

    def test_change_of_residence_changes_private_pension_taxing_state(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-pension-tax-classification.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["recipient"]["fiscal_residence"] = "ES"
            data["recipient"]["nationalities"] = ["ES"]
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = classify_it_es_pension_tax(input_path, SAMPLE_PENSION_INCOME, RULE_PACK, output_path)
            item = next(entry for entry in result["classifications"] if entry["stream_id"] == "spanish_public_pension")

            self.assertEqual(item["treaty_article"], "18")
            self.assertEqual(item["taxing_power"]["country"], "ES")
            self.assertFalse(item["withholding"]["expected"])

    def test_missing_stream_classification_blocks_stream_without_applying_treaty(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-pension-tax-classification.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["stream_classifications"] = []
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = classify_it_es_pension_tax(input_path, SAMPLE_PENSION_INCOME, RULE_PACK, output_path)

            self.assertEqual(result["status"], "partial")
            self.assertTrue(all(item["classification_status"] == "blocked_missing_facts" for item in result["classifications"]))
            self.assertIn("missing_stream_classification", {gap["code"] for item in result["classifications"] for gap in item["data_gaps"]})

    def test_blocks_when_rule_year_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-pension-tax-classification.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["tax_year"] = 2027
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = classify_it_es_pension_tax(input_path, SAMPLE_PENSION_INCOME, RULE_PACK, output_path)

            self.assertEqual(result["status"], "blocked_missing_rule")
            self.assertEqual(result["data_gaps"][0]["code"], "tax_year_not_covered")
            self.assertEqual(result["classifications"], [])

    def test_load_rule_pack_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            rule_path = Path(tmp_dir) / "rules.json"
            rule_path.write_text(json.dumps({"schema_version": "wrong", "rules": []}), encoding="utf-8")

            with self.assertRaisesRegex(ItEsPensionTaxClassificationError, "missing field"):
                load_it_es_pension_tax_classification_rule_pack(rule_path)


if __name__ == "__main__":
    unittest.main()
