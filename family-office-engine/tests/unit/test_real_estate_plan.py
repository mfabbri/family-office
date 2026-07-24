import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.real_estate_plan import RealEstatePlanError, build_real_estate_plan

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_INPUT = REPOSITORY_ROOT / "family-office-engine" / "examples" / "real-estate-plan-sample.json"


class RealEstatePlanTest(unittest.TestCase):
    def test_builds_hold_rent_and_sell_alternatives(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "real-estate-plan.snapshot.json"

            result = build_real_estate_plan(SAMPLE_INPUT, output)
            written = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "real-estate-plan/v1")
            self.assertEqual(written["status"], "complete")
            self.assertEqual(written["summary"]["alternative_count"], 3)
            by_strategy = {item["strategy"]: item for item in written["alternatives"]}
            self.assertEqual(by_strategy["hold"]["annual_net_cashflow_or_proceeds"], "-5100.00")
            self.assertEqual(by_strategy["rent"]["annual_gross_income"], "11000.00")
            self.assertEqual(by_strategy["rent"]["annual_net_cashflow_or_proceeds"], "5000.00")
            self.assertEqual(by_strategy["sell"]["liquidity_amount"], "229900.00")
            self.assertEqual(by_strategy["sell"]["liquidity_month"], 9)
            self.assertRegex(written["reproducibility"]["content_hash"], r"^[0-9a-f]{64}$")

    def test_spouse_co_ownership_is_preserved_in_output(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "snapshot.json"

            result = build_real_estate_plan(SAMPLE_INPUT, output)

            ownership = result["properties"][0]["ownership"]
            self.assertIn(("self", "0.5000"), {(item["relationship"], item["share"]) for item in ownership})
            self.assertIn(("spouse", "0.5000"), {(item["relationship"], item["share"]) for item in ownership})
            self.assertEqual(result["alternatives"][0]["owned_share"], "1.0000")

    def test_missing_rent_and_vacancy_become_gaps(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "real-estate.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["properties"][0]["rent_assumption"] = {}
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_real_estate_plan(input_path, output)

            self.assertEqual(result["status"], "partial")
            rent = next(item for item in result["alternatives"] if item["strategy"] == "rent")
            self.assertEqual(rent["status"], "partial")
            self.assertIn("missing_rent_assumption", rent["gap_codes"])
            self.assertIn("missing_vacancy_assumption", rent["gap_codes"])

    def test_missing_sale_price_becomes_gap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "real-estate.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["properties"][0]["sale_assumption"].pop("estimated_sale_price")
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_real_estate_plan(input_path, output)

            sell = next(item for item in result["alternatives"] if item["strategy"] == "sell")
            self.assertEqual(sell["status"], "partial")
            self.assertIn("missing_sale_price", sell["gap_codes"])

    def test_missing_declared_taxes_are_not_inferred(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "real-estate.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["properties"][0]["declared_taxes"] = []
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_real_estate_plan(input_path, output)

            self.assertEqual(result["status"], "partial")
            self.assertIn("missing_real_estate_tax_input", {gap["code"] for gap in result["data_gaps"]})

    def test_invalid_ownership_share_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "real-estate.json"
            output = root / "snapshot.json"
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["properties"][0]["ownership"][0]["share"] = "1.20"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(RealEstatePlanError, "share"):
                build_real_estate_plan(input_path, output)


if __name__ == "__main__":
    unittest.main()
