import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.ownership_graph import (
    OwnershipGraphError,
    import_ownership_graph,
    validate_ownership_graph,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_OWNERSHIP = REPOSITORY_ROOT / "family-office-engine" / "examples" / "ownership-beneficiary-graph-sample.json"
SAMPLE_HOUSEHOLD = REPOSITORY_ROOT / "family-office-engine" / "examples" / "household-facts-sample.json"


def valid_graph() -> dict:
    return json.loads(SAMPLE_OWNERSHIP.read_text(encoding="utf-8"))


def household_snapshot() -> dict:
    household = json.loads(SAMPLE_HOUSEHOLD.read_text(encoding="utf-8"))
    return {
        "schema_version": "household-facts/v1",
        "record_type": "HouseholdFactsSnapshot",
        "persons": household["persons"],
    }


class OwnershipGraphTest(unittest.TestCase):
    def test_validate_accepts_sample_graph(self):
        gaps = validate_ownership_graph(valid_graph(), household_snapshot())

        self.assertEqual(gaps, [])

    def test_import_writes_normalized_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "ownership-beneficiaries.json"
            household_path = root / "household-facts.snapshot.json"
            output_path = root / "ownership-beneficiary-graph.snapshot.json"
            input_path.write_text(json.dumps(valid_graph()), encoding="utf-8")
            household_path.write_text(json.dumps(household_snapshot()), encoding="utf-8")

            result = import_ownership_graph(input_path, output_path, household_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "ownership-beneficiary-graph/v1")
            self.assertEqual(written["record_type"], "OwnershipBeneficiaryGraphSnapshot")
            self.assertEqual(written["status"], "complete")
            self.assertEqual(len(written["assets"]), 3)

    def test_validate_rejects_asset_ownership_above_one_hundred_percent(self):
        graph = valid_graph()
        graph["ownership_interests"][1]["share_numerator"] = 2

        with self.assertRaisesRegex(OwnershipGraphError, "exceed 100%"):
            validate_ownership_graph(graph, household_snapshot())

    def test_validate_rejects_unknown_person_when_household_snapshot_is_available(self):
        graph = valid_graph()
        graph["ownership_interests"][0]["owner_person_id"] = "missing_person"

        with self.assertRaisesRegex(OwnershipGraphError, "unknown person"):
            validate_ownership_graph(graph, household_snapshot())

    def test_validate_records_unknown_ownership_as_gap(self):
        graph = valid_graph()
        graph["ownership_interests"] = [
            {
                "interest_type": "unknown",
                "ownership_id": "own_unknown",
                "provenance": "synthetic fixture",
                "subject_id": "asset_brokerage_self",
                "subject_type": "asset",
            }
        ]

        gaps = validate_ownership_graph(graph, household_snapshot())

        self.assertIn("unknown_ownership", [gap["code"] for gap in gaps])

    def test_validate_accepts_child_owned_asset(self):
        graph = valid_graph()
        child_interest = next(
            interest for interest in graph["ownership_interests"] if interest["ownership_id"] == "own_child_account"
        )

        self.assertEqual(child_interest["owner_person_id"], "person_child")
        self.assertEqual(validate_ownership_graph(graph, household_snapshot()), [])

    def test_validate_rejects_beneficiary_shares_above_one_hundred_percent(self):
        graph = valid_graph()
        graph["beneficiaries"].append(
            {
                "beneficiary_id": "ben_brokerage_child",
                "beneficiary_person_id": "person_child",
                "beneficiary_type": "primary",
                "provenance": "synthetic fixture",
                "share_denominator": 1,
                "share_numerator": 1,
                "subject_id": "asset_brokerage_self",
                "subject_type": "asset",
            }
        )

        with self.assertRaisesRegex(OwnershipGraphError, "Beneficiary shares"):
            validate_ownership_graph(graph, household_snapshot())


if __name__ == "__main__":
    unittest.main()
