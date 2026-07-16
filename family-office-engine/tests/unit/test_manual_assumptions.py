import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.ingestion.manual_assumptions import (
    AssumptionsImportError,
    import_assumptions,
    prepare_assumptions_input,
    validate_assumptions,
)


VALID_ASSUMPTIONS = {
    "personal": {
        "current_age": 55,
        "target_retirement_age": 62,
    },
    "cashflow": {
        "family_expenses_yearly": 80000,
        "net_salary_monthly": 5000,
        "salary_months": 14,
    },
    "returns": {
        "scenario": "prudent",
        "nominal_return": 0.03,
    },
    "notes": "Synthetic test fixture.",
}


class ManualAssumptionsTest(unittest.TestCase):
    def test_validate_accepts_valid_assumptions(self):
        validate_assumptions(VALID_ASSUMPTIONS)

    def test_validate_rejects_missing_required_field(self):
        assumptions = json.loads(json.dumps(VALID_ASSUMPTIONS))
        del assumptions["cashflow"]["salary_months"]

        with self.assertRaisesRegex(AssumptionsImportError, "cashflow.salary_months"):
            validate_assumptions(assumptions)

    def test_validate_rejects_target_age_before_current_age(self):
        assumptions = json.loads(json.dumps(VALID_ASSUMPTIONS))
        assumptions["personal"]["target_retirement_age"] = 50

        with self.assertRaisesRegex(AssumptionsImportError, "target_retirement_age"):
            validate_assumptions(assumptions)

    def test_validate_accepts_optional_retirement_income(self):
        assumptions = json.loads(json.dumps(VALID_ASSUMPTIONS))
        assumptions["cashflow"]["retirement_income_yearly"] = 36000
        assumptions["returns"]["nominal_volatility"] = 0.10

        validate_assumptions(assumptions)

    def test_validate_rejects_negative_optional_retirement_income(self):
        assumptions = json.loads(json.dumps(VALID_ASSUMPTIONS))
        assumptions["cashflow"]["retirement_income_yearly"] = -1

        with self.assertRaisesRegex(AssumptionsImportError, "cashflow.retirement_income_yearly"):
            validate_assumptions(assumptions)

    def test_validate_accepts_optional_spouse_salary_and_rental_income(self):
        assumptions = json.loads(json.dumps(VALID_ASSUMPTIONS))
        assumptions["cashflow"]["spouse_net_salary_monthly"] = 2500
        assumptions["cashflow"]["spouse_salary_months"] = 12
        assumptions["cashflow"]["rental_income_monthly_net"] = 900

        validate_assumptions(assumptions)

    def test_validate_rejects_negative_rental_income(self):
        assumptions = json.loads(json.dumps(VALID_ASSUMPTIONS))
        assumptions["cashflow"]["rental_income_monthly_net"] = -1

        with self.assertRaisesRegex(AssumptionsImportError, "cashflow.rental_income_monthly_net"):
            validate_assumptions(assumptions)

    def test_import_writes_normalized_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "assumptions.json"
            output_path = root / "snapshots" / "manual-assumptions.snapshot.json"
            input_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")

            result = import_assumptions(input_path, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "manual-assumptions/v1")
            self.assertEqual(written["record_type"], "ManualAssumptions")
            self.assertEqual(written["assumptions"]["returns"]["scenario"], "prudent")

    def test_import_reports_output_write_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "assumptions.json"
            output_path = root
            input_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")

            with self.assertRaisesRegex(AssumptionsImportError, "Cannot write output snapshot"):
                import_assumptions(input_path, output_path)

    def test_prepare_assumptions_input_writes_empty_draft_and_checklist(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            template_path = root / "base-assumptions.template.json"
            draft_path = root / "base-assumptions.draft.json"
            checklist_path = root / "assumptions-input-checklist.md"
            template_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")

            result = prepare_assumptions_input(template_path, draft_path, checklist_path)
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            checklist = checklist_path.read_text(encoding="utf-8")

            self.assertEqual(result["status"], "prepared")
            self.assertEqual(draft["record_type"], "ManualAssumptionsDraft")
            self.assertIsNone(draft["assumptions"]["personal"]["current_age"])
            self.assertIsNone(draft["assumptions"]["returns"]["nominal_return"])
            self.assertIn("retirement_income_yearly", draft["assumptions"]["cashflow"])
            self.assertIn("spouse_net_salary_monthly", draft["assumptions"]["cashflow"])
            self.assertIn("rental_income_monthly_net", draft["assumptions"]["cashflow"])
            self.assertIn("nominal_volatility", draft["assumptions"]["returns"])
            self.assertIn("base-assumptions.json", checklist)

    def test_prepare_assumptions_input_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            template_path = root / "base-assumptions.template.json"
            draft_path = root / "base-assumptions.draft.json"
            checklist_path = root / "assumptions-input-checklist.md"
            template_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")
            draft_path.write_text("existing", encoding="utf-8")

            with self.assertRaisesRegex(AssumptionsImportError, "Refusing to overwrite"):
                prepare_assumptions_input(template_path, draft_path, checklist_path)


if __name__ == "__main__":
    unittest.main()
