import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main, _work_exit_readiness_requirements
from test_italian_timeline_screening import synthetic_facts


class WorkTransitionPensionScreeningCliTest(unittest.TestCase):
    def run_screening(self, *, wrong_member=False, outside=False, empty=False):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            manifest = workspace / "planning/work-transition-readiness.json"
            manifest.parent.mkdir()
            manifest.write_text(json.dumps({
                "schema_version": "work-transition-readiness-input/v1",
                "record_type": "WorkTransitionReadinessInput", "household_id": "synthetic-household",
                "as_of_date": "2026-11-22", "household_members": ["primary", "spouse"],
                "required_inputs": _work_exit_readiness_requirements(), "sources": [],
            }), encoding="utf-8")
            request_path = workspace / "planning/screening.json"
            request_path.write_text(json.dumps({
                "household_id": "synthetic-household", "member_id": "another-member" if wrong_member else "primary",
                "facts": {} if empty else synthetic_facts(),
            }), encoding="utf-8")
            readiness = {"status": "blocked", "summary": {"selected_input_count": 0, "required_input_count": 0, "blocking_gap_count": 0}, "data_gaps": []}
            stdout = io.StringIO()
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(workspace)}), patch(
                "family_office_engine.cli.main.run_work_transition_source_setup",
                return_value={"readiness": readiness, "bound_count": 0},
            ), patch(
                "family_office_engine.cli.main._run_work_transition_scenario_wizard",
                return_value={"blockers": []},
            ), redirect_stdout(stdout):
                code = main([
                    "planning", "work-transition", "plan", "--input", str(manifest),
                    "--italian-screening-input", str(workspace.parent / "outside.json" if outside else request_path),
                ])
            return code, stdout.getvalue()

    def test_public_plan_invokes_real_screening_and_keeps_parent_blocker(self):
        code, output = self.run_screening()
        self.assertEqual(0, code, output)
        self.assertIn("Screening pensionistico IT (primary): assessed", output)
        self.assertIn("esito=eligible", output)
        self.assertIn("pension_entitlement_timeline_not_implemented", output)
        self.assertIn("nessuna data di diritto", output)

    def test_wrong_member_or_external_input_is_rejected(self):
        for kwargs in ({"wrong_member": True}, {"outside": True}):
            with self.subTest(kwargs=kwargs):
                code, output = self.run_screening(**kwargs)
                self.assertEqual(1, code, output)
                self.assertIn("ERROR", output)
                self.assertIn("must be inside workspace" if kwargs.get("outside") else "match the selected household/member", output)
                self.assertNotIn("esito=eligible", output)

    def test_missing_facts_remain_not_assessed(self):
        code, output = self.run_screening(empty=True)
        self.assertEqual(0, code, output)
        self.assertIn("Screening pensionistico IT (primary): not_assessed", output)

    def test_observed_screening_cannot_be_mixed_with_synthetic_projection(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["planning", "work-transition", "plan", "--demo", "--italian-screening-input", "unread.json"])
        self.assertEqual(2, code)
        self.assertIn("separato dalla proiezione", stdout.getvalue())
