import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.tool_registry import (
    SCHEMA_VERSION,
    ToolRegistryError,
    build_tool_registry,
    invoke_registered_tool,
    _coerce_path,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROTECTION_SAMPLE = REPOSITORY_ROOT / "family-office-engine" / "examples" / "protection-gap-sample.json"


class ToolRegistryTest(unittest.TestCase):
    def test_builds_valid_registry_snapshot(self):
        snapshot = build_tool_registry()

        self.assertEqual(snapshot["schema_version"], SCHEMA_VERSION)
        self.assertEqual(snapshot["status"], "complete")
        self.assertGreaterEqual(snapshot["tool_count"], 10)
        self.assertEqual(snapshot["tool_count"], len(snapshot["tools"]))
        self.assertTrue(snapshot["policy"]["llm_may_invoke_only_registered_tools"])
        self.assertTrue(snapshot["policy"]["llm_must_not_calculate_tax_pension_financial_values"])
        self.assertRegex(snapshot["reproducibility"]["content_hash"], r"^[0-9a-f]{64}$")
        tool_ids = {tool["tool_id"] for tool in snapshot["tools"]}
        self.assertIn("planning.wealth_strategy.build", tool_ids)
        self.assertIn("planning.work_exit_feasibility.build", tool_ids)
        self.assertIn("planning.work_transition_simulation.build", tool_ids)
        self.assertIn("planning.work_transition_candidates.build", tool_ids)
        self.assertIn("planning.work_transition_optimizer.build", tool_ids)
        self.assertIn("knowledge.citations.search", tool_ids)
        self.assertIn("orchestration.guardrails.evaluate", tool_ids)

    def test_new_work_transition_tools_are_registered_with_versioned_scenario_contracts(self):
        registry = build_tool_registry()
        tools = {item["tool_id"]: item for item in registry["tools"]}
        self.assertEqual(registry["tool_count"], 21)
        expected = {
            "planning.work_transition_simulation.build": "work-transition-simulation/v1",
            "planning.work_transition_candidates.build": "work-transition-candidate-set/v1",
            "planning.work_transition_optimizer.build": "work-transition-optimizer/v1",
        }
        for tool_id, version in expected.items():
            with self.subTest(tool_id=tool_id):
                self.assertEqual(tools[tool_id]["input_schema_version"], version)
                self.assertEqual(tools[tool_id]["output_schema_version"], version)
                self.assertEqual(tools[tool_id]["required_parameters"], ["input_path", "output_path"])
                self.assertIn("professional_review_required", tools[tool_id]["authorization_policy"])
        legacy = tools["planning.work_exit_feasibility.build"]
        self.assertEqual(legacy["input_schema_version"], "work-exit-feasibility-input/v1")
        self.assertEqual(legacy["output_schema_version"], "work-exit-feasibility/v1")
        self.assertEqual(legacy["required_parameters"], ["input_path", "rule_pack_path", "output_path"])
        self.assertEqual(legacy["optional_parameters"], ["inps_snapshot_path", "pro_rata_snapshot_path"])
        self.assertEqual(legacy["prerequisites"], ["it.inps-theoretical-pension.2026.v1", "it-es-eu-pension-pro-rata/v1"])

    def test_invokes_registered_work_transition_pipeline_and_keeps_entitlement_unassessed(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            simulation_input_path = root / "simulation-input.json"
            simulation_output_path = root / "simulation-output.json"
            candidates_input_path = root / "candidate-input.json"
            candidates_output_path = root / "candidate-output.json"
            optimizer_input_path = root / "optimizer-input.json"
            optimizer_output_path = root / "optimizer-output.json"
            simulation = {
                "schema_version": "work-transition-simulation/v1",
                "decision_question": "Can the declared work-transition scenario fund household spending?",
                "months": 3,
                "assumptions": {
                    "provenance": "synthetic registry test",
                    "annual_inflation_rate": "0",
                    "annual_return_rate": "0",
                    "monthly_net_income": "100",
                    "monthly_household_spending": "40",
                    "monthly_declared_tax": "0",
                    "monthly_declared_costs": "0",
                    "emergency_floor_months": "1",
                    "draw_order": ["emergency_reserve", "short_term"],
                    "buckets": [
                        {"bucket": "emergency_reserve", "opening_balance": "500"},
                        {"bucket": "short_term", "opening_balance": "0"},
                        {"bucket": "restricted", "opening_balance": "700"},
                    ],
                },
            }
            simulation_input_path.write_text(json.dumps(simulation), encoding="utf-8")
            simulation_result = invoke_registered_tool(
                "planning.work_transition_simulation.build", "work-transition-simulation/v1",
                {"input_path": simulation_input_path, "output_path": simulation_output_path},
            )
            self.assertEqual(simulation_result["output"]["status"], "scenario_projection")
            self.assertIsNone(simulation_result["output"]["pension_entitlement"]["verified_start_month"])
            self.assertTrue(simulation_output_path.is_file())

            candidates_input = {
                "schema_version": "work-transition-candidate-set/v1",
                "decision_question": simulation["decision_question"],
                "scenario_input": simulation,
                "grid": {
                    "full_time_exit_months": [1], "part_time_fractions": [0],
                    "part_time_durations_months": [0], "work_stop_months": [1],
                    "bridge_policies": [{"policy_id": "none", "income_streams": []}],
                },
            }
            candidates_input_path.write_text(json.dumps(candidates_input), encoding="utf-8")
            candidates_result = invoke_registered_tool(
                "planning.work_transition_candidates.build", "work-transition-candidate-set/v1",
                {"input_path": candidates_input_path, "output_path": candidates_output_path},
            )
            self.assertEqual(candidates_result["output"]["included_count"], 1)

            optimizer_input = {
                "schema_version": "work-transition-optimizer/v1",
                "decision_question": simulation["decision_question"],
                "plan_start_month": "2027-01",
                "candidate_set": candidates_result["output"],
                "policy": {
                    "stress": {"monthly_return_path": ["0", "0", "0"], "trials": 2, "seed": 7},
                    "constraints": {
                        "maximum_total_shortfall": "0", "minimum_success_probability": "1",
                        "minimum_p05_terminal_wealth": "0", "minimum_liquid_buffer": "0",
                        "minimum_post_stop_months": 1,
                    },
                    "objective": {"method": "lexicographic", "criteria": [
                        {"metric": "earliest_transition_month", "direction": "minimize"}
                    ]},
                },
            }
            optimizer_input_path.write_text(json.dumps(optimizer_input), encoding="utf-8")
            optimizer_result = invoke_registered_tool(
                "planning.work_transition_optimizer.build", "work-transition-optimizer/v1",
                {"input_path": optimizer_input_path, "output_path": optimizer_output_path},
            )
            self.assertEqual(optimizer_result["output"]["status"], "scenario_projection")
            self.assertIsNone(optimizer_result["output"]["pension_entitlement"]["verified_start_month"])
            self.assertTrue(optimizer_output_path.is_file())

    def test_work_transition_registry_rejects_bad_json_and_same_input_output(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = Path(tmp_dir) / "bad.json"
            source.write_text("{bad json", encoding="utf-8")
            with self.assertRaisesRegex(ToolRegistryError, "Cannot read valid JSON input"):
                invoke_registered_tool("planning.work_transition_simulation.build", "work-transition-simulation/v1",
                                      {"input_path": source, "output_path": Path(tmp_dir) / "result.json"})
            with self.assertRaisesRegex(ToolRegistryError, "must be different files"):
                invoke_registered_tool("planning.work_transition_simulation.build", "work-transition-simulation/v1",
                                      {"input_path": source, "output_path": source})

    def test_writes_registry_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "tool-registry.json"

            snapshot = build_tool_registry(output_path)

            self.assertTrue(output_path.exists())
            self.assertEqual(snapshot["schema_version"], "tool-registry/v1")

    def test_unknown_tool_is_rejected(self):
        with self.assertRaisesRegex(ToolRegistryError, "Unknown registered tool"):
            invoke_registered_tool("planning.unknown.build", "unknown/v1", {})

    def test_incompatible_requested_output_version_is_rejected(self):
        with self.assertRaisesRegex(ToolRegistryError, "produces protection-gap/v1"):
            invoke_registered_tool(
                "planning.protection_gap.build",
                "protection-gap/v2",
                {"input_path": PROTECTION_SAMPLE, "output_path": "unused.json"},
            )

    def test_invokes_registered_tool_with_validated_parameters(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "protection.json"

            result = invoke_registered_tool(
                "planning.protection_gap.build",
                "protection-gap/v1",
                {"input_path": PROTECTION_SAMPLE, "output_path": output_path},
            )

            self.assertEqual(result["schema_version"], "tool-invocation/v1")
            self.assertEqual(result["tool"]["actual_output_schema_version"], "protection-gap/v1")
            self.assertEqual(result["output"]["schema_version"], "protection-gap/v1")
            self.assertTrue(output_path.exists())

    def test_missing_required_parameter_is_rejected(self):
        with self.assertRaisesRegex(ToolRegistryError, "Missing required parameters"):
            invoke_registered_tool("planning.protection_gap.build", "protection-gap/v1", {"input_path": PROTECTION_SAMPLE})

    def test_repeated_snapshot_paths_are_normalized_for_wealth_strategy(self):
        values = _coerce_path(["one.json", Path("two.json")], "investment_opportunity_comparison_snapshot_paths")

        self.assertEqual([Path("one.json"), Path("two.json")], values)
        with self.assertRaisesRegex(ToolRegistryError, "list of path strings"):
            _coerce_path("one.json", "investment_opportunity_comparison_snapshot_paths")


if __name__ == "__main__":
    unittest.main()
