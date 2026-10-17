import json
import hashlib
import tempfile
import unittest
from pathlib import Path

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
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["spanish_entitlement"]["status"], "eligible_by_totalization")
        self.assertFalse(result["spanish_entitlement"]["autonomous"]["eligible"])
        self.assertTrue(result["spanish_entitlement"]["totalized"]["eligible"])
        self.assertEqual(result["periods"]["spain_months"], 60)
        self.assertEqual(result["periods"]["total_eu_non_overlapping_months"], 240)
        self.assertEqual(result["spanish_pro_rata_pension"]["ratio"]["value"], "0.250000")
        self.assertEqual(result["spanish_pro_rata_pension"]["amounts"]["monthly_gross_amount"], "500.00")
        self.assertEqual(result["spanish_pro_rata_pension"]["amounts"]["annual_gross_amount"], "6000.00")

    def test_keeps_autonomous_spanish_entitlement_distinct(self):
        result = self._build(_input([_period("ES", "2001-01-01", "2025-12-31")]))

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["spanish_entitlement"]["status"], "eligible_autonomous")
        self.assertTrue(result["spanish_entitlement"]["autonomous"]["eligible"])
        self.assertTrue(result["spanish_entitlement"]["totalized"]["eligible"])

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

        self.assertEqual(result["article_57"]["article_57_exception_status"], "applies")
        self.assertEqual(result["article_57"]["theoretical_amount_period_inclusion"], "required_by_57_2")
        self.assertEqual(result["article_57"]["national_payment_obligation_status"], "relieved_under_57_1")
        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_calculable")
        self.assertNotIn("threshold_months", str(result))

    def test_source_bound_duration_equal_or_greater_than_one_year_does_not_apply_article_57(self):
        payload = _input([_period("IT", "2006-01-01", "2024-12-31"), _period("ES", "2025-01-01", "2025-12-31")])
        payload["article_57_assessment"] = _article_57(duration=False, autonomous=False, annex=False)
        result = self._build(payload)

        self.assertEqual(result["spanish_entitlement"]["status"], "eligible_by_totalization")
        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "calculated")
        self.assertEqual(result["article_57"]["article_57_exception_status"], "does_not_apply")
        self.assertEqual(result["spanish_pro_rata_pension"]["ratio"]["spain_months"], 12)

        payload["article_57_assessment"] = _article_57(duration=False, autonomous=False, annex=False, legal_duration_days=366)
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "does_not_apply")

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

        self.assertEqual(result["article_57"]["article_57_exception_status"], "applies")

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
        self.assertEqual(result["article_57"]["article_57_exception_status"], "does_not_apply")
        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "calculated")

    def test_source_bound_autonomous_right_and_annex_are_independent_predicates(self):
        payload = _input([_period("IT", "2006-01-01", "2025-01-31"), _period("ES", "2025-02-01", "2025-12-31")])
        payload["article_57_assessment"] = _article_57(duration=True, autonomous=True, annex=False)
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "does_not_apply")

        payload["article_57_assessment"] = _article_57(duration=True, autonomous=False, annex=True)
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "excluded_by_57_4")

        payload["article_57_assessment"] = _article_57(duration=False, autonomous=False, annex=False)
        payload["article_57_assessment"]["annex_viii_part_2_applicability"].pop("annex_evidence_refs")
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertIn("missing_article_57_annex_viii_part_2_evidence", {gap["code"] for gap in result["data_gaps"]})

    def test_unknown_or_overlap_conversion_ambiguity_is_not_assessed(self):
        payload = _input([_period("IT", "2006-01-01", "2020-12-31"), _period("ES", "2020-01-01", "2025-12-31")])
        payload["article_57_assessment"] = _article_57(duration=None, autonomous=False, annex=False)
        result = self._build(payload)

        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertIn("missing_article_57_legal_duration", {gap["code"] for gap in result["data_gaps"]})

    def test_article_57_3_requires_last_state_evidence_and_legacy_contract_is_rejected(self):
        payload = _input([_period("IT", "2006-01-01", "2025-01-31"), _period("ES", "2025-02-01", "2025-12-31")])
        payload["article_57_assessment"] = _article_57(duration=True, autonomous=False, annex=False, all_relieved=True)
        result = self._build(payload)
        self.assertEqual(result["article_57"]["national_payment_obligation_status"], "not_assessed")
        self.assertIn("missing_article_57_3_last_state_evidence", {gap["code"] for gap in result["data_gaps"]})

        payload["article_57_assessment"]["contract_schema_version"] = "v0.16"
        payload["article_57_assessment"]["canonicalization_profile"] = "fo-art57-c14n-v3"
        with self.assertRaisesRegex(ItEsEuPensionProRataError, "legacy contracts"):
            self._build(payload)

    def test_article_57_rejects_c14n_mutation_and_uses_institutional_records_not_aggregate_boolean(self):
        payload = _input([])
        assessment = _article_57(True, False, False)
        assessment["duration_source_segment"]["preimage"]["source_bounds"][0]["native_duration"]["value"]["numerator"] = 363
        assessment["duration_source_segment"]["segment_id"] = _segment_id(assessment["duration_source_segment"]["preimage"])
        assessment["legal_duration_for_article_57"]["source_segment_id"] = assessment["duration_source_segment"]["segment_id"]
        payload["article_57_assessment"] = assessment
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertIn("invalid_article_57_duration_source_segment", {gap["code"] for gap in result["data_gaps"]})

        payload["article_57_assessment"] = _article_57(True, False, False, all_relieved=True)
        payload["article_57_assessment"]["all_concerned_institutions_relieved"] = False
        payload["article_57_assessment"].update({
            "article_57_3_last_state": "ES",
            "article_57_3_last_state_order": 1,
            "article_57_3_last_state_conditions_satisfied": True,
            "article_57_3_evidence_refs": ["synthetic-last-state"],
        })
        result = self._build(payload)
        self.assertEqual(result["article_57"]["national_payment_obligation_status"], "payer_under_57_3")

        payload["article_57_assessment"]["concerned_institutions"][0]["institution_order"] = 2
        result = self._build(payload)
        self.assertEqual(result["article_57"]["national_payment_obligation_status"], "not_assessed")
        self.assertIn("missing_article_57_3_last_state_evidence", {gap["code"] for gap in result["data_gaps"]})

    def test_article_57_root_dates_nfc_and_complete_institution_set_are_fail_closed(self):
        payload = _input([])
        assessment = _article_57(True, False, False, all_relieved=True)
        assessment.update({
            "article_57_3_last_state": "IT",
            "article_57_3_last_state_order": 2,
            "article_57_3_last_state_conditions_satisfied": True,
            "article_57_3_evidence_refs": ["synthetic-last-state"],
        })
        second = dict(assessment["concerned_institutions"][0])
        second.update({"institution_id": "synthetic-it", "member_state": "IT", "transitional_applicability": _transitional("IT", "2026-12-01"), "institution_order": 2})
        assessment["concerned_institutions"].append(second)
        assessment["concerned_institutions_complete"]["institution_ids"] = ["synthetic-es", "synthetic-it"]
        payload["article_57_assessment"] = assessment
        result = self._build(payload)
        self.assertEqual(result["article_57"]["national_payment_obligation_status"], "payer_under_57_3")

        assessment["concerned_institutions_complete"]["institution_ids"] = ["synthetic-es", "synthetic-unreported"]
        result = self._build(payload)
        self.assertEqual(result["article_57"]["national_payment_obligation_status"], "relieved_under_57_1")
        self.assertIn("missing_article_57_concerned_institutions_completeness", {gap["code"] for gap in result["data_gaps"]})

        assessment["concerned_institutions_complete"]["institution_ids"] = ["synthetic-es", "synthetic-it"]
        assessment["concerned_institutions_complete"] = {"result": None, "evidence_refs": ["synthetic-completeness-evidence"]}
        result = self._build(payload)
        self.assertEqual(result["article_57"]["national_payment_obligation_status"], "relieved_under_57_1")
        self.assertIn("missing_article_57_concerned_institutions_completeness", {gap["code"] for gap in result["data_gaps"]})

        assessment["concerned_institutions_complete"] = {"result": True, "evidence_refs": ["synthetic-completeness-evidence"]}
        assessment["assessment_date"] = "2026-02-30"
        with self.assertRaisesRegex(ItEsEuPensionProRataError, "ISO assessment_date"):
            self._build(payload)
        assessment["assessment_date"] = "2026-12-01"
        assessment["benefit_id"] = "synthetic-olde\u0301-age"
        with self.assertRaisesRegex(ItEsEuPensionProRataError, "canonical root"):
            self._build(payload)

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
        payload["article_57_assessment"]["annex_viii_part_2_applicability"]["annex_validity_or_applicability_date"] = "2026-12-02"
        result = self._build(payload)
        self.assertEqual(result["article_57"]["article_57_exception_status"], "not_assessed")
        self.assertIn("missing_article_57_annex_viii_part_2_evidence", {gap["code"] for gap in result["data_gaps"]})

        payload = _input([])
        assessment = _article_57(True, False, False)
        payload["article_57_assessment"] = assessment
        assessment.update({"article_57_3_last_state": "ES", "article_57_3_last_state_order": 1, "article_57_3_last_state_conditions_satisfied": True, "article_57_3_evidence_refs": ["synthetic-last-state"]})
        assessment["concerned_institutions"][0]["applicable_legislation_valid_to"] = "2026-11-30"
        result = self._build(payload)
        self.assertEqual(result["article_57"]["national_payment_obligation_status"], "not_assessed")
        self.assertIn("missing_article_57_multi_institution_evidence", {gap["code"] for gap in result["data_gaps"]})

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

        self.assertEqual(result["status"], "complete")
        self.assertNotIn("missing_spanish_theoretical_amount", {gap["code"] for gap in result["data_gaps"]})

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

    def _build(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "it-es-eu-pension-pro-rata-input.json"
            output_path = root / "it-es-eu-pension-pro-rata.snapshot.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")

            result = build_it_es_eu_pension_pro_rata(input_path, RULE_PACK, output_path)

            self.assertTrue(output_path.exists())
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
        "schema_version": "v0.17",
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
    return {
        "contract_schema_version": "v0.17",
        "canonicalization_profile": "fo-art57-c14n-v4",
        "human_review_required": True,
        "member_state": "ES",
        "benefit_id": "synthetic-old-age",
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
        "annex_viii_part_2_applicability": {
            "result": annex,
            "annex_consolidation_version": "reg-988-2009-2010-05-01",
            "annex_validity_or_applicability_date": "2026-12-01",
            "matched_scheme_entry": "synthetic-es-scheme",
            "scheme_match_status": "matched" if annex else "not_matched",
            "annex_evidence_refs": ["synthetic-annex-evidence"],
        },
        "concerned_institutions": [{
            "institution_id": "synthetic-es",
            "member_state": "ES",
            "benefit_id": "synthetic-old-age",
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
            "institution_order": 1,
            "institution_order_evidence_refs": ["synthetic-institution-order"],
            "article_57_1_relief_result": all_relieved,
            "evidence_refs": ["synthetic-institutional-art57"],
        }],
        "concerned_institutions_complete": {"result": True, "institution_ids": ["synthetic-es"], "evidence_refs": ["synthetic-completeness-evidence"]},
        "all_concerned_institutions_relieved": all_relieved,
    }


def _segment_id(preimage: dict) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(preimage, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


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
