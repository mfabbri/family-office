import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from family_office_engine.cli.main import main
from family_office_engine.services.investment_opportunity_comparison import (
    InvestmentOpportunityComparisonError,
    build_investment_opportunity_comparison,
)

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "family-office-engine" / "examples" / "investment-opportunity-comparison-v1-sample.json"
INPUT_SCHEMA = ROOT / "family-office-engine" / "schemas" / "investment-opportunity-comparison-input.schema.json"


class InvestmentOpportunityComparisonTest(unittest.TestCase):
    def build(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.json"
            source.write_text(json.dumps(data), encoding="utf-8")
            return build_investment_opportunity_comparison(source, root / "snapshot.json")

    def test_declared_stress_comparison_keeps_dimensions_and_opportunity_cost_separate(self):
        snapshot = self.build(json.loads(SAMPLE.read_text(encoding="utf-8")))
        adverse = next(item for item in snapshot["primary"]["scenarios"] if item["scenario_type"] == "adverse")
        base = next(item for item in snapshot["comparisons"] if item["scenario_type"] == "base")
        self.assertEqual(snapshot["schema_version"], "investment-opportunity-comparison/v1")
        self.assertEqual(base["primary_net_horizon_value_before_initial_capital"], "64000.00")
        self.assertEqual(base["opportunity_cost"], "-11000.00")
        self.assertTrue(adverse["risk"]["negative_annual_equity_cash_flow"])
        self.assertTrue(adverse["liquidity"]["liquidity_breach"])
        self.assertTrue(adverse["liquidity"]["concentration_breach"])
        self.assertEqual(snapshot["summary"]["dimensions_kept_separate"], ["return", "risk", "liquidity", "management_burden"])
        self.assertFalse(snapshot["summary"]["automatic_ranking_produced"])

    def test_missing_benchmark_is_a_data_gap_not_an_implicit_return(self):
        data = json.loads(SAMPLE.read_text(encoding="utf-8"))
        data.pop("benchmark")
        snapshot = self.build(data)
        self.assertEqual(snapshot["status"], "partial")
        self.assertIn("missing_benchmark", {item["code"] for item in snapshot["data_gaps"]})
        self.assertTrue(all(item["opportunity_cost"] is None for item in snapshot["comparisons"]))

    def test_rejects_different_capital_or_horizon_and_missing_adverse_stress(self):
        data = json.loads(SAMPLE.read_text(encoding="utf-8"))
        data["benchmark"]["capital_amount"] = "40000"
        data["benchmark"]["horizon_years"] = 2
        data["primary"]["scenarios"][2]["stress_factors"] = []
        snapshot = self.build(data)
        codes = {item["code"] for item in snapshot["data_gaps"]}
        self.assertIn("incomparable_capital", codes)
        self.assertIn("incomparable_horizon", codes)
        self.assertIn("missing_stress_factors", codes)
        self.assertFalse(snapshot["summary"]["same_capital_and_horizon_declared"])

    def test_requires_base_upside_and_adverse_for_primary(self):
        data = json.loads(SAMPLE.read_text(encoding="utf-8"))
        data["primary"]["scenarios"].pop()
        with self.assertRaisesRegex(InvestmentOpportunityComparisonError, "exactly base, upside and adverse"):
            self.build(data)

    def test_input_schema_documents_the_nested_service_contract(self):
        schema = json.loads(INPUT_SCHEMA.read_text(encoding="utf-8"))
        alternative = schema["$defs"]["alternative"]
        scenario = schema["$defs"]["scenario"]
        constraints = schema["$defs"]["household_constraints"]
        self.assertEqual(
            set(alternative["properties"]),
            {"alternative_id", "label", "capital_amount", "horizon_years", "provenance", "scenarios"},
        )
        self.assertEqual(
            set(scenario["required"]),
            {"scenario_type", "label", "provenance", "annual_equity_cash_flow", "net_exit_value", "annual_owner_hours", "annual_owner_time_cost"},
        )
        self.assertEqual(
            set(constraints["properties"]),
            {"liquidity_reserve_required", "liquid_assets_after_commitment", "concentration_limit", "concentration_after_commitment", "retirement_work_exit_cash_flow_impact", "reversibility"},
        )

    def test_cli_demo_uses_short_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "demo.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["planning", "investment-opportunity-comparison", "demo", "--output", str(output)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())
            self.assertIn("planning investment-opportunity-comparison: complete", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
