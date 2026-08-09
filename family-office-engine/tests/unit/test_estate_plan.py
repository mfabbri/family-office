import copy
import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.estate_plan import (
    EstatePlanError,
    build_estate_plan,
    load_estate_plan_rule_pack,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "succession" / "italy-2026-v2.json"
SAMPLE_INPUT = REPOSITORY_ROOT / "family-office-engine" / "examples" / "estate-plan-sample.json"


class EstatePlanTest(unittest.TestCase):
    def test_builds_spouse_two_children_plan_with_conflict_and_foreign_gap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "estate-plan.snapshot.json"

            result = build_estate_plan(SAMPLE_INPUT, RULE_PACK, output)
            written = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "estate-plan/v2")
            self.assertEqual(written["record_type"], "EstatePlanSnapshot")
            self.assertEqual(written["family_case"], "spouse_multiple_children")
            self.assertEqual(written["totals"]["known_estate_mass"], "870000.00")
            self.assertEqual(written["totals"]["declared_notional_donations"], "100000.00")
            self.assertEqual(written["totals"]["notional_mass"], "970000.00")
            self.assertEqual(written["forced_heirs"][0]["reserved_amount"], "242500.00")
            self.assertEqual(written["forced_heirs"][1]["reserved_amount"], "242500.00")
            self.assertEqual(written["summary"]["scenario_count"], 2)
            self.assertGreaterEqual(written["summary"]["conflict_count"], 1)
            self.assertIn("foreign_succession_review_required", {gap["code"] for gap in written["data_gaps"]})
            self.assertTrue(any(flag["code"] == "no_opaque_scheme" for flag in written["scenarios"][0]["operational_flags"]))

    def test_complete_domestic_equalized_plan_has_no_conflict(self):
        data = {
            "schema_version": "estate-plan/v2",
            "record_type": "EstatePlanInput",
            "household_id": "synthetic",
            "as_of_date": "2026-07-29",
            "base_currency": "EUR",
            "decedent_person_id": "self",
            "family": {
                "has_spouse": True,
                "children": [{"person_id": "child_1"}, {"person_id": "child_2"}],
            },
            "assets": [
                {
                    "asset_id": "cash",
                    "asset_class": "cash",
                    "jurisdiction": "IT",
                    "currency": "EUR",
                    "gross_value": "600000.00",
                    "ownership_share": "1",
                    "provenance": [{"source_id": "synthetic"}],
                }
            ],
            "tax_liquidity": {
                "available_immediate_liquidity": "50000.00",
                "provenance": [{"source_id": "synthetic"}],
            },
            "scenarios": [
                {
                    "scenario_id": "equal",
                    "allocations": [
                        {"beneficiary_person_id": "spouse", "relationship": "spouse", "asset_id": "cash", "share": "0.34"},
                        {"beneficiary_person_id": "child_1", "relationship": "child", "asset_id": "cash", "share": "0.33"},
                        {"beneficiary_person_id": "child_2", "relationship": "child", "asset_id": "cash", "share": "0.33"},
                    ],
                }
            ],
            "prior_donations": [],
            "insurance_policies": [],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "estate-plan.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_estate_plan(input_path, RULE_PACK, root / "out.json")

            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["scenarios"][0]["status"], "complete")
            self.assertEqual(result["scenarios"][0]["reserve_conflicts"], [])
            self.assertEqual(result["scenarios"][0]["estimated_transfer_taxes"], "0.00")

    def test_unknown_policy_treatment_and_unallocated_asset_are_gaps(self):
        data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
        data["assets"] = data["assets"][:1]
        data["insurance_policies"][0]["estate_treatment"] = "unknown"
        data["scenarios"] = [{"scenario_id": "empty", "allocations": []}]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "estate-plan.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_estate_plan(input_path, RULE_PACK, root / "out.json")

            gap_codes = {gap["code"] for gap in result["data_gaps"]}
            self.assertEqual(result["status"], "partial")
            self.assertIn("unknown_insurance_estate_treatment", gap_codes)
            self.assertIn("missing_scenario_allocations", gap_codes)

    def test_tax_estimate_for_other_relationship_uses_rule_pack(self):
        data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
        data["family"] = {"has_spouse": False, "children": [{"person_id": "child_1"}]}
        data["assets"] = [
            {
                "asset_id": "cash",
                "asset_class": "cash",
                "jurisdiction": "IT",
                "currency": "EUR",
                "gross_value": "100000.00",
                "ownership_share": "1",
                "provenance": [{"source_id": "synthetic"}],
            }
        ]
        data["prior_donations"] = []
        data["insurance_policies"] = []
        data["scenarios"] = [
            {
                "scenario_id": "friend",
                "allocations": [
                    {"beneficiary_person_id": "friend_1", "relationship": "other", "asset_id": "cash", "share": "1"}
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "estate-plan.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            result = build_estate_plan(input_path, RULE_PACK, root / "out.json")

            self.assertEqual(result["scenarios"][0]["tax_estimates"][0]["rule_id"], "it.transfer-tax.other.2026")
            self.assertEqual(result["scenarios"][0]["tax_estimates"][0]["estimated_tax"], "8000.00")
            self.assertEqual(result["scenarios"][0]["reserve_conflicts"][0]["beneficiary_person_id"], "child_1")

    def test_load_rule_pack_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "rules.json"
            path.write_text(json.dumps({"schema_version": "wrong"}), encoding="utf-8")

            with self.assertRaisesRegex(EstatePlanError, "missing field"):
                load_estate_plan_rule_pack(path)


if __name__ == "__main__":
    unittest.main()
