import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.protection_gap import ProtectionGapError, build_protection_gap

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_INPUT = REPOSITORY_ROOT / "family-office-engine" / "examples" / "protection-gap-sample.json"


class ProtectionGapTest(unittest.TestCase):
    def test_builds_protection_gap_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "protection-gap.snapshot.json"

            result = build_protection_gap(SAMPLE_INPUT, output)
            written = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "protection-gap/v1")
            self.assertEqual(written["status"], "complete")
            self.assertEqual(written["summary"]["need_count"], 2)
            self.assertEqual(written["summary"]["policy_count"], 3)
            self.assertEqual(written["summary"]["total_required_capital"], "310000.00")
            self.assertEqual(written["summary"]["total_protection_coverage"], "240000.00")
            self.assertEqual(written["summary"]["total_shortfall"], "70000.00")
            self.assertEqual(written["summary"]["investment_surrender_value"], "25000.00")
            self.assertRegex(written["reproducibility"]["content_hash"], r"^[0-9a-f]{64}$")

    def test_missing_beneficiary_becomes_data_gap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "protection-gap.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["policies"][0]["beneficiaries"] = []
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_protection_gap(input_path, output)

            self.assertEqual(result["status"], "partial")
            self.assertIn("missing_policy_beneficiary", {gap["code"] for gap in result["data_gaps"]})

    def test_insufficient_capital_is_reported_without_inference(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "snapshot.json"

            result = build_protection_gap(SAMPLE_INPUT, output)

            death_gap = next(item for item in result["protection_gaps"] if item["event_type"] == "death")
            self.assertEqual(death_gap["status"], "shortfall")
            self.assertEqual(death_gap["required_capital"], "220000.00")
            self.assertEqual(death_gap["protection_coverage"], "150000.00")
            self.assertEqual(death_gap["shortfall"], "70000.00")

    def test_investment_policy_surrender_value_is_not_counted_as_protection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "protection-gap.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["policies"][2]["coverage_events"] = [{"event_type": "death", "insured_capital": "25000.00"}]
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_protection_gap(input_path, output)

            death_gap = next(item for item in result["protection_gaps"] if item["event_type"] == "death")
            self.assertEqual(death_gap["protection_coverage"], "150000.00")
            self.assertIn("investment_policy_coverage_not_counted", {gap["code"] for gap in result["data_gaps"]})

    def test_invalid_beneficiary_share_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "protection-gap.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["policies"][0]["beneficiaries"][0]["share"] = "1.50"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ProtectionGapError, "share"):
                build_protection_gap(input_path, output)


if __name__ == "__main__":
    unittest.main()
