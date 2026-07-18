import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.services.decision_outcome import evaluate_decision_outcome

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

    def test_outcome_linked_analysis_reruns_variants_and_orders_by_metric_impact(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario_path = _write_json(root / "decision-scenario.json", _evaluator_ready_scenario())
            input_path = _write_json(root / "sensitivity-input.json", _outcome_linked_input())

            first = build_sensitivity_analysis(scenario_path, input_path, root / "sensitivity-1.json")
            copied_scenario = _write_json(root / "copied-scenario.json", _evaluator_ready_scenario())
            copied_input = _write_json(root / "copied-input.json", _outcome_linked_input())
            second = build_sensitivity_analysis(copied_scenario, copied_input, root / "sensitivity-2.json")

            self.assertEqual(first["status"], "complete")
            self.assertEqual(first["baseline_outcome"]["status"], "complete")
            self.assertEqual(first["outcome_evaluation"]["impact_metric_id"], "final_balance_p50")
            cases = {case["id"]: case for case in first["sensitivity_cases"]}
            return_delta = _metric_delta(cases["return_up"], "final_balance_p50")
            inflation_delta = _metric_delta(cases["inflation_up"], "final_balance_p50")
            self.assertNotEqual(return_delta["delta"], "0")
            self.assertEqual(inflation_delta["delta"], "0")
            self.assertEqual(
                [row["sensitivity_id"] for row in first["tornado_data"]],
                ["return_up", "inflation_up"],
            )
            self.assertEqual(first["tornado_data"][0]["impact_metric_id"], "final_balance_p50")
            self.assertEqual(first["reproducibility"]["content_hash"], second["reproducibility"]["content_hash"])

    def test_outcome_linked_stress_has_combined_outcome_and_deltas(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario_path = _write_json(root / "decision-scenario.json", _evaluator_ready_scenario())
            input_path = _write_json(root / "sensitivity-input.json", _outcome_linked_input())

            with patch(
                "family_office_engine.services.sensitivity_analysis.evaluate_decision_outcome",
                wraps=evaluate_decision_outcome,
            ) as evaluator:
                result = build_sensitivity_analysis(scenario_path, input_path, root / "sensitivity.json")

            stress = result["stress_matrix"][0]
            self.assertEqual(stress["status"], "complete")
            self.assertEqual(stress["outcome"]["status"], "complete")
            self.assertTrue(stress["metric_deltas"])
            self.assertEqual(stress["variant_assumptions"]["market"]["nominal_return"], "0.0315")
            self.assertEqual(evaluator.call_count, 4)

    def test_blocked_evaluator_produces_explicit_gaps_without_deltas(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario = _evaluator_ready_scenario()
            del scenario["assumptions"]["portfolio"]["starting_net_worth"]
            scenario_path = _write_json(root / "decision-scenario.json", scenario)
            input_path = _write_json(root / "sensitivity-input.json", _outcome_linked_input())

            result = build_sensitivity_analysis(scenario_path, input_path, root / "sensitivity.json")

            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["baseline_outcome"]["status"], "blocked_missing_inputs")
            self.assertEqual(result["tornado_data"], [])
            self.assertIn("outcome_evaluation_blocked", {gap["code"] for gap in result["data_gaps"]})
            self.assertIn("impact_metric_unavailable", {gap["code"] for gap in result["data_gaps"]})
            self.assertTrue(all(case["metric_deltas"] == [] for case in result["sensitivity_cases"]))


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


def _evaluator_ready_scenario() -> dict:
    scenario = _decision_scenario()
    scenario["assumptions"].update(
        {
            "personal": {"current_age": 60, "target_retirement_age": 64},
            "portfolio": {"starting_net_worth": "250000.00", "currency": "EUR"},
            "cashflow": {
                "family_expenses_yearly": "24000.00",
                "net_salary_monthly": "3000.00",
                "salary_months": 12,
                "retirement_income_yearly": "12000.00",
            },
        }
    )
    scenario["assumptions"]["market"]["nominal_volatility"] = "0.10"
    return scenario


def _outcome_linked_input() -> dict:
    data = _sensitivity_input()
    data["outcome_evaluation"] = {
        "schema_version": "decision-outcome/v1",
        "record_type": "DecisionOutcomeInput",
        "outcome_id": "synthetic-sensitivity-outcome",
        "label": "Synthetic sensitivity outcome",
        "evaluator_id": "retirement-monte-carlo/v1",
        "parameters": {"simulations": 25, "seed": 20260718, "end_age": 95},
        "impact_metric_id": "final_balance_p50",
    }
    return data


def _metric_delta(case: dict, metric_id: str) -> dict:
    return next(delta for delta in case["metric_deltas"] if delta["metric_id"] == metric_id)


if __name__ == "__main__":
    unittest.main()
