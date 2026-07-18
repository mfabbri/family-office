import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.decision_dossier import DecisionDossierError, build_decision_dossier


class DecisionDossierTest(unittest.TestCase):
    def test_build_complete_dossier_with_markdown_and_stable_hash(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            input_path = _write_json(root / "dossier-input.json", _dossier_input())

            first = _dossier(root, paths, input_path, "dossier-1.json", "dossier-1.md")
            second = _dossier(root, paths, input_path, "dossier-2.json", "dossier-2.md")

            self.assertEqual(first["schema_version"], "decision-dossier/v1")
            self.assertEqual(first["record_type"], "DecisionDossierSnapshot")
            self.assertEqual(first["status"], "complete")
            self.assertEqual(first["recommendation"]["alternative_id"], "balanced")
            self.assertEqual(first["ranking_rationale"][0]["alternative_id"], "balanced")
            self.assertEqual(first["reproducibility"]["content_hash"], second["reproducibility"]["content_hash"])
            self.assertIn("Recommended alternative: Balanced allocation", (root / "dossier-1.md").read_text())

    def test_blocking_gap_prevents_recommendation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            score = _decision_score()
            score["data_gaps"] = [{"code": "missing_alternative_metric", "message": "Synthetic gap."}]
            paths["decision_score"] = _write_json(root / "score-gap.json", score)
            dossier_input = _dossier_input()
            dossier_input["blocking_gap_codes"] = ["missing_alternative_metric"]
            input_path = _write_json(root / "dossier-input.json", dossier_input)

            result = _dossier(root, paths, input_path, "dossier.json", "dossier.md")

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertIsNone(result["recommendation"])
            self.assertIn("resolve_blocking_gaps", {action["action_id"] for action in result["next_actions"]})

    def test_incomplete_score_blocks_recommendation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            score = _decision_score()
            score["status"] = "partial"
            score["ranking"] = []
            paths["decision_score"] = _write_json(root / "score-partial.json", score)
            input_path = _write_json(root / "dossier-input.json", _dossier_input())

            result = _dossier(root, paths, input_path, "dossier.json", "dossier.md")

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertIn("missing_decision_ranking", {gap["code"] for gap in result["blocking_gaps"]})

    def test_rejects_wrong_source_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            paths["decision_scenario"] = _write_json(root / "wrong.json", {"schema_version": "wrong/v1"})
            input_path = _write_json(root / "dossier-input.json", _dossier_input())

            with self.assertRaisesRegex(DecisionDossierError, "Unsupported decision scenario snapshot schema"):
                _dossier(root, paths, input_path, "dossier.json", "dossier.md")


def _dossier(root: Path, paths: dict[str, Path], input_path: Path, snapshot_name: str, markdown_name: str) -> dict:
    return build_decision_dossier(
        paths["decision_scenario"],
        paths["sensitivity_analysis"],
        paths["decision_score"],
        input_path,
        root / snapshot_name,
        root / markdown_name,
    )


def _write_sources(root: Path) -> dict[str, Path]:
    return {
        "decision_scenario": _write_json(root / "decision-scenario.json", _decision_scenario()),
        "sensitivity_analysis": _write_json(root / "sensitivity-analysis.json", _sensitivity_analysis()),
        "decision_score": _write_json(root / "decision-score.json", _decision_score()),
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
        "source_summaries": {"household": {"person_count": 2}},
        "assumptions": {
            "market": {"nominal_return": "0.03", "inflation": "0.02"},
            "withdrawal_policy": {"policy_id": "fixed_real_need"},
        },
        "data_gaps": [],
        "reproducibility": {"content_hash": "scenario-hash"},
    }


def _sensitivity_analysis() -> dict:
    return {
        "schema_version": "sensitivity-analysis/v1",
        "record_type": "SensitivityAnalysisSnapshot",
        "status": "complete",
        "analysis_id": "synthetic_sensitivity",
        "tornado_data": [{"rank": 1, "sensitivity_id": "risk_up", "magnitude": "0.2"}],
        "stress_matrix": [{"id": "adverse", "status": "complete"}],
        "data_gaps": [],
        "reproducibility": {"content_hash": "sensitivity-hash"},
    }


def _decision_score() -> dict:
    provenance = {
        "scenario_content_hash": "scenario-hash",
        "evaluator_id": "retirement-monte-carlo/v1",
        "outcome_hash": "baseline-outcome-hash",
        "outcome_metric_id": "success_rate",
    }
    return {
        "schema_version": "decision-score/v1",
        "record_type": "DecisionScoreSnapshot",
        "status": "complete",
        "score_id": "synthetic_score",
        "lineage_status": "complete",
        "alternatives": [
            {
                "alternative_id": "balanced",
                "label": "Balanced allocation",
                "status": "complete",
                "lineage_status": "complete",
                "total_score": "0.7210",
                "metrics": [
                    {
                        "metric_id": "risk",
                        "label": "Risk",
                        "raw_value": "0.30",
                        "normalized_score": "0.7000",
                        "weight": "0.30",
                        "weighted_score": "0.2100",
                        "provenance": {**provenance, "outcome_metric_id": "risk_ratio"},
                    },
                    {
                        "metric_id": "sustainability",
                        "label": "Sustainability",
                        "raw_value": "0.78",
                        "normalized_score": "0.7800",
                        "weight": "0.45",
                        "weighted_score": "0.3510",
                        "provenance": provenance,
                    },
                ],
            },
            {
                "alternative_id": "aggressive",
                "label": "Aggressive allocation",
                "status": "complete",
                "lineage_status": "complete",
                "total_score": "0.6250",
                "metrics": [
                    {
                        "metric_id": "sustainability",
                        "label": "Sustainability",
                        "raw_value": "0.62",
                        "normalized_score": "0.6200",
                        "weight": "0.45",
                        "weighted_score": "0.2790",
                        "provenance": {**provenance, "outcome_hash": "aggressive-outcome-hash"},
                    }
                ],
            },
        ],
        "ranking": [
            {"rank": 1, "alternative_id": "balanced", "label": "Balanced allocation", "total_score": "0.7210"},
            {"rank": 2, "alternative_id": "aggressive", "label": "Aggressive allocation", "total_score": "0.6250"},
        ],
        "data_gaps": [],
        "reproducibility": {"content_hash": "score-hash"},
    }


def _dossier_input() -> dict:
    return {
        "schema_version": "decision-dossier/v1",
        "record_type": "DecisionDossierInput",
        "dossier_id": "synthetic_dossier",
        "label": "Synthetic decision dossier",
        "as_of_date": "2026-07-18",
        "blocking_gap_codes": [],
        "next_actions": [
            {"action_id": "human_review", "label": "Review ranking and evidence with a qualified human reviewer."}
        ],
        "human_review": {"required": True, "reviewer_role": "human_reviewer"},
    }


if __name__ == "__main__":
    unittest.main()
