import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.simulation.scenario_comparison import compare_retirement_scenarios


NET_WORTH = {
    "record_type": "NetWorthSnapshot",
    "totals": {
        "net_worth": "250000.00",
    },
}

ASSUMPTIONS = {
    "record_type": "ManualAssumptions",
    "assumptions": {
        "personal": {
            "current_age": 60,
            "target_retirement_age": 64,
        },
        "cashflow": {
            "family_expenses_yearly": 24000,
            "retirement_income_yearly": 6000,
            "net_salary_monthly": 3000,
            "salary_months": 12,
        },
        "returns": {
            "nominal_return": 0.03,
            "nominal_volatility": 0.10,
        },
    },
}


class ScenarioComparisonTest(unittest.TestCase):
    def test_compare_retirement_scenarios_reports_missing_inputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_path = root / "scenario-comparison.json"

            result = compare_retirement_scenarios(
                root / "missing-net-worth.json",
                root / "missing-assumptions.json",
                output_path,
            )

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertEqual(result["scenarios"], [])
            self.assertTrue(any("Missing net worth snapshot" in gap for gap in result["data_gaps"]))
            self.assertTrue(output_path.exists())

    def test_compare_retirement_scenarios_ranks_complete_scenarios(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = _write_json(root / "net-worth.json", NET_WORTH)
            assumptions_path = _write_json(root / "assumptions.json", ASSUMPTIONS)

            result = compare_retirement_scenarios(
                net_worth_path,
                assumptions_path,
                root / "scenario-comparison.json",
                target_ages=[62, 64, 67],
                simulations=25,
                seed=1234,
            )

            self.assertEqual(result["status"], "complete")
            self.assertEqual([scenario["target_retirement_age"] for scenario in result["scenarios"]], [62, 64, 67])
            self.assertEqual(len(result["ranking"]), 3)
            self.assertEqual(result["ranking"][0]["target_retirement_age"], 67)
            self.assertEqual(result["scenarios"][0]["result"]["net_retirement_drawdown_yearly"], "18000.00")

    def test_compare_retirement_scenarios_is_reproducible_with_seed(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = _write_json(root / "net-worth.json", NET_WORTH)
            assumptions_path = _write_json(root / "assumptions.json", ASSUMPTIONS)

            first = compare_retirement_scenarios(
                net_worth_path,
                assumptions_path,
                root / "scenario-comparison-1.json",
                target_ages=[62, 64, 67],
                simulations=25,
                seed=1234,
            )
            second = compare_retirement_scenarios(
                net_worth_path,
                assumptions_path,
                root / "scenario-comparison-2.json",
                target_ages=[62, 64, 67],
                simulations=25,
                seed=1234,
            )

            self.assertEqual(first["scenarios"], second["scenarios"])
            self.assertEqual(first["ranking"], second["ranking"])


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
