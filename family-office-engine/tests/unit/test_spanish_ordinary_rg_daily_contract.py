import copy
import json
import unittest
from pathlib import Path
from unittest import mock

from family_office_engine.services.spanish_pension_rules import (
    SpanishPensionRulesError,
    load_rule_pack,
    validate_ordinary_rg_daily_contract,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RULE_PACK_PATH = REPOSITORY_ROOT / "family-office-rules" / "spain" / "statutory-retirement-general.json"
BRANCHES = ("3.2.a", "3.2.b", "3.2.c", "3.2.d", "3.2.e")


class SpanishOrdinaryRgDailyContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rule_pack = json.loads(RULE_PACK_PATH.read_text(encoding="utf-8"))

    def valid_evidence(self, candidate="2026-10-20", filing="2026-10-20"):
        return {
            "application_kind": "actual",
            "candidate_date": candidate,
            "authoritative_filing_date": filing,
            "filing_country": "ES",
            "filing_scope": "domestic",
            "international_filing": False,
            "filing_scope_evidence_ref": "synthetic:domestic-filing-scope-1",
            "filing_evidence_ref": "synthetic:filing-record-1",
            "filing_conflicting": False,
            "ordinary_rg_scope": {
                "assertion": "ordinary_rg",
                "evidence_ref": "synthetic:regime-proof-1",
            },
            "article_3_2_exclusions": {
                branch: {
                    "provision": branch,
                    "finding": "not_applicable",
                    "conflicting": False,
                    "evidence_ref": f"synthetic:exclude-{branch}",
                }
                for branch in BRANCHES
            },
            "article_3_3_exclusion": {
                "provision": "Articulo 3.3",
                "finding": "not_applicable",
                "conflicting": False,
                "evidence_ref": "synthetic:exclude-3.3",
            },
            "eu_periods_status": "none_proven",
            "eu_periods_evidence_ref": "synthetic:no-eu-periods-1",
        }

    def validate(self, evidence, as_of="2026-11-14", pack=None):
        return validate_ordinary_rg_daily_contract(pack or self.rule_pack, evidence, as_of)

    def test_actual_domestic_filing_and_same_day_candidate_are_contract_valid(self):
        result = self.validate(self.valid_evidence())
        self.assertEqual(result["contract_validation_status"], "contract_valid")
        self.assertEqual(result["candidate_date"], result["authoritative_filing_date"])

    def test_inclusive_three_month_calendar_edges_and_one_day_outside(self):
        self.assertEqual(self.validate(self.valid_evidence("2026-07-20", "2026-10-20"))["contract_validation_status"], "contract_valid")
        future_edge = self.validate(self.valid_evidence("2027-01-20", "2026-10-20"))
        self.assertIn("candidate_outside_currentness", self.gap_codes(future_edge))
        self.assertNotIn("candidate_outside_inclusive_three_month_window", self.gap_codes(future_edge))
        for candidate in ("2026-07-19", "2027-01-21"):
            with self.subTest(candidate=candidate):
                result = self.validate(self.valid_evidence(candidate, "2026-10-20"))
                self.assertEqual(result["contract_validation_status"], "unknown")
                self.assertIn("candidate_outside_inclusive_three_month_window", self.gap_codes(result))

    def test_exact_filing_day_is_valid(self):
        self.assertEqual(self.validate(self.valid_evidence("2026-10-20", "2026-10-20"))["contract_validation_status"], "contract_valid")

    def test_authoritative_filing_after_as_of_fails_closed(self):
        result = self.validate(self.valid_evidence("2026-11-01", "2027-01-01"), as_of="2026-11-14")
        self.assertEqual(result["contract_validation_status"], "unknown")
        self.assertIn("authoritative_filing_date_after_as_of", self.gap_codes(result))

    def test_authoritative_filing_conflict_flag_must_be_explicit_and_false(self):
        for state in ("missing", True, "yes"):
            with self.subTest(state=state):
                evidence = self.valid_evidence()
                if state == "missing":
                    evidence.pop("filing_conflicting")
                else:
                    evidence["filing_conflicting"] = state
                result = self.validate(evidence)
                self.assertEqual(result["contract_validation_status"], "unknown")
                self.assertTrue(any(code.startswith("authoritative_filing_") for code in self.gap_codes(result)))

    def test_malformed_article_exclusion_conflict_flag_fails_closed(self):
        evidence = self.valid_evidence()
        evidence["article_3_2_exclusions"]["3.2.a"]["conflicting"] = "yes"
        result = self.validate(evidence)
        self.assertEqual(result["contract_validation_status"], "unknown")
        self.assertIn("article_3_2_a_evidence_conflicting", self.gap_codes(result))

    def test_exact_source_manifest_rejects_mutated_or_extra_bindings(self):
        def wrong_locator(pack):
            sources = pack["ordinary_rg_daily_contract"]["source_refs"]
            rd = next(item for item in sources if item["source_id"] == "boe.rd-453-2022.official-publication")
            rd["url"] = "https://www.boe.es/eli/es/rd/2022/06/14/453"

        def extra_source(pack):
            sources = pack["ordinary_rg_daily_contract"]["source_refs"]
            extra = copy.deepcopy(sources[0])
            extra["source_id"] = "boe.extra.unbound-source"
            sources.append(extra)

        def coordinated_role_mutation(pack):
            contract = pack["ordinary_rg_daily_contract"]
            rd = next(item for item in contract["source_refs"] if item["source_id"] == "boe.rd-453-2022.official-publication")
            rd["source_role"] = "official_consolidated_consultation"
            contract["required_source_roles_by_id"][rd["source_id"]] = "official_consolidated_consultation"

        def coordinated_provision_removal(pack):
            contract = pack["ordinary_rg_daily_contract"]
            source_id = "boe.rd-453-2022.official-publication"
            rd = next(item for item in contract["source_refs"] if item["source_id"] == source_id)
            rd["provisions"].remove("Articulo 3.1")
            contract["required_source_provisions"][source_id].remove("Articulo 3.1")

        def coordinated_rdl_31_locator_mutation(pack):
            contract = pack["ordinary_rg_daily_contract"]
            source_id = "boe.rdl-31-2026.official-publication"
            rdl_31 = next(item for item in contract["source_refs"] if item["source_id"] == source_id)
            rdl_31["provisions"][:] = ["Articulo 144.4", "Disposicion final cuarta"]
            contract["required_source_provisions"][source_id] = ["Articulo 144.4", "Disposicion final cuarta"]

        for label, mutate in (("wrong locator", wrong_locator), ("extra source", extra_source), ("coordinated role", coordinated_role_mutation), ("coordinated provision", coordinated_provision_removal), ("coordinated RDL 31 locator", coordinated_rdl_31_locator_mutation)):
            with self.subTest(binding=label):
                broken_pack = copy.deepcopy(self.rule_pack)
                mutate(broken_pack)
                result = self.validate(self.valid_evidence(), pack=broken_pack)
                self.assertEqual(result["contract_validation_status"], "unknown")
                self.assertIn("contract_definition_invalid", self.gap_codes(result))

    def test_month_end_clips_to_last_day_when_equivalent_day_is_missing(self):
        cases = (
            ("2026-05-31", "2026-08-31", "2026-11-30"),
            ("2026-02-28", "2026-05-31", "2026-08-31"),
        )
        for lower, filing, upper in cases:
            for candidate in (lower, upper):
                with self.subTest(filing=filing, candidate=candidate):
                    result = self.validate(self.valid_evidence(candidate, filing))
                    self.assertNotIn("candidate_outside_inclusive_three_month_window", self.gap_codes(result))

    def test_leap_day_date_to_date_edges(self):
        for candidate in ("2023-11-30", "2024-05-29"):
            with self.subTest(candidate=candidate):
                result = self.validate(self.valid_evidence(candidate, "2024-02-29"))
                self.assertNotIn("candidate_outside_inclusive_three_month_window", self.gap_codes(result))
        outside = self.validate(self.valid_evidence("2024-05-30", "2024-02-29"))
        self.assertIn("candidate_outside_inclusive_three_month_window", self.gap_codes(outside))

    def test_candidate_before_2022_06_16_fails_closed(self):
        result = self.validate(self.valid_evidence("2022-06-15", "2022-06-15"))
        self.assertEqual(result["contract_validation_status"], "unknown")
        self.assertIn("candidate_before_contract_start", self.gap_codes(result))

    def test_international_filing_is_outside_contract(self):
        evidence = self.valid_evidence()
        evidence["filing_country"] = "FR"
        result = self.validate(evidence)
        self.assertEqual(result["contract_validation_status"], "unknown")
        self.assertIn("domestic_filing_required", self.gap_codes(result))

    def test_domestic_country_requires_separate_international_route_exclusion(self):
        evidence = self.valid_evidence()
        evidence.pop("international_filing")
        result = self.validate(evidence)
        self.assertIn("international_filing_status_unknown", self.gap_codes(result))

    def test_branch_specific_conflict_flag_fails_closed(self):
        evidence = self.valid_evidence()
        evidence["article_3_2_exclusions"]["3.2.a"]["conflicting"] = True
        result = self.validate(evidence)
        self.assertIn("article_3_2_a_evidence_conflicting", self.gap_codes(result))

    def test_each_article_3_2_exclusion_requires_its_own_evidence(self):
        for branch in BRANCHES:
            evidence = self.valid_evidence()
            evidence["article_3_2_exclusions"].pop(branch)
            result = self.validate(evidence)
            with self.subTest(branch=branch):
                self.assertEqual(result["contract_validation_status"], "unknown")
                self.assertIn(f"article_{branch.replace('.', '_')}_evidence_unknown", self.gap_codes(result))

    def test_each_applicable_or_conflicting_article_3_2_exclusion_fails_closed(self):
        for branch, finding in ((branch, finding) for branch in BRANCHES for finding in ("applicable", "conflicting")):
            evidence = self.valid_evidence()
            evidence["article_3_2_exclusions"][branch]["finding"] = finding
            result = self.validate(evidence)
            with self.subTest(branch=branch, finding=finding):
                self.assertEqual(result["contract_validation_status"], "unknown")
                self.assertIn(f"article_{branch.replace('.', '_')}_evidence_unknown", self.gap_codes(result))

    def test_article_3_3_requires_separate_non_conflicting_not_applicable_evidence(self):
        for label, mutate, code in (
            ("missing", lambda item: item.pop("article_3_3_exclusion"), "article_3_3_evidence_unknown"),
            ("applicable", lambda item: item["article_3_3_exclusion"].update(finding="applicable"), "article_3_3_evidence_unknown"),
            ("conflicting", lambda item: item["article_3_3_exclusion"].update(conflicting=True), "article_3_3_evidence_conflicting"),
        ):
            evidence = self.valid_evidence()
            mutate(evidence)
            result = self.validate(evidence)
            with self.subTest(case=label):
                self.assertEqual(result["contract_validation_status"], "unknown")
                self.assertIn(code, self.gap_codes(result))

    def test_article_3_3_valid_non_applicable_control_is_contract_valid(self):
        result = self.validate(self.valid_evidence())
        self.assertEqual(result["contract_validation_status"], "contract_valid")

    def test_clause_evidence_must_bind_the_specific_article_branch(self):
        evidence = self.valid_evidence()
        evidence["article_3_2_exclusions"]["3.2.a"]["provision"] = "3.2.b"
        result = self.validate(evidence)
        self.assertIn("article_3_2_a_evidence_conflicting", self.gap_codes(result))

    def test_generic_no_special_case_boolean_does_not_substitute_for_exclusions(self):
        evidence = self.valid_evidence()
        evidence.pop("article_3_2_exclusions")
        evidence["no_special_case"] = True
        result = self.validate(evidence)
        self.assertEqual(result["contract_validation_status"], "unknown")
        codes = self.gap_codes(result)
        self.assertTrue(all(f"article_{branch.replace('.', '_')}_evidence_unknown" in codes for branch in BRANCHES))

    def test_missing_or_conflicting_filing_and_scope_evidence_are_unknown(self):
        for field in ("authoritative_filing_date", "filing_evidence_ref"):
            evidence = self.valid_evidence()
            evidence.pop(field)
            result = self.validate(evidence)
            with self.subTest(field=field):
                self.assertEqual(result["contract_validation_status"], "unknown")
        evidence = self.valid_evidence()
        evidence["ordinary_rg_scope"]["assertion"] = "conflicting"
        self.assertEqual(self.validate(evidence)["contract_validation_status"], "unknown")

    def test_currentness_is_half_open_and_review_cutoff_fails_closed(self):
        for candidate, as_of in (("2026-06-15", "2026-06-16"), ("2026-11-15", "2026-11-14"), ("2026-11-14", "2026-11-15")):
            result = self.validate(self.valid_evidence(candidate, candidate), as_of)
            with self.subTest(candidate=candidate, as_of=as_of):
                self.assertEqual(result["contract_validation_status"], "unknown")
                self.assertTrue(any(code in self.gap_codes(result) for code in ("contract_currentness_gap", "candidate_outside_currentness")))

    def test_as_of_must_match_the_reviewed_source_evidence_cutoff(self):
        before = self.validate(self.valid_evidence(), as_of="2026-11-13")
        self.assertEqual(before["contract_validation_status"], "unknown")
        self.assertIn("contract_source_evidence_cutoff_gap", self.gap_codes(before))
        self.assertEqual(self.validate(self.valid_evidence(), as_of="2026-11-14")["contract_validation_status"], "contract_valid")
        after = self.validate(self.valid_evidence(), as_of="2026-11-15")
        self.assertEqual(after["contract_validation_status"], "unknown")
        self.assertIn("contract_currentness_gap", self.gap_codes(after))

    def test_unknown_205_1_b_anchor_and_status_obligation_are_not_assessed(self):
        result = self.validate(self.valid_evidence())
        self.assertEqual(result["lgss_205_1_b_anchor"], "not_assessed")
        self.assertEqual(result["legal_status"], "not_assessed")
        self.assertEqual(result["contribution_obligation"], "not_assessed")
        self.assertIn("lgss_205_1_b_anchor_not_assessed", self.gap_codes(result))

    def test_daily_rd_31_2026_and_rd_35_2026_transition_dates_do_not_infer_status(self):
        transition_dates = (
            "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23",
            "2026-10-31", "2026-11-01", "2026-11-11", "2026-11-12",
        )
        for candidate in transition_dates:
            result = self.validate(self.valid_evidence(candidate, candidate))
            with self.subTest(candidate=candidate):
                self.assertEqual(result["legal_status"], "not_assessed")
                self.assertEqual(result["contribution_obligation"], "not_assessed")
                self.assertEqual(result["contract_validation_status"], "contract_valid")
        for candidate in ("2026-11-30", "2026-12-01", "2026-12-31", "2027-01-01"):
            result = self.validate(self.valid_evidence(candidate, candidate))
            with self.subTest(candidate=candidate):
                self.assertEqual(result["contract_validation_status"], "unknown")
                self.assertIn("candidate_outside_currentness", self.gap_codes(result))
                self.assertEqual(result["legal_status"], "not_assessed")

    def test_eligibility_hecho_causante_and_article_4_outcomes_stay_unassessed(self):
        result = self.validate(self.valid_evidence())
        self.assertEqual(result["eligibility"], "not_assessed")
        self.assertEqual(result["hecho_causante"], {"status": "not_assessed", "date": None})
        self.assertEqual(result["recognition"], "not_assessed")
        self.assertEqual(result["economic_effect"], "not_assessed")
        self.assertEqual(result["payment"], "not_assessed")
        self.assertTrue(result["human_review_required"])

    def test_eu_periods_and_aggregation_are_out_of_scope(self):
        evidence = self.valid_evidence()
        evidence["eu_periods"] = [{"synthetic": True}]
        result = self.validate(evidence)
        self.assertEqual(result["contract_validation_status"], "unknown")
        self.assertIn("eu_coordination_out_of_scope", self.gap_codes(result))

    def test_unknown_eu_period_status_fails_closed(self):
        evidence = self.valid_evidence()
        evidence.pop("eu_periods_status")
        evidence.pop("eu_periods_evidence_ref")
        result = self.validate(evidence)
        self.assertIn("eu_periods_unknown", self.gap_codes(result))

    def test_source_role_mismatch_fails_closed(self):
        broken_pack = copy.deepcopy(self.rule_pack)
        sources = broken_pack["ordinary_rg_daily_contract"]["source_refs"]
        rd = next(item for item in sources if item["source_id"] == "boe.rd-453-2022.official-publication")
        rd["source_role"] = "official_consolidated_consultation"
        result = self.validate(self.valid_evidence(), pack=broken_pack)
        self.assertEqual(result["contract_validation_status"], "unknown")
        self.assertIn("contract_definition_invalid", self.gap_codes(result))

    def test_missing_daily_contract_returns_unknown_without_throwing(self):
        broken_pack = copy.deepcopy(self.rule_pack)
        broken_pack.pop("ordinary_rg_daily_contract")
        result = self.validate(self.valid_evidence(), pack=broken_pack)
        self.assertEqual(result["contract_validation_status"], "unknown")
        self.assertIn("contract_version_unsupported", self.gap_codes(result))
        self.assertIn("contract_currentness_unknown", self.gap_codes(result))

    def test_contract_source_authority_mismatch_fails_closed(self):
        broken_pack = copy.deepcopy(self.rule_pack)
        sources = broken_pack["ordinary_rg_daily_contract"]["source_refs"]
        rd = next(item for item in sources if item["source_id"] == "boe.rd-453-2022.official-publication")
        rd["authority"] = "Private publisher"
        result = self.validate(self.valid_evidence(), pack=broken_pack)
        self.assertEqual(result["contract_validation_status"], "unknown")
        self.assertIn("contract_definition_invalid", self.gap_codes(result))

    def test_contract_source_jurisdiction_mismatch_fails_closed(self):
        broken_pack = copy.deepcopy(self.rule_pack)
        sources = broken_pack["ordinary_rg_daily_contract"]["source_refs"]
        rd = next(item for item in sources if item["source_id"] == "boe.rd-453-2022.official-publication")
        rd["jurisdiction"] = "IT"
        result = self.validate(self.valid_evidence(), pack=broken_pack)
        self.assertEqual(result["contract_validation_status"], "unknown")
        self.assertIn("contract_definition_invalid", self.gap_codes(result))

    def test_duplicate_contract_source_id_fails_closed(self):
        broken_pack = copy.deepcopy(self.rule_pack)
        sources = broken_pack["ordinary_rg_daily_contract"]["source_refs"]
        sources.append(copy.deepcopy(sources[0]))
        result = self.validate(self.valid_evidence(), pack=broken_pack)
        self.assertEqual(result["contract_validation_status"], "unknown")
        self.assertIn("contract_definition_invalid", self.gap_codes(result))

    def test_rule_pack_loader_requires_half_open_source_bound_contract(self):
        for mutate, message in (
            (lambda pack: pack.pop("ordinary_rg_daily_contract"), "ordinary_rg_daily_contract"),
            (lambda pack: pack["ordinary_rg_daily_contract"].update(validity_semantics="inclusive"), "half-open"),
            (lambda pack: pack["ordinary_rg_daily_contract"]["required_source_provisions"].pop("boe.rd-453-2022.official-publication"), "source provisions"),
            (lambda pack: pack["ordinary_rg_daily_contract"]["application"].update(conflict_flag_required=False), "authoritative filing conflict flag"),
            (lambda pack: pack["ordinary_rg_daily_contract"].update(article_3_2_exclusion_conflict_flag_required=False), "explicit conflict flag"),
            (lambda pack: pack["ordinary_rg_daily_contract"].pop("source_evidence_as_of"), "source evidence cutoff"),
            (lambda pack: pack["ordinary_rg_daily_contract"].pop("article_3_3_exclusion"), "art. 3.3"),
        ):
            broken = copy.deepcopy(self.rule_pack)
            mutate(broken)
            with self.subTest(message=message), mock.patch.object(Path, "read_text", return_value=json.dumps(broken)), self.assertRaisesRegex(SpanishPensionRulesError, message):
                load_rule_pack(RULE_PACK_PATH)

    @staticmethod
    def gap_codes(result):
        return {gap["code"] for gap in result["data_gaps"]}


if __name__ == "__main__":
    unittest.main()
