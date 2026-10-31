import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.eu_pension_coordination import (
    EuPensionCoordinationError,
    coordinate_it_es_pensions,
    load_rule_pack,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "cross-border" / "eu-pension-coordination-it-es.json"


class EuPensionCoordinationTest(unittest.TestCase):
    def test_complete_dossier_keeps_national_entitlements_separate(self):
        result = self._coordinate(_inps_snapshot(), _spanish_snapshot(), italian_months=240)

        self.assertEqual(result["schema_version"], "eu-pension-coordination-it-es/v1")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["period_summary"]["total_eu_months"], 540)
        self.assertEqual(result["period_summary"]["ratios"]["IT"], "0.4444")
        self.assertEqual(result["period_summary"]["ratios"]["ES"], "0.5556")
        self.assertEqual([item["country"] for item in result["national_entitlements"]], ["IT", "ES"])
        self.assertTrue(result["coordination_principles"]["no_transfer_or_merger_of_contributions"])
        self.assertTrue(result["coordination_principles"]["aggregation_for_entitlement_and_theoretical_calculation"])
        self.assertNotIn("separate_payment_by_country", result["coordination_principles"])
        self.assertTrue(result["coordination_principles"]["payment_obligation_not_assessed_without_article_57_evidence"])
        self.assertEqual(result["rule_pack"]["schema_version"], "eu-pension-coordination-rule-pack/v2")
        self.assertEqual(result["pro_rata_diagnostics"]["countries"][0]["pro_rata_status"], "not_calculable")
        self.assertIn("entitlement and theoretical/pro-rata calculation", result["notes"])

    def test_missing_italian_normalized_months_is_partial_gap(self):
        result = self._coordinate(_inps_snapshot(), _spanish_snapshot(), italian_months=None)

        self.assertEqual(result["status"], "partial")
        self.assertIn("missing_italian_periods_normalized_months", {gap["code"] for gap in result["data_gaps"]})
        self.assertEqual(result["period_summary"]["status"], "not_normalized")

    def test_blocked_spanish_pension_stays_separate(self):
        spanish = _spanish_snapshot(status="blocked_missing_inputs", gross_pension=None)

        result = self._coordinate(_inps_snapshot(), spanish, italian_months=240)

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["national_entitlements"][1]["country"], "ES")
        self.assertEqual(result["national_entitlements"][1]["status"], "not_calculable")
        self.assertIn("spanish_pension_not_calculable", {gap["code"] for gap in result["data_gaps"]})

    def test_out_of_period_candidate_dates_cannot_produce_complete_dossier(self):
        inps = _inps_snapshot()
        inps["projection"]["retirement_date"] = "2039-05-01"
        spanish = _spanish_snapshot()
        spanish["retirement_date"] = "2039-05"

        result = self._coordinate(inps, spanish, italian_months=240)

        self.assertEqual(result["status"], "partial")
        outside_gaps = [gap for gap in result["data_gaps"] if gap["code"] == "retirement_date_outside_rule_pack_period"]
        self.assertEqual(len(outside_gaps), 2)
        self.assertEqual({gap["country"] for gap in outside_gaps}, {"IT", "ES"})
        self.assertEqual(
            {item["status"] for item in result["national_entitlements"]},
            {"not_assessed_rule_pack_period"},
        )
        self.assertEqual(result["rule_pack"]["valid_from"], "2026-01-01")
        self.assertEqual(result["rule_pack"]["valid_to"], "2026-12-31")

    def test_missing_candidate_date_blocks_complete_dossier(self):
        inps = _inps_snapshot()
        inps["projection"].pop("retirement_date")
        spanish = _spanish_snapshot()
        spanish.pop("retirement_date")

        result = self._coordinate(inps, spanish, italian_months=240)

        self.assertEqual(result["status"], "partial")
        self.assertEqual(
            {gap["code"] for gap in result["data_gaps"]},
            {"missing_or_invalid_retirement_date_for_rule_pack_period"},
        )
        self.assertEqual(
            {item["status"] for item in result["national_entitlements"]},
            {"not_assessed_rule_pack_period"},
        )

    def test_rejects_rule_pack_without_official_source(self):
        broken = json.loads(RULE_PACK.read_text(encoding="utf-8"))
        broken["source_refs"][0]["url"] = "https://example.com/not-official"
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "rules.json"
            path.write_text(json.dumps(broken), encoding="utf-8")

            with self.assertRaisesRegex(EuPensionCoordinationError, "official EU or Spanish URL"):
                load_rule_pack(path)

    def test_rejects_removed_article_57_under_one_year_section(self):
        broken = json.loads(RULE_PACK.read_text(encoding="utf-8"))
        pro_rata_method = broken["pro_rata_method"]
        pro_rata_method.pop("article_57_source_bound")
        pro_rata_method["article_57_under_one_year"] = {"threshold_months": 12}
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "rules.json"
            path.write_text(json.dumps(broken), encoding="utf-8")

            with self.assertRaisesRegex(EuPensionCoordinationError, "article_57_source_bound"):
                load_rule_pack(path)

    def test_requires_reviewed_v024_article_57_contract(self):
        broken = json.loads(RULE_PACK.read_text(encoding="utf-8"))
        broken["pro_rata_method"]["article_57_source_bound"]["contract_schema_version"] = "v0.22"
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "rules.json"
            path.write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaisesRegex(EuPensionCoordinationError, "v0.25/fo-art57-c14n-v4"):
                load_rule_pack(path)

    def test_rejects_annex_version_or_date_missing_from_rule_pack(self):
        for field, value in (("applicable_annex_part_2_version", ""), ("applicable_annex_part_2_valid_from", "2026-13-01")):
            broken = json.loads(RULE_PACK.read_text(encoding="utf-8"))
            broken["pro_rata_method"]["article_57_source_bound"]["annex_viii_part_2"][field] = value
            with tempfile.TemporaryDirectory() as tmp_dir:
                path = Path(tmp_dir) / "rules.json"
                path.write_text(json.dumps(broken), encoding="utf-8")
                with self.assertRaisesRegex(EuPensionCoordinationError, "Annex VIII"):
                    load_rule_pack(path)

    def _coordinate(self, inps: dict, spanish: dict, italian_months: int | None) -> dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inps_path = root / "inps-pension.snapshot.json"
            spanish_path = root / "spanish-statutory-pension.snapshot.json"
            output_path = root / "eu-pension-coordination-it-es.snapshot.json"
            inps_path.write_text(json.dumps(inps), encoding="utf-8")
            spanish_path.write_text(json.dumps(spanish), encoding="utf-8")

            result = coordinate_it_es_pensions(
                inps_path,
                spanish_path,
                RULE_PACK,
                output_path,
                italian_months,
            )

            self.assertTrue(output_path.exists())
            return result


def _inps_snapshot() -> dict:
    return {
        "schema_version": "inps-pension/v1",
        "record_type": "InpsPensionSnapshot",
        "extraction_status": "extracted",
        "projection": {
            "retirement_date": "2026-05-01",
            "monthly_gross_pension": "3562.00",
            "prices_year": "2026",
        },
        "contribution_position": {
            "pension_contribution_weeks": "1040",
            "separate_management_weeks": "0",
        },
        "data_gaps": [],
    }


def _spanish_snapshot(status: str = "complete", gross_pension: dict | None = None) -> dict:
    if gross_pension is None and status == "complete":
        gross_pension = {
            "monthly_amount": "1500.00",
            "annual_amount": "21000.00",
            "currency": "EUR",
            "payments_per_year": 14,
        }
    return {
        "schema_version": "spanish-statutory-pension/v1",
        "record_type": "SpanishStatutoryPensionEstimate",
        "status": status,
        "retirement_date": "2026-05",
        "eligibility": {
            "contribution_months": 300,
            "status": "eligible_by_encoded_rules",
        },
        "gross_pension": gross_pension,
        "data_gaps": [] if status == "complete" else [{"code": "insufficient_base_reguladora_months"}],
    }


if __name__ == "__main__":
    unittest.main()
