import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.tax_calculation import (
    TaxCalculationError,
    calculate_tax,
    load_rule_pack,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ITALY_2026_RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "italy" / "2026" / "irpef-national.json"
ITALY_2025_RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "italy" / "2025" / "irpef-national.json"


SYNTHETIC_RULE_PACK = {
    "schema_version": "tax-rule-pack/v1",
    "rule_pack_id": "synthetic.progressive-tax.v1",
    "jurisdiction": "SYNTH",
    "currency": "EUR",
    "status": "synthetic_fixture_not_for_real_tax",
    "rules": [
        {
            "rule_id": "synthetic.progressive-tax.2026",
            "tax_type": "personal_income_tax",
            "valid_from": "2026-01-01",
            "valid_to": "2026-12-31",
            "brackets": [
                {"from": "0.00", "to": "10000.00", "rate": "0.10"},
                {"from": "10000.00", "to": "30000.00", "rate": "0.20"},
                {"from": "30000.00", "to": None, "rate": "0.30"},
            ],
        }
    ],
}


class TaxCalculationTest(unittest.TestCase):
    def test_calculate_tax_uses_italy_2026_irpef_rule_pack(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "tax-calculation.snapshot.json"

            result = calculate_tax(ITALY_2026_RULE_PACK, 2026, "IT", "60000.00", output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "complete")
            self.assertEqual(written["result"]["tax_due"], "18000.00")
            self.assertEqual(written["result"]["tax_type"], "personal_income_tax_gross_national")
            self.assertEqual(
                written["result"]["explainability"]["rule_id"],
                "it.irpef-national.gross.2026.v2",
            )
            self.assertEqual(len(written["result"]["applied_brackets"]), 3)
            self.assertEqual(
                written["rule_pack"]["source_refs"][0]["source_id"],
                "gazzetta.legge-2025-199.art1-comma3",
            )
            self.assertIn("national gross IRPEF", written["rule_pack"]["limitations"][0])

    def test_italy_2026_irpef_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            at_first_threshold = calculate_tax(ITALY_2026_RULE_PACK, 2026, "IT", "28000.00", root / "a.json")
            above_first_threshold = calculate_tax(ITALY_2026_RULE_PACK, 2026, "IT", "28001.00", root / "a-plus.json")
            at_second_threshold = calculate_tax(ITALY_2026_RULE_PACK, 2026, "IT", "50000.00", root / "b.json")
            above_second_threshold = calculate_tax(ITALY_2026_RULE_PACK, 2026, "IT", "50001.00", root / "b-plus.json")

            self.assertEqual(at_first_threshold["result"]["tax_due"], "6440.00")
            self.assertEqual(above_first_threshold["result"]["tax_due"], "6440.33")
            self.assertEqual(at_second_threshold["result"]["tax_due"], "13700.00")
            self.assertEqual(above_second_threshold["result"]["tax_due"], "13700.43")

    def test_italy_2025_irpef_historical_brackets_remain_separate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = calculate_tax(ITALY_2025_RULE_PACK, 2025, "IT", "50000.00", Path(tmp_dir) / "tax.json")

            self.assertEqual(result["rule_pack"]["rule_pack_id"], "it.irpef-national.2025.v1")
            self.assertEqual(result["result"]["tax_due"], "14140.00")

    def test_calculate_tax_applies_progressive_brackets(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            rule_pack_path = root / "rules.json"
            output_path = root / "tax-calculation.snapshot.json"
            rule_pack_path.write_text(json.dumps(SYNTHETIC_RULE_PACK), encoding="utf-8")

            result = calculate_tax(rule_pack_path, 2026, "SYNTH", "45000.00", output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "tax-calculation/v1")
            self.assertEqual(written["status"], "complete")
            self.assertEqual(written["result"]["tax_due"], "9500.00")
            self.assertEqual(len(written["result"]["applied_brackets"]), 3)
            self.assertEqual(
                written["result"]["explainability"]["rule_id"],
                "synthetic.progressive-tax.2026",
            )

    def test_calculate_tax_blocks_when_year_is_not_covered(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            rule_pack_path = root / "rules.json"
            output_path = root / "tax-calculation.snapshot.json"
            rule_pack_path.write_text(json.dumps(SYNTHETIC_RULE_PACK), encoding="utf-8")

            result = calculate_tax(rule_pack_path, 2027, "SYNTH", "45000.00", output_path)

            self.assertEqual(result["status"], "blocked_missing_rule")
            self.assertIsNone(result["result"])
            self.assertEqual(result["data_gaps"][0]["code"], "tax_year_not_covered")

    def test_calculate_tax_blocks_when_jurisdiction_does_not_match(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            rule_pack_path = root / "rules.json"
            output_path = root / "tax-calculation.snapshot.json"
            rule_pack_path.write_text(json.dumps(SYNTHETIC_RULE_PACK), encoding="utf-8")

            result = calculate_tax(rule_pack_path, 2026, "IT", "45000.00", output_path)

            self.assertEqual(result["status"], "blocked_missing_rule")
            self.assertEqual(result["data_gaps"][0]["code"], "jurisdiction_not_covered")

    def test_load_rule_pack_rejects_non_contiguous_brackets(self):
        broken = dict(SYNTHETIC_RULE_PACK)
        broken["rules"] = [
            {
                **SYNTHETIC_RULE_PACK["rules"][0],
                "brackets": [
                    {"from": "0.00", "to": "10000.00", "rate": "0.10"},
                    {"from": "11000.00", "to": None, "rate": "0.20"},
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            rule_pack_path = Path(tmp_dir) / "rules.json"
            rule_pack_path.write_text(json.dumps(broken), encoding="utf-8")

            with self.assertRaisesRegex(TaxCalculationError, "non-contiguous"):
                load_rule_pack(rule_pack_path)


if __name__ == "__main__":
    unittest.main()
