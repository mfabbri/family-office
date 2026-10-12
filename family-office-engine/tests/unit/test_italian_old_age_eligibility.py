import unittest
import json
import tempfile
from pathlib import Path
from family_office_engine.services.italian_old_age_eligibility import ItalianOldAgeEligibilityError, assess_italian_old_age_eligibility

PACK = Path(__file__).resolve().parents[3] / "family-office-rules/italy/2026/inps-old-age-eligibility.json"
def facts(**updates):
    value = {"candidate_date": "2026-10-10", "date_of_birth": "1959-10-10", "date_of_birth_verified": True, "date_of_birth_source_refs": ["identity-record-1"], "contribution_cohort": "before_1996", "contribution_cohort_confirmed": True, "ordinary_single_management_profile_confirmed": True, "scope_evidence": {"verified": True, "as_of_date": "2026-10-10", "source_refs": ["employment-record-1"]}, "management": "FPLD", "management_confirmed": True, "employment_category": "employee", "multiple_managements": False, "foreign_or_eu_aggregation": False, "special_or_excluded_profile": False, "cessation_confirmed": True, "cessation_evidence": {"verified": True, "cessation_date": "2026-10-10", "source_refs": ["employer-separation-1"]}, "contribution_evidence": {"as_of_date": "2026-10-10", "period_end": "2026-10-10", "verified": True, "source_refs": ["contribution-statement-1"], "first_contribution_date": "1990-01-01", "qualifying_contribution_years": "20", "effective_contribution_years_excluding_figurative": "20"}}
    value.update(updates)
    if "contribution_cohort" in updates and "contribution_evidence" not in updates:
        value["contribution_evidence"] = {**value["contribution_evidence"], "first_contribution_date": "2000-01-01" if updates["contribution_cohort"] == "on_or_after_1996" else "1990-01-01"}
    if isinstance(updates.get("contribution_evidence"), dict):
        value["contribution_evidence"] = {**facts()["contribution_evidence"], **updates["contribution_evidence"]}
        if "contribution_cohort" in updates:
            value["contribution_evidence"]["first_contribution_date"] = "2000-01-01" if updates["contribution_cohort"] == "on_or_after_1996" else "1990-01-01"
    return value

class ItalianOldAgeEligibilityTest(unittest.TestCase):
    def assess(self, **updates): return assess_italian_old_age_eligibility(facts(**updates), PACK, "2026-10-11")
    def gap(self, result, code): self.assertEqual(result["status"], "not_assessed"); self.assertIsNone(result["result"]); self.assertIn(code, {g["code"] for g in result["data_gaps"]})
    def test_age_contribution_boundaries_and_2026_2028_requirements(self):
        self.assertEqual(self.assess()["result"], "eligible")
        self.assertEqual(self.assess(contribution_evidence={"as_of_date": "2026-10-10", "qualifying_contribution_years": "19.99"})["result"], "not_yet_eligible")
        self.assertEqual(self.assess(candidate_date="2027-11-10", date_of_birth="1960-10-10")["result"], "eligible")
        self.assertEqual(self.assess(candidate_date="2028-01-10", date_of_birth="1960-10-10")["result"], "eligible")
    def test_2029_and_missing_evidence_are_gaps(self):
        self.gap(self.assess(candidate_date="2029-10-10"), "rule_pack_period_unsupported")
        self.gap(self.assess(contribution_cohort="unknown"), "contribution_cohort_unknown")
        self.gap(self.assess(management_confirmed=False), "management_unsupported_or_unconfirmed")
        self.gap(self.assess(contribution_evidence=None), "contribution_evidence_missing_or_undated")
        self.gap(self.assess(cessation_confirmed=False), "employee_cessation_evidence_missing")
        self.gap(self.assess(cessation_required=False), "employee_cessation_evidence_missing")
        self.gap(self.assess(cessation_evidence={"verified": True, "cessation_date": "2026-10-10"}), "employee_cessation_evidence_missing")
    def test_pure_contributory_threshold_equal_below_and_alternative(self):
        base = {"contribution_cohort": "on_or_after_1996", "documented_monthly_pension_amount": "600", "documented_monthly_social_allowance": "600", "monthly_amount_evidence": {"as_of_date": "2026-10-10", "valid_for_year": 2026, "verified": True, "source_refs": ["amount-record-1"]}}
        self.assertEqual(self.assess(**base)["result"], "eligible")
        self.assertEqual(self.assess(**{**base, "documented_monthly_pension_amount": "599.99"})["result"], "not_yet_eligible")
        evidence = {"as_of_date": "2026-10-10", "period_end": "2026-10-10", "verified": True, "source_refs": ["contribution-statement-1"], "first_contribution_date": "2000-01-01", "qualifying_contribution_years": "5", "effective_contribution_years_excluding_figurative": "5"}
        self.assertEqual(self.assess(candidate_date="2026-10-10", date_of_birth="1955-10-10", contribution_cohort="on_or_after_1996", contribution_evidence=evidence)["result"], "eligible")
        evidence["effective_contribution_years_excluding_figurative"] = "4.99"
        self.assertEqual(self.assess(candidate_date="2026-10-10", date_of_birth="1955-10-10", contribution_cohort="on_or_after_1996", contribution_evidence=evidence)["result"], "not_yet_eligible")
    def test_excluded_profiles_and_no_timeline_fields(self):
        for update, code in (({"multiple_managements": True}, "multiple_managements_unsupported"), ({"foreign_or_eu_aggregation": True}, "foreign_or_eu_aggregation_unsupported"), ({"special_or_excluded_profile": True}, "special_or_excluded_profile_unsupported"), ({"multiple_managements": None}, "multiple_managements_unsupported"), ({"date_of_birth": "1960-02-29"}, "age_day_semantics_unsupported")):
            self.gap(self.assess(**update), code)
        result = self.assess()
        self.assertTrue({"official_recognition_date", "economic_effective_date", "first_cash_payment_date", "pension_stream", "work_exit_feasibility"}.isdisjoint(result))
    def test_alternative_path_survives_below_or_missing_twenty_year_amount_threshold(self):
        evidence = {"as_of_date": "2026-10-10", "period_end": "2026-10-10", "verified": True, "source_refs": ["contribution-statement-1"], "first_contribution_date": "2000-01-01", "qualifying_contribution_years": "20", "effective_contribution_years_excluding_figurative": "5"}
        common = {"candidate_date": "2026-10-10", "date_of_birth": "1955-10-10", "contribution_cohort": "on_or_after_1996", "contribution_evidence": evidence}
        self.assertEqual(self.assess(**common, documented_monthly_pension_amount="599", documented_monthly_social_allowance="600", monthly_amount_evidence={"as_of_date": "2026-10-10", "valid_for_year": 2026, "verified": True, "source_refs": ["amount-record-1"]})["result"], "eligible")
        self.assertEqual(self.assess(**common)["result"], "eligible")
        common["contribution_evidence"] = {**evidence, "effective_contribution_years_excluding_figurative": None}
        self.gap(self.assess(**common, documented_monthly_pension_amount="599", documented_monthly_social_allowance="600", monthly_amount_evidence={"as_of_date": "2026-10-10", "valid_for_year": 2026, "verified": True, "source_refs": ["amount-record-1"]}), "effective_contribution_total_missing")
    def test_candidate_date_and_year_bind_evidence(self):
        self.gap(self.assess(contribution_evidence={"as_of_date": "2026-10-11", "period_end": "2026-10-11"}), "contribution_evidence_not_applicable_to_candidate")
        self.gap(self.assess(contribution_evidence={"as_of_date": "2026-10-10", "period_end": "2026-10-11"}), "contribution_evidence_not_applicable_to_candidate")
        self.gap(self.assess(contribution_cohort="on_or_after_1996", documented_monthly_pension_amount="600", documented_monthly_social_allowance="600", monthly_amount_evidence={"as_of_date": "2026-10-10", "valid_for_year": 2025, "verified": True, "source_refs": ["amount-record-1"]}), "monthly_amount_evidence_missing")
        self.gap(self.assess(contribution_cohort="on_or_after_1996", documented_monthly_pension_amount="600", documented_monthly_social_allowance="600", monthly_amount_evidence={"as_of_date": "2026-10-11", "valid_for_year": 2026, "verified": True, "source_refs": ["amount-record-1"]}), "monthly_amount_evidence_missing")
        self.gap(self.assess(scope_evidence=None), "scope_evidence_missing_or_unverified")
        self.gap(self.assess(cessation_evidence={"verified": True, "cessation_date": "2026-10-11", "source_refs": ["employer-separation-1"]}), "employee_cessation_after_candidate")
    def test_consumer_reads_contribution_thresholds_from_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            pack_path = Path(directory) / "pack.json"
            pack = json.loads(PACK.read_text(encoding="utf-8"))
            pack["paths"]["pre_1996"]["minimum_qualifying_contribution_years"] = 21
            pack_path.write_text(json.dumps(pack), encoding="utf-8")
            result = assess_italian_old_age_eligibility(facts(), pack_path, "2026-10-11")
        self.assertEqual(result["result"], "not_yet_eligible")
        with tempfile.TemporaryDirectory() as directory:
            pack_path = Path(directory) / "pack.json"
            pack = json.loads(PACK.read_text(encoding="utf-8"))
            pack["supported_scope"]["managements"] = ["FPLD"]
            pack_path.write_text(json.dumps(pack), encoding="utf-8")
            result = assess_italian_old_age_eligibility(facts(management="AGO"), pack_path, "2026-10-11")
        self.assertEqual(result["status"], "not_assessed")
        with tempfile.TemporaryDirectory() as directory:
            pack_path = Path(directory) / "pack.json"
            pack = json.loads(PACK.read_text(encoding="utf-8"))
            pack["paths"]["post_1996_alternative"]["minimum_effective_contribution_years"] = 6
            pack_path.write_text(json.dumps(pack), encoding="utf-8")
            evidence = {"as_of_date": "2026-10-10", "period_end": "2026-10-10", "verified": True, "source_refs": ["contribution-statement-1"], "first_contribution_date": "2000-01-01", "qualifying_contribution_years": "5", "effective_contribution_years_excluding_figurative": "5"}
            alternative_facts = facts(candidate_date="2026-10-10", date_of_birth="1955-10-10", contribution_cohort="on_or_after_1996", contribution_evidence=evidence)
            result = assess_italian_old_age_eligibility(alternative_facts, pack_path, "2026-10-11")
        self.assertEqual(result["result"], "not_yet_eligible")
    def test_invalid_age_threshold_and_nonfinite_numbers_fail_closed(self):
        self.gap(self.assess(candidate_date="2027-02-28", date_of_birth="1960-01-29"), "age_day_semantics_unsupported")
        self.gap(self.assess(contribution_evidence={"qualifying_contribution_years": "NaN"}), "qualifying_contribution_total_missing")
    def test_malformed_or_unsupported_rule_pack_is_rejected(self):
        mutations = (
            lambda pack: pack["paths"]["pre_1996"].pop("minimum_qualifying_contribution_years"),
            lambda pack: None,
            lambda pack: pack["requirements_by_year"].pop("2028"),
            lambda pack: pack.update(schema_version="wrong/v1"),
            lambda pack: pack.update(jurisdiction="ES"),
            lambda pack: pack.update(rule_pack_id="wrong.id"),
            lambda pack: pack.update(valid_to="2029-12-31"),
            lambda pack: pack["paths"]["post_1996_alternative"].update(figurative_contribution_counts=True),
            lambda pack: pack["source_refs"][1]["provision_periods"][0].update(valid_to="2027-12-31"),
            lambda pack: pack["supported_scope"].update(managements=["OTHER"]),
            lambda pack: next(source for source in pack["source_refs"] if source["source_id"] == "inps.pensione-vecchiaia")["provision_periods"][1].update(valid_from="2026-12-31", valid_to="2028-01-01"),
            lambda pack: pack["source_refs"][1]["provision_periods"][0].update(provision_id="contribution_threshold"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, mutate in enumerate(mutations):
                with self.subTest(index=index):
                    path = Path(directory) / f"pack-{index}.json"
                    pack = json.loads(PACK.read_text(encoding="utf-8"))
                    if index == 1:
                        pack["paths"]["post_1996"]["minimum_qualifying_contribution_years"] = "twenty"
                    else:
                        mutate(pack)
                    path.write_text(json.dumps(pack), encoding="utf-8")
                    with self.assertRaises(ItalianOldAgeEligibilityError):
                        assess_italian_old_age_eligibility(facts(), path, "2026-10-11")
