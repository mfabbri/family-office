import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.earned_income_cashflow import build_earned_income_cashflow


def _payroll(records: list[dict]) -> dict:
    return {
        "record_type": "PayrollSnapshot",
        "schema_version": "payroll/v1",
        "records": records,
        "data_gaps": [],
    }


def _record(month: int, net_pay: str, employer: str = "ACME SRL") -> dict:
    return {
        "period_label": f"Mese {month} 2026",
        "period_year": 2026,
        "employer": employer,
        "net_pay": net_pay,
        "currency": "EUR",
        "confidence": "parsed_from_payslip_text",
        "source": {"filename": f"cedolino-{month}.pdf"},
    }


class EarnedIncomeCashflowTest(unittest.TestCase):
    def test_builds_observed_full_year_cashflow(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payroll_path = _write_json(
                root / "payroll.json",
                _payroll([_record(month, "2500.00") for month in range(1, 13)]),
            )
            output_path = root / "earned-income.json"

            result = build_earned_income_cashflow(payroll_path, output_path)

            self.assertEqual(result["schema_version"], "earned-income-cashflow/v1")
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["summary"]["latest_year_observed_net_pay"], "30000.00")
            self.assertEqual(result["summary"]["latest_year_annualized_net_pay"], "30000.00")
            self.assertEqual(result["summary"]["latest_year_annualization_method"], "observed_full_year")
            self.assertEqual(result["summary"]["confidence"], "observed")

    def test_annualizes_missing_months(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payroll_path = _write_json(
                root / "payroll.json",
                _payroll([_record(1, "2500.00"), _record(2, "2600.00")]),
            )

            result = build_earned_income_cashflow(payroll_path, root / "earned-income.json")

            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["summary"]["latest_year_observed_periods"], 2)
            self.assertEqual(result["summary"]["latest_year_observed_net_pay"], "5100.00")
            self.assertEqual(result["summary"]["latest_year_annualized_net_pay"], "30600.00")
            self.assertEqual(result["summary"]["confidence"], "annualized_from_partial_year")
            self.assertTrue(any(gap["code"] == "missing_payroll_periods" for gap in result["data_gaps"]))

    def test_keeps_extra_payroll_periods_for_thirteenth_fourteenth(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payroll_path = _write_json(
                root / "payroll.json",
                _payroll([_record(month, "2500.00") for month in range(1, 15)]),
            )

            result = build_earned_income_cashflow(payroll_path, root / "earned-income.json")

            self.assertEqual(result["summary"]["latest_year_observed_periods"], 14)
            self.assertEqual(result["summary"]["latest_year_observed_net_pay"], "35000.00")
            self.assertEqual(result["summary"]["latest_year_annualized_net_pay"], "35000.00")
            self.assertEqual(result["summary"]["confidence"], "observed_with_extra_periods")
            self.assertTrue(any(gap["code"] == "extra_payroll_periods" for gap in result["data_gaps"]))

    def test_reports_multiple_employers_and_excludes_duplicates(self):
        duplicate = _record(1, "2500.00")
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payroll_path = _write_json(
                root / "payroll.json",
                _payroll(
                    [
                        duplicate,
                        dict(duplicate),
                        _record(2, "1500.00", employer="OTHER SPA"),
                    ]
                ),
            )

            result = build_earned_income_cashflow(payroll_path, root / "earned-income.json")

            self.assertEqual(len(result["records"]), 2)
            self.assertTrue(
                any(gap["code"] == "duplicate_payroll_records_excluded" for gap in result["data_gaps"])
            )
            self.assertTrue(any(gap["code"] == "multiple_payroll_employers" for gap in result["data_gaps"]))

    def test_reports_manual_salary_superseded_by_payroll(self):
        assumptions = {
            "record_type": "ManualAssumptions",
            "assumptions": {
                "cashflow": {
                    "net_salary_monthly": 3000,
                    "salary_months": 12,
                }
            },
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payroll_path = _write_json(
                root / "payroll.json",
                _payroll([_record(month, "2500.00") for month in range(1, 13)]),
            )
            assumptions_path = _write_json(root / "manual-assumptions.json", assumptions)

            result = build_earned_income_cashflow(
                payroll_path,
                root / "earned-income.json",
                assumptions_path,
            )

            self.assertTrue(
                any(gap["code"] == "manual_salary_superseded_by_payroll" for gap in result["data_gaps"])
            )

    def test_blocks_when_payroll_has_no_net_pay(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payroll_path = _write_json(root / "payroll.json", _payroll([]))

            result = build_earned_income_cashflow(payroll_path, root / "earned-income.json")

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertIsNone(result["summary"])
            self.assertTrue(
                any(gap["code"] == "missing_payroll_net_pay_records" for gap in result["data_gaps"])
            )


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
