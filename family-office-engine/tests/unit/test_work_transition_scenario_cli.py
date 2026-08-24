import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main


class WorkTransitionScenarioCliTest(unittest.TestCase):
    def test_demo_builds_ready_monthly_scenario(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "scenario.json"
            stdout = io.StringIO()

            with patch(
                "family_office_engine.services.work_transition_readiness._workspace_root",
                return_value=Path(tmp_dir),
            ), patch(
                "family_office_engine.services.work_transition_scenario._workspace_root",
                return_value=Path(tmp_dir),
            ), redirect_stdout(stdout):
                exit_code = main(["planning", "work-transition", "scenario", "--demo", "--output", str(output)])

            self.assertEqual(exit_code, 0)
            self.assertIn("planning work-transition scenario: ready", stdout.getvalue())
            snapshot = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["schema_version"], "work-transition-scenario/v1")
            self.assertEqual(snapshot["summary"]["member_count"], 2)
            self.assertEqual(snapshot["derived_dates"]["full_time_exit_date_by_member"]["primary"], "2030-01-01")
            self.assertEqual(snapshot["derived_dates"]["work_cessation_date_by_member"]["primary"], "2032-01-01")

    def test_demo_without_output_uses_dedicated_synthetic_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "synthetic-scenario.json"

            with patch(
                "family_office_engine.cli.main.default_work_transition_scenario_demo_output",
                return_value=output,
            ), patch(
                "family_office_engine.services.work_transition_readiness._workspace_root",
                return_value=Path(tmp_dir),
            ), patch(
                "family_office_engine.services.work_transition_scenario._workspace_root",
                return_value=Path(tmp_dir),
            ), redirect_stdout(io.StringIO()):
                exit_code = main(["planning", "work-transition", "scenario", "--demo"])

            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
