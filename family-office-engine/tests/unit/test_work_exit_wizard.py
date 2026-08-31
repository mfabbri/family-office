import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main


class WorkExitWizardTests(unittest.TestCase):
    def _run(self, workspace, answers, *, overwrite=False):
        input_path = workspace / "planning" / "work-exit.json"
        readiness_input = workspace / "planning" / "readiness.json"
        readiness_output = workspace / "snapshots" / "readiness.json"
        command = ["planning", "work-exit", "wizard", "--input", str(input_path), "--readiness-input", str(readiness_input), "--readiness-output", str(readiness_output)]
        if overwrite:
            command.append("--overwrite")
        stdout = io.StringIO()
        with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(workspace)}), patch("family_office_engine.services.work_transition_readiness._workspace_root", return_value=workspace), patch("builtins.input", side_effect=answers), redirect_stdout(stdout):
            code = main(command)
        return code, input_path, readiness_input, readiness_output, stdout.getvalue()

    def test_wizard_writes_workspace_local_inputs_and_readiness_summary(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            code, input_path, manifest_path, readiness_path, text = self._run(workspace, ["case_private", "2026-08-30", "1970-05-20", "1972-03-10", "2035-01-01", "60000.00", "100000.00", ""])
            self.assertEqual(0, code, text)
            work_exit = json.loads(input_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            self.assertEqual("work-exit-feasibility-input/v1", work_exit["schema_version"])
            self.assertEqual("work-transition-readiness-input/v1", manifest["schema_version"])
            self.assertEqual([], manifest["sources"])
            self.assertEqual("blocked", readiness["status"])
            self.assertIn("Fatti:", text)
            self.assertIn("Prossima azione:", text)

    def test_wizard_resumes_only_with_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            self._run(workspace, ["case_private", "2026-08-30", "1970-05-20", "1972-03-10", "2035-01-01", "60000.00", "100000.00", ""])
            code, _, _, _, text = self._run(workspace, [])
            self.assertEqual(0, code)
            self.assertIn("bozza gia presente", text)
            code, input_path, _, _, _ = self._run(workspace, ["case_revised", "", "", "", "", "", "", ""], overwrite=True)
            self.assertEqual(0, code)
            self.assertEqual("case_revised", json.loads(input_path.read_text(encoding="utf-8"))["household_id"])

    def test_uncertain_answers_are_data_gaps(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            code, input_path, _, _, _ = self._run(workspace, ["case_private", "2026-08-30", "", "", "2035-01-01", "", "", ""])
            self.assertEqual(0, code)
            gaps = {gap["code"] for gap in json.loads(input_path.read_text(encoding="utf-8"))["data_gaps"]}
            self.assertTrue({"unknown_primary_date_of_birth", "unknown_spouse_date_of_birth", "unknown_annual_spending_need", "unknown_available_bridge_assets"} <= gaps)

    def test_unknown_primary_is_kept_as_blocking_adult_and_does_not_suggest_build(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            code, input_path, _, _, text = self._run(workspace, ["case_private", "2026-08-30", "", "1972-03-10", "2035-01-01", "60000.00", "100000.00", ""])
            self.assertEqual(0, code)
            data = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(["primary", "spouse"], [adult["person_id"] for adult in data["adults"]])
            self.assertIn("il build resta bloccato", text)

    def test_unknown_spouse_does_not_suggest_build(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            code, _, _, _, text = self._run(workspace, ["case_private", "2026-08-30", "1970-05-20", "", "2035-01-01", "60000.00", "100000.00", ""])
            self.assertEqual(0, code)
            self.assertIn("completa le date di nascita degli adulti", text)

    def test_numeric_values_are_reprompted_until_valid(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            code, input_path, _, _, text = self._run(workspace, ["case_private", "2026-08-30", "1970-05-20", "1972-03-10", "2035-01-01", "-1", "60000.00", "-2", "100000.00", "0", "30"], overwrite=False)
            self.assertEqual(0, code, text)
            data = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual("60000.00", data["sustainability_constraints"]["annual_spending_need"])
            self.assertEqual("100000.00", data["sustainability_constraints"]["available_bridge_assets"])

    def test_readiness_manifest_has_only_contract_fields_and_paths_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            _, _, manifest_path, _, _ = self._run(workspace, ["case_private", "2026-08-30", "1970-05-20", "1972-03-10", "2035-01-01", "60000.00", "100000.00", ""])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertNotIn("data_gaps", manifest)
            self.assertEqual({"schema_version", "record_type", "household_id", "as_of_date", "household_members", "required_inputs", "sources"}, set(manifest))
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(workspace)}), patch("builtins.input", side_effect=AssertionError("must not prompt")):
                self.assertEqual(1, main(["planning", "work-exit", "wizard", "--input", str(workspace / "planning" / "same.json"), "--readiness-input", str(workspace / "planning" / "same.json")]))

    def test_wizard_rejects_paths_outside_workspace_and_cli_help_lists_it(self):
        with tempfile.TemporaryDirectory() as tmp_dir, tempfile.TemporaryDirectory() as outside:
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": tmp_dir}), patch("builtins.input", side_effect=AssertionError("must not prompt")):
                self.assertEqual(1, main(["planning", "work-exit", "wizard", "--input", str(Path(outside) / "work-exit.json")]))
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as exit_info:
                main(["planning", "work-exit", "--help"])
            self.assertEqual(0, exit_info.exception.code)
        self.assertIn("wizard", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
