import copy
import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.decision_outcome import (
    DecisionOutcomeError,
    build_decision_outcome,
)


class DecisionOutcomeTest(unittest.TestCase):
    def test_evaluator_calculates_metrics_with_lineage_and_stable_hash(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario_path = _write_json(root / "scenario.json", _scenario())
            input_path = _write_json(root / "outcome-input.json", _outcome_input())

            first = build_decision_outcome(scenario_path, input_path, root / "outcome-1.json")
            second = build_decision_outcome(scenario_path, input_path, root / "outcome-2.json")
            copied_scenario_path = _write_json(root / "copied-scenario.json", _scenario())
            copied_input_path = _write_json(root / "copied-outcome-input.json", _outcome_input())
            copied = build_decision_outcome(copied_scenario_path, copied_input_path, root / "outcome-3.json")

            self.assertEqual(first["schema_version"], "decision-outcome/v1")
            self.assertEqual(first["record_type"], "DecisionOutcomeSnapshot")
            self.assertEqual(first["status"], "complete")
            self.assertEqual(first["metrics"], second["metrics"])
            self.assertEqual(first["reproducibility"]["content_hash"], second["reproducibility"]["content_hash"])
            self.assertEqual(first["reproducibility"]["content_hash"], copied["reproducibility"]["content_hash"])
            metrics = {metric["metric_id"]: metric for metric in first["metrics"]}
            self.assertIn("success_rate", metrics)
            self.assertIn("final_balance_p50", metrics)
            self.assertEqual(metrics["retirement_income_yearly"]["value"], "12000.00")
            for metric in first["metrics"]:
                self.assertEqual(metric["provenance"]["scenario_content_hash"], "scenario-hash-1")
                self.assertEqual(metric["provenance"]["evaluator_id"], "retirement-monte-carlo/v1")
                self.assertEqual(metric["provenance"]["seed"], 1234)

    def test_missing_scenario_inputs_block_without_metrics(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario = _scenario()
            del scenario["assumptions"]["portfolio"]["starting_net_worth"]
            scenario["status"] = "partial"
            scenario_path = _write_json(root / "scenario.json", scenario)
            input_path = _write_json(root / "outcome-input.json", _outcome_input())

            result = build_decision_outcome(scenario_path, input_path, root / "outcome.json")

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertEqual(result["metrics"], [])
            self.assertIn("missing_evaluator_input", {gap["code"] for gap in result["data_gaps"]})

    def test_source_gaps_are_explicit_while_supported_metrics_are_calculated(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario = _scenario()
            scenario["status"] = "partial"
            scenario["data_gaps"] = [{"code": "missing_optional_source", "message": "Synthetic gap."}]
            scenario_path = _write_json(root / "scenario.json", scenario)
            input_path = _write_json(root / "outcome-input.json", _outcome_input())

            result = build_decision_outcome(scenario_path, input_path, root / "outcome.json")

            self.assertEqual(result["status"], "partial")
            self.assertTrue(result["metrics"])
            self.assertEqual(result["data_gaps"][0]["source"], "decision_scenario")

    def test_rejects_unsupported_evaluator(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario_path = _write_json(root / "scenario.json", _scenario())
            outcome_input = _outcome_input()
            outcome_input["evaluator_id"] = "unknown/v1"
            input_path = _write_json(root / "outcome-input.json", outcome_input)

            with self.assertRaisesRegex(DecisionOutcomeError, "Unsupported deterministic evaluator"):
                build_decision_outcome(scenario_path, input_path, root / "outcome.json")

    def test_rejects_unsupported_scenario_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario = _scenario()
            scenario["schema_version"] = "decision-scenario/v1"
            scenario_path = _write_json(root / "scenario.json", scenario)
            input_path = _write_json(root / "outcome-input.json", _outcome_input())

            with self.assertRaisesRegex(DecisionOutcomeError, "Unsupported decision scenario snapshot schema"):
                build_decision_outcome(scenario_path, input_path, root / "outcome.json")


def _scenario() -> dict:
    return {
        "schema_version": "decision-scenario/v2",
        "record_type": "DecisionScenarioSnapshot",
        "status": "complete",
        "scenario_id": "synthetic-retirement",
        "assumptions": {
            "personal": {"current_age": 60, "target_retirement_age": 64},
            "portfolio": {"starting_net_worth": "250000.00", "currency": "EUR"},
            "cashflow": {
                "family_expenses_yearly": "24000.00",
                "net_salary_monthly": "3000.00",
                "salary_months": 12,
                "retirement_income_yearly": "12000.00",
            },
            "market": {"nominal_return": "0.03", "nominal_volatility": "0.10"},
        },
        "data_gaps": [],
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": "scenario-hash-1"},
    }


def _outcome_input() -> dict:
    return {
        "schema_version": "decision-outcome/v1",
        "record_type": "DecisionOutcomeInput",
        "outcome_id": "synthetic-outcome",
        "label": "Synthetic outcome",
        "evaluator_id": "retirement-monte-carlo/v1",
        "parameters": {"simulations": 25, "seed": 1234, "end_age": 95},
    }


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(copy.deepcopy(data)), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
