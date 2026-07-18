import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main, resolve_fonte_source_paths, resolve_repo, validate

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SPAIN_RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "spain" / "statutory-retirement-general.json"
EU_PENSION_COORDINATION_RULE_PACK = (
    REPOSITORY_ROOT / "family-office-rules" / "cross-border" / "eu-pension-coordination-it-es.json"
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
}

VALID_PAYSLIP_TEXT = """
PERIODO DI RETRIBUZIONE
Gennaio 2026
000001 ACME SRL
Imp. IRPEF
3.000,00
IRPEF pagata
750,00
NETTO DEL MESE
2.500,00 EUR
"""

VALID_CU_TEXT = """
CERTIFICAZIONE UNICA2026
RELATIVA ALL'ANNO 2025
CERTIFICAZIONE LAVORO DIPENDENTE, ASSIMILATI ED ASSISTENZA FISCALE
Redditi di lavoro dipendente e assimilati
45.000,00
Ritenute Irpef 9.500,00
"""

VALID_DECLARATION_TEXT = """
PERSONE FISICHE2025
Periodo d'imposta 2024
RN1 REDDITO COMPLESSIVO 45.000,00
RN5 IMPOSTA LORDA 9.500,00
RN26 IMPOSTA NETTA 8.100,00
"""

SYNTHETIC_TAX_RULE_PACK = {
    "schema_version": "tax-rule-pack/v1",
    "rule_pack_id": "synthetic.progressive-tax.v1",
    "jurisdiction": "SYNTH",
    "currency": "EUR",
    "status": "synthetic_fixture_not_for_real_tax",
    "rules": [
        {
            "rule_id": "synthetic.progressive-tax.2026",
            "tax_type": "personal_income_tax",
            "valid_from": "2026-01-01",
            "valid_to": "2026-12-31",
            "brackets": [
                {"from": "0.00", "to": "10000.00", "rate": "0.10"},
                {"from": "10000.00", "to": "30000.00", "rate": "0.20"},
                {"from": "30000.00", "to": None, "rate": "0.30"},
            ],
        }
    ],
}


class ValidateCliTest(unittest.TestCase):
    def test_validate_returns_repo_status_dict(self):
        result = validate()

        self.assertEqual(
            set(result),
            {"bootstrap", "engine", "rules", "knowledge", "workspace"},
        )

    def test_resolve_repo_uses_environment_override(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            override = Path(tmp_dir) / "custom-rules"
            environ = {"FO_RULES_PATH": str(override)}

            self.assertEqual(resolve_repo("rules", environ), override)

    def test_validate_reports_missing_override_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing = Path(tmp_dir) / "missing-workspace"
            result = validate({"FO_WORKSPACE_PATH": str(missing)})

            self.assertIs(result["workspace"], False)

    def test_main_validate_returns_success_for_existing_layout(self):
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["validate"])

        self.assertEqual(exit_code, 0)
        self.assertIn("engine: OK", stdout.getvalue())

    def test_main_validate_returns_failure_for_missing_override(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing = Path(tmp_dir) / "missing-rules"
            stdout = io.StringIO()
            environ = os.environ.copy()
            environ["FO_RULES_PATH"] = str(missing)

            with patch.dict(os.environ, environ, clear=True):
                with redirect_stdout(stdout):
                    exit_code = main(["validate"])

            self.assertEqual(exit_code, 1)
            self.assertIn(f"rules: MISSING ({missing})", stdout.getvalue())

    def test_main_assumptions_import_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "assumptions.json"
            output_path = root / "snapshot.json"
            input_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "assumptions",
                        "import",
                        "--input",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("assumptions: OK", stdout.getvalue())

    def test_main_assumptions_prepare_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            template_path = root / "base-assumptions.template.json"
            draft_path = root / "base-assumptions.draft.json"
            checklist_path = root / "assumptions-input-checklist.md"
            template_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "assumptions",
                        "prepare",
                        "--template",
                        str(template_path),
                        "--draft",
                        str(draft_path),
                        "--checklist",
                        str(checklist_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(draft_path.exists())
            self.assertTrue(checklist_path.exists())
            self.assertIn("assumptions: prepared", stdout.getvalue())

    def test_main_assumptions_check_returns_success_with_missing_input(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            template_path = root / "base-assumptions.template.json"
            output_path = root / "assumptions-readiness.snapshot.json"
            template_path.write_text(json.dumps(VALID_ASSUMPTIONS), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "assumptions",
                        "check",
                        "--input",
                        str(root / "base-assumptions.json"),
                        "--template",
                        str(template_path),
                        "--snapshot",
                        str(root / "manual-assumptions.snapshot.json"),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("assumptions: missing_input", stdout.getvalue())

    def test_main_documents_inventory_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inbox = root / "inbox"
            output_path = root / "document-inventory.snapshot.json"
            (inbox / "pensione").mkdir(parents=True)
            (inbox / "pensione" / "simulazione.pdf").write_bytes(b"synthetic")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "documents",
                        "inventory",
                        "--inbox",
                        str(inbox),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("documents: OK 1 files", stdout.getvalue())

    def test_main_documents_organize_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inbox = root / "inbox"
            documents = root / "documents"
            manifest = documents / "manifest.json"
            (inbox / "fonte").mkdir(parents=True)
            (inbox / "fonte" / "sintesi_posizione.pdf").write_bytes(b"fonte")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "documents",
                        "organize",
                        "--inbox",
                        str(inbox),
                        "--documents",
                        str(documents),
                        "--manifest",
                        str(manifest),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(manifest.exists())
            self.assertIn("documents: planned 1 operations", stdout.getvalue())

    def test_main_pension_import_inps_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "pensione"
            output_path = root / "inps-pension.snapshot.json"
            input_dir.mkdir()
            (input_dir / "simulazione.pdf").write_text("placeholder", encoding="utf-8")
            stdout = io.StringIO()

            with patch(
                "family_office_engine.ingestion.inps_pension._extract_pdf_text",
                return_value=(
                    "Codice Fiscale: SYNTHETIC_TEST_ID\n"
                    "Data elaborazione: 09/07/2026\n"
                    "Previsione della tua pensione nel sistema contributivo\n"
                    "Pensione di vecchiaia\n"
                    "Data di pensionamento 01/05/2039\n"
                    "Importo pensione mensile lordo EUR 3.562,00\n"
                    "367 settimane Contributi utili ai fini della pensione:\n"
                    "533 settimane Contributi utili in Gestione Separata:\n"
                ),
            ):
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "pension",
                            "import-inps",
                            "--input-dir",
                            str(input_dir),
                            "--output",
                            str(output_path),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("pension: extracted", stdout.getvalue())

    def test_main_pension_import_spain_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "pensione" / "spagna"
            output_path = root / "spanish-contribution-history.snapshot.json"
            input_dir.mkdir(parents=True)
            (input_dir / "vida_laboral.pdf").write_text("placeholder", encoding="utf-8")
            stdout = io.StringIO()

            with patch(
                "family_office_engine.ingestion.spanish_contribution_history._extract_pdf_text",
                return_value=(
                    "TESORERIA GENERAL DE LA SEGURIDAD SOCIAL\n"
                    "INFORME DE VIDA LABORAL\n"
                    "SITUACION/ES\n"
                    "REGIMEN GENERAL ACME SL 01/01/2024 31/01/2024 31\n"
                ),
            ):
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "pension",
                            "import-spain",
                            "--input-dir",
                            str(input_dir),
                            "--output",
                            str(output_path),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("pension: partial_extracted", stdout.getvalue())

    def test_main_pension_reconcile_spain_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            history_path = root / "spanish-contribution-history.snapshot.json"
            output_path = root / "spanish-contribution-reconciliation.snapshot.json"
            history_path.write_text(
                json.dumps(
                    {
                        "schema_version": "spanish-contribution-history/v1",
                        "record_type": "SpanishContributionHistorySnapshot",
                        "periods": [
                            {
                                "start_date": "2024-01-01",
                                "end_date": "2024-01-31",
                                "regime": "GENERAL",
                                "employer": "SYNTHETIC EMPLOYER SA",
                                "source_document": "vida_laboral.pdf",
                            }
                        ],
                        "monthly_bases": [
                            {
                                "month": "2024-01",
                                "base_amount": "2500.00",
                                "currency": "EUR",
                                "source_type": "official_bases",
                                "confidence": "high",
                                "source_document": "bases.pdf",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "pension",
                        "reconcile-spain",
                        "--history-snapshot",
                        str(history_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("pension: complete 1 usable months", stdout.getvalue())

    def test_main_pension_estimate_spain_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            reconciliation_path = root / "spanish-contribution-reconciliation.snapshot.json"
            output_path = root / "spanish-statutory-pension.snapshot.json"
            reconciliation_path.write_text(
                json.dumps(
                    {
                        "schema_version": "spanish-contribution-reconciliation/v1",
                        "record_type": "SpanishContributionReconciliationSnapshot",
                        "status": "complete",
                        "summary": {
                            "covered_month_count": 304,
                            "usable_month_count": 304,
                            "data_gap_count": 0,
                            "anomaly_count": 0,
                        },
                        "months": _spanish_reconciled_months("2001-08", 304, "3000.00"),
                        "data_gaps": [],
                        "anomalies": [],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "pension",
                        "estimate-spain",
                        "--reconciliation-snapshot",
                        str(reconciliation_path),
                        "--rule-pack",
                        str(SPAIN_RULE_PACK),
                        "--retirement-year",
                        "2026",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("pension: complete monthly=", stdout.getvalue())

    def test_main_pension_coordinate_it_es_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inps_path = root / "inps-pension.snapshot.json"
            spanish_path = root / "spanish-statutory-pension.snapshot.json"
            output_path = root / "eu-pension-coordination-it-es.snapshot.json"
            inps_path.write_text(json.dumps(_synthetic_inps_pension_snapshot()), encoding="utf-8")
            spanish_path.write_text(json.dumps(_synthetic_spanish_statutory_pension_snapshot()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "pension",
                        "coordinate-it-es",
                        "--inps-snapshot",
                        str(inps_path),
                        "--spanish-pension-snapshot",
                        str(spanish_path),
                        "--rule-pack",
                        str(EU_PENSION_COORDINATION_RULE_PACK),
                        "--italian-contribution-months",
                        "240",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("pension: complete 0 gaps", stdout.getvalue())

    def test_main_pension_compose_income_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inps_path = root / "inps-pension.snapshot.json"
            spanish_path = root / "spanish-statutory-pension.snapshot.json"
            output_path = root / "pension-income.snapshot.json"
            inps_path.write_text(json.dumps(_synthetic_inps_pension_snapshot()), encoding="utf-8")
            spanish_path.write_text(json.dumps(_synthetic_spanish_statutory_pension_snapshot()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "pension",
                        "compose-income",
                        "--inps-snapshot",
                        str(inps_path),
                        "--spanish-pension-snapshot",
                        str(spanish_path),
                        "--no-rita",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("pension: partial 2 streams, 1 gaps", stdout.getvalue())

    def test_main_expenses_build_lifecycle_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "lifecycle-expenses.json"
            output_path = root / "lifecycle-expenses.snapshot.json"
            input_path.write_text(json.dumps(_synthetic_lifecycle_expense_plan()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "expenses",
                        "build-lifecycle",
                        "--input",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("expenses: complete 1 entries, 2 years, 0 gaps", stdout.getvalue())

    def test_main_investments_import_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            italy_dir = root / "investimenti" / "italia"
            spain_dir = root / "investimenti" / "spagna"
            directa_dir = root / "investimenti" / "directa"
            output_path = root / "investments.snapshot.json"
            italy_dir.mkdir(parents=True)
            spain_dir.mkdir(parents=True)
            directa_dir.mkdir(parents=True)
            (italy_dir / "amundi.pdf").write_text("placeholder", encoding="utf-8")
            stdout = io.StringIO()

            with patch(
                "family_office_engine.ingestion.investments._extract_pdf_text",
                return_value=(
                    "Amundi\n"
                    "Quanto hai finora maturato nella tua posizione individuale\n"
                    "EUR 1.000,00 EUR 0,00 EUR 50,00 EUR 1.050,00\n"
                    "Hai versato\n"
                    "Posizione individuale al 31/12/2025\n"
                ),
            ):
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "investments",
                            "import",
                            "--italy-dir",
                            str(italy_dir),
                            "--spain-dir",
                            str(spain_dir),
                            "--directa-dir",
                            str(directa_dir),
                            "--output",
                            str(output_path),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("investments: extracted", stdout.getvalue())

    def test_main_bank_insurance_import_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            bank_dir = root / "banca"
            insurance_dir = root / "polizze"
            output_path = root / "bank-insurance.snapshot.json"
            bank_dir.mkdir()
            insurance_dir.mkdir()
            (insurance_dir / "generali.pdf").write_text("placeholder", encoding="utf-8")
            stdout = io.StringIO()

            with patch(
                "family_office_engine.ingestion.bank_insurance._extract_pdf_text",
                return_value=(
                    "Generali Italia S.p.A\n"
                    "Dichiariamo che nel 2025 i contributi complessivi versati "
                    "sono pari a EUR 2.802,58\n"
                ),
            ):
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "bank-insurance",
                            "import",
                            "--bank-dir",
                            str(bank_dir),
                            "--insurance-dir",
                            str(insurance_dir),
                            "--output",
                            str(output_path),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("bank-insurance: extracted", stdout.getvalue())

    def test_main_payroll_import_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "redditi" / "buste-paga"
            output_path = root / "payroll.snapshot.json"
            input_dir.mkdir(parents=True)
            (input_dir / "cedolino.pdf").write_text("placeholder", encoding="utf-8")
            stdout = io.StringIO()

            with patch(
                "family_office_engine.ingestion.payroll._extract_pdf_text",
                return_value=VALID_PAYSLIP_TEXT,
            ):
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "payroll",
                            "import",
                            "--input-dir",
                            str(input_dir),
                            "--output",
                            str(output_path),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("payroll: extracted 1 records, 1 documents, 0 gaps", stdout.getvalue())

    def test_main_payroll_diagnose_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "redditi" / "buste-paga"
            input_dir.mkdir(parents=True)
            (input_dir / "cedolino.pdf").write_text("placeholder", encoding="utf-8")
            stdout = io.StringIO()

            with patch(
                "family_office_engine.ingestion.payroll._extract_pdf_text",
                return_value=VALID_PAYSLIP_TEXT,
            ):
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "payroll",
                            "diagnose",
                            "--input-dir",
                            str(input_dir),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertIn("payroll diagnostics: extracted", stdout.getvalue())
            self.assertIn("summary: 1 documents, 1 records, 0 gaps", stdout.getvalue())
            self.assertNotIn("2500.00", stdout.getvalue())

    def test_main_cashflow_earned_income_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payroll_path = root / "payroll.snapshot.json"
            output_path = root / "earned-income-cashflow.snapshot.json"
            payroll_path.write_text(
                json.dumps(
                    {
                        "record_type": "PayrollSnapshot",
                        "schema_version": "payroll/v1",
                        "records": [
                            {
                                "period_label": "Gennaio 2026",
                                "period_year": 2026,
                                "employer": "ACME SRL",
                                "net_pay": "2500.00",
                                "currency": "EUR",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "cashflow",
                        "earned-income",
                        "--payroll-snapshot",
                        str(payroll_path),
                        "--assumptions-snapshot",
                        str(root / "missing-assumptions.snapshot.json"),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("cashflow: complete", stdout.getvalue())

    def test_main_tax_calculate_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            rule_pack_path = root / "synthetic-rules.json"
            output_path = root / "tax-calculation.snapshot.json"
            rule_pack_path.write_text(json.dumps(SYNTHETIC_TAX_RULE_PACK), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "tax",
                        "calculate",
                        "--rule-pack",
                        str(rule_pack_path),
                        "--tax-year",
                        "2026",
                        "--jurisdiction",
                        "SYNTH",
                        "--taxable-income",
                        "45000.00",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("tax: complete due=9500.00", stdout.getvalue())

    def test_main_tax_calculate_uses_italy_rule_pack_by_default(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "tax-calculation.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "tax",
                        "calculate",
                        "--taxable-income",
                        "60000.00",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("tax: complete due=18440.00", stdout.getvalue())
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["input"]["jurisdiction"], "IT")
            self.assertEqual(written["rule_pack"]["rule_pack_id"], "it.irpef-national.2026.v1")

    def test_main_rita_optimize_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "rita-options.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "rita",
                        "optimize",
                        "--age",
                        "62",
                        "--years-to-public-pension",
                        "4",
                        "--employment-status",
                        "ceased",
                        "--mandatory-contribution-years",
                        "32",
                        "--complementary-pension-years",
                        "8",
                        "--complementary-balance",
                        "120000.00",
                        "--duration-months",
                        "48",
                        "--monthly-need",
                        "3000.00",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("rita: complete eligible=True options=1", stdout.getvalue())
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["rule_pack"]["rule_pack_id"], "it.rita.current.v1")

    def test_main_estate_baseline_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            net_worth_path = root / "net-worth.snapshot.json"
            output_path = root / "estate-baseline.snapshot.json"
            net_worth_path.write_text(
                json.dumps(
                    {
                        "record_type": "NetWorthSnapshot",
                        "schema_version": "net-worth/v1",
                        "currency": "EUR",
                        "components": [
                            {
                                "id": "cash_1",
                                "label": "Current account",
                                "asset_class": "cash",
                                "value": "90000.00",
                                "currency": "EUR",
                                "ownership": {"owner_id": "self", "share": "1"},
                            }
                        ],
                        "totals": {"assets": "90000.00", "liabilities": "0.00", "net_worth": "90000.00"},
                        "data_gaps": [],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "estate",
                        "baseline",
                        "--net-worth-snapshot",
                        str(net_worth_path),
                        "--has-spouse",
                        "--children-count",
                        "2",
                        "--prior-donations",
                        "0.00",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("estate: complete known_mass=90000.00 heirs=3 gaps=0", stdout.getvalue())
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["rule_pack"]["rule_pack_id"], "it.estate-baseline.current.v1")

    def test_main_household_validate_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "household-facts.snapshot.json"
            sample_path = Path(__file__).resolve().parents[3] / "family-office-engine" / "examples" / "household-facts-sample.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "household",
                        "validate",
                        "--input",
                        str(sample_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("household: complete 3 persons, 2 relationships, 0 gaps", stdout.getvalue())
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["record_type"], "HouseholdFactsSnapshot")

    def test_main_household_ownership_validate_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_path = root / "ownership-beneficiary-graph.snapshot.json"
            household_path = root / "household-facts.snapshot.json"
            sample_path = (
                Path(__file__).resolve().parents[3]
                / "family-office-engine"
                / "examples"
                / "ownership-beneficiary-graph-sample.json"
            )
            household_sample_path = (
                Path(__file__).resolve().parents[3] / "family-office-engine" / "examples" / "household-facts-sample.json"
            )
            household = json.loads(household_sample_path.read_text(encoding="utf-8"))
            household_path.write_text(
                json.dumps(
                    {
                        "schema_version": "household-facts/v1",
                        "record_type": "HouseholdFactsSnapshot",
                        "persons": household["persons"],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "household",
                        "ownership",
                        "validate",
                        "--input",
                        str(sample_path),
                        "--household-snapshot",
                        str(household_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("household ownership: complete 3 assets, 1 debts, 1 beneficiaries, 0 gaps", stdout.getvalue())
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["record_type"], "OwnershipBeneficiaryGraphSnapshot")

    def test_main_household_availability_validate_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_path = root / "asset-availability.snapshot.json"
            ownership_path = root / "ownership-beneficiary-graph.snapshot.json"
            sample_path = (
                Path(__file__).resolve().parents[3]
                / "family-office-engine"
                / "examples"
                / "asset-availability-sample.json"
            )
            ownership_sample_path = (
                Path(__file__).resolve().parents[3]
                / "family-office-engine"
                / "examples"
                / "ownership-beneficiary-graph-sample.json"
            )
            ownership = json.loads(ownership_sample_path.read_text(encoding="utf-8"))
            ownership_path.write_text(
                json.dumps(
                    {
                        "schema_version": "ownership-beneficiary-graph/v1",
                        "record_type": "OwnershipBeneficiaryGraphSnapshot",
                        "assets": ownership["assets"],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "household",
                        "availability",
                        "validate",
                        "--input",
                        str(sample_path),
                        "--ownership-snapshot",
                        str(ownership_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("household availability: complete 3 classifications, 0 gaps", stdout.getvalue())
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["record_type"], "AssetAvailabilitySnapshot")

    def test_main_household_timeline_validate_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_path = root / "timeline-events.snapshot.json"
            household_path = root / "household-facts.snapshot.json"
            availability_path = root / "asset-availability.snapshot.json"
            sample_path = (
                Path(__file__).resolve().parents[3] / "family-office-engine" / "examples" / "timeline-events-sample.json"
            )
            household_sample_path = (
                Path(__file__).resolve().parents[3] / "family-office-engine" / "examples" / "household-facts-sample.json"
            )
            availability_sample_path = (
                Path(__file__).resolve().parents[3]
                / "family-office-engine"
                / "examples"
                / "asset-availability-sample.json"
            )
            policy_path = (
                Path(__file__).resolve().parents[3]
                / "family-office-rules"
                / "timeline"
                / "default-overlap-policy.json"
            )
            household = json.loads(household_sample_path.read_text(encoding="utf-8"))
            availability = json.loads(availability_sample_path.read_text(encoding="utf-8"))
            household_path.write_text(
                json.dumps(
                    {
                        "schema_version": "household-facts/v1",
                        "record_type": "HouseholdFactsSnapshot",
                        "persons": household["persons"],
                    }
                ),
                encoding="utf-8",
            )
            availability_path.write_text(
                json.dumps(
                    {
                        "schema_version": "asset-availability/v1",
                        "record_type": "AssetAvailabilitySnapshot",
                        "classifications": availability["classifications"],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "household",
                        "timeline",
                        "validate",
                        "--input",
                        str(sample_path),
                        "--policy",
                        str(policy_path),
                        "--household-snapshot",
                        str(household_path),
                        "--asset-availability-snapshot",
                        str(availability_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("household timeline: complete 8 events, 12 occurrences, 0 gaps", stdout.getvalue())
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["record_type"], "TimelineEventsSnapshot")

    def test_main_tax_reconcile_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payroll_path = root / "payroll.snapshot.json"
            tax_documents_path = root / "tax-documents.snapshot.json"
            output_path = root / "tax-reconciliation.snapshot.json"
            payroll_path.write_text(
                json.dumps(
                    {
                        "record_type": "PayrollSnapshot",
                        "schema_version": "payroll/v1",
                        "records": [
                            {
                                "period_label": "Gennaio 2025",
                                "period_year": 2025,
                                "employer": "ACME SRL",
                                "net_pay": "2500.00",
                                "taxable_irpef": "3000.00",
                                "irpef_withheld": "750.00",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            tax_documents_path.write_text(
                json.dumps(
                    {
                        "record_type": "TaxDocumentsSnapshot",
                        "schema_version": "tax-documents/v1",
                        "records": [
                            {
                                "document_type": "certificazione_unica",
                                "fields": {"model_year": "2026", "tax_year": "2025"},
                            },
                            {
                                "document_type": "dichiarazione_redditi_pf",
                                "fields": {"model_year": "2026", "tax_year": "2025"},
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "tax",
                        "reconcile",
                        "--payroll-snapshot",
                        str(payroll_path),
                        "--tax-documents-snapshot",
                        str(tax_documents_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("tax: complete reconciliation 1 years, 0 gaps", stdout.getvalue())

    def test_main_tax_documents_import_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            cu_dir = root / "redditi" / "cu"
            declarations_dir = root / "dichiarazioni"
            output_path = root / "tax-documents.snapshot.json"
            cu_dir.mkdir(parents=True)
            declarations_dir.mkdir()
            (cu_dir / "cu.pdf").write_text("placeholder", encoding="utf-8")
            (declarations_dir / "redditi.pdf").write_text("placeholder", encoding="utf-8")
            stdout = io.StringIO()

            def extract(path: Path) -> str:
                return VALID_CU_TEXT if path.name == "cu.pdf" else VALID_DECLARATION_TEXT

            with patch("family_office_engine.ingestion.tax_documents._extract_pdf_text", side_effect=extract):
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "tax-documents",
                            "import",
                            "--cu-dir",
                            str(cu_dir),
                            "--declarations-dir",
                            str(declarations_dir),
                            "--output",
                            str(output_path),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("tax-documents: extracted 2 records, 2 documents, 0 gaps", stdout.getvalue())

    def test_main_tax_documents_diagnose_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            cu_dir = root / "redditi" / "cu"
            declarations_dir = root / "dichiarazioni"
            cu_dir.mkdir(parents=True)
            declarations_dir.mkdir()
            (cu_dir / "cu.pdf").write_text("placeholder", encoding="utf-8")
            stdout = io.StringIO()

            with patch(
                "family_office_engine.ingestion.tax_documents._extract_pdf_text",
                return_value=VALID_CU_TEXT,
            ):
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "tax-documents",
                            "diagnose",
                            "--cu-dir",
                            str(cu_dir),
                            "--declarations-dir",
                            str(declarations_dir),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertIn("tax-documents diagnostics: extracted", stdout.getvalue())
            self.assertIn("summary: 1 documents, 1 records, 0 gaps", stdout.getvalue())
            self.assertNotIn("45000.00", stdout.getvalue())

    def test_main_fonte_import_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "fonte.csv"
            output_path = root / "fonte.snapshot.json"
            input_path.write_text(
                "\n".join(
                    [
                        "date,description,amount,category",
                        "2026-01-31,Employee monthly contribution,250.00,employee_contribution",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "fonte",
                        "import",
                        "--input",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("fonte: OK", stdout.getvalue())

    def test_main_net_worth_consolidate_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            fonte_path = root / "fonte.snapshot.json"
            investments_path = root / "investments.snapshot.json"
            bank_insurance_path = root / "bank-insurance.snapshot.json"
            output_path = root / "net-worth.snapshot.json"
            fonte_path.write_text(
                json.dumps(
                    {
                        "record_type": "FonTeSourceBundle",
                        "position": {
                            "statement_date": "2026-07-08",
                            "position_value": "100.00",
                        },
                    }
                ),
                encoding="utf-8",
            )
            investments_path.write_text(
                json.dumps(
                    {
                        "record_type": "InvestmentsSnapshot",
                        "positions": [
                            {
                                "provider": "Moneyfarm",
                                "description": "Gestione patrimoniale",
                                "instrument_type": "managed_portfolio",
                                "market_value": "50.00",
                                "currency": "EUR",
                            }
                        ],
                        "data_gaps": [],
                    }
                ),
                encoding="utf-8",
            )
            bank_insurance_path.write_text(
                json.dumps(
                    {
                        "record_type": "BankInsuranceSnapshot",
                        "items": [
                            {
                                "provider": "Kutxabank",
                                "document_group": "bank",
                                "amount_type": "account_balance",
                                "amount": "25.00",
                                "currency": "EUR",
                            }
                        ],
                        "data_gaps": [],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "net-worth",
                        "consolidate",
                        "--fonte-snapshot",
                        str(fonte_path),
                        "--investments-snapshot",
                        str(investments_path),
                        "--bank-insurance-snapshot",
                        str(bank_insurance_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("net-worth: OK", stdout.getvalue())
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["totals"]["net_worth"], "175.00")

    def test_main_tax_events_impatriati_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "tax-events.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "tax-events",
                        "impatriati",
                        "--start-year",
                        "2026",
                        "--end-year",
                        "2029",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("tax-events: OK", stdout.getvalue())

    def test_main_retirement_simulate_returns_success_with_missing_inputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "retirement-simulation.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "retirement",
                        "simulate",
                        "--net-worth-snapshot",
                        str(Path(tmp_dir) / "missing-net-worth.json"),
                        "--assumptions-snapshot",
                        str(Path(tmp_dir) / "missing-assumptions.json"),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("retirement: OK", stdout.getvalue())

    def test_main_monte_carlo_simulate_returns_success_with_missing_inputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "monte-carlo.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "monte-carlo",
                        "simulate",
                        "--net-worth-snapshot",
                        str(Path(tmp_dir) / "missing-net-worth.json"),
                        "--assumptions-snapshot",
                        str(Path(tmp_dir) / "missing-assumptions.json"),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("monte-carlo: blocked_missing_inputs", stdout.getvalue())

    def test_main_scenarios_compare_retirement_returns_success_with_missing_inputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "scenario-comparison.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "scenarios",
                        "compare-retirement",
                        "--net-worth-snapshot",
                        str(Path(tmp_dir) / "missing-net-worth.json"),
                        "--assumptions-snapshot",
                        str(Path(tmp_dir) / "missing-assumptions.json"),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("scenarios: blocked_missing_inputs", stdout.getvalue())

    def test_main_scenarios_compose_v2_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "decision-scenario-input.json"
            household_path = root / "household.snapshot.json"
            ownership_path = root / "ownership.snapshot.json"
            availability_path = root / "asset-availability.snapshot.json"
            timeline_path = root / "timeline-events.snapshot.json"
            pension_income_path = root / "pension-income.snapshot.json"
            lifecycle_expenses_path = root / "lifecycle-expenses.snapshot.json"
            output_path = root / "decision-scenario-v2.snapshot.json"
            input_path.write_text(json.dumps(_synthetic_decision_scenario_input()), encoding="utf-8")
            household_path.write_text(json.dumps(_synthetic_household_facts_snapshot()), encoding="utf-8")
            ownership_path.write_text(json.dumps(_synthetic_ownership_graph_snapshot()), encoding="utf-8")
            availability_path.write_text(json.dumps(_synthetic_asset_availability_snapshot()), encoding="utf-8")
            timeline_path.write_text(json.dumps(_synthetic_timeline_events_snapshot()), encoding="utf-8")
            pension_income_path.write_text(json.dumps(_synthetic_pension_income_snapshot()), encoding="utf-8")
            lifecycle_expenses_path.write_text(json.dumps(_synthetic_lifecycle_expenses_snapshot()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "scenarios",
                        "compose-v2",
                        "--input",
                        str(input_path),
                        "--household-snapshot",
                        str(household_path),
                        "--ownership-snapshot",
                        str(ownership_path),
                        "--asset-availability-snapshot",
                        str(availability_path),
                        "--timeline-snapshot",
                        str(timeline_path),
                        "--pension-income-snapshot",
                        str(pension_income_path),
                        "--lifecycle-expenses-snapshot",
                        str(lifecycle_expenses_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("scenarios: complete 6 sources, 0 gaps", stdout.getvalue())

    def test_main_scenarios_sensitivity_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            decision_scenario_path = root / "decision-scenario-v2.snapshot.json"
            input_path = root / "sensitivity-analysis.json"
            output_path = root / "sensitivity-analysis.snapshot.json"
            decision_scenario_path.write_text(json.dumps(_synthetic_decision_scenario_snapshot()), encoding="utf-8")
            input_path.write_text(json.dumps(_synthetic_sensitivity_analysis_input()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "scenarios",
                        "sensitivity",
                        "--decision-scenario-snapshot",
                        str(decision_scenario_path),
                        "--input",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("scenarios: complete 2 sensitivities, 1 stress scenarios, 0 gaps", stdout.getvalue())

    def test_main_scenarios_score_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            decision_scenario_path = root / "decision-scenario-v2.snapshot.json"
            sensitivity_path = root / "sensitivity-analysis.snapshot.json"
            input_path = root / "decision-score.json"
            policy_path = root / "score-policy-v1.json"
            output_path = root / "decision-score.snapshot.json"
            decision_scenario_path.write_text(json.dumps(_synthetic_decision_scenario_snapshot()), encoding="utf-8")
            sensitivity_path.write_text(json.dumps(_synthetic_sensitivity_analysis_snapshot()), encoding="utf-8")
            input_path.write_text(json.dumps(_synthetic_decision_score_input()), encoding="utf-8")
            policy_path.write_text(json.dumps(_synthetic_decision_score_policy()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "scenarios",
                        "score",
                        "--decision-scenario-snapshot",
                        str(decision_scenario_path),
                        "--sensitivity-analysis-snapshot",
                        str(sensitivity_path),
                        "--input",
                        str(input_path),
                        "--policy",
                        str(policy_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("scenarios: complete 2 alternatives, 2 ranked, 0 gaps", stdout.getvalue())

    def test_main_dashboard_build_returns_success_with_missing_inputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "decision-dashboard.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "dashboard",
                        "build",
                        "--net-worth-snapshot",
                        str(Path(tmp_dir) / "missing-net-worth.json"),
                        "--assumptions-snapshot",
                        str(Path(tmp_dir) / "missing-assumptions.json"),
                        "--monte-carlo-snapshot",
                        str(Path(tmp_dir) / "missing-monte-carlo.json"),
                        "--scenario-comparison-snapshot",
                        str(Path(tmp_dir) / "missing-scenario-comparison.json"),
                        "--assumptions-readiness-snapshot",
                        str(Path(tmp_dir) / "missing-readiness.json"),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("dashboard: partial", stdout.getvalue())

    def test_main_report_build_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            simulation_path = root / "retirement-simulation.snapshot.json"
            net_worth_path = root / "net-worth.snapshot.json"
            output_path = root / "retirement-report.md"
            simulation_path.write_text(
                json.dumps(
                    {
                        "record_type": "RetirementSimulationSnapshot",
                        "status": "blocked_missing_inputs",
                        "sources": {"net_worth": str(net_worth_path)},
                        "target_ages": [62, 64, 67],
                        "scenarios": [],
                        "data_gaps": ["Missing manual assumptions snapshot"],
                    }
                ),
                encoding="utf-8",
            )
            net_worth_path.write_text(
                json.dumps(
                    {
                        "record_type": "NetWorthSnapshot",
                        "currency": "EUR",
                        "sources": {},
                        "components": [],
                        "totals": {
                            "assets": "100.00",
                            "liabilities": "0.00",
                            "net_worth": "100.00",
                        },
                        "data_gaps": [],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "report",
                        "build",
                        "--simulation-snapshot",
                        str(simulation_path),
                        "--net-worth-snapshot",
                        str(net_worth_path),
                        "--assumptions-snapshot",
                        str(root / "missing-assumptions.json"),
                        "--assumptions-readiness-snapshot",
                        str(root / "missing-readiness.json"),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("report: OK", stdout.getvalue())

    def test_resolve_fonte_source_paths_accepts_explicit_dated_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            position_pdf = root / "sintesi_posizione_aderente_2026-07-08.pdf"
            contributions_xlsx = root / "importi_versati_2026-07-08.xlsx"

            resolved = resolve_fonte_source_paths(position_pdf, contributions_xlsx)

            self.assertEqual(resolved, (position_pdf, contributions_xlsx))


def _spanish_reconciled_months(start_month: str, count: int, amount: str) -> list[dict]:
    start_year, start_month_number = (int(part) for part in start_month.split("-"))
    months: list[dict] = []
    for offset in range(count):
        index = start_year * 12 + start_month_number - 1 + offset
        year = index // 12
        month = index % 12 + 1
        month_key = f"{year:04d}-{month:02d}"
        months.append(
            {
                "month": month_key,
                "covered_by_vida_laboral": True,
                "periods": [{"source_document": "synthetic-vida-laboral.txt"}],
                "official_bases": [{"base_amount": amount, "source_document": "synthetic-bases.csv"}],
                "payroll_bases": [],
                "selected_base": {
                    "month": month_key,
                    "base_amount": amount,
                    "currency": "EUR",
                    "source_type": "official_bases",
                    "confidence": "high",
                    "source_documents": ["synthetic-bases.csv"],
                    "component_count": 1,
                },
                "usable_for_estimator": True,
                "data_gap_codes": [],
                "anomaly_codes": [],
            }
        )
    return months


def _synthetic_inps_pension_snapshot() -> dict:
    return {
        "schema_version": "inps-pension/v1",
        "record_type": "InpsPensionSnapshot",
        "extraction_status": "extracted",
        "projection": {
            "retirement_date": "2039-05-01",
            "monthly_gross_pension": "3562.00",
            "prices_year": "2026",
        },
        "contribution_position": {
            "pension_contribution_weeks": "1040",
            "separate_management_weeks": "0",
        },
        "data_gaps": [],
    }


def _synthetic_spanish_statutory_pension_snapshot() -> dict:
    return {
        "schema_version": "spanish-statutory-pension/v1",
        "record_type": "SpanishStatutoryPensionEstimate",
        "status": "complete",
        "retirement_date": "2039-05",
        "eligibility": {
            "contribution_months": 300,
            "status": "eligible_by_encoded_rules",
        },
        "gross_pension": {
            "monthly_amount": "1500.00",
            "annual_amount": "21000.00",
            "currency": "EUR",
            "payments_per_year": 14,
        },
        "data_gaps": [],
    }


def _synthetic_lifecycle_expense_plan() -> dict:
    return {
        "schema_version": "lifecycle-expenses/v1",
        "record_type": "LifecycleExpensePlan",
        "household_id": "synthetic_household",
        "as_of_date": "2026-07-17",
        "expense_entries": [
            {
                "entry_id": "expense_living",
                "category": "living",
                "phase": "working_life",
                "owner_type": "household",
                "frequency": "annual",
                "start_year": 2026,
                "end_year": 2027,
                "amount": "24000.00",
                "currency": "EUR",
                "annual_inflation_rate": "0.02",
                "provenance": "synthetic fixture",
            }
        ],
        "data_gaps": [],
    }


def _synthetic_decision_scenario_input() -> dict:
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


def _synthetic_decision_scenario_snapshot() -> dict:
    return {
        "schema_version": "decision-scenario/v2",
        "record_type": "DecisionScenarioSnapshot",
        "status": "complete",
        "scenario_id": "synthetic_base_case",
        "label": "Synthetic base case",
        "as_of_date": "2026-07-17",
        "assumptions": {
            "market": {"nominal_return": "0.03", "inflation": "0.02", "source": "synthetic fixture"},
            "withdrawal_policy": {"policy_id": "fixed_real_need", "source": "synthetic fixture"},
        },
        "data_gaps": [],
        "reproducibility": {"content_hash": "synthetic-hash"},
    }


def _synthetic_sensitivity_analysis_input() -> dict:
    return {
        "schema_version": "sensitivity-analysis/v1",
        "record_type": "SensitivityAnalysisInput",
        "analysis_id": "synthetic_sensitivity",
        "label": "Synthetic sensitivity analysis",
        "as_of_date": "2026-07-18",
        "seed": 20260718,
        "sensitivities": [
            {
                "id": "inflation_up",
                "label": "Inflation +1pp",
                "domain": "inflation",
                "path": ["assumptions", "market", "inflation"],
                "operation": "absolute",
                "delta": "0.01",
            },
            {
                "id": "return_up",
                "label": "Nominal return +5%",
                "domain": "returns",
                "path": ["assumptions", "market", "nominal_return"],
                "operation": "relative",
                "delta": "0.05",
            },
        ],
        "stress_scenarios": [
            {
                "id": "market_upside",
                "label": "Market upside",
                "sensitivity_ids": ["return_up", "inflation_up"],
            }
        ],
    }


def _synthetic_sensitivity_analysis_snapshot() -> dict:
    return {
        "schema_version": "sensitivity-analysis/v1",
        "record_type": "SensitivityAnalysisSnapshot",
        "status": "complete",
        "analysis_id": "synthetic_sensitivity",
        "data_gaps": [],
    }


def _synthetic_decision_score_input() -> dict:
    return {
        "schema_version": "decision-score/v1",
        "record_type": "DecisionScoreInput",
        "score_id": "synthetic_decision_score",
        "label": "Synthetic decision score",
        "as_of_date": "2026-07-18",
        "weights": {"sustainability": "0.45", "final_wealth": "0.25", "risk": "0.30"},
        "alternatives": [
            {
                "alternative_id": "aggressive",
                "label": "Aggressive allocation",
                "metrics": {"sustainability": "0.80", "final_wealth": "700000", "risk": "0.70"},
            },
            {
                "alternative_id": "balanced",
                "label": "Balanced allocation",
                "metrics": {"sustainability": "0.78", "final_wealth": "620000", "risk": "0.30"},
            },
        ],
    }


def _synthetic_decision_score_policy() -> dict:
    return {
        "schema_version": "decision-score-policy/v1",
        "record_type": "DecisionScorePolicy",
        "policy_id": "decision.score.policy.v1",
        "metrics": [
            {
                "metric_id": "sustainability",
                "label": "Sustainability",
                "orientation": "higher_is_better",
                "min_value": "0",
                "max_value": "1",
                "unit": "ratio",
            },
            {
                "metric_id": "final_wealth",
                "label": "Final wealth",
                "orientation": "higher_is_better",
                "min_value": "0",
                "max_value": "1000000",
                "unit": "EUR",
            },
            {
                "metric_id": "risk",
                "label": "Risk",
                "orientation": "lower_is_better",
                "min_value": "0",
                "max_value": "1",
                "unit": "ratio",
            },
        ],
        "limitations": ["synthetic fixture"],
    }


def _synthetic_household_facts_snapshot() -> dict:
    return {
        "schema_version": "household-facts/v1",
        "record_type": "HouseholdFactsSnapshot",
        "status": "complete",
        "persons": [{"person_id": "person_self"}, {"person_id": "person_spouse"}],
        "relationships": [
            {
                "from_person_id": "person_self",
                "to_person_id": "person_spouse",
                "relationship_type": "spouse",
            }
        ],
        "data_gaps": [],
    }


def _synthetic_ownership_graph_snapshot() -> dict:
    return {
        "schema_version": "ownership-beneficiary-graph/v1",
        "record_type": "OwnershipBeneficiaryGraphSnapshot",
        "status": "complete",
        "assets": [{"asset_id": "asset_brokerage"}],
        "debts": [],
        "beneficiaries": [],
        "data_gaps": [],
    }


def _synthetic_asset_availability_snapshot() -> dict:
    return {
        "schema_version": "asset-availability/v1",
        "record_type": "AssetAvailabilitySnapshot",
        "status": "complete",
        "classifications": [{"asset_id": "asset_brokerage", "liquidity_bucket": "immediate"}],
        "data_gaps": [],
    }


def _synthetic_timeline_events_snapshot() -> dict:
    return {
        "schema_version": "timeline-events/v1",
        "record_type": "TimelineEventsSnapshot",
        "status": "complete",
        "events": [{"event_id": "retirement", "event_type": "retirement"}],
        "occurrences": [{"event_id": "retirement", "occurrence_date": "2039-05-01"}],
        "data_gaps": [],
    }


def _synthetic_pension_income_snapshot() -> dict:
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


def _synthetic_lifecycle_expenses_snapshot() -> dict:
    return {
        "schema_version": "lifecycle-expenses/v1",
        "record_type": "LifecycleExpensesSnapshot",
        "status": "complete",
        "expense_entries": [{"entry_id": "expense_living"}],
        "summary": {"entry_count": 1, "year_count": 3, "first_year": 2026, "last_year": 2028},
        "data_gaps": [],
    }


if __name__ == "__main__":
    unittest.main()
