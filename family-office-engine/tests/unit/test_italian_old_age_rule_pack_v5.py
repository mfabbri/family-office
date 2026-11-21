"""Synthetic tests for the branch-specific non-active Italian Rules v5 candidate."""

import json
import unittest
from pathlib import Path

from family_office_engine.services.italian_old_age_eligibility import (
    ItalianOldAgeEligibilityError,
    assess_italian_old_age_eligibility,
)

ROOT = Path(__file__).resolve().parents[3]
RULES = ROOT / "family-office-rules/italy/2026"
V2 = RULES / "inps-old-age-eligibility.json"
V3 = RULES / "inps-old-age-eligibility-v3.json"
V4 = RULES / "inps-old-age-eligibility-v4.json"
V5 = RULES / "inps-old-age-eligibility-v5.json"
KNOWLEDGE = ROOT / "family-office-knowledge/pensions/italian-pension-adjustment-2027-2028-exceptions-v0.3.md"

class ItalianOldAgeRulePackV5Tests(unittest.TestCase):
    def test_candidate_identity_and_branch_specific_admin_sources(self):
        pack = json.loads(V5.read_text(encoding="utf-8"))
        self.assertEqual(pack["rule_pack_id"], "it.inps-old-age-eligibility.2026-2028.v5")
        self.assertEqual(pack["status"], "candidate_not_approved_branch_specific_administrative_contract")
        contract = pack["adjustment_exception_contract"]
        self.assertEqual(contract["reviewed_knowledge_id"], "knowledge.pensions.italian-adjustment-exceptions-v0.3")
        self.assertNotIn("base_age_without_comma185_increase", contract)
        branches = contract["exception_conditions"]["alternative_evidence_branches"]
        self.assertEqual([b["branch_id"] for b in branches], [
            "qualifying_profession_annex_b_seven_of_last_ten",
            "qualifying_profession_annex_b_six_of_last_seven",
            "heavy_or_arduous_work_dlgs67_2011",
        ])
        ages = [(b["administrative_age_reference"]["years"], b["administrative_age_reference"]["months"]) for b in branches]
        self.assertEqual(ages, [(66, 7), (67, 0), (66, 7)])
        for branch in branches:
            ref = branch["administrative_age_reference"]
            self.assertEqual(ref["source_id"], "inps.circolare-28-2026")
            self.assertEqual(ref["period_from"], "2027-01-01")
            self.assertEqual(ref["period_to"], "2028-12-31")
            self.assertTrue(ref["not_an_individual_determination"])
            self.assertIn("inps.circolare-28-2026", branch["source_refs"])
        self.assertEqual(contract["no_individual_outcome"], True)
        self.assertEqual(contract["exception_conditions"]["missing_or_conflicting_evidence"], "not_assessed_with_blocking_data_gaps")

    def test_heavy_work_conditions_are_explicit_and_source_bound(self):
        pack = json.loads(V5.read_text(encoding="utf-8"))
        branch = pack["adjustment_exception_contract"]["exception_conditions"]["alternative_evidence_branches"][2]
        self.assertIn("heavy_work_period_at_least_seven_of_last_ten_years", branch["required_evidence"])
        self.assertIn("heavy_work_period_at_least_half_of_total_working_life", branch["required_evidence"])
        self.assertIn("gazzetta.dlgs-67-2011.11g0111", branch["source_refs"])
        self.assertIn("gazzetta.l-199-2025.25g00212", branch["source_refs"])

    def test_knowledge_v03_preserves_admin_guidance_and_non_inference(self):
        note = KNOWLEDGE.read_text(encoding="utf-8")
        self.assertIn("66 anni e 7 mesi", note)
        self.assertIn("67 anni", note)
        self.assertIn("sette anni negli ultimi dieci", note)
        self.assertIn("sei anni negli ultimi sette", note)
        self.assertIn("faticosa e pesante", note)
        self.assertIn("not_assessed + data_gaps", note)
        self.assertNotIn(chr(0xfffd), note)
        self.assertNotIn(chr(0x00c3), note)

    def test_engine_service_rejects_candidate_v5(self):
        with self.assertRaises(ItalianOldAgeEligibilityError):
            assess_italian_old_age_eligibility({}, V5, "2026-10-13")

    def test_v2_v3_v4_baselines_are_not_rewritten(self):
        self.assertEqual(json.loads(V2.read_text(encoding="utf-8"))["rule_pack_id"], "it.inps-old-age-eligibility.2026-2028.v2")
        self.assertEqual(json.loads(V3.read_text(encoding="utf-8"))["rule_pack_id"], "it.inps-old-age-eligibility.2026-2028.v3")
        self.assertEqual(json.loads(V4.read_text(encoding="utf-8"))["rule_pack_id"], "it.inps-old-age-eligibility.2026-2028.v4")

if __name__ == "__main__":
    unittest.main()

