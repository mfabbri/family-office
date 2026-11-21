import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4


SAMPLE = Path(__file__).resolve().parents[2] / "examples" / "retirement-bridge-projection-input-sample.json"


class RetirementBridgeProjectionCliTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.gettempdir()) / f"fo-bridge-{uuid4().hex}"
        self.root.mkdir()
        self.addCleanup(shutil.rmtree, self.root)
        self.output = self.root / "projection.json"

    def simulate(self, source, output=None):
        return subprocess.run(
            [sys.executable, "-m", "family_office_engine.cli.main", "planning",
             "retirement-bridge", "simulate", "--input", str(source),
             "--output", str(output if output is not None else self.output)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
        )

    def test_sample_projection_and_repeatability(self):
        first = self.simulate(SAMPLE)
        self.assertEqual(first.returncode, 0, first.stderr)
        data = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "scenario_projection")
        self.assertEqual([s["work_fraction"] for s in data["scenarios"]], ["1.00", "0.60", "0.00"])
        self.assertEqual([s["cashflows"][0]["net_cashflow"] for s in data["scenarios"]],
                         ["1000.00", "200.00", "-1000.00"])
        zero = data["scenarios"][2]
        self.assertEqual(zero["summary"]["total_no_work_funding_need"], "1000.00")
        self.assertEqual(zero["cashflows"][0]["asset_withdrawal"], "1000.00")
        self.assertEqual(zero["summary"]["ending_available_assets"], "9000.00")
        second_output = self.root / "second.json"
        second = self.simulate(SAMPLE, second_output)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.output.read_bytes(), second_output.read_bytes())

    def test_pension_assumption_stays_in_scenario(self):
        sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
        sample["assumptions"]["hypothetical_pension"] = {
            "monthly_net_amount": "500.00", "start_month": 1,
            "assumption_status": "scenario_assumption", "provenance": "synthetic",
        }
        source = self.root / "pension.json"
        source.write_text(json.dumps(sample), encoding="utf-8-sig")
        result = self.simulate(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(data["scenarios"][2]["cashflows"][0]["hypothetical_pension_net_income"], "500.00")
        self.assertEqual(data["pension_entitlement"], {
            "status": "not_assessed", "verified_monthly_amount": None, "verified_start_month": None,
        })
        self.assertIn("future_pension_entitlement_not_verified", {gap["code"] for gap in data["data_gaps"]})

        sample["assumptions"]["hypothetical_pension"]["assumption_status"] = "verified"
        source.write_text(json.dumps(sample), encoding="utf-8")
        rejected = self.simulate(source, self.root / "rejected.json")
        self.assertEqual(rejected.returncode, 1)
        self.assertIn("scenario_assumption", rejected.stderr)
        self.assertFalse((self.root / "rejected.json").exists())

    def test_invalid_input_has_actionable_error_and_no_output(self):
        source = self.root / "invalid.json"
        for raw in ("{broken", "[]", '{"schema_version":"unsupported"}'):
            with self.subTest(raw=raw):
                source.write_text(raw, encoding="utf-8")
                result = self.simulate(source)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Check --input", result.stderr)
                self.assertFalse(self.output.exists())

    def test_existing_output_is_preserved(self):
        self.output.write_text("keep me", encoding="utf-8")
        result = self.simulate(SAMPLE)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Choose a new --output path", result.stderr)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "keep me")
