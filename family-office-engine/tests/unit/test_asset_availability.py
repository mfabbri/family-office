import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.asset_availability import (
    AssetAvailabilityError,
    import_asset_availability,
    validate_asset_availability,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_AVAILABILITY = REPOSITORY_ROOT / "family-office-engine" / "examples" / "asset-availability-sample.json"
SAMPLE_OWNERSHIP = REPOSITORY_ROOT / "family-office-engine" / "examples" / "ownership-beneficiary-graph-sample.json"


def valid_availability() -> dict:
    return json.loads(SAMPLE_AVAILABILITY.read_text(encoding="utf-8"))


def ownership_snapshot() -> dict:
    ownership = json.loads(SAMPLE_OWNERSHIP.read_text(encoding="utf-8"))
    return {
        "schema_version": "ownership-beneficiary-graph/v1",
        "record_type": "OwnershipBeneficiaryGraphSnapshot",
        "assets": ownership["assets"],
    }


class AssetAvailabilityTest(unittest.TestCase):
    def test_validate_accepts_sample_availability(self):
        gaps = validate_asset_availability(valid_availability(), ownership_snapshot())

        self.assertEqual(gaps, [])

    def test_import_writes_normalized_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "asset-availability.json"
            ownership_path = root / "ownership-beneficiary-graph.snapshot.json"
            output_path = root / "asset-availability.snapshot.json"
            input_path.write_text(json.dumps(valid_availability()), encoding="utf-8")
            ownership_path.write_text(json.dumps(ownership_snapshot()), encoding="utf-8")

            result = import_asset_availability(input_path, output_path, ownership_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "asset-availability/v1")
            self.assertEqual(written["record_type"], "AssetAvailabilitySnapshot")
            self.assertEqual(written["status"], "complete")
            self.assertEqual(len(written["classifications"]), 3)
            self.assertIn("liquidity_tiers", written["taxonomy"])

    def test_validate_rejects_unknown_asset_when_ownership_snapshot_is_available(self):
        availability = valid_availability()
        availability["classifications"][0]["asset_id"] = "missing_asset"

        with self.assertRaisesRegex(AssetAvailabilityError, "unknown asset"):
            validate_asset_availability(availability, ownership_snapshot())

    def test_validate_records_missing_asset_class_as_gap(self):
        availability = valid_availability()
        availability["classifications"][0]["asset_class"] = None

        gaps = validate_asset_availability(availability, ownership_snapshot())

        self.assertIn("missing_asset_class", [gap["code"] for gap in gaps])

    def test_validate_rejects_immediate_liquidity_after_as_of_date(self):
        availability = valid_availability()
        availability["classifications"][2]["first_available_date"] = "2026-02-01"

        with self.assertRaisesRegex(AssetAvailabilityError, "immediate liquidity"):
            validate_asset_availability(availability, ownership_snapshot())

    def test_validate_records_missing_classification_for_owned_asset(self):
        availability = valid_availability()
        availability["classifications"] = availability["classifications"][:2]

        gaps = validate_asset_availability(availability, ownership_snapshot())

        self.assertIn("missing_asset_availability", [gap["code"] for gap in gaps])

    def test_validate_accepts_foreign_policy_with_unknown_tax_treatment_as_gap(self):
        availability = valid_availability()
        availability["classifications"][0].update(
            {
                "asset_class": "insurance_policy",
                "constraints": ["policy_terms", "foreign_reporting"],
                "jurisdiction": "ES",
                "liquidity_tier": "locked_until_date",
                "risk_level": "unknown",
                "tax_treatment": "unknown",
            }
        )

        gaps = validate_asset_availability(availability, ownership_snapshot())

        self.assertIn("unknown_risk_level", [gap["code"] for gap in gaps])
        self.assertIn("unknown_tax_treatment", [gap["code"] for gap in gaps])

    def test_validate_accepts_locked_pension_fund(self):
        availability = valid_availability()
        availability["classifications"][0].update(
            {
                "asset_class": "pension_fund",
                "constraints": ["pension_lock"],
                "first_available_date": "2035-01-01",
                "liquidity_tier": "locked_until_date",
                "tax_treatment": "pension_taxation",
            }
        )

        gaps = validate_asset_availability(availability, ownership_snapshot())

        self.assertEqual(gaps, [])

    def test_validate_accepts_unknown_first_available_date_as_gap(self):
        availability = valid_availability()
        availability["classifications"][0].update(
            {
                "asset_class": "pension_fund",
                "constraints": ["pension_lock"],
                "first_available_date": "unknown",
                "liquidity_tier": "locked_until_date",
                "tax_treatment": "pension_taxation",
            }
        )

        gaps = validate_asset_availability(availability, ownership_snapshot())

        self.assertIn("missing_first_available_date", [gap["code"] for gap in gaps])


if __name__ == "__main__":
    unittest.main()
