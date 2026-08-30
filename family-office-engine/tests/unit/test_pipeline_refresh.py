import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.services.pipeline_refresh import PipelineRefreshError, refresh_pipeline


class PipelineRefreshTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp_dir.name) / "family-office-workspace"
        (self.workspace / "inbox").mkdir(parents=True)
        (self.workspace / "inbox" / "synthetic-statement.pdf").write_bytes(b"version one")
        self.manifest = self.workspace / "snapshots" / "pipeline-run.manifest.json"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_complete_incremental_and_changed_input_runs_are_deterministic(self):
        first = refresh_pipeline(self.workspace)
        self.assertEqual("pipeline-run/v1", first["schema_version"])
        self.assertEqual(["executed", "executed"], [step["status"] for step in first["steps"]])
        second = refresh_pipeline(self.workspace)
        self.assertEqual(["skipped", "skipped"], [step["status"] for step in second["steps"]])
        second_manifest = self.manifest.read_text(encoding="utf-8")
        refresh_pipeline(self.workspace)
        self.assertEqual(second_manifest, self.manifest.read_text(encoding="utf-8"))

        (self.workspace / "inbox" / "synthetic-statement.pdf").write_bytes(b"version two")
        changed = refresh_pipeline(self.workspace)
        self.assertEqual(["executed", "executed"], [step["status"] for step in changed["steps"]])
        self.assertEqual(1, json.loads((self.workspace / "snapshots" / "document-inventory.snapshot.json").read_text(encoding="utf-8"))["summary"]["document_count"])

    def test_failed_step_preserves_prior_baseline_and_exposes_failure_state(self):
        refresh_pipeline(self.workspace)
        baseline = self.manifest.read_text(encoding="utf-8")
        (self.workspace / "inbox" / "later.pdf").write_bytes(b"changed")
        with patch("family_office_engine.services.pipeline_refresh.build_document_inventory", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaisesRegex(PipelineRefreshError, "document_inventory") as context:
                refresh_pipeline(self.workspace)
        self.assertEqual("failed", context.exception.run["steps"][0]["status"])
        self.assertEqual(baseline, self.manifest.read_text(encoding="utf-8"))

    def test_cli_and_dry_run_keep_outputs_inside_selected_workspace(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["pipeline", "refresh", "--workspace", str(self.workspace), "--manifest", str(self.manifest), "--dry-run"])
        self.assertEqual(0, exit_code)
        self.assertIn("dry_run executed=0", stdout.getvalue())
        self.assertFalse(self.manifest.exists())

        with redirect_stdout(stdout):
            exit_code = main(["pipeline", "refresh", "--workspace", str(self.workspace), "--manifest", str(self.manifest)])
        self.assertEqual(0, exit_code)
        self.assertTrue(self.manifest.is_file())

    def test_rejects_manifest_outside_workspace(self):
        with self.assertRaisesRegex(ValueError, "outside workspace"):
            refresh_pipeline(self.workspace, self.workspace.parent / "outside.json")

    def test_cli_uses_selected_workspace_for_default_manifest(self):
        with redirect_stdout(StringIO()):
            exit_code = main(["pipeline", "refresh", "--workspace", str(self.workspace)])
        self.assertEqual(0, exit_code)
        self.assertTrue(self.manifest.is_file())


if __name__ == "__main__":
    unittest.main()
