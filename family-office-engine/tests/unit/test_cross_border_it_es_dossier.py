import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.cross_border_it_es_dossier import (
    CrossBorderItEsDossierError,
    build_cross_border_it_es_dossier,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPOSITORY_ROOT / "family-office-engine" / "examples"
CLASSIFICATION = EXAMPLES / "spanish-pension-net-it-es-classification-sample.json"
PENSION_NET = EXAMPLES / "cross-border-spanish-pension-net-sample.json"
PRO_RATA = EXAMPLES / "cross-border-it-es-eu-pension-pro-rata-sample.json"
FOREIGN_ASSETS = EXAMPLES / "cross-border-it-es-foreign-assets-sample.json"
PENSION_INCOME = EXAMPLES / "it-es-pension-income-sample.json"
PENSION_SCENARIO = EXAMPLES / "pension-scenario-snapshot-sample.json"


class CrossBorderItEsDossierTest(unittest.TestCase):
    def test_builds_complete_dossier_with_pension_and_spanish_assets(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "cross-border-it-es.snapshot.json"

            result = build_cross_border_it_es_dossier(
                output,
                pension_scenario_snapshot_path=PENSION_SCENARIO,
                pension_income_snapshot_path=PENSION_INCOME,
                pension_tax_classification_snapshot_path=CLASSIFICATION,
                spanish_pension_net_snapshot_path=PENSION_NET,
                eu_pension_pro_rata_snapshot_path=PRO_RATA,
                foreign_assets_snapshot_path=FOREIGN_ASSETS,
            )
            written = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "cross-border-it-es/v1")
            self.assertEqual(written["status"], "complete")
            self.assertEqual(written["context"]["fiscal_residence"], "IT")
            self.assertEqual(written["pension_scenario"]["selected_scenario_id"], "baseline_it_retirement")
            self.assertEqual(written["pension_scenario"]["selected_scenario"]["retirement"]["country"], "IT")
            self.assertTrue(written["pension_flows"]["streams"])
            self.assertEqual(written["pension_flows"]["streams"][0]["gross"]["annual_amount"], "21000.00")
            self.assertEqual(written["pension_flows"]["streams"][0]["gross"]["currency"], "EUR")
            self.assertEqual(written["pension_rights"]["spanish_entitlement"]["status"], "eligible_by_totalization")
            self.assertEqual(written["pension_taxation"]["net_streams"][0]["net"]["annual_amount"], "13650.00")
            self.assertEqual(written["pension_taxation"]["classifications"][0]["rule_id"], "it-es.treaty.private-pension.article-18.2026")
            self.assertEqual(written["foreign_asset_monitoring"]["totals"]["total_wealth_tax_due"], "528.00")
            self.assertTrue(written["summary"]["review_required"])
            self.assertRegex(written["source"]["foreign_assets"]["content_hash"], r"^[0-9a-f]{64}$")
            self.assertEqual(written["source"]["foreign_assets"]["rule_pack"]["rule_pack_id"], "it-es.foreign-asset-monitoring.2026.v2")
            self.assertEqual(written["source"]["foreign_assets"]["rule_pack"]["applied_rule_id"], "it-es.foreign-asset-monitoring.2026.v2")
            self.assertTrue(written["source"]["foreign_assets"]["source_refs"])
            self.assertTrue(written["source"]["foreign_assets"]["limitations"])

    def test_pension_only_dossier_remains_complete_with_asset_action_item(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "cross-border-it-es.snapshot.json"

            result = build_cross_border_it_es_dossier(
                output,
                pension_tax_classification_snapshot_path=CLASSIFICATION,
                spanish_pension_net_snapshot_path=PENSION_NET,
                eu_pension_pro_rata_snapshot_path=PRO_RATA,
            )

            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["foreign_asset_monitoring"]["status"], "missing")
            self.assertIn("build_foreign_asset_monitoring", {item["action_id"] for item in result["action_items"]})

    def test_asset_only_dossier_remains_complete_with_pension_action_item(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "cross-border-it-es.snapshot.json"

            result = build_cross_border_it_es_dossier(output, foreign_assets_snapshot_path=FOREIGN_ASSETS)

            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["pension_rights"]["status"], "missing")
            self.assertIn("build_pension_tax_classification", {item["action_id"] for item in result["action_items"]})

    def test_change_of_residence_is_reflected_from_classification_source(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            classification = root / "classification.json"
            output = root / "cross-border-it-es.snapshot.json"
            data = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
            data["input"]["recipient"]["fiscal_residence"] = "ES"
            classification.write_text(json.dumps(data), encoding="utf-8")

            result = build_cross_border_it_es_dossier(output, pension_tax_classification_snapshot_path=classification)

            self.assertEqual(result["context"]["fiscal_residence"], "ES")
            self.assertEqual(result["pension_taxation"]["classification_status"], "complete")

    def test_blocked_classification_blocks_dossier_and_preserves_gap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            classification = root / "classification.json"
            output = root / "cross-border-it-es.snapshot.json"
            data = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
            data["status"] = "blocked_missing_inputs"
            data["data_gaps"] = [{"code": "missing_stream_classification", "message": "Synthetic blocked classification."}]
            classification.write_text(json.dumps(data), encoding="utf-8")

            result = build_cross_border_it_es_dossier(output, pension_tax_classification_snapshot_path=classification)

            self.assertEqual(result["status"], "blocked_source")
            self.assertIn("pension_tax_classification_blocked", {gap["code"] for gap in result["data_gaps"]})
            self.assertIn("pension_tax_classification.missing_stream_classification", {gap["code"] for gap in result["data_gaps"]})

    def test_nested_asset_gap_makes_dossier_partial(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            foreign_assets = root / "assets.json"
            output = root / "cross-border-it-es.snapshot.json"
            data = json.loads(FOREIGN_ASSETS.read_text(encoding="utf-8"))
            data["status"] = "partial"
            data["assets"][0]["data_gaps"] = [{"code": "missing_year_end_value", "message": "Synthetic nested gap."}]
            foreign_assets.write_text(json.dumps(data), encoding="utf-8")

            result = build_cross_border_it_es_dossier(output, foreign_assets_snapshot_path=foreign_assets)

            self.assertEqual(result["status"], "partial")
            self.assertIn("foreign_assets_partial", {gap["code"] for gap in result["data_gaps"]})
            self.assertIn("foreign_assets.missing_year_end_value", {gap["code"] for gap in result["data_gaps"]})

    def test_blocked_not_eligible_pro_rata_blocks_dossier(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            pro_rata = root / "pro-rata.json"
            output = root / "cross-border-it-es.snapshot.json"
            data = json.loads(PRO_RATA.read_text(encoding="utf-8"))
            data["status"] = "blocked_not_eligible"
            data["input"] = {
                "household_id": "synthetic_household",
                "as_of_date": "2026-07-23",
                "tax_year": 2026,
                "resident_country": "IT",
            }
            data["data_gaps"] = [{"code": "spanish_entitlement_not_reached_even_with_totalization", "message": "Synthetic not eligible."}]
            pro_rata.write_text(json.dumps(data), encoding="utf-8")

            result = build_cross_border_it_es_dossier(output, eu_pension_pro_rata_snapshot_path=pro_rata)

            self.assertEqual(result["status"], "blocked_source")
            self.assertEqual(result["summary"]["blocking_source_count"], 1)

    def test_context_mismatch_blocks_dossier(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            assets = root / "assets.json"
            output = root / "cross-border-it-es.snapshot.json"
            data = json.loads(FOREIGN_ASSETS.read_text(encoding="utf-8"))
            data["input"]["tax_year"] = 2027
            assets.write_text(json.dumps(data), encoding="utf-8")

            result = build_cross_border_it_es_dossier(output, pension_tax_classification_snapshot_path=CLASSIFICATION, foreign_assets_snapshot_path=assets)

            self.assertEqual(result["status"], "blocked_source")
            self.assertIn("source_context_mismatch", {gap["code"] for gap in result["data_gaps"]})

    def test_personal_output_outside_workspace_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            assets = root / "assets.json"
            output = root / "cross-border-it-es.snapshot.json"
            data = json.loads(FOREIGN_ASSETS.read_text(encoding="utf-8"))
            data["input"]["household_id"] = "real_household"
            assets.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(CrossBorderItEsDossierError, "family-office-workspace"):
                build_cross_border_it_es_dossier(output, foreign_assets_snapshot_path=assets)

    def test_personal_dossier_rejects_synthetic_pension_scenario(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario = root / "pension-scenario.json"
            output = root / "cross-border-it-es.snapshot.json"
            data = json.loads(PENSION_SCENARIO.read_text(encoding="utf-8"))
            data["input"]["household_id"] = "real_household"
            scenario.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(CrossBorderItEsDossierError, "Synthetic pension scenarios"):
                build_cross_border_it_es_dossier(output, pension_scenario_snapshot_path=scenario)

    def test_pension_income_only_without_context_is_partial(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "cross-border-it-es.snapshot.json"

            result = build_cross_border_it_es_dossier(output, pension_income_snapshot_path=PENSION_INCOME)

            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["pension_flows"]["streams"][0]["gross"]["annual_amount"], "21000.00")
            self.assertIn("source_context_missing", {gap["code"] for gap in result["data_gaps"]})

    def test_personal_pension_income_without_context_cannot_write_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            pension_income = root / "pension-income.json"
            output = root / "cross-border-it-es.snapshot.json"
            data = json.loads(PENSION_INCOME.read_text(encoding="utf-8"))
            pension_income.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(CrossBorderItEsDossierError, "family-office-workspace"):
                build_cross_border_it_es_dossier(output, pension_income_snapshot_path=pension_income)

    def test_missing_configured_snapshot_becomes_partial_gap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "cross-border-it-es.snapshot.json"
            missing = Path(tmp_dir) / "missing.json"

            result = build_cross_border_it_es_dossier(output, foreign_assets_snapshot_path=missing)

            self.assertEqual(result["status"], "partial")
            self.assertIn("missing_foreign_assets_snapshot", {gap["code"] for gap in result["data_gaps"]})

    def test_requires_at_least_one_source(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "cross-border-it-es.snapshot.json"

            with self.assertRaisesRegex(CrossBorderItEsDossierError, "At least one"):
                build_cross_border_it_es_dossier(output)


if __name__ == "__main__":
    unittest.main()
