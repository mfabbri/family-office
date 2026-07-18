import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.planning_goals import (
    PlanningGoalsError,
    import_planning_goals,
    validate_planning_goals,
)


class PlanningGoalsTest(unittest.TestCase):
    def test_import_complete_goals_with_stable_hash(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = _write_json(root / "planning-goals.json", _planning_goals())
            timeline_path = _write_json(root / "timeline.json", _timeline_snapshot())

            first = import_planning_goals(input_path, root / "goals-1.json", timeline_path)
            second = import_planning_goals(input_path, root / "goals-2.json", timeline_path)

            self.assertEqual(first["schema_version"], "planning-goals/v1")
            self.assertEqual(first["record_type"], "PlanningGoalsSnapshot")
            self.assertEqual(first["status"], "complete")
            self.assertEqual(len(first["objectives"]), 2)
            self.assertEqual(len(first["constraints"]), 2)
            self.assertEqual(first["data_gaps"], [])
            self.assertEqual(first["reproducibility"]["content_hash"], second["reproducibility"]["content_hash"])

    def test_duplicate_priority_is_rejected(self):
        data = _planning_goals()
        data["objectives"][1]["priority"] = 1

        with self.assertRaisesRegex(PlanningGoalsError, "Duplicate objective priority"):
            validate_planning_goals(data, _timeline_snapshot())

    def test_invalid_range_threshold_is_rejected(self):
        data = _planning_goals()
        data["constraints"][0]["threshold"] = {
            "metric": "reserve_months",
            "operator": "range",
            "unit": "months",
            "min_value": 12,
            "max_value": 6,
        }

        with self.assertRaisesRegex(PlanningGoalsError, "max_value must be greater than or equal to min_value"):
            validate_planning_goals(data, _timeline_snapshot())

    def test_unknown_objective_reference_is_rejected(self):
        data = _planning_goals()
        data["constraints"][0]["applies_to_objective_ids"] = ["missing_objective"]

        with self.assertRaisesRegex(PlanningGoalsError, "references unknown objective"):
            validate_planning_goals(data, _timeline_snapshot())

    def test_missing_timeline_reference_creates_gap(self):
        data = _planning_goals()
        data["constraints"][1]["timeline_event_ids"] = ["missing_event"]

        gaps = validate_planning_goals(data, _timeline_snapshot())

        self.assertIn("timeline_event_reference_missing", {gap["code"] for gap in gaps})

    def test_missing_optional_profiles_create_gaps(self):
        data = _planning_goals()
        data.pop("risk_profile")
        data.pop("liquidity_policy")
        data["objectives"][0].pop("target")
        data["constraints"] = []

        gaps = validate_planning_goals(data, _timeline_snapshot())

        self.assertIn("missing_risk_profile", {gap["code"] for gap in gaps})
        self.assertIn("missing_liquidity_policy", {gap["code"] for gap in gaps})
        self.assertIn("missing_objective_target", {gap["code"] for gap in gaps})
        self.assertIn("missing_constraints", {gap["code"] for gap in gaps})

    def test_rejects_wrong_schema(self):
        data = _planning_goals()
        data["schema_version"] = "wrong/v1"

        with self.assertRaisesRegex(PlanningGoalsError, "Unsupported planning goals schema"):
            validate_planning_goals(data, _timeline_snapshot())


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _planning_goals() -> dict:
    return {
        "schema_version": "planning-goals/v1",
        "record_type": "PlanningGoals",
        "household_id": "synthetic_household",
        "as_of_date": "2026-07-18",
        "planning_horizon": {"start_year": 2026, "end_year": 2055},
        "risk_profile": {"capacity": "medium", "tolerance": "medium", "max_loss_ratio": "0.20"},
        "liquidity_policy": {"minimum_reserve_months": 12, "preferred_bucket": "emergency_reserve"},
        "objectives": [
            {
                "objective_id": "objective_emergency_reserve",
                "label": "Maintain emergency reserve",
                "category": "liquidity",
                "priority": 1,
                "time_horizon_year": 2027,
                "target": {"metric": "reserve_months", "operator": "min", "unit": "months", "value": 12},
            },
            {
                "objective_id": "objective_retirement_income",
                "label": "Sustain retirement income",
                "category": "retirement_income",
                "priority": 2,
                "time_horizon_year": 2035,
                "target": {"metric": "annual_net_need", "operator": "target", "unit": "EUR/year", "value": 48000},
            },
        ],
        "constraints": [
            {
                "constraint_id": "constraint_emergency_reserve",
                "label": "Keep emergency reserve available",
                "constraint_type": "liquidity",
                "severity": "hard",
                "priority": 1,
                "applies_to_objective_ids": ["objective_emergency_reserve", "objective_retirement_income"],
                "threshold": {"metric": "reserve_months", "operator": "min", "unit": "months", "value": 12},
            },
            {
                "constraint_id": "constraint_retirement_timing",
                "label": "Retirement date drives the income horizon",
                "constraint_type": "timing",
                "severity": "soft",
                "priority": 2,
                "applies_to_objective_ids": ["objective_retirement_income"],
                "timeline_event_ids": ["event_self_retirement"],
                "threshold": {"metric": "target_year", "operator": "target", "unit": "year", "value": 2035},
            },
        ],
        "data_gaps": [],
    }


def _timeline_snapshot() -> dict:
    return {
        "schema_version": "timeline-events/v1",
        "record_type": "TimelineEventsSnapshot",
        "status": "complete",
        "events": [{"event_id": "event_self_retirement", "event_type": "retirement"}],
        "data_gaps": [],
    }


if __name__ == "__main__":
    unittest.main()
