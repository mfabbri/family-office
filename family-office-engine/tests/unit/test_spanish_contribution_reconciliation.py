import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.spanish_contribution_reconciliation import (
    SpanishContributionReconciliationError,
    reconcile_spanish_contributions,
)


def contribution_history(periods, monthly_bases):
    return {
        "schema_version": "spanish-contribution-history/v1",
        "record_type": "SpanishContributionHistorySnapshot",
        "periods": periods,
        "monthly_bases": monthly_bases,
        "data_gaps": [],
    }


def period(start, end="2024-03-31"):
    return {
        "start_date": start,
        "end_date": end,
        "regime": "GENERAL",
        "employer": "SYNTHETIC EMPLOYER SA",
        "source_document": "vida_laboral.pdf",
    }


def base(month, amount, source_type="official_bases", document="bases.pdf"):
    return {
        "month": month,
        "base_amount": amount,
        "currency": "EUR",
        "source_type": source_type,
        "confidence": "high" if source_type == "official_bases" else "medium",
        "source_document": document,
    }


class SpanishContributionReconciliationTest(unittest.TestCase):
    def test_reconcile_selects_official_base_over_payroll_and_reports_difference(self):
        result = self._reconcile(
            contribution_history(
                [period("2024-01-01", "2024-01-31")],
                [
                    base("2024-01", "2500.00", "official_bases", "official.pdf"),
                    base("2024-01", "2450.00", "payroll", "nomina.pdf"),
                ],
            )
        )

        self.assertEqual(result["schema_version"], "spanish-contribution-reconciliation/v1")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["months"][0]["selected_base"]["source_type"], "official_bases")
        self.assertEqual(result["months"][0]["selected_base"]["base_amount"], "2500.00")
        self.assertEqual(result["months"][0]["usable_for_estimator"], True)
        self.assertEqual(result["anomalies"][0]["code"], "payroll_official_base_difference")

    def test_reconcile_reports_period_without_base(self):
        result = self._reconcile(contribution_history([period("2024-01-01", "2024-02-29")], []))

        self.assertEqual(result["status"], "partial")
        gap_codes = [gap["code"] for gap in result["data_gaps"]]
        self.assertEqual(gap_codes.count("covered_month_without_base"), 2)
        self.assertFalse(any(month["usable_for_estimator"] for month in result["months"]))

    def test_reconcile_reports_base_without_period(self):
        result = self._reconcile(contribution_history([], [base("2024-01", "2500.00")]))

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["data_gaps"][0]["code"], "base_without_vida_laboral_period")
        self.assertFalse(result["months"][0]["usable_for_estimator"])

    def test_reconcile_payroll_only_is_gap_and_not_usable(self):
        result = self._reconcile(
            contribution_history(
                [period("2024-01-01", "2024-01-31")],
                [base("2024-01", "2450.00", "payroll", "nomina.pdf")],
            )
        )

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["months"][0]["selected_base"]["source_type"], "payroll")
        self.assertEqual(result["data_gaps"][0]["code"], "payroll_base_without_official_base")
        self.assertFalse(result["months"][0]["usable_for_estimator"])

    def test_reconcile_reports_multiple_official_bases_same_month(self):
        result = self._reconcile(
            contribution_history(
                [period("2024-01-01", "2024-01-31")],
                [
                    base("2024-01", "1000.00", "official_bases", "employer-a.pdf"),
                    base("2024-01", "1500.00", "official_bases", "employer-b.pdf"),
                ],
            )
        )

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["months"][0]["selected_base"]["base_amount"], "2500.00")
        self.assertEqual(result["anomalies"][0]["code"], "multiple_official_bases_same_month")

    def test_reconcile_rejects_wrong_schema(self):
        with self.assertRaisesRegex(SpanishContributionReconciliationError, "Unsupported"):
            self._reconcile({"schema_version": "wrong/v1"})

    def _reconcile(self, snapshot):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "history.json"
            output_path = root / "reconciliation.json"
            input_path.write_text(json.dumps(snapshot), encoding="utf-8")

            result = reconcile_spanish_contributions(input_path, output_path)

            self.assertTrue(output_path.exists())
            return result


if __name__ == "__main__":
    unittest.main()
