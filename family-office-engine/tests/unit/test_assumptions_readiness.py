import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.assumptions_readiness import (
    check_assumptions_readiness,
)


VALID_ASSUMPTIONS = {
    "personal": {
        "current_age": 55,
        "target_retirement_age": 62,
    },
    "cashflow": {
        "family_expenses_yearly": 80000,
        "net_salary_monthly": 5000,
        "salary_months": 14,
    },
    "returns": {
        "scenario": "prudent",
        "nominal_return": 0.03,
    },
}


class AssumptionsReadinessTest(unittest.TestCase):
    def test_reports_missing_input_without_creating_private_data(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            template_path = root / "base-assumptions.template.json"
            input_path = root / "base-assumptions.json"
            snapshot_path = root / "manual-assumptions.snapshot.json"
            output_path = root / "assumptions-readiness.snapshot.json"
            template_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")

            result = check_assumptions_readiness(
                input_path,
                template_path,
                snapshot_path,
                output_path,
            )

            self.assertEqual(result["status"], "missing_input")
            self.assertFalse(input_path.exists())
            self.assertTrue(output_path.exists())
            self.assertEqual(result["data_gaps"][0]["code"], "missing_assumptions_input")

    def test_reports_missing_snapshot_after_valid_input(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            template_path = root / "base-assumptions.template.json"
            input_path = root / "base-assumptions.json"
            snapshot_path = root / "manual-assumptions.snapshot.json"
            output_path = root / "assumptions-readiness.snapshot.json"
            template_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")
            input_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")

            result = check_assumptions_readiness(
                input_path,
                template_path,
                snapshot_path,
                output_path,
            )

            self.assertEqual(result["status"], "missing_snapshot")
            self.assertEqual(result["data_gaps"][0]["code"], "missing_manual_assumptions_snapshot")

    def test_reports_ready_when_input_and_snapshot_exist(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            template_path = root / "base-assumptions.template.json"
            input_path = root / "base-assumptions.json"
            snapshot_path = root / "manual-assumptions.snapshot.json"
            output_path = root / "assumptions-readiness.snapshot.json"
            template_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")
            input_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")
            snapshot_path.write_text(json.dumps({"record_type": "ManualAssumptions"}), encoding="utf-8")

            result = check_assumptions_readiness(
                input_path,
                template_path,
                snapshot_path,
                output_path,
            )

            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["data_gaps"], [])

    def test_reports_invalid_input(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            template_path = root / "base-assumptions.template.json"
            input_path = root / "base-assumptions.json"
            snapshot_path = root / "manual-assumptions.snapshot.json"
            output_path = root / "assumptions-readiness.snapshot.json"
            template_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")
            input_path.write_text(json.dumps({"personal": {}}), encoding="utf-8")

            result = check_assumptions_readiness(
                input_path,
                template_path,
                snapshot_path,
                output_path,
            )

            self.assertEqual(result["status"], "invalid_input")
            self.assertEqual(result["data_gaps"][0]["code"], "invalid_assumptions_input")


if __name__ == "__main__":
    unittest.main()
