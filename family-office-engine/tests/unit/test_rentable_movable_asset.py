import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from family_office_engine.cli.main import main
from family_office_engine.services.rentable_movable_asset import build_rentable_movable_asset

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "family-office-engine" / "examples" / "rentable-movable-asset-v1-sample.json"


class RentableMovableAssetTest(unittest.TestCase):
    def build(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / "input.json"; source.write_text(json.dumps(data), encoding="utf-8")
            return build_rentable_movable_asset(source, root / "snapshot.json")

    def test_builds_camper_with_personal_use_separate_from_rental_cash_flow(self):
        snapshot = self.build(json.loads(SAMPLE.read_text(encoding="utf-8")))
        metrics = snapshot["scenarios"][0]["metrics"]
        self.assertEqual(snapshot["schema_version"], "rentable-movable-asset/v1")
        self.assertEqual(metrics["rental_revenue"], "12000.00")
        self.assertEqual(metrics["platform_agency_fee"], "1800.00")
        self.assertEqual(metrics["net_operating_income"], "4500.00")
        self.assertEqual(metrics["annual_free_cash_flow"], "3150.00")
        self.assertEqual(metrics["personal_use_economic_benefit"], "2500.00")
        self.assertEqual(metrics["rental_utilization_rate"], "0.2667")
        self.assertTrue(snapshot["summary"]["personal_use_is_not_taxable_cash_flow"])
        repeated = self.build(json.loads(SAMPLE.read_text(encoding="utf-8")))
        self.assertEqual(snapshot["reproducibility"]["content_hash"], repeated["reproducibility"]["content_hash"])

    def test_zero_rental_downtime_and_major_repair_are_explicit(self):
        data = json.loads(SAMPLE.read_text(encoding="utf-8")); scenario = data["scenarios"][0]
        scenario["availability"] = {"available_days": 300, "personal_use_days": 30, "rental_days": 0, "downtime_days": 80}
        scenario["major_repair"] = [{"code": "engine_repair", "amount": "5000"}]
        snapshot = self.build(data); metrics = snapshot["scenarios"][0]["metrics"]
        self.assertEqual(metrics["annual_revenue"], "0.00")
        self.assertEqual(metrics["annual_operating_costs"], "10700.00")
        self.assertEqual(metrics["rental_utilization_rate"], "0.0000")

    def test_missing_classification_is_gap_not_inference_and_residual_shock_is_preserved(self):
        data = json.loads(SAMPLE.read_text(encoding="utf-8")); scenario = data["scenarios"][0]
        scenario.pop("activity_classification"); scenario["exit"]["residual_value"][0]["amount"] = "10000"
        snapshot = self.build(data)
        self.assertEqual(snapshot["status"], "partial")
        self.assertIn("missing_activity_classification", snapshot["scenarios"][0]["gap_codes"])
        self.assertEqual(snapshot["scenarios"][0]["metrics"]["net_exit_value"], "9000.00")

    def test_rejects_days_above_declared_availability(self):
        data = json.loads(SAMPLE.read_text(encoding="utf-8")); data["scenarios"][0]["availability"]["rental_days"] = 280
        with self.assertRaisesRegex(ValueError, "exceed available_days"):
            self.build(data)

    def test_cli_demo_uses_short_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "demo.json"; stdout = StringIO()
            with redirect_stdout(stdout): exit_code = main(["planning", "rentable-movable-asset", "demo", "--output", str(output)])
            self.assertEqual(exit_code, 0); self.assertTrue(output.exists())
            self.assertIn("planning rentable-movable-asset: complete", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
