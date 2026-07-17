import json
import tempfile
import unittest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from family_office_engine.services.spanish_statutory_pension import (
    estimate_spanish_statutory_pension,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SPAIN_RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "spain" / "statutory-retirement-general.json"


class SpanishStatutoryPensionTest(unittest.TestCase):
    def test_estimates_complete_ordinary_pension_from_official_bases(self):
        result = self._estimate(_reconciliation(_months("2001-08", 304, "3000.00")), 2026)

        self.assertEqual(result["schema_version"], "spanish-statutory-pension/v1")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["result_type"], "internal_estimate")
        self.assertEqual(result["eligibility"]["status"], "eligible_by_encoded_rules")
        self.assertEqual(result["base_reguladora"]["selected_base_count"], 302)
        self.assertEqual(result["accrued_percentage"]["percentage"], "0.7454")

        expected_base = _money(Decimal("3000.00") * Decimal("302") / Decimal("352.33"))
        expected_monthly = _money(Decimal(expected_base) * Decimal("0.7454"))
        expected_annual = _money(Decimal(expected_monthly) * Decimal("14"))
        self.assertEqual(result["base_reguladora"]["amount"], expected_base)
        self.assertEqual(result["gross_pension"]["monthly_amount"], expected_monthly)
        self.assertEqual(result["gross_pension"]["annual_amount"], expected_annual)
        self.assertEqual(result["gross_pension"]["payments_per_year"], 14)

    def test_blocks_short_career_without_inventing_amounts(self):
        result = self._estimate(_reconciliation(_months("2020-01", 100, "2500.00")), 2026)

        self.assertEqual(result["status"], "blocked_missing_inputs")
        self.assertIsNone(result["gross_pension"])
        self.assertIn("insufficient_total_contribution_months", {gap["code"] for gap in result["data_gaps"]})

    def test_blocks_when_base_reguladora_window_lacks_official_bases(self):
        result = self._estimate(_reconciliation(_months("2001-08", 301, "3000.00")), 2026)

        self.assertEqual(result["status"], "blocked_missing_inputs")
        self.assertIn("insufficient_base_reguladora_months", {gap["code"] for gap in result["data_gaps"]})

    def test_uses_2027_transition_parameters(self):
        result = self._estimate(_reconciliation(_months("2001-12", 308, "3100.00")), 2027)

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["base_reguladora"]["parameters"]["lookback_months"], 308)
        self.assertEqual(result["base_reguladora"]["selected_base_count"], 304)
        self.assertEqual(result["ordinary_retirement_age"]["matched_rule"]["from_year"], 2027)

    def _estimate(self, reconciliation: dict, retirement_year: int) -> dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            reconciliation_path = root / "spanish-contribution-reconciliation.snapshot.json"
            output_path = root / "spanish-statutory-pension.snapshot.json"
            reconciliation_path.write_text(json.dumps(reconciliation), encoding="utf-8")

            result = estimate_spanish_statutory_pension(
                reconciliation_path,
                SPAIN_RULE_PACK,
                output_path,
                retirement_year,
            )

            self.assertTrue(output_path.exists())
            return result


def _reconciliation(months: list[dict]) -> dict:
    return {
        "schema_version": "spanish-contribution-reconciliation/v1",
        "record_type": "SpanishContributionReconciliationSnapshot",
        "status": "complete",
        "summary": {
            "covered_month_count": len(months),
            "usable_month_count": len(months),
            "data_gap_count": 0,
            "anomaly_count": 0,
        },
        "months": months,
        "data_gaps": [],
        "anomalies": [],
    }


def _months(start_month: str, count: int, amount: str) -> list[dict]:
    start_year, start_month_number = (int(part) for part in start_month.split("-"))
    months: list[dict] = []
    for offset in range(count):
        index = start_year * 12 + start_month_number - 1 + offset
        year = index // 12
        month = index % 12 + 1
        month_key = f"{year:04d}-{month:02d}"
        months.append(
            {
                "month": month_key,
                "covered_by_vida_laboral": True,
                "periods": [{"source_document": "synthetic-vida-laboral.txt"}],
                "official_bases": [{"base_amount": amount, "source_document": "synthetic-bases.csv"}],
                "payroll_bases": [],
                "selected_base": {
                    "month": month_key,
                    "base_amount": amount,
                    "currency": "EUR",
                    "source_type": "official_bases",
                    "confidence": "high",
                    "source_documents": ["synthetic-bases.csv"],
                    "component_count": 1,
                },
                "usable_for_estimator": True,
                "data_gap_codes": [],
                "anomaly_codes": [],
            }
        )
    return months


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


if __name__ == "__main__":
    unittest.main()
