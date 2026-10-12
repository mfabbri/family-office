import io
import hashlib
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main


class WorkTransitionPlanCliTest(unittest.TestCase):
    def test_projection_command_is_exposed_without_retirement_date_arguments(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as exit_info:
                main(["planning", "work-transition", "projection", "build", "--help"])

        self.assertEqual(0, exit_info.exception.code)
        help_text = stdout.getvalue()
        self.assertIn("periodized projection input", help_text)
        self.assertNotIn("retirement", help_text.lower())

    def test_plan_creates_workspace_readiness_without_asking_for_retirement_date(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            stdout = io.StringIO()
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(workspace)}), patch(
                "builtins.input",
                side_effect=[
                    "household_test", "2026-10-11",
                    "1", "full_time", "2026-10-01", "2026-10-01",
                    "1", "not_working", "2026-10-01", "2026-10-01",
                    "", "",
                ],
            ) as prompt, redirect_stdout(stdout):
                code = main(["planning", "work-transition", "plan"])

            output = stdout.getvalue()
            self.assertEqual(0, code, output)
            self.assertEqual(12, prompt.call_count)
            self.assertIn("Domanda familiare:", output)
            self.assertIn("Fatti:", output)
            self.assertIn("Assunzioni:", output)
            self.assertIn("Data gaps:", output)
            self.assertIn("Limiti:", output)
            self.assertIn("Prossima azione:", output)
            self.assertNotIn("mese pensionamento", output.lower())
            self.assertNotIn("data candidata", output.lower())
            self.assertIn("nessuna data pensionistica", output.lower())
            self.assertIn("Scenario non calcolato:", output)
            self.assertIn("scenario_or_readiness_blocked", output)
            self.assertIn("pension_entitlement_timeline_not_implemented", output)
            manifest_path = workspace / "planning" / "work-transition-readiness.json"
            readiness_path = workspace / "snapshots" / "work-transition-readiness.snapshot.json"
            self.assertTrue(manifest_path.is_file())
            self.assertTrue(readiness_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual("work-transition-readiness-input/v1", manifest["schema_version"])
            self.assertEqual("household_test", manifest["household_id"])
            self.assertEqual([], manifest["sources"])
            self.assertNotIn("candidate_dates", manifest)
            self.assertNotIn("retirement_date", manifest)
            scenario_input = workspace / "planning" / "work-transition-scenario.json"
            projection_input = workspace / "planning" / "employment-income-projection.json"
            self.assertTrue(scenario_input.is_file())
            self.assertTrue(projection_input.is_file())
            scenario_draft = json.loads(scenario_input.read_text(encoding="utf-8"))
            projection_draft = json.loads(projection_input.read_text(encoding="utf-8"))
            self.assertEqual("work-transition-scenario-input/v1", scenario_draft["schema_version"])
            self.assertEqual("employment-income-projection-input/v1", projection_draft["schema_version"])
            self.assertEqual([], projection_draft["periods"])
            self.assertNotIn("candidate_dates", scenario_draft)
            self.assertNotIn("retirement_date", scenario_draft)

    def test_plan_rejects_paths_outside_private_workspace(self):
        with tempfile.TemporaryDirectory() as workspace_dir, tempfile.TemporaryDirectory() as outside_dir:
            outside_input = Path(outside_dir) / "manifest.json"
            stdout = io.StringIO()
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": workspace_dir}), redirect_stdout(stdout):
                code = main([
                    "planning", "work-transition", "plan", "--input", str(outside_input)
                ])

            self.assertEqual(1, code)
            self.assertIn("must be inside workspace", stdout.getvalue())
            self.assertFalse(outside_input.exists())

    def test_plan_builds_scenario_and_projection_from_declared_monthly_inputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            stdout = io.StringIO()

            def ready_setup(manifest_path, output_path, overwrite=False):
                core = {
                    "household_id": "household_test",
                    "as_of_date": "2026-10-11",
                    "status": "ready",
                    "optimization_allowed": True,
                    "policy": {},
                    "household_members": ["primary", "spouse"],
                    "input_selections": [],
                    "sources": [],
                    "data_gaps": [],
                    "summary": {"required_input_count": 0, "selected_input_count": 0, "source_count": 0,
                                "blocking_gap_count": 0, "warning_count": 0},
                }
                encoded = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
                readiness = {
                    "schema_version": "work-transition-readiness/v1",
                    "record_type": "WorkTransitionReadinessSnapshot",
                    **core,
                    "reproducibility": {"hash_algorithm": "sha256", "content_hash": hashlib.sha256(encoded).hexdigest()},
                }
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(readiness), encoding="utf-8")
                return {"readiness": readiness, "bound_count": 0}

            answers = [
                "household_test", "2026-10-11",
                "1", "full_time", "2026-10-01", "2026-10-01",
                "1", "not_working", "2026-10-01", "2026-10-01",
                "1000.00", "declared", "",
            ]
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(workspace)}), patch(
                "builtins.input", side_effect=answers
            ), patch("family_office_engine.cli.main.run_work_transition_source_setup", side_effect=ready_setup), patch(
                "family_office_engine.services.work_transition_scenario._workspace_root", return_value=workspace
            ), patch(
                "family_office_engine.services.employment_income_projection._workspace_root", return_value=workspace
            ), redirect_stdout(stdout):
                code = main(["planning", "work-transition", "plan"])

            output = stdout.getvalue()
            self.assertEqual(0, code, output)
            self.assertIn("Scenario FTE: ready", output)
            self.assertIn("Proiezione lavoro: blocked", output)
            self.assertIn("Data gaps proiezione:", output)
            self.assertNotIn("data pensionistica obiettivo", output.lower())
            scenario = json.loads((workspace / "snapshots" / "work-transition-scenario.snapshot.json").read_text(encoding="utf-8"))
            projection = json.loads((workspace / "snapshots" / "employment-income-projection.snapshot.json").read_text(encoding="utf-8"))
            self.assertEqual("work-transition-scenario/v1", scenario["schema_version"])
            self.assertEqual("employment-income-projection/v1", projection["schema_version"])
            self.assertEqual("1000.00", projection["periods"][0]["taxable_income"])
            self.assertIsNone(projection["periods"][0]["payroll_net"])
            self.assertEqual("blocked", projection["status"])


if __name__ == "__main__":
    unittest.main()
