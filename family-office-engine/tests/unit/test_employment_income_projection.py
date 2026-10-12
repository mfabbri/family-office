import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.services.employment_income_projection import (
    EmploymentIncomeProjectionError,
    build_employment_income_projection,
)


ROOT = Path(__file__).resolve().parents[3]
IRPEF = ROOT / "family-office-rules" / "italy" / "2026" / "irpef-national.json"
INPS = ROOT / "family-office-rules" / "italy" / "2026" / "inps-theoretical-pension.json"


class EmploymentIncomeProjectionTest(unittest.TestCase):
    def test_projects_explicit_bases_and_preserves_observed_streams(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            result = self._build(root, _input())

            self.assertEqual(result["schema_version"], "employment-income-projection/v1")
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(len(result["sources"]["input"]["sha256"]), 64)
            january = result["periods"][0]
            self.assertIsNone(january["pension_capital_contribution"])
            self.assertIsNone(january["employee_inps_withholding"])
            self.assertIsNone(january["payroll_net"])
            self.assertEqual(january["tfr"]["amount"], "100.00")
            self.assertEqual(
                [item["contributor"] for item in january["complementary_contributions"]],
                ["employee", "employer"],
            )
            self.assertEqual(january["complementary_contributions"][0]["amount"], "25.00")
            self.assertEqual(result["illustrative_annual_national_gross_irpef_on_employment_income"][0], {
                "member_id": "primary", "tax_year": 2026, "explicit_employment_taxable_income": "3500.00",
                "illustrative_national_gross_irpef": "805.00",
            })
            self.assertEqual([item["fte"] for item in result["periods"][:3]], [1.0, 0.6, 0.4])
            codes = {gap["code"] for gap in result["data_gaps"]}
            self.assertIn("full_payroll_net_unsupported", codes)
            self.assertIn("tfr_accrual_unsupported", codes)
            self.assertIn("inps_management_not_covered_by_rule_pack", codes)
            self.assertIn("other_taxable_income_not_included_in_irpef_base", codes)
            self.assertNotIn("irpef_source_verification_date_not_recorded", codes)
            self.assertEqual(result["sources"]["irpef_rule_pack"]["rule_pack_id"], "it.irpef-national.2026.v2")
            self.assertNotIn("full_payroll_net_unsupported", {
                gap["code"] for gap in result["data_gaps"] if gap.get("month") == "2026-04-01"
            })

    def test_missing_management_or_base_blocks_pension_capital_without_guessing(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            data = _input()
            del data["periods"][0]["inps_management"]
            result = self._build(root, data)

            self.assertIsNone(result["periods"][0]["pension_capital_contribution"])
            self.assertIn("missing_declared_inps_management_or_pensionable_base", {gap["code"] for gap in result["data_gaps"]})

    def test_rejects_undocumented_or_unsupported_payroll_fields(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            data = _input()
            data["periods"][0]["payroll_net"] = "2000.00"
            with self.assertRaisesRegex(EmploymentIncomeProjectionError, "unsupported fields"):
                self._build(root, data)

    def test_partial_calendar_year_does_not_claim_annual_irpef(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            scenario = _scenario()
            scenario["monthly_timeline"][0]["months"] = scenario["monthly_timeline"][0]["months"][:2]
            _rehash_scenario(scenario)
            data = _input()
            data["periods"] = data["periods"][:2]
            result = self._build(root, data, scenario)

            self.assertIsNone(result["illustrative_annual_national_gross_irpef_on_employment_income"][0]["illustrative_national_gross_irpef"])
            self.assertIn(
                "incomplete_calendar_year_coverage_for_irpef",
                {gap["code"] for gap in result["data_gaps"]},
            )

    def test_inps_rate_is_not_projected_beyond_rule_validity(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            scenario = _scenario()
            scenario["as_of_date"] = "2027-01-01"
            scenario["monthly_timeline"][0]["months"] = [
                {"month": f"2027-{month:02d}-01", "phase_id": "full", "status": "full_time", "fte": 1.0}
                for month in range(1, 13)
            ]
            data = _input()
            data["as_of_date"] = "2027-01-01"
            data["periods"] = [
                {"member_id": "primary", "month": f"2027-{month:02d}-01", "taxable_income": "1000.00",
                 "taxable_income_basis": "declared", "pensionable_base": "1000.00",
                 "pensionable_base_basis": "declared", "inps_management": "employee",
                 "provenance": {"origin": "synthetic"}, "complementary_contributions": []}
                for month in range(1, 13)
            ]
            _rehash_scenario(scenario)
            result = self._build(root, data, scenario)

            self.assertIsNone(result["periods"][0]["pension_capital_contribution"])
            self.assertIn(
                "inps_computation_rule_outside_validity",
                {gap["code"] for gap in result["data_gaps"]},
            )

    def test_additional_pay_is_included_only_when_explicitly_in_monthly_base(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            scenario = _scenario()
            scenario["monthly_timeline"][0]["months"][-1].update({
                "phase_id": "part40", "status": "part_time", "fte": 0.4,
            })
            _rehash_scenario(scenario)
            data = _input()
            data["periods"].append({
                "member_id": "primary", "month": "2026-12-01", "taxable_income": "1500.00",
                "taxable_income_basis": "declared", "pensionable_base": "600.00",
                "pensionable_base_basis": "declared", "inps_management": "employee",
                "provenance": {"origin": "synthetic explicit December base including additional pay"},
                "complementary_contributions": [],
            })
            result = self._build(root, data, scenario)

            tax = result["illustrative_annual_national_gross_irpef_on_employment_income"][0]
            self.assertEqual(tax["explicit_employment_taxable_income"], "5000.00")
            self.assertEqual(tax["illustrative_national_gross_irpef"], "1150.00")

    def test_scenario_tampering_is_detected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            scenario = _scenario()
            scenario["monthly_timeline"][0]["months"][0]["fte"] = 0.8
            with self.assertRaisesRegex(EmploymentIncomeProjectionError, "content hash"):
                self._build(root, _input(), scenario)

    def test_personal_inputs_outside_workspace_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            input_path = workspace / "input.json"
            input_path.write_text(json.dumps(_input()), encoding="utf-8")
            with patch("family_office_engine.services.employment_income_projection._workspace_root", return_value=workspace):
                with self.assertRaisesRegex(EmploymentIncomeProjectionError, "must stay inside"):
                    build_employment_income_projection(IRPEF, input_path, IRPEF, INPS, workspace / "output.json")

    def test_projection_output_outside_workspace_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            scenario_path = workspace / "scenario.json"
            input_path = workspace / "input.json"
            scenario_path.write_text(json.dumps(_scenario()), encoding="utf-8")
            input_path.write_text(json.dumps(_input()), encoding="utf-8")
            with patch("family_office_engine.services.employment_income_projection._workspace_root", return_value=workspace):
                with self.assertRaisesRegex(EmploymentIncomeProjectionError, "output must stay inside"):
                    build_employment_income_projection(scenario_path, input_path, IRPEF, INPS, IRPEF)

    def _build(self, root: Path, data: dict, scenario: dict | None = None) -> dict:
        workspace = root / "workspace"
        workspace.mkdir()
        scenario_path = workspace / "scenario.json"
        input_path = workspace / "input.json"
        output_path = workspace / "projection.json"
        scenario_path.write_text(json.dumps(scenario or _scenario()), encoding="utf-8")
        input_path.write_text(json.dumps(data), encoding="utf-8")
        with patch("family_office_engine.services.employment_income_projection._workspace_root", return_value=workspace):
            return build_employment_income_projection(scenario_path, input_path, IRPEF, INPS, output_path)


def _scenario() -> dict:
    result = {
        "schema_version": "work-transition-scenario/v1", "record_type": "WorkTransitionScenarioSnapshot",
        "household_id": "synthetic_household", "as_of_date": "2026-01-01",
        "monthly_timeline": [{"member_id": "primary", "months": [
            {"month": f"2026-{month:02d}-01", "phase_id": "full" if month == 1 else "part60" if month == 2 else "part40" if month == 3 else "stop",
             "status": "full_time" if month == 1 else "part_time" if month in {2, 3} else "not_working",
             "fte": 1.0 if month == 1 else 0.6 if month == 2 else 0.4 if month == 3 else 0.0,
             "compensation_policy_ref": "declared-compensation",
             "contribution_benefit_policy_ref": "declared-benefits"}
            for month in range(1, 13)
        ]}],
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": ""},
    }
    _rehash_scenario(result)
    return result


def _rehash_scenario(scenario: dict) -> None:
    core = {
        key: value for key, value in scenario.items()
        if key not in {"schema_version", "record_type", "reproducibility", "notes"}
    }
    payload = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    scenario["reproducibility"] = {"hash_algorithm": "sha256", "content_hash": hashlib.sha256(payload).hexdigest()}


def _input() -> dict:
    provenance = {"origin": "synthetic documented declaration"}
    return {
        "schema_version": "employment-income-projection-input/v1", "record_type": "EmploymentIncomeProjectionInput",
        "household_id": "synthetic_household", "as_of_date": "2026-01-01",
        "periods": [
            {"member_id": "primary", "month": "2026-01-01", "taxable_income": "1000.00", "taxable_income_basis": "declared",
             "pensionable_base": "1000.00", "pensionable_base_basis": "declared", "inps_management": "employee", "provenance": provenance,
             "tfr": {"amount": "100.00", "basis": "observed", "provenance": provenance},
             "complementary_contributions": [
                 {"amount": "25.00", "basis": "declared", "contributor": "employee", "provenance": provenance},
                 {"amount": "10.00", "basis": "observed", "contributor": "employer", "provenance": provenance},
             ]},
            {"member_id": "primary", "month": "2026-02-01", "taxable_income": "2000.00", "taxable_income_basis": "observed",
             "pensionable_base": "1200.00", "pensionable_base_basis": "declared", "inps_management": "employee",
             "provenance": provenance, "complementary_contributions": []},
            {"member_id": "primary", "month": "2026-03-01", "taxable_income": "500.00", "taxable_income_basis": "declared",
             "pensionable_base": "600.00", "pensionable_base_basis": "declared", "inps_management": "employee",
             "provenance": provenance, "complementary_contributions": []},
        ],
    }


if __name__ == "__main__":
    unittest.main()
