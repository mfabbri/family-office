import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas/pension-entitlement-timeline-v2.schema.json"
EVENT_NAMES = (
    "eligibility_date",
    "requirements_met_date",
    "official_recognition_date",
    "economic_effective_date",
    "first_cash_payment_date",
)


def gap(code="event_evidence_missing"):
    return {"code": code, "message": "Synthetic missing evidence.", "severity": "blocking"}


def source_provenance(authority):
    return {
        "source_ref": "workspace-ref:synthetic-source",
        "digest_sha256": "a" * 64,
        "source_authority": authority,
        "jurisdiction": "IT",
        "act_identifier": "synthetic-act",
        "article_identifier": "synthetic-article",
        "source_version": "synthetic-version",
        "legal_applicability": {"valid_from": "2026-01-01", "valid_to": None, "validity_status": "bounded"},
        "coverage_assessment": {
            "coverage_status": "covered",
            "event_date": "2026-01-01",
            "event_date_coverage_status": "covered",
            "as_of_date": "2026-11-08",
            "as_of_date_coverage_status": "covered",
            "assessed_on": "2026-11-08",
            "data_gaps": [],
        },
        "retrieved_on": "2026-11-08",
        "reviewed_on": "2026-11-08",
    }


def evidence(event_name, role, authority, transition_status="applicable"):
    return {
        "evidence_ref": f"{event_name}:synthetic-001",
        "evidence_role": role,
        "source_provenance": source_provenance(authority),
        "transition_scope": {
            "status": transition_status,
            "scope_evidence": [{
                "source_provenance": source_provenance("primary_legislation"),
                "scope": {
                    "scope_status": "resolved",
                    "applies_to_event": event_name,
                    "transition_status": "not_applicable" if transition_status == "not_applicable" else "applicable",
                },
            }],
        },
    }


def assert_coverage_date_within_half_open_applicability(source_provenance, label):
    """Require coverage date in [valid_from, valid_to); null valid_to is open ended."""
    applicability = source_provenance["legal_applicability"]
    coverage_date = source_provenance["coverage_assessment"]["event_date"]
    valid_from = applicability["valid_from"]
    valid_to = applicability["valid_to"]
    if coverage_date < valid_from or (valid_to is not None and coverage_date >= valid_to):
        raise ValueError(f"{label} coverage date is outside legal applicability [valid_from, valid_to)")


def unknown_event(event_name):
    value = {
        "event_kind": event_name,
        "status": "not_assessed",
        "date": None,
        "evidence": [],
        "data_gaps": [gap()],
    }
    if event_name == "economic_effective_date":
        value["retroactivity_status"] = "not_assessed"
    return value


def snapshot():
    return {
        "schema_version": "pension-entitlement-timeline/v2",
        "record_type": "PensionEntitlementTimeline",
        "status": "not_assessed",
        "member_id": "synthetic-member",
        "as_of_date": "2026-11-08",
        "human_review_required": True,
        "events": {name: unknown_event(name) for name in EVENT_NAMES},
        "pension_amount_basis": {
            "basis_state": "unknown",
            "tax_jurisdiction": None,
            "tax_period": None,
            "source_evidence": [],
            "data_gaps": [gap("amount_basis_unknown")],
        },
        "data_gaps": [gap()],
        "limitations": ["Synthetic candidate contract; no individual conclusion."],
    }


class PensionEntitlementTimelineV2ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema, format_checker=FormatChecker())

    def assert_invalid(self, value):
        with self.assertRaises((ValidationError, ValueError)):
            self.validate_candidate(value)

    def validate_candidate(self, value):
        self.validator.validate(value)
        for event_name, event in value["events"].items():
            if event["status"] == "supported":
                for proof in event["evidence"]:
                    coverage = proof["source_provenance"]["coverage_assessment"]
                    if coverage["event_date"] != event["date"]:
                        raise ValueError(f"{event_name} evidence coverage date must equal the supported event date")
                    if coverage["as_of_date"] != value["as_of_date"]:
                        raise ValueError(f"{event_name} evidence coverage as_of_date must equal the record as_of_date")
                    assert_coverage_date_within_half_open_applicability(
                        proof["source_provenance"], f"{event_name} evidence"
                    )
            for proof in event["evidence"]:
                transition_scope = proof["transition_scope"]
                inner_statuses = [
                    scope_proof["scope"]["transition_status"]
                    for scope_proof in transition_scope["scope_evidence"]
                ]
                transition_gap_codes = {
                    item["code"] for item in transition_scope.get("data_gaps", [])
                }
                if transition_scope["status"] == "unknown":
                    if inner_statuses:
                        raise ValueError(f"{event_name} unknown transition scope cannot carry resolved evidence")
                    if not any(
                        item["code"] == "transitional_branch_unknown" and item["severity"] == "blocking"
                        for item in transition_scope["data_gaps"]
                    ):
                        raise ValueError(f"{event_name} unknown transition scope requires a blocking gap")
                else:
                    if not inner_statuses or any(status != transition_scope["status"] for status in inner_statuses):
                        raise ValueError(f"{event_name} resolved transition scope must match all inner evidence")
                    if "transitional_branch_unknown" in transition_gap_codes:
                        raise ValueError(f"{event_name} resolved transition scope cannot retain an unknown gap")
                if proof["evidence_role"] == "retroactive_from_basis":
                    assert_coverage_date_within_half_open_applicability(
                        proof["source_provenance"], f"{event_name} retroactive evidence"
                    )
                for scope_proof in proof["transition_scope"]["scope_evidence"]:
                    if scope_proof["scope"]["applies_to_event"] != event_name:
                        raise ValueError(f"{event_name} transition-scope evidence is bound to another event")
                    scope_coverage = scope_proof["source_provenance"]["coverage_assessment"]
                    if scope_coverage["as_of_date"] != value["as_of_date"]:
                        raise ValueError(f"{event_name} transition-scope evidence is bound to another as_of_date")
                    if event["status"] == "supported" and scope_coverage["event_date"] != event["date"]:
                        raise ValueError(f"{event_name} transition-scope evidence is bound to another event date")
                    if event["status"] == "supported":
                        assert_coverage_date_within_half_open_applicability(
                            scope_proof["source_provenance"], f"{event_name} transition-scope evidence"
                        )

    def test_all_five_events_fail_closed_with_null_dates_and_stable_gaps(self):
        self.validator.validate(snapshot())

    def test_supported_event_requires_its_role_authority_and_no_blocking_gap(self):
        value = snapshot()
        event = value["events"]["eligibility_date"]
        event.update({"status": "supported", "date": "2026-01-01", "data_gaps": []})
        event["evidence"] = [evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")]
        self.validator.validate(value)
        event["data_gaps"] = [gap()]
        self.assert_invalid(value)

    def test_unknown_event_cannot_emit_date_or_omit_gap(self):
        value = snapshot()
        value["events"]["first_cash_payment_date"]["date"] = "2026-01-01"
        self.assert_invalid(value)
        value = snapshot()
        value["events"]["first_cash_payment_date"]["data_gaps"] = []
        self.assert_invalid(value)

    def test_not_applicable_requires_scoped_evidence(self):
        value = snapshot()
        event = value["events"]["requirements_met_date"]
        event.update({"status": "not_applicable", "data_gaps": [], "evidence": []})
        self.assert_invalid(value)
        event["evidence"] = [evidence("requirements_met_date", "non_applicability_scope", "primary_legislation", "not_applicable")]
        self.validator.validate(value)

    def test_cross_event_evidence_reuse_is_rejected_by_event_scoped_reference(self):
        value = snapshot()
        event = value["events"]["requirements_met_date"]
        event.update({"status": "supported", "date": "2026-01-01", "data_gaps": []})
        event["evidence"] = [evidence("eligibility_date", "requirements_evidence", "primary_legislation")]
        self.assert_invalid(value)

    def test_wrong_source_authority_or_validity_is_rejected(self):
        value = snapshot()
        event = value["events"]["official_recognition_date"]
        event.update({"status": "supported", "date": "2026-01-01", "data_gaps": []})
        event["evidence"] = [evidence("official_recognition_date", "individual_decision", "official_administrative_guidance")]
        self.assert_invalid(value)
        event["evidence"][0]["source_provenance"]["source_authority"] = "individual_institutional_decision"
        event["evidence"][0]["source_provenance"]["legal_applicability"]["validity_status"] = "unverified"
        self.assert_invalid(value)

    def test_decision_notification_does_not_substitute_for_the_decision(self):
        value = snapshot()
        event = value["events"]["official_recognition_date"]
        event.update({"status": "supported", "date": "2026-01-01", "data_gaps": []})
        event["evidence"] = [evidence("official_recognition_date", "decision_notification", "individual_institutional_decision")]
        self.assert_invalid(value)

    def test_retroactivity_is_explicit_and_requires_its_own_evidence(self):
        value = snapshot()
        event = value["events"]["economic_effective_date"]
        event.update({"status": "supported", "date": "2026-01-01", "data_gaps": [], "retroactivity_status": "retroactive"})
        event["evidence"] = [evidence("economic_effective_date", "economic_effective_basis", "binding_implementing_act")]
        self.assert_invalid(value)
        event["evidence"].append(evidence("economic_effective_date", "retroactive_from_basis", "binding_implementing_act"))
        self.validator.validate(value)

    def test_administrative_schedule_or_payment_order_cannot_assert_cash_availability(self):
        value = snapshot()
        event = value["events"]["first_cash_payment_date"]
        event.update({"status": "supported", "date": "2026-01-01", "data_gaps": []})
        event["evidence"] = [evidence("first_cash_payment_date", "payment_order", "official_administrative_guidance")]
        self.assert_invalid(value)

    def test_amount_basis_keeps_unknown_or_mixed_gap_bearing_and_net_tax_contextualized(self):
        value = snapshot()
        value["pension_amount_basis"]["basis_state"] = "mixed"
        value["pension_amount_basis"]["data_gaps"] = [gap("amount_basis_mixed")]
        self.validator.validate(value)
        value["pension_amount_basis"]["data_gaps"] = []
        self.assert_invalid(value)
        value = snapshot()
        value["pension_amount_basis"] = {
            "basis_state": "net_calculated",
            "tax_jurisdiction": "IT",
            "tax_period": "2026",
            "source_evidence": [source_provenance("official_administrative_guidance")],
            "data_gaps": [],
        }
        self.validator.validate(value)

    def test_source_version_cannot_be_blank(self):
        for source_version, is_valid in (("", False), ("   ", False), ("version-1", True)):
            with self.subTest(source_version=repr(source_version)):
                value = snapshot()
                event = value["events"]["eligibility_date"]
                event.update({"status": "supported", "date": "2026-01-01", "data_gaps": []})
                event["evidence"] = [evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")]
                event["evidence"][0]["source_provenance"]["source_version"] = source_version
                if is_valid:
                    self.validate_candidate(value)
                else:
                    self.assert_invalid(value)

    def test_open_ended_applicability_accepts_supported_and_retroactive_evidence_after_valid_from(self):
        value = snapshot()
        event = value["events"]["eligibility_date"]
        event.update({"status": "supported", "date": "2026-03-01", "data_gaps": []})
        event["evidence"] = [evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")]
        event["evidence"][0]["source_provenance"]["coverage_assessment"]["event_date"] = "2026-03-01"
        event["evidence"][0]["transition_scope"]["scope_evidence"][0]["source_provenance"]["coverage_assessment"]["event_date"] = "2026-03-01"
        self.validate_candidate(value)

        value = snapshot()
        event = value["events"]["economic_effective_date"]
        event.update({"status": "supported", "date": "2026-03-01", "data_gaps": [], "retroactivity_status": "retroactive"})
        event["evidence"] = [
            evidence("economic_effective_date", "economic_effective_basis", "binding_implementing_act"),
            evidence("economic_effective_date", "retroactive_from_basis", "binding_implementing_act"),
        ]
        for proof in event["evidence"]:
            proof["source_provenance"]["coverage_assessment"]["event_date"] = "2026-03-01"
            proof["transition_scope"]["scope_evidence"][0]["source_provenance"]["coverage_assessment"]["event_date"] = "2026-03-01"
        self.validate_candidate(value)

    def test_supported_event_evidence_respects_half_open_applicability_boundaries(self):
        for event_date, is_valid in (
            ("2026-01-01", True),
            ("2026-02-01", False),
            ("2025-12-31", False),
            ("2026-02-02", False),
        ):
            with self.subTest(event_date=event_date):
                value = snapshot()
                event = value["events"]["eligibility_date"]
                event.update({"status": "supported", "date": event_date, "data_gaps": []})
                event["evidence"] = [evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")]
                provenance = event["evidence"][0]["source_provenance"]
                provenance["legal_applicability"].update({"valid_from": "2026-01-01", "valid_to": "2026-02-01"})
                provenance["coverage_assessment"]["event_date"] = event_date
                event["evidence"][0]["transition_scope"]["scope_evidence"][0]["source_provenance"]["coverage_assessment"]["event_date"] = event_date
                if is_valid:
                    self.validate_candidate(value)
                else:
                    self.assert_invalid(value)

    def test_retroactive_evidence_respects_half_open_applicability_boundaries(self):
        for event_date, is_valid in (
            ("2026-01-01", True),
            ("2026-02-01", False),
            ("2025-12-31", False),
            ("2026-02-02", False),
        ):
            with self.subTest(event_date=event_date):
                value = snapshot()
                event = value["events"]["economic_effective_date"]
                event.update({"status": "supported", "date": event_date, "data_gaps": [], "retroactivity_status": "retroactive"})
                event["evidence"] = [
                    evidence("economic_effective_date", "economic_effective_basis", "binding_implementing_act"),
                    evidence("economic_effective_date", "retroactive_from_basis", "binding_implementing_act"),
                ]
                for proof in event["evidence"]:
                    proof["source_provenance"]["coverage_assessment"]["event_date"] = event_date
                    proof["transition_scope"]["scope_evidence"][0]["source_provenance"]["coverage_assessment"]["event_date"] = event_date
                retroactive_provenance = event["evidence"][1]["source_provenance"]
                retroactive_provenance["legal_applicability"].update({"valid_from": "2026-01-01", "valid_to": "2026-02-01"})
                if is_valid:
                    self.validate_candidate(value)
                else:
                    self.assert_invalid(value)

    def test_transition_scope_resolved_status_must_match_each_inner_scope_and_clear_unknown_gap(self):
        value = snapshot()
        event = value["events"]["eligibility_date"]
        event.update({"status": "supported", "date": "2026-01-01", "data_gaps": []})
        event["evidence"] = [evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")]
        event["evidence"][0]["transition_scope"]["scope_evidence"][0]["scope"]["transition_status"] = "not_applicable"
        self.assert_invalid(value)

        value = snapshot()
        event = value["events"]["requirements_met_date"]
        event.update({"status": "not_applicable", "data_gaps": []})
        event["evidence"] = [evidence("requirements_met_date", "non_applicability_scope", "primary_legislation", "not_applicable")]
        event["evidence"][0]["transition_scope"]["scope_evidence"][0]["scope"]["transition_status"] = "applicable"
        self.assert_invalid(value)

        value = snapshot()
        event = value["events"]["eligibility_date"]
        event.update({"status": "supported", "date": "2026-01-01", "data_gaps": []})
        event["evidence"] = [evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")]
        event["evidence"][0]["transition_scope"]["data_gaps"] = [{"code": "transitional_branch_unknown", "message": "Synthetic missing evidence.", "severity": "warning"}]
        self.assert_invalid(value)

    def test_net_amount_basis_requires_non_null_tax_context_for_each_net_state(self):
        for basis_state in ("net_documented", "net_calculated"):
            for context, tax_context in (
                ("null_jurisdiction", {"tax_jurisdiction": None, "tax_period": "2026"}),
                ("null_period", {"tax_jurisdiction": "IT", "tax_period": None}),
                ("missing_jurisdiction", {"tax_period": "2026"}),
                ("missing_period", {"tax_jurisdiction": "IT"}),
            ):
                with self.subTest(basis_state=basis_state, context=context):
                    value = snapshot()
                    value["pension_amount_basis"] = {
                        "basis_state": basis_state,
                        **tax_context,
                        "source_evidence": [source_provenance("official_administrative_guidance")],
                        "data_gaps": [],
                    }
                    self.assert_invalid(value)
            with self.subTest(basis_state=basis_state, context="valid"):
                value = snapshot()
                value["pension_amount_basis"] = {
                    "basis_state": basis_state,
                    "tax_jurisdiction": "IT",
                    "tax_period": "2026",
                    "source_evidence": [source_provenance("official_administrative_guidance")],
                    "data_gaps": [],
                }
                self.validate_candidate(value)

    def test_supported_event_rejects_date_or_as_of_coverage_mismatch(self):
        value = snapshot()
        event = value["events"]["eligibility_date"]
        event.update({"status": "supported", "date": "2026-01-01", "data_gaps": []})
        event["evidence"] = [evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation")]
        event["evidence"][0]["source_provenance"]["coverage_assessment"]["as_of_date_coverage_status"] = "not_covered"
        self.assert_invalid(value)
        event["evidence"][0]["source_provenance"]["coverage_assessment"]["as_of_date_coverage_status"] = "covered"
        event["evidence"][0]["source_provenance"]["coverage_assessment"]["event_date"] = "2026-01-02"
        self.assert_invalid(value)
        event["evidence"][0]["source_provenance"]["coverage_assessment"]["event_date"] = "2026-01-01"
        event["evidence"][0]["source_provenance"]["coverage_assessment"]["as_of_date"] = "2026-11-07"
        self.assert_invalid(value)

    def test_unknown_transition_scope_requires_blocking_gap_and_structured_source_evidence(self):
        value = snapshot()
        event = value["events"]["eligibility_date"]
        event.update({"status": "not_assessed", "date": None, "data_gaps": [gap()]})
        event["evidence"] = [evidence("eligibility_date", "eligibility_legal_basis", "primary_legislation", "unknown")]
        self.assert_invalid(value)
        event["evidence"][0]["transition_scope"]["data_gaps"] = [gap("transitional_branch_unknown")]
        self.assert_invalid(value)
        event["evidence"][0]["transition_scope"]["scope_evidence"] = []
        self.validate_candidate(value)
        event["evidence"][0]["transition_scope"]["scope_evidence"] = ["unbound-ref"]
        self.assert_invalid(value)
        event["evidence"][0]["transition_scope"]["scope_evidence"] = [{"source_provenance": source_provenance("primary_legislation"), "scope": {"scope_status": "resolved", "applies_to_event": "requirements_met_date", "transition_status": "applicable"}}]
        self.assert_invalid(value)
        event["evidence"][0]["transition_scope"]["scope_evidence"] = [{"source_provenance": source_provenance("official_administrative_guidance"), "scope": {"scope_status": "resolved", "applies_to_event": "eligibility_date", "transition_status": "applicable"}}]
        self.assert_invalid(value)
        event["evidence"][0]["transition_scope"]["scope_evidence"] = [{"source_provenance": source_provenance("primary_legislation"), "scope": {"scope_status": "resolved", "applies_to_event": "eligibility_date", "transition_status": "applicable"}}]
        event["evidence"][0]["transition_scope"]["scope_evidence"][0]["source_provenance"]["coverage_assessment"]["as_of_date_coverage_status"] = "not_covered"
        self.assert_invalid(value)

    def test_not_applicable_rejects_wrong_authority_or_unbound_scope(self):
        value = snapshot()
        event = value["events"]["requirements_met_date"]
        event.update({"status": "not_applicable", "data_gaps": []})
        event["evidence"] = [evidence("requirements_met_date", "non_applicability_scope", "primary_legislation", "not_applicable")]
        self.validator.validate(value)
        event["evidence"][0]["source_provenance"]["source_authority"] = "official_administrative_guidance"
        self.assert_invalid(value)
        event["evidence"][0]["source_provenance"]["source_authority"] = "primary_legislation"
        event["evidence"][0]["transition_scope"]["scope_evidence"][0]["source_provenance"]["source_authority"] = "official_administrative_guidance"
        self.assert_invalid(value)

    def test_retroactivity_rejects_wrong_authority_or_unverified_temporal_applicability(self):
        value = snapshot()
        event = value["events"]["economic_effective_date"]
        event.update({"status": "supported", "date": "2026-01-01", "data_gaps": [], "retroactivity_status": "retroactive"})
        event["evidence"] = [
            evidence("economic_effective_date", "economic_effective_basis", "binding_implementing_act"),
            evidence("economic_effective_date", "retroactive_from_basis", "official_administrative_guidance"),
        ]
        self.assert_invalid(value)
        event["evidence"][1]["source_provenance"]["source_authority"] = "binding_implementing_act"
        event["evidence"][1]["source_provenance"]["legal_applicability"]["validity_status"] = "unverified"
        self.assert_invalid(value)

    def test_gross_requires_source_and_amount_gaps_must_match_basis(self):
        value = snapshot()
        value["pension_amount_basis"].update({"basis_state": "gross_documented", "data_gaps": []})
        self.assert_invalid(value)
        value = snapshot()
        value["pension_amount_basis"].update({"basis_state": "unknown", "data_gaps": [gap("event_evidence_missing")]})
        self.assert_invalid(value)
        value["pension_amount_basis"]["basis_state"] = "mixed"
        self.assert_invalid(value)


if __name__ == "__main__":
    unittest.main()
