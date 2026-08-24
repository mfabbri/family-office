import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main


class WorkTransitionReadinessCliTest(unittest.TestCase):
    def test_demo_builds_ready_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "readiness.json"
            stdout = io.StringIO()

            with patch(
                "family_office_engine.services.work_transition_readiness._workspace_root",
                return_value=Path(tmp_dir),
            ), redirect_stdout(stdout):
                exit_code = main(["planning", "work-transition", "readiness", "--demo", "--output", str(output)])

            self.assertEqual(exit_code, 0)
            self.assertIn("planning work-transition readiness: ready", stdout.getvalue())
            snapshot = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["schema_version"], "work-transition-readiness/v1")
            self.assertTrue(snapshot["optimization_allowed"])
            self.assertEqual(snapshot["summary"]["selected_input_count"], 9)

    def test_demo_without_output_uses_dedicated_synthetic_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "synthetic-readiness.json"
            with patch(
                "family_office_engine.cli.main.default_work_transition_readiness_demo_output",
                return_value=output,
            ), patch(
                "family_office_engine.services.work_transition_readiness._workspace_root",
                return_value=Path(tmp_dir),
            ), redirect_stdout(io.StringIO()):
                exit_code = main(["planning", "work-transition", "readiness", "--demo"])

            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
