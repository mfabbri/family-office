import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.estate_baseline import (
    EstateBaselineError,
    build_estate_baseline,
    load_rule_pack,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ESTATE_RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "succession" / "italy-current.json"


def net_worth_snapshot(components):
    return {
        "record_type": "NetWorthSnapshot",
        "schema_version": "net-worth/v1",
        "currency": "EUR",
        "components": components,
        "totals": {"assets": "0.00", "liabilities": "0.00", "net_worth": "0.00"},
        "data_gaps": [],
    }


class EstateBaselineTest(unittest.TestCase):
    def test_builds_spouse_and_two_children_baseline(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = root / "net-worth.snapshot.json"
            output_path = root / "estate-baseline.snapshot.json"
            net_worth_path.write_text(
                json.dumps(
                    net_worth_snapshot(
                        [
                            {
                                "id": "cash_1",
                                "label": "Current account",
                                "asset_class": "cash",
                                "value": "90000.00",
                                "currency": "EUR",
                                "ownership": {"owner_id": "self", "share": "1"},
                            },
                            {
                                "id": "investment_1",
                                "label": "Portfolio",
                                "asset_class": "investment",
                                "value": "210000.00",
                                "currency": "EUR",
                                "ownership": {"owner_id": "self", "share": "1"},
                            },
                        ]
                    )
                ),
                encoding="utf-8",
            )

            result = build_estate_baseline(
                net_worth_path,
                ESTATE_RULE_PACK,
                output_path,
                has_spouse=True,
                children_count=2,
                prior_donations="0.00",
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "estate-baseline/v1")
            self.assertEqual(written["status"], "complete")
            self.assertEqual(written["totals"]["known_estate_mass"], "300000.00")
            self.assertEqual(written["theoretical_heirs"][0]["relationship"], "spouse")
            self.assertEqual(written["theoretical_heirs"][0]["known_estate_amount"], "100000.00")
            self.assertEqual(written["theoretical_heirs"][1]["relationship"], "child")
            self.assertEqual(written["theoretical_heirs"][1]["known_estate_amount"], "100000.00")
            self.assertEqual(written["theoretical_heirs"][2]["known_estate_amount"], "100000.00")
            self.assertEqual(written["liquidity"]["immediate"], "90000.00")
            self.assertEqual(written["liquidity"]["market_liquid"], "210000.00")

    def test_spouse_only_gets_known_estate_mass(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = root / "net-worth.snapshot.json"
            net_worth_path.write_text(
                json.dumps(
                    net_worth_snapshot(
                        [
                            {
                                "id": "cash_1",
                                "asset_class": "cash",
                                "value": "1000.00",
                                "currency": "EUR",
                                "ownership": {"owner_id": "self", "share": "1"},
                            }
                        ]
                    )
                ),
                encoding="utf-8",
            )

            result = build_estate_baseline(
                net_worth_path,
                ESTATE_RULE_PACK,
                root / "estate.json",
                has_spouse=True,
                children_count=0,
                prior_donations="0.00",
            )

            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["theoretical_heirs"][0]["relationship"], "spouse")
            self.assertEqual(result["theoretical_heirs"][0]["theoretical_share"], "1.0000000000")

    def test_children_only_split_equally(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = root / "net-worth.snapshot.json"
            net_worth_path.write_text(
                json.dumps(
                    net_worth_snapshot(
                        [
                            {
                                "id": "portfolio",
                                "asset_class": "investment",
                                "value": "1200.00",
                                "currency": "EUR",
                                "ownership": {"owner_id": "self", "share": "1"},
                            }
                        ]
                    )
                ),
                encoding="utf-8",
            )

            result = build_estate_baseline(
                net_worth_path,
                ESTATE_RULE_PACK,
                root / "estate.json",
                has_spouse=False,
                children_count=3,
                prior_donations="0.00",
            )

            self.assertEqual([heir["known_estate_amount"] for heir in result["theoretical_heirs"]], ["400.00", "400.00", "400.00"])

    def test_unknown_ownership_foreign_asset_and_insurance_are_gaps(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = root / "net-worth.snapshot.json"
            net_worth_path.write_text(
                json.dumps(
                    net_worth_snapshot(
                        [
                            {
                                "id": "foreign_account",
                                "asset_class": "cash",
                                "value": "5000.00",
                                "currency": "USD",
                            },
                            {
                                "id": "policy",
                                "asset_class": "insurance",
                                "value": "10000.00",
                                "currency": "EUR",
                                "ownership": {"owner_id": "self", "share": "1"},
                            },
                        ]
                    )
                ),
                encoding="utf-8",
            )

            result = build_estate_baseline(
                net_worth_path,
                ESTATE_RULE_PACK,
                root / "estate.json",
                has_spouse=True,
                children_count=1,
            )

            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["totals"]["known_estate_mass"], "10000.00")
            self.assertEqual(result["totals"]["unknown_ownership_assets"], "5000.00")
            gap_codes = [gap["code"] for gap in result["data_gaps"]]
            self.assertIn("missing_ownership", gap_codes)
            self.assertIn("foreign_currency_or_asset", gap_codes)
            self.assertIn("beneficiary_review_required", gap_codes)
            self.assertIn("prior_donations_not_provided", gap_codes)

    def test_family_case_without_spouse_or_children_is_not_supported(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = root / "net-worth.snapshot.json"
            net_worth_path.write_text(json.dumps(net_worth_snapshot([])), encoding="utf-8")

            result = build_estate_baseline(
                net_worth_path,
                ESTATE_RULE_PACK,
                root / "estate.json",
                has_spouse=False,
                children_count=0,
                prior_donations="0.00",
            )

            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["theoretical_heirs"], [])
            self.assertEqual(result["data_gaps"][0]["code"], "family_case_not_supported")

    def test_load_rule_pack_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            rule_pack_path = Path(tmp_dir) / "estate.json"
            rule_pack_path.write_text(
                json.dumps(
                    {
                        "schema_version": "wrong",
                        "rule_pack_id": "synthetic",
                        "jurisdiction": "IT",
                        "currency": "EUR",
                        "intestate_share_rules": [],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(EstateBaselineError, "Unsupported estate rule pack schema"):
                load_rule_pack(rule_pack_path)


if __name__ == "__main__":
    unittest.main()
