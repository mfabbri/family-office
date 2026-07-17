import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.pension_income import compose_pension_income


class PensionIncomeTest(unittest.TestCase):
    def test_inps_only_keeps_monthly_projection_without_annualizing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inps_path = _write_json(root / "inps.json", _inps_snapshot())
            output_path = root / "pension-income.json"

            result = compose_pension_income(inps_path, None, output_path)

            self.assertEqual(result["schema_version"], "pension-income/v1")
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["income_streams"][0]["stream_id"], "inps_public_pension")
            self.assertEqual(result["income_streams"][0]["gross"]["monthly_amount"], "3562.00")
            self.assertIsNone(result["summary"]["gross_annual_recurring_total"])
            self.assertIn(
                "inps_public_pension",
                result["summary"]["gross_annual_recurring_total_excluded_stream_ids"],
            )

    def test_inps_and_spain_remain_separate_with_only_explicit_annual_total(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inps_path = _write_json(root / "inps.json", _inps_snapshot(retirement_date="2039-05-01"))
            spanish_path = _write_json(root / "spain.json", _spanish_snapshot(retirement_date="2040-01"))
            output_path = root / "pension-income.json"

            result = compose_pension_income(inps_path, spanish_path, output_path)
            streams = {stream["stream_id"]: stream for stream in result["income_streams"]}

            self.assertEqual(set(streams), {"inps_public_pension", "spanish_public_pension"})
            self.assertEqual(streams["inps_public_pension"]["start_date"], "2039-05-01")
            self.assertEqual(streams["spanish_public_pension"]["start_date"], "2040-01")
            self.assertEqual(result["summary"]["gross_annual_recurring_total"], "21000.00")
            self.assertEqual(
                result["summary"]["gross_annual_recurring_total_included_stream_ids"],
                ["spanish_public_pension"],
            )

    def test_optional_rita_is_added_as_finite_bridge_not_recurring_total(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inps_path = _write_json(root / "inps.json", _inps_snapshot())
            rita_path = _write_json(root / "rita.json", _rita_snapshot())
            output_path = root / "pension-income.json"

            result = compose_pension_income(
                inps_path,
                None,
                output_path,
                rita_options_snapshot_path=rita_path,
            )
            rita_stream = next(stream for stream in result["income_streams"] if stream["benefit_type"] == "rita_bridge_income")

            self.assertEqual(rita_stream["gross"]["monthly_amount"], "2500.00")
            self.assertEqual(rita_stream["gross"]["duration_months"], 48)
            self.assertIn("rita_straight_line_gross_drawdown", result["summary"]["gross_annual_recurring_total_excluded_stream_ids"])

    def test_non_estimable_spanish_pension_creates_gap_without_amount(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            spanish_path = _write_json(
                root / "spain.json",
                _spanish_snapshot(status="blocked_missing_inputs", gross_pension=None),
            )
            output_path = root / "pension-income.json"

            result = compose_pension_income(None, spanish_path, output_path)

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertEqual(result["income_streams"], [])
            self.assertIn("spanish_pension_not_calculable", {gap["code"] for gap in result["data_gaps"]})


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _inps_snapshot(retirement_date: str = "2039-05-01") -> dict:
    return {
        "schema_version": "inps-pension/v1",
        "record_type": "InpsPensionSnapshot",
        "extraction_status": "extracted",
        "projection": {
            "retirement_date": retirement_date,
            "monthly_gross_pension": "3562.00",
            "prices_year": "2026",
        },
        "contribution_position": {
            "pension_contribution_weeks": "1040",
            "separate_management_weeks": "0",
        },
        "data_gaps": [],
    }


def _spanish_snapshot(
    status: str = "complete",
    gross_pension: dict | None = None,
    retirement_date: str = "2039-05",
) -> dict:
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
        "retirement_date": retirement_date,
        "gross_pension": gross_pension,
        "result_type": "internal_estimate",
        "confidence": "medium",
        "data_gaps": [{"code": "insufficient_base_reguladora_months"}] if status != "complete" else [],
    }


def _rita_snapshot() -> dict:
    return {
        "schema_version": "rita-options/v1",
        "record_type": "RitaOptionsSnapshot",
        "status": "complete",
        "eligibility": {"eligible": True},
        "options": [
            {
                "option_id": "straight_line_gross_drawdown",
                "duration_months": 48,
                "gross_monthly_amount": "2500.00",
                "gross_total_amount": "120000.00",
                "currency": "EUR",
            }
        ],
        "data_gaps": [],
    }


if __name__ == "__main__":
    unittest.main()
