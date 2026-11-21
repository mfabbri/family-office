import copy
import unittest

from family_office_engine.services.work_transition_candidates import (
    WorkTransitionCandidateError,
    build_work_transition_candidates,
)


def sample():
    return {
        "schema_version": "work-transition-candidate-set/v1",
        "decision_question": "Which declared work transition scenarios meet the stated constraints?",
        "scenario_input": {
            "schema_version": "work-transition-simulation/v1",
            "decision_question": "Can the declared household assumptions support this scenario?",
            "months": 6,
            "assumptions": {
                "provenance": "synthetic candidate test",
                "annual_inflation_rate": "0",
                "annual_return_rate": "0",
                "monthly_net_income": "100",
                "monthly_household_spending": "50",
                "monthly_declared_tax": "0",
                "monthly_declared_costs": "0",
                "emergency_floor_months": "1",
                "draw_order": ["emergency_reserve"],
                "buckets": [{"bucket": "emergency_reserve", "opening_balance": "1000"}],
            },
        },
        "grid": {
            "full_time_exit_months": [2],
            "part_time_fractions": [0, "0.5"],
            "part_time_durations_months": [0, 2],
            "work_stop_months": [2, 4],
            "bridge_policies": [{"policy_id": "none", "income_streams": []}],
        },
        "constraints": {"minimum_terminal_spendable_assets": "0", "maximum_total_shortfall": "0"},
    }


class WorkTransitionCandidateTests(unittest.TestCase):
    def test_builds_stable_candidate_ids_and_derived_scenario_assumptions(self):
        source = sample()
        first = build_work_transition_candidates(source)
        second = build_work_transition_candidates(copy.deepcopy(source))
        self.assertEqual([x["content_hash"] for x in first["candidates"]],
                         [x["content_hash"] for x in second["candidates"]])
        included = [x for x in first["candidates"] if x["status"] == "included"]
        self.assertTrue(included)
        scenario = included[0]["scenario_input"]
        self.assertEqual(scenario["assumptions"]["monthly_net_income"], "0.00")
        self.assertTrue(all(x["assumption_status"] == "scenario_assumption"
                            for x in scenario["assumptions"]["income_streams"]))
        self.assertIsNone(first["pension_entitlement"]["verified_monthly_amount"])
        self.assertEqual(first["status"], "scenario_projection")

    def test_incompatible_grid_and_family_constraint_explain_exclusions(self):
        source = sample()
        result = build_work_transition_candidates(source)
        reasons = {x["reason"] for x in result["candidates"] if x["status"] == "excluded"}
        self.assertIn("work_stop_must_match_exit_plus_part_time_duration", reasons)
        source["constraints"]["minimum_terminal_spendable_assets"] = "100000"
        constrained = build_work_transition_candidates(source)
        self.assertTrue(all(x["reason"] == "minimum_terminal_spendable_assets_constraint_not_met"
                            for x in constrained["candidates"] if x["scenario_summary"] is not None))

    def test_rejects_duplicate_or_unbounded_grid(self):
        source = sample()
        source["grid"]["full_time_exit_months"] = [2, 2]
        with self.assertRaises(WorkTransitionCandidateError):
            build_work_transition_candidates(source)
        source = sample()
        source["grid"].update({"full_time_exit_months": list(range(1, 7)),
                               "part_time_fractions": [0, "0.2", "0.4", "0.6", "0.8", 1],
                               "part_time_durations_months": list(range(7)),
                               "work_stop_months": list(range(1, 7))})
        with self.assertRaisesRegex(WorkTransitionCandidateError, "candidate limit"):
            build_work_transition_candidates(source)

    def test_rejects_invalid_fraction_and_keeps_hypothetical_bridge_tagged(self):
        source = sample()
        source["grid"]["part_time_fractions"] = ["NaN"]
        with self.assertRaises(WorkTransitionCandidateError):
            build_work_transition_candidates(source)
        source = sample()
        source["grid"]["bridge_policies"] = [{"policy_id": "hypothetical", "income_streams": [{
            "monthly_net_amount": "25", "start_month": 3, "end_month": 4,
            "assumption_status": "scenario_assumption", "provenance": "synthetic bridge assumption",
        }]}]
        result = build_work_transition_candidates(source)
        self.assertTrue(any(x["status"] == "included" for x in result["candidates"]))
        self.assertIsNone(result["pension_entitlement"]["verified_start_month"])


if __name__ == "__main__":
    unittest.main()
