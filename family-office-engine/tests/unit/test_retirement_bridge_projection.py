import unittest

from family_office_engine.services.retirement_bridge_projection import (
    RetirementBridgeProjectionError,
    build_retirement_bridge_projection,
)


def _input(months=1, hypothetical_pension=None):
    assumptions = {
        "opening_available_assets": "10000.00",
        "monthly_household_spending": "1000.00",
        "monthly_full_time_net_income": "2000.00",
        "annual_inflation_rate": "0",
        "annual_return_rate": "0",
        "provenance": "synthetic_fixture",
    }
    if hypothetical_pension is not None:
        assumptions["hypothetical_pension"] = hypothetical_pension
    return {
        "schema_version": "retirement-bridge-projection/v1",
        "household_id": "synthetic_household",
        "as_of_month": "2026-11",
        "months": months,
        "assumptions": assumptions,
    }


class RetirementBridgeProjectionTests(unittest.TestCase):
    def test_golden_compares_100_60_and_zero_work(self):
        result = build_retirement_bridge_projection(_input())
        self.assertEqual(result["status"], "scenario_projection")
        self.assertEqual([item["scenario_id"] for item in result["scenarios"]], ["work_100", "work_60", "work_0"])
        self.assertEqual([item["summary"]["ending_available_assets"] for item in result["scenarios"]], ["11000.00", "10200.00", "9000.00"])
        self.assertEqual(result["scenarios"][2]["summary"]["total_no_work_funding_need"], "1000.00")
        one_hundred = result["scenarios"][0]["cashflows"][0]
        sixty = result["scenarios"][1]["cashflows"][0]
        zero = result["scenarios"][2]["cashflows"][0]
        self.assertEqual((one_hundred["net_work_income"], one_hundred["monthly_expenses"], one_hundred["net_cashflow"], one_hundred["asset_withdrawal"]), ("2000.00", "1000.00", "1000.00", "0.00"))
        self.assertEqual((sixty["net_work_income"], sixty["net_cashflow"], sixty["asset_withdrawal"]), ("1200.00", "200.00", "0.00"))
        self.assertEqual((zero["net_work_income"], zero["net_cashflow"], zero["requested_asset_withdrawal"], zero["asset_withdrawal"], zero["closing_available_assets"]), ("0.00", "-1000.00", "1000.00", "1000.00", "9000.00"))

    def test_hypothetical_pension_reduces_gap_but_never_becomes_entitlement(self):
        result = build_retirement_bridge_projection(_input(
            months=2,
            hypothetical_pension={
                "monthly_net_amount": "500.00",
                "start_month": 2,
                "assumption_status": "scenario_assumption",
                "provenance": "synthetic_demo_assumption",
            },
        ))
        zero_work = result["scenarios"][2]
        self.assertEqual(zero_work["summary"]["total_no_work_funding_need"], "1500.00")
        self.assertEqual(zero_work["cashflows"][1]["hypothetical_pension_net_income"], "500.00")
        self.assertEqual(zero_work["cashflows"][1]["asset_withdrawal"], "500.00")
        self.assertEqual(result["pension_entitlement"], {
            "status": "not_assessed",
            "verified_monthly_amount": None,
            "verified_start_month": None,
        })
        self.assertIn("future_pension_entitlement_not_verified", {gap["code"] for gap in result["data_gaps"]})

    def test_rejects_hypothetical_pension_without_explicit_tag(self):
        data = _input(hypothetical_pension={"monthly_net_amount": "500", "start_month": 2, "provenance": "synthetic"})
        with self.assertRaisesRegex(RetirementBridgeProjectionError, "scenario_assumption"):
            build_retirement_bridge_projection(data)


if __name__ == "__main__":
    unittest.main()
