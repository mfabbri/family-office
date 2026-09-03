import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.services.release_governance import ReleaseGovernanceError, build_release_gate

ROOT = Path(__file__).resolve().parents[3]
ENGINE = ROOT / "family-office-engine"


class ReleaseGovernanceTest(unittest.TestCase):
    def _completed(self, returncode=0):
        return SimpleNamespace(returncode=returncode, stdout="", stderr="")

    def test_builds_release_gate_with_versions_evaluation_and_rollback(self):
        with tempfile.TemporaryDirectory() as folder, patch("family_office_engine.services.release_governance.subprocess.run", return_value=self._completed()):
            output = Path(folder) / "release.json"
            report = build_release_gate(ENGINE, candidate_id="synthetic-release", output_path=output, run_tests=False)
            self.assertTrue(report["release_gate"]["passed"])
            self.assertEqual("release-gate/v1", report["schema_version"])
            self.assertGreaterEqual(len(report["version_matrix"]), 3)
            self.assertFalse(report["release_gate"]["network_used"])
            self.assertFalse(report["rollback_plan"]["automatic_execution"])
            self.assertTrue(output.exists())

    def test_rejects_schema_change_and_failed_baseline_regression(self):
        with tempfile.TemporaryDirectory() as folder, patch("family_office_engine.services.release_governance.subprocess.run", return_value=self._completed(1)):
            baseline = build_release_gate(ENGINE, candidate_id="previous", run_tests=False)
            baseline["release_gate"]["passed"] = True
            baseline["version_matrix"][1]["schema_version"] = "changed/v2"
            baseline_path = Path(folder) / "baseline.json"
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            report = build_release_gate(ENGINE, candidate_id="candidate", baseline_path=baseline_path, run_tests=False)
            self.assertFalse(report["release_gate"]["passed"])
            self.assertIn("schema_incompatibility", report["release_gate"]["failures"])
            self.assertIn("baseline_regression", report["release_gate"]["failures"])

    def test_rejects_invalid_baseline_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "baseline.json"
            path.write_text(json.dumps({"schema_version": "wrong/v1"}), encoding="utf-8")
            with self.assertRaisesRegex(ReleaseGovernanceError, "unsupported schema"):
                build_release_gate(ENGINE, candidate_id="candidate", baseline_path=path, run_tests=False)

    def test_cli_release_check_is_integrated_with_the_gate(self):
        with tempfile.TemporaryDirectory() as folder, patch("family_office_engine.services.release_governance.subprocess.run", return_value=self._completed()):
            output = Path(folder) / "release.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["release", "check", "--candidate-id", "synthetic-cli", "--output", str(output)])
            self.assertEqual(0, exit_code)
            self.assertIn("release check: passed", stdout.getvalue())
            self.assertEqual("release-gate/v1", json.loads(output.read_text(encoding="utf-8"))["schema_version"])


if __name__ == "__main__":
    unittest.main()
