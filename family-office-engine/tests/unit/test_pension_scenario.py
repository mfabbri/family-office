import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.pension_scenario import PensionScenarioError, build_pension_scenario

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_INPUT = REPOSITORY_ROOT / "family-office-engine" / "examples" / "pension-scenario-sample.json"


class PensionScenarioTest(unittest.TestCase):
    def test_builds_baseline_italy_retirement_scenario(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "pension-scenario.snapshot.json"

            result = build_pension_scenario(SAMPLE_INPUT, output)
            written = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "pension-scenario/v1")
            self.assertEqual(written["status"], "complete")
            self.assertEqual(written["selected_scenario_id"], "baseline_it_retirement")
            selected = written["selected_scenario"]
            self.assertEqual(selected["retirement"]["country"], "IT")
            self.assertEqual(selected["initial_fiscal_residence"], "IT")
            self.assertIn(("ES", "none"), {(item["country"], item["status"]) for item in selected["future_contributions"]})
            self.assertRegex(written["reproducibility"]["content_hash"], r"^[0-9a-f]{64}$")

    def test_transfer_to_spain_requires_explicit_effective_date(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "scenario.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["selected_scenario_id"] = "post_retirement_transfer_es"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_pension_scenario(input_path, output)

            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["summary"]["selected_fiscal_residence"], "ES")
            self.assertEqual(
                result["selected_scenario"]["post_retirement_residence_changes"][0]["effective_date"],
                "2041-01",
            )

    def test_missing_transfer_date_becomes_gap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "scenario.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["selected_scenario_id"] = "post_retirement_transfer_es"
            data["scenarios"][1]["post_retirement_residence_changes"][0].pop("effective_date")
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_pension_scenario(input_path, output)

            self.assertEqual(result["status"], "partial")
            self.assertIn("missing_residence_change_effective_date", {gap["code"] for gap in result["data_gaps"]})

    def test_missing_future_contributions_becomes_gap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "scenario.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["scenarios"][0].pop("future_contributions")
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_pension_scenario(input_path, output)

            self.assertEqual(result["status"], "partial")
            self.assertIn("missing_future_contribution_assumptions", {gap["code"] for gap in result["data_gaps"]})

    def test_spanish_future_contribution_cannot_use_italian_periods_as_basis(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "scenario.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["scenarios"][0]["future_contributions"][1]["status"] = "planned"
            data["scenarios"][0]["future_contributions"][1]["basis"] = "italian_periods"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_pension_scenario(input_path, output)

            self.assertEqual(result["status"], "partial")
            self.assertIn("spanish_future_contribution_uses_italian_periods", {gap["code"] for gap in result["data_gaps"]})

    def test_missing_provenance_becomes_gap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "scenario.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["scenarios"][0]["provenance"] = []
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_pension_scenario(input_path, output)

            self.assertEqual(result["status"], "partial")
            self.assertIn("missing_scenario_provenance", {gap["code"] for gap in result["data_gaps"]})

    def test_synthetic_sources_are_rejected_for_personal_household(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "scenario.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["household_id"] = "real_household"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(PensionScenarioError, "Synthetic"):
                build_pension_scenario(input_path, output)


if __name__ == "__main__":
    unittest.main()
