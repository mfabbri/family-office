import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.reporting.dashboard import build_decision_dashboard


NET_WORTH = {
    "record_type": "NetWorthSnapshot",
    "currency": "EUR",
    "totals": {
        "net_worth": "250000.00",
    },
    "data_gaps": ["unsupported bank document"],
}

ASSUMPTIONS = {
    "record_type": "ManualAssumptions",
    "assumptions": {},
}

MONTE_CARLO = {
    "record_type": "MonteCarloSimulationSnapshot",
    "status": "complete",
    "result": {
        "success_rate": "0.0000",
        "net_retirement_drawdown_yearly": "80000.00",
        "pre_retirement_income_yearly": "120000.00",
        "pre_retirement_net_cashflow_yearly": "40000.00",
        "rental_income_yearly": "12000.00",
    },
    "data_gaps": [],
}

SCENARIO_COMPARISON = {
    "record_type": "ScenarioComparisonSnapshot",
    "status": "complete",
    "ranking": [
        {
            "rank": 1,
            "scenario_id": "retire_at_67",
            "target_retirement_age": 67,
            "success_rate": "0.0000",
            "final_balance_p50": "-100.00",
        },
        {
            "rank": 2,
            "scenario_id": "retire_at_64",
            "target_retirement_age": 64,
            "success_rate": "0.0000",
            "final_balance_p50": "-200.00",
        },
    ],
    "data_gaps": [],
}

READINESS = {
    "record_type": "AssumptionsReadinessSnapshot",
    "status": "ready",
    "data_gaps": [],
}


class DashboardTest(unittest.TestCase):
    def test_build_decision_dashboard_collects_metrics_and_actions(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_path = root / "dashboard.json"

            result = build_decision_dashboard(
                _write_json(root / "net-worth.json", NET_WORTH),
                _write_json(root / "assumptions.json", ASSUMPTIONS),
                _write_json(root / "monte-carlo.json", MONTE_CARLO),
                _write_json(root / "scenario-comparison.json", SCENARIO_COMPARISON),
                _write_json(root / "readiness.json", READINESS),
                output_path,
            )

            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["summary"]["net_worth"], "250000.00")
            self.assertEqual(result["summary"]["best_ranked_scenario"]["target_retirement_age"], 67)
            metrics = {metric["id"]: metric["value"] for metric in result["metrics"]}
            self.assertEqual(metrics["pre_retirement_income_yearly"], "120000.00")
            self.assertEqual(metrics["rental_income_yearly"], "12000.00")
            self.assertTrue(any(signal["code"] == "zero_monte_carlo_success_rate" for signal in result["decision_signals"]))
            self.assertTrue(any("unsupported bank document" in gap for gap in result["data_gaps"]))
            self.assertTrue(output_path.exists())

    def test_build_decision_dashboard_reports_missing_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_path = root / "dashboard.json"

            result = build_decision_dashboard(
                root / "missing-net-worth.json",
                root / "missing-assumptions.json",
                root / "missing-monte-carlo.json",
                root / "missing-scenario-comparison.json",
                root / "missing-readiness.json",
                output_path,
            )

            self.assertEqual(result["status"], "partial")
            self.assertTrue(any("Missing net worth snapshot" in gap for gap in result["data_gaps"]))
            self.assertIn("Resolve missing snapshots", result["next_actions"][0])


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
