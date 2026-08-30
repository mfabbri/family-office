import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.services.document_data_quality import (
    DocumentDataQualityError,
    build_document_data_quality,
    build_workspace_document_data_quality,
    setup_workspace_document_data_quality,
)


class DocumentDataQualityTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name) / "family-office-workspace"
        (self.workspace / "snapshots").mkdir(parents=True)
        self.inventory_path = self.workspace / "snapshots" / "document-inventory.snapshot.json"
        self.input_path = self.workspace / "quality-input.json"
        self.output_path = self.workspace / "snapshots" / "data-quality.report.json"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_inventory(self, documents):
        self.inventory_path.write_text(json.dumps({"schema_version": "document-inventory/v1", "documents": documents}), encoding="utf-8")

    def _write_input(self, **overrides):
        declaration = {
            "schema_version": "data-quality-input/v1",
            "as_of_date": "2026-08-28",
            "inventory_path": "snapshots/document-inventory.snapshot.json",
            "expected_periods": [{"category": "payroll", "start_month": "2026-01", "end_month": "2026-03"}],
            "declared_totals": [{"total_id": "payroll-count", "category": "payroll", "document_count": 3}],
        }
        declaration.update(overrides)
        self.input_path.write_text(json.dumps(declaration), encoding="utf-8")

    @staticmethod
    def _document(relative_path, category, sha256, size_bytes=10):
        return {"relative_path": relative_path, "category": category, "sha256": sha256, "size_bytes": size_bytes}

    def test_reports_duplicates_missing_month_unclassified_and_inconsistent_total(self):
        self._write_inventory([
            self._document("payroll/cedolino_2026-01.pdf", "payroll", "a" * 64),
            self._document("payroll/copy_2026-01.pdf", "payroll", "a" * 64),
            self._document("upload.pdf", "uncategorized", "b" * 64),
        ])
        self._write_input()

        report = build_document_data_quality(self.input_path, self.output_path, self.workspace)

        self.assertEqual("data-quality-report/v1", report["schema_version"])
        self.assertEqual("needs_remediation", report["status"])
        self.assertEqual(
            {"duplicate_document", "missing_month", "unclassified_document", "declared_total_mismatch"},
            {finding["code"] for finding in report["findings"]},
        )
        self.assertEqual(["2026-02", "2026-03"], [finding["month"] for finding in report["findings"] if finding["code"] == "missing_month"])
        self.assertEqual("snapshots/document-inventory.snapshot.json", report["inventory_path"])
        self.assertTrue(self.output_path.is_file())

    def test_default_report_marks_unconfigured_monthly_coverage_as_data_gap(self):
        self._write_inventory([
            self._document("payroll/cedolino_2026-01.pdf", "payroll", "a" * 64),
            self._document("payroll/cedolino_2026-02.pdf", "payroll", "b" * 64),
        ])

        report = build_workspace_document_data_quality(self.workspace, self.output_path, "2026-03-31")

        self.assertEqual("needs_configuration", report["status"])
        self.assertEqual("monthly_expectation_not_configured", report["data_gaps"][0]["code"])
        self.assertEqual("payroll", report["data_gaps"][0]["category"])

    def test_cli_uses_selected_workspace_for_default_report(self):
        self._write_inventory([
            self._document("payroll/cedolino_2026-01.pdf", "payroll", "a" * 64),
        ])
        with redirect_stdout(StringIO()):
            exit_code = main([
                "pipeline", "quality", "--workspace", str(self.workspace),
                "--as-of-date", "2026-01-31",
            ])
        self.assertEqual(2, exit_code)
        self.assertTrue(self.output_path.is_file())

    def test_setup_saves_policy_from_inventory_defaults_and_default_cli_is_readable(self):
        self._write_inventory([
            self._document("payroll/cedolino_2026-01.pdf", "payroll", "a" * 64),
            self._document("payroll/cedolino_2026-02.pdf", "payroll", "b" * 64),
            self._document("payroll/cedolino_2026-03.pdf", "payroll", "c" * 64),
        ])
        answers = iter(["y", "", ""])
        policy = setup_workspace_document_data_quality(self.workspace, "2026-03-31", lambda _prompt: next(answers))
        self.assertEqual([{"category": "payroll", "start_month": "2026-01", "end_month": "2026-03"}], policy["expected_periods"])
        self.assertTrue((self.workspace / "snapshots" / "data-quality.policy.json").is_file())

        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["pipeline", "quality", "--workspace", str(self.workspace), "--output", str(self.output_path), "--as-of-date", "2026-03-31"])

        self.assertEqual(0, exit_code)
        self.assertIn("pipeline quality: ready documents=3 findings=0 data_gaps=0", stdout.getvalue())
        self.assertEqual("ready", json.loads(self.output_path.read_text(encoding="utf-8"))["status"])

    def test_cli_setup_asks_only_for_observed_monthly_categories(self):
        self._write_inventory([
            self._document("payroll/cedolino_2026-01.pdf", "payroll", "a" * 64),
            self._document("banca/saldo.pdf", "banca", "b" * 64),
        ])
        stdout = StringIO()
        with patch("builtins.input", side_effect=["n"]), redirect_stdout(stdout):
            exit_code = main(["pipeline", "quality", "setup", "--workspace", str(self.workspace), "--as-of-date", "2026-01-31"])

        self.assertEqual(0, exit_code)
        self.assertIn("monthly_categories=0", stdout.getvalue())
        policy = json.loads((self.workspace / "snapshots" / "data-quality.policy.json").read_text(encoding="utf-8"))
        self.assertEqual(["payroll"], policy["excluded_categories"])
        resumed = setup_workspace_document_data_quality(self.workspace, "2026-01-31", lambda _prompt: self.fail("already answered"))
        self.assertEqual(["payroll"], resumed["excluded_categories"])

    def test_rejects_windows_absolute_and_outside_workspace_inventory_paths(self):
        self._write_inventory([])
        self._write_input(inventory_path="C:\\private\\inventory.json")
        with self.assertRaisesRegex(DocumentDataQualityError, "relative path"):
            build_document_data_quality(self.input_path, self.output_path, self.workspace)

        self._write_input(inventory_path="../outside.json")
        with self.assertRaisesRegex(DocumentDataQualityError, "outside workspace"):
            build_document_data_quality(self.input_path, self.output_path, self.workspace)


if __name__ == "__main__":
    unittest.main()
