import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from family_office_engine.cli.main import main
from family_office_engine.services.artifact_lineage import (
    ArtifactLineageError,
    build_artifact_lineage,
    check_artifact_freshness,
)


class ArtifactLineageTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name) / "family-office-workspace"
        (self.workspace / "inputs").mkdir(parents=True)
        (self.workspace / "rules").mkdir()
        (self.workspace / "snapshots").mkdir()
        (self.workspace / "inputs" / "statement.json").write_text('{"synthetic": true}\n', encoding="utf-8")
        (self.workspace / "rules" / "tax-rules.json").write_text('{"version": 1}\n', encoding="utf-8")
        (self.workspace / "snapshots" / "report.json").write_text('{"report": "synthetic"}\n', encoding="utf-8")
        self.declaration = self.workspace / "lineage-input.json"
        self.sidecar = self.workspace / "snapshots" / "report.lineage.json"
        self._write_declaration()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_declaration(self, *, artifact_path="snapshots/report.json"):
        self.declaration.write_text(
            json.dumps(
                {
                    "schema_version": "artifact-lineage-input/v1",
                    "as_of_date": "2026-08-28",
                    "artifact_path": artifact_path,
                    "producer_version": "report-builder/v2",
                    "freshness_policy": {"max_age_days": 7},
                    "sources": [
                        {"source_id": "statement", "kind": "input", "version": "parser/v3", "path": "inputs/statement.json"},
                        {"source_id": "tax", "kind": "rule_pack", "version": "it-tax/2026.1", "path": "rules\\tax-rules.json"},
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_build_records_relative_paths_hashes_and_declared_versions(self):
        lineage = build_artifact_lineage(self.declaration, self.sidecar, self.workspace)

        self.assertEqual("artifact-lineage/v1", lineage["schema_version"])
        self.assertEqual("snapshots/report.json", lineage["artifact"]["path"])
        self.assertEqual("report-builder/v2", lineage["producer_version"])
        self.assertEqual("rules/tax-rules.json", lineage["sources"][1]["path"])
        self.assertTrue(lineage["artifact"]["sha256"])
        self.assertEqual("2026-08-28", lineage["observed_at"])
        self.assertTrue(self.sidecar.is_file())

    def test_checker_reports_changed_input_changed_rule_missing_source_and_staleness(self):
        build_artifact_lineage(self.declaration, self.sidecar, self.workspace)
        (self.workspace / "inputs" / "statement.json").write_text('{"synthetic": false}\n', encoding="utf-8")
        (self.workspace / "rules" / "tax-rules.json").write_text('{"version": 2}\n', encoding="utf-8")
        report = check_artifact_freshness(self.sidecar, self.workspace, "2026-09-06")

        self.assertEqual("stale", report["status"])
        self.assertEqual(
            {"source_changed", "rule_pack_changed", "artifact_stale"},
            {issue["code"] for issue in report["issues"]},
        )

        (self.workspace / "inputs" / "statement.json").unlink()
        report = check_artifact_freshness(self.sidecar, self.workspace, "2026-09-06")
        self.assertIn("source_missing", {issue["code"] for issue in report["issues"]})

    def test_rejects_outside_and_nonportable_paths_without_reading_them(self):
        self._write_declaration(artifact_path="C:\\private\\report.json")
        with self.assertRaisesRegex(ArtifactLineageError, "relative path"):
            build_artifact_lineage(self.declaration, self.sidecar, self.workspace)

        self._write_declaration(artifact_path="../outside.json")
        with self.assertRaisesRegex(ArtifactLineageError, "outside workspace"):
            build_artifact_lineage(self.declaration, self.sidecar, self.workspace)

    def test_cli_build_and_check_have_reproducible_status(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main([
                "pipeline", "lineage", "build", "--workspace", str(self.workspace),
                "--input", str(self.declaration), "--output", str(self.sidecar),
            ])
        self.assertEqual(0, exit_code)
        self.assertIn("pipeline lineage: recorded", stdout.getvalue())

        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main([
                "pipeline", "lineage", "check", "--workspace", str(self.workspace),
                "--lineage", str(self.sidecar), "--as-of-date", "2026-08-30",
            ])
        self.assertEqual(0, exit_code)
        self.assertIn("pipeline lineage: fresh issues=0", stdout.getvalue())

        (self.workspace / "rules" / "tax-rules.json").write_text('{"version": 2}\n', encoding="utf-8")
        with redirect_stdout(StringIO()):
            exit_code = main([
                "pipeline", "lineage", "check", "--workspace", str(self.workspace),
                "--lineage", str(self.sidecar), "--as-of-date", "2026-08-30",
            ])
        self.assertEqual(2, exit_code)

    def test_cli_uses_selected_workspace_for_default_sidecar(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main([
                "pipeline", "lineage", "build", "--workspace", str(self.workspace),
                "--input", str(self.declaration),
            ])
        self.assertEqual(0, exit_code)
        self.assertTrue((self.workspace / "snapshots" / "artifact-lineage.sidecar.json").is_file())

        with redirect_stdout(StringIO()):
            exit_code = main([
                "pipeline", "lineage", "check", "--workspace", str(self.workspace),
                "--as-of-date", "2026-08-30",
            ])
        self.assertEqual(0, exit_code)


if __name__ == "__main__":
    unittest.main()
