import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.pension_contribution_options import (
    PensionContributionOptionsError,
    build_pension_contribution_options,
    load_pension_contribution_rule_pack,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "italy" / "2026" / "pension-contribution-deduction.json"
SAMPLE_INPUT = REPOSITORY_ROOT / "family-office-engine" / "examples" / "pension-contribution-input-sample.json"


class PensionContributionOptionsTest(unittest.TestCase):
    def test_build_options_applies_ordinary_limit_and_employer_contribution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "pension-contribution-options.snapshot.json"

            result = build_pension_contribution_options(SAMPLE_INPUT, RULE_PACK, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "pension-contribution-options/v1")
            self.assertEqual(written["status"], "complete")
            first = written["options"][0]
            self.assertEqual(first["option_id"], "employee_plus_match")
            self.assertEqual(first["contributions"]["deductible_total"], "4000.00")
            self.assertEqual(first["estimated_tax_benefit"]["amount"], "1400.00")
            self.assertEqual(first["net_estimated_value"], "2310.00")
            self.assertEqual(written["ranking"][0]["option_id"], "employee_plus_match")
            self.assertEqual(
                written["rule_pack"]["source_refs"][0]["source_id"],
                "normattiva.dlgs-2005-252.art8",
            )

    def test_build_options_uses_first_employment_extra_room_and_flags_excess(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "pension-contribution-options.snapshot.json"

            result = build_pension_contribution_options(SAMPLE_INPUT, RULE_PACK, output_path)
            option = next(item for item in result["options"] if item["option_id"] == "max_personal_with_extra_room")

            self.assertEqual(option["contributions"]["ordinary_deductible"], "4164.57")
            self.assertEqual(option["contributions"]["first_employment_extra_deductible"], "1500.00")
            self.assertEqual(option["contributions"]["non_deductible"], "835.43")
            self.assertIn("deduction_limit_exceeded", {constraint["code"] for constraint in option["constraints"]})

    def test_build_options_separates_tfr_and_liquidity_constraint(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "pension-contribution-options.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["available_liquidity"] = "9000.00"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_pension_contribution_options(input_path, RULE_PACK, output_path)
            option = next(item for item in result["options"] if item["option_id"] == "employee_plus_tfr")

            self.assertEqual(option["contributions"]["tfr_transfer"], "6000.00")
            self.assertEqual(option["contributions"]["deductible_candidate"], "2000.00")
            self.assertIn("tfr_transfer_locked", {constraint["code"] for constraint in option["constraints"]})
            self.assertIn("liquidity_floor_breached", {constraint["code"] for constraint in option["constraints"]})

    def test_build_options_blocks_when_rule_year_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.json"
            output_path = root / "pension-contribution-options.snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["tax_year"] = 2027
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_pension_contribution_options(input_path, RULE_PACK, output_path)

            self.assertEqual(result["status"], "blocked_missing_rule")
            self.assertEqual(result["data_gaps"][0]["code"], "tax_year_not_covered")
            self.assertEqual(result["options"], [])

    def test_load_rule_pack_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            rule_path = Path(tmp_dir) / "rules.json"
            rule_path.write_text(json.dumps({"schema_version": "wrong", "rules": []}), encoding="utf-8")

            with self.assertRaisesRegex(PensionContributionOptionsError, "missing field"):
                load_pension_contribution_rule_pack(rule_path)


if __name__ == "__main__":
    unittest.main()
