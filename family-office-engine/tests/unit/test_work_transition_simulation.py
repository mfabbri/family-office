import copy
import unittest
from decimal import Decimal

from family_office_engine.services.work_transition_simulation import (
    WorkTransitionSimulationError,
    build_work_transition_simulation,
)


def sample(path=None):
    assumptions = {
        "provenance": "synthetic test assumptions",
        "annual_inflation_rate": "0",
        "annual_return_rate": "0",
        "monthly_net_income": "0",
        "monthly_household_spending": "40",
        "monthly_declared_tax": "0",
        "monthly_declared_costs": "0",
        "emergency_floor_months": "1",
        "draw_order": ["emergency_reserve", "short_term"],
        "buckets": [
            {"bucket": "emergency_reserve", "opening_balance": "100"},
            {"bucket": "short_term", "opening_balance": "0"},
            {"bucket": "restricted", "opening_balance": "500"},
        ],
    }
    if path is not None:
        assumptions["deterministic_monthly_return_path"] = path
        assumptions["stress"] = {"monthly_return_path": path, "trials": 12, "seed": 17}
    return {"schema_version": "work-transition-simulation/v1",
            "decision_question": "Can declared resources support this transition scenario?",
            "months": len(path) if path else 2,
            "assumptions": assumptions}


class WorkTransitionSimulationTests(unittest.TestCase):
    def test_sequence_order_changes_shortfall_and_terminal_wealth(self):
        early_crash = sample(["-0.5", "1"])
        late_crash = sample(["1", "-0.5"])
        first = build_work_transition_simulation(early_crash)
        second = build_work_transition_simulation(late_crash)
        self.assertEqual(first["deterministic_baseline"]["summary"]["total_shortfall"], "20.00")
        self.assertEqual(first["deterministic_baseline"]["summary"]["terminal_spendable_assets"], "0.00")
        self.assertEqual(second["deterministic_baseline"]["summary"]["total_shortfall"], "0.00")
        self.assertEqual(second["deterministic_baseline"]["summary"]["terminal_spendable_assets"], "40.00")
        self.assertEqual(first["pension_entitlement"]["verified_monthly_amount"], None)

    def test_seed_reproducibility_and_baseline_independence(self):
        source = sample(["-0.2", "0.1", "0.05"])
        with_stress = build_work_transition_simulation(source)
        again = build_work_transition_simulation(copy.deepcopy(source))
        without_stress = copy.deepcopy(source)
        del without_stress["assumptions"]["stress"]
        baseline_only = build_work_transition_simulation(without_stress)
        self.assertEqual(with_stress["stress"], again["stress"])
        self.assertEqual(with_stress["deterministic_baseline"], baseline_only["deterministic_baseline"])

    def test_income_stream_is_inclusive_and_keeps_entitlement_unassessed(self):
        source = sample()
        source["assumptions"]["income_streams"] = [{
            "monthly_net_amount": "25", "start_month": 2, "end_month": 2,
            "assumption_status": "scenario_assumption", "provenance": "synthetic deferred income",
        }]
        result = build_work_transition_simulation(source)
        self.assertEqual(result["deterministic_baseline"]["months"][0]["net_income"], "0.00")
        self.assertEqual(result["deterministic_baseline"]["months"][1]["net_income"], "25.00")
        self.assertEqual(result["pension_entitlement"]["status"], "not_assessed")
        self.assertEqual(result["pension_entitlement"]["verified_start_month"], None)

    def test_restricted_assets_do_not_fund_spending(self):
        source = sample()
        source["assumptions"]["buckets"] = [{"bucket": "restricted", "opening_balance": "500"}]
        source["assumptions"]["draw_order"] = ["short_term"]
        source["assumptions"]["buckets"].append({"bucket": "short_term", "opening_balance": "0"})
        result = build_work_transition_simulation(source)
        summary = result["deterministic_baseline"]["summary"]
        self.assertEqual(summary["total_shortfall"], "80.00")
        self.assertEqual(summary["terminal_buckets"]["restricted"], "500.00")

    def test_rejects_nonfinite_inputs_and_unverified_pension_tags(self):
        source = sample()
        source["assumptions"]["monthly_declared_costs"] = "NaN"
        with self.assertRaises(WorkTransitionSimulationError):
            build_work_transition_simulation(source)
        source = sample()
        source["assumptions"]["income_streams"] = [{"monthly_net_amount": "500", "start_month": 1,
            "end_month": 2, "assumption_status": "verified_pension", "provenance": "synthetic"}]
        with self.assertRaises(WorkTransitionSimulationError):
            build_work_transition_simulation(source)

    def test_monthly_tax_costs_inflation_and_reserve_breach_are_visible(self):
        source = sample()
        source["assumptions"].update({"annual_inflation_rate": "0.12", "monthly_declared_tax": "2",
                                      "monthly_declared_costs": "3"})
        result = build_work_transition_simulation(source)
        first, second = result["deterministic_baseline"]["months"]
        self.assertEqual(first["declared_tax"], "2.00")
        self.assertEqual(first["declared_costs"], "3.00")
        self.assertEqual(second["inflation_adjusted_spending"], "40.40")
        self.assertEqual(result["deterministic_baseline"]["summary"]["reserve_breach_months"], 1)

    def test_invalid_stress_path_and_draw_order_fail_closed(self):
        source = sample(["-0.5"])
        source["assumptions"]["stress"]["monthly_return_path"] = ["-0.5", "0"]
        with self.assertRaises(WorkTransitionSimulationError):
            build_work_transition_simulation(source)
        source = sample()
        source["assumptions"]["draw_order"] = ["restricted"]
        with self.assertRaises(WorkTransitionSimulationError):
            build_work_transition_simulation(source)

    def test_growth_ledger_reconciles_posted_bucket_rounding(self):
        source = sample(["0.5"])
        source["months"] = 1
        source["assumptions"]["buckets"] = [
            {"bucket": "emergency_reserve", "opening_balance": "0.01"},
            {"bucket": "short_term", "opening_balance": "0.01"},
        ]
        source["assumptions"]["draw_order"] = ["emergency_reserve", "short_term"]
        source["assumptions"]["monthly_household_spending"] = "0"
        source["assumptions"]["deterministic_monthly_return_path"] = ["0.5"]
        result = build_work_transition_simulation(source)
        month = result["deterministic_baseline"]["months"][0]
        self.assertEqual(month["investment_growth"], "0.02")
        self.assertEqual(sum(Decimal(value) for value in month["closing_buckets"].values()), Decimal("0.04"))

    def test_maximum_horizon_and_return_have_supported_decimal_precision(self):
        source = sample()
        source["months"] = 600
        source["assumptions"]["monthly_household_spending"] = "0"
        source["assumptions"]["buckets"] = [{"bucket": "emergency_reserve", "opening_balance": "0.01"}]
        source["assumptions"]["draw_order"] = ["emergency_reserve"]
        source["assumptions"]["deterministic_monthly_return_path"] = ["1"] * 600
        source["assumptions"]["stress"] = {"monthly_return_path": ["1"] * 600, "trials": 1, "seed": 3}
        result = build_work_transition_simulation(source)
        self.assertEqual(len(result["deterministic_baseline"]["months"]), 600)
        self.assertTrue(len(result["stress"]["terminal_wealth"]["p50"]) > 100)

    def test_rejects_negative_subcent_cash_inputs_before_rounding(self):
        source = sample()
        source["assumptions"]["monthly_declared_costs"] = "-0.001"
        with self.assertRaises(WorkTransitionSimulationError):
            build_work_transition_simulation(source)

    def test_stress_result_preserves_declared_path_for_reproducibility(self):
        source = sample(["-0.1", "0.2"])
        result = build_work_transition_simulation(source)
        self.assertEqual(result["stress"]["declared_monthly_return_path"], ["-0.1", "0.2"])


if __name__ == "__main__":
    unittest.main()
