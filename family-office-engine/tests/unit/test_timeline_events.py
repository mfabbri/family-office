import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.timeline_events import (
    TimelineEventsError,
    import_timeline_events,
    validate_timeline_events,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_TIMELINE = REPOSITORY_ROOT / "family-office-engine" / "examples" / "timeline-events-sample.json"
SAMPLE_HOUSEHOLD = REPOSITORY_ROOT / "family-office-engine" / "examples" / "household-facts-sample.json"
SAMPLE_ASSET_AVAILABILITY = REPOSITORY_ROOT / "family-office-engine" / "examples" / "asset-availability-sample.json"
SAMPLE_POLICY = REPOSITORY_ROOT / "family-office-rules" / "timeline" / "default-overlap-policy.json"


def valid_timeline() -> dict:
    return json.loads(SAMPLE_TIMELINE.read_text(encoding="utf-8"))


def household_snapshot() -> dict:
    household = json.loads(SAMPLE_HOUSEHOLD.read_text(encoding="utf-8"))
    return {
        "schema_version": "household-facts/v1",
        "record_type": "HouseholdFactsSnapshot",
        "persons": household["persons"],
    }


def asset_availability_snapshot() -> dict:
    availability = json.loads(SAMPLE_ASSET_AVAILABILITY.read_text(encoding="utf-8"))
    return {
        "schema_version": "asset-availability/v1",
        "record_type": "AssetAvailabilitySnapshot",
        "classifications": availability["classifications"],
    }


def policy() -> dict:
    return json.loads(SAMPLE_POLICY.read_text(encoding="utf-8"))


class TimelineEventsTest(unittest.TestCase):
    def test_validate_accepts_sample_timeline(self):
        gaps, occurrences = validate_timeline_events(
            valid_timeline(),
            household_snapshot(),
            asset_availability_snapshot(),
            policy(),
        )

        self.assertEqual(gaps, [])
        self.assertEqual(len(occurrences), 12)

    def test_import_writes_normalized_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "timeline-events.json"
            policy_path = root / "timeline-policy.json"
            household_path = root / "household-facts.snapshot.json"
            availability_path = root / "asset-availability.snapshot.json"
            output_path = root / "timeline-events.snapshot.json"
            input_path.write_text(json.dumps(valid_timeline()), encoding="utf-8")
            policy_path.write_text(json.dumps(policy()), encoding="utf-8")
            household_path.write_text(json.dumps(household_snapshot()), encoding="utf-8")
            availability_path.write_text(json.dumps(asset_availability_snapshot()), encoding="utf-8")

            result = import_timeline_events(input_path, output_path, policy_path, household_path, availability_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "timeline-events/v1")
            self.assertEqual(written["record_type"], "TimelineEventsSnapshot")
            self.assertEqual(written["status"], "complete")
            self.assertEqual(len(written["events"]), 8)
            self.assertEqual(len(written["occurrences"]), 12)

    def test_validate_sorts_same_date_by_policy_priority(self):
        timeline = valid_timeline()
        timeline["events"] = [
            {
                "event_id": "event_expense_same_date",
                "event_type": "extraordinary_expense",
                "provenance": "synthetic fixture",
                "start_date": "2028-06-30",
                "timing_type": "point",
            },
            {
                "event_id": "event_deadline_same_date",
                "event_type": "deadline",
                "provenance": "synthetic fixture",
                "start_date": "2028-06-30",
                "timing_type": "point",
            },
        ]

        _, occurrences = validate_timeline_events(timeline, household_snapshot(), asset_availability_snapshot(), policy())

        self.assertEqual([item["event_id"] for item in occurrences], ["event_deadline_same_date", "event_expense_same_date"])

    def test_validate_records_missing_start_date_as_gap(self):
        timeline = valid_timeline()
        timeline["events"][0]["start_date"] = None

        gaps, _ = validate_timeline_events(timeline, household_snapshot(), asset_availability_snapshot(), policy())

        self.assertIn("missing_start_date", [gap["code"] for gap in gaps])

    def test_validate_records_missing_recurrence_end_as_gap(self):
        timeline = valid_timeline()
        timeline["events"][2]["recurrence"] = {
            "frequency": "annual",
            "interval": 1,
        }

        gaps, _ = validate_timeline_events(timeline, household_snapshot(), asset_availability_snapshot(), policy())

        self.assertIn("missing_recurrence_end", [gap["code"] for gap in gaps])

    def test_validate_rejects_unknown_person_when_household_snapshot_is_available(self):
        timeline = valid_timeline()
        timeline["events"][0]["subject_person_id"] = "missing_person"

        with self.assertRaisesRegex(TimelineEventsError, "unknown person"):
            validate_timeline_events(timeline, household_snapshot(), asset_availability_snapshot(), policy())

    def test_validate_rejects_unknown_asset_when_availability_snapshot_is_available(self):
        timeline = valid_timeline()
        timeline["events"][3]["related_asset_id"] = "missing_asset"

        with self.assertRaisesRegex(TimelineEventsError, "unknown asset"):
            validate_timeline_events(timeline, household_snapshot(), asset_availability_snapshot(), policy())

    def test_validate_rejects_overlapping_residence_periods_for_same_person(self):
        timeline = valid_timeline()
        timeline["events"].append(
            {
                "description": "Synthetic overlapping residence.",
                "end_date": "2026-12-31",
                "event_id": "event_residence_overlap",
                "event_type": "residence_change",
                "provenance": "synthetic fixture",
                "start_date": "2025-06-01",
                "subject_person_id": "person_self",
                "timing_type": "period",
            }
        )

        with self.assertRaisesRegex(TimelineEventsError, "overlapping period"):
            validate_timeline_events(timeline, household_snapshot(), asset_availability_snapshot(), policy())

    def test_validate_rejects_multiple_retirement_events_for_same_person(self):
        timeline = valid_timeline()
        timeline["events"].append(
            {
                "event_id": "event_self_retirement_duplicate",
                "event_type": "retirement",
                "provenance": "synthetic fixture",
                "start_date": "2037-01-01",
                "subject_person_id": "person_self",
                "timing_type": "point",
            }
        )

        with self.assertRaisesRegex(TimelineEventsError, "exclusive event"):
            validate_timeline_events(timeline, household_snapshot(), asset_availability_snapshot(), policy())


if __name__ == "__main__":
    unittest.main()
