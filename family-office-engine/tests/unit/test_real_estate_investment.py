import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from family_office_engine.cli.main import main
from family_office_engine.services.real_estate_investment import build_real_estate_investment

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "family-office-engine" / "examples" / "real-estate-investment-v2-sample.json"


class RealEstateInvestmentTest(unittest.TestCase):
    def test_builds_mixed_use_income_property_with_separate_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = build_real_estate_investment(SAMPLE, Path(tmp) / "snapshot.json")
        metrics = snapshot["scenarios"][0]["metrics"]
        self.assertEqual(snapshot["schema_version"], "real-estate-investment/v2")
        self.assertEqual(metrics["annual_revenue"], "20100.00")
        self.assertEqual(metrics["net_operating_income"], "14490.00")
        self.assertEqual(metrics["annual_free_cash_flow"], "11090.00")
        self.assertEqual(metrics["tax_drag"], "2500.00")
        self.assertEqual(metrics["residual_value"], "225000.00")
        self.assertEqual(metrics["net_exit_value"], "217000.00")
        self.assertEqual(snapshot["scenarios"][0]["personal_use_days"], 20)
        self.assertEqual(metrics["personal_use_economic_benefit"], "2000.00")

    def test_vacancy_management_maintenance_and_tax_classification_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = json.loads(SAMPLE.read_text(encoding="utf-8"))
            scenario = data["scenarios"][0]
            scenario["rental_streams"] = [{"stream_id": "lease", "stream_type": "long_term", "monthly_rent": "1000", "vacancy_months": 12}]
            scenario["rental_model"] = "long_term"
            scenario["personal_use_days"] = 0
            scenario.pop("tax_classification")
            scenario["management_fee_rate"] = "0.20"
            scenario["operating_costs"] = [{"code": "maintenance_shock", "amount": "7000"}]
            source = root / "gap.json"; source.write_text(json.dumps(data), encoding="utf-8")
            snapshot = build_real_estate_investment(source, root / "snapshot.json")
        metrics = snapshot["scenarios"][0]["metrics"]
        self.assertEqual(snapshot["status"], "partial")
        self.assertEqual(metrics["annual_revenue"], "0.00")
        self.assertEqual(metrics["annual_operating_costs"], "7000.00")
        self.assertIn("missing_tax_classification", snapshot["scenarios"][0]["gap_codes"])

    def test_rejects_short_stay_bookings_above_availability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); data = json.loads(SAMPLE.read_text(encoding="utf-8"))
            data["scenarios"][0]["rental_streams"][1]["booked_nights"] = 41
            source = root / "invalid.json"; source.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "booked_nights"):
                build_real_estate_investment(source, root / "snapshot.json")

    def test_marks_scenarios_with_different_capital_as_not_comparable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); data = json.loads(SAMPLE.read_text(encoding="utf-8"))
            adverse = json.loads(json.dumps(data["scenarios"][0])); adverse["scenario_id"] = "adverse"
            adverse["acquisition"]["purchase_price"][0]["amount"] = "210000"
            data["scenarios"].append(adverse)
            source = root / "incomparable.json"; source.write_text(json.dumps(data), encoding="utf-8")
            snapshot = build_real_estate_investment(source, root / "snapshot.json")
        self.assertEqual(snapshot["status"], "partial")
        self.assertFalse(snapshot["summary"]["same_capital_and_horizon_declared"])
        self.assertTrue(all("incomparable_acquisition_basis" in item["gap_codes"] for item in snapshot["scenarios"]))

    def test_cli_demo_uses_short_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "demo.json"; stdout = StringIO()
            with redirect_stdout(stdout): exit_code = main(["planning", "real-estate-investment", "demo", "--output", str(output)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())
            self.assertIn("planning real-estate-investment: complete", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
