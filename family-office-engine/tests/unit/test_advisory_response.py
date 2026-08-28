import copy
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from family_office_engine.cli.main import main
from family_office_engine.services.advisory_response import AdvisoryResponseError, build_advisory_response, compose_advisory_response


class AdvisoryResponseTest(unittest.TestCase):
    def test_composes_only_resolved_evidence_with_active_citations(self):
        snapshot = compose_advisory_response(_input())

        self.assertEqual("advisory-response/v1", snapshot["schema_version"])
        self.assertEqual("complete_with_limitations", snapshot["status"])
        self.assertEqual(1200, snapshot["items"][0]["value"])
        self.assertEqual("unverified_descriptor", snapshot["items"][0]["descriptor"]["status"])
        self.assertEqual("source.current", snapshot["items"][0]["citations"][0]["citation_id"])
        self.assertEqual("missing_input", snapshot["limitations"][0]["detail"]["code"])
        self.assertFalse(snapshot["policy"]["composer_calculates_tax_pension_financial_values"])

    def test_rejects_uncited_or_unresolved_numbers(self):
        uncited = _input()
        uncited["items"][0]["citation_ids"] = []
        with self.assertRaisesRegex(AdvisoryResponseError, "requires a specific active citation"):
            compose_advisory_response(uncited)

        unresolved = _input()
        unresolved["items"][0]["evidence"]["pointer"] = "/summary/not-a-value"
        with self.assertRaisesRegex(AdvisoryResponseError, "does not resolve"):
            compose_advisory_response(unresolved)

    def test_exposes_conflicting_evidence_and_rejects_inactive_citation(self):
        conflicting = _input()
        second = copy.deepcopy(conflicting["items"][0])
        second["item_id"] = "monthly-income-conflict"
        second["evidence"]["pointer"] = "/summary/alternative_monthly_income"
        conflicting["items"].append(second)
        snapshot = compose_advisory_response(conflicting)
        self.assertEqual("complete_with_limitations", snapshot["status"])
        self.assertEqual("conflicting_evidence_values", snapshot["conflicts"][0]["reason"])

        inactive = _input()
        inactive["citation_search"]["citations"][0]["temporal_status"] = "expired"
        with self.assertRaisesRegex(AdvisoryResponseError, "not active"):
            compose_advisory_response(inactive)

    def test_writes_response_and_cli_smoke(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path, output_path = root / "input.json", root / "output.json"
            input_path.write_text(json.dumps(_input()), encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["orchestration", "response", "build", "--input", str(input_path), "--output", str(output_path)])

            self.assertEqual(0, exit_code)
            self.assertTrue(output_path.exists())
            self.assertIn("evidence-backed items", stdout.getvalue())
            self.assertEqual("advisory-response/v1", build_advisory_response(input_path, root / "second.json")["schema_version"])


def _input() -> dict:
    output = {"schema_version": "synthetic-income/v1", "summary": {"monthly_income": 1200, "alternative_monthly_income": 900}}
    evidence = {
        "schema_version": "evidence-bundle/v1",
        "record_type": "EvidenceBundle",
        "execution_id": "synthetic-execution",
        "nodes": [{"node_id": "income", "execution_state": "succeeded", "output": output, "output_hash": "b" * 64}],
        "errors": [],
        "data_gaps": [{"code": "missing_input", "message": "Synthetic documented gap"}],
        "reproducibility": {"content_hash": "a" * 64},
    }
    citation = {"citation_id": "source.current", "title": "Synthetic official source", "official_reference": "SYN-1", "authority_level": "official", "temporal_status": "active"}
    search = {"schema_version": "citation-search/v1", "citations": [citation], "data_gaps": [], "source_index": {"content_hash": "c" * 64}, "reproducibility": {"content_hash": "d" * 64}}
    item = {"item_id": "monthly-income", "section": "number", "label": "Monthly documented income", "evidence": {"node_id": "income", "pointer": "/summary/monthly_income"}, "citation_ids": ["source.current"]}
    return {"schema_version": "response-composition-input/v1", "record_type": "ResponseCompositionInput", "response_id": "synthetic-response", "evidence_bundle": evidence, "citation_search": search, "items": [item]}
