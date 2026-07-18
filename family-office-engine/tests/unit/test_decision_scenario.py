import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.decision_scenario import (
    DecisionScenarioError,
    compose_decision_scenario,
)


class DecisionScenarioTest(unittest.TestCase):
    def test_compose_complete_scenario_with_stable_hash(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            input_path = _write_json(root / "scenario-input.json", _scenario_input())

            first = _compose(root, input_path, paths, "scenario-1.json")
            second = _compose(root, input_path, paths, "scenario-2.json")

            self.assertEqual(first["schema_version"], "decision-scenario/v2")
            self.assertEqual(first["record_type"], "DecisionScenarioSnapshot")
            self.assertEqual(first["status"], "complete")
            self.assertEqual(len(first["sources"]), 6)
            self.assertEqual(first["source_summaries"]["pension_income"]["stream_count"], 1)
            self.assertEqual(first["reproducibility"]["content_hash"], second["reproducibility"]["content_hash"])

    def test_missing_optional_snapshot_creates_partial_scenario(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            input_path = _write_json(root / "scenario-input.json", _scenario_input())

            result = compose_decision_scenario(
                input_path,
                root / "scenario.json",
                household_snapshot_path=paths["household"],
                ownership_snapshot_path=paths["ownership"],
                asset_availability_snapshot_path=paths["asset_availability"],
                timeline_snapshot_path=paths["timeline"],
                pension_income_snapshot_path=None,
                lifecycle_expenses_snapshot_path=paths["lifecycle_expenses"],
            )

            self.assertEqual(result["status"], "partial")
            self.assertIn("missing_pension_income_snapshot", {gap["code"] for gap in result["data_gaps"]})

    def test_source_gaps_are_carried_into_scenario(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            lifecycle = _lifecycle_expenses_snapshot()
            lifecycle["data_gaps"] = [{"code": "missing_expense_end_year", "entry_id": "expense_living"}]
            paths["lifecycle_expenses"] = _write_json(root / "lifecycle-expenses.json", lifecycle)
            input_path = _write_json(root / "scenario-input.json", _scenario_input())

            result = _compose(root, input_path, paths, "scenario.json")

            self.assertEqual(result["status"], "partial")
            self.assertIn("lifecycle_expenses", {gap.get("source") for gap in result["data_gaps"]})

    def test_missing_market_assumptions_are_gap_not_defaulted(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            scenario_input = _scenario_input()
            scenario_input["assumptions"].pop("market")
            input_path = _write_json(root / "scenario-input.json", scenario_input)

            result = _compose(root, input_path, paths, "scenario.json")

            self.assertEqual(result["status"], "partial")
            self.assertIn("missing_market_assumptions", {gap["code"] for gap in result["data_gaps"]})

    def test_rejects_wrong_required_snapshot_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _write_sources(root)
            paths["household"] = _write_json(root / "wrong-household.json", {"schema_version": "wrong/v1"})
            input_path = _write_json(root / "scenario-input.json", _scenario_input())

            with self.assertRaisesRegex(DecisionScenarioError, "Unsupported Household facts schema"):
                _compose(root, input_path, paths, "scenario.json")


def _compose(root: Path, input_path: Path, paths: dict[str, Path], filename: str) -> dict:
    return compose_decision_scenario(
        input_path,
        root / filename,
        household_snapshot_path=paths["household"],
        ownership_snapshot_path=paths["ownership"],
        asset_availability_snapshot_path=paths["asset_availability"],
        timeline_snapshot_path=paths["timeline"],
        pension_income_snapshot_path=paths["pension_income"],
        lifecycle_expenses_snapshot_path=paths["lifecycle_expenses"],
    )


def _write_sources(root: Path) -> dict[str, Path]:
    return {
        "household": _write_json(root / "household.json", _household_snapshot()),
        "ownership": _write_json(root / "ownership.json", _ownership_snapshot()),
        "asset_availability": _write_json(root / "asset-availability.json", _asset_availability_snapshot()),
        "timeline": _write_json(root / "timeline.json", _timeline_snapshot()),
        "pension_income": _write_json(root / "pension-income.json", _pension_income_snapshot()),
        "lifecycle_expenses": _write_json(root / "lifecycle-expenses.json", _lifecycle_expenses_snapshot()),
    }


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _scenario_input() -> dict:
    return {
        "schema_version": "decision-scenario/v2",
        "record_type": "DecisionScenarioInput",
        "scenario_id": "synthetic_base_case",
        "label": "Synthetic base case",
        "as_of_date": "2026-07-17",
        "scenario_type": "planning",
        "assumptions": {
            "market": {"nominal_return": "0.03", "inflation": "0.02", "source": "synthetic fixture"},
            "withdrawal_policy": {"policy_id": "fixed_real_need", "source": "synthetic fixture"},
        },
        "objectives": [{"objective_id": "sustainability", "priority": 1}],
        "constraints": [],
        "review": {"requires_human_review": True},
    }


def _household_snapshot() -> dict:
    return {
        "schema_version": "household-facts/v1",
        "record_type": "HouseholdFactsSnapshot",
        "status": "complete",
        "persons": [{"person_id": "person_self"}, {"person_id": "person_spouse"}],
        "relationships": [{"from_person_id": "person_self", "to_person_id": "person_spouse", "relationship_type": "spouse"}],
        "data_gaps": [],
    }


def _ownership_snapshot() -> dict:
    return {
        "schema_version": "ownership-beneficiary-graph/v1",
        "record_type": "OwnershipBeneficiaryGraphSnapshot",
        "status": "complete",
        "assets": [{"asset_id": "asset_brokerage"}],
        "debts": [],
        "beneficiaries": [],
        "data_gaps": [],
    }


def _asset_availability_snapshot() -> dict:
    return {
        "schema_version": "asset-availability/v1",
        "record_type": "AssetAvailabilitySnapshot",
        "status": "complete",
        "classifications": [{"asset_id": "asset_brokerage", "liquidity_bucket": "immediate"}],
        "data_gaps": [],
    }


def _timeline_snapshot() -> dict:
    return {
        "schema_version": "timeline-events/v1",
        "record_type": "TimelineEventsSnapshot",
        "status": "complete",
        "events": [{"event_id": "retirement", "event_type": "retirement"}],
        "occurrences": [{"event_id": "retirement", "occurrence_date": "2039-05-01"}],
        "data_gaps": [],
    }


def _pension_income_snapshot() -> dict:
    return {
        "schema_version": "pension-income/v1",
        "record_type": "PensionIncomeSnapshot",
        "status": "complete",
        "income_streams": [{"stream_id": "spanish_public_pension"}],
        "summary": {
            "stream_count": 1,
            "gross_annual_recurring_total": "21000.00",
            "gross_annual_recurring_total_currency": "EUR",
        },
        "data_gaps": [],
    }


def _lifecycle_expenses_snapshot() -> dict:
    return {
        "schema_version": "lifecycle-expenses/v1",
        "record_type": "LifecycleExpensesSnapshot",
        "status": "complete",
        "expense_entries": [{"entry_id": "expense_living"}],
        "summary": {
            "entry_count": 1,
            "year_count": 3,
            "first_year": 2026,
            "last_year": 2028,
        },
        "data_gaps": [],
    }


if __name__ == "__main__":
    unittest.main()
