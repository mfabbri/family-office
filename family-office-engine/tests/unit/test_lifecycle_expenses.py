import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.lifecycle_expenses import (
    LifecycleExpensesError,
    build_lifecycle_expenses,
)


class LifecycleExpensesTest(unittest.TestCase):
    def test_annual_expense_applies_explicit_inflation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            plan_path = _write_json(root / "expenses.json", _expense_plan())
            output_path = root / "lifecycle-expenses.snapshot.json"

            result = build_lifecycle_expenses(plan_path, output_path)

            self.assertEqual(result["schema_version"], "lifecycle-expenses/v1")
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["yearly_cashflow"][0]["total_expenses"], "30000.00")
            self.assertEqual(result["yearly_cashflow"][1]["total_expenses"], "30600.00")
            self.assertEqual(result["summary"]["max_yearly_expenses"], "31212.00")

    def test_limited_period_has_no_cashflow_outside_window(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            plan = _expense_plan()
            plan["expense_entries"][0]["start_year"] = 2030
            plan["expense_entries"][0]["end_year"] = 2031
            plan_path = _write_json(root / "expenses.json", plan)
            output_path = root / "lifecycle-expenses.snapshot.json"

            result = build_lifecycle_expenses(plan_path, output_path)

            self.assertEqual([year["year"] for year in result["yearly_cashflow"]], [2030, 2031])

    def test_one_time_expense_can_use_timeline_event_year(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            plan = _expense_plan(entries=[_one_time_expense(event_id="event_university")])
            plan_path = _write_json(root / "expenses.json", plan)
            timeline_path = _write_json(root / "timeline.json", _timeline_snapshot())
            output_path = root / "lifecycle-expenses.snapshot.json"

            result = build_lifecycle_expenses(plan_path, output_path, timeline_snapshot_path=timeline_path)

            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["expense_entries"][0]["start_year"], 2032)
            self.assertEqual(result["yearly_cashflow"], [
                {
                    "year": 2032,
                    "total_expenses": "12000.00",
                    "currency": "EUR",
                    "categories": {"education": "12000.00"},
                    "items": [
                        {
                            "entry_id": "expense_university_fee",
                            "category": "education",
                            "phase": "children_university",
                            "amount": "12000.00",
                            "currency": "EUR",
                        }
                    ],
                }
            ])

    def test_missing_year_becomes_gap_without_invented_cashflow(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            plan = _expense_plan()
            plan["expense_entries"][0]["start_year"] = None
            plan_path = _write_json(root / "expenses.json", plan)
            output_path = root / "lifecycle-expenses.snapshot.json"

            result = build_lifecycle_expenses(plan_path, output_path)

            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["yearly_cashflow"], [])
            self.assertIn("missing_expense_start_year", {gap["code"] for gap in result["data_gaps"]})

    def test_unknown_person_is_rejected_when_household_snapshot_is_available(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            plan = _expense_plan(entries=[_annual_expense(owner_type="person", person_id="missing_person")])
            plan_path = _write_json(root / "expenses.json", plan)
            household_path = _write_json(root / "household.json", _household_snapshot())
            output_path = root / "lifecycle-expenses.snapshot.json"

            with self.assertRaisesRegex(LifecycleExpensesError, "unknown person"):
                build_lifecycle_expenses(plan_path, output_path, household_snapshot_path=household_path)

    def test_missing_category_is_validation_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            plan = _expense_plan()
            plan["expense_entries"][0]["category"] = ""
            plan_path = _write_json(root / "expenses.json", plan)
            output_path = root / "lifecycle-expenses.snapshot.json"

            with self.assertRaisesRegex(LifecycleExpensesError, "category is required"):
                build_lifecycle_expenses(plan_path, output_path)


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _expense_plan(entries: list[dict] | None = None) -> dict:
    return {
        "schema_version": "lifecycle-expenses/v1",
        "record_type": "LifecycleExpensePlan",
        "household_id": "synthetic_household",
        "as_of_date": "2026-07-17",
        "expense_entries": entries if entries is not None else [_annual_expense()],
        "data_gaps": [],
    }


def _annual_expense(owner_type: str = "household", person_id: str | None = None) -> dict:
    return {
        "entry_id": "expense_household_living",
        "category": "living",
        "phase": "working_life",
        "owner_type": owner_type,
        "person_id": person_id,
        "frequency": "annual",
        "start_year": 2026,
        "end_year": 2028,
        "amount": "30000.00",
        "currency": "EUR",
        "annual_inflation_rate": "0.02",
        "provenance": "synthetic fixture",
    }


def _one_time_expense(event_id: str) -> dict:
    return {
        "entry_id": "expense_university_fee",
        "category": "education",
        "phase": "children_university",
        "owner_type": "household",
        "frequency": "one_time",
        "event_id": event_id,
        "amount": "12000.00",
        "currency": "EUR",
        "annual_inflation_rate": "0",
        "provenance": "synthetic fixture",
    }


def _household_snapshot() -> dict:
    return {
        "schema_version": "household-facts/v1",
        "record_type": "HouseholdFactsSnapshot",
        "persons": [{"person_id": "person_self"}],
    }


def _timeline_snapshot() -> dict:
    return {
        "schema_version": "timeline-events/v1",
        "record_type": "TimelineEventsSnapshot",
        "occurrences": [
            {
                "event_id": "event_university",
                "event_type": "extraordinary_expense",
                "occurrence_date": "2032-09-01",
                "sequence": 1,
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
