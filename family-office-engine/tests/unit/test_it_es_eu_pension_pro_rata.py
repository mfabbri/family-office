import json
import hashlib
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from family_office_engine.services.it_es_eu_pension_pro_rata import (
    ItEsEuPensionProRataError,
    build_it_es_eu_pension_pro_rata,
    load_rule_pack,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "cross-border" / "eu-pension-coordination-it-es.json"


class ItEsEuPensionProRataTest(unittest.TestCase):
    def test_calculates_spanish_pro_rata_when_entitled_by_totalization(self):
        result = self._build(
            _input(
                [
                    _period("IT", "2006-01-01", "2020-12-31"),
                    _period("ES", "2021-01-01", "2025-12-31"),
                ]
            )
        )

        self.assertEqual(result["schema_version"], "it-es-eu-pension-pro-rata/v1")
        self.assertEqual(result["status"], "blocked_missing_inputs")
        self.assertEqual(result["spanish_entitlement"]["status"], "eligible_by_totalization")
        self.assertFalse(result["spanish_entitlement"]["autonomous"]["eligible"])
        self.assertTrue(result["spanish_entitlement"]["totalized"]["eligible"])
        self.assertEqual(result["periods"]["spain_months"], 60)
        self.assertEqual(result["periods"]["total_eu_non_overlapping_months"], 240)
        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_calculable")
        self.assertIsNone(result["spanish_pro_rata_pension"]["amounts"])
        self.assertIn("missing_article_57_annex_viii_part_2_catalogue", {gap["code"] for gap in result["data_gaps"]})

    def test_keeps_autonomous_spanish_entitlement_distinct(self):
        result = self._build(_input([_period("ES", "2001-01-01", "2025-12-31")]))

        self.assertEqual(result["status"], "blocked_missing_inputs")
        self.assertEqual(result["spanish_entitlement"]["status"], "eligible_autonomous")
        self.assertTrue(result["spanish_entitlement"]["autonomous"]["eligible"])
        self.assertTrue(result["spanish_entitlement"]["totalized"]["eligible"])
        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_calculable")

    def test_blocks_pro_rata_for_unclassified_it_es_overlap(self):
        result = self._build(
            _input(
                [
                    _period("IT", "2006-01-01", "2020-12-31"),
                    _period("ES", "2020-01-01", "2025-12-31"),
                ]
            )
        )

        self.assertEqual(result["periods"]["spain_months"], 72)
        self.assertEqual(result["periods"]["overlap_month_count"], 12)
        self.assertEqual(result["periods"]["total_eu_non_overlapping_months"], 240)
        self.assertEqual(result["spanish_entitlement"]["status"], "not_eligible")
        self.assertFalse(result["spanish_entitlement"]["totalized"]["eligible"])
        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_calculable")
        self.assertIsNone(result["spanish_pro_rata_pension"]["amounts"])
        self.assertIn("unclassified_it_es_period_overlap", {gap["code"] for gap in result["data_gaps"]})
        self.assertIn(
            "overlapping_periods_require_institutional_classification",
            {warning["code"] for warning in result["warnings"]},
        )

    def test_source_bound_duration_less_than_one_year_applies_article_57_without_calendar_threshold(self):
        payload = _input([_period("IT", "2006-01-01", "2025-01-31"), _period("ES", "2025-02-01", "2025-12-31")])
        payload["article_57_assessment"] = _article_57(duration=True, autonomous=False, annex=False)
        result = self._build(payload)

        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertIn("missing_article_57_annex_viii_part_2_catalogue", {gap["code"] for gap in result["data_gaps"]})
        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_calculable")
        self.assertNotIn("threshold_months", str(result))

    def test_source_bound_duration_equal_or_greater_than_one_year_does_not_apply_article_57(self):
        payload = _input([_period("IT", "2006-01-01", "2024-12-31"), _period("ES", "2025-01-01", "2025-12-31")])
        payload["article_57_assessment"] = _article_57(duration=False, autonomous=False, annex=False)
        result = self._build(payload)

        self.assertEqual(result["spanish_entitlement"]["status"], "eligible_by_totalization")
        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_calculable")
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")

        payload["article_57_assessment"] = _article_57(duration=False, autonomous=False, annex=False, legal_duration_days=366)
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")

    def test_source_bound_rational_duration_comparison_uses_cross_multiplication(self):
        payload = _input([_period("IT", "2006-01-01", "2025-01-31"), _period("ES", "2025-02-01", "2025-12-31")])
        payload["article_57_assessment"] = _article_57(
            duration=True,
            autonomous=False,
            annex=False,
            legal_duration_rational=(2, 3),
            comparator_rational=(1, 1),
        )

        result = self._build(payload)

        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")

    def test_rejects_boolean_or_negative_rationals_and_invalid_ternary_values(self):
        for rational in ((True, 1), (-1, 1), (1, False)):
            payload = _input([])
            payload["article_57_assessment"] = _article_57(True, False, False, legal_duration_rational=rational)
            result = self._build(payload)
            self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
            self.assertIn("invalid_article_57_duration_comparator_binding", {gap["code"] for gap in result["data_gaps"]})

        payload = _input([])
        payload["article_57_assessment"] = _article_57(True, False, False)
        payload["article_57_assessment"]["duration_strictly_less_than_one_year"] = 1
        with self.assertRaisesRegex(ItEsEuPensionProRataError, "true, false, or null"):
            self._build(payload)

    def test_calendar_months_do_not_substitute_for_source_bound_legal_duration(self):
        payload = _input([_period("IT", "2006-01-01", "2025-01-31"), _period("ES", "2025-02-01", "2025-12-31")])
        payload["article_57_assessment"] = _article_57(duration=False, autonomous=False, annex=False)
        result = self._build(payload)

        self.assertEqual(result["periods"]["spain_months"], 11)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_calculable")

    def test_source_bound_autonomous_right_and_annex_are_independent_predicates(self):
        payload = _input([_period("IT", "2006-01-01", "2025-01-31"), _period("ES", "2025-02-01", "2025-12-31")])
        payload["article_57_assessment"] = _article_57(duration=True, autonomous=True, annex=False)
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")

        payload["article_57_assessment"] = _article_57(duration=True, autonomous=False, annex=True)
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")

        payload["article_57_assessment"] = _article_57(duration=False, autonomous=False, annex=False)
        payload["article_57_assessment"]["annex_viii_part_2_applicability"] = {"result": False, "matched_scheme_entry": "invented-entry"}
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertIn("missing_article_57_annex_viii_part_2_catalogue", {gap["code"] for gap in result["data_gaps"]})

    def test_unknown_or_overlap_conversion_ambiguity_is_not_assessed(self):
        payload = _input([_period("IT", "2006-01-01", "2020-12-31"), _period("ES", "2020-01-01", "2025-12-31")])
        payload["article_57_assessment"] = _article_57(duration=None, autonomous=False, annex=False)
        result = self._build(payload)

        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertIn("missing_article_57_legal_duration", {gap["code"] for gap in result["data_gaps"]})

    def test_article_57_v019_rejects_legacy_contract_and_fails_closed_without_catalogue(self):
        payload = _input([])
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertIn("missing_article_57_annex_viii_part_2_catalogue", {gap["code"] for gap in result["data_gaps"]})

        payload["article_57_assessment"]["contract_schema_version"] = "v0.17"
        with self.assertRaisesRegex(ItEsEuPensionProRataError, "legacy contracts"):
            self._build(payload)

    def test_c14n_v4_rejects_later_parent_or_bound_entries(self):
        payload = _input([])
        preimage = payload["article_57_assessment"]["duration_source_segment"]["preimage"]
        preimage["parent_period_refs"].append("later-period")
        preimage["source_bounds"].append(dict(preimage["source_bounds"][0], period_ref="later-period"))
        segment_id = _segment_id(preimage)
        payload["article_57_assessment"]["duration_source_segment"]["segment_id"] = segment_id
        payload["article_57_assessment"]["legal_duration_for_article_57"]["source_segment_id"] = segment_id
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertIn("invalid_article_57_duration_source_segment", {gap["code"] for gap in result["data_gaps"]})

        payload = _input([])
        payload["article_57_assessment"]["duration_source_segment"]["preimage"]["parent_period_refs"] = [{}]
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertIn("invalid_article_57_duration_source_segment", {gap["code"] for gap in result["data_gaps"]})

    def test_manifest_scope_and_last_state_are_technical_evidence_not_payer_selection(self):
        from family_office_engine.services.it_es_eu_pension_pro_rata import _article_57_assessment

        policy = load_rule_pack(RULE_PACK)
        annex_policy = policy["pro_rata_method"]["article_57_source_bound"]["annex_viii_part_2"]
        annex_policy.update({"machine_readable_validity_catalogue_status": "available", "catalogue_entry_ids": ["synthetic-catalogue-entry"], "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1", "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01", "catalogue_valid_to": None})
        assessment = _article_57(True, False, False, all_relieved=True)
        assessment["annex_viii_part_2_applicability"] = {"result": False, "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1", "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01", "catalogue_valid_to": None, "annex_consolidation_version": "reg-988-2009-2010-05-01", "annex_validity_or_applicability_date": "2026-12-01", "scheme_match_status": "not_matched", "matched_scheme_entry": None, "annex_evidence_refs": ["synthetic-annex-evidence"]}
        assessment["last_state_attestation"] = _last_state_attestation()
        result = _article_57_assessment(assessment, policy)["result"]
        self.assertNotIn("article_57_3_status", result)
        self.assertEqual(result["national_payment_obligation_status"], "not_assessed")

        two_states = deepcopy(assessment)
        second = deepcopy(two_states["concerned_institutions"][0])
        second.update({
            "institution_ref": "synthetic-it",
            "member_state": "IT",
            "local_claim_ref": {"issuer_institution_ref": "synthetic-it", "namespace": "synthetic-it-claim", "value": "claim-2", "evidence_refs": ["synthetic-it-claim-evidence"]},
            "local_benefit_ref": {"issuer_institution_ref": "synthetic-it", "namespace": "synthetic-it-benefit", "value": "benefit-2", "evidence_refs": ["synthetic-it-benefit-evidence"]},
            "scheme_id": "synthetic-it-scheme",
            "competent_institution": "synthetic-it-institution",
            "applicable_legislation_id": "synthetic-it-law",
            "applicable_legislation_version": "synthetic-it-v1",
            "applicable_legislation_valid_from": "2025-01-01",
            "transitional_applicability": _transitional("IT", "2026-12-01"),
            "evidence_refs": ["synthetic-it-institutional-art57"],
        })
        second["article_57_1_evidence"]["applicable_legislation"] = {"id": "synthetic-it-law", "version": "synthetic-it-v1", "valid_from": "2025-01-01", "valid_to": None, "source_refs": ["synthetic-it-law-source"]}
        second["article_57_1_evidence"]["source_evidence_refs"] = ["synthetic-it-institutional-art57"]
        two_states["concerned_institutions"].append(second)
        two_states["institution_scope_evidence"]["institution_refs"] = ["synthetic-es", "synthetic-it"]
        two_states["last_state_attestation"]["candidate_institution_refs"] = ["synthetic-es", "synthetic-it"]
        ordered_result = _article_57_assessment(two_states, policy)
        self.assertNotIn("article_57_3_status", ordered_result["result"])
        self.assertTrue({"missing_article_57_verified_institution_scope", "inconsistent_article_57_3_registry_binding"} & {gap["code"] for gap in ordered_result["data_gaps"]})
        permuted = deepcopy(two_states)
        permuted["concerned_institutions"].reverse()
        self.assertEqual(_article_57_assessment(permuted, policy), ordered_result)

        assessment["institution_scope_evidence"]["case_ref"] = "other-case"
        mismatch = _article_57_assessment(assessment, policy)
        gaps = mismatch["data_gaps"]
        self.assertIn("missing_article_57_verified_institution_scope", {gap["code"] for gap in gaps})
        self.assertEqual(mismatch["result"]["national_payment_obligation_status"], "not_assessed")

        assessment["institution_scope_evidence"] = None
        missing_scope = _article_57_assessment(assessment, policy)
        self.assertIn("missing_article_57_verified_institution_scope", {gap["code"] for gap in missing_scope["data_gaps"]})
        self.assertEqual(missing_scope["result"]["national_payment_obligation_status"], "not_assessed")

        assessment = _article_57(True, False, False, all_relieved=True)
        assessment["annex_viii_part_2_applicability"] = {"result": False, "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1", "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01", "catalogue_valid_to": None, "annex_consolidation_version": "reg-988-2009-2010-05-01", "annex_validity_or_applicability_date": "2026-12-01", "scheme_match_status": "not_matched", "matched_scheme_entry": None, "annex_evidence_refs": ["synthetic-annex-evidence"]}
        assessment["root_local_benefit_ref"] = dict(assessment["root_local_benefit_ref"], value="other-benefit")
        gaps = _article_57_assessment(assessment, policy)["data_gaps"]
        self.assertIn("inconsistent_article_57_root_institution_binding", {gap["code"] for gap in gaps})

        assessment = _article_57(True, False, False, all_relieved=True)
        assessment["annex_viii_part_2_applicability"] = {"result": False, "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1", "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01", "catalogue_valid_to": None, "annex_consolidation_version": "reg-988-2009-2010-05-01", "annex_validity_or_applicability_date": "2026-12-01", "scheme_match_status": "not_matched", "matched_scheme_entry": None, "annex_evidence_refs": ["synthetic-annex-evidence"]}
        assessment["concerned_institutions"][0]["coordination_case_ref"] = "other-case"
        gaps = _article_57_assessment(assessment, policy)["data_gaps"]
        self.assertIn("missing_article_57_multi_institution_evidence", {gap["code"] for gap in gaps})

        assessment = _article_57(True, False, False, all_relieved=True)
        assessment["annex_viii_part_2_applicability"] = {"result": True, "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1", "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01", "catalogue_valid_to": None, "annex_consolidation_version": "reg-988-2009-2010-05-01", "annex_validity_or_applicability_date": "2026-12-01", "scheme_match_status": "matched", "matched_scheme_entry": "invented-entry", "annex_evidence_refs": ["synthetic-annex-evidence"]}
        gaps = _article_57_assessment(assessment, policy)["data_gaps"]
        self.assertIn("missing_article_57_annex_viii_part_2_catalogue", {gap["code"] for gap in gaps})

    def test_v019_missing_or_invalid_scope_institution_and_last_state_evidence_fails_closed(self):
        from family_office_engine.services.it_es_eu_pension_pro_rata import _article_57_assessment

        policy = load_rule_pack(RULE_PACK)
        annex_policy = policy["pro_rata_method"]["article_57_source_bound"]["annex_viii_part_2"]
        annex_policy.update({"machine_readable_validity_catalogue_status": "available", "catalogue_entry_ids": ["synthetic-catalogue-entry"], "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1", "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01", "catalogue_valid_to": None})
        assessment = _article_57(True, False, False, all_relieved=True)
        assessment["annex_viii_part_2_applicability"] = {"result": False, "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1", "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01", "catalogue_valid_to": None, "annex_consolidation_version": "reg-988-2009-2010-05-01", "annex_validity_or_applicability_date": "2026-12-01", "scheme_match_status": "not_matched", "matched_scheme_entry": None, "annex_evidence_refs": ["synthetic-annex-evidence"]}
        assessment["last_state_attestation"] = _last_state_attestation()

        for field, invalid in (("issuer_institution_ref", None), ("as_of_date", "2026-11-30"), ("temporal_coverage_to", "2026-11-30"), ("procedural_coverage_ref", None), ("resolved_source_refs", []), ("operator_verification_status", "unverified"), ("full_perimeter_status", "attested_complete")):
            candidate = deepcopy(assessment)
            candidate["institution_scope_evidence"][field] = invalid
            outcome = _article_57_assessment(candidate, policy)
            self.assertIn("missing_article_57_verified_institution_scope", {gap["code"] for gap in outcome["data_gaps"]})
            self.assertEqual(outcome["result"]["national_payment_obligation_status"], "not_assessed")

        candidate = deepcopy(assessment)
        candidate["evidence_registry"][0]["content_digest"] = "sha256:" + "0" * 64
        outcome = _article_57_assessment(candidate, policy)
        self.assertTrue({"missing_article_57_verified_institution_scope", "inconsistent_article_57_3_registry_binding"} & {gap["code"] for gap in outcome["data_gaps"]})
        self.assertEqual(outcome["result"]["national_payment_obligation_status"], "not_assessed")
        self.assertNotIn("article_57_3_last_state", outcome["result"])

        for field in ("pertinent_period_refs", "total_duration", "one_year_comparator", "applicable_legislation", "autonomous_right_determination", "source_evidence_refs"):
            candidate = deepcopy(assessment)
            candidate["concerned_institutions"][0]["article_57_1_evidence"].pop(field)
            outcome = _article_57_assessment(candidate, policy)
            self.assertIn("missing_article_57_multi_institution_evidence", {gap["code"] for gap in outcome["data_gaps"]})
            self.assertEqual(outcome["result"]["national_payment_obligation_status"], "not_assessed")

        candidate = deepcopy(assessment)
        candidate["concerned_institutions"][0].pop("article_57_1_evidence")
        outcome = _article_57_assessment(candidate, policy)
        self.assertIn("missing_article_57_multi_institution_evidence", {gap["code"] for gap in outcome["data_gaps"]})

        for field, invalid in (("applicable_legislation", None), ("conditions_event_ref", None), ("candidate_conditions_comparability_status", "not_assessed"), ("last_state_selection_status", "tied"), ("comparability_evidence_refs", [])):
            candidate = deepcopy(assessment)
            candidate["last_state_attestation"][field] = invalid
            outcome = _article_57_assessment(candidate, policy)
            self.assertTrue({"missing_article_57_3_comparable_last_state_evidence", "missing_article_57_3_registry_evidence", "invalid_article_57_3_last_state_attestation"} & {gap["code"] for gap in outcome["data_gaps"]})
            self.assertEqual(outcome["result"]["national_payment_obligation_status"], "not_assessed")

    def test_v022_assessment_registry_and_root_predicates_fail_closed(self):
        from family_office_engine.services.it_es_eu_pension_pro_rata import _article_57_assessment

        policy = load_rule_pack(RULE_PACK)
        policy["pro_rata_method"]["article_57_source_bound"]["annex_viii_part_2"].update({"machine_readable_validity_catalogue_status": "available", "catalogue_entry_ids": ["synthetic-catalogue-entry"], "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1", "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01", "catalogue_valid_to": None})
        for duration, matched in ((True, True), (False, False)):
            assessment = _article_57(duration, False, False, all_relieved=duration)
            assessment["annex_viii_part_2_applicability"] = {"result": matched, "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1", "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01", "catalogue_valid_to": None, "annex_consolidation_version": "reg-988-2009-2010-05-01", "annex_validity_or_applicability_date": "2026-12-01", "scheme_match_status": "matched" if matched else "not_matched", "matched_scheme_entry": "synthetic-catalogue-entry" if matched else None, "annex_evidence_refs": ["synthetic-annex-evidence"]}
            self.assertEqual(_article_57_assessment(assessment, policy)["result"]["article_57_exception_status"], "excluded_by_57_4" if matched else "does_not_apply")
            for mutation in ("duplicate", "digest", "issuer", "coverage", "unresolved", "malformed_extra"):
                candidate = deepcopy(assessment)
                entry = candidate["evidence_registry"][0]
                if mutation == "duplicate": candidate["evidence_registry"].append(deepcopy(entry))
                elif mutation == "digest": entry["content_digest"] = "sha256:" + "0" * 64
                elif mutation == "issuer": entry["issuer_institution_ref"] = "other"
                elif mutation == "coverage": entry["coverage"]["temporal_coverage_to"] = "2026-11-30"
                elif mutation == "malformed_extra": entry["coverage"] = None
                else: candidate["institution_scope_evidence"]["resolved_source_refs"] = ["missing"]
                with self.subTest(duration=duration, matched=matched, mutation=mutation):
                    outcome = _article_57_assessment(candidate, policy)
                    self.assertEqual(outcome["result"]["article_57_exception_status"], "not_assessed")
                    self.assertTrue(outcome["data_gaps"])
            candidate = deepcopy(assessment)
            evidence = candidate["concerned_institutions"][0]["article_57_1_evidence"]
            evidence["total_duration"]["value"]["numerator"] = 365 if duration else 364
            candidate["concerned_institutions"][0]["article_57_1_relief_result"] = not duration
            outcome = _article_57_assessment(candidate, policy)
            self.assertEqual(outcome["result"]["article_57_exception_status"], "not_assessed")
            self.assertTrue(outcome["data_gaps"])
            for field in ("unit", "comparator", "autonomous", "legislation"):
                candidate = deepcopy(assessment)
                record = candidate["concerned_institutions"][0]
                evidence = record["article_57_1_evidence"]
                if field == "unit":
                    evidence["total_duration"]["unit"] = "synthetic-unit"
                    evidence["one_year_comparator"]["unit"] = "synthetic-unit"
                elif field == "comparator":
                    evidence["one_year_comparator"]["value"]["numerator"] = 400 if duration else 300
                elif field == "autonomous":
                    evidence["autonomous_right_determination"]["result"] = True
                    record["article_57_1_relief_result"] = False
                else:
                    record["applicable_legislation_version"] = "other-version"
                    evidence["applicable_legislation"]["version"] = "other-version"
                with self.subTest(duration=duration, field=field):
                    outcome = _article_57_assessment(candidate, policy)
                    self.assertEqual(outcome["result"]["article_57_exception_status"], "not_assessed")
                    self.assertTrue(outcome["data_gaps"])

    def test_v023_public_snapshot_rejects_invalid_registry_and_root_mismatches(self):
        policy = load_rule_pack(RULE_PACK)
        policy["pro_rata_method"]["article_57_source_bound"]["annex_viii_part_2"].update({
            "machine_readable_validity_catalogue_status": "available",
            "catalogue_entry_ids": ["synthetic-catalogue-entry"],
            "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1",
            "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01",
            "catalogue_valid_to": None,
        })

        def build(assessment):
            payload = _input([_period("IT", "2006-01-01", "2020-12-31"),
                              _period("ES", "2021-01-01", "2025-12-31")])
            payload["article_57_assessment"] = assessment
            with tempfile.TemporaryDirectory() as tmp_dir:
                root = Path(tmp_dir)
                input_path, output_path = root / "input.json", root / "snapshot.json"
                input_path.write_text(json.dumps(payload), encoding="utf-8")
                with patch("family_office_engine.services.it_es_eu_pension_pro_rata.load_rule_pack", return_value=policy):
                    result = build_it_es_eu_pension_pro_rata(input_path, RULE_PACK, output_path)
                self.assertEqual(result, json.loads(output_path.read_text(encoding="utf-8")))
                return result

        def assert_closed(snapshot, expected_gap):
            article = snapshot["article_57"]
            self.assertEqual(article["article_57_exception_status"], "not_assessed")
            self.assertEqual(article["national_payment_obligation_status"], "not_assessed")
            self.assertTrue(snapshot["data_gaps"])
            self.assertIn(expected_gap, {gap["code"] for gap in snapshot["data_gaps"]})
            self.assertEqual(snapshot["spanish_pro_rata_pension"]["status"], "not_calculable")
            self.assertIsNone(snapshot["spanish_pro_rata_pension"]["amounts"])
            for output in (article, snapshot["spanish_pro_rata_pension"]):
                for key in ("payer", "paying_institution", "competent_institution", "article_57_3_last_state"):
                    self.assertNotIn(key, output)

        for duration, matched in ((True, True), (False, False)):
            assessment = _article_57(duration, False, False, all_relieved=duration)
            assessment["annex_viii_part_2_applicability"] = {
                "result": matched, "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1",
                "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01",
                "catalogue_valid_to": None, "annex_consolidation_version": "reg-988-2009-2010-05-01",
                "annex_validity_or_applicability_date": "2026-12-01",
                "scheme_match_status": "matched" if matched else "not_matched",
                "matched_scheme_entry": "synthetic-catalogue-entry" if matched else None,
                "annex_evidence_refs": ["synthetic-annex-evidence"],
            }
            baseline = build(assessment)
            self.assertEqual(baseline["article_57"]["article_57_exception_status"],
                             "excluded_by_57_4" if matched else "does_not_apply")
            for mutation in ("duplicate", "digest", "issuer", "coverage", "unresolved", "malformed_extra"):
                candidate = deepcopy(assessment)
                registry = candidate["evidence_registry"]
                if mutation == "duplicate": registry.append(deepcopy(registry[0]))
                elif mutation == "digest": registry[0]["content_digest"] = "sha256:" + "0" * 64
                elif mutation == "issuer": registry[0]["issuer_institution_ref"] = "other"
                elif mutation == "coverage": registry[0]["coverage"]["temporal_coverage_to"] = "2026-11-30"
                elif mutation == "unresolved": candidate["institution_scope_evidence"]["resolved_source_refs"] = ["missing"]
                else: registry[0]["coverage"] = None
                expected_gap = {
                    "unresolved": "missing_article_57_3_registry_evidence",
                }.get(mutation, "inconsistent_article_57_3_registry_binding")
                with self.subTest(duration=duration, matched=matched, mutation=mutation):
                    assert_closed(build(candidate), expected_gap)

            for field in ("duration", "unit", "comparator", "autonomous", "legislation_id", "legislation_version", "relief"):
                candidate = deepcopy(assessment)
                record = candidate["concerned_institutions"][0]
                evidence = record["article_57_1_evidence"]
                if field == "duration":
                    evidence["total_duration"]["value"]["numerator"] = 365 if duration else 364
                    record["article_57_1_relief_result"] = not duration
                elif field == "unit":
                    evidence["total_duration"]["unit"] = evidence["one_year_comparator"]["unit"] = "synthetic-unit"
                elif field == "comparator":
                    evidence["one_year_comparator"]["value"]["numerator"] = 300 if duration else 400
                    record["article_57_1_relief_result"] = not duration
                elif field == "autonomous":
                    evidence["autonomous_right_determination"]["result"] = True
                    record["article_57_1_relief_result"] = False
                elif field == "relief":
                    record["article_57_1_relief_result"] = not duration
                else:
                    name = "id" if field == "legislation_id" else "version"
                    record["applicable_legislation_" + name] = "synthetic-other"
                    evidence["applicable_legislation"][name] = "synthetic-other"
                with self.subTest(duration=duration, field=field):
                    snapshot = build(candidate)
                    assert_closed(snapshot, "missing_article_57_multi_institution_evidence" if field == "relief" else "inconsistent_article_57_root_institution_binding")

        # Reverse the autonomous-right disagreement: root says yes, institution says no.
        valid = _article_57(True, False, False, all_relieved=True)
        valid["annex_viii_part_2_applicability"] = deepcopy(assessment["annex_viii_part_2_applicability"])
        valid_snapshot = build(valid)
        self.assertEqual(valid_snapshot["article_57"]["article_57_exception_status"], "applies")
        self.assertNotIn("article_57_3_last_state", valid_snapshot["article_57"])
        self.assertEqual(valid_snapshot["article_57"]["national_payment_obligation_status"], "not_assessed")
        self.assertFalse({"payer", "paying_institution", "competent_institution"} & set(valid_snapshot["article_57"]))
        permuted = deepcopy(valid)
        permuted["evidence_registry"].reverse()
        permuted["concerned_institutions"].reverse()
        self.assertEqual(build(permuted), valid_snapshot)

        candidate = _article_57(True, True, False)
        candidate["annex_viii_part_2_applicability"] = deepcopy(assessment["annex_viii_part_2_applicability"])
        self.assertEqual(build(candidate)["article_57"]["article_57_exception_status"], "does_not_apply")
        record = candidate["concerned_institutions"][0]
        record["article_57_1_evidence"]["autonomous_right_determination"]["result"] = False
        record["article_57_1_relief_result"] = True
        assert_closed(build(candidate), "inconsistent_article_57_root_institution_binding")

    def test_v024_public_builder_fails_closed_for_last_state_types_references_and_registry_bindings(self):
        policy = load_rule_pack(RULE_PACK)
        policy["pro_rata_method"]["article_57_source_bound"]["annex_viii_part_2"].update({
            "machine_readable_validity_catalogue_status": "available",
            "catalogue_entry_ids": ["synthetic-catalogue-entry"],
            "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1",
            "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01",
            "catalogue_valid_to": None,
        })

        def required_payload():
            payload = _input([_period("IT", "2006-01-01", "2020-12-31"), _period("ES", "2021-01-01", "2025-12-31")])
            payload["article_57_assessment"] = _article_57(True, False, False, all_relieved=True)
            payload["article_57_assessment"]["annex_viii_part_2_applicability"] = {
                "result": False, "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1",
                "catalogue_digest": "sha256:synthetic", "catalogue_valid_from": "2010-05-01", "catalogue_valid_to": None,
                "annex_consolidation_version": "reg-988-2009-2010-05-01", "annex_validity_or_applicability_date": "2026-12-01",
                "scheme_match_status": "not_matched", "matched_scheme_entry": None, "annex_evidence_refs": ["synthetic-annex-evidence"],
            }
            return payload

        def build_required(payload):
            with tempfile.TemporaryDirectory() as tmp_dir:
                root = Path(tmp_dir)
                input_path, output_path = root / "input.json", root / "snapshot.json"
                input_path.write_text(json.dumps(payload), encoding="utf-8")
                with patch("family_office_engine.services.it_es_eu_pension_pro_rata.load_rule_pack", return_value=policy):
                    result = build_it_es_eu_pension_pro_rata(input_path, RULE_PACK, output_path)
                self.assertEqual(result, json.loads(output_path.read_text(encoding="utf-8")))
                return result

        def assert_closed(payload, gap):
            snapshot = build_required(payload)
            self.assertEqual(snapshot["article_57"]["article_57_exception_status"], "not_assessed")
            self.assertEqual(snapshot["article_57"]["national_payment_obligation_status"], "not_assessed")
            self.assertIn(gap, {item["code"] for item in snapshot["data_gaps"]})
            self.assertEqual(snapshot["spanish_pro_rata_pension"]["status"], "not_calculable")
            self.assertIsNone(snapshot["spanish_pro_rata_pension"]["amounts"])
            self.assertNotIn("article_57_3_last_state", snapshot["article_57"])
            self.assertFalse({"payer", "paying_institution", "competent_institution"} & set(snapshot["article_57"]))

        for name, assessment, expected in (
            ("annex", _article_57(True, False, False, all_relieved=True), "excluded_by_57_4"),
            ("duration", _article_57(False, False, False), "does_not_apply"),
            ("autonomous", _article_57(True, True, False), "does_not_apply"),
            ("not_all_relieved", _article_57(True, False, False), "applies"),
        ):
            payload = required_payload()
            payload["article_57_assessment"] = assessment
            annex = payload["article_57_assessment"]["annex_viii_part_2_applicability"] = deepcopy(required_payload()["article_57_assessment"]["annex_viii_part_2_applicability"])
            if name == "annex":
                annex.update({"result": True, "scheme_match_status": "matched", "matched_scheme_entry": "synthetic-catalogue-entry"})
            if name == "not_all_relieved":
                second = deepcopy(payload["article_57_assessment"]["concerned_institutions"][0])
                second.update({
                    "institution_ref": "synthetic-it", "member_state": "IT",
                    "local_claim_ref": {"issuer_institution_ref": "synthetic-it", "namespace": "synthetic-it-claim", "value": "claim-2", "evidence_refs": ["synthetic-it-claim-evidence"]},
                    "local_benefit_ref": {"issuer_institution_ref": "synthetic-it", "namespace": "synthetic-it-benefit", "value": "benefit-2", "evidence_refs": ["synthetic-it-benefit-evidence"]},
                    "transitional_applicability": _transitional("IT", "2026-12-01"), "article_57_1_relief_result": False,
                })
                second["article_57_1_evidence"]["autonomous_right_determination"]["result"] = True
                payload["article_57_assessment"]["concerned_institutions"].append(second)
                institution_refs = ["synthetic-es", "synthetic-it"]
                payload["article_57_assessment"]["institution_scope_evidence"]["institution_refs"] = institution_refs
                for entry in payload["article_57_assessment"]["evidence_registry"]:
                    entry["coverage"]["institution_refs"] = institution_refs
            payload["article_57_assessment"]["last_state_attestation"] = "malformed-but-not-required"
            with self.subTest(branch=name):
                snapshot = build_required(payload)
                self.assertEqual(snapshot["article_57"]["article_57_exception_status"], expected)
                self.assertNotIn("invalid_article_57_3_last_state_attestation", {item["code"] for item in snapshot["data_gaps"]})
                self.assertNotIn("article_57_3_last_state", snapshot["article_57"])

        for invalid in ("not-an-object", [], 7, True, None, {"institution_ref": "synthetic-es"}):
            payload = required_payload()
            payload["article_57_assessment"]["last_state_attestation"] = invalid
            with self.subTest(kind=type(invalid).__name__):
                assert_closed(payload, "invalid_article_57_3_last_state_attestation")

        for field in ("selection_evidence_refs", "conditions_evidence_refs", "comparability_evidence_refs", "institutional_record_evidence_refs"):
            for invalid in (None, [], ["synthetic-selection", "synthetic-selection"]):
                payload = required_payload()
                payload["article_57_assessment"]["last_state_attestation"][field] = invalid
                with self.subTest(field=field, invalid=invalid):
                    assert_closed(payload, "inconsistent_article_57_3_registry_binding" if isinstance(invalid, list) and invalid else "missing_article_57_3_registry_evidence")
        payload = required_payload()
        attestation = payload["article_57_assessment"]["last_state_attestation"]
        attestation["conditions_evidence_refs"] = list(attestation["selection_evidence_refs"])
        assert_closed(payload, "inconsistent_article_57_3_registry_binding")
        for field, invalid in (("conditions_event_ref", None), ("conditions_event_ref", ""), ("applicable_legislation", None)):
            payload = required_payload()
            payload["article_57_assessment"]["last_state_attestation"][field] = invalid
            with self.subTest(field=field, invalid=invalid):
                assert_closed(payload, "missing_article_57_3_registry_evidence")
        for conditions_date, expected_gap in (("2020-01-01", None), ("2026-12-01", None), ("2019-12-31", "invalid_article_57_3_last_state_attestation")):
            payload = required_payload()
            payload["article_57_assessment"]["last_state_attestation"]["conditions_satisfied_on"] = conditions_date
            with self.subTest(conditions_date=conditions_date):
                if expected_gap is None:
                    snapshot = build_required(payload)
                    self.assertEqual(snapshot["article_57"]["article_57_exception_status"], "applies")
                    self.assertNotIn("article_57_3_last_state", snapshot["article_57"])
                else:
                    assert_closed(payload, expected_gap)

        from family_office_engine.services.it_es_eu_pension_pro_rata import _article_57_last_state_evidence
        validity_case = _article_57(True, False, False, all_relieved=True)
        validity_record = validity_case["concerned_institutions"][0]
        validity_attestation = validity_case["last_state_attestation"]
        self.assertTrue(_article_57_last_state_evidence(validity_attestation, validity_case["coordination_manifest"], validity_record, ["synthetic-es"], "2026-12-01"))
        for valid_to in ("2019-12-31", "2026-11-30"):
            with self.subTest(legislation_valid_to=valid_to):
                candidate_record = deepcopy(validity_record)
                candidate_attestation = deepcopy(validity_attestation)
                candidate_attestation["conditions_satisfied_on"] = "2026-12-01"
                candidate_attestation["applicable_legislation"]["valid_to"] = valid_to
                candidate_record["applicable_legislation_valid_to"] = valid_to
                candidate_record["article_57_1_evidence"]["applicable_legislation"]["valid_to"] = valid_to
                self.assertFalse(_article_57_last_state_evidence(candidate_attestation, validity_case["coordination_manifest"], candidate_record, ["synthetic-es"], "2026-12-01"))

        for mutation in ("unresolved", "duplicate_id", "content", "digest", "malformed_digest", "verified", "issuer", "case", "benefit", "date", "coverage"):
            payload = required_payload()
            assessment = payload["article_57_assessment"]
            registry = assessment["evidence_registry"]
            entry = registry[-1]
            if mutation == "unresolved": assessment["last_state_attestation"]["selection_evidence_refs"] = ["missing"]
            elif mutation == "duplicate_id": registry.append(deepcopy(entry))
            elif mutation == "content": entry["content_utf8"] = "mutated"
            elif mutation == "digest": entry["content_digest"] = "sha256:" + "0" * 64
            elif mutation == "malformed_digest": entry["content_digest"] = "sha256:BAD"
            elif mutation == "verified": entry["verified"] = False
            elif mutation == "issuer": entry["issuer_institution_ref"] = "other"
            elif mutation == "case": entry["coverage"]["case_ref"] = "other-case"
            elif mutation == "benefit": entry["coverage"]["coordinated_benefit_ref"] = "other-benefit"
            elif mutation == "date": entry["coverage"]["as_of_date"] = "2026-11-30"
            else: entry["coverage"]["temporal_coverage_to"] = "2026-11-30"
            with self.subTest(mutation=mutation):
                assert_closed(payload, "missing_article_57_3_registry_evidence" if mutation == "unresolved" else "inconsistent_article_57_3_registry_binding")

    def test_v021_registry_integrity_and_coverage_fail_closed(self):
        from family_office_engine.services.it_es_eu_pension_pro_rata import _article_57_full_perimeter_scope

        assessment = _article_57(True, False, False, all_relieved=True)
        scope = assessment["institution_scope_evidence"]
        manifest = assessment["coordination_manifest"]
        registry = assessment["evidence_registry"]

        def valid(s, m, r):
            return _article_57_full_perimeter_scope(s, m, ["synthetic-es"], r)

        self.assertTrue(valid(scope, manifest, registry))
        expanded = deepcopy(registry)
        expanded[0]["coverage"].update(temporal_coverage_from="2025-12-31", temporal_coverage_to="2027-01-01")
        self.assertTrue(valid(scope, manifest, expanded))
        cases = []
        duplicate = deepcopy(registry)
        duplicate.append(deepcopy(duplicate[0]))
        cases.append(("duplicate registry id", scope, manifest, duplicate))
        duplicate_unreferenced = deepcopy(registry)
        duplicate_unreferenced.append(deepcopy(duplicate_unreferenced[1]))
        cases.append(("duplicate unreferenced registry id", scope, manifest, duplicate_unreferenced))
        corrupted_unreferenced = deepcopy(registry)
        corrupted_unreferenced[1]["content_digest"] = "sha256:" + "0" * 64
        cases.append(("corrupted unreferenced registry entry", scope, manifest, corrupted_unreferenced))
        repeated_scope = deepcopy(scope)
        repeated_scope["resolved_source_refs"].append(repeated_scope["resolved_source_refs"][0])
        cases.append(("duplicate resolved reference", repeated_scope, manifest, registry))
        unresolved = deepcopy(scope)
        unresolved["resolved_source_refs"] = ["missing-evidence"]
        cases.append(("unresolved reference", unresolved, manifest, registry))
        mismatched_scope = deepcopy(scope)
        mismatched_scope["issuer_institution_ref"] = "other-issuer"
        mismatched_registry = deepcopy(registry)
        mismatched_registry[0]["issuer_institution_ref"] = "other-issuer"
        cases.append(("manifest issuer mismatch", mismatched_scope, manifest, mismatched_registry))
        for digest in ("sha256:" + "A" * 64, "sha256:" + "a" * 63, "sha256:" + "g" * 64, "sha256:" + "0" * 64, None):
            candidate = deepcopy(registry)
            candidate[0]["content_digest"] = digest
            cases.append((f"invalid digest {digest}", scope, manifest, candidate))
        for field, invalid in (("content_utf8", None), ("content_utf8", "changed"), ("content_utf8", "\ud800")):
            candidate = deepcopy(registry)
            candidate[0][field] = invalid
            cases.append((f"invalid {field}", scope, manifest, candidate))
        for field, invalid in (("temporal_coverage_from", None), ("temporal_coverage_to", None), ("temporal_coverage_from", "2026-01-02"), ("temporal_coverage_to", "2026-12-30"), ("temporal_coverage_from", "2026-99-01")):
            candidate = deepcopy(registry)
            candidate[0]["coverage"][field] = invalid
            cases.append((f"invalid coverage {field} {invalid}", scope, manifest, candidate))
        for field in ("temporal_coverage_from", "temporal_coverage_to"):
            candidate = deepcopy(registry)
            candidate[0]["coverage"].pop(field)
            cases.append((f"missing coverage {field}", scope, manifest, candidate))
        for field in ("temporal_coverage_from", "temporal_coverage_to"):
            candidate_scope = deepcopy(scope)
            candidate_scope.pop(field)
            cases.append((f"missing perimeter {field}", candidate_scope, manifest, registry))
        for label, candidate_scope, candidate_manifest, candidate_registry in cases:
            with self.subTest(case=label):
                self.assertFalse(valid(candidate_scope, candidate_manifest, candidate_registry))

    def test_institution_relief_must_match_duration_and_autonomous_right(self):
        from family_office_engine.services.it_es_eu_pension_pro_rata import _article_57_per_institution_evidence

        record = _article_57(True, False, False, all_relieved=True)["concerned_institutions"][0]
        evidence = record["article_57_1_evidence"]
        for days, right, expected in ((364, False, True), (365, False, False), (366, False, False), (364, True, False)):
            with self.subTest(days=days, right=right):
                evidence["total_duration"]["value"] = {"numerator": days, "denominator": 1}
                evidence["autonomous_right_determination"]["result"] = right
                record["article_57_1_relief_result"] = expected
                self.assertTrue(_article_57_per_institution_evidence(evidence, record))
                record["article_57_1_relief_result"] = not expected
                self.assertFalse(_article_57_per_institution_evidence(evidence, record))
        evidence["autonomous_right_determination"]["result"] = None
        self.assertFalse(_article_57_per_institution_evidence(evidence, record))

    def test_sample_duration_segment_binding_is_valid(self):
        from family_office_engine.services.it_es_eu_pension_pro_rata import _article_57_duration_binding_gaps, _article_57_full_perimeter_scope

        sample_path = Path(__file__).resolve().parents[2] / "examples" / "spanish-eu-theoretical-pension-pro-rata-input-sample.json"
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
        self.assertEqual(_article_57_duration_binding_gaps(sample["article_57_assessment"]), [])
        assessment = sample["article_57_assessment"]
        self.assertTrue(_article_57_full_perimeter_scope(assessment["institution_scope_evidence"], assessment["coordination_manifest"], ["synthetic-es"], assessment["evidence_registry"]))

    def test_rejects_root_schema_version_and_unknown_root_shape(self):
        payload = _input([])
        payload["article_57_assessment"]["schema_version"] = "v0.17"
        with self.assertRaisesRegex(ItEsEuPensionProRataError, "forbidden root schema_version"):
            self._build(payload)
        payload["article_57_assessment"].pop("schema_version")
        payload["article_57_assessment"]["unbound"] = True
        with self.assertRaisesRegex(ItEsEuPensionProRataError, "forbidden root schema_version"):
            self._build(payload)

    def test_unknown_transitional_annex_or_institution_binding_is_fail_closed(self):
        payload = _input([])
        payload["article_57_assessment"]["transitional_applicability"]["basic_regulation_883_87"]["result"] = "not_assessed"
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertIn("missing_article_57_transitional_applicability", {gap["code"] for gap in result["data_gaps"]})

        payload = _input([])
        payload["article_57_assessment"]["annex_viii_part_2_applicability"] = {"result": False, "matched_scheme_entry": "invented-entry"}
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertIn("missing_article_57_annex_viii_part_2_catalogue", {gap["code"] for gap in result["data_gaps"]})

    def test_requires_spanish_insured_or_equivalent_status_when_rule_pack_requires_it(self):
        payload = _input([_period("IT", "2006-01-01", "2020-12-31"), _period("ES", "2021-01-01", "2025-12-31")])
        payload.pop("spanish_insured_or_equivalent_status")

        result = self._build(payload)

        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_calculable")
        self.assertIn(
            "missing_spanish_insured_or_equivalent_status",
            {gap["code"] for gap in result["data_gaps"]},
        )

    def test_blocks_when_spanish_insured_or_equivalent_status_is_not_confirmed(self):
        payload = _input([_period("IT", "2006-01-01", "2020-12-31"), _period("ES", "2021-01-01", "2025-12-31")])
        payload["spanish_insured_or_equivalent_status"] = False

        result = self._build(payload)

        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_calculable")
        self.assertIsNone(result["spanish_pro_rata_pension"]["amounts"])
        self.assertIn(
            "spanish_insured_or_equivalent_status_not_confirmed",
            {gap["code"] for gap in result["data_gaps"]},
        )

    def test_blocks_when_recent_requirement_not_met_even_with_totalization(self):
        result = self._build(
            _input(
                [
                    _period("IT", "1990-01-01", "2004-12-31"),
                    _period("ES", "2005-01-01", "2009-12-31"),
                ]
            )
        )

        self.assertEqual(result["status"], "blocked_not_eligible")
        self.assertEqual(result["spanish_entitlement"]["status"], "not_eligible")
        self.assertIn(
            "spanish_entitlement_not_reached_even_with_totalization",
            {gap["code"] for gap in result["data_gaps"]},
        )

    def test_blocks_pro_rata_without_spanish_theoretical_amount(self):
        payload = _input([_period("IT", "2006-01-01", "2020-12-31"), _period("ES", "2021-01-01", "2025-12-31")])
        payload.pop("spanish_theoretical_pension")

        result = self._build(payload)

        self.assertEqual(result["status"], "blocked_missing_inputs")
        self.assertIn("missing_spanish_theoretical_pension", {gap["code"] for gap in result["data_gaps"]})
        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_calculable")

    def test_complete_theoretical_snapshot_resolves_stale_declared_missing_amount_gap(self):
        payload = _input([_period("IT", "2006-01-01", "2020-12-31"), _period("ES", "2021-01-01", "2025-12-31")])
        payload.pop("spanish_theoretical_pension")
        payload["data_gaps"] = [
            {
                "code": "missing_spanish_theoretical_amount",
                "message": "Spanish theoretical pension is not available yet.",
            }
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "it-es-eu-pension-pro-rata-input.json"
            snapshot_path = root / "spanish-eu-theoretical-pension.snapshot.json"
            output_path = root / "it-es-eu-pension-pro-rata.snapshot.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            snapshot_path.write_text(
                json.dumps(
                    {
                        "schema_version": "spanish-eu-theoretical-pension/v1",
                        "status": "complete",
                        "spanish_theoretical_pension": _input([])["spanish_theoretical_pension"],
                    }
                ),
                encoding="utf-8",
            )

            result = build_it_es_eu_pension_pro_rata(input_path, RULE_PACK, output_path, snapshot_path)

        self.assertEqual(result["status"], "blocked_missing_inputs")
        self.assertNotIn("missing_spanish_theoretical_amount", {gap["code"] for gap in result["data_gaps"]})
        self.assertIn("missing_article_57_annex_viii_part_2_catalogue", {gap["code"] for gap in result["data_gaps"]})

    def test_blocks_uncovered_retirement_year_instead_of_using_2026_pack(self):
        payload = _input([_period("IT", "2006-01-01", "2020-12-31"), _period("ES", "2021-01-01", "2025-12-31")])
        payload["retirement_date"] = "2039-12"
        payload["recent_contribution_anchor_date"] = "2039-12-01"

        result = self._build(payload)

        self.assertEqual(result["status"], "blocked_not_eligible")
        self.assertIn("retirement_date_not_covered_by_rule_pack", {gap["code"] for gap in result["data_gaps"]})

    def test_missing_periods_returns_gap_not_key_error(self):
        payload = _input([])

        result = self._build(payload)

        self.assertEqual(result["status"], "blocked_not_eligible")
        self.assertIn("missing_dated_insurance_periods", {gap["code"] for gap in result["data_gaps"]})

    def test_blocks_when_future_assumptions_are_not_explicit(self):
        payload = _input([_period("IT", "2006-01-01", "2020-12-31"), _period("ES", "2021-01-01", "2025-12-31")])
        payload["future_assumptions_status"] = "missing"

        result = self._build(payload)

        self.assertEqual(result["status"], "blocked_missing_inputs")
        self.assertIn("missing_future_contribution_assumptions", {gap["code"] for gap in result["data_gaps"]})

    def test_rejects_partial_month_periods(self):
        payload = _input([_period("ES", "2025-01-15", "2025-01-31")])

        with self.assertRaisesRegex(ItEsEuPensionProRataError, "first day of month"):
            self._build(payload)

    def test_requires_spanish_only_theoretical_provenance(self):
        payload = _input([_period("IT", "2006-01-01", "2020-12-31"), _period("ES", "2021-01-01", "2025-12-31")])
        payload["spanish_theoretical_pension"]["basis"] = "mixed_eu_bases"

        result = self._build(payload)

        self.assertEqual(result["status"], "blocked_missing_inputs")
        self.assertIn("spanish_theoretical_basis_not_spanish_only", {gap["code"] for gap in result["data_gaps"]})

    def test_blocks_periods_after_retirement_month(self):
        payload = _input([_period("IT", "2006-01-01", "2020-12-31"), _period("ES", "2021-01-01", "2026-12-31")])

        result = self._build(payload)

        self.assertEqual(result["status"], "blocked_missing_inputs")
        self.assertIn("insurance_period_after_retirement_date", {gap["code"] for gap in result["data_gaps"]})

    def test_rejects_unofficial_rule_source(self):
        broken = json.loads(RULE_PACK.read_text(encoding="utf-8"))
        broken["source_refs"][0]["url"] = "https://example.com/not-official"
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "rules.json"
            path.write_text(json.dumps(broken), encoding="utf-8")

            with self.assertRaisesRegex(ItEsEuPensionProRataError, "official EU or Spanish URL"):
                load_rule_pack(path)

    def test_real_rule_pack_cites_regulation_988_2009_article_1_16_for_article_57_4(self):
        rule_pack = load_rule_pack(RULE_PACK)
        regulation_988 = next(source for source in rule_pack["source_refs"] if source["source_id"] == "eurlex.reg-988-2009")
        article_57 = rule_pack["pro_rata_method"]["article_57_source_bound"]
        article_57_legal_basis = article_57["legal_basis"]

        self.assertEqual(article_57["contract_schema_version"], "v0.25")
        self.assertEqual(article_57["evidence_registry"]["content_digest_format"], "sha256-lowercase-hex-64")
        self.assertTrue(article_57["evidence_registry"]["requires_registry_coverage_of_declared_temporal_interval"])
        self.assertEqual(regulation_988["provisions"][0], "Article 1(16)")
        self.assertEqual(article_57_legal_basis[-1], "Regulation (EC) No 988/2009 Article 1(16)")
        self.assertIn("Regulation (EC) No 987/2009 Articles 12-13 and 47(4)-(7)", article_57_legal_basis)
        regulation_987 = next(source for source in rule_pack["source_refs"] if source["source_id"] == "eurlex.reg-987-2009")
        self.assertIn("Article 47(4)-(7)", regulation_987["provisions"])
        self.assertNotIn("Article 1(27)", regulation_988["provisions"])
        self.assertNotIn("Regulation (EC) No 988/2009 Article 1(27)", article_57_legal_basis)

    def test_v025_public_builder_binds_each_institutional_evidence_list_to_verified_registry(self):
        payload = _input([_period("ES", "2020-01-01", "2026-11-30")])
        valid = self._build(payload)
        valid_codes = {gap["code"] for gap in valid["data_gaps"]}
        self.assertNotIn("missing_article_57_3_registry_evidence", valid_codes)
        self.assertNotIn("inconsistent_article_57_3_registry_binding", valid_codes)

        for field, invalid, expected_gap in (
            ("source_evidence_refs", ["unknown-institutional-evidence"], "missing_article_57_3_registry_evidence"),
            ("source_evidence_refs", ["synthetic-institutional-art57", "synthetic-institutional-art57"], "inconsistent_article_57_3_registry_binding"),
            ("evidence_refs", ["unknown-institutional-evidence"], "missing_article_57_3_registry_evidence"),
            ("evidence_refs", ["synthetic-institutional-art57", "synthetic-institutional-art57"], "inconsistent_article_57_3_registry_binding"),
        ):
            with self.subTest(field=field, invalid=invalid):
                candidate = deepcopy(payload)
                record = candidate["article_57_assessment"]["concerned_institutions"][0]
                target = record["article_57_1_evidence"] if field == "source_evidence_refs" else record
                target[field] = invalid
                snapshot = self._build(candidate)
                self.assertIn(expected_gap, {gap["code"] for gap in snapshot["data_gaps"]})
                self.assertEqual(snapshot["article_57"]["article_57_exception_status"], "not_assessed")
                self.assertEqual(snapshot["article_57"]["national_payment_obligation_status"], "not_assessed")

    def test_v025_institutional_registry_non_utf8_content_fails_closed(self):
        from family_office_engine.services.it_es_eu_pension_pro_rata import _article_57_assessment

        policy = load_rule_pack(RULE_PACK)
        assessment = _article_57(False, False, False)
        entry = next(item for item in assessment["evidence_registry"] if item["evidence_id"] == "synthetic-institutional-art57")
        entry["content_utf8"] = "\ud800"

        outcome = _article_57_assessment(assessment, policy)
        self.assertIn("inconsistent_article_57_3_registry_binding", {gap["code"] for gap in outcome["data_gaps"]})
        self.assertEqual(outcome["result"]["article_57_exception_status"], "not_assessed")

    def test_v025_institutional_evidence_list_mutations_fail_closed(self):
        from family_office_engine.services.it_es_eu_pension_pro_rata import _article_57_assessment

        policy = load_rule_pack(RULE_PACK)
        for field, invalid, expected_gap in (
            ("source_evidence_refs", ["unknown-institutional-evidence"], "missing_article_57_3_registry_evidence"),
            ("source_evidence_refs", ["synthetic-institutional-art57", "synthetic-institutional-art57"], "inconsistent_article_57_3_registry_binding"),
            ("evidence_refs", ["unknown-institutional-evidence"], "missing_article_57_3_registry_evidence"),
            ("evidence_refs", ["synthetic-institutional-art57", "synthetic-institutional-art57"], "inconsistent_article_57_3_registry_binding"),
        ):
            with self.subTest(field=field, invalid=invalid):
                candidate = _article_57(False, False, False)
                record = candidate["concerned_institutions"][0]
                target = record["article_57_1_evidence"] if field == "source_evidence_refs" else record
                target[field] = invalid
                outcome = _article_57_assessment(candidate, policy)
                self.assertIn(expected_gap, {gap["code"] for gap in outcome["data_gaps"]})
                self.assertEqual(outcome["result"]["article_57_exception_status"], "not_assessed")

    def test_public_sample_resolves_institutional_evidence_without_relaxing_annex_boundary(self):
        sample_path = Path(__file__).resolve().parents[2] / "examples" / "spanish-eu-theoretical-pension-pro-rata-input-sample.json"
        sample = json.loads(sample_path.read_text(encoding="utf-8"))

        snapshot = self._build(sample)

        gap_codes = {gap["code"] for gap in snapshot["data_gaps"]}
        self.assertNotIn("missing_article_57_3_registry_evidence", gap_codes)
        self.assertNotIn("inconsistent_article_57_3_registry_binding", gap_codes)
        self.assertIn("missing_article_57_annex_viii_part_2_catalogue", gap_codes)
        article_57 = snapshot["article_57"]
        self.assertEqual(article_57["article_57_exception_status"], "not_assessed")
        self.assertEqual(article_57["national_payment_obligation_status"], "not_assessed")
        self.assertNotIn("article_57_3_last_state", article_57)

    def _build(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "it-es-eu-pension-pro-rata-input.json"
            output_path = root / "it-es-eu-pension-pro-rata.snapshot.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")

            result = build_it_es_eu_pension_pro_rata(input_path, RULE_PACK, output_path)

            self.assertTrue(output_path.exists())
            self.assertEqual(result, json.loads(output_path.read_text(encoding="utf-8")))
            return result


def _input(periods: list[dict]) -> dict:
    return {
        "schema_version": "it-es-eu-pension-pro-rata-input/v1",
        "scenario": "ordinary",
        "retirement_date": "2026-12",
        "date_of_birth": "1960-01-01",
        "recent_contribution_anchor_date": "2026-12-01",
        "spanish_insured_or_equivalent_status": True,
        "inps_history_status": "complete_dated_history",
        "future_assumptions_status": "explicit",
        "sources": [{"source_id": "synthetic-case", "type": "synthetic_fixture"}],
        "insurance_periods": periods,
        "article_57_assessment": _article_57(duration=False, autonomous=False, annex=False),
        "spanish_theoretical_pension": {
            "monthly_gross_amount": "2000.00",
            "annual_gross_amount": "24000.00",
            "currency": "EUR",
            "payments_per_year": 12,
            "source": "synthetic Spanish theoretical estimate",
            "source_country": "ES",
            "basis": "spanish_only_bases",
        },
    }


def _article_57(
    duration: bool | None,
    autonomous: bool | None,
    annex: bool | None,
    all_relieved: bool = False,
    legal_duration_days: int | None = None,
    legal_duration_rational: tuple[int, int] | None = None,
    comparator_rational: tuple[int, int] = (365, 1),
) -> dict:
    if legal_duration_days is None:
        legal_duration_days = 364 if duration is True else 365
    legal_duration = legal_duration_rational or (legal_duration_days, 1)
    preimage = {
        "canonicalization_profile": "fo-art57-c14n-v4",
        "parent_period_refs": ["synthetic-period"],
        "schema_version": "v0.19",
        "source_bounds": [
            {
                "native_duration": {
                    "precision": "exact",
                    "unit": "day",
                    "value": {"numerator": legal_duration[0], "denominator": legal_duration[1]},
                },
                "native_end": None,
                "native_start": None,
                "period_ref": "synthetic-period",
            }
        ],
    }
    segment_id = _segment_id(preimage)
    root_local_claim = {"issuer_institution_ref": "synthetic-es", "namespace": "synthetic-es-claim", "value": "claim-1", "evidence_refs": ["synthetic-local-claim"]}
    root_local_benefit = {"issuer_institution_ref": "synthetic-es", "namespace": "synthetic-es-benefit", "value": "benefit-1", "evidence_refs": ["synthetic-local-benefit"]}
    assessment = {
        "contract_schema_version": "v0.25",
        "canonicalization_profile": "fo-art57-c14n-v4",
        "human_review_required": True,
        "member_state": "ES",
        "benefit_id": "synthetic-old-age",
        "benefit_type": "old_age",
        "scheme_id": "synthetic-es-scheme",
        "competent_institution": "synthetic-es",
        "root_institution_ref": "synthetic-es",
        "root_local_claim_ref": root_local_claim,
        "root_local_benefit_ref": root_local_benefit,
        "applicable_legislation_id": "synthetic-legislation",
        "applicable_legislation_version": "synthetic-v1",
        "applicable_legislation_valid_from": "2020-01-01",
        "applicable_legislation_valid_to": None,
        "risk_materialization_date": "2026-12-01",
        "assessment_date": "2026-12-01",
        "transitional_applicability": _transitional("ES", "2026-12-01"),
        "legal_duration_for_article_57": {
            "value": {"numerator": legal_duration[0], "denominator": legal_duration[1]},
            "unit": "day",
            "source_segment_id": segment_id,
        },
        "one_year_comparator": {
            "value": {"numerator": comparator_rational[0], "denominator": comparator_rational[1]},
            "unit": "day",
            "legal_basis_refs": ["synthetic-art57-comparator"],
        },
        "duration_basis": "synthetic legal duration evidence",
        "duration_assessment_evidence_refs": ["synthetic-duration-evidence"],
        "duration_strictly_less_than_one_year": duration,
        "duration_source_segment": {"segment_id": segment_id, "preimage": preimage},
        "autonomous_right_from_state_periods_only": {
            "result": autonomous,
            "national_benefit_rule_pack_id": "synthetic-national-pack",
            "national_rule_version": "synthetic-v1",
            "risk_materialization_date": "2026-12-01",
            "evidence_refs": ["synthetic-autonomous-evidence"],
        },
        "annex_viii_part_2_applicability": {"result": None},
        "coordination_manifest": {
            "manifest_ref": "synthetic-manifest",
            "case_ref": "synthetic-case",
            "coordinated_benefit_ref": "synthetic-coordinated-old-age",
            "contingency_date": "2026-12-01",
            "issuer_institution_ref": "synthetic-contact-institution",
            "as_of_date": "2026-12-01",
            "evidence_refs": ["synthetic-manifest-evidence"],
        },
        "concerned_institutions": [{
            "institution_ref": "synthetic-es",
            "member_state": "ES",
            "coordination_manifest_ref": "synthetic-manifest",
            "coordination_case_ref": "synthetic-case",
            "coordinated_benefit_ref": "synthetic-coordinated-old-age",
            "contingency_date": "2026-12-01",
            "local_claim_ref": root_local_claim,
            "local_benefit_ref": root_local_benefit,
            "benefit_type": "old_age",
            "scheme_id": "synthetic-es-scheme",
            "competent_institution": "synthetic-es",
            "applicable_legislation_id": "synthetic-legislation",
            "applicable_legislation_version": "synthetic-v1",
            "applicable_legislation_valid_from": "2020-01-01",
            "applicable_legislation_valid_to": None,
            "risk_materialization_date": "2026-12-01",
            "assessment_date": "2026-12-01",
            "transitional_applicability": _transitional("ES", "2026-12-01"),
            "article_57_1_relief_result": duration is True and autonomous is False,
            "article_57_1_evidence": {
                "pertinent_period_refs": ["synthetic-period"],
                "total_duration": {"value": {"numerator": legal_duration[0], "denominator": legal_duration[1]}, "unit": "day", "legal_basis_refs": ["synthetic-art57-duration"]},
                "one_year_comparator": {"value": {"numerator": comparator_rational[0], "denominator": comparator_rational[1]}, "unit": "day", "legal_basis_refs": ["synthetic-art57-comparator"]},
                "applicable_legislation": {"id": "synthetic-legislation", "version": "synthetic-v1", "valid_from": "2020-01-01", "valid_to": None, "source_refs": ["synthetic-legislation-source"]},
                "autonomous_right_determination": {"result": autonomous if autonomous is not None else False, "national_rule_pack_id": "synthetic-national-pack", "national_rule_version": "synthetic-v1", "risk_materialization_date": "2026-12-01", "evidence_refs": ["synthetic-autonomous-evidence"]},
                "source_evidence_refs": ["synthetic-institutional-art57"],
            },
            "evidence_refs": ["synthetic-institutional-art57"],
        }],
        "institution_scope_evidence": {"manifest_ref": "synthetic-manifest", "case_ref": "synthetic-case", "coordinated_benefit_ref": "synthetic-coordinated-old-age", "contingency_date": "2026-12-01", "issuer_institution_ref": "synthetic-contact-institution", "as_of_date": "2026-12-01", "temporal_coverage_from": "2026-01-01", "temporal_coverage_to": "2026-12-31", "procedural_coverage_ref": "synthetic-procedural-scope", "institution_refs": ["synthetic-es"], "full_perimeter_status": "source_bound_full_perimeter", "operator_verification_status": "verified", "resolved_source_refs": ["synthetic-completeness-evidence"]},
        "evidence_registry": [{"evidence_id": "synthetic-completeness-evidence", "issuer_institution_ref": "synthetic-contact-institution", "content_utf8": "synthetic evidence é", "content_digest": "sha256:" + hashlib.sha256("synthetic evidence é".encode("utf-8")).hexdigest(), "coverage": {"manifest_ref": "synthetic-manifest", "case_ref": "synthetic-case", "coordinated_benefit_ref": "synthetic-coordinated-old-age", "contingency_date": "2026-12-01", "as_of_date": "2026-12-01", "temporal_coverage_from": "2026-01-01", "temporal_coverage_to": "2026-12-31", "procedural_coverage_ref": "synthetic-procedural-scope", "institution_refs": ["synthetic-es"]}, "verified": True}],
    }
    assessment["last_state_attestation"] = _last_state_attestation()
    assessment["evidence_registry"].extend(_last_state_registry_entries())
    return assessment


def _segment_id(preimage: dict) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(preimage, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def _last_state_attestation() -> dict:
    return {
        "manifest_ref": "synthetic-manifest", "case_ref": "synthetic-case", "coordinated_benefit_ref": "synthetic-coordinated-old-age", "contingency_date": "2026-12-01",
        "institution_ref": "synthetic-es", "member_state": "ES",
        "applicable_legislation": {"id": "synthetic-legislation", "version": "synthetic-v1", "valid_from": "2020-01-01", "valid_to": None, "source_refs": ["synthetic-legislation-source"]},
        "conditions_satisfied": True, "conditions_satisfied_on": "2026-11-01", "conditions_event_ref": "synthetic-condition-event",
        "candidate_institution_refs": ["synthetic-es"], "candidate_conditions_comparability_status": "verified_comparable", "last_state_selection_status": "operator_verified_unique_last_state",
        "selection_evidence_refs": ["synthetic-selection"], "conditions_evidence_refs": ["synthetic-conditions"], "comparability_evidence_refs": ["synthetic-comparability"], "institutional_record_evidence_refs": ["synthetic-institutional-art57"],
    }


def _last_state_registry_entries() -> list[dict]:
    coverage = {
        "manifest_ref": "synthetic-manifest", "case_ref": "synthetic-case",
        "coordinated_benefit_ref": "synthetic-coordinated-old-age", "contingency_date": "2026-12-01",
        "as_of_date": "2026-12-01", "temporal_coverage_from": "2020-01-01",
        "temporal_coverage_to": "2026-12-31", "procedural_coverage_ref": "synthetic-procedural-scope",
        "institution_refs": ["synthetic-es"], "applicable_legislation_valid_from": "2020-01-01",
        "applicable_legislation_valid_to": None,
    }
    entries = []
    for evidence_id in ("synthetic-selection", "synthetic-conditions", "synthetic-comparability", "synthetic-condition-event", "synthetic-legislation-source", "synthetic-institutional-art57"):
        content = f"synthetic {evidence_id}"
        entries.append({
            "evidence_id": evidence_id,
            "issuer_institution_ref": "synthetic-contact-institution",
            "content_utf8": content,
            "content_digest": "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "coverage": deepcopy(coverage),
            "verified": True,
        })
    return entries


def _transitional(member_state: str, risk_date: str) -> dict:
    return {
        "basic_regulation_883_87": {"member_state": member_state, "territorial_application_date": {"date": "2010-05-01", "legal_source_ref": "synthetic-883-87"}, "contingency_date": risk_date, "pre_application_period_refs": [], "result": "not_applicable", "evidence_refs": ["synthetic-transitional-evidence"], "data_gaps": []},
        "implementing_regulation_987_93": {"result": "not_applicable", "evidence_refs": ["synthetic-987-93"], "data_gaps": []},
        "regulation_465_2012_883_87a": {"title_ii_change_caused_by_465_2012": None, "legislation_before_change": None, "legislation_after_change": None, "relevant_situation_unchanged": None, "within_ten_year_limit": None, "opt_out_request_date": None, "opt_out_effective_date": None, "result": "not_applicable", "evidence_refs": ["synthetic-465-87a"], "data_gaps": []},
        "pension_transitional_987_94_1": {"benefits_due_for_pre_application_period": None, "contingency_pre_application": None, "claim_awarded_before_application_date": None, "prior_leg": None, "basic_regulation_leg": None, "comparison": "not_applicable", "preserved_result": "not_applicable", "result": "not_applicable", "data_gaps": []},
    }


def _period(country: str, start: str, end: str) -> dict:
    return {
        "country": country,
        "start_date": start,
        "end_date": end,
        "period_type": "compulsory",
        "source_document": f"synthetic-{country.lower()}-periods",
    }


if __name__ == "__main__":
    unittest.main()
