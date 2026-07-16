import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.tax_reconciliation import reconcile_tax_sources


def payroll_snapshot(records):
    return {
        "record_type": "PayrollSnapshot",
        "schema_version": "payroll/v1",
        "records": records,
    }


def tax_documents_snapshot(records):
    return {
        "record_type": "TaxDocumentsSnapshot",
        "schema_version": "tax-documents/v1",
        "records": records,
    }


class TaxReconciliationTest(unittest.TestCase):
    def test_reconcile_tax_sources_matches_same_year_sources(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payroll_path = root / "payroll.json"
            tax_docs_path = root / "tax-documents.json"
            output_path = root / "tax-reconciliation.json"
            payroll_path.write_text(
                json.dumps(
                    payroll_snapshot(
                        [
                            {
                                "period_label": "Gennaio 2025",
                                "period_year": 2025,
                                "employer": "ACME SRL",
                                "net_pay": "2500.00",
                                "taxable_irpef": "3000.00",
                                "irpef_withheld": "750.00",
                            }
                        ]
                    )
                ),
                encoding="utf-8",
            )
            tax_docs_path.write_text(
                json.dumps(
                    tax_documents_snapshot(
                        [
                            {
                                "document_type": "certificazione_unica",
                                "fields": {"model_year": "2026", "tax_year": "2025"},
                            },
                            {
                                "document_type": "dichiarazione_redditi_pf",
                                "fields": {"model_year": "2026", "tax_year": "2025"},
                            },
                        ]
                    )
                ),
                encoding="utf-8",
            )

            result = reconcile_tax_sources(payroll_path, tax_docs_path, output_path)

            self.assertEqual(result["schema_version"], "tax-reconciliation/v1")
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["years"][0]["year"], 2025)
            self.assertEqual(result["years"][0]["payroll"]["taxable_irpef_observed"], "3000.00")
            self.assertEqual(result["data_gaps"], [])

    def test_reconcile_tax_sources_reports_temporal_gaps_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payroll_path = root / "payroll.json"
            tax_docs_path = root / "tax-documents.json"
            output_path = root / "tax-reconciliation.json"
            payroll_record = {
                "period_label": "Gennaio 2026",
                "period_year": 2026,
                "employer": "ACME SRL",
                "net_pay": "2500.00",
                "taxable_irpef": "3000.00",
                "irpef_withheld": "750.00",
            }
            payroll_path.write_text(json.dumps(payroll_snapshot([payroll_record, payroll_record])), encoding="utf-8")
            tax_docs_path.write_text(
                json.dumps(
                    tax_documents_snapshot(
                        [
                            {
                                "document_type": "certificazione_unica",
                                "fields": {"model_year": "2026", "tax_year": "2025"},
                            }
                        ]
                    )
                ),
                encoding="utf-8",
            )

            result = reconcile_tax_sources(payroll_path, tax_docs_path, output_path)

            self.assertEqual(result["status"], "partial")
            gap_codes = {gap["code"] for gap in result["data_gaps"]}
            self.assertIn("duplicate_payroll_records_excluded", gap_codes)
            self.assertIn("payroll_year_without_tax_document", gap_codes)
            self.assertIn("tax_document_year_without_payroll", gap_codes)


if __name__ == "__main__":
    unittest.main()
