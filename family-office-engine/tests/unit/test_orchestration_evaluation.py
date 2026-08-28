import copy
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from family_office_engine.cli.main import main
from family_office_engine.services.orchestration_evaluation import (
    OrchestrationEvaluationError,
    build_orchestration_evaluation,
    evaluate_orchestration,
)

ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = ROOT / "family-office-engine" / "evaluations" / "v5.11-orchestration-evaluation.json"
POLICY_PATH = ROOT / "family-office-rules" / "compliance" / "guardrail-policy-v1.json"


class OrchestrationEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        self.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_runs_all_synthetic_contract_cases_and_passes_release_gate(self):
        report = evaluate_orchestration(self.dataset, self.policy, candidate_id="synthetic-candidate-v1")

        self.assertEqual("orchestration-evaluation-report/v1", report["schema_version"])
        self.assertTrue(report["release_gate"]["passed"])
        self.assertEqual(8, len(report["cases"]))
        self.assertTrue(all(metric["score"] == 1.0 for metric in report["metrics"].values()))
        self.assertTrue(report["dataset"]["synthetic_only"])
        self.assertFalse(report["release_gate"]["llm_used"])
        self.assertFalse(report["release_gate"]["calculations_delegated_to_llm"])

    def test_rejects_dataset_without_synthetic_data_policy_or_wrong_baseline(self):
        invalid = copy.deepcopy(self.dataset)
        invalid["data_policy"] = "unknown"
        with self.assertRaisesRegex(OrchestrationEvaluationError, "synthetic-only"):
            evaluate_orchestration(invalid, self.policy, candidate_id="candidate")

        report = evaluate_orchestration(self.dataset, self.policy, candidate_id="candidate")
        changed = copy.deepcopy(self.dataset)
        changed["suite_id"] = "changed"
        with self.assertRaisesRegex(OrchestrationEvaluationError, "same dataset"):
            evaluate_orchestration(changed, self.policy, candidate_id="candidate", baseline=report)
        malformed = copy.deepcopy(report)
        malformed["metrics"].pop("privacy")
        with self.assertRaisesRegex(OrchestrationEvaluationError, "same dataset"):
            evaluate_orchestration(self.dataset, self.policy, candidate_id="candidate", baseline=malformed)

    def test_writes_report_and_cli_release_gate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "report.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main([
                    "orchestration", "evaluate", "--dataset", str(DATASET_PATH), "--policy", str(POLICY_PATH),
                    "--candidate-id", "synthetic-candidate-v1", "--output", str(output),
                ])
            self.assertEqual(0, exit_code)
            self.assertTrue(output.exists())
            self.assertIn("release_gate=passed", stdout.getvalue())
            self.assertTrue(build_orchestration_evaluation(DATASET_PATH, POLICY_PATH, Path(tmp_dir) / "again.json", candidate_id="candidate")["release_gate"]["passed"])


if __name__ == "__main__":
    unittest.main()
