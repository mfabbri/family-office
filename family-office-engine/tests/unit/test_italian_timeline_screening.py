import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from family_office_engine.services import pension_entitlement_timeline_producer as producer


def synthetic_facts():
    return {
        "candidate_date": "2026-10-10", "date_of_birth": "1959-10-10",
        "date_of_birth_verified": True, "date_of_birth_source_refs": ["synthetic-identity"],
        "contribution_cohort": "before_1996", "contribution_cohort_confirmed": True,
        "ordinary_single_management_profile_confirmed": True,
        "scope_evidence": {"verified": True, "as_of_date": "2026-10-10", "coverage_from": "2026-01-01", "coverage_to": "2026-10-10", "source_refs": ["synthetic-scope"]},
        "management": "FPLD", "management_confirmed": True, "employment_category": "employee",
        "multiple_managements": False, "foreign_or_eu_aggregation": False,
        "special_or_excluded_profile": False, "cessation_confirmed": True,
        "cessation_evidence": {"verified": True, "cessation_date": "2026-10-10", "as_of_date": "2026-10-10", "source_refs": ["synthetic-cessation"]},
        "contribution_evidence": {"as_of_date": "2026-10-10", "period_end": "2026-10-10", "verified": True, "source_refs": ["synthetic-contribution"], "first_contribution_date": "1990-01-01", "qualifying_contribution_years": "20", "effective_contribution_years_excluding_figurative": "20"},
    }


class ItalianTimelineScreeningTest(unittest.TestCase):
    def assess(self, facts=None, **kwargs):
        return producer.assess_italian_timeline_screening(
            facts=synthetic_facts() if facts is None else facts,
            as_of_date="2026-11-22", **kwargs,
        )

    def test_real_approved_service_runs_without_promoting_candidate_day(self):
        result = self.assess()
        self.assertEqual("assessed", result["status"])
        self.assertEqual("eligible", result["screening"]["result"])
        self.assertEqual(producer.ITALIAN_SCREENING_PACK["rule_pack_id"], result["screening"]["rule_pack_id"])
        self.assertEqual("2029-01-01", result["rule_pack"]["valid_to_exclusive"])
        self.assertEqual("candidate_day_check", result["precision"])
        self.assertTrue(all(result["pension_entitlement"][name] is None for name in producer.EVENTS))

    def test_candidate_day_is_not_an_earliest_date_and_future_is_rejected(self):
        facts = synthetic_facts()
        facts["candidate_date"] = "2027-10-10"
        result = self.assess(facts)
        self.assertIsNone(result["screening"])
        self.assertEqual("not_assessed", result["status"])
        self.assertEqual("candidate_date_missing_or_invalid", result["data_gaps"][0]["code"])

    def test_unsupported_profile_and_unknown_input_remain_gaps(self):
        for facts in ({}, {**synthetic_facts(), "foreign_or_eu_aggregation": True}):
            with self.subTest(facts=bool(facts)):
                result = self.assess(facts)
                self.assertEqual("not_assessed", result["status"])
                self.assertTrue(result["data_gaps"])
                self.assertIsNone(result["pension_entitlement"]["eligibility_date"])

    def test_pack_drift_blocks_before_service_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / producer.ITALIAN_SCREENING_PACK["path"]
            path.parent.mkdir(parents=True)
            path.write_text('{}', encoding="utf-8")
            with patch.object(producer, "assess_italian_old_age_eligibility") as invoke:
                result = self.assess(rules_root=root)
            invoke.assert_not_called()
            self.assertIsNone(result["screening"])
            self.assertEqual("source_version_missing", result["data_gaps"][0]["code"])

    def test_pack_drift_during_invocation_discards_service_result(self):
        original = producer._read_rule_pack_bytes
        reads = 0
        def drift(path):
            nonlocal reads
            reads += 1
            return original(path) if reads == 1 else b'{}'
        with patch.object(producer, "_read_rule_pack_bytes", side_effect=drift):
            result = self.assess()
        self.assertIsNone(result["screening"])
        self.assertEqual("source_version_missing", result["data_gaps"][0]["code"])

    def test_real_month_search_preserves_month_precision_and_input(self):
        facts = synthetic_facts()
        facts.update(candidate_date=None, date_of_birth="1959-03-10")
        facts["scope_evidence"].update(as_of_date="2026-11-22", coverage_to="2026-10-31")
        facts["cessation_evidence"]["cessation_date"] = "2026-01-01"
        from calendar import monthrange
        history = [{
            "month": f"2026-{month:02d}", "period_start": f"2026-{month:02d}-01",
            "period_end": f"2026-{month:02d}-{monthrange(2026, month)[1]}",
            "as_of_date": "2026-11-22", "verified": True,
            "source_refs": [f"synthetic-month-{month}"],
            "qualifying_contribution_years": "20", "qualifying_contribution_unit": "years",
            "original_contribution_units": ["years"], "original_contribution_types": ["mandatory"],
        } for month in range(1, 11)]
        before = copy.deepcopy((facts, history))
        result = self.assess(facts, search_path="pre_1996_ordinary", monthly_history=history)
        self.assertEqual("assessed", result["status"])
        self.assertEqual("2026-03", result["screening"]["first_observed_eligible_month"])
        self.assertEqual("observed_month", result["precision"])
        self.assertIsNone(result["pension_entitlement"]["eligibility_date"])
        self.assertEqual(before, (facts, history))
        history.pop(0)
        result = self.assess(facts, search_path="pre_1996_ordinary", monthly_history=history)
        self.assertEqual("not_assessed", result["status"])

    def test_stale_pack_and_candidate_versions_are_not_activated(self):
        result = producer.assess_italian_timeline_screening(facts=synthetic_facts(), as_of_date="2027-04-01")
        self.assertEqual("not_assessed", result["status"])
        self.assertEqual("rule_pack_unavailable_or_stale", result["data_gaps"][0]["code"])
        pack_path = producer.FAMILY_RULES_ROOT / producer.ITALIAN_SCREENING_PACK["path"]
        self.assertEqual(producer.ITALIAN_SCREENING_PACK["sha256"], hashlib.sha256(pack_path.read_bytes()).hexdigest())
        self.assertNotIn("v6", json.dumps(result))

    def test_ambiguous_or_unsupported_search_modes_are_rejected(self):
        with self.assertRaises(ValueError): self.assess(search_path="overall_earliest")
        with self.assertRaises(ValueError): self.assess(monthly_history=[])

    def test_candidate_evidence_mutations_require_observed_dated_coverage(self):
        self.assertEqual("eligible", self.assess()["screening"]["result"])
        mutations = [
            ("cessation_evidence", "as_of_date", None),
            ("cessation_evidence", "as_of_date", "2026-12-31"),
            ("cessation_evidence", "as_of_date", "2026-01-01"),
            ("scope_evidence", "coverage_to", "2025-12-31"),
            ("scope_evidence", "coverage_from", "2026-10-11"),
            ("scope_evidence", "as_of_date", "2026-12-31"),
            ("scope_evidence", "as_of_date", None),
        ]
        for key, field, value in mutations:
            with self.subTest(key=key, field=field, value=value):
                facts = synthetic_facts()
                if value is None: facts[key].pop(field)
                else: facts[key][field] = value
                result = self.assess(facts)
                self.assertEqual("not_assessed", result["status"])
                self.assertIsNone(result["screening"])
                self.assertEqual("blocking", result["data_gaps"][0]["severity"])

    def test_consumer_and_freshness_use_exact_verified_payload_without_reopening(self):
        original = Path.read_text
        pack_path = (producer.FAMILY_RULES_ROOT / producer.ITALIAN_SCREENING_PACK["path"]).resolve()
        altered = json.loads(pack_path.read_text(encoding="utf-8"))
        altered["paths"]["pre_1996"]["minimum_qualifying_contribution_years"] = "21"
        # Freshness ignores thresholds: stale provenance detects its own reopen.
        altered["source_refs"][0]["next_review_due"] = "2026-01-01"
        def substituted(path, *args, **kwargs):
            if path.resolve() == pack_path:
                return json.dumps(altered)
            return original(path, *args, **kwargs)
        with patch.object(Path, "read_text", substituted):
            result = self.assess()
        self.assertEqual("eligible", result["screening"]["result"])
        with patch.object(producer, "_read_rule_pack_bytes", return_value=json.dumps(altered).encode()):
            result = self.assess()
        self.assertEqual("not_assessed", result["status"])
        self.assertIsNone(result["screening"])

    def test_rules_escape_is_rejected_before_any_payload_read(self):
        self.assertEqual("eligible", self.assess()["screening"]["result"])
        original_resolve = Path.resolve
        pack_path = producer.FAMILY_RULES_ROOT / producer.ITALIAN_SCREENING_PACK["path"]
        outside = producer.FAMILY_RULES_ROOT.parent / "synthetic-outside-pack.json"
        def escaping_resolve(path, *args, **kwargs):
            if path == pack_path:
                return outside
            return original_resolve(path, *args, **kwargs)
        with patch.object(Path, "resolve", escaping_resolve), patch.object(producer, "_read_rule_pack_bytes") as reader:
            result = self.assess()
        reader.assert_not_called()
        self.assertEqual("not_assessed", result["status"])
        self.assertEqual("source_version_missing", result["data_gaps"][0]["code"])

    def test_output_contract_covers_real_assessment_and_gaps_and_forbids_dates(self):
        schema_path = Path(__file__).resolve().parents[2] / "schemas/italian-timeline-screening.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for result in (self.assess(), self.assess({})):
            validator.validate(result)
        result = self.assess()
        result["pension_entitlement"]["eligibility_date"] = "2026-10-10"
        with self.assertRaises(ValidationError): validator.validate(result)


if __name__ == "__main__":
    unittest.main()
