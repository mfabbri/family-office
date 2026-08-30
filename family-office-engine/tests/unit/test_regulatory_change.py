import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from io import StringIO

from family_office_engine.cli.main import main
from family_office_engine.services.regulatory_change import (
    RegulatoryChangeError,
    approve_regulatory_change,
    build_regulatory_change,
    rollback_regulatory_change,
    write_regulatory_change,
)


def proposal(**overrides):
    value = {
        "change_id": "it.demo.2026.v2",
        "summary": "Synthetic versioned change",
        "source": {"url": "https://example.gov/change", "authority": "official"},
        "jurisdiction": "IT",
        "valid_from": "2026-09-01",
        "affected_rule_packs": ["it.demo.2026.v1"],
        "required_tests": ["test_demo_regression"],
        "rollback_strategy": "restore previous versioned rule pack",
    }
    value.update(overrides)
    return value


class RegulatoryChangeTest(unittest.TestCase):
    def test_authoritative_proposal_is_releasable(self):
        result = build_regulatory_change(proposal(), as_of_date="2026-08-30")
        self.assertEqual(result["schema_version"], "regulatory-change/v1")
        self.assertEqual(result["source"]["verification_status"], "verified")
        self.assertEqual(result["impact_assessment"]["findings"], [])

    def test_non_authoritative_source_is_explicit_gap(self):
        result = build_regulatory_change(proposal(source={"url": "https://professional.example/change", "authority": "professional"}), as_of_date="2026-08-30")
        self.assertEqual(result["source"]["verification_status"], "needs_review")
        self.assertEqual(result["data_gaps"][0]["code"], "source_not_authoritative")
        with self.assertRaisesRegex(RegulatoryChangeError, "unresolved"):
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "proposal.json"
                write_regulatory_change(result, path, Path(folder))
                approve_regulatory_change(path, Path(folder), "reviewer", tests_passed=True)

    def test_retroactive_change_requires_review(self):
        result = build_regulatory_change(proposal(valid_from="2026-01-01"), as_of_date="2026-08-30")
        self.assertTrue(result["validity"]["retroactive"])
        self.assertEqual(result["impact_assessment"]["findings"][0]["code"], "retroactive_validity")

    def test_approval_and_rollback_are_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            path = workspace / "snapshots" / "change.json"
            write_regulatory_change(build_regulatory_change(proposal(), as_of_date="2026-08-30"), path, workspace)
            with self.assertRaisesRegex(RegulatoryChangeError, "knowledge and rule-pack"):
                approve_regulatory_change(path, workspace, "human-reviewer", tests_passed=True, knowledge_updated=False, rule_pack_versioned=False, test_evidence="test_demo")
            proposal_data = json.loads(path.read_text())
            proposal_data["release_checklist"].update({"knowledge_updated": True, "rule_pack_versioned": True})
            path.write_text(json.dumps(proposal_data), encoding="utf-8")
            approved = approve_regulatory_change(path, workspace, "human-reviewer", tests_passed=True, knowledge_updated=True, rule_pack_versioned=True, test_evidence="test_demo")
            self.assertEqual(approved["status"], "approved")
            self.assertEqual(approved["approval"]["test_evidence"], "test_demo")
            rolled_back = rollback_regulatory_change(path, workspace, "synthetic regression failed")
            self.assertEqual(rolled_back["status"], "rolled_back")
            self.assertEqual(json.loads(path.read_text())["rollback"]["status"], "executed")

    def test_output_cannot_escape_workspace(self):
        with self.assertRaisesRegex(RegulatoryChangeError, "inside the workspace"):
            write_regulatory_change(build_regulatory_change(proposal(), as_of_date="2026-08-30"), Path(tempfile.gettempdir()) / "escape.json", Path("."))

    def test_cli_prepare_and_approve(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            output = workspace / "snapshots" / "cli-change.json"
            args = ["compliance", "regulatory", "prepare", "--workspace", str(workspace), "--output", str(output), "--change-id", "cli.demo", "--summary", "Synthetic CLI change", "--source-url", "https://example.gov/change", "--authority", "official", "--jurisdiction", "IT", "--valid-from", "2026-09-01", "--affected-rule-pack", "it.demo.v1", "--required-test", "test_demo", "--rollback-strategy", "restore previous", "--as-of-date", "2026-08-30"]
            with patch("sys.stdout", new_callable=StringIO):
                self.assertEqual(main(args), 0)
                self.assertEqual(main(["compliance", "regulatory", "approve", "--workspace", str(workspace), "--input", str(output), "--approver", "reviewer", "--tests-passed", "--knowledge-updated", "--rule-pack-versioned", "--test-evidence", "test_demo"]), 0)
            self.assertEqual(json.loads(output.read_text())["status"], "approved")


if __name__ == "__main__":
    unittest.main()
