import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.services.operator_analysis import analyze_operator_question


class OperatorAnalysisTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name) / "family-office-workspace"
        (self.workspace / "snapshots").mkdir(parents=True)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _snapshot(self, name, schema_version):
        (self.workspace / "snapshots" / name).write_text(json.dumps({"schema_version": schema_version}), encoding="utf-8")

    def test_reuses_workspace_snapshot_metadata_and_keeps_question_private(self):
        self._snapshot("goals.json", "planning-goals/v1")
        self._snapshot("net-worth.json", "net-worth/v1")
        self._snapshot("availability.json", "asset-availability/v1")

        result = analyze_operator_question("Come gestisco la liquidita familiare?", self.workspace)

        self.assertEqual("ready_for_analysis", result["status"])
        self.assertEqual([], result["data_gaps"])
        self.assertIn("planning.liquidity_plan.build", result["required_tools"])
        self.assertTrue(result["assumptions"])
        self.assertNotIn("Come gestisco", json.dumps(result))
        self.assertFalse(result["policy"]["registered_tools_invoked"])

    def test_reports_missing_data_and_recoverable_next_action(self):
        self._snapshot("goals.json", "planning-goals/v1")

        result = analyze_operator_question("Come gestisco la liquidita familiare?", self.workspace)

        self.assertEqual("needs_information", result["status"])
        self.assertEqual({"asset-availability/v1", "net-worth/v1"}, {gap["source"] for gap in result["data_gaps"]})
        self.assertIn("rerun 'fo ask'", result["next_action"])

    def test_wealth_protection_estate_gaps_point_to_guided_wizards(self):
        result = analyze_operator_question("Come proteggo e organizzo la successione del patrimonio?", self.workspace)

        self.assertEqual("needs_information", result["status"])
        self.assertIn("fo planning wealth-strategy wizard --overwrite", result["next_action"])
        self.assertIn("fo planning protection wizard --overwrite", result["next_action"])
        self.assertIn("fo planning estate wizard --overwrite", result["next_action"])

    def test_refuses_unsupported_question_with_limits_and_no_tool_execution(self):
        result = analyze_operator_question("Scrivi una poesia sul mare", self.workspace)

        self.assertEqual("not_supported", result["status"])
        self.assertEqual([], result["required_tools"])
        self.assertIn("outside the registered", " ".join(result["limitations"]))

    def test_cli_is_question_first_and_readable_without_json(self):
        self._snapshot("goals.json", "planning-goals/v1")
        self._snapshot("net-worth.json", "net-worth/v1")
        self._snapshot("availability.json", "asset-availability/v1")
        self._snapshot("irrelevant.json", "tax-calculation/v1")
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["ask", "Come gestisco la liquidita familiare?", "--workspace", str(self.workspace)])

        self.assertEqual(0, exit_code)
        self.assertIn("Decision understood: Liquidity and cash-flow planning", stdout.getvalue())
        self.assertIn("No analysis or calculation has been run.", stdout.getvalue())
        self.assertIn("Relevant facts:", stdout.getvalue())
        self.assertIn("your planning goals", stdout.getvalue())
        self.assertNotIn("tax-calculation/v1", stdout.getvalue())
        self.assertNotIn("planning.liquidity_plan.build", stdout.getvalue())
        self.assertNotIn("ready_for_analysis", stdout.getvalue())
        self.assertIn("No separate analysis-plan command is available", stdout.getvalue())
        self.assertIn("Assumptions:", stdout.getvalue())
        self.assertNotIn("{\"schema_version\"", stdout.getvalue())

    def test_cli_explains_missing_facts_without_technical_snapshot_ids(self):
        self._snapshot("goals.json", "planning-goals/v1")
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["ask", "Come gestisco la liquidita familiare?", "--workspace", str(self.workspace)])

        self.assertEqual(2, exit_code)
        self.assertIn("Missing: your current net-worth summary", stdout.getvalue())
        self.assertIn("Missing: availability of your assets", stdout.getvalue())
        self.assertNotIn("net-worth/v1", stdout.getvalue())
        self.assertIn("rerun 'fo ask'", stdout.getvalue())

    def test_cli_prompts_only_for_question_and_explains_invalid_input(self):
        stdout = StringIO()
        with patch("builtins.input", return_value="   "), redirect_stdout(stdout):
            exit_code = main(["ask", "--workspace", str(self.workspace)])

        self.assertEqual(1, exit_code)
        self.assertIn("Next: run 'fo ask", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
