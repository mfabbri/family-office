import unittest
import json
import tempfile
from pathlib import Path
from family_office_engine.services.italian_old_age_eligibility import ItalianOldAgeEligibilityError, assess_italian_old_age_eligibility, search_first_post_1996_alternative_eligibility_month, search_first_post_1996_ordinary_threshold_eligibility_month

PACK = Path(__file__).resolve().parents[3] / "family-office-rules/italy/2026/inps-old-age-eligibility.json"
def facts(**updates):
    value = {"candidate_date": "2026-10-10", "date_of_birth": "1959-10-10", "date_of_birth_verified": True, "date_of_birth_source_refs": ["identity-record-1"], "contribution_cohort": "before_1996", "contribution_cohort_confirmed": True, "ordinary_single_management_profile_confirmed": True, "scope_evidence": {"verified": True, "as_of_date": "2026-10-10", "coverage_from": "2026-01-01", "coverage_to": "2026-10-10", "source_refs": ["employment-record-1"]}, "management": "FPLD", "management_confirmed": True, "employment_category": "employee", "multiple_managements": False, "foreign_or_eu_aggregation": False, "special_or_excluded_profile": False, "cessation_confirmed": True, "cessation_evidence": {"verified": True, "cessation_date": "2026-10-10", "as_of_date": "2026-10-10", "source_refs": ["employer-separation-1"]}, "contribution_evidence": {"as_of_date": "2026-10-10", "period_end": "2026-10-10", "verified": True, "source_refs": ["contribution-statement-1"], "first_contribution_date": "1990-01-01", "qualifying_contribution_years": "20", "effective_contribution_years_excluding_figurative": "20"}}
    value.update(updates)
    if "contribution_cohort" in updates and "contribution_evidence" not in updates:
        value["contribution_evidence"] = {**value["contribution_evidence"], "first_contribution_date": "2000-01-01" if updates["contribution_cohort"] == "on_or_after_1996" else "1990-01-01"}
    if isinstance(updates.get("contribution_evidence"), dict):
        value["contribution_evidence"] = {**facts()["contribution_evidence"], **updates["contribution_evidence"]}
        if "contribution_cohort" in updates:
            value["contribution_evidence"]["first_contribution_date"] = "2000-01-01" if updates["contribution_cohort"] == "on_or_after_1996" else "1990-01-01"
    return value

def monthly_history(last_month="2026-09", eligible_month="2026-09"):
    from calendar import monthrange
    year, month = 2026, 1
    rows = []
    while f"{year:04d}-{month:02d}" <= last_month:
        key = f"{year:04d}-{month:02d}"
        last_day = monthrange(year, month)[1]
        rows.append({"month": key, "period_start": f"{key}-01", "period_end": f"{key}-{last_day:02d}", "as_of_date": f"{key}-{last_day:02d}", "verified": True, "source_refs": [f"statement-{key}"], "effective_contribution_years_excluding_figurative": "5" if key >= eligible_month else "4.99", "effective_contribution_unit": "years", "original_contribution_units": ["years"], "original_contribution_types": ["mandatory"], "figurative_excluded": True})
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return rows

def ordinary_monthly_history(last_month="2026-09", eligible_month="2026-09", amount="546.24"):
    rows = monthly_history(last_month, eligible_month)
    for row in rows:
        row.pop("effective_contribution_years_excluding_figurative")
        row.pop("effective_contribution_unit")
        row.pop("figurative_excluded")
        row["qualifying_contribution_years"] = "20" if row["month"] >= eligible_month else "19.99"
        row["qualifying_contribution_unit"] = "years"
        row["documented_monthly_pension_amount"] = amount
        row["monthly_pension_amount_evidence"] = {"verified": True, "as_of_date": "2026-10-13", "valid_for_month": row["month"], "documented_monthly_pension_amount": amount, "source_refs": [f"pension-estimate-{row['month']}"]}
    return rows

class ItalianOldAgeEligibilityTest(unittest.TestCase):
    def assess(self, **updates): return assess_italian_old_age_eligibility(facts(**updates), PACK, "2026-10-13")
    def gap(self, result, code): self.assertEqual(result["status"], "not_assessed"); self.assertIsNone(result["result"]); self.assertIn(code, {g["code"] for g in result["data_gaps"]})
    def month_search_facts(self, **updates):
        value = facts(candidate_date=None, date_of_birth="1955-09-10", contribution_cohort="on_or_after_1996", contribution_cohort_confirmed=True, scope_evidence={"verified": True, "as_of_date": "2026-10-13", "coverage_from": "2026-01-01", "coverage_to": "2026-09-30", "source_refs": ["employment-record-1"]}, cessation_evidence={"verified": True, "cessation_date": "2026-01-01", "as_of_date": "2026-10-13", "source_refs": ["employer-separation-1"]}, contribution_evidence={"verified": True, "as_of_date": "2026-10-13", "period_end": "2026-10-13", "source_refs": ["contribution-statement-1"], "first_contribution_date": "2000-01-01"})
        value.update(updates)
        return value
    def test_pack_declares_primary_chain_and_retains_explicit_gap(self):
        pack = json.loads(PACK.read_text(encoding="utf-8"))
        self.assertEqual(pack["provenance_schema_version"], "normative-source-provenance/v1")
        self.assertEqual(pack["schema_version"], "inps-old-age-eligibility-rule-pack/v2")
        self.assertEqual(pack["rule_pack_id"], "it.inps-old-age-eligibility.2026-2028.v2")
        self.assertEqual(pack["provenance_status"], "source_bound_reviewed_limited")
        self.assertNotIn("historic_derivation_of_base_71_not_fully_reconstructed", pack["provenance_gaps"])
        roles = {source["source_id"]: source.get("legal_role") for source in pack["source_refs"]}
        self.assertEqual(roles["inps.pensione-vecchiaia"], "administrative_guidance")
        self.assertEqual(roles["normattiva.dl-201-2011.art24"], "primary_legislation")
        self.assertEqual(roles["normattiva.l199-2025.art1.c185"], "primary_legislation")
        self.assertEqual(roles["gazzetta.decreto-19-12-2025.25a07010"], "binding_implementing_act")
        self.assertEqual(roles["gazzetta.decreto-06-12-2011.11a16083"], "binding_implementing_act")
        self.assertEqual(roles["gazzetta.decreto-16-12-2014.14a09922"], "binding_implementing_act")
        self.assertEqual(roles["gazzetta.decreto-05-12-2017.17a08386"], "binding_implementing_act")
        self.assertEqual(roles["gazzetta.decreto-05-11-2019.19a07047"], "binding_implementing_act")
        self.assertEqual(roles["gazzetta.decreto-27-10-2021.21a06556"], "binding_implementing_act")
        self.assertEqual(roles["gazzetta.decreto-18-07-2023.23a05661"], "binding_implementing_act")
        self.assertEqual(roles["inps.circolare-62-2018"], "administrative_guidance")
        provision = next(source for source in pack["source_refs"] if source["source_id"] == "gazzetta.decreto-05-12-2017.17a08386")["provision_periods"][0]
        self.assertEqual((provision["legal_effective_from"], provision["legal_effective_to"]), ("2019-01-01", None))
        self.assertEqual((provision["pack_coverage_from"], provision["pack_coverage_to"]), ("2026-01-01", "2028-12-31"))
        self.assertEqual(roles["inps.requisiti-2027-2028"], "administrative_guidance")
        adjustment_ids = {"historic_adjustment_2013", "historic_adjustment_2016", "historic_adjustment_2019"}
        adjustments = {
            item["provision_id"]: item
            for source in pack["source_refs"]
            for item in source["provision_periods"]
            if item["provision_id"] in adjustment_ids
        }
        months_added = {key: item["adjustment_months"] for key, item in adjustments.items()}
        self.assertEqual(months_added, {"historic_adjustment_2013": 3, "historic_adjustment_2016": 4, "historic_adjustment_2019": 5})
        self.assertEqual(70 * 12 + sum(months_added.values()), 71 * 12)
        self.assertEqual({item["legal_effective_to"] for item in adjustments.values()}, {None})
        self.assertEqual(pack["requirements_by_year"]["2026"]["contributory_alternative_age"]["years"], 71)
        self.assertEqual(pack["requirements_by_year"]["2026"]["contributory_alternative_age"]["months"], 0)
        self.assertEqual(pack["requirements_by_year"]["2027"]["contributory_alternative_age"]["months"], 1)
        self.assertEqual(pack["requirements_by_year"]["2028"]["contributory_alternative_age"]["months"], 3)
    def test_age_contribution_boundaries_and_2026_2028_requirements(self):
        self.assertEqual(self.assess()["result"], "eligible")
        self.assertEqual(self.assess(contribution_evidence={"as_of_date": "2026-10-10", "qualifying_contribution_years": "19.99"})["result"], "not_yet_eligible")
        self.assertEqual(self.assess(candidate_date="2027-11-10", date_of_birth="1960-10-10")["result"], "eligible")
        self.assertEqual(self.assess(candidate_date="2028-01-10", date_of_birth="1960-10-10")["result"], "eligible")

    def test_path_specific_month_search_uses_complete_monthly_source_bound_history(self):
        value = self.month_search_facts()
        result = search_first_post_1996_alternative_eligibility_month(value, monthly_history(), PACK, "2026-10-13")
        self.assertEqual((result["status"], result["result"], result["path"], result["first_eligible_month"]), ("assessed", "eligible", "post_1996_alternative", "2026-09"))
        self.assertNotIn("candidate_date", result)
        self.assertEqual(result["as_of_date"], "2026-10-13")
        self.assertTrue(result["human_review_required"])

    def ordinary_month_search_facts(self, **updates):
        value = self.month_search_facts(
            date_of_birth="1959-09-10",
            cessation_evidence={"verified": True, "cessation_date": "2026-01-01", "as_of_date": "2026-01-01", "source_refs": ["employer-separation-1"]},
        )
        value.update(updates)
        return value

    def test_ordinary_threshold_month_search_returns_exact_threshold_and_below_amount(self):
        result = search_first_post_1996_ordinary_threshold_eligibility_month(self.ordinary_month_search_facts(), ordinary_monthly_history(), PACK, "2026-10-13")
        self.assertEqual((result["status"], result["result"], result["path"], result["first_eligible_month"]), ("assessed", "eligible", "post_1996_ordinary_threshold", "2026-09"))
        history = ordinary_monthly_history(last_month="2026-10", eligible_month="2026-09", amount="546.23")
        history[-1]["documented_monthly_pension_amount"] = "546.24"
        history[-1]["monthly_pension_amount_evidence"]["documented_monthly_pension_amount"] = "546.24"
        history[-1]["monthly_pension_amount_evidence"]["as_of_date"] = "2026-10-31"
        value = self.ordinary_month_search_facts(
            scope_evidence={"verified": True, "as_of_date": "2026-10-31", "coverage_from": "2026-01-01", "coverage_to": "2026-10-31", "source_refs": ["employment-record-1"]},
            cessation_evidence={"verified": True, "cessation_date": "2026-01-01", "as_of_date": "2026-10-13", "source_refs": ["employer-separation-1"]},
        )
        result = search_first_post_1996_ordinary_threshold_eligibility_month(value, history, PACK, "2026-10-31")
        self.assertEqual((result["status"], result["result"], result["first_eligible_month"]), ("assessed", "eligible", "2026-10"))

    def test_ordinary_threshold_month_search_requires_month_valid_amount_and_separate_provenance(self):
        history = ordinary_monthly_history()
        history[-1]["monthly_pension_amount_evidence"]["valid_for_month"] = "2026-08"
        result = search_first_post_1996_ordinary_threshold_eligibility_month(self.ordinary_month_search_facts(), history, PACK, "2026-10-13")
        self.assertIn("monthly_pension_amount_evidence_missing_or_not_applicable", {item["code"] for item in result["data_gaps"]})
        history = ordinary_monthly_history()
        history[-1]["monthly_pension_amount_evidence"]["source_refs"] = history[-1]["source_refs"]
        result = search_first_post_1996_ordinary_threshold_eligibility_month(self.ordinary_month_search_facts(), history, PACK, "2026-10-13")
        self.assertIn("monthly_pension_amount_evidence_missing_or_not_applicable", {item["code"] for item in result["data_gaps"]})
        history = ordinary_monthly_history()
        history[-1]["monthly_pension_amount_evidence"]["as_of_date"] = "2026-08-31"
        result = search_first_post_1996_ordinary_threshold_eligibility_month(self.ordinary_month_search_facts(), history, PACK, "2026-10-13")
        self.assertIn("monthly_pension_amount_evidence_missing_or_not_applicable", {item["code"] for item in result["data_gaps"]})
        history = ordinary_monthly_history()
        history[-1]["monthly_pension_amount_evidence"]["documented_monthly_pension_amount"] = "546.25"
        result = search_first_post_1996_ordinary_threshold_eligibility_month(self.ordinary_month_search_facts(), history, PACK, "2026-10-13")
        self.assertIn("monthly_pension_amount_evidence_missing_or_not_applicable", {item["code"] for item in result["data_gaps"]})

    def test_ordinary_threshold_month_search_uses_month_end_age_and_contribution_boundaries(self):
        value = self.ordinary_month_search_facts(date_of_birth="1959-09-15")
        history = ordinary_monthly_history(last_month="2026-09", eligible_month="2026-09")
        result = search_first_post_1996_ordinary_threshold_eligibility_month(value, history, PACK, "2026-10-13")
        self.assertEqual(result["first_eligible_month"], "2026-09")
        history[-1]["qualifying_contribution_years"] = "19.99"
        result = search_first_post_1996_ordinary_threshold_eligibility_month(value, history, PACK, "2026-10-13")
        self.assertIn("eligibility_not_found_in_observed_history", {item["code"] for item in result["data_gaps"]})

    def test_ordinary_threshold_month_search_stops_on_first_2027_or_2028_threshold_gap(self):
        from datetime import date as Date, timedelta
        for year, dob, last_month, as_of, eligible_month in ((2027, "1960-01-15", "2027-02", "2027-02-28", "2026-01"), (2028, "1960-09-15", "2028-01", "2028-01-31", "2028-01")):
            with self.subTest(year=year), tempfile.TemporaryDirectory() as directory:
                pack = json.loads(PACK.read_text(encoding="utf-8"))
                for source in pack["source_refs"]:
                    source["retrieved_on"] = source["reviewed_on"] = as_of
                    source["next_review_due"] = (Date.fromisoformat(as_of) + timedelta(days=90)).isoformat()
                path = Path(directory) / "pack.json"
                path.write_text(json.dumps(pack), encoding="utf-8")
                value = self.ordinary_month_search_facts(date_of_birth=dob, scope_evidence={"verified": True, "as_of_date": as_of, "coverage_from": "2026-01-01", "coverage_to": as_of, "source_refs": ["employment-record-1"]}, cessation_evidence={"verified": True, "cessation_date": "2026-01-01", "as_of_date": "2026-01-01", "source_refs": ["employer-separation-1"]}, contribution_evidence={"verified": True, "as_of_date": as_of, "period_end": as_of, "source_refs": ["contribution-statement-1"], "first_contribution_date": "2000-01-01"})
                history = ordinary_monthly_history(last_month=last_month, eligible_month=eligible_month)
                for row in history:
                    row["monthly_pension_amount_evidence"]["as_of_date"] = as_of
                result = search_first_post_1996_ordinary_threshold_eligibility_month(value, history, path, as_of)
                self.assertEqual(result["status"], "not_assessed")
                self.assertIsNone(result["first_eligible_month"])
                self.assertIn("monthly_social_allowance_threshold_not_source_bound", {item["code"] for item in result["data_gaps"]})

    def test_ordinary_threshold_month_search_fails_closed_for_history_scope_cessation_and_freshness_dates(self):
        history = ordinary_monthly_history()
        history[4]["qualifying_contribution_years"] = "18"
        result = search_first_post_1996_ordinary_threshold_eligibility_month(self.ordinary_month_search_facts(), history, PACK, "2026-10-13")
        self.assertIn("monthly_history_invalid_or_incomplete", {item["code"] for item in result["data_gaps"]})
        value = self.ordinary_month_search_facts(cessation_evidence={"verified": True, "cessation_date": "2026-10-31", "as_of_date": "2026-10-31", "source_refs": ["employer-separation-1"]})
        result = search_first_post_1996_ordinary_threshold_eligibility_month(value, ordinary_monthly_history(), PACK, "2026-10-13")
        self.assertIn("employee_cessation_evidence_missing", {item["code"] for item in result["data_gaps"]})
        history = ordinary_monthly_history()
        history[-1]["monthly_pension_amount_evidence"]["as_of_date"] = "2026-10-14"
        result = search_first_post_1996_ordinary_threshold_eligibility_month(self.ordinary_month_search_facts(), history, PACK, "2026-10-13")
        self.assertIn("monthly_pension_amount_evidence_missing_or_not_applicable", {item["code"] for item in result["data_gaps"]})

    def test_path_specific_month_search_fails_closed_for_gap_or_unconverted_units(self):
        value = self.month_search_facts()
        history = monthly_history()
        del history[4]
        result = search_first_post_1996_alternative_eligibility_month(value, history, PACK, "2026-10-13")
        self.assertIsNone(result["first_eligible_month"])
        self.assertIn("monthly_history_invalid_or_incomplete", {item["code"] for item in result["data_gaps"]})
        history = monthly_history()
        history[0]["original_contribution_units"] = ["weeks"]
        result = search_first_post_1996_alternative_eligibility_month(value, history, PACK, "2026-10-13")
        self.assertIsNone(result["first_eligible_month"])
        self.assertIn("original_contribution_units_missing_or_unsupported", {item["code"] for item in result["data_gaps"]})

    def test_month_search_rejects_future_cohort_scope_and_nonreproducible_inputs(self):
        value = self.month_search_facts()
        value["contribution_evidence"]["first_contribution_date"] = "2027-01-01"
        result = search_first_post_1996_alternative_eligibility_month(value, monthly_history(), PACK, "2026-10-13")
        self.assertIsNone(result["first_eligible_month"])
        self.assertTrue({"post_1996_cohort_unconfirmed", "monthly_history_invalid_or_incomplete"} & {item["code"] for item in result["data_gaps"]})
        value = self.month_search_facts(scope_evidence={"verified": True, "as_of_date": "2026-10-13", "coverage_from": "2026-01-01", "coverage_to": "2026-08-31", "source_refs": ["employment-record-1"]})
        result = search_first_post_1996_alternative_eligibility_month(value, monthly_history(), PACK, "2026-10-13")
        self.assertIsNone(result["first_eligible_month"])
        self.assertIn("scope_evidence_does_not_cover_history", {item["code"] for item in result["data_gaps"]})
        result = search_first_post_1996_alternative_eligibility_month(self.month_search_facts(), monthly_history(), PACK)
        self.assertIsNone(result["first_eligible_month"])
        self.assertIn("as_of_date_missing_or_invalid", {item["code"] for item in result["data_gaps"]})
        result = search_first_post_1996_alternative_eligibility_month(self.month_search_facts(), monthly_history(), PACK, "2026-02-30")
        self.assertIsNone(result["as_of_date"])
        self.assertIn("as_of_date_missing_or_invalid", {item["code"] for item in result["data_gaps"]})
        value = self.month_search_facts()
        value["contribution_evidence"]["as_of_date"] = "2026-10-14"
        value["contribution_evidence"]["period_end"] = "2026-10-14"
        result = search_first_post_1996_alternative_eligibility_month(value, monthly_history(), PACK, "2026-10-13")
        self.assertIsNone(result["first_eligible_month"])
        self.assertIn("post_1996_cohort_unconfirmed", {item["code"] for item in result["data_gaps"]})
        for field in ("first_contribution_date", "as_of_date", "period_end"):
            with self.subTest(malformed_cohort_date=field):
                value = self.month_search_facts()
                value["contribution_evidence"][field] = "2026-02-30"
                result = search_first_post_1996_alternative_eligibility_month(value, monthly_history(), PACK, "2026-10-13")
                self.assertIsNone(result["first_eligible_month"])
                self.assertIn("post_1996_cohort_unconfirmed", {item["code"] for item in result["data_gaps"]})

    def test_month_search_requires_original_units_types_and_nonfigurative_evidence(self):
        for field, bad_value, expected_gap in (("original_contribution_units", [], "original_contribution_units_missing_or_unsupported"), ("original_contribution_units", ["years", "weeks"], "original_contribution_units_missing_or_unsupported"), ("original_contribution_units", ["years", "years"], "original_contribution_units_missing_or_unsupported"), ("original_contribution_types", [""], "monthly_history_invalid_or_incomplete"), ("figurative_excluded", False, "monthly_history_invalid_or_incomplete")):
            with self.subTest(field=field, value=bad_value):
                history = monthly_history()
                history[0][field] = bad_value
                result = search_first_post_1996_alternative_eligibility_month(self.month_search_facts(), history, PACK, "2026-10-13")
                self.assertIsNone(result["first_eligible_month"])
                self.assertIn(expected_gap, {item["code"] for item in result["data_gaps"]})

    def test_month_search_rejects_scope_coverage_after_scope_evidence_date(self):
        value = self.month_search_facts(scope_evidence={"verified": True, "as_of_date": "2026-06-30", "coverage_from": "2026-01-01", "coverage_to": "2026-09-30", "source_refs": ["employment-record-1"]})
        result = search_first_post_1996_alternative_eligibility_month(value, monthly_history(), PACK, "2026-10-13")
        self.assertIsNone(result["first_eligible_month"])
        self.assertIn("scope_evidence_coverage_missing_or_invalid", {item["code"] for item in result["data_gaps"]})

    def test_month_search_rejects_reordered_nonmonotonic_and_future_history(self):
        for mutation in ("reordered", "nonmonotonic", "future"):
            with self.subTest(mutation=mutation):
                history = monthly_history()
                if mutation == "reordered":
                    history[1], history[2] = history[2], history[1]
                elif mutation == "nonmonotonic":
                    history[1]["effective_contribution_years_excluding_figurative"] = "4.5"
                else:
                    history[-1]["as_of_date"] = "2026-10-31"
                result = search_first_post_1996_alternative_eligibility_month(self.month_search_facts(), history, PACK, "2026-10-13")
                self.assertIsNone(result["first_eligible_month"])
                self.assertTrue(result["data_gaps"])

    def test_month_search_binds_cessation_to_candidate_month(self):
        value = self.month_search_facts(cessation_evidence={"verified": True, "cessation_date": "2026-09-15", "as_of_date": "2026-10-13", "source_refs": ["employer-separation-1"]})
        result = search_first_post_1996_alternative_eligibility_month(value, monthly_history(), PACK, "2026-10-13")
        self.assertEqual(result["first_eligible_month"], "2026-09")
        value["cessation_evidence"]["cessation_date"] = "2026-10-01"
        result = search_first_post_1996_alternative_eligibility_month(value, monthly_history(), PACK, "2026-10-13")
        self.assertIsNone(result["first_eligible_month"])
        self.assertIn("eligibility_not_found_in_observed_history", {item["code"] for item in result["data_gaps"]})

    def test_month_search_uses_2027_and_2028_pack_age_boundaries(self):
        for year, dob, last_month, as_of, expected in ((2027, "1956-01-15", "2027-02", "2027-02-28", "2027-02"), (2028, "1957-01-15", "2028-04", "2028-04-30", "2028-04")):
            with self.subTest(year=year), tempfile.TemporaryDirectory() as directory:
                pack = json.loads(PACK.read_text(encoding="utf-8"))
                review_date = f"{year}-01-01" if year == 2027 else f"{year}-03-01"
                from datetime import date as Date, timedelta
                due_date = (Date.fromisoformat(review_date) + timedelta(days=90)).isoformat()
                for source in pack["source_refs"]:
                    source["retrieved_on"] = source["reviewed_on"] = review_date
                    source["next_review_due"] = due_date
                pack_path = Path(directory) / "synthetic-pack.json"
                pack_path.write_text(json.dumps(pack), encoding="utf-8")
                history = monthly_history(last_month=last_month, eligible_month="2026-01")
                value = self.month_search_facts(date_of_birth=dob, scope_evidence={"verified": True, "as_of_date": as_of, "coverage_from": "2026-01-01", "coverage_to": as_of, "source_refs": ["employment-record-1"]}, cessation_evidence={"verified": True, "cessation_date": "2026-01-01", "as_of_date": as_of, "source_refs": ["employer-separation-1"]}, contribution_evidence={"verified": True, "as_of_date": as_of, "period_end": as_of, "source_refs": ["contribution-statement-1"], "first_contribution_date": "2000-01-01"})
                result = search_first_post_1996_alternative_eligibility_month(value, history, pack_path, as_of)
                self.assertEqual(result["first_eligible_month"], expected)

    def test_alternative_age_boundaries_bind_to_2027_and_2028_pack_values(self):
        evidence = {"as_of_date": "2027-01-08", "period_end": "2027-01-08", "verified": True, "source_refs": ["contribution-statement-1"], "first_contribution_date": "2000-01-01", "qualifying_contribution_years": "4", "effective_contribution_years_excluding_figurative": "5"}
        self.assertEqual(self.assess(candidate_date="2027-01-08", date_of_birth="1955-12-09", contribution_cohort="on_or_after_1996", contribution_evidence=evidence)["result"], "not_yet_eligible")
        evidence["as_of_date"] = evidence["period_end"] = "2027-01-09"
        self.assertEqual(self.assess(candidate_date="2027-01-09", date_of_birth="1955-12-09", contribution_cohort="on_or_after_1996", contribution_evidence=evidence)["result"], "eligible")
        evidence["as_of_date"] = evidence["period_end"] = "2028-01-06"
        self.assertEqual(self.assess(candidate_date="2028-01-06", date_of_birth="1956-10-07", contribution_cohort="on_or_after_1996", contribution_evidence=evidence)["result"], "not_yet_eligible")
        evidence["as_of_date"] = evidence["period_end"] = "2028-01-07"
        self.assertEqual(self.assess(candidate_date="2028-01-07", date_of_birth="1956-10-07", contribution_cohort="on_or_after_1996", contribution_evidence=evidence)["result"], "eligible")
    def test_2029_and_missing_evidence_are_gaps(self):
        self.gap(self.assess(candidate_date="2029-10-10"), "rule_pack_period_unsupported")
        self.gap(self.assess(contribution_cohort="unknown"), "contribution_cohort_unknown")
        self.gap(self.assess(management_confirmed=False), "management_unsupported_or_unconfirmed")
        self.gap(self.assess(contribution_evidence=None), "contribution_evidence_missing_or_undated")
        self.gap(self.assess(cessation_confirmed=False), "employee_cessation_evidence_missing")
        self.gap(self.assess(cessation_required=False), "employee_cessation_evidence_missing")
        self.gap(self.assess(cessation_evidence={"verified": True, "cessation_date": "2026-10-10"}), "employee_cessation_evidence_missing")
    def test_pure_contributory_threshold_equal_below_and_alternative(self):
        pension_evidence = {"as_of_date": "2026-10-10", "valid_for_year": 2026, "verified": True, "source_refs": ["amount-record-1"]}
        allowance_evidence = {"as_of_date": "2026-10-10", "valid_for_year": 2026, "verified": True, "source_refs": ["allowance-record-1"]}
        base = {"contribution_cohort": "on_or_after_1996", "documented_monthly_pension_amount": "546.24", "documented_monthly_social_allowance": "546.24", "monthly_pension_amount_evidence": pension_evidence, "monthly_social_allowance_evidence": allowance_evidence}
        self.assertEqual(self.assess(**base)["result"], "eligible")
        self.assertEqual(self.assess(**{**base, "documented_monthly_pension_amount": "546.23"})["result"], "not_yet_eligible")
        evidence = {"as_of_date": "2026-10-10", "period_end": "2026-10-10", "verified": True, "source_refs": ["contribution-statement-1"], "first_contribution_date": "2000-01-01", "qualifying_contribution_years": "5", "effective_contribution_years_excluding_figurative": "5"}
        self.assertEqual(self.assess(candidate_date="2026-10-10", date_of_birth="1955-10-10", contribution_cohort="on_or_after_1996", contribution_evidence=evidence)["result"], "eligible")
        evidence["effective_contribution_years_excluding_figurative"] = "4.99"
        self.assertEqual(self.assess(candidate_date="2026-10-10", date_of_birth="1955-10-10", contribution_cohort="on_or_after_1996", contribution_evidence=evidence)["result"], "not_yet_eligible")
    def test_threshold_requires_separate_amount_and_allowance_provenance(self):
        evidence = {"as_of_date": "2026-10-10", "valid_for_year": 2026, "verified": True, "source_refs": ["amount-record-1"]}
        self.gap(self.assess(contribution_cohort="on_or_after_1996", documented_monthly_pension_amount="600", documented_monthly_social_allowance="600", monthly_pension_amount_evidence=evidence), "monthly_amount_evidence_missing")
        self.gap(self.assess(contribution_cohort="on_or_after_1996", documented_monthly_pension_amount="600", documented_monthly_social_allowance="600", monthly_social_allowance_evidence=evidence), "monthly_amount_evidence_missing")
        self.gap(self.assess(contribution_cohort="on_or_after_1996", documented_monthly_pension_amount="546.24", documented_monthly_social_allowance="546.24", monthly_pension_amount_evidence=evidence, monthly_social_allowance_evidence=evidence), "monthly_amount_evidence_missing")
    def test_threshold_is_source_bound_by_year(self):
        evidence = {"as_of_date": "2027-01-10", "valid_for_year": 2027, "verified": True, "source_refs": ["amount-record-1"]}
        allowance = {"as_of_date": "2027-01-10", "valid_for_year": 2027, "verified": True, "source_refs": ["allowance-record-1"]}
        result = self.assess(candidate_date="2027-01-10", date_of_birth="1959-12-10", contribution_cohort="on_or_after_1996", documented_monthly_pension_amount="600", documented_monthly_social_allowance="600", monthly_pension_amount_evidence=evidence, monthly_social_allowance_evidence=allowance)
        self.assertIsNone(result["result"])
        self.assertIn("monthly_social_allowance_threshold_not_source_bound", {item["code"] for item in result["data_gaps"]})
        evidence["as_of_date"] = allowance["as_of_date"] = "2028-01-10"
        evidence["valid_for_year"] = allowance["valid_for_year"] = 2028
        result = self.assess(candidate_date="2028-01-10", date_of_birth="1960-10-07", contribution_cohort="on_or_after_1996", documented_monthly_pension_amount="600", documented_monthly_social_allowance="600", monthly_pension_amount_evidence=evidence, monthly_social_allowance_evidence=allowance)
        self.assertIn("monthly_social_allowance_threshold_not_source_bound", {item["code"] for item in result["data_gaps"]})
    def test_excluded_profiles_and_no_timeline_fields(self):
        for update, code in (({"multiple_managements": True}, "multiple_managements_unsupported"), ({"foreign_or_eu_aggregation": True}, "foreign_or_eu_aggregation_unsupported"), ({"special_or_excluded_profile": True}, "special_or_excluded_profile_unsupported"), ({"multiple_managements": None}, "multiple_managements_unsupported"), ({"date_of_birth": "1960-02-29"}, "age_day_semantics_unsupported")):
            self.gap(self.assess(**update), code)
        result = self.assess()
        self.assertTrue({"official_recognition_date", "economic_effective_date", "first_cash_payment_date", "pension_stream", "work_exit_feasibility"}.isdisjoint(result))
    def test_alternative_path_survives_below_or_missing_twenty_year_amount_threshold(self):
        evidence = {"as_of_date": "2026-10-10", "period_end": "2026-10-10", "verified": True, "source_refs": ["contribution-statement-1"], "first_contribution_date": "2000-01-01", "qualifying_contribution_years": "20", "effective_contribution_years_excluding_figurative": "5"}
        common = {"candidate_date": "2026-10-10", "date_of_birth": "1955-10-10", "contribution_cohort": "on_or_after_1996", "contribution_evidence": evidence}
        self.assertEqual(self.assess(**common, documented_monthly_pension_amount="599", documented_monthly_social_allowance="600", monthly_pension_amount_evidence={"as_of_date": "2026-10-10", "valid_for_year": 2026, "verified": True, "source_refs": ["amount-record-1"]}, monthly_social_allowance_evidence={"as_of_date": "2026-10-10", "valid_for_year": 2026, "verified": True, "source_refs": ["allowance-record-1"]})["result"], "eligible")
        self.assertEqual(self.assess(**common)["result"], "eligible")
        common["contribution_evidence"] = {**evidence, "effective_contribution_years_excluding_figurative": None}
        self.gap(self.assess(**common, documented_monthly_pension_amount="599", documented_monthly_social_allowance="600", monthly_pension_amount_evidence={"as_of_date": "2026-10-10", "valid_for_year": 2026, "verified": True, "source_refs": ["amount-record-1"]}, monthly_social_allowance_evidence={"as_of_date": "2026-10-10", "valid_for_year": 2026, "verified": True, "source_refs": ["allowance-record-1"]}), "effective_contribution_total_missing")
    def test_candidate_date_and_year_bind_evidence(self):
        self.gap(self.assess(contribution_evidence={"as_of_date": "2026-10-11", "period_end": "2026-10-11"}), "contribution_evidence_not_applicable_to_candidate")
        self.gap(self.assess(contribution_evidence={"as_of_date": "2026-10-10", "period_end": "2026-10-11"}), "contribution_evidence_not_applicable_to_candidate")
        self.gap(self.assess(contribution_cohort="on_or_after_1996", documented_monthly_pension_amount="600", documented_monthly_social_allowance="600", monthly_pension_amount_evidence={"as_of_date": "2026-10-10", "valid_for_year": 2025, "verified": True, "source_refs": ["amount-record-1"]}, monthly_social_allowance_evidence={"as_of_date": "2026-10-10", "valid_for_year": 2026, "verified": True, "source_refs": ["allowance-record-1"]}), "monthly_amount_evidence_missing")
        self.gap(self.assess(contribution_cohort="on_or_after_1996", documented_monthly_pension_amount="600", documented_monthly_social_allowance="600", monthly_pension_amount_evidence={"as_of_date": "2026-10-11", "valid_for_year": 2026, "verified": True, "source_refs": ["amount-record-1"]}, monthly_social_allowance_evidence={"as_of_date": "2026-10-11", "valid_for_year": 2026, "verified": True, "source_refs": ["allowance-record-1"]}), "monthly_amount_evidence_missing")
        self.gap(self.assess(scope_evidence=None), "scope_evidence_missing_or_unverified")
        self.gap(self.assess(cessation_evidence={"verified": True, "cessation_date": "2026-10-11", "source_refs": ["employer-separation-1"]}), "employee_cessation_after_candidate")
    def test_consumer_reads_contribution_thresholds_from_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            pack_path = Path(directory) / "pack.json"
            pack = json.loads(PACK.read_text(encoding="utf-8"))
            pack["paths"]["pre_1996"]["minimum_qualifying_contribution_years"] = 21
            pack_path.write_text(json.dumps(pack), encoding="utf-8")
            result = assess_italian_old_age_eligibility(facts(), pack_path, "2026-10-13")
        self.assertEqual(result["result"], "not_yet_eligible")
        with tempfile.TemporaryDirectory() as directory:
            pack_path = Path(directory) / "pack.json"
            pack = json.loads(PACK.read_text(encoding="utf-8"))
            pack["supported_scope"]["managements"] = ["FPLD"]
            pack_path.write_text(json.dumps(pack), encoding="utf-8")
            result = assess_italian_old_age_eligibility(facts(management="AGO"), pack_path, "2026-10-13")
        self.assertEqual(result["status"], "not_assessed")
        with tempfile.TemporaryDirectory() as directory:
            pack_path = Path(directory) / "pack.json"
            pack = json.loads(PACK.read_text(encoding="utf-8"))
            pack["paths"]["post_1996_alternative"]["minimum_effective_contribution_years"] = 6
            pack_path.write_text(json.dumps(pack), encoding="utf-8")
            evidence = {"as_of_date": "2026-10-10", "period_end": "2026-10-10", "verified": True, "source_refs": ["contribution-statement-1"], "first_contribution_date": "2000-01-01", "qualifying_contribution_years": "5", "effective_contribution_years_excluding_figurative": "5"}
            alternative_facts = facts(candidate_date="2026-10-10", date_of_birth="1955-10-10", contribution_cohort="on_or_after_1996", contribution_evidence=evidence)
            result = assess_italian_old_age_eligibility(alternative_facts, pack_path, "2026-10-13")
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
            lambda pack: next(source for source in pack["source_refs"] if source["source_id"] == "inps.requisiti-2027-2028")["provision_periods"][0].update(pack_coverage_to="2027-12-31"),
            lambda pack: pack["supported_scope"].update(managements=["OTHER"]),
            lambda pack: next(source for source in pack["source_refs"] if source["source_id"] == "inps.pensione-vecchiaia")["provision_periods"][1].update(pack_coverage_from="2026-12-31", pack_coverage_to="2028-01-01"),
            lambda pack: next(source for source in pack["source_refs"] if source["source_id"] == "inps.requisiti-2027-2028")["provision_periods"][0].update(provision_id="contribution_threshold"),
            lambda pack: pack["source_refs"].remove(next(source for source in pack["source_refs"] if source["source_id"] == "gazzetta.decreto-06-12-2011.11a16083")),
            lambda pack: pack["source_refs"].append(dict(pack["source_refs"][0])),
            lambda pack: (lambda item: item["provision_periods"].append(dict(item["provision_periods"][0])))(next(source for source in pack["source_refs"] if source["source_id"] == "gazzetta.decreto-06-12-2011.11a16083")),
            lambda pack: next(source for source in pack["source_refs"] if source["source_id"] == "gazzetta.decreto-19-12-2025.25a07010").update(legal_role="administrative_guidance"),
            lambda pack: next(source for source in pack["source_refs"] if source["source_id"] == "inps.pensione-vecchiaia").pop("legal_role"),
            lambda pack: next(source for source in pack["source_refs"] if source["source_id"] == "inps.pensione-vecchiaia").update(legal_role="primary_legislation"),
            lambda pack: next(source for source in pack["source_refs"] if source["source_id"] == "gazzetta.decreto-06-12-2011.11a16083")["provision_periods"][0].update(legal_effective_from="2013-13-01"),
            lambda pack: next(source for source in pack["source_refs"] if source["source_id"] == "gazzetta.decreto-06-12-2011.11a16083")["provision_periods"][0].update(legal_effective_from="2019-01-01", legal_effective_to="2018-12-31"),
            lambda pack: next(source for source in pack["source_refs"] if source["source_id"] == "gazzetta.decreto-06-12-2011.11a16083")["provision_periods"][0].update(adjustment_months=4),
            lambda pack: pack["requirements_by_year"]["2028"]["contributory_alternative_age"].update(months=2),
            lambda pack: next(source for source in pack["source_refs"] if source["source_id"] == "inps.requisiti-2027-2028")["requirements_by_year"]["2028"]["contributory_alternative_age"].update(months=2),
            lambda pack: pack["threshold_bindings"]["post_1996_ordinary"]["by_year"]["2026"].update(currency="ITL"),
            lambda pack: pack["threshold_bindings"]["post_1996_ordinary"]["by_year"]["2026"].update(payments_per_year=12),
            lambda pack: pack["threshold_bindings"]["post_1996_ordinary"]["by_year"]["2026"].update(monthly_amount="546.25"),
            lambda pack: pack["source_refs"].remove(next(source for source in pack["source_refs"] if source["source_id"] == "inps.assegno-sociale-2026")),
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
                        assess_italian_old_age_eligibility(facts(), path, "2026-10-13")
