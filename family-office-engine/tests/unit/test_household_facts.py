import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.household_facts import (
    HouseholdFactsError,
    import_household_facts,
    validate_household_facts,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_HOUSEHOLD = REPOSITORY_ROOT / "family-office-engine" / "examples" / "household-facts-sample.json"


def valid_household() -> dict:
    return json.loads(SAMPLE_HOUSEHOLD.read_text(encoding="utf-8"))


class HouseholdFactsTest(unittest.TestCase):
    def test_validate_accepts_sample_household(self):
        gaps = validate_household_facts(valid_household())

        self.assertEqual(gaps, [])

    def test_import_writes_normalized_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "household-facts.json"
            output_path = root / "household-facts.snapshot.json"
            input_path.write_text(json.dumps(valid_household()), encoding="utf-8")

            result = import_household_facts(input_path, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "household-facts/v1")
            self.assertEqual(written["record_type"], "HouseholdFactsSnapshot")
            self.assertEqual(written["status"], "complete")
            self.assertEqual(len(written["persons"]), 3)

    def test_validate_rejects_duplicate_person_ids(self):
        household = valid_household()
        household["persons"][1]["person_id"] = "person_self"

        with self.assertRaisesRegex(HouseholdFactsError, "Duplicate person_id"):
            validate_household_facts(household)

    def test_validate_rejects_relationship_to_missing_person(self):
        household = valid_household()
        household["relationships"][0]["to_person_id"] = "missing_person"

        with self.assertRaisesRegex(HouseholdFactsError, "unknown person"):
            validate_household_facts(household)

    def test_validate_rejects_period_with_end_before_start(self):
        household = valid_household()
        household["relationships"][0]["valid_from"] = "2026-01-01"
        household["relationships"][0]["valid_to"] = "2025-01-01"

        with self.assertRaisesRegex(HouseholdFactsError, "valid_to"):
            validate_household_facts(household)

    def test_validate_rejects_economic_role_for_missing_person(self):
        household = valid_household()
        household["economic_roles"][0]["person_id"] = "missing_person"

        with self.assertRaisesRegex(HouseholdFactsError, "economic_roles"):
            validate_household_facts(household)

    def test_validate_marks_missing_birth_year_and_tax_residence_as_gaps(self):
        household = valid_household()
        del household["persons"][2]["birth_year"]
        household["tax_residences"] = household["tax_residences"][:2]

        gaps = validate_household_facts(household)

        gap_codes = [gap["code"] for gap in gaps]
        self.assertIn("missing_birth_date_or_year", gap_codes)
        self.assertIn("missing_tax_residence", gap_codes)

    def test_validate_requires_exactly_one_self(self):
        household = valid_household()
        household["persons"][0]["role"] = "other"

        with self.assertRaisesRegex(HouseholdFactsError, "Exactly one"):
            validate_household_facts(household)


if __name__ == "__main__":
    unittest.main()
