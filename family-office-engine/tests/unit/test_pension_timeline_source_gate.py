"""Public synthetic acceptance tests for the non-activating source gate."""

import unittest
from unittest.mock import patch

from family_office_engine.services.pension_timeline_source_gate import (
    EVENTS,
    JURISDICTIONS,
    PACK_REGISTRY,
    evaluate_pension_timeline_source_branch,
    select_eu_pension_rule_pack,
)


def select(**overrides):
    values = {
        "member_state": "IT",
        "applicable_date": "2026-11-01",
        "right_acquisition_date": "2026-11-01",
        "contingency_date": "2026-11-01",
        "transition_classification": "post_application_contingency",
        "pre_application_periods": "none",
    }
    values.update(overrides)
    return select_eu_pension_rule_pack(**values)


class PensionTimelineSourceGateTests(unittest.TestCase):
    def test_selects_exact_packs_at_both_inclusive_boundaries(self):
        before = select(
            right_acquisition_date="2026-10-31",
            contingency_date="2026-10-31",
            transition_classification="acquired_before_application_date",
        )
        on_boundary = select()

        self.assertEqual(before["status"], "candidate_selected")
        self.assertEqual(before["rule_pack_id"], "eu.it-es.pension-coordination.2026.v11.1.1")
        self.assertEqual(before["digest_sha256"], PACK_REGISTRY[before["rule_pack_id"]]["sha256"])
        self.assertEqual(on_boundary["status"], "candidate_selected")
        self.assertEqual(on_boundary["rule_pack_id"], "eu.it-es.pension-coordination.2026.v12.1.1")
        self.assertEqual(on_boundary["digest_sha256"], PACK_REGISTRY[on_boundary["rule_pack_id"]]["sha256"])
        self.assertFalse(on_boundary["activation_allowed"])
        self.assertTrue(on_boundary["human_review_required"])
        self.assertNotIn("date", on_boundary)

    def test_selects_for_spanish_member_state_and_rejects_dates_outside_candidate_period(self):
        spanish = select(member_state="ES")
        outside_application_period = select(applicable_date="2027-01-01")
        outside_pack_period = select(
            right_acquisition_date="2027-01-01",
            contingency_date="2027-01-01",
        )
        self.assertEqual(spanish["status"], "candidate_selected")
        self.assertEqual(spanish["rule_pack_id"], "eu.it-es.pension-coordination.2026.v12.1.1")
        for result in (outside_application_period, outside_pack_period):
            self.assertEqual(result["status"], "not_assessed")
            self.assertIsNone(result["rule_pack_id"])

    def test_article_87b_allows_prior_contingency_with_prior_periods_classified(self):
        selected = select(
            right_acquisition_date="2026-11-02",
            contingency_date="2026-10-31",
            transition_classification="pre_application_contingency_right_acquired_after_date",
            pre_application_periods="considered_under_article_87b_2",
        )
        self.assertEqual(selected["status"], "candidate_selected")
        self.assertEqual(selected["rule_pack_id"], "eu.it-es.pension-coordination.2026.v12.1.1")
        self.assertEqual(selected["transition_classification"], "pre_application_contingency_right_acquired_after_date")

    def test_missing_or_ambiguous_legal_timing_fails_closed(self):
        cases = (
            select(applicable_date=None),
            select(right_acquisition_date="not-a-date"),
            select(transition_classification="ambiguous"),
            select(pre_application_periods="unknown"),
            select(
                right_acquisition_date="2025-12-31",
                contingency_date="2025-12-31",
                transition_classification="acquired_before_application_date",
            ),
            select(
                right_acquisition_date="2026-10-31",
                contingency_date="2026-11-01",
                transition_classification="acquired_before_application_date",
            ),
            select(
                right_acquisition_date="2026-11-02",
                contingency_date="2026-10-31",
                transition_classification="post_application_contingency",
                pre_application_periods="none",
            ),
        )
        for result in cases:
            with self.subTest(gap=result["data_gaps"][0]["code"]):
                self.assertEqual(result["status"], "not_assessed")
                self.assertIsNone(result["rule_pack_id"])
                self.assertIsNone(result["digest_sha256"])
                self.assertFalse(result["activation_allowed"])
                self.assertEqual(result["data_gaps"][0]["severity"], "blocking")

    def test_pack_digest_drift_is_rejected_without_latest_fallback(self):
        pack_id = "eu.it-es.pension-coordination.2026.v12.1.1"
        modified = dict(PACK_REGISTRY[pack_id], sha256="0" * 64)
        with patch.dict(PACK_REGISTRY, {pack_id: modified}):
            result = select()
        self.assertEqual(result["status"], "not_assessed")
        self.assertEqual(result["data_gaps"][0]["code"], "source_version_missing")

    def test_each_of_fifteen_event_jurisdiction_branches_stays_unknown(self):
        observed = set()
        for event in EVENTS:
            for jurisdiction in JURISDICTIONS:
                selection = select(member_state="ES" if jurisdiction == "ES" else "IT")
                self.assertEqual(selection["status"], "candidate_selected")
                result = evaluate_pension_timeline_source_branch(
                    event=event,
                    jurisdiction=jurisdiction,
                    rule_selection=selection,
                )
                observed.add((result["event"], result["jurisdiction"]))
                self.assertEqual(result["status"], "not_assessed")
                self.assertIsNone(result["date"])
                self.assertIsNone(result["payer"])
                self.assertIsNone(result["amount"])
                self.assertTrue(result["human_review_required"])
                self.assertEqual(len(result["data_gaps"]), 1)
                self.assertEqual(result["data_gaps"][0]["severity"], "blocking")
                self.assertIn(event, result["data_gaps"][0]["message"])
                self.assertIn(jurisdiction, result["data_gaps"][0]["message"])
        self.assertEqual(len(observed), 15)

    def test_branch_facade_rejects_tampered_pack_identity_or_digest(self):
        valid = select()
        for field, bad_value in (("rule_pack_id", "unknown.latest"), ("digest_sha256", "0" * 64)):
            selection = dict(valid)
            selection[field] = bad_value
            result = evaluate_pension_timeline_source_branch(
                event="eligibility_date", jurisdiction="EU", rule_selection=selection
            )
            self.assertEqual(result["date"], None)
            self.assertEqual(result["data_gaps"][0]["code"], "source_version_missing")

    def test_rejects_unknown_branch_keys(self):
        with self.assertRaisesRegex(ValueError, "Unsupported timeline event"):
            evaluate_pension_timeline_source_branch(event="unknown", jurisdiction="EU")
        with self.assertRaisesRegex(ValueError, "Unsupported jurisdiction"):
            evaluate_pension_timeline_source_branch(event=EVENTS[0], jurisdiction="CH")


if __name__ == "__main__":
    unittest.main()
