import copy
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from family_office_engine.cli.main import main
from family_office_engine.services.execution_plan import (
    ExecutionPlanError,
    build_execution_plan,
    demo_execution_plan_input,
    plan_execution,
)


class ExecutionPlanTest(unittest.TestCase):
    def test_builds_inspectable_registered_tool_dag_without_invocation(self):
        snapshot = plan_execution(demo_execution_plan_input())

        self.assertEqual("execution-plan/v1", snapshot["schema_version"])
        self.assertEqual("ready", snapshot["status"])
        self.assertEqual(["pension_scenario", "spanish_theoretical", "eu_pro_rata", "work_exit"], snapshot["execution_order"])
        self.assertTrue(snapshot["policy"]["registered_tools_only"])
        self.assertFalse(snapshot["policy"]["planner_invokes_tools"])
        self.assertFalse(snapshot["policy"]["planner_calculates_tax_pension_financial_values"])
        self.assertTrue(all(node["execution_state"] == "not_executed" for node in snapshot["nodes"]))
        self.assertTrue(all("tool_registered" in node["checks"] for node in snapshot["nodes"]))

    def test_writes_plan_from_json_input(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.json"
            output_path = Path(tmp_dir) / "output.json"
            input_path.write_text(json.dumps(demo_execution_plan_input()), encoding="utf-8")

            snapshot = build_execution_plan(input_path, output_path)

            self.assertTrue(output_path.exists())
            self.assertEqual(snapshot["reproducibility"]["content_hash"], json.loads(output_path.read_text(encoding="utf-8"))["reproducibility"]["content_hash"])

    def test_rejects_cycle(self):
        value = demo_execution_plan_input()
        value["nodes"][0]["depends_on"] = ["work_exit"]
        value["nodes"][3]["depends_on"].append("pension_scenario")

        with self.assertRaisesRegex(ExecutionPlanError, "dependency cycle"):
            plan_execution(value)

    def test_rejects_unregistered_or_catalog_unauthorized_tool(self):
        missing = demo_execution_plan_input()
        missing["nodes"][0]["tool_id"] = "planning.not-registered.build"
        with self.assertRaisesRegex(ExecutionPlanError, "not registered"):
            plan_execution(missing)

        unauthorized = demo_execution_plan_input()
        unauthorized["nodes"][0]["tool_id"] = "planning.real_estate_plan.build"
        with self.assertRaisesRegex(ExecutionPlanError, "outside selected catalog intents"):
            plan_execution(unauthorized)

    def test_rejects_sensitive_input_without_explicit_consent(self):
        value = demo_execution_plan_input()
        value["nodes"][0]["input_bindings"]["input_path"]["sensitivity"] = "sensitive"

        with self.assertRaisesRegex(ExecutionPlanError, "sensitive input is not authorized"):
            plan_execution(value)

    def test_rejects_stale_router_catalog_lineage(self):
        value = copy.deepcopy(demo_execution_plan_input())
        value["question_intent"]["catalog"]["content_hash"] = "0" * 64

        with self.assertRaisesRegex(ExecutionPlanError, "catalog lineage is stale"):
            plan_execution(value)

    def test_cli_demo_uses_short_command_and_never_executes_tools(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "execution-plan.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["orchestration", "execution-plan", "demo", "--output", str(output)])

            self.assertEqual(0, exit_code)
            self.assertTrue(output.exists())
            self.assertIn("no tool invocations", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
