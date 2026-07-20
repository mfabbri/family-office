import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.decumulation_strategy import (
    DecumulationStrategyError,
    build_decumulation_strategy,
)


class DecumulationStrategyTest(unittest.TestCase):
    def test_builds_stable_strategy_with_multiple_policies(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = _write_json(root / "policies.json", _policy_set())
            net_worth_path = _write_json(root / "net-worth.json", _net_worth())
            liquidity_path = _write_json(root / "liquidity.json", _liquidity_plan())
            pension_path = _write_json(root / "pension.json", _pension_income())
            rita_path = _write_json(root / "rita.json", _rita_options())

            first = build_decumulation_strategy(
                input_path,
                root / "first.json",
                net_worth_snapshot_path=net_worth_path,
                liquidity_plan_snapshot_path=liquidity_path,
                pension_income_snapshot_path=pension_path,
                rita_options_snapshot_path=rita_path,
            )
            second = build_decumulation_strategy(
                input_path,
                root / "second.json",
                net_worth_snapshot_path=net_worth_path,
                liquidity_plan_snapshot_path=liquidity_path,
                pension_income_snapshot_path=pension_path,
                rita_options_snapshot_path=rita_path,
            )

            self.assertEqual(first["schema_version"], "decumulation-strategy/v1")
            self.assertEqual(first["status"], "partial")
            self.assertEqual(first["summary"]["policy_count"], 2)
            self.assertEqual(first["reproducibility"]["content_hash"], second["reproducibility"]["content_hash"])
            self.assertIn("asset_not_decumulable", {gap["code"] for gap in first["data_gaps"]})

    def test_rita_policy_reduces_asset_withdrawals_during_bridge(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            result = build_decumulation_strategy(
                _write_json(root / "policies.json", _policy_set()),
                root / "strategy.json",
                net_worth_snapshot_path=_write_json(root / "net-worth.json", _net_worth()),
                liquidity_plan_snapshot_path=_write_json(root / "liquidity.json", _liquidity_plan()),
                pension_income_snapshot_path=_write_json(root / "pension.json", _pension_income()),
                rita_options_snapshot_path=_write_json(root / "rita.json", _rita_options()),
            )

            bridge = next(policy for policy in result["policies"] if policy["policy_id"] == "bridge_rita")
            no_rita = next(policy for policy in result["policies"] if policy["policy_id"] == "early_no_rita")

            self.assertGreater(float(bridge["metrics"]["total_rita_net_used"]), 0)
            self.assertLess(
                float(bridge["annual_cashflows"][2]["asset_withdrawal_gross"]),
                float(no_rita["annual_cashflows"][2]["asset_withdrawal_gross"]),
            )

    def test_return_sequence_changes_final_balance(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            policies = _policy_set()
            policies["policies"][0]["annual_return_sequence"] = ["-0.20"]
            policies["policies"][1]["annual_return_sequence"] = ["0.06"]
            policies["policies"][0]["annual_spending_need"] = "20000.00"
            policies["policies"][1]["annual_spending_need"] = "20000.00"
            policies["policies"][0]["end_age"] = 75
            policies["policies"][1]["end_age"] = 75

            result = build_decumulation_strategy(
                _write_json(root / "policies.json", policies),
                root / "strategy.json",
                net_worth_snapshot_path=_write_json(root / "net-worth.json", _net_worth()),
                liquidity_plan_snapshot_path=_write_json(root / "liquidity.json", _liquidity_plan()),
                pension_income_snapshot_path=_write_json(root / "pension.json", _pension_income()),
            )

            adverse = next(policy for policy in result["policies"] if policy["policy_id"] == "bridge_rita")
            positive = next(policy for policy in result["policies"] if policy["policy_id"] == "early_no_rita")
            self.assertLess(float(adverse["metrics"]["final_balance"]), float(positive["metrics"]["final_balance"]))

    def test_longer_longevity_horizon_can_create_shortfall(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            policies = _policy_set()
            policies["policies"] = [policies["policies"][0]]
            policies["policies"][0]["end_age"] = 105
            policies["policies"][0]["annual_spending_need"] = "90000.00"

            result = build_decumulation_strategy(
                _write_json(root / "policies.json", policies),
                root / "strategy.json",
                net_worth_snapshot_path=_write_json(root / "net-worth.json", _net_worth()),
                liquidity_plan_snapshot_path=_write_json(root / "liquidity.json", _liquidity_plan()),
                pension_income_snapshot_path=_write_json(root / "pension.json", _pension_income()),
            )

            policy = result["policies"][0]
            self.assertGreater(policy["metrics"]["shortfall_year_count"], 0)
            self.assertIsNotNone(policy["metrics"]["depletion_age"])
            self.assertIn("longevity_horizon_high", {warning["code"] for warning in policy["warnings"]})

    def test_missing_snapshots_block_without_invented_assets(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            result = build_decumulation_strategy(
                _write_json(root / "policies.json", _policy_set()),
                root / "strategy.json",
            )

            self.assertEqual(result["status"], "blocked_missing_inputs")
            self.assertEqual(result["asset_pool"]["assets"], [])
            self.assertIn("missing_net_worth_snapshot", {gap["code"] for gap in result["data_gaps"]})

    def test_rejects_invalid_policy(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            policies = _policy_set()
            policies["policies"][0]["retirement_age"] = 50

            with self.assertRaisesRegex(DecumulationStrategyError, "retirement_age cannot be before current_age"):
                build_decumulation_strategy(_write_json(root / "policies.json", policies), root / "strategy.json")


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _policy_set() -> dict:
    return {
        "schema_version": "decumulation-policy-set/v1",
        "record_type": "DecumulationPolicySet",
        "household_id": "synthetic_household",
        "as_of_date": "2026-07-20",
        "base_currency": "EUR",
        "current_age": 60,
        "policies": [
            {
                "policy_id": "bridge_rita",
                "label": "Bridge with RITA",
                "retirement_age": 62,
                "end_age": 90,
                "annual_spending_need": "36000.00",
                "cash_buffer_target": "24000.00",
                "withdrawal_order": ["asset_brokerage", "asset_cash"],
                "annual_return_sequence": ["0.02"],
                "withdrawal_tax_rate": "0.10",
                "pension_tax_rate": "0.20",
                "rita_tax_rate": "0.15",
                "include_rita": True,
            },
            {
                "policy_id": "early_no_rita",
                "label": "Early without RITA",
                "retirement_age": 62,
                "end_age": 90,
                "annual_spending_need": "36000.00",
                "cash_buffer_target": "24000.00",
                "withdrawal_order": ["asset_brokerage", "asset_cash"],
                "annual_return_sequence": ["0.02"],
                "withdrawal_tax_rate": "0.10",
                "pension_tax_rate": "0.20",
                "rita_tax_rate": "0.15",
                "include_rita": False,
            },
        ],
        "data_gaps": [],
    }


def _net_worth() -> dict:
    return {
        "schema_version": "net-worth/v1",
        "record_type": "NetWorthSnapshot",
        "components": [
            {
                "id": "asset_cash",
                "label": "Cash buffer",
                "type": "asset",
                "asset_class": "cash",
                "value": "30000.00",
                "currency": "EUR",
            },
            {
                "id": "asset_brokerage",
                "label": "Brokerage",
                "type": "asset",
                "asset_class": "brokerage",
                "value": "220000.00",
                "currency": "EUR",
            },
            {
                "id": "asset_home",
                "label": "Home",
                "type": "asset",
                "asset_class": "real_estate",
                "value": "250000.00",
                "currency": "EUR",
            },
        ],
        "data_gaps": [],
    }


def _liquidity_plan() -> dict:
    return {
        "schema_version": "liquidity-plan/v1",
        "record_type": "LiquidityPlanSnapshot",
        "status": "complete",
        "asset_assignments": [
            {"asset_id": "asset_cash", "bucket": "emergency_reserve"},
            {"asset_id": "asset_brokerage", "bucket": "medium_term"},
            {"asset_id": "asset_home", "bucket": "restricted"},
        ],
        "data_gaps": [],
    }


def _pension_income() -> dict:
    return {
        "schema_version": "pension-income/v1",
        "record_type": "PensionIncomeSnapshot",
        "status": "complete",
        "summary": {
            "stream_count": 1,
            "gross_annual_recurring_total": "18000.00",
            "gross_annual_recurring_total_currency": "EUR",
        },
        "data_gaps": [],
    }


def _rita_options() -> dict:
    return {
        "schema_version": "rita-options/v1",
        "record_type": "RitaOptionsSnapshot",
        "status": "complete",
        "options": [
            {
                "option_id": "synthetic_rita",
                "gross_monthly_amount": "900.00",
                "duration_months": 36,
                "currency": "EUR",
            }
        ],
        "data_gaps": [],
    }


if __name__ == "__main__":
    unittest.main()
