import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPOSITORY_ROOT / "family-office-knowledge" / "international" / "eu-annex-viii-applicability-evidence-v0.3.json"
SCHEMA_PATH = REPOSITORY_ROOT / "family-office-knowledge" / "international" / "eu-annex-viii-applicability-evidence-v0.3.schema.json"
RULE_PACK_PATH = REPOSITORY_ROOT / "family-office-rules" / "cross-border" / "eu-pension-coordination-it-es-v11.json"
CATALOGUE_PATH = REPOSITORY_ROOT / "family-office-knowledge" / "international" / "eu-annex-viii-part-2-catalogue-v0.4.json"


class AnnexViiiApplicabilityContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.policy = json.loads(RULE_PACK_PATH.read_text(encoding="utf-8"))["pro_rata_method"]["article_57_source_bound"]["annex_viii_part_2"]

    def test_schema_and_rule_pack_bind_the_versioned_contract_exactly(self):
        Draft202012Validator(self.schema, format_checker=FormatChecker()).validate(self.contract)
        knowledge = self.policy["knowledge_contract"]

        self.assertEqual(knowledge["contract_id"], self.contract["contract_id"])
        self.assertEqual(knowledge["schema_version"], self.contract["schema_version"])
        self.assertEqual(knowledge["sha256"], _sha256(CONTRACT_PATH))
        self.assertEqual(knowledge["source_ledger_sha256"], _sha256(CATALOGUE_PATH))
        self.assertEqual(self.policy["contract_schema_version"], "v0.3")
        self.assertEqual(self.policy["assessment_results"], ["matched", "not_matched", "not_assessed"])
        self.assertEqual(self.policy["source_registry"], _policy_registry(self.contract))

    def test_currentness_boundaries_are_half_open_through_2026_11_14(self):
        self.assertEqual(self.contract["currentness_chain"]["verified_through"], "2026-11-14")
        self.assertEqual(self.contract["currentness_chain"]["part_ii_status"], "unchanged_through_2026-11-14_inclusive")
        self.assertEqual({item["valid_to"] for item in self.contract["source_registry"]}, {"2026-11-15"})

        for assessment_date in ("2026-11-01", "2026-11-02", "2026-11-14"):
            with self.subTest(assessment_date=assessment_date):
                self.assertIs(_source_bound_result(self.policy, assessment_date), False)
        for assessment_date in ("2026-11-15", "2026-11-16"):
            with self.subTest(assessment_date=assessment_date):
                self.assertIsNone(_source_bound_result(self.policy, assessment_date))

    def test_part_i_only_amendment_leaves_part_ii_catalogue_and_absence_non_eligibility_semantics_intact(self):
        self.assertTrue(any("Regulation (EU) 2026/2359 changes Annex VIII Part I only and does not change Part II." in item for item in self.contract["limitations"]))
        self.assertEqual(self.contract["source_ledger"]["catalogue_id"], "eu-annex-viii-part-2-source-ledger-v0.4")
        self.assertEqual(self.policy["complete_part_2_absent_state_codes"], ["IT", "ES"])
        self.assertTrue(self.policy["not_matched_requires_complete_current_part_2"])
        self.assertTrue(self.policy["matched_requires_separate_official_national_or_institutional_binding"])
        self.assertIn("separate official national or institutional source", self.contract["assessment_contract"]["matched"])

    def test_later_oj_event_is_not_assessed_with_data_gap(self):
        """Synthetic contract test; it does not exercise production runtime behavior."""
        later_event = {
            "source_id": "synthetic-later-official-oj",
            "role": "annex_currentness_official_oj",
            "published_on": "2026-11-14",
        }
        outcome = _contract_assessment(self.contract, self.policy, "IT", "2026-11-14", later_event)

        self.assertEqual(outcome["assessment_result"], "not_assessed")
        self.assertEqual(outcome["data_gaps"], ["annex_viii_currentness_outside_verified_interval"])

    def test_it_and_es_absence_has_no_eligibility_or_human_review_conclusion(self):
        """Synthetic contract test; it does not exercise production runtime behavior."""
        self.assertIn("not_assessed", self.contract["assessment_contract"]["fail_closed"])
        self.assertIn("not_assessed", self.policy["assessment_results"])
        for state_code in ("IT", "ES"):
            with self.subTest(state_code=state_code):
                outcome = _contract_assessment(self.contract, self.policy, state_code, "2026-11-14")
                self.assertEqual(outcome["assessment_result"], "not_matched")
                self.assertEqual(outcome["data_gaps"], [])
                self.assertNotIn("eligibility", outcome)
                self.assertNotIn("human_review", outcome)

    def test_2026_11_16_is_not_assessed_with_currentness_gap(self):
        """Synthetic contract test; it does not exercise production runtime behavior."""
        outcome = _contract_assessment(self.contract, self.policy, "IT", "2026-11-16")

        self.assertEqual(outcome["assessment_result"], "not_assessed")
        self.assertEqual(outcome["data_gaps"], ["annex_viii_currentness_outside_verified_interval"])


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _policy_registry(contract):
    return [{key: source[key] for key in ("source_id", "role", "valid_from", "valid_to")} for source in contract["source_registry"]]


def _source_bound_result(policy, assessment_date):
    return False if all(source["valid_from"] <= assessment_date < source["valid_to"] for source in policy["source_registry"]) else None


def _contract_assessment(contract, policy, state_code, assessment_date, later_event=None):
    in_interval = _source_bound_result(policy, assessment_date) is False
    if later_event is not None and assessment_date >= later_event["published_on"]:
        in_interval = False
    if not in_interval:
        return _fail_closed_currentness_outcome(contract, policy)
    absence = state_code in contract["reviewed_absence"]["state_codes"] and state_code in policy["complete_part_2_absent_state_codes"]
    return {"assessment_result": "not_matched" if absence else "not_assessed", "data_gaps": []}


def _fail_closed_currentness_outcome(contract, policy):
    assert "not_assessed" in contract["assessment_contract"]["fail_closed"]
    assessment_result = next(result for result in policy["assessment_results"] if result == "not_assessed")
    return {"assessment_result": assessment_result, "data_gaps": ["annex_viii_currentness_outside_verified_interval"]}


if __name__ == "__main__":
    unittest.main()
