import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.it_es_foreign_assets import (
    ItEsForeignAssetsError,
    build_it_es_foreign_assets,
    load_it_es_foreign_asset_rule_pack,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "cross-border" / "it-es-foreign-asset-monitoring-v2.json"
SAMPLE_INPUT = REPOSITORY_ROOT / "family-office-engine" / "examples" / "it-es-foreign-assets-input-sample.json"


class ItEsForeignAssetsTest(unittest.TestCase):
    def test_build_assets_calculates_account_funds_pension_plan_and_real_estate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "it-es-foreign-assets.snapshot.json"

            result = build_it_es_foreign_assets(SAMPLE_INPUT, RULE_PACK, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "it-es-foreign-assets/v1")
            self.assertEqual(written["status"], "partial")
            account = next(item for item in written["assets"] if item["asset_id"] == "es_bank_account")
            fund = next(item for item in written["assets"] if item["asset_id"] == "es_fund")
            pension = next(item for item in written["assets"] if item["asset_id"] == "es_pension_plan")
            property_asset = next(item for item in written["assets"] if item["asset_id"] == "es_property")

            self.assertTrue(account["rw_monitoring"]["required"])
            self.assertEqual(account["wealth_tax"]["amount"], "34.20")
            self.assertEqual(fund["wealth_tax"]["amount"], "100.00")
            self.assertEqual(pension["wealth_tax"]["amount"], "60.00")
            self.assertEqual(property_asset["wealth_tax"]["tax_type"], "IVIE")
            self.assertEqual(property_asset["wealth_tax"]["amount"], "428.00")
            self.assertEqual(written["totals"]["ivafe_due"], "194.20")
            self.assertEqual(written["totals"]["ivie_due"], "428.00")
            self.assertIn("period_end_value", property_asset["declared_values"])
            self.assertEqual(written["rule_pack"]["applied_rule_id"], "it-es.foreign-asset-monitoring.2026.v2")
            self.assertRegex(written["rule_pack"]["content_hash"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                written["rule_pack"]["source_refs"][0]["source_id"],
                "agenziaentrate.precompilata.quadro-rw-2026",
            )

    def test_documented_italian_intermediary_does_not_infer_foreign_ivafe(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "it-es-foreign-assets.snapshot.json"

            result = build_it_es_foreign_assets(SAMPLE_INPUT, RULE_PACK, output_path)
            item = next(entry for entry in result["assets"] if entry["asset_id"] == "it_custody_spanish_fund")

            self.assertFalse(item["rw_monitoring"]["required"])
            self.assertEqual(item["rw_monitoring"]["reason"], "documented_italian_intermediary_conditions_met")
            self.assertEqual(item["wealth_tax"]["calculation_status"], "not_calculated_exemption_documented")

    def test_unclassified_asset_becomes_data_gap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "it-es-foreign-assets.snapshot.json"

            result = build_it_es_foreign_assets(SAMPLE_INPUT, RULE_PACK, output_path)
            item = next(entry for entry in result["assets"] if entry["asset_id"] == "unclassified_asset")

            self.assertEqual(result["status"], "partial")
            self.assertIn("asset_type_not_classified", {gap["code"] for gap in item["data_gaps"]})
            self.assertIsNone(item["rw_monitoring"]["required"])

    def test_pension_plan_requires_documented_classification(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-foreign-assets.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            pension = next(item for item in data["assets"] if item["asset_id"] == "es_pension_plan")
            pension["classification"] = {"outcome": "monitorable_financial_product", "documented": False}
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_it_es_foreign_assets(input_path, RULE_PACK, output_path)
            item = next(entry for entry in result["assets"] if entry["asset_id"] == "es_pension_plan")

            self.assertEqual(result["status"], "partial")
            self.assertIn("pension_plan_classification_not_documented", {gap["code"] for gap in item["data_gaps"]})
            self.assertEqual(item["wealth_tax"]["calculation_status"], "blocked_missing_facts")

    def test_bank_account_under_threshold_has_no_rw_or_ivafe(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-foreign-assets.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["assets"] = [
                {
                    "asset_id": "small_account",
                    "label": "Small account",
                    "asset_type": "foreign_bank_account",
                    "jurisdiction": "ES",
                    "intermediary_residence": "ES",
                    "ownership_share": "1.0000",
                    "days_held": 365,
                    "period_end_value": "1000.00",
                    "max_value": "3000.00",
                    "average_balance": "1000.00",
                    "source_document_types": ["bank_statement", "year_end_balance", "average_balance_statement", "ownership_evidence"],
                }
            ]
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_it_es_foreign_assets(input_path, RULE_PACK, output_path)
            item = result["assets"][0]

            self.assertEqual(result["status"], "complete")
            self.assertFalse(item["rw_monitoring"]["required"])
            self.assertEqual(item["wealth_tax"]["amount"], "0.00")

    def test_multiple_bank_accounts_require_documented_aggregate_values(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-foreign-assets.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            account = next(item for item in data["assets"] if item["asset_id"] == "es_bank_account")
            second = dict(account)
            second["asset_id"] = "es_second_account"
            second["max_value"] = "8000.00"
            second["average_balance"] = "3000.00"
            data["assets"] = [account, second]
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_it_es_foreign_assets(input_path, RULE_PACK, output_path)

            self.assertEqual(result["status"], "partial")
            self.assertIn("missing_bank_account_aggregate_values", {gap["code"] for item in result["assets"] for gap in item["data_gaps"]})

    def test_multiple_bank_accounts_use_documented_aggregate_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-foreign-assets.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            account = next(item for item in data["assets"] if item["asset_id"] == "es_bank_account")
            account["max_value"] = "8000.00"
            account["average_balance"] = "3000.00"
            account["bank_account_aggregate"] = {"max_value": "16000.00", "average_balance": "6000.00", "documented": True}
            second = dict(account)
            second["asset_id"] = "es_second_account"
            data["assets"] = [account, second]
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_it_es_foreign_assets(input_path, RULE_PACK, output_path)

            self.assertEqual(result["status"], "complete")
            self.assertTrue(all(item["rw_monitoring"]["required"] for item in result["assets"]))
            self.assertEqual(result["totals"]["ivafe_due"], "68.40")

    def test_ivie_below_payment_threshold_is_not_due_but_remains_monitored(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-foreign-assets.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            property_asset = next(item for item in data["assets"] if item["asset_id"] == "es_property")
            property_asset["period_end_value"] = "10000.00"
            property_asset["foreign_property_tax_credit"] = "0.00"
            property_asset["tax_events"] = []
            data["assets"] = [property_asset]
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_it_es_foreign_assets(input_path, RULE_PACK, output_path)
            item = result["assets"][0]

            self.assertEqual(result["status"], "complete")
            self.assertTrue(item["rw_monitoring"]["required"])
            self.assertEqual(item["wealth_tax"]["calculation_status"], "below_payment_threshold")
            self.assertEqual(item["wealth_tax"]["amount"], "0.00")

    def test_domestic_intermediary_exemption_does_not_apply_to_real_estate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-foreign-assets.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            property_asset = next(item for item in data["assets"] if item["asset_id"] == "es_property")
            property_asset["intermediary_residence"] = "IT"
            property_asset["domestic_intermediary_evidence"] = {
                "managed_or_administered_by_italian_intermediary": True,
                "income_subject_to_italian_withholding_or_substitute_tax": True,
                "intermediary_documented": True,
            }
            data["assets"] = [property_asset]
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_it_es_foreign_assets(input_path, RULE_PACK, output_path)
            item = result["assets"][0]

            self.assertTrue(item["rw_monitoring"]["required"])
            self.assertEqual(item["wealth_tax"]["tax_type"], "IVIE")

    def test_blocks_when_currency_or_as_of_year_do_not_match_rule_pack(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-foreign-assets.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["base_currency"] = "USD"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_it_es_foreign_assets(input_path, RULE_PACK, output_path)

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertIn("currency_not_covered", {gap["code"] for gap in result["data_gaps"]})
            self.assertIsNone(result["totals"]["ivafe_due"])

    def test_content_hash_changes_when_declared_basis_changes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            first_output = root / "first.json"
            second_input = root / "input.json"
            second_output = root / "second.json"
            first = build_it_es_foreign_assets(SAMPLE_INPUT, RULE_PACK, first_output)
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            fund = next(item for item in data["assets"] if item["asset_id"] == "es_fund")
            fund["period_end_value"] = "51000.00"
            second_input.write_text(json.dumps(data), encoding="utf-8")

            second = build_it_es_foreign_assets(second_input, RULE_PACK, second_output)

            self.assertNotEqual(first["reproducibility"]["content_hash"], second["reproducibility"]["content_hash"])

    def test_blocks_when_rule_year_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "it-es-foreign-assets.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["tax_year"] = 2027
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_it_es_foreign_assets(input_path, RULE_PACK, output_path)

            self.assertEqual(result["status"], "blocked_missing_rule")
            self.assertEqual(result["data_gaps"][0]["code"], "tax_year_not_covered")
            self.assertEqual(result["assets"], [])
            self.assertIsNone(result["totals"]["ivafe_due"])

    def test_load_rule_pack_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            rule_path = Path(tmp_dir) / "rules.json"
            rule_path.write_text(json.dumps({"schema_version": "wrong", "rules": []}), encoding="utf-8")

            with self.assertRaisesRegex(ItEsForeignAssetsError, "missing field"):
                load_it_es_foreign_asset_rule_pack(rule_path)


if __name__ == "__main__":
    unittest.main()
