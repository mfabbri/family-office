import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from family_office_engine.cli.main import main
from family_office_engine.services.financing_plan import FinancingPlanError, build_financing_plan

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "family-office-engine" / "examples" / "financing-plan-v1-sample.json"


class FinancingPlanTest(unittest.TestCase):
    def build(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / "input.json"; source.write_text(json.dumps(data), encoding="utf-8")
            return build_financing_plan(source, root / "snapshot.json")

    def test_fixed_rate_schedule_separates_asset_and_equity_cash_flow(self):
        snapshot = self.build(json.loads(SAMPLE.read_text(encoding="utf-8")))
        first = snapshot["annual_schedule"][0]
        self.assertEqual(snapshot["schema_version"], "financing-plan/v1")
        self.assertEqual(snapshot["metrics"]["loan_to_value"], "0.7500")
        self.assertEqual(first["opening_debt"], "150000.00")
        self.assertEqual(first["interest"], "6000.00")
        self.assertEqual(first["asset_cash_flow_before_financing"], "12000.00")
        self.assertNotEqual(first["asset_cash_flow_before_financing"], first["equity_cash_flow_after_financing"])
        self.assertIsNotNone(first["dscr"])
        self.assertEqual(snapshot["annual_schedule"][1]["early_repayment_fee"], "150.00")
        self.assertEqual(snapshot["annual_schedule"][-1]["remaining_debt"], "0.00")

    def test_variable_rate_path_and_high_ltv_use_declared_inputs(self):
        data = json.loads(SAMPLE.read_text(encoding="utf-8")); terms = data["terms"]
        terms.pop("fixed_annual_rate"); terms["rate_type"] = "variable"; terms["variable_annual_rates"] = ["0.03", "0.05", "0.06"]
        data["collateral_value"] = "100000.00"
        snapshot = self.build(data)
        self.assertEqual(snapshot["metrics"]["loan_to_value"], "1.5000")
        self.assertEqual(snapshot["terms"]["annual_rates"], ["0.0300", "0.0500", "0.0600"])
        self.assertEqual(snapshot["annual_schedule"][1]["interest"], "5073.52")

    def test_zero_debt_is_explicit_and_dscr_is_not_inferred(self):
        data = json.loads(SAMPLE.read_text(encoding="utf-8")); data["terms"]["loan_amount"] = "0"; data["terms"]["early_repayments"] = []
        snapshot = self.build(data)
        self.assertEqual(snapshot["annual_schedule"], [])
        self.assertEqual(snapshot["metrics"]["loan_to_value"], "0.0000")
        self.assertEqual(snapshot["metrics"]["equity_cash_flow_after_financing"], "-1000.00")
        self.assertIn("dscr_not_applicable_zero_debt", {item["code"] for item in snapshot["data_gaps"]})

    def test_debt_service_stress_and_missing_noi_are_visible(self):
        data = json.loads(SAMPLE.read_text(encoding="utf-8")); data["asset_cash_flow"].pop("annual_net_operating_income")
        data["terms"]["fixed_annual_rate"] = "0.12"
        snapshot = self.build(data)
        self.assertGreater(float(snapshot["annual_schedule"][0]["debt_service"]), 60000)
        self.assertIsNone(snapshot["annual_schedule"][0]["dscr"])
        self.assertIn("missing_noi_for_dscr", {item["code"] for item in snapshot["data_gaps"]})

    def test_rejects_rate_inference_and_early_repayment_above_debt(self):
        data = json.loads(SAMPLE.read_text(encoding="utf-8")); data["terms"].pop("fixed_annual_rate")
        with self.assertRaisesRegex(FinancingPlanError, "fixed_annual_rate"):
            self.build(data)
        data = json.loads(SAMPLE.read_text(encoding="utf-8")); data["terms"]["early_repayments"][0]["principal_amount"] = "200000"
        with self.assertRaisesRegex(FinancingPlanError, "exceeds remaining debt"):
            self.build(data)

    def test_cli_demo_uses_short_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "demo.json"; stdout = StringIO()
            with redirect_stdout(stdout): exit_code = main(["planning", "financing-plan", "demo", "--output", str(output)])
            self.assertEqual(exit_code, 0); self.assertTrue(output.exists())
            self.assertIn("planning financing-plan: complete", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
