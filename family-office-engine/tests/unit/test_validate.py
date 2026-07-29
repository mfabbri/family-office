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
    def test_json_input_guides_cover_active_cli_inputs(self):
        guide_path = REPOSITORY_ROOT / "family-office-engine" / "docs" / "json-input-guides.md"
        workflow_path = REPOSITORY_ROOT / "family-office-engine" / "docs" / "cli-workflow.md"
        decumulation_guide_path = (
            REPOSITORY_ROOT / "family-office-engine" / "examples" / "decumulation-policy-set-guide.md"
        )
        liquidity_guide_path = REPOSITORY_ROOT / "family-office-engine" / "examples" / "liquidity-plan-input-guide.md"
        decumulation_draft_path = (
            REPOSITORY_ROOT / "family-office-workspace" / "planning" / "decumulation-policy-set.draft.json"
        )

        for path in [guide_path, workflow_path, decumulation_guide_path, liquidity_guide_path, decumulation_draft_path]:
            self.assertTrue(path.exists(), f"Missing guide or draft: {path}")

        guide = guide_path.read_text(encoding="utf-8")
        required_inputs = [
            "base-assumptions.json",
            "household-facts/v1",
            "ownership-beneficiary-graph/v1",
            "asset-availability/v1",
            "timeline-events/v1",
            "lifecycle-expenses/v1",
            "planning-goals/v1",
            "liquidity-plan-input/v1",
            "decumulation-policy-set/v1",
            "decision-scenario-v2.json",
            "decision-outcome.json",
            "sensitivity-analysis.json",
            "decision-score.json",
            "decision-dossier.json",
        ]

        for input_name in required_inputs:
            self.assertIn(input_name, guide)

        decumulation_guide = decumulation_guide_path.read_text(encoding="utf-8")
        for field in [
            "policy_id",
            "retirement_age",
            "end_age",
            "annual_spending_need",
            "cash_buffer_target",
            "withdrawal_order",
            "annual_return_sequence",
            "include_rita",
        ]:
            self.assertIn(field, decumulation_guide)

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

    def test_main_household_availability_validate_explains_ownership_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "asset-availability.json"
            ownership_path = root / "ownership.snapshot.json"
            output_path = root / "asset-availability.snapshot.json"
            availability_sample_path = REPOSITORY_ROOT / "family-office-engine" / "examples" / "asset-availability-sample.json"
            ownership_sample_path = REPOSITORY_ROOT / "family-office-engine" / "examples" / "ownership-beneficiary-graph-sample.json"
            ownership = json.loads(ownership_sample_path.read_text(encoding="utf-8"))
            availability = json.loads(availability_sample_path.read_text(encoding="utf-8"))
            availability["classifications"][0]["asset_id"] = "net_worth_asset"
            input_path.write_text(json.dumps(availability), encoding="utf-8")
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
                        str(input_path),
                        "--ownership-snapshot",
                        str(ownership_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("not present in the ownership graph", stdout.getvalue())
            self.assertIn("--skip-ownership-check", stdout.getvalue())

    def test_main_household_availability_validate_can_skip_ownership_check(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "asset-availability.json"
            output_path = root / "asset-availability.snapshot.json"
            availability_sample_path = REPOSITORY_ROOT / "family-office-engine" / "examples" / "asset-availability-sample.json"
            availability = json.loads(availability_sample_path.read_text(encoding="utf-8"))
            availability["classifications"][0]["asset_id"] = "net_worth_asset"
            input_path.write_text(json.dumps(availability), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "household",
                        "availability",
                        "validate",
                        "--input",
                        str(input_path),
                        "--skip-ownership-check",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("household availability: complete", stdout.getvalue())

    def test_main_household_availability_wizard_writes_valid_input_from_net_worth(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "asset-availability.json"
            net_worth_path = root / "net-worth.snapshot.json"
            net_worth_path.write_text(json.dumps(_synthetic_decumulation_net_worth()), encoding="utf-8")
            answers = ["synthetic_household", "2026-07-24"] + [""] * 24
            stdout = io.StringIO()

            with patch("builtins.input", side_effect=answers), redirect_stdout(stdout):
                exit_code = main(
                    [
                        "household",
                        "availability",
                        "wizard",
                        "--input",
                        str(input_path),
                        "--net-worth-snapshot",
                        str(net_worth_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "asset-availability/v1")
            self.assertEqual(len(written["classifications"]), 3)
            by_asset = {item["asset_id"]: item for item in written["classifications"]}
            self.assertEqual(by_asset["asset_cash"]["liquidity_tier"], "immediate")
            self.assertEqual(by_asset["asset_home"]["liquidity_tier"], "illiquid")
            self.assertIn("household availability wizard: prepared 3 classifications, 0 gaps", stdout.getvalue())

    def test_main_household_availability_wizard_reprompts_invalid_country(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "asset-availability.json"
            net_worth_path = root / "net-worth.snapshot.json"
            net_worth = _synthetic_decumulation_net_worth()
            net_worth["components"] = net_worth["components"][:1]
            net_worth_path.write_text(json.dumps(net_worth), encoding="utf-8")
            answers = [
                "synthetic_household",
                "2026-07-24",
                "",
                "",
                "",
                "",
                "",
                "+",
                "ES",
                "",
            ]
            stdout = io.StringIO()

            with patch("builtins.input", side_effect=answers), redirect_stdout(stdout):
                exit_code = main(
                    [
                        "household",
                        "availability",
                        "wizard",
                        "--input",
                        str(input_path),
                        "--net-worth-snapshot",
                        str(net_worth_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(written["classifications"][0]["jurisdiction"], "ES")
            self.assertIn("Valore non valido", stdout.getvalue())

    def test_main_household_availability_wizard_saves_progress_when_interrupted(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "asset-availability.json"
            net_worth_path = root / "net-worth.snapshot.json"
            net_worth_path.write_text(json.dumps(_synthetic_decumulation_net_worth()), encoding="utf-8")
            answers = [
                "synthetic_household",
                "2026-07-24",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                EOFError("interrupted"),
            ]
            stdout = io.StringIO()

            with patch("builtins.input", side_effect=answers), redirect_stdout(stdout):
                exit_code = main(
                    [
                        "household",
                        "availability",
                        "wizard",
                        "--input",
                        str(input_path),
                        "--net-worth-snapshot",
                        str(net_worth_path),
                    ]
                )

            self.assertEqual(exit_code, 1)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(len(written["classifications"]), 1)
            self.assertEqual(written["classifications"][0]["asset_id"], "asset_cash")
            self.assertEqual(written["data_gaps"][0]["code"], "wizard_incomplete")
            self.assertIn("interrupted", stdout.getvalue())

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

    def test_main_planning_goals_validate_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "planning-goals.json"
            timeline_path = root / "timeline-events.snapshot.json"
            output_path = root / "planning-goals.snapshot.json"
            goals = _synthetic_planning_goals()
            goals["draft_notes"] = {"objectives": "Human-readable guidance ignored by the validator."}
            goals["draft_examples"] = {"objective": goals["objectives"][0]}
            input_path.write_text(json.dumps(goals), encoding="utf-8")
            timeline_path.write_text(json.dumps(_synthetic_timeline_events_snapshot()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "goals",
                        "validate",
                        "--input",
                        str(input_path),
                        "--timeline-snapshot",
                        str(timeline_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("planning goals: complete 2 objectives, 2 constraints, 0 gaps", stdout.getvalue())

    def test_main_planning_goals_prepare_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            draft_path = root / "planning-goals.draft.json"
            input_path = root / "planning-goals.json"
            draft_path.write_text(json.dumps(_synthetic_planning_goals()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "goals",
                        "prepare",
                        "--draft",
                        str(draft_path),
                        "--input",
                        str(input_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(input_path.exists())
            self.assertEqual(
                json.loads(input_path.read_text(encoding="utf-8")),
                _synthetic_planning_goals(),
            )
            self.assertIn("planning goals: prepared", stdout.getvalue())
            self.assertIn("fo planning goals validate", stdout.getvalue())

    def test_main_planning_goals_prepare_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            draft_path = root / "planning-goals.draft.json"
            input_path = root / "planning-goals.json"
            draft_path.write_text(json.dumps(_synthetic_planning_goals()), encoding="utf-8")
            input_path.write_text("{}", encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "goals",
                        "prepare",
                        "--draft",
                        str(draft_path),
                        "--input",
                        str(input_path),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("use --overwrite", stdout.getvalue())

    def test_main_planning_goals_wizard_writes_valid_input(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "planning-goals.json"
            answers = [
                "wizard_household",
                "2026-07-20",
                "2026",
                "2056",
                "medium",
                "low",
                "0.15",
                "9",
                "3000.00",
                "0.02",
                "2036",
            ]
            stdout = io.StringIO()

            with patch("builtins.input", side_effect=answers), redirect_stdout(stdout):
                exit_code = main(["planning", "goals", "wizard", "--input", str(input_path)])

            self.assertEqual(exit_code, 0)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "planning-goals/v1")
            self.assertEqual(written["household_id"], "wizard_household")
            self.assertEqual(written["liquidity_policy"]["minimum_reserve_months"], 9)
            retirement_target = written["objectives"][1]["target"]
            self.assertEqual(retirement_target["current_monthly_spending"], "3000.00")
            self.assertEqual(retirement_target["annual_cost_growth"], "0.02")
            self.assertEqual(retirement_target["projection_years"], 10)
            self.assertEqual(retirement_target["value"], "43883.80")
            self.assertEqual(written["data_gaps"], [])
            self.assertIn("planning goals wizard: prepared 0 gaps", stdout.getvalue())

    def test_main_planning_goals_wizard_skips_existing_input_without_prompting(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "planning-goals.json"
            input_path.write_text(json.dumps(_synthetic_planning_goals()), encoding="utf-8")
            stdout = io.StringIO()

            with patch("builtins.input", side_effect=AssertionError("wizard should not prompt")), redirect_stdout(stdout):
                exit_code = main(["planning", "goals", "wizard", "--input", str(input_path)])

            self.assertEqual(exit_code, 0)
            self.assertIn("existing input found", stdout.getvalue())
            self.assertIn("fo planning goals validate", stdout.getvalue())

    def test_main_planning_goals_wizard_uses_existing_input_as_defaults_with_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "planning-goals.json"
            existing = _synthetic_planning_goals()
            existing["household_id"] = "existing_household"
            existing["liquidity_policy"]["minimum_reserve_months"] = 8
            input_path.write_text(json.dumps(existing), encoding="utf-8")
            stdout = io.StringIO()

            with patch("builtins.input", side_effect=[""] * 11), redirect_stdout(stdout):
                exit_code = main(["planning", "goals", "wizard", "--input", str(input_path), "--overwrite"])

            self.assertEqual(exit_code, 0)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(written["household_id"], "existing_household")
            self.assertEqual(written["liquidity_policy"]["minimum_reserve_months"], 8)
            self.assertIn("uso i dati esistenti come default", stdout.getvalue())

    def test_main_planning_goals_wizard_saves_progress_when_interrupted(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "planning-goals.json"
            answers = ["partial_household", "2026-07-24", "2026", "2056", EOFError("interrupted")]
            stdout = io.StringIO()

            with patch("builtins.input", side_effect=answers), redirect_stdout(stdout):
                exit_code = main(["planning", "goals", "wizard", "--input", str(input_path), "--overwrite"])

            self.assertEqual(exit_code, 1)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(written["household_id"], "partial_household")
            self.assertEqual(written["as_of_date"], "2026-07-24")
            self.assertEqual(written["planning_horizon"]["end_year"], 2056)
            self.assertEqual(written["data_gaps"][0]["code"], "wizard_incomplete")
            self.assertEqual(written["data_gaps"][0]["last_answered"], "end_year")
            self.assertIn("progress saved", stdout.getvalue())

    def test_main_planning_goals_status_reports_missing_input(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            draft_path = root / "planning-goals.draft.json"
            input_path = root / "planning-goals.json"
            output_path = root / "planning-goals.snapshot.json"
            timeline_path = root / "timeline-events.snapshot.json"
            draft_path.write_text(json.dumps(_synthetic_planning_goals()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "goals",
                        "status",
                        "--draft",
                        str(draft_path),
                        "--input",
                        str(input_path),
                        "--output",
                        str(output_path),
                        "--timeline-snapshot",
                        str(timeline_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("planning goals status: input_missing", stdout.getvalue())
            self.assertIn("fo planning goals prepare", stdout.getvalue())

    def test_main_planning_goals_status_reports_unedited_draft(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            draft_path = root / "planning-goals.draft.json"
            input_path = root / "planning-goals.json"
            output_path = root / "planning-goals.snapshot.json"
            timeline_path = root / "timeline-events.snapshot.json"
            input_path.write_text(
                json.dumps(
                    {
                        "schema_version": "planning-goals/v1",
                        "record_type": "PlanningGoals",
                        "household_id": None,
                        "as_of_date": None,
                        "planning_horizon": {"start_year": None, "end_year": None},
                        "risk_profile": {
                            "capacity": "unknown",
                            "tolerance": "unknown",
                            "max_loss_ratio": None,
                        },
                        "liquidity_policy": {
                            "minimum_reserve_months": None,
                            "preferred_bucket": "unknown",
                        },
                        "objectives": [],
                        "constraints": [],
                        "data_gaps": [{"code": "draft_not_completed", "message": "Complete the draft."}],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "goals",
                        "status",
                        "--draft",
                        str(draft_path),
                        "--input",
                        str(input_path),
                        "--output",
                        str(output_path),
                        "--timeline-snapshot",
                        str(timeline_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("planning goals status: draft_needs_editing", stdout.getvalue())
            self.assertIn("fo planning goals wizard --overwrite", stdout.getvalue())

    def test_main_planning_goals_validate_missing_file_suggests_prepare(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "missing-planning-goals.json"
            output_path = root / "planning-goals.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "goals",
                        "validate",
                        "--input",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("Planning goals file not found", stdout.getvalue())
            self.assertIn("fo planning goals prepare", stdout.getvalue())

    def test_main_planning_liquidity_build_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "liquidity-input.json"
            net_worth_path = root / "net-worth.snapshot.json"
            availability_path = root / "asset-availability.snapshot.json"
            goals_path = root / "planning-goals.snapshot.json"
            output_path = root / "liquidity-plan.snapshot.json"
            input_path.write_text(json.dumps(_synthetic_liquidity_input()), encoding="utf-8")
            net_worth_path.write_text(json.dumps(_synthetic_liquidity_net_worth()), encoding="utf-8")
            availability_path.write_text(json.dumps(_synthetic_liquidity_availability()), encoding="utf-8")
            goals_path.write_text(json.dumps(_synthetic_planning_goals_snapshot()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "liquidity",
                        "build",
                        "--input",
                        str(input_path),
                        "--net-worth-snapshot",
                        str(net_worth_path),
                        "--asset-availability-snapshot",
                        str(availability_path),
                        "--planning-goals-snapshot",
                        str(goals_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("planning liquidity: partial", stdout.getvalue())
            self.assertIn("reserve: funded 12000.00 / target 36000.00 (shortfall 24000.00 EUR)", stdout.getvalue())
            self.assertIn("assets: 2 total, 1 not usable for current spending", stdout.getvalue())

    def test_main_planning_liquidity_explain_translates_blocking_reasons(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            snapshot_path = root / "liquidity-plan.snapshot.json"
            snapshot = {
                "schema_version": "liquidity-plan/v1",
                "record_type": "LiquidityPlanSnapshot",
                "status": "complete",
                "base_currency": "EUR",
                "asset_assignments": [
                    {
                        "asset_id": "asset_cash",
                        "label": "Cash account",
                        "value": "12000.00",
                        "currency": "EUR",
                        "bucket": "emergency_reserve",
                        "blocks_current_spending": False,
                        "reason_codes": ["immediate_liquidity"],
                    },
                    {
                        "asset_id": "asset_family_home",
                        "label": "Family home",
                        "value": "180000.00",
                        "currency": "EUR",
                        "bucket": "restricted",
                        "blocks_current_spending": True,
                        "reason_codes": [
                            "blocking_constraint:co_ownership",
                            "blocking_constraint:sale_process",
                            "blocked_for_current_spending",
                        ],
                    },
                ],
                "data_gaps": [],
            }
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["planning", "liquidity", "explain", "--snapshot", str(snapshot_path)])

            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("planning liquidity explain: complete", output)
            self.assertIn("1 utilizzabili per spese correnti, 1 non utilizzabili", output)
            self.assertIn("Family home [asset_family_home]", output)
            self.assertIn("comproprieta", output)
            self.assertIn("serve processo di vendita", output)
            self.assertIn("emergency_reserve: 12000.00 EUR (1 asset)", output)

    def test_main_planning_liquidity_wizard_writes_valid_input(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "liquidity-plan-input.json"
            answers = ["3500.00", "10", "0.55"]
            stdout = io.StringIO()

            with patch("builtins.input", side_effect=answers), redirect_stdout(stdout):
                exit_code = main(["planning", "liquidity", "wizard", "--input", str(input_path)])

            self.assertEqual(exit_code, 0)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "liquidity-plan-input/v1")
            self.assertEqual(written["monthly_expenses"], "3500.00")
            self.assertEqual(written["minimum_reserve_months"], 10)
            self.assertEqual(written["data_gaps"], [])
            self.assertIn("planning liquidity wizard: prepared 0 gaps", stdout.getvalue())

    def test_main_planning_liquidity_wizard_reuses_context_and_removes_placeholder_gap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "liquidity-plan-input.json"
            existing = _synthetic_liquidity_input()
            existing["data_gaps"] = [{"code": "replace_with_known_gap_or_remove", "message": "placeholder"}]
            input_path.write_text(json.dumps(existing), encoding="utf-8")
            stdout = io.StringIO()

            with patch("builtins.input", side_effect=["", "", ""]), redirect_stdout(stdout):
                exit_code = main(["planning", "liquidity", "wizard", "--input", str(input_path), "--overwrite"])

            self.assertEqual(exit_code, 0)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(written["household_id"], existing["household_id"])
            self.assertEqual(written["as_of_date"], existing["as_of_date"])
            self.assertEqual(written["base_currency"], existing["base_currency"])
            self.assertEqual(written["data_gaps"], [])
            self.assertIn("contesto: nucleo=", stdout.getvalue())

    def test_main_planning_decumulation_build_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "decumulation-policy-set.json"
            net_worth_path = root / "net-worth.snapshot.json"
            liquidity_path = root / "liquidity-plan.snapshot.json"
            pension_path = root / "pension-income.snapshot.json"
            rita_path = root / "rita-options.snapshot.json"
            output_path = root / "decumulation-strategy.snapshot.json"
            input_path.write_text(json.dumps(_synthetic_decumulation_policy_set()), encoding="utf-8")
            net_worth_path.write_text(json.dumps(_synthetic_decumulation_net_worth()), encoding="utf-8")
            liquidity_path.write_text(json.dumps(_synthetic_decumulation_liquidity_plan()), encoding="utf-8")
            pension_path.write_text(json.dumps(_synthetic_pension_income_snapshot()), encoding="utf-8")
            rita_path.write_text(json.dumps(_synthetic_rita_options_snapshot()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "decumulation",
                        "build",
                        "--input",
                        str(input_path),
                        "--net-worth-snapshot",
                        str(net_worth_path),
                        "--liquidity-plan-snapshot",
                        str(liquidity_path),
                        "--pension-income-snapshot",
                        str(pension_path),
                        "--rita-options-snapshot",
                        str(rita_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("planning decumulation: partial 2 policies", stdout.getvalue())

    def test_main_planning_decumulation_wizard_writes_valid_input(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "decumulation-policy-set.json"
            answers = [
                "60",
                "67",
                "95",
                "36000.00",
                "24000.00",
                "asset_cash, asset_brokerage",
                "yes",
                "0.02,0.03",
                "0.10",
                "0.20",
                "0.15",
            ]
            stdout = io.StringIO()

            with patch("builtins.input", side_effect=answers), redirect_stdout(stdout):
                exit_code = main(["planning", "decumulation", "wizard", "--input", str(input_path)])

            self.assertEqual(exit_code, 0)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "decumulation-policy-set/v1")
            self.assertEqual(written["policies"][0]["withdrawal_order"], ["asset_cash", "asset_brokerage"])
            self.assertTrue(written["policies"][0]["include_rita"])
            self.assertEqual(written["data_gaps"], [])
            self.assertIn("planning decumulation wizard: prepared 0 gaps", stdout.getvalue())

    def test_main_planning_decumulation_wizard_uses_saved_context_without_metadata_prompts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "decumulation-policy-set.json"
            liquidity_input_path = root / "liquidity-plan-input.json"
            liquidity_snapshot_path = root / "liquidity-plan.snapshot.json"
            goals_snapshot_path = root / "planning-goals.snapshot.json"
            missing_goals_input_path = root / "missing-planning-goals.json"
            liquidity_input = _synthetic_liquidity_input()
            liquidity_input["household_id"] = "wizard_household"
            liquidity_input["as_of_date"] = "2026-07-20"
            liquidity_input_path.write_text(json.dumps(liquidity_input), encoding="utf-8")
            liquidity_snapshot_path.write_text(json.dumps(_synthetic_decumulation_liquidity_plan()), encoding="utf-8")
            goals_snapshot = _synthetic_planning_goals()
            goals_snapshot["objectives"][1]["target"]["value"] = "42000.00"
            goals_snapshot_path.write_text(json.dumps(goals_snapshot), encoding="utf-8")
            prompts: list[str] = []
            answers = iter(["60", "67", "95", "", "", "", "no", "0.02,0.03", "0.10", "0.20", "0.00"])

            def answer(prompt: str) -> str:
                prompts.append(prompt)
                return next(answers)

            stdout = io.StringIO()
            with (
                patch("family_office_engine.cli.main.default_liquidity_plan_input", return_value=liquidity_input_path),
                patch("family_office_engine.cli.main.default_liquidity_plan_output", return_value=liquidity_snapshot_path),
                patch("family_office_engine.cli.main.default_planning_goals_output", return_value=goals_snapshot_path),
                patch("family_office_engine.cli.main.default_planning_goals_input", return_value=missing_goals_input_path),
                patch("builtins.input", side_effect=answer),
                redirect_stdout(stdout),
            ):
                exit_code = main(["planning", "decumulation", "wizard", "--input", str(input_path)])

            self.assertEqual(exit_code, 0)
            joined_prompts = "\n".join(prompts)
            self.assertNotIn("Nome tecnico del nucleo/caso", joined_prompts)
            self.assertNotIn("Data di riferimento", joined_prompts)
            self.assertNotIn("Valuta base", joined_prompts)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(written["household_id"], "wizard_household")
            self.assertEqual(written["as_of_date"], "2026-07-20")
            self.assertEqual(written["policies"][0]["annual_spending_need"], "42000.00")
            self.assertEqual(written["policies"][0]["cash_buffer_target"], "18000.00")
            self.assertEqual(written["policies"][0]["withdrawal_order"], ["asset_brokerage", "asset_cash"])
            self.assertIn("contesto: nucleo=wizard_household", stdout.getvalue())

    def test_main_planning_decumulation_wizard_marks_unknown_tax_rates_as_gaps(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "decumulation-policy-set.json"
            answers = [
                "60",
                "67",
                "95",
                "36000.00",
                "24000.00",
                "asset_cash, asset_brokerage",
                "yes",
                "0.02,0.03",
                "",
                "",
                "",
            ]
            stdout = io.StringIO()

            with patch("builtins.input", side_effect=answers), redirect_stdout(stdout):
                exit_code = main(["planning", "decumulation", "wizard", "--input", str(input_path)])

            self.assertEqual(exit_code, 0)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            gap_codes = {gap["code"] for gap in written["data_gaps"]}
            self.assertIn("unknown_withdrawal_tax_rate", gap_codes)
            self.assertIn("unknown_pension_tax_rate", gap_codes)
            self.assertIn("unknown_rita_tax_rate", gap_codes)
            self.assertIn("prepared 3 gaps", stdout.getvalue())

    def test_main_planning_decumulation_demo_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "decumulation-strategy.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "decumulation",
                        "demo",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("planning decumulation demo: partial 2 policies", stdout.getvalue())

    def test_main_planning_goals_validate_unedited_draft_explains_next_step(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "planning-goals.json"
            output_path = root / "planning-goals.snapshot.json"
            input_path.write_text(
                json.dumps(
                    {
                        "schema_version": "planning-goals/v1",
                        "record_type": "PlanningGoals",
                        "household_id": None,
                        "as_of_date": None,
                        "planning_horizon": {"start_year": None, "end_year": None},
                        "risk_profile": {
                            "capacity": "unknown",
                            "tolerance": "unknown",
                            "max_loss_ratio": None,
                        },
                        "liquidity_policy": {
                            "minimum_reserve_months": None,
                            "preferred_bucket": "unknown",
                        },
                        "objectives": [],
                        "constraints": [],
                        "data_gaps": [{"code": "draft_not_completed", "message": "Complete the draft."}],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "goals",
                        "validate",
                        "--input",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("Planning goals input is still the starter draft", stdout.getvalue())
            self.assertIn("fo planning goals wizard --overwrite", stdout.getvalue())

    def test_main_planning_goals_demo_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            timeline_output_path = root / "timeline-events.snapshot.json"
            output_path = root / "planning-goals.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "goals",
                        "demo",
                        "--timeline-output",
                        str(timeline_output_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(timeline_output_path.exists())
            self.assertTrue(output_path.exists())
            self.assertIn(
                "planning goals demo: timeline=complete 8 events, goals=complete 2 objectives, 2 constraints, 0 gaps",
                stdout.getvalue(),
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["record_type"], "PlanningGoalsSnapshot")

    def test_main_planning_pension_contributions_demo_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "pension-contribution-options.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "pension-contributions",
                        "demo",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn(
                "planning pension-contributions demo: complete 3 options, best=employee_plus_match",
                stdout.getvalue(),
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "pension-contribution-options/v1")
            self.assertEqual(written["rule_pack"]["rule_pack_id"], "it.pension-contribution-deduction.2026.v1")

    def test_main_planning_pension_contributions_build_missing_input_suggests_wizard(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "missing-pension-contribution-input.json"
            output_path = root / "pension-contribution-options.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "pension-contributions",
                        "build",
                        "--input",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("fo planning pension-contributions wizard", stdout.getvalue())

    def test_main_planning_pension_contributions_wizard_writes_valid_input(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "pension-contribution-input.json"
            liquidity_input_path = root / "liquidity-plan-input.json"
            liquidity_snapshot_path = root / "liquidity-plan.snapshot.json"
            liquidity_input = _synthetic_liquidity_input()
            liquidity_input["household_id"] = "wizard_household"
            liquidity_input["as_of_date"] = "2026-07-20"
            liquidity_input_path.write_text(json.dumps(liquidity_input), encoding="utf-8")
            liquidity_snapshot_path.write_text(
                json.dumps(
                    {
                        "schema_version": "liquidity-plan/v1",
                        "record_type": "LiquidityPlanSnapshot",
                        "status": "complete",
                        "base_currency": "EUR",
                        "emergency_reserve": {"target_amount": "18000.00"},
                        "buckets": {
                            "emergency_reserve": {"total_value": "12000.00"},
                            "short_term": {"total_value": "22000.00"},
                        },
                        "asset_assignments": [],
                        "data_gaps": [],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            answers = [
                "0.35",
                "1000.00",
                "1500.00",
                "3000.00",
                "1000.00",
                "6000.00",
                "0.03",
            ]

            with (
                patch("family_office_engine.cli.main.default_liquidity_plan_input", return_value=liquidity_input_path),
                patch("family_office_engine.cli.main.default_liquidity_plan_output", return_value=liquidity_snapshot_path),
                patch("builtins.input", side_effect=answers),
                redirect_stdout(stdout),
            ):
                exit_code = main(["planning", "pension-contributions", "wizard", "--input", str(input_path)])

            self.assertEqual(exit_code, 0)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "pension-contribution-input/v1")
            self.assertEqual(written["household_id"], "wizard_household")
            self.assertEqual(written["tax_year"], 2026)
            self.assertEqual(written["available_liquidity"], "34000.00")
            self.assertEqual(written["minimum_liquidity_after_contributions"], "18000.00")
            self.assertEqual(len(written["options"]), 4)
            self.assertEqual(written["data_gaps"], [])
            self.assertIn("planning pension-contributions wizard: prepared 0 gaps", stdout.getvalue())

    def test_main_planning_tax_aware_portfolio_demo_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "tax-aware-portfolio.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "tax-aware-portfolio",
                        "demo",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn(
                "planning tax-aware-portfolio demo: complete 3 options, best=foreign_declarative_low_turnover",
                stdout.getvalue(),
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "tax-aware-portfolio/v1")
            self.assertEqual(written["rule_pack"]["rule_pack_id"], "it.tax-aware-investment.2026.v1")

    def test_main_planning_it_es_pension_tax_demo_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "it-es-pension-tax-classification.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "it-es-pension-tax",
                        "demo",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn(
                "planning it-es-pension-tax demo: complete 2/2 classified, 0 gaps, 0 warnings",
                stdout.getvalue(),
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "it-es-pension-tax-classification/v1")
            self.assertEqual(written["rule_pack"]["rule_pack_id"], "it-es.pension-tax-classification.2026.v1")

    def test_main_planning_spanish_pension_net_demo_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "spanish-pension-net-it-resident.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "spanish-pension-net",
                        "demo",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn(
                "planning spanish-pension-net demo: complete 2/2 complete, net=24370.00, 0 gaps, 0 warnings",
                stdout.getvalue(),
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "spanish-pension-net-it-resident/v1")
            self.assertEqual(written["rule_pack"]["rule_pack_id"], "it.spanish-pension-net-it-resident.2026.v1")

    def test_main_planning_pension_scenario_demo_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "pension-scenario.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "pension-scenario",
                        "demo",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn(
                "planning pension-scenario demo: complete 2 scenarios, selected=baseline_it_retirement, 0 gaps",
                stdout.getvalue(),
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "pension-scenario/v1")
            self.assertEqual(written["selected_scenario"]["initial_fiscal_residence"], "IT")

    def test_main_planning_it_es_eu_pension_wizard_writes_mixed_case_input(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "it-es-eu-pension-pro-rata-input.json"
            reconciliation_path = root / "spanish-contribution-reconciliation.snapshot.json"
            reconciliation_path.write_text(
                json.dumps(
                    {
                        "schema_version": "spanish-contribution-reconciliation/v1",
                        "status": "complete",
                        "months": [
                            {"month": "2021-01", "covered_by_vida_laboral": True},
                            {"month": "2021-02", "covered_by_vida_laboral": True},
                            {"month": "2021-03", "covered_by_vida_laboral": True},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            answers = [
                "2026-12",
                "1960-01-01",
                "2026-12-01",
                "180",
                "2020-12",
                "60",
                "2025-12",
                "yes",
                "2000.00",
                "12",
            ]
            stdout = io.StringIO()

            with (
                patch(
                    "family_office_engine.cli.main.default_spanish_contribution_reconciliation_output",
                    return_value=reconciliation_path,
                ),
                patch("builtins.input", side_effect=answers),
                redirect_stdout(stdout),
            ):
                exit_code = main(["planning", "it-es-eu-pension", "wizard", "--input", str(input_path)])

            self.assertEqual(exit_code, 0)
            written = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "it-es-eu-pension-pro-rata-input/v1")
            self.assertEqual(written["future_assumptions_status"], "explicit")
            self.assertNotIn("synthetic_fixture", json.dumps(written))
            self.assertEqual(written["insurance_periods"][1]["country"], "ES")
            self.assertEqual(written["insurance_periods"][1]["end_date"], "2025-12-31")
            self.assertEqual(written["spanish_theoretical_pension"]["basis"], "spanish_only_bases")
            self.assertEqual(written["data_gaps"], [])
            self.assertIn("planning it-es-eu-pension wizard: prepared 0 gaps", stdout.getvalue())

    def test_main_planning_spanish_eu_theoretical_pension_demo_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "spanish-eu-theoretical-pension.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "spanish-eu-theoretical-pension",
                        "demo",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn(
                "planning spanish-eu-theoretical-pension demo: complete theoretical=1916.76, 0 gaps",
                stdout.getvalue(),
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "spanish-eu-theoretical-pension/v1")
            self.assertEqual(written["rule_pack"]["rule_pack_id"], "eu.es.spanish-eu-theoretical-pension.2026.v1")

    def test_main_planning_it_es_eu_pension_build_uses_default_theoretical_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            theoretical_path = root / "spanish-eu-theoretical-pension.snapshot.json"
            output_path = root / "it-es-eu-pension-pro-rata.snapshot.json"
            stdout = io.StringIO()

            with (
                patch(
                    "family_office_engine.cli.main.default_spanish_eu_theoretical_pension_output",
                    return_value=theoretical_path,
                ),
                redirect_stdout(stdout),
            ):
                theoretical_exit = main(
                    [
                        "planning",
                        "spanish-eu-theoretical-pension",
                        "demo",
                        "--output",
                        str(theoretical_path),
                    ]
                )
                pro_rata_exit = main(
                    [
                        "planning",
                        "it-es-eu-pension",
                        "build",
                        "--input",
                        str(REPOSITORY_ROOT / "family-office-engine" / "examples" / "spanish-eu-theoretical-pension-pro-rata-input-sample.json"),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(theoretical_exit, 0)
            self.assertEqual(pro_rata_exit, 0)
            self.assertTrue(output_path.exists())
            self.assertIn(
                "planning it-es-eu-pension: complete entitlement=eligible_by_totalization, pro-rata=calculated, 0 gaps",
                stdout.getvalue(),
            )

    def test_main_planning_protection_demo_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "protection-gap.snapshot.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "planning",
                        "protection",
                        "demo",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn(
                "planning protection demo: complete 2 needs, 3 policies, shortfall=70000.00 EUR, 0 gaps",
                stdout.getvalue(),
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "protection-gap/v1")
            self.assertEqual(written["summary"]["investment_surrender_value"], "25000.00")

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
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["baseline_outcome"]["status"], "complete")
            self.assertEqual(written["tornado_data"][0]["impact_metric_id"], "final_balance_p50")

    def test_main_scenarios_evaluate_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            decision_scenario_path = root / "decision-scenario-v2.snapshot.json"
            input_path = root / "decision-outcome.json"
            output_path = root / "decision-outcome.snapshot.json"
            decision_scenario_path.write_text(json.dumps(_synthetic_decision_scenario_snapshot()), encoding="utf-8")
            input_path.write_text(json.dumps(_synthetic_decision_outcome_input()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "scenarios",
                        "evaluate",
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
            self.assertIn("scenarios: complete evaluator=retirement-monte-carlo/v1", stdout.getvalue())
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["record_type"], "DecisionOutcomeSnapshot")
            self.assertTrue(written["metrics"])

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

    def test_main_scenarios_dossier_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            decision_scenario_path = root / "decision-scenario-v2.snapshot.json"
            sensitivity_path = root / "sensitivity-analysis.snapshot.json"
            score_path = root / "decision-score.snapshot.json"
            input_path = root / "decision-dossier.json"
            output_path = root / "decision-dossier.snapshot.json"
            markdown_path = root / "decision-dossier.md"
            decision_scenario_path.write_text(json.dumps(_synthetic_decision_scenario_snapshot()), encoding="utf-8")
            sensitivity_path.write_text(json.dumps(_synthetic_sensitivity_analysis_snapshot()), encoding="utf-8")
            score_path.write_text(json.dumps(_synthetic_decision_score_snapshot()), encoding="utf-8")
            input_path.write_text(json.dumps(_synthetic_decision_dossier_input()), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "scenarios",
                        "dossier",
                        "--decision-scenario-snapshot",
                        str(decision_scenario_path),
                        "--sensitivity-analysis-snapshot",
                        str(sensitivity_path),
                        "--decision-score-snapshot",
                        str(score_path),
                        "--input",
                        str(input_path),
                        "--output",
                        str(output_path),
                        "--markdown-output",
                        str(markdown_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertIn("scenarios: complete recommendation=balanced, 0 blocking gaps", stdout.getvalue())

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
            "market": {
                "nominal_return": "0.03",
                "nominal_volatility": "0.10",
                "inflation": "0.02",
                "source": "synthetic fixture",
            },
            "personal": {"current_age": 60, "target_retirement_age": 64},
            "portfolio": {"starting_net_worth": "250000.00", "currency": "EUR"},
            "cashflow": {
                "family_expenses_yearly": "24000.00",
                "net_salary_monthly": "3000.00",
                "salary_months": 12,
                "retirement_income_yearly": "12000.00",
            },
            "withdrawal_policy": {"policy_id": "fixed_real_need", "source": "synthetic fixture"},
        },
        "data_gaps": [],
        "reproducibility": {"content_hash": "synthetic-hash"},
    }


def _synthetic_decision_outcome_input() -> dict:
    return {
        "schema_version": "decision-outcome/v1",
        "record_type": "DecisionOutcomeInput",
        "outcome_id": "synthetic_retirement_outcome",
        "label": "Synthetic retirement outcome",
        "evaluator_id": "retirement-monte-carlo/v1",
        "parameters": {"simulations": 25, "seed": 1234, "end_age": 95},
    }


def _synthetic_sensitivity_analysis_input() -> dict:
    return {
        "schema_version": "sensitivity-analysis/v1",
        "record_type": "SensitivityAnalysisInput",
        "analysis_id": "synthetic_sensitivity",
        "label": "Synthetic sensitivity analysis",
        "as_of_date": "2026-07-18",
        "seed": 20260718,
        "outcome_evaluation": {
            "schema_version": "decision-outcome/v1",
            "record_type": "DecisionOutcomeInput",
            "outcome_id": "synthetic-sensitivity-outcome",
            "label": "Synthetic sensitivity outcome",
            "evaluator_id": "retirement-monte-carlo/v1",
            "parameters": {"simulations": 25, "seed": 20260718, "end_age": 95},
            "impact_metric_id": "final_balance_p50",
        },
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
        "baseline_outcome": _synthetic_decision_outcome_snapshot(
            "baseline",
            "0.90",
            "620000.00",
            "0.30",
            "synthetic_base_case",
        ),
        "sensitivity_cases": [
            {
                "id": "return_up",
                "status": "complete",
                "outcome": _synthetic_decision_outcome_snapshot(
                    "return-up",
                    "0.78",
                    "700000.00",
                    "0.70",
                    "synthetic_base_case::sensitivity:return_up",
                ),
            }
        ],
        "stress_matrix": [],
        "data_gaps": [],
        "reproducibility": {"content_hash": "synthetic-sensitivity-hash"},
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
                "outcome_ref": {"kind": "sensitivity", "id": "return_up"},
                "metrics": {
                    "sustainability": {"outcome_metric_id": "success_rate"},
                    "final_wealth": {"outcome_metric_id": "final_balance_p50"},
                    "risk": {"outcome_metric_id": "risk_ratio"},
                },
            },
            {
                "alternative_id": "balanced",
                "label": "Balanced allocation",
                "outcome_ref": {"kind": "baseline"},
                "metrics": {
                    "sustainability": {"outcome_metric_id": "success_rate"},
                    "final_wealth": {"outcome_metric_id": "final_balance_p50"},
                    "risk": {"outcome_metric_id": "risk_ratio"},
                },
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


def _synthetic_decision_score_snapshot() -> dict:
    provenance = {
        "scenario_content_hash": "synthetic-hash",
        "evaluator_id": "retirement-monte-carlo/v1",
        "outcome_hash": "baseline-outcome-hash",
        "outcome_metric_id": "success_rate",
    }
    return {
        "schema_version": "decision-score/v1",
        "record_type": "DecisionScoreSnapshot",
        "status": "complete",
        "score_id": "synthetic_decision_score",
        "lineage_status": "complete",
        "alternatives": [
            {
                "alternative_id": "balanced",
                "label": "Balanced allocation",
                "status": "complete",
                "lineage_status": "complete",
                "total_score": "0.7210",
                "metrics": [
                    {
                        "metric_id": "sustainability",
                        "label": "Sustainability",
                        "raw_value": "0.78",
                        "normalized_score": "0.7800",
                        "weight": "0.45",
                        "weighted_score": "0.3510",
                        "provenance": provenance,
                    }
                ],
            },
            {
                "alternative_id": "aggressive",
                "label": "Aggressive allocation",
                "status": "complete",
                "lineage_status": "complete",
                "total_score": "0.6250",
                "metrics": [
                    {
                        "metric_id": "sustainability",
                        "label": "Sustainability",
                        "raw_value": "0.62",
                        "normalized_score": "0.6200",
                        "weight": "0.45",
                        "weighted_score": "0.2790",
                        "provenance": {**provenance, "outcome_hash": "return-up-outcome-hash"},
                    }
                ],
            },
        ],
        "ranking": [
            {"rank": 1, "alternative_id": "balanced", "label": "Balanced allocation", "total_score": "0.7210"},
            {"rank": 2, "alternative_id": "aggressive", "label": "Aggressive allocation", "total_score": "0.6250"},
        ],
        "data_gaps": [],
        "reproducibility": {"content_hash": "synthetic-score-hash"},
    }


def _synthetic_decision_outcome_snapshot(
    outcome_id: str,
    success_rate: str,
    final_balance: str,
    risk_ratio: str,
    scenario_id: str,
) -> dict:
    provenance = {
        "scenario_id": scenario_id,
        "scenario_content_hash": f"{scenario_id}-hash",
        "evaluator_id": "retirement-monte-carlo/v1",
        "evaluator_version": "v1",
        "seed": 20260718,
    }
    return {
        "schema_version": "decision-outcome/v1",
        "record_type": "DecisionOutcomeSnapshot",
        "status": "complete",
        "outcome_id": outcome_id,
        "metrics": [
            {"metric_id": "success_rate", "value": success_rate, "unit": "ratio", "provenance": provenance},
            {"metric_id": "final_balance_p50", "value": final_balance, "unit": "EUR", "provenance": provenance},
            {"metric_id": "risk_ratio", "value": risk_ratio, "unit": "ratio", "provenance": provenance},
        ],
        "data_gaps": [],
        "reproducibility": {"content_hash": f"{outcome_id}-outcome-hash"},
    }


def _synthetic_decision_dossier_input() -> dict:
    return {
        "schema_version": "decision-dossier/v1",
        "record_type": "DecisionDossierInput",
        "dossier_id": "synthetic_dossier",
        "label": "Synthetic decision dossier",
        "as_of_date": "2026-07-18",
        "blocking_gap_codes": [],
        "next_actions": [
            {"action_id": "human_review", "label": "Review ranking and evidence with a human reviewer."}
        ],
        "human_review": {"required": True, "reviewer_role": "human_reviewer"},
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


def _synthetic_planning_goals() -> dict:
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
                "target": {"metric": "reserve_months", "operator": "min", "unit": "months", "value": 12},
            },
            {
                "objective_id": "objective_retirement_income",
                "label": "Sustain retirement income",
                "category": "retirement_income",
                "priority": 2,
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
                "applies_to_objective_ids": ["objective_emergency_reserve"],
                "threshold": {"metric": "reserve_months", "operator": "min", "unit": "months", "value": 12},
            },
            {
                "constraint_id": "constraint_retirement_timing",
                "label": "Retirement event anchors the income horizon",
                "constraint_type": "timing",
                "severity": "soft",
                "priority": 2,
                "applies_to_objective_ids": ["objective_retirement_income"],
                "timeline_event_ids": ["retirement"],
                "threshold": {"metric": "target_year", "operator": "target", "unit": "year", "value": 2039},
            },
        ],
        "data_gaps": [],
    }


def _synthetic_planning_goals_snapshot() -> dict:
    return {
        "schema_version": "planning-goals/v1",
        "record_type": "PlanningGoalsSnapshot",
        "status": "complete",
        "liquidity_policy": {"minimum_reserve_months": 12, "preferred_bucket": "emergency_reserve"},
        "data_gaps": [],
    }


def _synthetic_liquidity_input() -> dict:
    return {
        "schema_version": "liquidity-plan-input/v1",
        "record_type": "LiquidityPlanInput",
        "household_id": "synthetic_household",
        "as_of_date": "2026-07-18",
        "base_currency": "EUR",
        "monthly_expenses": "3000.00",
        "minimum_reserve_months": 6,
        "concentration_threshold": "0.80",
        "data_gaps": [],
    }


def _synthetic_liquidity_net_worth() -> dict:
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


def _synthetic_liquidity_availability() -> dict:
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
                "asset_id": "asset_family_home",
                "liquidity_tier": "illiquid",
                "first_available_date": "2027-07-18",
                "constraints": ["co_ownership", "sale_process"],
                "risk_level": "illiquid",
            },
        ],
        "data_gaps": [],
    }


def _synthetic_decumulation_policy_set() -> dict:
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
                "end_age": 95,
                "annual_spending_need": "36000.00",
                "cash_buffer_target": "24000.00",
                "withdrawal_order": ["asset_brokerage", "asset_cash"],
                "annual_return_sequence": ["-0.08", "0.02", "0.03"],
                "withdrawal_tax_rate": "0.10",
                "pension_tax_rate": "0.20",
                "rita_tax_rate": "0.15",
                "include_rita": True,
            },
            {
                "policy_id": "later_no_rita",
                "label": "Later without RITA",
                "retirement_age": 67,
                "end_age": 90,
                "annual_spending_need": "36000.00",
                "cash_buffer_target": "30000.00",
                "withdrawal_order": ["asset_cash", "asset_brokerage"],
                "annual_return_sequence": ["0.03"],
                "withdrawal_tax_rate": "0.10",
                "pension_tax_rate": "0.20",
                "rita_tax_rate": "0.15",
                "include_rita": False,
            },
        ],
        "data_gaps": [],
    }


def _synthetic_decumulation_net_worth() -> dict:
    return {
        "schema_version": "net-worth/v1",
        "record_type": "NetWorthSnapshot",
        "components": [
            {
                "id": "asset_cash",
                "label": "Synthetic cash",
                "type": "asset",
                "asset_class": "cash",
                "value": "30000.00",
                "currency": "EUR",
            },
            {
                "id": "asset_brokerage",
                "label": "Synthetic brokerage",
                "type": "asset",
                "asset_class": "brokerage",
                "value": "220000.00",
                "currency": "EUR",
            },
            {
                "id": "asset_home",
                "label": "Synthetic home",
                "type": "asset",
                "asset_class": "real_estate",
                "value": "250000.00",
                "currency": "EUR",
            },
        ],
        "data_gaps": [],
    }


def _synthetic_decumulation_liquidity_plan() -> dict:
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


def _synthetic_rita_options_snapshot() -> dict:
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
