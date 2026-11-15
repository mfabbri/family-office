import json
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.services.pension_entitlement_timeline import (
    PensionEntitlementTimelineError,
    build_pension_entitlement_timeline,
    validate_pension_entitlement_timeline,
)
import family_office_engine.services.pension_entitlement_timeline as timeline_module
from test_pension_entitlement_timeline_contract import evidence, snapshot


class PensionEntitlementTimelineBuilderTest(unittest.TestCase):
    def test_builds_declared_snapshot_without_inference(self):
        value = snapshot()
        workspace = Path(__file__).resolve().parents[3] / "family-office-workspace"
        input_path = workspace / "synthetic-input.json"
        output_path = workspace / "synthetic-output.json"
        with patch.object(Path, "read_text", return_value=json.dumps(value)), patch.object(Path, "write_text") as write_text, patch.object(Path, "mkdir"), patch.object(timeline_module, "_verify_provenance"), patch.object(timeline_module, "_workspace_root", return_value=workspace):
            result = build_pension_entitlement_timeline(input_path, output_path)
            self.assertEqual(value, result)
            self.assertIn('"pension-entitlement-timeline/v2"', write_text.call_args.args[0])

    def test_supported_event_requires_event_bound_coverage_and_no_blocking_gap(self):
        value = snapshot()
        event = value["events"]["eligibility_date"]
        event.update({"status": "supported", "date": "2026-01-01", "data_gaps": []})
        event["evidence"] = [evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")]
        workspace = Path(__file__).resolve().parents[3] / "family-office-workspace"
        with patch.object(timeline_module, "_verify_provenance"), patch.object(timeline_module, "_workspace_root", return_value=workspace):
            validate_pension_entitlement_timeline(value)
            event["evidence"][0]["source_provenance"]["coverage_assessment"]["event_date"] = "2026-01-02"
            with self.assertRaises(PensionEntitlementTimelineError):
                validate_pension_entitlement_timeline(value)

    def test_half_open_valid_to_is_rejected(self):
        value = snapshot()
        event = value["events"]["eligibility_date"]
        event.update({"status": "supported", "date": "2026-01-01", "data_gaps": []})
        proof = evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")
        proof["source_provenance"]["legal_applicability"]["valid_to"] = "2026-01-01"
        event["evidence"] = [proof]
        with patch.object(timeline_module, "_verify_provenance"), patch.object(timeline_module, "_workspace_root", return_value=Path(__file__).resolve().parents[3] / "family-office-workspace"):
            with self.assertRaises(PensionEntitlementTimelineError):
                validate_pension_entitlement_timeline(value)

    def test_builder_does_not_turn_unknown_into_a_date(self):
        value = snapshot()
        value["events"]["first_cash_payment_date"]["date"] = "2026-01-01"
        workspace = Path(__file__).resolve().parents[3] / "family-office-workspace"
        input_path = workspace / "synthetic-input.json"
        output_path = workspace / "synthetic-output.json"
        with patch.object(Path, "read_text", return_value=json.dumps(value)), patch.object(Path, "write_text"), patch.object(Path, "mkdir"), patch.object(timeline_module, "_workspace_root", return_value=workspace):
            with self.assertRaises(PensionEntitlementTimelineError):
                build_pension_entitlement_timeline(input_path, output_path)

    def test_rejects_future_supported_event_and_future_source_dates(self):
        value = snapshot()
        event = value["events"]["eligibility_date"]
        event.update({"status": "supported", "date": "2027-01-01", "data_gaps": []})
        event["evidence"] = [evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")]
        with patch.object(timeline_module, "_verify_provenance"), patch.object(timeline_module, "_workspace_root", return_value=Path(__file__).resolve().parents[3] / "family-office-workspace"):
            with self.assertRaisesRegex(PensionEntitlementTimelineError, "future date"):
                validate_pension_entitlement_timeline(value)

        event["date"] = "2026-01-01"
        event["evidence"][0]["source_provenance"]["reviewed_on"] = "2026-12-01"
        with self.assertRaisesRegex(PensionEntitlementTimelineError, "reviewed_on"):
            validate_pension_entitlement_timeline(value)

    def test_not_assessed_requires_blocking_gap(self):
        value = snapshot()
        value["events"]["eligibility_date"]["data_gaps"][0]["severity"] = "warning"
        with patch.object(timeline_module, "_workspace_root", return_value=Path(__file__).resolve().parents[3]):
            with self.assertRaisesRegex(PensionEntitlementTimelineError, "blocking data gap"):
                validate_pension_entitlement_timeline(value)

    def test_builder_rejects_output_outside_workspace(self):
        workspace = Path(__file__).resolve().parents[3] / "family-office-workspace"
        with self.assertRaisesRegex(PensionEntitlementTimelineError, "output must stay inside"):
            with patch.object(timeline_module, "_workspace_root", return_value=workspace):
                build_pension_entitlement_timeline(workspace / "input.json", workspace.parent / "outside.json")

    def test_source_reference_must_exist_and_digest_must_match(self):
        import hashlib
        source = Path(__file__).resolve()
        workspace = source.parent
        proof = evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")
        provenance = proof["source_provenance"]
        provenance["source_ref"] = f"workspace-ref:{source.name}"
        provenance["digest_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        with patch.object(timeline_module, "_workspace_path", return_value=source):
            timeline_module._verify_provenance(provenance, workspace.resolve(), __import__("datetime").date(2026, 11, 8))
        provenance["digest_sha256"] = "0" * 64
        with patch.object(timeline_module, "_workspace_path", return_value=source):
            with self.assertRaisesRegex(PensionEntitlementTimelineError, "does not match"):
                timeline_module._verify_provenance(provenance, workspace.resolve(), __import__("datetime").date(2026, 11, 8))

    def test_amount_basis_provenance_is_verified(self):
        value = snapshot()
        value["pension_amount_basis"]["source_evidence"] = [evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")["source_provenance"]]
        workspace = Path(__file__).resolve().parents[3] / "family-office-workspace"
        with patch.object(timeline_module, "_workspace_root", return_value=workspace), patch.object(timeline_module, "_verify_provenance") as verify:
            validate_pension_entitlement_timeline(value)
        self.assertEqual(1, verify.call_count)

    def test_amount_basis_evidence_must_cover_snapshot_as_of_date(self):
        value = snapshot()
        provenance = evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")["source_provenance"]
        value["pension_amount_basis"].update({"basis_state": "gross_documented", "data_gaps": [], "source_evidence": [provenance]})
        workspace = Path(__file__).resolve().parents[3] / "family-office-workspace"
        with patch.object(timeline_module, "_workspace_root", return_value=workspace), patch.object(timeline_module, "_verify_provenance"):
            validate_pension_entitlement_timeline(value)
            provenance["coverage_assessment"]["as_of_date"] = "2026-11-07"
            with self.assertRaisesRegex(PensionEntitlementTimelineError, "not bound to snapshot as_of_date"):
                validate_pension_entitlement_timeline(value)

    def test_amount_basis_evidence_rejects_unknown_coverage_with_gaps(self):
        value = snapshot()
        provenance = evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")["source_provenance"]
        provenance["coverage_assessment"].update({
            "coverage_status": "unknown",
            "event_date_coverage_status": "unknown",
            "as_of_date_coverage_status": "unknown",
            "data_gaps": [{"code": "legal_applicability_unknown", "message": "Synthetic coverage gap.", "severity": "blocking"}],
        })
        value["pension_amount_basis"].update({"basis_state": "gross_documented", "data_gaps": [], "source_evidence": [provenance]})
        workspace = Path(__file__).resolve().parents[3] / "family-office-workspace"
        with patch.object(timeline_module, "_workspace_root", return_value=workspace), patch.object(timeline_module, "_verify_provenance"):
            with self.assertRaisesRegex(PensionEntitlementTimelineError, "fully covered"):
                validate_pension_entitlement_timeline(value)

    def test_not_applicable_source_must_cover_as_of_date(self):
        value = snapshot()
        event = value["events"]["requirements_met_date"]
        event.update({"status": "not_applicable", "date": None, "data_gaps": [], "evidence": [evidence("requirements_met_date", "non_applicability_scope", "primary_legislation", "not_applicable")]})
        event["evidence"][0]["source_provenance"]["legal_applicability"]["valid_from"] = "2026-12-01"
        workspace = Path(__file__).resolve().parents[3] / "family-office-workspace"
        with patch.object(timeline_module, "_workspace_root", return_value=workspace), patch.object(timeline_module, "_verify_provenance"):
            with self.assertRaisesRegex(PensionEntitlementTimelineError, "not valid at as_of_date"):
                validate_pension_entitlement_timeline(value)

    def test_not_applicable_source_must_be_covered_at_snapshot_as_of_date(self):
        value = snapshot()
        event = value["events"]["requirements_met_date"]
        event.update({"status": "not_applicable", "date": None, "data_gaps": [], "evidence": [evidence("requirements_met_date", "non_applicability_scope", "primary_legislation", "not_applicable")]})
        coverage = event["evidence"][0]["source_provenance"]["coverage_assessment"]
        coverage["as_of_date"] = "2026-11-07"
        workspace = Path(__file__).resolve().parents[3] / "family-office-workspace"
        with patch.object(timeline_module, "_workspace_root", return_value=workspace), patch.object(timeline_module, "_verify_provenance"):
            with self.assertRaisesRegex(PensionEntitlementTimelineError, "not bound to snapshot as_of_date"):
                validate_pension_entitlement_timeline(value)

        coverage["as_of_date"] = value["as_of_date"]
        coverage.update({
            "coverage_status": "unknown",
            "event_date_coverage_status": "unknown",
            "as_of_date_coverage_status": "unknown",
            "data_gaps": [{"code": "legal_applicability_unknown", "message": "Synthetic coverage gap.", "severity": "blocking"}],
        })
        with patch.object(timeline_module, "_workspace_root", return_value=workspace), patch.object(timeline_module, "_verify_provenance"):
            with self.assertRaisesRegex(PensionEntitlementTimelineError, "fully covered"):
                validate_pension_entitlement_timeline(value)

    def test_not_applicable_transition_scope_must_be_valid_at_as_of_date(self):
        value = snapshot()
        event = value["events"]["requirements_met_date"]
        event.update({"status": "not_applicable", "date": None, "data_gaps": [], "evidence": [evidence("requirements_met_date", "non_applicability_scope", "primary_legislation", "not_applicable")]})
        scope_provenance = event["evidence"][0]["transition_scope"]["scope_evidence"][0]["source_provenance"]
        scope_provenance["legal_applicability"]["valid_from"] = "2026-12-01"
        workspace = Path(__file__).resolve().parents[3] / "family-office-workspace"
        with patch.object(timeline_module, "_workspace_root", return_value=workspace), patch.object(timeline_module, "_verify_provenance"):
            with self.assertRaisesRegex(PensionEntitlementTimelineError, "at the applicable date"):
                validate_pension_entitlement_timeline(value)

    def test_not_applicable_transition_evidence_must_match_snapshot_as_of_date(self):
        value = snapshot()
        event = value["events"]["requirements_met_date"]
        event.update({"status": "not_applicable", "date": None, "data_gaps": [], "evidence": [evidence("requirements_met_date", "non_applicability_scope", "primary_legislation", "not_applicable")]})
        transition_provenance = event["evidence"][0]["transition_scope"]["scope_evidence"][0]["source_provenance"]
        transition_provenance["coverage_assessment"]["as_of_date"] = "2026-11-07"
        workspace = Path(__file__).resolve().parents[3] / "family-office-workspace"
        with patch.object(timeline_module, "_workspace_root", return_value=workspace), patch.object(timeline_module, "_verify_provenance"):
            with self.assertRaisesRegex(PensionEntitlementTimelineError, "another as_of_date"):
                validate_pension_entitlement_timeline(value)

    def test_not_assessed_record_requires_blocking_gap(self):
        value = snapshot()
        value["data_gaps"] = [{"code": "event_evidence_missing", "message": "synthetic", "severity": "warning"}]
        workspace = Path(__file__).resolve().parents[3] / "family-office-workspace"
        with patch.object(timeline_module, "_workspace_root", return_value=workspace):
            with self.assertRaisesRegex(PensionEntitlementTimelineError, "timeline requires a blocking data gap"):
                validate_pension_entitlement_timeline(value)


if __name__ == "__main__":
    unittest.main()
