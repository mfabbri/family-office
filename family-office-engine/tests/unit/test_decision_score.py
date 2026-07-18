import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.decision_score import DecisionScoreError, build_decision_score


class DecisionScoreTest(unittest.TestCase):
    def test_build_decision_score_with_stable_hash_and_metric_scores(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)

            first = _score(root, paths, _scoring_input(), "score-1.json")
            second = _score(root, paths, _scoring_input(), "score-2.json")

            self.assertEqual(first["schema_version"], "decision-score/v1")
            self.assertEqual(first["record_type"], "DecisionScoreSnapshot")
            self.assertEqual(first["status"], "complete")
            self.assertEqual(first["ranking"][0]["alternative_id"], "balanced")
            self.assertEqual(first["alternatives"][0]["metrics"][0]["metric_id"], "final_wealth")
            self.assertEqual(first["reproducibility"]["content_hash"], second["reproducibility"]["content_hash"])

    def test_changing_weights_can_change_ranking(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            score_input = _scoring_input()
            score_input["weights"] = {"final_wealth": "0.9", "sustainability": "0.1"}

            result = _score(root, paths, score_input, "score.json")

            self.assertEqual(result["ranking"][0]["alternative_id"], "aggressive")

    def test_ties_share_rank_with_stable_order(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            score_input = _scoring_input()
            score_input["alternatives"][1]["outcome_ref"] = dict(score_input["alternatives"][0]["outcome_ref"])

            result = _score(root, paths, score_input, "score.json")

            self.assertEqual([row["rank"] for row in result["ranking"]], [1, 1])
            self.assertEqual([row["alternative_id"] for row in result["ranking"]], ["aggressive", "balanced"])

    def test_missing_metric_creates_gap_and_excludes_from_ranking(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            score_input = _scoring_input()
            score_input["alternatives"][0]["metrics"].pop("final_wealth")

            result = _score(root, paths, score_input, "score.json")

            self.assertEqual(result["status"], "partial")
            self.assertIn("missing_alternative_metric", {gap["code"] for gap in result["data_gaps"]})
            self.assertEqual(result["alternatives"][0]["status"], "partial")
            self.assertEqual([row["alternative_id"] for row in result["ranking"]], ["balanced"])

    def test_manual_metric_without_outcome_lineage_is_blocking(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            score_input = _scoring_input()
            score_input["alternatives"][0]["metrics"]["final_wealth"] = "700000"

            result = _score(root, paths, score_input, "score.json")

            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["lineage_status"], "incomplete")
            self.assertIn("metric_provenance_missing", {gap["code"] for gap in result["data_gaps"]})
            self.assertTrue(next(gap for gap in result["data_gaps"] if gap["code"] == "metric_provenance_missing")["blocking"])

    def test_missing_outcome_reference_is_blocking(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            score_input = _scoring_input()
            score_input["alternatives"][0]["outcome_ref"] = {"kind": "stress", "id": "missing"}

            result = _score(root, paths, score_input, "score.json")

            self.assertEqual(result["status"], "partial")
            self.assertIn("outcome_reference_unavailable", {gap["code"] for gap in result["data_gaps"]})

    def test_unsupported_weight_metric_creates_gap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            score_input = _scoring_input()
            score_input["weights"]["unsupported_metric"] = "0.1"

            result = _score(root, paths, score_input, "score.json")

            self.assertEqual(result["status"], "partial")
            self.assertIn("unsupported_weight_metric", {gap["code"] for gap in result["data_gaps"]})

    def test_rejects_wrong_source_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            paths["decision_scenario"] = _write_json(root / "wrong-scenario.json", {"schema_version": "wrong/v1"})

            with self.assertRaisesRegex(DecisionScoreError, "Unsupported decision scenario snapshot schema"):
                _score(root, paths, _scoring_input(), "score.json")


def _score(root: Path, paths: dict[str, Path], score_input: dict, filename: str) -> dict:
    input_path = _write_json(root / "decision-score-input.json", score_input)
    return build_decision_score(
        paths["decision_scenario"],
        paths["sensitivity_analysis"],
        input_path,
        paths["policy"],
        root / filename,
    )


def _write_sources(root: Path) -> dict[str, Path]:
    return {
        "decision_scenario": _write_json(root / "decision-scenario.json", _decision_scenario()),
        "sensitivity_analysis": _write_json(root / "sensitivity-analysis.json", _sensitivity_analysis()),
        "policy": _write_json(root / "score-policy.json", _score_policy()),
    }


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
        "data_gaps": [],
    }


def _sensitivity_analysis() -> dict:
    return {
        "schema_version": "sensitivity-analysis/v1",
        "record_type": "SensitivityAnalysisSnapshot",
        "status": "complete",
        "analysis_id": "synthetic_sensitivity",
        "baseline_outcome": _outcome("baseline", "0.90", "500000.00", "synthetic_base_case"),
        "sensitivity_cases": [
            {
                "id": "return_up",
                "status": "complete",
                "outcome": _outcome("return-up", "0.70", "800000.00", "synthetic_base_case::return_up"),
            }
        ],
        "stress_matrix": [],
        "data_gaps": [],
        "reproducibility": {"content_hash": "sensitivity-hash"},
    }


def _outcome(outcome_id: str, success_rate: str, final_balance: str, scenario_id: str) -> dict:
    provenance = {
        "scenario_id": scenario_id,
        "scenario_content_hash": f"{scenario_id}-hash",
        "evaluator_id": "retirement-monte-carlo/v1",
        "evaluator_version": "v1",
        "seed": 20260718,
    }
    return {
        "schema_version": "decision-outcome/v1",
        "record_type": "DecisionOutcomeSnapshot",
        "status": "complete",
        "outcome_id": outcome_id,
        "evaluator": {
            "evaluator_id": "retirement-monte-carlo/v1",
            "version": "v1",
            "parameters": {"simulations": 25, "seed": 20260718, "end_age": 95},
        },
        "metrics": [
            {"metric_id": "success_rate", "value": success_rate, "unit": "ratio", "provenance": provenance},
            {"metric_id": "final_balance_p50", "value": final_balance, "unit": "EUR", "provenance": provenance},
        ],
        "data_gaps": [],
        "reproducibility": {"content_hash": f"{outcome_id}-hash"},
    }


def _score_policy() -> dict:
    return {
        "schema_version": "decision-score-policy/v1",
        "record_type": "DecisionScorePolicy",
        "policy_id": "decision.score.policy.v1",
        "metrics": [
            {
                "metric_id": "sustainability",
                "label": "Sustainability",
                "orientation": "higher_is_better",
                "min_value": "0",
                "max_value": "1",
                "unit": "ratio",
            },
            {
                "metric_id": "final_wealth",
                "label": "Final wealth",
                "orientation": "higher_is_better",
                "min_value": "0",
                "max_value": "1000000",
                "unit": "EUR",
            },
            {
                "metric_id": "risk",
                "label": "Risk",
                "orientation": "lower_is_better",
                "min_value": "0",
                "max_value": "1",
                "unit": "ratio",
            },
        ],
        "limitations": ["synthetic fixture"],
    }


def _scoring_input() -> dict:
    return {
        "schema_version": "decision-score/v1",
        "record_type": "DecisionScoreInput",
        "score_id": "synthetic_decision_score",
        "label": "Synthetic decision score",
        "as_of_date": "2026-07-18",
        "weights": {"sustainability": "0.75", "final_wealth": "0.25"},
        "alternatives": [
            {
                "alternative_id": "aggressive",
                "label": "Aggressive allocation",
                "outcome_ref": {"kind": "sensitivity", "id": "return_up"},
                "metrics": {
                    "sustainability": {"outcome_metric_id": "success_rate"},
                    "final_wealth": {"outcome_metric_id": "final_balance_p50"},
                },
            },
            {
                "alternative_id": "balanced",
                "label": "Balanced allocation",
                "outcome_ref": {"kind": "baseline"},
                "metrics": {
                    "sustainability": {"outcome_metric_id": "success_rate"},
                    "final_wealth": {"outcome_metric_id": "final_balance_p50"},
                },
            },
        ],
    }


if __name__ == "__main__":
    unittest.main()
