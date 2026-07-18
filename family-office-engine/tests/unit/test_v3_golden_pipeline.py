import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.decision_dossier import build_decision_dossier
from family_office_engine.services.decision_score import build_decision_score
from family_office_engine.services.sensitivity_analysis import build_sensitivity_analysis


class V3GoldenPipelineTest(unittest.TestCase):
    def test_traceable_scoring_pipeline_builds_complete_dossier(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario_path = _write_json(root / "scenario.json", _decision_scenario())
            sensitivity_input_path = _write_json(root / "sensitivity-input.json", _sensitivity_input())
            score_input_path = _write_json(root / "score-input.json", _score_input())
            score_policy_path = _write_json(root / "score-policy.json", _score_policy())
            dossier_input_path = _write_json(root / "dossier-input.json", _dossier_input())

            first_sensitivity = build_sensitivity_analysis(
                scenario_path,
                sensitivity_input_path,
                root / "sensitivity-1.json",
            )
            second_sensitivity = build_sensitivity_analysis(
                scenario_path,
                sensitivity_input_path,
                root / "sensitivity-2.json",
            )
            score = build_decision_score(
                scenario_path,
                root / "sensitivity-1.json",
                score_input_path,
                score_policy_path,
                root / "score.json",
            )
            dossier = build_decision_dossier(
                scenario_path,
                root / "sensitivity-1.json",
                root / "score.json",
                dossier_input_path,
                root / "dossier.json",
                root / "dossier.md",
            )

            self.assertEqual(first_sensitivity["status"], "complete")
            self.assertEqual(
                first_sensitivity["reproducibility"]["content_hash"],
                second_sensitivity["reproducibility"]["content_hash"],
            )
            self.assertEqual(score["status"], "complete")
            self.assertEqual(score["lineage_status"], "complete")
            self.assertEqual(score["ranking"][0]["alternative_id"], "return_upside")
            self.assertEqual(dossier["status"], "complete")
            self.assertEqual(dossier["recommendation"]["alternative_id"], "return_upside")
            self.assertEqual(dossier["lineage_summary"]["status"], "complete")
            self.assertEqual(dossier["blocking_gaps"], [])


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _decision_scenario() -> dict:
    return {
        "schema_version": "decision-scenario/v2",
        "record_type": "DecisionScenarioSnapshot",
        "status": "complete",
        "scenario_id": "v3_golden_synthetic",
        "label": "V3 golden synthetic scenario",
        "as_of_date": "2026-07-18",
        "assumptions": {
            "personal": {"current_age": 60, "target_retirement_age": 65},
            "portfolio": {"starting_net_worth": "350000.00", "currency": "EUR"},
            "cashflow": {
                "family_expenses_yearly": "36000.00",
                "net_salary_monthly": "3500.00",
                "salary_months": 12,
                "retirement_income_yearly": "18000.00",
            },
            "market": {"nominal_return": "0.03", "nominal_volatility": "0.08"},
            "withdrawal_policy": {"policy_id": "synthetic_fixed_need"},
        },
        "source_summaries": {"fixture": {"kind": "synthetic"}},
        "data_gaps": [],
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": "v3-golden-scenario-hash"},
    }


def _sensitivity_input() -> dict:
    return {
        "schema_version": "sensitivity-analysis/v1",
        "record_type": "SensitivityAnalysisInput",
        "analysis_id": "v3_golden_sensitivity",
        "label": "V3 golden sensitivity",
        "as_of_date": "2026-07-18",
        "seed": 20260718,
        "outcome_evaluation": {
            "schema_version": "decision-outcome/v1",
            "record_type": "DecisionOutcomeInput",
            "outcome_id": "v3-golden-outcome",
            "label": "V3 golden outcome",
            "evaluator_id": "retirement-monte-carlo/v1",
            "parameters": {"simulations": 50, "seed": 20260718, "end_age": 95},
            "impact_metric_id": "final_balance_p50",
        },
        "sensitivities": [
            {
                "id": "return_up",
                "label": "Nominal return +1pp",
                "domain": "returns",
                "path": ["assumptions", "market", "nominal_return"],
                "operation": "absolute",
                "delta": "0.01",
            }
        ],
        "stress_scenarios": [],
    }


def _score_input() -> dict:
    return {
        "schema_version": "decision-score/v1",
        "record_type": "DecisionScoreInput",
        "score_id": "v3_golden_score",
        "label": "V3 golden score",
        "as_of_date": "2026-07-18",
        "weights": {"final_wealth": "1.0"},
        "alternatives": [
            {
                "alternative_id": "baseline",
                "label": "Baseline",
                "outcome_ref": {"kind": "baseline"},
                "metrics": {"final_wealth": {"outcome_metric_id": "final_balance_p50"}},
            },
            {
                "alternative_id": "return_upside",
                "label": "Return upside",
                "outcome_ref": {"kind": "sensitivity", "id": "return_up"},
                "metrics": {"final_wealth": {"outcome_metric_id": "final_balance_p50"}},
            },
        ],
    }


def _score_policy() -> dict:
    return {
        "schema_version": "decision-score-policy/v1",
        "record_type": "DecisionScorePolicy",
        "policy_id": "v3.golden.score.policy",
        "metrics": [
            {
                "metric_id": "final_wealth",
                "label": "Final wealth",
                "orientation": "higher_is_better",
                "min_value": "0",
                "max_value": "1000000",
                "unit": "EUR",
            }
        ],
        "limitations": ["Synthetic golden fixture only."],
    }


def _dossier_input() -> dict:
    return {
        "schema_version": "decision-dossier/v1",
        "record_type": "DecisionDossierInput",
        "dossier_id": "v3_golden_dossier",
        "label": "V3 golden dossier",
        "as_of_date": "2026-07-18",
        "blocking_gap_codes": [],
        "next_actions": [{"action_id": "human_review", "label": "Review deterministic evidence."}],
        "human_review": {"required": True, "reviewer_role": "human_reviewer"},
    }


if __name__ == "__main__":
    unittest.main()
