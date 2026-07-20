import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.liquidity_plan import (
    LiquidityPlanError,
    build_liquidity_plan,
)


class LiquidityPlanTest(unittest.TestCase):
    def test_builds_stable_plan_with_shortfall_and_blocked_assets(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = _write_json(root / "liquidity-input.json", _input())
            net_worth_path = _write_json(root / "net-worth.json", _net_worth())
            availability_path = _write_json(root / "availability.json", _availability())
            goals_path = _write_json(root / "goals.json", _planning_goals())

            first = build_liquidity_plan(
                input_path,
                root / "first.json",
                net_worth_snapshot_path=net_worth_path,
                asset_availability_snapshot_path=availability_path,
                planning_goals_snapshot_path=goals_path,
            )
            second = build_liquidity_plan(
                input_path,
                root / "second.json",
                net_worth_snapshot_path=net_worth_path,
                asset_availability_snapshot_path=availability_path,
                planning_goals_snapshot_path=goals_path,
            )

            self.assertEqual(first["schema_version"], "liquidity-plan/v1")
            self.assertEqual(first["status"], "partial")
            self.assertEqual(first["emergency_reserve"]["target_amount"], "36000.00")
            self.assertEqual(first["emergency_reserve"]["funded_amount"], "12000.00")
            self.assertEqual(first["emergency_reserve"]["shortfall"], "24000.00")
            self.assertEqual(first["reproducibility"]["content_hash"], second["reproducibility"]["content_hash"])
            self.assertIn("asset_family_home", {asset["asset_id"] for asset in first["blocked_current_spending_assets"]})
            self.assertIn("emergency_reserve_shortfall", {gap["code"] for gap in first["data_gaps"]})

    def test_foreign_currency_asset_is_gap_without_conversion(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth = _net_worth()
            net_worth["components"][1]["currency"] = "USD"

            result = build_liquidity_plan(
                _write_json(root / "liquidity-input.json", _input()),
                root / "liquidity.json",
                net_worth_snapshot_path=_write_json(root / "net-worth.json", net_worth),
                asset_availability_snapshot_path=_write_json(root / "availability.json", _availability()),
                planning_goals_snapshot_path=_write_json(root / "goals.json", _planning_goals()),
            )

            self.assertIn("foreign_currency_asset", {gap["code"] for gap in result["data_gaps"]})
            brokerage = next(asset for asset in result["asset_assignments"] if asset["asset_id"] == "asset_brokerage")
            self.assertTrue(brokerage["blocks_current_spending"])

    def test_foreign_currency_immediate_asset_does_not_fund_reserve(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth = _net_worth()
            net_worth["components"][0]["currency"] = "USD"

            result = build_liquidity_plan(
                _write_json(root / "liquidity-input.json", _input()),
                root / "liquidity.json",
                net_worth_snapshot_path=_write_json(root / "net-worth.json", net_worth),
                asset_availability_snapshot_path=_write_json(root / "availability.json", _availability()),
                planning_goals_snapshot_path=_write_json(root / "goals.json", _planning_goals()),
            )

            cash = next(asset for asset in result["asset_assignments"] if asset["asset_id"] == "asset_cash")
            self.assertEqual(cash["bucket"], "restricted")
            self.assertTrue(cash["blocks_current_spending"])
            self.assertEqual(result["emergency_reserve"]["funded_amount"], "0.00")
            self.assertEqual(result["emergency_reserve"]["shortfall"], "36000.00")

    def test_concentration_warning_uses_declared_threshold(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            plan_input = _input()
            plan_input["concentration_threshold"] = "0.40"

            result = build_liquidity_plan(
                _write_json(root / "liquidity-input.json", plan_input),
                root / "liquidity.json",
                net_worth_snapshot_path=_write_json(root / "net-worth.json", _net_worth()),
                asset_availability_snapshot_path=_write_json(root / "availability.json", _availability()),
                planning_goals_snapshot_path=_write_json(root / "goals.json", _planning_goals()),
            )

            self.assertIn("asset_concentration", {warning["code"] for warning in result["warnings"]})

    def test_missing_snapshots_block_without_invented_assets(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            result = build_liquidity_plan(_write_json(root / "liquidity-input.json", _input()), root / "liquidity.json")

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertEqual(result["asset_assignments"], [])
            self.assertIn("missing_net_worth_snapshot", {gap["code"] for gap in result["data_gaps"]})

    def test_rejects_invalid_monthly_expenses(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            plan_input = _input()
            plan_input["monthly_expenses"] = "0"

            with self.assertRaisesRegex(LiquidityPlanError, "monthly_expenses must be positive"):
                build_liquidity_plan(_write_json(root / "liquidity-input.json", plan_input), root / "liquidity.json")


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _input() -> dict:
    return {
        "schema_version": "liquidity-plan-input/v1",
        "record_type": "LiquidityPlanInput",
        "household_id": "synthetic_household",
        "as_of_date": "2026-07-18",
        "base_currency": "EUR",
        "monthly_expenses": "3000.00",
        "minimum_reserve_months": 6,
        "concentration_threshold": "0.60",
        "data_gaps": [],
    }


def _net_worth() -> dict:
    return {
        "schema_version": "net-worth/v1",
        "record_type": "NetWorthSnapshot",
        "components": [
            {
                "id": "asset_cash",
                "label": "Cash account",
                "type": "asset",
                "asset_class": "cash",
                "value": "12000.00",
                "currency": "EUR",
            },
            {
                "id": "asset_brokerage",
                "label": "Brokerage account",
                "type": "asset",
                "asset_class": "brokerage",
                "value": "30000.00",
                "currency": "EUR",
            },
            {
                "id": "asset_family_home",
                "label": "Family home",
                "type": "asset",
                "asset_class": "real_estate",
                "value": "180000.00",
                "currency": "EUR",
            },
        ],
        "data_gaps": [],
    }


def _availability() -> dict:
    return {
        "schema_version": "asset-availability/v1",
        "record_type": "AssetAvailabilitySnapshot",
        "classifications": [
            {
                "asset_id": "asset_cash",
                "liquidity_tier": "immediate",
                "first_available_date": "2026-07-18",
                "constraints": ["none"],
                "risk_level": "low",
            },
            {
                "asset_id": "asset_brokerage",
                "liquidity_tier": "short_term",
                "first_available_date": "2026-07-25",
                "constraints": ["none"],
                "risk_level": "medium",
            },
            {
                "asset_id": "asset_family_home",
                "liquidity_tier": "illiquid",
                "first_available_date": "2027-07-18",
                "constraints": ["co_ownership", "sale_process"],
                "risk_level": "illiquid",
            },
        ],
        "data_gaps": [],
    }


def _planning_goals() -> dict:
    return {
        "schema_version": "planning-goals/v1",
        "record_type": "PlanningGoalsSnapshot",
        "liquidity_policy": {"minimum_reserve_months": 12, "preferred_bucket": "emergency_reserve"},
        "data_gaps": [],
    }


if __name__ == "__main__":
    unittest.main()
