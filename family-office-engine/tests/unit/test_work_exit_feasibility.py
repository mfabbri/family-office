import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.work_exit_feasibility import (
    WorkExitFeasibilityError,
    build_work_exit_feasibility,
)


RULE_PACK = Path(__file__).resolve().parents[2].parent / "family-office-rules" / "italy" / "2026" / "inps-theoretical-pension.json"


class WorkExitFeasibilityTest(unittest.TestCase):
    def test_finds_2039_after_discarding_2037(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            result = build_work_exit_feasibility(
                _write_json(root / "input.json", _input()),
                RULE_PACK,
                root / "work-exit.json",
                pro_rata_snapshot_path=_write_json(root / "pro-rata.json", _pro_rata()),
            )

            self.assertEqual(result["schema_version"], "work-exit-feasibility/v1")
            self.assertEqual(result["first_sustainable_exit_date"], "2039-01-01")
            self.assertEqual(result["candidate_dates"][0]["status"], "not_sustainable")
            self.assertIn("terminal_assets_below_minimum", result["candidate_dates"][0]["failure_reasons"])
            self.assertEqual(result["candidate_dates"][1]["status"], "sustainable")
            self.assertIn(
                "spanish_eu_pro_rata",
                {stream["source_type"] for stream in result["candidate_dates"][1]["gross_pension_streams"]},
            )

    def test_no_sustainable_date_is_blocked_with_reasons(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            data = _input()
            data["sustainability_constraints"]["available_bridge_assets"] = "0.00"
            data["sustainability_constraints"]["annual_spending_need"] = "110000.00"

            result = build_work_exit_feasibility(_write_json(root / "input.json", data), RULE_PACK, root / "out.json")

            self.assertEqual(result["status"], "blocked_no_sustainable_date")
            self.assertIsNone(result["first_sustainable_exit_date"])
            self.assertTrue(result["discarded_dates"])

    def test_documentary_inps_projection_is_kept_as_benchmark(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            result = build_work_exit_feasibility(
                _write_json(root / "input.json", _input()),
                RULE_PACK,
                root / "out.json",
                inps_snapshot_path=_write_json(root / "inps.json", _inps_snapshot()),
            )

            streams = result["candidate_dates"][1]["gross_pension_streams"]
            benchmark = next(stream for stream in streams if stream["source_type"] == "documentary_inps_projection_benchmark")

            self.assertEqual(benchmark["annual_gross_amount"], "55900.00")
            self.assertIsNotNone(benchmark["benchmark_difference_vs_internal_estimate"])

    def test_missing_spouse_pension_blocks_candidate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            data = _input()
            data["adults"][1].pop("declared_pension_streams")

            result = build_work_exit_feasibility(_write_json(root / "input.json", data), RULE_PACK, root / "out.json")

            self.assertIn("missing_spouse_pension_stream", {gap["code"] for gap in result["candidate_dates"][0]["data_gaps"]})
            self.assertEqual(result["first_sustainable_exit_date"], None)

    def test_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            data = _input()
            data["schema_version"] = "wrong/v1"

            with self.assertRaisesRegex(WorkExitFeasibilityError, "Unsupported work-exit"):
                build_work_exit_feasibility(_write_json(root / "input.json", data), RULE_PACK, root / "out.json")


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _input() -> dict:
    return {
        "schema_version": "work-exit-feasibility-input/v1",
        "record_type": "WorkExitFeasibilityInput",
        "household_id": "synthetic_household",
        "as_of_date": "2026-07-29",
        "candidate_dates": ["2037-01-01", "2039-01-01"],
        "sustainability_constraints": {
            "annual_spending_need": "90000.00",
            "available_bridge_assets": "10000.00",
            "minimum_terminal_assets": "0.00",
            "horizon_years": 30,
        },
        "adults": [
            {
                "person_id": "primary",
                "role": "primary",
                "date_of_birth": "1970-05-20",
                "inps_contributory_estimate": {
                    "calculation_scope": "contributory_only",
                    "as_of_year": 2026,
                    "historical_montante": "520000.00",
                    "annual_revaluation_rate": "0.0150",
                    "future_contributions": {
                        "annual_taxable_income": "95000.00",
                        "computation_rate": "0.33",
                        "through_year": 2039,
                    },
                },
            },
            {
                "person_id": "spouse",
                "role": "spouse",
                "date_of_birth": "1972-03-10",
                "inps_contributory_estimate": {
                    "calculation_scope": "contributory_only",
                    "as_of_year": 2026,
                    "historical_montante": "180000.00",
                    "annual_revaluation_rate": "0.0150",
                    "future_contributions": {
                        "annual_taxable_income": "32000.00",
                        "computation_rate": "0.33",
                        "through_year": 2039,
                    },
                },
                "declared_pension_streams": [
                    {
                        "source_type": "declared_spouse_private_pension",
                        "country": "IT",
                        "payer": "Declared spouse pension",
                        "start_date": "2039-01-01",
                        "annual_gross_amount": "9000.00",
                    }
                ],
            },
        ],
    }


def _pro_rata() -> dict:
    return {
        "schema_version": "it-es-eu-pension-pro-rata/v1",
        "record_type": "ItEsEuPensionProRataEstimate",
        "status": "complete",
        "retirement_date": "2039-01-01",
        "spanish_pro_rata_pension": {
            "status": "estimated",
            "monthly_gross_amount": "420.00",
            "annual_gross_amount": "5880.00",
            "payments_per_year": 14,
            "currency": "EUR",
        },
        "data_gaps": [],
    }


def _inps_snapshot() -> dict:
    return {
        "schema_version": "inps-pension/v1",
        "record_type": "InpsPensionSnapshot",
        "extraction_status": "extracted",
        "projection": {
            "retirement_date": "2039-01-01",
            "monthly_gross_pension": "4300.00",
        },
        "contribution_position": {},
        "data_gaps": [],
    }


if __name__ == "__main__":
    unittest.main()
