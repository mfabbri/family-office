import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.tax_aware_portfolio import (
    TaxAwarePortfolioError,
    build_tax_aware_portfolio,
    load_tax_aware_investment_rule_pack,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "italy" / "2026" / "tax-aware-investment.json"
SAMPLE_INPUT = REPOSITORY_ROOT / "family-office-engine" / "examples" / "tax-aware-portfolio-input-sample.json"


class TaxAwarePortfolioTest(unittest.TestCase):
    def test_build_portfolio_applies_26_percent_12_5_percent_costs_and_bollo(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "tax-aware-portfolio.snapshot.json"

            result = build_tax_aware_portfolio(SAMPLE_INPUT, RULE_PACK, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "tax-aware-portfolio/v1")
            self.assertEqual(written["status"], "complete")
            option = next(item for item in written["options"] if item["option_id"] == "domestic_admin_balanced")
            self.assertEqual(option["totals"]["gross_expected_return"], "4200.00")
            self.assertEqual(option["totals"]["annual_costs"], "160.00")
            self.assertEqual(option["totals"]["taxable_realized_gain_before_losses"], "2400.00")
            self.assertEqual(option["totals"]["loss_offset_used"], "200.00")
            self.assertEqual(option["totals"]["tax_due"], "410.00")
            self.assertEqual(option["totals"]["wealth_tax"], "200.00")
            self.assertEqual(option["totals"]["net_expected_return"], "3430.00")
            self.assertEqual(
                written["rule_pack"]["source_refs"][0]["source_id"],
                "agenziaentrate.precompilata.plusvalenze-finanziarie-2026",
            )

    def test_build_portfolio_models_turnover_ivafe_and_deferred_tax(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "tax-aware-portfolio.snapshot.json"

            result = build_tax_aware_portfolio(SAMPLE_INPUT, RULE_PACK, output_path)
            option = next(item for item in result["options"] if item["option_id"] == "foreign_declarative_low_turnover")

            self.assertEqual(option["totals"]["taxable_realized_gain_before_losses"], "500.00")
            self.assertEqual(option["totals"]["tax_due"], "130.00")
            self.assertEqual(option["totals"]["wealth_tax"], "200.00")
            self.assertEqual(option["totals"]["deferred_tax_estimate"], "1170.00")
            self.assertEqual(option["totals"]["net_expected_return"], "4520.00")
            self.assertEqual(result["ranking"][0]["option_id"], "foreign_declarative_low_turnover")

    def test_build_portfolio_flags_regime_incompatible_with_foreign_intermediary(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "tax-aware-portfolio.snapshot.json"

            result = build_tax_aware_portfolio(SAMPLE_INPUT, RULE_PACK, output_path)
            option = next(item for item in result["options"] if item["option_id"] == "foreign_admin_incompatible")

            self.assertIn("regime_holding_location_incompatible", {item["code"] for item in option["constraints"]})

    def test_build_portfolio_requires_documented_government_tax_category(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "tax-aware-portfolio.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["options"][0]["positions"][1]["tax_category_documented"] = False
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_tax_aware_portfolio(input_path, RULE_PACK, output_path)
            option = next(item for item in result["options"] if item["option_id"] == "domestic_admin_balanced")

            self.assertEqual(result["status"], "partial")
            self.assertIn("government_tax_category_not_documented", {item["code"] for item in option["data_gaps"]})

    def test_build_portfolio_blocks_when_rule_year_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "tax-aware-portfolio.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["tax_year"] = 2027
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_tax_aware_portfolio(input_path, RULE_PACK, output_path)

            self.assertEqual(result["status"], "blocked_missing_rule")
            self.assertEqual(result["data_gaps"][0]["code"], "tax_year_not_covered")
            self.assertEqual(result["options"], [])

    def test_load_rule_pack_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            rule_path = Path(tmp_dir) / "rules.json"
            rule_path.write_text(json.dumps({"schema_version": "wrong", "rules": []}), encoding="utf-8")

            with self.assertRaisesRegex(TaxAwarePortfolioError, "missing field"):
                load_tax_aware_investment_rule_pack(rule_path)


if __name__ == "__main__":
    unittest.main()
