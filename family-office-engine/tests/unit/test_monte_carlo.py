import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.simulation.monte_carlo import simulate_monte_carlo


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
            "net_salary_monthly": 3000,
            "salary_months": 12,
        },
        "returns": {
            "nominal_return": 0.03,
            "nominal_volatility": 0.10,
        },
    },
}


class MonteCarloSimulationTest(unittest.TestCase):
    def test_simulate_monte_carlo_reports_missing_assumptions(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = _write_json(root / "net-worth.json", NET_WORTH)
            output_path = root / "monte-carlo.json"

            result = simulate_monte_carlo(net_worth_path, root / "missing-assumptions.json", output_path)

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertIsNone(result["result"])
            self.assertTrue(any("Missing manual assumptions snapshot" in gap for gap in result["data_gaps"]))

    def test_simulate_monte_carlo_is_reproducible_with_seed(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = _write_json(root / "net-worth.json", NET_WORTH)
            assumptions_path = _write_json(root / "assumptions.json", ASSUMPTIONS)

            first = simulate_monte_carlo(
                net_worth_path,
                assumptions_path,
                root / "monte-carlo-1.json",
                simulations=25,
                seed=1234,
            )
            second = simulate_monte_carlo(
                net_worth_path,
                assumptions_path,
                root / "monte-carlo-2.json",
                simulations=25,
                seed=1234,
            )

            self.assertEqual(first["status"], "complete")
            self.assertEqual(first["result"], second["result"])
            self.assertEqual(first["result"]["target_retirement_age"], 64)
            self.assertIn("final_balance_p50", first["result"])
            self.assertIn("success_rate", first["result"])
            self.assertEqual(first["result"]["retirement_income_yearly"], "0.00")
            self.assertEqual(first["result"]["net_retirement_drawdown_yearly"], "24000.00")
            self.assertEqual(first["result"]["self_salary_yearly"], "36000.00")
            self.assertEqual(first["result"]["pre_retirement_net_cashflow_yearly"], "12000.00")

    def test_simulate_monte_carlo_uses_retirement_income(self):
        assumptions_with_income = json.loads(json.dumps(ASSUMPTIONS))
        assumptions_with_income["assumptions"]["cashflow"]["retirement_income_yearly"] = 12000
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = _write_json(root / "net-worth.json", NET_WORTH)
            assumptions_path = _write_json(root / "assumptions.json", ASSUMPTIONS)
            assumptions_with_income_path = _write_json(
                root / "assumptions-with-income.json",
                assumptions_with_income,
            )

            without_income = simulate_monte_carlo(
                net_worth_path,
                assumptions_path,
                root / "monte-carlo-without-income.json",
                simulations=25,
                seed=1234,
            )
            with_income = simulate_monte_carlo(
                net_worth_path,
                assumptions_with_income_path,
                root / "monte-carlo-with-income.json",
                simulations=25,
                seed=1234,
            )

            self.assertEqual(with_income["status"], "complete")
            self.assertEqual(with_income["result"]["retirement_income_yearly"], "12000.00")
            self.assertEqual(with_income["result"]["net_retirement_drawdown_yearly"], "12000.00")
            self.assertGreater(
                float(with_income["result"]["final_balance_p50"]),
                float(without_income["result"]["final_balance_p50"]),
            )

    def test_simulate_monte_carlo_uses_spouse_salary_and_rental_income(self):
        assumptions_with_cashflow = json.loads(json.dumps(ASSUMPTIONS))
        assumptions_with_cashflow["assumptions"]["cashflow"]["spouse_net_salary_monthly"] = 2000
        assumptions_with_cashflow["assumptions"]["cashflow"]["spouse_salary_months"] = 12
        assumptions_with_cashflow["assumptions"]["cashflow"]["rental_income_monthly_net"] = 1000
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = _write_json(root / "net-worth.json", NET_WORTH)
            assumptions_path = _write_json(root / "assumptions.json", ASSUMPTIONS)
            assumptions_with_cashflow_path = _write_json(
                root / "assumptions-with-cashflow.json",
                assumptions_with_cashflow,
            )

            base = simulate_monte_carlo(
                net_worth_path,
                assumptions_path,
                root / "monte-carlo-base.json",
                simulations=25,
                seed=1234,
            )
            with_cashflow = simulate_monte_carlo(
                net_worth_path,
                assumptions_with_cashflow_path,
                root / "monte-carlo-cashflow.json",
                simulations=25,
                seed=1234,
            )

            self.assertEqual(with_cashflow["result"]["spouse_salary_yearly"], "24000.00")
            self.assertEqual(with_cashflow["result"]["rental_income_yearly"], "12000.00")
            self.assertEqual(with_cashflow["result"]["pre_retirement_income_yearly"], "72000.00")
            self.assertEqual(with_cashflow["result"]["pre_retirement_net_cashflow_yearly"], "48000.00")
            self.assertEqual(with_cashflow["result"]["net_retirement_drawdown_yearly"], "12000.00")
            self.assertGreater(
                float(with_cashflow["result"]["final_balance_p50"]),
                float(base["result"]["final_balance_p50"]),
            )

    def test_simulate_monte_carlo_requires_volatility(self):
        assumptions = json.loads(json.dumps(ASSUMPTIONS))
        del assumptions["assumptions"]["returns"]["nominal_volatility"]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = _write_json(root / "net-worth.json", NET_WORTH)
            assumptions_path = _write_json(root / "assumptions.json", assumptions)
            output_path = root / "monte-carlo.json"

            result = simulate_monte_carlo(net_worth_path, assumptions_path, output_path)

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertTrue(any("nominal_volatility" in gap for gap in result["data_gaps"]))


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
