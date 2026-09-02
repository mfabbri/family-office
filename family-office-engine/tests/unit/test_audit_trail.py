import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.services.audit_trail import (
    AuditTrailError,
    append_audit_event,
    replay_audit,
    verify_audit_log,
)


class AuditTrailTest(unittest.TestCase):
    def test_append_verify_and_replay_approval_chain(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace, log = Path(folder), Path(folder) / "snapshots" / "audit.jsonl"
            append_audit_event(log, workspace, event_type="recommendation", actor="engine", subject_id="scenario-1", action="generated", reference="evidence:abc")
            append_audit_event(log, workspace, event_type="approval", actor="reviewer", subject_id="scenario-1", action="approve", reference="test:golden")
            result = replay_audit(log, workspace)
            self.assertEqual(result["approvals"]["scenario-1"]["status"], "approved")
            self.assertEqual(verify_audit_log(log, workspace)["event_count"], 2)

    def test_revocation_is_append_only_and_replayable(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace, log = Path(folder), Path(folder) / "audit.jsonl"
            append_audit_event(log, workspace, event_type="approval", actor="reviewer", subject_id="scenario-1", action="approve", reference="test:1")
            before = log.read_text(encoding="utf-8")
            append_audit_event(log, workspace, event_type="revocation", actor="reviewer", subject_id="scenario-1", action="revoke", reference="reason:changed")
            self.assertTrue(log.read_text(encoding="utf-8").startswith(before))
            self.assertEqual(replay_audit(log, workspace)["approvals"]["scenario-1"]["status"], "revoked")

    def test_tamper_and_clock_skew_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace, log = Path(folder), Path(folder) / "audit.jsonl"
            append_audit_event(log, workspace, event_type="import", actor="operator", subject_id="documents", action="completed", reference="sha256:abc")
            event = json.loads(log.read_text(encoding="utf-8"))
            event["action"] = "tampered"
            log.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(AuditTrailError, "tampered|hash"):
                verify_audit_log(log, workspace)
            with self.assertRaisesRegex(AuditTrailError, "clock skew"):
                append_audit_event(workspace / "clock.jsonl", workspace, event_type="import", actor="operator", subject_id="documents", action="completed", reference="sha256:def", occurred_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())

    def test_path_confinement_and_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder) / "workspace"
            workspace.mkdir()
            self.assertEqual(main(["audit", "append", "--workspace", str(workspace), "--event-type", "approval", "--actor", "reviewer", "--subject-id", "scenario-1", "--action", "approve", "--reference", "test:cli"]), 0)
            self.assertEqual(main(["audit", "verify", "--workspace", str(workspace)]), 0)
            self.assertEqual(main(["audit", "replay", "--workspace", str(workspace)]), 0)
            with self.assertRaises(AuditTrailError):
                append_audit_event(workspace.parent / "escape.jsonl", workspace, event_type="import", actor="x", subject_id="y", action="z", reference="r")


if __name__ == "__main__":
    unittest.main()
