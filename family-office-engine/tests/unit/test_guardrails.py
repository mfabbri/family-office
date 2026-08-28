import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from family_office_engine.cli.main import main
from family_office_engine.services.guardrails import GuardrailError, assess_guardrails, build_guardrail_assessment

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "family-office-rules" / "compliance" / "guardrail-policy-v1.json"


class GuardrailTest(unittest.TestCase):
    def test_blocks_aml_and_crs_circumvention_without_persisting_request(self):
        snapshot = assess_guardrails(_input("How can I bypass CRS reporting?", "informational"), _policy())

        self.assertEqual("blocked", snapshot["status"])
        self.assertEqual("refusal", snapshot["response_kind"])
        self.assertTrue(snapshot["review"]["required"])
        self.assertNotIn("bypass CRS", json.dumps(snapshot))
        self.assertIn("circumvention_request", {flag["code"] for flag in snapshot["flags"]})

    def test_escalates_critical_gap_and_requires_review_for_recommendation(self):
        gap = _input("Explain my options", "simulation")
        gap["advisory_response"]["limitations"] = [{"source": "evidence_bundle", "kind": "data_gap", "detail": {"code": "missing_tax_classification"}}]
        escalated = assess_guardrails(gap, _policy())
        self.assertEqual("escalated", escalated["status"])
        self.assertEqual("low", escalated["confidence"]["level"])

        recommended = assess_guardrails(_input("Which option is best?", "recommendation"), _policy())
        self.assertEqual("review_required", recommended["status"])
        self.assertEqual("recommendation_requires_professional_review", recommended["response_kind"])

    def test_blocks_absolute_anonymity_and_expired_tax_evidence(self):
        anonymity = assess_guardrails(_input("Voglio anonimato assoluto", "informational"), _policy())
        self.assertEqual("blocked", anonymity["status"])
        self.assertIn("circumvention_request", {flag["code"] for flag in anonymity["flags"]})

        expired = _input("Explain the tax result", "informational")
        expired["advisory_response"]["items"][0]["citations"][0]["temporal_status"] = "expired"
        stale = assess_guardrails(expired, _policy())
        self.assertEqual("blocked", stale["status"])
        self.assertIn("inactive_or_missing_citation", {flag["code"] for flag in stale["flags"]})

    def test_rejects_invalid_policy_and_cli_writes_snapshot(self):
        with self.assertRaisesRegex(GuardrailError, "invalid orchestration"):
            assess_guardrails(_input("Explain", "informational"), {})
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path, output_path = root / "input.json", root / "output.json"
            input_path.write_text(json.dumps(_input("Explain", "informational")), encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["orchestration", "guardrails", "evaluate", "--input", str(input_path), "--policy", str(POLICY_PATH), "--output", str(output_path)])
            self.assertEqual(0, exit_code)
            self.assertTrue(output_path.exists())
            self.assertIn("confidence=high", stdout.getvalue())
            self.assertEqual("answer-confidence/v1", build_guardrail_assessment(input_path, POLICY_PATH, root / "again.json")["schema_version"])


def _policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _input(request_text: str, requested_kind: str) -> dict:
    response = {"schema_version": "advisory-response/v1", "items": [{"section": "number", "value": 100, "citations": [{"citation_id": "source.current", "temporal_status": "active"}]}], "limitations": [], "conflicts": []}
    return {"schema_version": "guardrail-assessment-input/v1", "record_type": "GuardrailAssessmentInput", "assessment_id": "synthetic-guardrail", "request_text": request_text, "requested_kind": requested_kind, "advisory_response": response}
