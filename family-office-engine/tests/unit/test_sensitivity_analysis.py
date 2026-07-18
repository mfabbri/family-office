import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.sensitivity_analysis import (
    SensitivityAnalysisError,
    build_sensitivity_analysis,
)


class SensitivityAnalysisTest(unittest.TestCase):
    def test_build_sensitivity_analysis_with_stable_hash_and_tornado_order(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario_path = _write_json(root / "decision-scenario.json", _decision_scenario())
            input_path = _write_json(root / "sensitivity-input.json", _sensitivity_input())

            first = build_sensitivity_analysis(scenario_path, input_path, root / "sensitivity-1.json")
            second = build_sensitivity_analysis(scenario_path, input_path, root / "sensitivity-2.json")

            self.assertEqual(first["schema_version"], "sensitivity-analysis/v1")
            self.assertEqual(first["record_type"], "SensitivityAnalysisSnapshot")
            self.assertEqual(first["status"], "complete")
            self.assertEqual([row["sensitivity_id"] for row in first["tornado_data"]], ["return_up", "inflation_up"])
            self.assertEqual(first["sensitivity_cases"][0]["path"], "assumptions.market.inflation")
            self.assertEqual(first["reproducibility"]["content_hash"], second["reproducibility"]["content_hash"])

    def test_stress_matrix_combines_multiple_perturbations(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario_path = _write_json(root / "decision-scenario.json", _decision_scenario())
            input_path = _write_json(root / "sensitivity-input.json", _sensitivity_input())

            result = build_sensitivity_analysis(scenario_path, input_path, root / "sensitivity.json")

            stress = result["stress_matrix"][0]
            self.assertEqual(stress["status"], "complete")
            self.assertEqual(stress["variant_assumptions"]["market"]["nominal_return"], "0.0315")
            self.assertEqual(stress["variant_assumptions"]["market"]["inflation"], "0.03")

    def test_missing_path_creates_gap_without_defaulting_value(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario_path = _write_json(root / "decision-scenario.json", _decision_scenario())
            sensitivity_input = _sensitivity_input()
            sensitivity_input["sensitivities"].append(
                {
                    "id": "missing_tax_rate",
                    "label": "Missing tax rate",
                    "domain": "tax",
                    "path": ["assumptions", "tax", "effective_rate"],
                    "operation": "absolute",
                    "delta": "0.01",
                }
            )
            input_path = _write_json(root / "sensitivity-input.json", sensitivity_input)

            result = build_sensitivity_analysis(scenario_path, input_path, root / "sensitivity.json")

            self.assertEqual(result["status"], "partial")
            self.assertIn("sensitivity_not_applied", {gap["code"] for gap in result["data_gaps"]})
            missing_case = next(case for case in result["sensitivity_cases"] if case["id"] == "missing_tax_rate")
            self.assertEqual(missing_case["status"], "partial")
            self.assertIsNone(missing_case["changed_value"])

    def test_source_scenario_gaps_are_carried_into_analysis(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario = _decision_scenario()
            scenario["data_gaps"] = [{"code": "missing_lifecycle_expenses_snapshot"}]
            scenario_path = _write_json(root / "decision-scenario.json", scenario)
            input_path = _write_json(root / "sensitivity-input.json", _sensitivity_input())

            result = build_sensitivity_analysis(scenario_path, input_path, root / "sensitivity.json")

            self.assertEqual(result["status"], "partial")
            self.assertIn("decision_scenario", {gap.get("source") for gap in result["data_gaps"]})

    def test_rejects_wrong_decision_scenario_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario_path = _write_json(root / "decision-scenario.json", {"schema_version": "wrong/v1"})
            input_path = _write_json(root / "sensitivity-input.json", _sensitivity_input())

            with self.assertRaisesRegex(SensitivityAnalysisError, "Unsupported decision scenario schema"):
                build_sensitivity_analysis(scenario_path, input_path, root / "sensitivity.json")


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _decision_scenario() -> dict:
    return {
        "schema_version": "decision-scenario/v2",
        "record_type": "DecisionScenarioSnapshot",
        "status": "complete",
        "scenario_id": "synthetic_base_case",
        "label": "Synthetic base case",
        "as_of_date": "2026-07-18",
        "assumptions": {
            "market": {"nominal_return": "0.03", "inflation": "0.02"},
            "withdrawal_policy": {"policy_id": "fixed_real_need"},
        },
        "data_gaps": [],
        "reproducibility": {"content_hash": "synthetic-hash"},
    }


def _sensitivity_input() -> dict:
    return {
        "schema_version": "sensitivity-analysis/v1",
        "record_type": "SensitivityAnalysisInput",
        "analysis_id": "synthetic_sensitivity",
        "label": "Synthetic sensitivity analysis",
        "as_of_date": "2026-07-18",
        "seed": 20260718,
        "sensitivities": [
            {
                "id": "inflation_up",
                "label": "Inflation +1pp",
                "domain": "inflation",
                "path": ["assumptions", "market", "inflation"],
                "operation": "absolute",
                "delta": "0.01",
            },
            {
                "id": "return_up",
                "label": "Nominal return +5%",
                "domain": "returns",
                "path": ["assumptions", "market", "nominal_return"],
                "operation": "relative",
                "delta": "0.05",
            },
        ],
        "stress_scenarios": [
            {
                "id": "market_upside",
                "label": "Market upside",
                "sensitivity_ids": ["return_up", "inflation_up"],
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
