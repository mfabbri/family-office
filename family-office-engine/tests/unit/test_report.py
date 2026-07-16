import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.reporting.report import build_retirement_report


NET_WORTH = {
    "record_type": "NetWorthSnapshot",
    "currency": "EUR",
    "sources": {"fonte": "fonte.snapshot.json"},
    "components": [
        {
            "label": "Fon.Te pension fund position",
            "asset_class": "pension",
            "value": "100.00",
            "currency": "EUR",
            "valuation_date": "2026-07-08",
        }
    ],
    "totals": {
        "assets": "100.00",
        "liabilities": "0.00",
        "net_worth": "100.00",
    },
    "data_gaps": [],
}


COMPLETE_SIMULATION = {
    "record_type": "RetirementSimulationSnapshot",
    "status": "complete",
    "sources": {"net_worth": "net-worth.snapshot.json"},
    "target_ages": [62, 64, 67],
    "scenarios": [
        {
            "target_retirement_age": 62,
            "status": "complete",
            "final_balance": "10.00",
        }
    ],
    "data_gaps": [],
}


BLOCKED_SIMULATION = {
    "record_type": "RetirementSimulationSnapshot",
    "status": "blocked_missing_inputs",
    "sources": {"net_worth": "net-worth.snapshot.json"},
    "target_ages": [62, 64, 67],
    "scenarios": [],
    "data_gaps": ["Missing manual assumptions snapshot: assumptions.json"],
}


ASSUMPTIONS = {
    "record_type": "ManualAssumptions",
    "assumptions": {
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
            "nominal_return": "0.03",
        },
    },
}


READINESS = {
    "record_type": "AssumptionsReadinessSnapshot",
    "status": "ready",
    "data_gaps": [],
    "next_actions": [],
}


class ReportTest(unittest.TestCase):
    def test_build_retirement_report_writes_complete_markdown(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            simulation_path = _write_json(root / "simulation.json", COMPLETE_SIMULATION)
            net_worth_path = _write_json(root / "net-worth.json", NET_WORTH)
            assumptions_path = _write_json(root / "assumptions.json", ASSUMPTIONS)
            readiness_path = _write_json(root / "readiness.json", READINESS)
            output_path = root / "report.md"

            markdown = build_retirement_report(
                simulation_path,
                net_worth_path,
                output_path,
                assumptions_path,
                readiness_path,
            )

            self.assertTrue(output_path.exists())
            self.assertIn("# Retirement planning report", markdown)
            self.assertIn("Simulation status: `complete`", markdown)
            self.assertIn("| 62 | complete | 10.00 |", markdown)
            self.assertIn("Current age: 55", markdown)
            self.assertIn("simulation.net_worth", markdown)

    def test_build_retirement_report_reports_blocked_inputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            simulation_path = _write_json(root / "simulation.json", BLOCKED_SIMULATION)
            net_worth_path = _write_json(root / "net-worth.json", NET_WORTH)
            output_path = root / "report.md"

            markdown = build_retirement_report(
                simulation_path,
                net_worth_path,
                output_path,
                root / "missing-assumptions.json",
                root / "missing-readiness.json",
            )

            self.assertIn("Simulation status: `blocked_missing_inputs`", markdown)
            self.assertIn("No complete retirement scenario is available.", markdown)
            self.assertIn("Manual assumptions snapshot: `missing`", markdown)
            self.assertIn("Missing manual assumptions snapshot", markdown)


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
