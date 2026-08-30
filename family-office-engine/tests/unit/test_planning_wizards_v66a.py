import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main


class PlanningWizardsV66aTests(unittest.TestCase):
    def _run(self, command, answers, output):
        stdout = io.StringIO()
        workspace = output.parent.parent
        with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(workspace)}), patch("builtins.input", side_effect=answers), redirect_stdout(stdout):
            exit_code = main(command + ["--input", str(output)])
        self.assertEqual(0, exit_code, stdout.getvalue())
        return json.loads(output.read_text(encoding="utf-8")), stdout.getvalue()

    def test_protection_wizard_writes_private_declared_input_and_gaps(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "planning" / "protection-gap.json"
            data, text = self._run(
                ["planning", "protection", "wizard"],
                ["case_private", "2026-08-30", "", "", "beneficiary_review"], output,
            )
            self.assertEqual("ProtectionGapInput", data["record_type"])
            self.assertEqual("user_declared_input", data["family_needs"][0]["provenance"][0]["type"])
            self.assertIn("unknown_policy_coverage", {gap["code"] for gap in data["data_gaps"]})
            self.assertIn("next: `fo planning protection build`", text)
            snapshot_path = output.with_suffix(".snapshot.json")
            self.assertEqual(0, main(["planning", "protection", "build", "--input", str(output), "--output", str(snapshot_path)]))
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            self.assertEqual("review_required", snapshot["protection_gaps"][0]["status"])

    def test_estate_wizard_accepts_contract_minimum_and_marks_review_gaps(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "planning" / "estate-plan.json"
            data, text = self._run(
                ["planning", "estate", "wizard"],
                ["case_private", "2026-08-30", "person_a", "asset_a", ""], output,
            )
            self.assertEqual("EstatePlanInput", data["record_type"])
            self.assertEqual("user_declared_input", data["assets"][0]["provenance"][0]["type"])
            self.assertIn("family_and_allocation_review_required", {gap["code"] for gap in data["data_gaps"]})
            self.assertIn("next: `fo planning estate build`", text)
            self.assertEqual(0, main(["planning", "estate", "build", "--input", str(output), "--output", str(output.with_suffix(".snapshot.json"))]))

    def test_wealth_strategy_wizard_requires_two_declared_packages_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "planning" / "wealth-strategy-input.json"
            data, text = self._run(
                ["planning", "wealth-strategy", "wizard"],
                ["case_private", "2026-08-30", "liquidity first", "protection first"], output,
            )
            self.assertEqual("WealthStrategyInput", data["record_type"])
            self.assertEqual(2, len(data["packages"]))
            self.assertIn("wizard_requires_source_review", {gap["code"] for gap in data["data_gaps"]})
            self.assertIn("next: `fo planning wealth-strategy build`", text)
            self.assertEqual(0, main(["planning", "wealth-strategy", "build", "--input", str(output), "--output", str(output.with_suffix(".snapshot.json"))]))
            stdout = io.StringIO()
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(output.parent.parent)}), redirect_stdout(stdout):
                self.assertEqual(0, main(["planning", "wealth-strategy", "wizard", "--input", str(output)]))
            self.assertIn("existing input found", stdout.getvalue())

    def test_protection_wizard_saves_private_progress_on_interrupt(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "planning" / "protection-gap.json"
            stdout = io.StringIO()
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(output.parent.parent)}), patch("builtins.input", side_effect=["case_private", KeyboardInterrupt]), redirect_stdout(stdout):
                self.assertEqual(1, main(["planning", "protection", "wizard", "--input", str(output)]))
            progress = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("case_private", progress["household_id"])
            self.assertEqual("wizard_incomplete", progress["data_gaps"][0]["code"])
            self.assertIn("resume/revise", stdout.getvalue())

    def test_wizard_rejects_input_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp_dir, tempfile.TemporaryDirectory() as outside:
            workspace = Path(tmp_dir)
            output = Path(outside) / "protection-gap.json"
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(workspace)}), patch("builtins.input", side_effect=AssertionError("must reject before prompting")):
                self.assertEqual(1, main(["planning", "protection", "wizard", "--input", str(output)]))
            self.assertFalse(output.exists())
