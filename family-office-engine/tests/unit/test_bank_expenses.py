import json
import io
import tempfile
import unittest
import zipfile
from decimal import Decimal
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.ingestion.bank_expenses import (
    _parse_date,
    _propose_category,
    import_bank_expense_exports,
    review_bank_expenses,
    review_bank_expenses_grouped,
)


class BankExpensesTest(unittest.TestCase):
    def test_category_proposal_covers_common_unknown_merchants_and_financial_rows(self):
        self.assertEqual(_propose_category("Operazione POS Eurozona TOKI Faenza", Decimal("-25")), ("food", True))
        self.assertEqual(_propose_category("Operazione POS Eurozona CINEDREAM Faenza", Decimal("-10")), ("leisure", True))
        self.assertEqual(_propose_category("Prelevamento su nostro bancomat", Decimal("-100")), ("cash_withdrawal", True))
        self.assertEqual(_propose_category("Prelievo bancomat data ora op sportello Faenza", Decimal("-50")), ("cash_withdrawal", True))
        self.assertEqual(
            _propose_category("Prelievo pagament maestro vpay data ora op LUL ticket machine pagamento POS no zona euro", Decimal("-18")),
            ("transport", True),
        )
        self.assertEqual(_propose_category("Prelievo non meglio specificato", Decimal("-20")), ("unknown", True))
        self.assertEqual(_propose_category("Spese tenuta conto", Decimal("-5")), ("financial_non_expense", False))
        self.assertEqual(_propose_category("HERA S.P.A. utenza", Decimal("-48.21")), ("utilities", True))
        self.assertEqual(_propose_category("Sottosc fondi PAC Etica SGR", Decimal("-1000")), ("financial_non_expense", False))
        self.assertEqual(_propose_category("Spesa PagoBANCOMAT al distributore AGIP", Decimal("-60")), ("transport", True))
        self.assertEqual(_propose_category("Prelievo pagament maestro vpay LUL ticket machine Victoria", Decimal("-18")), ("transport", True))
        self.assertEqual(_propose_category("Spesa PagoBANCOMAT Locali Parco", Decimal("-25")), ("unknown", True))

    def test_import_normalizes_categories_and_excludes_non_expenses(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "documents" / "banca" / "spese"
            source.mkdir(parents=True)
            (source / "export.csv").write_text(
                "Data;Descrizione;Dare;Avere;Valuta\n"
                "01/01/2026;Affitto gennaio;1200,00;;EUR\n"
                "02/01/2026;Supermercato;85,50;;EUR\n"
                "03/01/2026;Stipendio;;3000,00;EUR\n"
                "04/01/2026;Bonifico giroconto;500,00;;EUR\n",
                encoding="utf-8",
            )
            snapshot = import_bank_expense_exports(source, root / "snapshots" / "transactions.json")

            self.assertEqual(snapshot["status"], "complete")
            self.assertEqual(snapshot["summary"]["transaction_count"], 4)
            self.assertEqual(snapshot["summary"]["expense_count"], 2)
            proposals = {item["description"]: item["category_proposal"] for item in snapshot["transactions"]}
            self.assertEqual(proposals["Affitto gennaio"], "housing")
            self.assertEqual(proposals["Supermercato"], "food")
            self.assertFalse(next(item for item in snapshot["transactions"] if item["description"] == "Bonifico giroconto")["include_in_expenses"])

    def test_import_accepts_excel_serial_date(self):
        self.assertEqual(_parse_date("39573"), "2008-05-05")

    def test_import_reads_all_excel_sheets(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "documents" / "banca" / "spese"
            source.mkdir(parents=True)
            workbook = source / "multi-year.xlsx"
            sheet = lambda serial, description: (
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                '<row><c r="A1" t="inlineStr"><is><t>Data</t></is></c><c r="B1" t="inlineStr"><is><t>Causale</t></is></c><c r="C1" t="inlineStr"><is><t>Dare</t></is></c></row>'
                f'<row><c r="A2"><v>{serial}</v></c><c r="B2" t="inlineStr"><is><t>{description}</t></is></c><c r="C2"><v>100</v></c></row>'
                '</sheetData></worksheet>'
            )
            with zipfile.ZipFile(workbook, "w") as archive:
                archive.writestr("xl/worksheets/sheet1.xml", sheet(43831, "Affitto 2020"))
                archive.writestr("xl/worksheets/sheet2.xml", sheet(44197, "Affitto 2021"))

            snapshot = import_bank_expense_exports(source, root / "transactions.json")
            self.assertEqual(snapshot["summary"]["transaction_count"], 2)
            self.assertEqual({item["date"] for item in snapshot["transactions"]}, {"2020-01-01", "2021-01-01"})

    def test_import_uses_headers_of_each_excel_sheet(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "documents" / "banca" / "spese"
            source.mkdir(parents=True)
            workbook = source / "different-layouts.xlsx"

            def sheet(headers, values):
                header_cells = "".join(
                    f'<c r="{column}1" t="inlineStr"><is><t>{header}</t></is></c>'
                    for column, header in zip(("A", "B", "C"), headers)
                )
                value_cells = "".join(
                    f'<c r="{column}2" t="inlineStr"><is><t>{value}</t></is></c>'
                    for column, value in zip(("A", "B", "C"), values)
                )
                return (
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                    f'<row>{header_cells}</row><row>{value_cells}</row></sheetData></worksheet>'
                )

            with zipfile.ZipFile(workbook, "w") as archive:
                archive.writestr("xl/worksheets/sheet1.xml", sheet(("Data", "Descrizione", "Dare"), ("43831", "Supermercato", "100")))
                archive.writestr("xl/worksheets/sheet2.xml", sheet(("Data Contabile", "Importo", "Descrizione"), ("44197", "-50", "Farmacia")))

            snapshot = import_bank_expense_exports(source, root / "transactions.json")
            self.assertEqual(snapshot["summary"]["transaction_count"], 2)
            self.assertEqual({item["category_proposal"] for item in snapshot["transactions"]}, {"food", "health"})

    def test_review_builds_lifecycle_plan_only_from_approved_categories(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "documents" / "banca" / "spese"
            source.mkdir(parents=True)
            (source / "export.csv").write_text(
                "date,description,amount\n2026-01-01,Affitto,-1200\n2026-02-01,Affitto,-1200\n",
                encoding="utf-8",
            )
            input_path = root / "transactions.json"
            import_bank_expense_exports(source, input_path)
            result = review_bank_expenses(
                input_path,
                root / "review.json",
                root / "lifecycle.json",
                "household_private",
                "2026-09-03",
                {"housing": "housing"},
            )

            self.assertEqual(result["review"]["summary"]["approved_count"], 2)
            lifecycle = json.loads((root / "lifecycle.json").read_text(encoding="utf-8"))
            self.assertEqual(lifecycle["expense_entries"][0]["category"], "housing")
            self.assertEqual(lifecycle["expense_entries"][0]["amount"], "2400.00")
            self.assertEqual(lifecycle["expense_entries"][0]["start_year"], 2026)

    def test_cli_import_and_review_bank_exports(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "documents" / "banca" / "spese"
            source.mkdir(parents=True)
            (source / "export.csv").write_text("date,description,amount\n2026-01-01,Affitto,-1200\n", encoding="utf-8")
            transactions = root / "transactions.json"
            review = root / "review.json"
            lifecycle = root / "lifecycle.json"
            lifecycle_snapshot = root / "lifecycle.snapshot.json"
            with patch("family_office_engine.cli.main._validate_v66a_input_path", side_effect=lambda path, error: path.resolve()), redirect_stdout(io.StringIO()):
                self.assertEqual(main(["expenses", "import-bank", "--input-dir", str(source), "--output", str(transactions)]), 0)
            output = io.StringIO()
            with patch("family_office_engine.cli.main._validate_v66a_input_path", side_effect=lambda path, error: path.resolve()), patch(
                "family_office_engine.cli.main.default_lifecycle_expenses_output", return_value=lifecycle_snapshot
            ), patch("builtins.input", side_effect=["n", "d", "y"]), redirect_stdout(output):
                self.assertEqual(main(["expenses", "review-bank", "--input", str(transactions), "--output", str(review), "--lifecycle-output", str(lifecycle)]), 0)
            self.assertIn("Affitto", output.getvalue())
            self.assertTrue(review.exists())
            self.assertTrue(lifecycle_snapshot.exists())

    def test_cli_reviews_homogeneous_groups_in_batch_and_keeps_exceptions(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "documents" / "banca" / "spese"
            source.mkdir(parents=True)
            (source / "export.csv").write_text(
                "date,description,amount\n"
                "2026-01-01,Supermercato Via Roma,-10\n"
                "2026-02-01,Supermercato Via Roma,-20\n"
                "2026-03-01,Acquisto speciale,-5\n",
                encoding="utf-8",
            )
            transactions = root / "transactions.json"
            review = root / "review.json"
            lifecycle = root / "lifecycle.json"
            lifecycle_snapshot = root / "lifecycle.snapshot.json"
            import_bank_expense_exports(source, transactions)
            output = io.StringIO()
            with patch("family_office_engine.cli.main._validate_v66a_input_path", side_effect=lambda path, error: path.resolve()), patch(
                "family_office_engine.cli.main.default_lifecycle_expenses_output", return_value=lifecycle_snapshot
            ), patch("builtins.input", side_effect=["y", "e"]), redirect_stdout(output):
                self.assertEqual(main(["expenses", "review-bank", "--input", str(transactions), "--output", str(review), "--lifecycle-output", str(lifecycle)]), 0)
            self.assertIn("Confermata in blocco la categoria food: 1 gruppi", output.getvalue())
            reviewed = json.loads(review.read_text(encoding="utf-8"))
            self.assertEqual(1, reviewed["summary"]["approved_group_count"])
            self.assertEqual(1, reviewed["summary"]["unresolved_group_count"])

    def test_grouped_review_preserves_raw_rows_and_exposes_exceptions(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "documents" / "banca" / "spese"
            source.mkdir(parents=True)
            (source / "export.csv").write_text(
                "date,description,amount\n"
                "2026-01-01,Supermercato Via Roma,-10\n"
                "2026-02-01,Supermercato Via Roma,-20\n"
                "2026-03-01,Acquisto speciale,-5\n",
                encoding="utf-8",
            )
            transactions = root / "transactions.json"
            import_bank_expense_exports(source, transactions)
            result = review_bank_expenses_grouped(
                transactions, root / "review.json", root / "lifecycle.json", "household_private", "2026-09-06", {"merchant_group_0001": "other"}, root / "rules.json"
            )
            groups = result["review"]["groups"]
            self.assertEqual(len(groups), 2)
            self.assertEqual(groups[0]["transaction_count"], 2)
            self.assertEqual(groups[0]["review_priority"], "high_homogeneity")
            self.assertEqual(groups[0]["total"], "30.00")
            self.assertEqual(groups[1]["transaction_count"], 1)
            self.assertIn("single_transaction", groups[1]["exception_codes"])
            self.assertEqual(result["review"]["transactions"][-1]["description"], "Acquisto speciale")
            rules = json.loads((root / "rules.json").read_text(encoding="utf-8"))
            self.assertEqual(rules["schema_version"], "bank-expense-review-rules/v1")

    def test_local_merchant_rule_is_applied_on_next_import(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "documents" / "banca" / "spese"
            source.mkdir(parents=True)
            (source / "export.csv").write_text("date,description,amount\n2026-01-01,Acquisto speciale,-5\n", encoding="utf-8")
            transactions = root / "transactions.json"
            import_bank_expense_exports(source, transactions)
            first = json.loads(transactions.read_text(encoding="utf-8"))["transactions"][0]
            rules = root / "rules.json"
            rules.write_text(json.dumps({"schema_version": "bank-expense-review-rules/v1", "rules_by_merchant": {first["merchant_fingerprint"]: {"rule_id": "r1", "category": "leisure", "provenance": "human_review:test"}}}), encoding="utf-8")
            import_bank_expense_exports(source, root / "transactions-2.json", rules)
            applied = json.loads((root / "transactions-2.json").read_text(encoding="utf-8"))["transactions"][0]
            self.assertEqual(applied["category_proposal"], "leisure")
            self.assertEqual(applied["rule_applied"], "r1")


if __name__ == "__main__":
    unittest.main()
