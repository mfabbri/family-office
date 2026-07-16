import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.rita_options import (
    RitaOptionsError,
    load_rule_pack,
    optimize_rita_options,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RITA_RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "italy" / "current" / "rita.yaml"


class RitaOptionsTest(unittest.TestCase):
    def test_ordinary_eligibility_builds_straight_line_option(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "rita-options.snapshot.json"

            result = optimize_rita_options(
                RITA_RULE_PACK,
                output_path,
                age=62,
                years_to_public_pension="4",
                employment_status="ceased",
                mandatory_contribution_years="32",
                complementary_pension_years="8",
                complementary_balance="120000.00",
                duration_months=48,
                monthly_need="3000.00",
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "rita-options/v1")
            self.assertEqual(written["status"], "complete")
            self.assertTrue(written["eligibility"]["eligible"])
            self.assertEqual(written["eligibility"]["matched_rule_id"], "it.rita.ordinary.current")
            self.assertEqual(written["options"][0]["gross_monthly_amount"], "2500.00")
            self.assertEqual(written["options"][0]["monthly_need_coverage_ratio"], "0.8333")
            self.assertIn("no_tax_calculation", written["options"][0]["assumptions"])

    def test_long_unemployment_path_does_not_require_twenty_mandatory_years(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "rita-options.snapshot.json"

            result = optimize_rita_options(
                RITA_RULE_PACK,
                output_path,
                age=58,
                years_to_public_pension="9",
                employment_status="unemployed",
                unemployed_months=25,
                mandatory_contribution_years="12",
                complementary_pension_years="6",
                complementary_balance="60000.00",
                duration_months=60,
            )

            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["eligibility"]["matched_rule_id"], "it.rita.long-unemployment.current")
            self.assertEqual(result["options"][0]["gross_monthly_amount"], "1000.00")

    def test_not_eligible_when_requirements_are_not_met(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "rita-options.snapshot.json"

            result = optimize_rita_options(
                RITA_RULE_PACK,
                output_path,
                age=55,
                years_to_public_pension="12",
                employment_status="employed",
                mandatory_contribution_years="25",
                complementary_pension_years="8",
                complementary_balance="90000.00",
                duration_months=60,
            )

            self.assertEqual(result["status"], "not_eligible")
            self.assertFalse(result["eligibility"]["eligible"])
            self.assertEqual(result["options"], [])

    def test_blocks_when_option_inputs_are_missing_after_eligibility(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "rita-options.snapshot.json"

            result = optimize_rita_options(
                RITA_RULE_PACK,
                output_path,
                age=62,
                years_to_public_pension="4",
                employment_status="ceased",
                mandatory_contribution_years="32",
                complementary_pension_years="8",
            )

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertTrue(result["eligibility"]["eligible"])
            self.assertEqual(
                [gap["code"] for gap in result["data_gaps"]],
                ["missing_complementary_balance", "missing_duration_months"],
            )

    def test_load_rule_pack_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            rule_pack_path = Path(tmp_dir) / "rita.yaml"
            rule_pack_path.write_text(
                json.dumps(
                    {
                        "schema_version": "wrong",
                        "rule_pack_id": "synthetic.rita",
                        "jurisdiction": "IT",
                        "currency": "EUR",
                        "requirements": {},
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RitaOptionsError, "Unsupported RITA rule pack schema"):
                load_rule_pack(rule_pack_path)


if __name__ == "__main__":
    unittest.main()
