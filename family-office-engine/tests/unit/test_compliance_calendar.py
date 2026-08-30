import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.services.compliance_calendar import (
    ComplianceCalendarError,
    build_compliance_calendar,
    setup_workspace_compliance_event,
)


def policy(events):
    return {
        "schema_version": "compliance-calendar-policy/v1", "policy_id": "synthetic.calendar.v1",
        "jurisdictions": ["IT"], "valid_from": "2026-01-01", "valid_to": "2026-12-31",
        "verified_at": "2026-01-01", "source_refs": ["synthetic.source"], "events": events,
    }


def event(event_id, schedule, offsets=[30, 7, 0], timezone="Europe/Rome"):
    return {
        "event_id": event_id, "title": "Synthetic review", "category": "review", "schedule": schedule,
        "timezone": timezone, "owner": "reviewer", "required_action": "Review evidence.",
        "source_refs": ["synthetic.source"], "alert_offsets_days": offsets,
    }


class ComplianceCalendarTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name) / "workspace"; self.workspace.mkdir()
        self.policy_path = Path(self.temp.name) / "policy.json"
        self.output = self.workspace / "snapshots" / "calendar.json"

    def tearDown(self):
        self.temp.cleanup()

    def _write_policy(self, events):
        self.policy_path.write_text(json.dumps(policy(events)), encoding="utf-8")

    def test_annual_recurrence_and_timezone_are_deterministic(self):
        self._write_policy([event("annual", {"kind": "annual", "month": 6, "day": 30})])
        result = build_compliance_calendar(self.policy_path, self.workspace, "2026-04-01", self.output)
        self.assertEqual("2026-06-30T09:00:00+02:00", result["entries"][0]["due_at"])
        self.assertEqual(["2026-05-31", "2026-06-23", "2026-06-30"], [item["alert_date"] for item in result["alerts"]])
        self.assertTrue(self.output.is_file())

    def test_movable_last_business_day_and_duplicate_offsets(self):
        self._write_policy([event("mobile", {"kind": "last_business_day", "month": 5}, offsets=[7, 7, 0])])
        result = build_compliance_calendar(self.policy_path, self.workspace, "2026-04-01")
        self.assertEqual("2026-05-29T09:00:00+02:00", result["entries"][0]["due_at"])
        self.assertEqual(2, result["summary"]["alert_count"])

    def test_rejects_duplicate_event_and_unknown_timezone(self):
        duplicate = event("same", {"kind": "once", "date": "2026-06-30"})
        self._write_policy([duplicate, duplicate])
        with self.assertRaisesRegex(ComplianceCalendarError, "duplicate event_id"):
            build_compliance_calendar(self.policy_path, self.workspace, "2026-01-01")
        self._write_policy([event("bad-zone", {"kind": "once", "date": "2026-06-30"}, timezone="Mars/Olympus")])
        with self.assertRaisesRegex(ComplianceCalendarError, "unknown timezone"):
            build_compliance_calendar(self.policy_path, self.workspace, "2026-01-01")

    def test_rejects_event_id_shared_by_policy_and_local_setup(self):
        self._write_policy([event("shared", {"kind": "once", "date": "2026-06-30"})])
        local_path = self.workspace / "snapshots" / "compliance-calendar.local-events.json"
        local_path.parent.mkdir()
        local_path.write_text(json.dumps({
            "schema_version": "compliance-calendar-local-events/v1",
            "record_type": "ComplianceCalendarLocalEvents",
            "events": [event("shared", {"kind": "once", "date": "2026-07-01"})],
        }), encoding="utf-8")

        with self.assertRaisesRegex(ComplianceCalendarError, "duplicate event_id: shared"):
            build_compliance_calendar(self.policy_path, self.workspace, "2026-01-01")

    def test_setup_persists_local_event_and_reports_missing_source_as_gap(self):
        answers = iter(["Insurance renewal", "2026-11-15", "Alex", "Request renewal quote", ""])
        result = setup_workspace_compliance_event(self.workspace, lambda _prompt: next(answers))
        self.assertEqual("saved", result["status"])
        self._write_policy([])
        report = build_compliance_calendar(self.policy_path, self.workspace, "2026-09-01")
        self.assertEqual("needs_review", report["status"])
        self.assertEqual("source_not_verified", report["data_gaps"][0]["code"])

    def test_cli_calendar_is_readable_and_setup_needs_no_json(self):
        self._write_policy([event("cli", {"kind": "once", "date": "2026-06-30"})])
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(["compliance", "calendar", "--workspace", str(self.workspace), "--policy", str(self.policy_path), "--as-of-date", "2026-06-01"])
        self.assertEqual(0, code)
        self.assertIn("compliance calendar: ready events=1 alerts=2 data_gaps=0", stdout.getvalue())
        with patch("builtins.input", side_effect=["Document review", "2026-12-01", "", "Check documents", "family records"]), redirect_stdout(StringIO()):
            code = main(["compliance", "setup", "--workspace", str(self.workspace)])
        self.assertEqual(0, code)


if __name__ == "__main__":
    unittest.main()
