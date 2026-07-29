import json
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

    def test_counts_overlapping_it_es_month_once_in_eu_denominator(self):
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
        self.assertIn("overlapping_periods_removed_from_total", {warning["code"] for warning in result["warnings"]})

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
        "inps_history_status": "complete_dated_history",
        "future_assumptions_status": "explicit",
        "sources": [{"source_id": "synthetic-case", "type": "synthetic_fixture"}],
        "insurance_periods": periods,
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
