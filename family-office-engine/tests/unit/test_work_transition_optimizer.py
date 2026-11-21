import copy
import unittest

from family_office_engine.services.work_transition_candidates import build_work_transition_candidates
from family_office_engine.services.work_transition_optimizer import (
    WorkTransitionOptimizerError,
    build_work_transition_optimizer,
)


def candidate_set(work_stop_months=(1, 2, 3), exit_months=(1, 2), fractions=(0, "0.5"), durations=(0, 1)):
    data = {
        "schema_version": "work-transition-candidate-set/v1",
        "decision_question": "Which work transition paths meet the family's declared limits?",
        "scenario_input": {
            "schema_version": "work-transition-simulation/v1",
            "decision_question": "Can the declared assumptions support this path?",
            "months": 4,
            "assumptions": {
                "provenance": "synthetic optimizer test", "annual_inflation_rate": "0",
                "annual_return_rate": "0", "monthly_net_income": "100",
                "monthly_household_spending": "50", "monthly_declared_tax": "0",
                "monthly_declared_costs": "0", "emergency_floor_months": "1",
                "draw_order": ["emergency_reserve"],
                "buckets": [{"bucket": "emergency_reserve", "opening_balance": "1000"}],
            },
        },
        "grid": {"full_time_exit_months": list(exit_months), "part_time_fractions": list(fractions),
                  "part_time_durations_months": list(durations), "work_stop_months": list(work_stop_months),
                  "bridge_policies": [{"policy_id": "none", "income_streams": []}]},
        "constraints": {"maximum_total_shortfall": "0", "minimum_terminal_spendable_assets": "0"},
    }
    return build_work_transition_candidates(data)


def policy(objective=None):
    return {"stress": {"monthly_return_path": ["0", "0", "0", "0"], "trials": 8, "seed": 19},
            "constraints": {"maximum_total_shortfall": "0", "minimum_success_probability": "1.0000",
                            "minimum_p05_terminal_wealth": "950", "minimum_liquid_buffer": "0",
                            "minimum_post_stop_months": 1},
            "objective": objective,
            "sensitivity_variants": [{"variant_id": "stricter_p05", "constraints": {"minimum_p05_terminal_wealth": "2000"}}]}


def optimizer_input(candidates=None, objective=None):
    return {"schema_version": "work-transition-optimizer/v1",
            "decision_question": "Which transition is feasible and which best matches the declared objective?",
            "plan_start_month": "2027-01", "candidate_set": candidates or candidate_set(),
            "policy": policy(objective)}


class WorkTransitionOptimizerTests(unittest.TestCase):
    def test_earliest_date_is_separate_and_month_boundary_is_explicit(self):
        result = build_work_transition_optimizer(optimizer_input())
        self.assertEqual(result["earliest_full_time_exit_date"], "2027-02-01")
        self.assertIsNone(result["recommended_full_time_exit_date"])
        self.assertIsNone(result["full_work_exit_date"])
        self.assertEqual(result["pension_entitlement"]["verified_start_month"], None)

    def test_objective_recommendation_uses_one_candidate_for_transition_and_stop(self):
        objective = {"method": "lexicographic", "criteria": [{"metric": "p05_terminal_wealth", "direction": "maximize"}],
                     "tie_breaker": "earliest_transition"}
        result = build_work_transition_optimizer(optimizer_input(objective=objective))
        self.assertIsNotNone(result["recommended_candidate_id"])
        selected = next(x for x in result["evaluated_candidates"] if x["candidate_id"] == result["recommended_candidate_id"])
        self.assertEqual(result["earliest_full_time_exit_date"], "2027-02-01")
        self.assertEqual(result["recommended_full_time_exit_date"], "2027-03-01")
        self.assertEqual(result["recommended_fte_plan"], selected["parameters"])
        self.assertEqual(result["sensitivity"][0]["variant_id"], "stricter_p05")

    def test_thresholds_are_inclusive_and_part_time_can_pass_when_no_work_fails(self):
        data = optimizer_input()
        result = build_work_transition_optimizer(data)
        candidates = [x for x in result["evaluated_candidates"] if x["status"] == "feasible"]
        self.assertTrue(any(x["parameters"]["part_time_fraction"] == "0.5" for x in candidates))
        self.assertTrue(any(x["parameters"]["part_time_fraction"] == "0" and x["status"] == "infeasible"
                            for x in result["evaluated_candidates"]))
        self.assertEqual(result["data_gaps"][0]["code"], "family_objective_not_declared")

    def test_tied_or_absent_objective_emits_no_recommendation_and_hash_drift_is_unknown(self):
        objective = {"method": "lexicographic", "criteria": [{"metric": "success_probability", "direction": "maximize"}]}
        result = build_work_transition_optimizer(optimizer_input(objective=objective))
        self.assertIsNone(result["recommended_candidate_id"])
        tampered = copy.deepcopy(candidate_set())
        included = next(x for x in tampered["candidates"] if x["status"] == "included")
        included["scenario_input"]["assumptions"]["monthly_net_income"] = "999"
        invalid_result = build_work_transition_optimizer(optimizer_input(tampered, objective))
        self.assertIsNone(invalid_result["earliest_full_time_exit_date"])
        self.assertTrue(invalid_result["unassessed_candidates"])
        changed_status = copy.deepcopy(candidate_set())
        changed_status["candidates"][0]["status"] = "not_assessed"
        status_result = build_work_transition_optimizer(optimizer_input(changed_status))
        self.assertEqual(status_result["status"], "not_assessed")
        self.assertIsNone(status_result["earliest_full_time_exit_date"])

    def test_missing_or_inconsistent_stress_is_rejected(self):
        source = optimizer_input()
        source["policy"]["stress"]["monthly_return_path"] = ["0"]
        with self.assertRaises(WorkTransitionOptimizerError):
            build_work_transition_optimizer(source)
        source = optimizer_input()
        source["policy"]["stress"]["trials"] = 10000
        source["policy"]["sensitivity_variants"] = [{"variant_id": str(i), "constraints": {}} for i in range(20)]
        result = build_work_transition_optimizer(source)
        self.assertEqual(result["status"], "not_assessed")
        self.assertIsNone(result["earliest_full_time_exit_date"])
        self.assertTrue(result["unassessed_candidates"])

    def test_declared_reversibility_requirement_is_a_hard_gate(self):
        source = optimizer_input()
        source["policy"]["constraints"].update({"require_reversible": True, "reversible_candidate_ids": []})
        result = build_work_transition_optimizer(source)
        self.assertTrue(all(x["reason"] == "reversibility_not_attested_by_candidate_input"
                            for x in result["evaluated_candidates"] if x["status"] == "infeasible"))
        self.assertIsNone(result["earliest_full_time_exit_date"])

    def test_invalid_thresholds_and_incomplete_post_stop_horizon_fail_closed(self):
        for value in ("-Infinity", "NaN", "-0.01", "1.01"):
            source = optimizer_input()
            source["policy"]["constraints"]["minimum_success_probability"] = value
            with self.subTest(probability=value), self.assertRaises(WorkTransitionOptimizerError):
                build_work_transition_optimizer(source)
        source = optimizer_input(candidate_set(work_stop_months=(4,), exit_months=(4,), fractions=(0,), durations=(0,)))
        result = build_work_transition_optimizer(source)
        self.assertIsNone(result["earliest_full_time_exit_date"])
        self.assertTrue(any(x.get("reason") == "post_stop_horizon_coverage_incomplete"
                            for x in result["evaluated_candidates"]))

    def test_sensitivity_reassesses_post_stop_coverage_in_both_directions(self):
        narrow_set = candidate_set(work_stop_months=(3,), exit_months=(1,), fractions=("0.5",), durations=(2,))
        source = optimizer_input(narrow_set)
        source["policy"]["sensitivity_variants"] = [{"variant_id": "needs_two_months",
                                                     "constraints": {"minimum_post_stop_months": 2}}]
        base_one = build_work_transition_optimizer(source)
        variant = base_one["sensitivity"][0]
        self.assertEqual(base_one["earliest_full_time_exit_date"], "2027-02-01")
        self.assertIsNone(variant["earliest_full_time_exit_date"])
        self.assertEqual(variant["feasible_count"], 0)
        self.assertTrue(variant["unassessed_candidate_ids"])

        source["policy"]["constraints"]["minimum_post_stop_months"] = 2
        source["policy"]["sensitivity_variants"][0]["constraints"]["minimum_post_stop_months"] = 1
        base_two = build_work_transition_optimizer(source)
        self.assertIsNone(base_two["earliest_full_time_exit_date"])
        self.assertEqual(base_two["sensitivity"][0]["earliest_full_time_exit_date"], "2027-02-01")
        self.assertEqual(base_two["sensitivity"][0]["feasible_count"], 1)
        self.assertEqual(base_two["sensitivity"][0]["unassessed_candidate_ids"], [])


if __name__ == "__main__":
    unittest.main()
