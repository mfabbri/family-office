import copy
import unittest

from family_office_engine.services.work_transition_plan import (
    WorkTransitionPlanError,
    build_work_transition_plan,
    synthetic_work_transition_plan_input,
)


class WorkTransitionPlanTests(unittest.TestCase):
    def test_golden_composes_bridge_simulation_candidates_and_optimizer(self):
        source = synthetic_work_transition_plan_input()
        result = build_work_transition_plan(source)
        repeated = build_work_transition_plan(copy.deepcopy(source))

        self.assertEqual(result, repeated)
        self.assertEqual(result["schema_version"], "work-transition-plan/v1")
        self.assertEqual(result["status"], "scenario_projection")
        self.assertEqual(
            [item["scenario_id"] for item in result["bridge_projection"]["scenarios"]],
            ["work_100", "work_60", "work_0"],
        )
        self.assertEqual([item["stage"] for item in result["phase_plan"]], ["full_time", "part_time", "stop"])
        self.assertEqual(result["candidate_set"]["candidate_count"], 16)
        self.assertTrue(result["risk_metrics"]["optimizer_earliest_full_time_exit_date"])
        self.assertTrue(result["rejected_candidates"])
        self.assertTrue(result["risk_metrics"]["simulation_stress"])
        self.assertEqual(result["pension_entitlement"], {
            "status": "not_assessed", "verified_start_date": None, "verified_monthly_amount": None,
        })
        gap_codes = {item["code"] for item in result["data_gaps"]}
        self.assertIn("source_bound_pension_entitlement_missing", gap_codes)
        self.assertIn("spouse_income_excluded_from_linear_bridge", gap_codes)
        self.assertTrue(all(
            item["status"] == "scenario_projection"
            for item in (result["bridge_projection"], result["candidate_set"], result["optimization"])
        ))

    def test_rejects_bad_schema_and_missing_readiness(self):
        source = synthetic_work_transition_plan_input()
        source["schema_version"] = "work-transition-plan/v2"
        with self.assertRaisesRegex(WorkTransitionPlanError, "schema_version"):
            build_work_transition_plan(source)

        source = synthetic_work_transition_plan_input()
        source["readiness"] = {"status": "unknown", "data_gaps": []}
        with self.assertRaisesRegex(WorkTransitionPlanError, "readiness"):
            build_work_transition_plan(source)

    def test_rejects_untagged_hypothetical_pension_and_invalid_phase(self):
        source = synthetic_work_transition_plan_input()
        source["bridge_input"]["assumptions"]["hypothetical_pension"].pop("assumption_status")
        with self.assertRaisesRegex(WorkTransitionPlanError, "scenario_assumption"):
            build_work_transition_plan(source)

        source = synthetic_work_transition_plan_input()
        source["phase_plan"][1]["work_fraction"] = "0.75"
        with self.assertRaisesRegex(WorkTransitionPlanError, "work fraction"):
            build_work_transition_plan(source)


if __name__ == "__main__":
    unittest.main()
