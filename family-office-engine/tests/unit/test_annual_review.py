import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from family_office_engine.cli.main import main
from family_office_engine.services.annual_review import AnnualReviewError, build_annual_review


class AnnualReviewTest(unittest.TestCase):
    def _workspace(self):
        folder = tempfile.TemporaryDirectory()
        workspace = Path(folder.name)
        (workspace / "snapshots").mkdir()
        return folder, workspace

    def _snapshot(self, workspace, name, schema, as_of="2026-06-30", gaps=None, events=None):
        payload = {"schema_version": schema, "record_type": "Synthetic", "as_of_date": as_of, "data_gaps": gaps or []}
        if events is not None:
            payload["events"] = events
        (workspace / "snapshots" / name).write_text(json.dumps(payload), encoding="utf-8")

    def test_incomplete_year_reports_actionable_gaps(self):
        folder, workspace = self._workspace()
        with folder:
            self._snapshot(workspace, "goals.json", "planning-goals/v1")
            report = build_annual_review(workspace, 2026, "2026-09-03", required_sources=["planning-goals/v1", "net-worth/v1"])
        self.assertEqual("needs_review", report["status"])
        self.assertTrue(any(gap["code"] == "missing_annual_source" for gap in report["data_gaps"]))
        self.assertEqual(2, report["kpis"][0]["target"])

    def test_stale_source_and_source_gaps_are_visible(self):
        folder, workspace = self._workspace()
        with folder:
            self._snapshot(workspace, "expenses.json", "lifecycle-expenses/v1", "2024-01-01", gaps=[{"code": "missing_month"}])
            report = build_annual_review(workspace, 2026, "2026-09-03", required_sources=["lifecycle-expenses/v1"], freshness_days=365)
        codes = {gap["code"] for gap in report["data_gaps"]}
        self.assertEqual({"stale_annual_source", "source_outside_review_year", "source_has_data_gaps"}, codes)
        self.assertEqual("open", report["contingency_actions"][0]["status"])

    def test_residence_and_extraordinary_events_require_review(self):
        folder, workspace = self._workspace()
        with folder:
            self._snapshot(workspace, "events.json", "timeline-events/v1", events=[
                {"event_type": "residence_change", "event_date": "2026-03-01", "note": "private"},
                {"event_type": "extraordinary_event", "event_date": "2026-05-01", "note": "private"},
            ])
            report = build_annual_review(workspace, 2026, "2026-09-03", required_sources=["timeline-events/v1"])
        self.assertEqual({"residence_change", "extraordinary_event"}, {event["kind"] for event in report["events"]})
        self.assertNotIn("private", json.dumps(report))
        self.assertTrue(any(gap["code"] == "events_require_human_review" for gap in report["data_gaps"]))

    def test_cli_writes_workspace_local_contract(self):
        folder, workspace = self._workspace()
        with folder:
            self._snapshot(workspace, "goals.json", "planning-goals/v1")
            output = workspace / "snapshots" / "annual.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = main(["review", "annual", "--workspace", str(workspace), "--year", "2026", "--as-of-date", "2026-09-03", "--required-source", "planning-goals/v1", "--output", str(output)])
            self.assertEqual(0, code)
            self.assertIn("annual review: ready", stdout.getvalue())
            self.assertEqual("annual-review/v1", json.loads(output.read_text(encoding="utf-8"))["schema_version"])

    def test_output_must_remain_inside_workspace(self):
        folder, workspace = self._workspace()
        with folder:
            with self.assertRaisesRegex(AnnualReviewError, "outside workspace"):
                build_annual_review(workspace, 2026, "2026-09-03", output_path=workspace.parent / "outside.json")


if __name__ == "__main__":
    unittest.main()
