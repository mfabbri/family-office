import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.simulation.retirement import simulate_retirement


NET_WORTH = {
    "record_type": "NetWorthSnapshot",
    "totals": {
        "net_worth": "100000.00",
    },
}

ASSUMPTIONS = {
    "record_type": "ManualAssumptions",
    "assumptions": {
        "personal": {
            "current_age": 60,
            "target_retirement_age": 62,
        },
        "cashflow": {
            "family_expenses_yearly": 10000,
            "net_salary_monthly": 5000,
            "salary_months": 14,
        },
        "returns": {
            "scenario": "synthetic",
            "nominal_return": 0.02,
        },
    },
}


class RetirementSimulationTest(unittest.TestCase):
    def test_simulate_retirement_generates_three_scenarios(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = _write_json(root / "net-worth.json", NET_WORTH)
            assumptions_path = _write_json(root / "assumptions.json", ASSUMPTIONS)
            output_path = root / "retirement.json"

            result = simulate_retirement(net_worth_path, assumptions_path, None, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["record_type"], "RetirementSimulationSnapshot")
            self.assertEqual(written["status"], "complete")
            self.assertEqual([scenario["target_retirement_age"] for scenario in written["scenarios"]], [62, 64, 67])
            self.assertEqual(written["scenarios"][0]["cashflows"][0]["age"], 60)

    def test_simulate_retirement_reports_missing_assumptions(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = _write_json(root / "net-worth.json", NET_WORTH)
            output_path = root / "retirement.json"

            result = simulate_retirement(net_worth_path, root / "missing-assumptions.json", None, output_path)

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertEqual(result["scenarios"], [])
            self.assertEqual(len(result["data_gaps"]), 1)


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
