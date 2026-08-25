import json
import tempfile
import unittest
from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from family_office_engine.cli.main import main
from family_office_engine.services.investment_opportunity import InvestmentOpportunityError, build_investment_opportunity

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROPERTY_FIXTURE = REPOSITORY_ROOT / "family-office-engine" / "examples" / "investment-opportunity-income-property-sample.json"
MOVABLE_FIXTURE = REPOSITORY_ROOT / "family-office-engine" / "examples" / "investment-opportunity-rentable-movable-asset-sample.json"


class InvestmentOpportunityTest(unittest.TestCase):
    def test_calculates_explicit_common_metrics_and_keeps_personal_use_separate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = build_investment_opportunity(PROPERTY_FIXTURE, Path(tmp_dir) / "snapshot.json")

        metrics = result["scenarios"][0]["metrics"]
        self.assertEqual(result["schema_version"], "investment-opportunity/v1")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(metrics["acquisition_basis"], "210000.00")
        self.assertEqual(metrics["net_operating_income"], "15000.00")
        self.assertEqual(metrics["annual_free_cash_flow"], "11900.00")
        self.assertEqual(metrics["residual_value"], "210000.00")
        self.assertEqual(metrics["exit_costs"], "5000.00")
        self.assertEqual(metrics["personal_use_economic_benefit"], "0.00")
        self.assertEqual(result["scenarios"][0]["provenance"], [{"origin": "synthetic fixture"}])
        self.assertTrue(result["summary"]["personal_use_benefit_is_not_cash_flow"])

    def test_movable_asset_fixture_reuses_core_and_does_not_add_personal_benefit_to_cashflow(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = build_investment_opportunity(MOVABLE_FIXTURE, Path(tmp_dir) / "snapshot.json")

        metrics = result["scenarios"][0]["metrics"]
        self.assertEqual(result["asset_type"], "rentable_movable_asset")
        self.assertEqual(metrics["annual_free_cash_flow"], "6625.00")
        self.assertEqual(metrics["personal_use_economic_benefit"], "3000.00")

    def test_missing_operational_assumptions_become_explicit_gaps(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            data = json.loads(PROPERTY_FIXTURE.read_text(encoding="utf-8"))
            data["scenarios"][0].pop("operations")
            data["scenarios"][0].pop("owner_time")
            data["scenarios"][0].pop("personal_use")
            input_path = root / "input.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")
            result = build_investment_opportunity(input_path, root / "snapshot.json")

        self.assertEqual(result["status"], "partial")
        codes = {item["code"] for item in result["data_gaps"]}
        self.assertTrue({"missing_operations_inputs", "missing_owner_time_input", "missing_personal_use_benefit"} <= codes)

    def test_zero_and_negative_cash_flow_are_preserved_without_inference(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            data = json.loads(PROPERTY_FIXTURE.read_text(encoding="utf-8"))
            scenario = data["scenarios"][0]
            scenario["operations"]["revenue"] = []
            scenario["operations"]["costs"] = [{"code": "maintenance", "amount": "0"}]
            scenario["operations"]["taxes_fees"] = []
            scenario["owner_time"] = {"annual_hours": "0", "hourly_value": "0"}
            scenario["personal_use"] = {"annual_economic_benefit": "0"}
            input_path = root / "zero.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")
            zero_result = build_investment_opportunity(input_path, root / "zero.snapshot.json")

            scenario["operations"]["costs"] = [{"code": "major_repair", "amount": "1250"}]
            input_path.write_text(json.dumps(data), encoding="utf-8")
            negative_result = build_investment_opportunity(input_path, root / "negative.snapshot.json")

        self.assertEqual(zero_result["scenarios"][0]["metrics"]["annual_free_cash_flow"], "0.00")
        self.assertEqual(negative_result["scenarios"][0]["metrics"]["annual_free_cash_flow"], "-1250.00")

    def test_rejects_missing_versioned_assumptions(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            data = json.loads(PROPERTY_FIXTURE.read_text(encoding="utf-8"))
            data.pop("assumptions")
            input_path = root / "input.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(InvestmentOpportunityError, "assumptions must be"):
                build_investment_opportunity(input_path, root / "snapshot.json")

    def test_hash_is_independent_of_input_and_output_paths(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            first = build_investment_opportunity(PROPERTY_FIXTURE, root / "first.json")
            copied = root / "copy.json"
            copied.write_text(PROPERTY_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            second = build_investment_opportunity(copied, root / "second.json")

        self.assertEqual(first["reproducibility"]["content_hash"], second["reproducibility"]["content_hash"])

    def test_rejects_non_explicit_currency_and_non_list_revenue(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            data = json.loads(PROPERTY_FIXTURE.read_text(encoding="utf-8"))
            data["base_currency"] = "eur"
            input_path = root / "bad-currency.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(InvestmentOpportunityError, "ISO-4217"):
                build_investment_opportunity(input_path, root / "snapshot.json")

            data["base_currency"] = "EUR"
            data["scenarios"][0]["operations"]["revenue"] = "18000"
            input_path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(InvestmentOpportunityError, "operations.revenue must be a list"):
                build_investment_opportunity(input_path, root / "snapshot.json")

    def test_rejects_values_outside_the_strict_input_contract(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            base = json.loads(PROPERTY_FIXTURE.read_text(encoding="utf-8"))
            invalid_cases = [
                ("top level", lambda value: value.update({"unexpected": True})),
                ("scenario", lambda value: value["scenarios"][0].update({"unexpected": True})),
                ("operations", lambda value: value["scenarios"][0]["operations"].update({"unexpected": True})),
                ("amount", lambda value: value["scenarios"][0]["operations"]["revenue"][0].update({"unexpected": True})),
                ("owner_time", lambda value: value["scenarios"][0]["owner_time"].update({"unexpected": True})),
                ("personal_use", lambda value: value["scenarios"][0]["personal_use"].update({"unexpected": True})),
            ]
            for label, mutate in invalid_cases:
                with self.subTest(label=label):
                    data = deepcopy(base)
                    mutate(data)
                    input_path = root / f"{label}.json"
                    input_path.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaisesRegex(InvestmentOpportunityError, "unknown fields"):
                        build_investment_opportunity(input_path, root / "snapshot.json")

            data = deepcopy(base)
            data["as_of_date"] = "not-a-date"
            input_path = root / "invalid-date.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(InvestmentOpportunityError, "as_of_date must be an ISO date"):
                build_investment_opportunity(input_path, root / "snapshot.json")

            data = deepcopy(base)
            data["scenarios"][0]["operations"]["revenue"][0]["amount"] = "NaN"
            input_path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(InvestmentOpportunityError, "finite decimal"):
                build_investment_opportunity(input_path, root / "snapshot.json")

            data = deepcopy(base)
            data["scenarios"][0]["personal_use"] = "3000"
            input_path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(InvestmentOpportunityError, "personal_use must be an object"):
                build_investment_opportunity(input_path, root / "snapshot.json")

    def test_cli_build_and_demo_offer_short_paths(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "snapshot.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["planning", "investment-opportunity", "build", "--input", str(PROPERTY_FIXTURE), "--output", str(output)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())
            self.assertIn("planning investment-opportunity: complete", stdout.getvalue())

            demo_output = Path(tmp_dir) / "demo.json"
            with redirect_stdout(StringIO()):
                exit_code = main(["planning", "investment-opportunity", "demo", "--output", str(demo_output)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(demo_output.exists())


if __name__ == "__main__":
    unittest.main()
