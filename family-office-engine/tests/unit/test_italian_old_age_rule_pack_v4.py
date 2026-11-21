"""Synthetic source/period contract checks for the non-active Italian v4 candidate."""

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
KNOWLEDGE = ROOT / "family-office-knowledge/pensions/italian-pension-adjustment-2027-2028-exceptions-v0.2.md"


class ItalianOldAgeRulePackV4Tests(unittest.TestCase):
    def test_candidate_has_complete_primary_source_roles_and_covered_periods(self):
        pack = json.loads(V4.read_text(encoding="utf-8"))
        self.assertEqual(pack["schema_version"], "inps-old-age-eligibility-rule-pack/v2")
        self.assertEqual(pack["rule_pack_id"], "it.inps-old-age-eligibility.2026-2028.v4")
        self.assertEqual(pack["provenance_status"], "candidate_pending_exact_hash_normative_review")
        self.assertEqual(pack["status"], "candidate_not_approved_source_to_rule_contract")

        sources = {source["source_id"]: source for source in pack["source_refs"]}
        original_law = sources["gazzetta.l-199-2025.25g00212"]
        self.assertEqual(original_law["legal_role"], "primary_legislation")
        self.assertTrue(original_law["url"].endswith("/25G00212/SG"))
        self.assertEqual(
            {row["provision_id"] for row in original_law["provision_periods"]},
            {
                "l199_2025_art1_comma185_general_increase",
                "l199_2025_art1_commi186_187_old_age_exception_conditions",
                "l199_2025_art1_comma190_ape_sociale_exclusion",
            },
        )
        for period in original_law["provision_periods"]:
            self.assertEqual(period["legal_effective_from"], "2025-12-30")
            self.assertEqual(period["pack_coverage_from"], "2027-01-01")
            self.assertEqual(period["pack_coverage_to"], "2028-12-31")

        self.assertEqual(
            sources["normattiva.l199-2025.art1.c185"]["legal_role"],
            "official_consolidated_consultation",
        )
        self.assertEqual(sources["inps.circolare-28-2026"]["legal_role"], "administrative_guidance")
        self.assertTrue(all(source.get("provision_periods") for source in pack["source_refs"]))
        self.assertIn("gazzetta.dl-201-2011.11g0247", sources)
        self.assertIn("gazzetta.l-214-2011.11g0256", sources)
        self.assertEqual(sources["gazzetta.l-205-2017.17g00222"]["legal_role"], "primary_legislation")
        self.assertEqual(sources["gazzetta.dlgs-67-2011.11g0111"]["legal_role"], "primary_legislation")

    def test_exception_contract_is_external_and_limited_to_article_24_comma_6(self):
        pack = json.loads(V4.read_text(encoding="utf-8"))
        contract = pack["adjustment_exception_contract"]
        self.assertEqual(contract["only_supported_age_component"], "ordinary_old_age_age_requirement_dl201_art24_comma6")
        self.assertEqual(contract["general_increase_by_year"]["2027"]["months"], 1)
        self.assertEqual(contract["general_increase_by_year"]["2028"]["months"], 3)
        self.assertEqual(contract["base_age_without_comma185_increase"]["years"], 67)
        self.assertEqual(contract["base_age_without_comma185_increase"]["months"], 0)
        self.assertEqual(contract["exception_conditions"]["assessment"], "external_source_attested_evidence_required; this pack does not classify an individual")
        self.assertEqual(contract["exception_conditions"]["missing_or_conflicting_evidence"], "not_assessed_with_blocking_data_gaps")
        self.assertEqual(
            set(contract["not_supported_paths"]),
            {
                "art24_comma7_post_1996_contributory_alternative",
                "art24_comma10_early_retirement",
                "art1_comma188_precocious_reduced_contribution",
                "art1_comma189_heavy_work_period_change",
            },
        )
        branches = contract["exception_conditions"]["alternative_evidence_branches"]
        self.assertEqual(branches[0]["source_refs"], ["gazzetta.l-199-2025.25g00212", "gazzetta.l-205-2017.17g00222"])
        self.assertEqual(branches[1]["source_refs"], ["gazzetta.l-199-2025.25g00212", "gazzetta.dlgs-67-2011.11g0111"])
        self.assertIn("social_allowance_threshold_2027_2028_not_source_bound", pack["provenance_gaps"])
        self.assertEqual(pack["threshold_bindings"]["post_1996_ordinary"]["by_year"]["2027"]["status"], "gap")
        self.assertEqual(pack["threshold_bindings"]["post_1996_ordinary"]["by_year"]["2028"]["status"], "gap")

    def test_knowledge_v02_maps_sources_and_preserves_ambiguous_paths(self):
        note = KNOWLEDGE.read_text(encoding="utf-8")
        self.assertIn("commi 185-190", note)
        self.assertIn("art. 24, comma 6", note)
        self.assertIn("art. 24, comma 7", note)
        self.assertIn("Comma 190", note)
        self.assertIn("not_assessed", note)
        self.assertIn("Non e' una regola eseguibile", note)
        self.assertIn("soglia dell'assegno sociale 2027-2028", note)
        self.assertIn("https://www.gazzettaufficiale.it/eli/id/2017/12/29/17G00222/SG", note)
        self.assertIn("https://www.gazzettaufficiale.it/eli/id/2011/05/11/11G0111/SG", note)
        self.assertNotIn(chr(0xfffd), note)
        self.assertNotIn(chr(0x00c3), note)

    def test_active_v2_service_does_not_load_candidate_v4(self):
        with self.assertRaises(ItalianOldAgeEligibilityError):
            assess_italian_old_age_eligibility({}, V4, "2026-10-13")

    def test_historical_v2_and_v3_packs_are_not_rewritten(self):
        v2 = json.loads(V2.read_text(encoding="utf-8"))
        v3 = json.loads(V3.read_text(encoding="utf-8"))
        self.assertEqual(v2["rule_pack_id"], "it.inps-old-age-eligibility.2026-2028.v2")
        self.assertEqual(v3["rule_pack_id"], "it.inps-old-age-eligibility.2026-2028.v3")
        self.assertEqual(v3["provenance_status"], "candidate_pending_exact_hash_normative_review")


if __name__ == "__main__":
    unittest.main()
