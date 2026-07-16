import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.net_worth import NetWorthError, consolidate_net_worth


FONTE_SNAPSHOT = {
    "record_type": "FonTeSourceBundle",
    "schema_version": "fonte-source-bundle/v1",
    "position": {
        "statement_date": "2026-07-08",
        "position_value": "44243.42",
        "pending_investment": "0.00",
        "holdings": [],
    },
}


INVESTMENTS_SNAPSHOT = {
    "record_type": "InvestmentsSnapshot",
    "positions": [
        {
            "provider": "Moneyfarm",
            "description": "Gestione patrimoniale",
            "instrument_type": "managed_portfolio",
            "market_value": "1000.25",
            "currency": "EUR",
            "statement_date": "2025-12-31",
            "source": {"filename": "moneyfarm.pdf"},
        },
        {
            "provider": "Kutxabank",
            "description": "Saldo cuenta",
            "instrument_type": "cash_account",
            "market_value": "350.22",
            "currency": "EUR",
            "statement_date": "2025-12-31",
            "source": {"filename": "kutxabank.pdf"},
        },
    ],
    "data_gaps": [
        {
            "code": "unsupported_investment_statement",
            "filename": "unsupported.pdf",
            "message": "No parser matched.",
        }
    ],
}


BANK_INSURANCE_SNAPSHOT = {
    "record_type": "BankInsuranceSnapshot",
    "items": [
        {
            "provider": "Kutxabank",
            "description": "Current account",
            "document_group": "bank",
            "amount_type": "account_balance",
            "amount": "250.00",
            "currency": "EUR",
            "statement_date": "2025-12-31",
            "source": {"filename": "bank.pdf"},
        },
        {
            "provider": "Generali",
            "description": "Annual contributions",
            "document_group": "insurance",
            "amount_type": "annual_contributions",
            "amount": "2802.58",
            "currency": "EUR",
            "period_year": "2025",
            "source": {"filename": "generali.pdf"},
        },
    ],
    "data_gaps": [],
}


class NetWorthTest(unittest.TestCase):
    def test_consolidate_net_worth_includes_fonte_asset(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            fonte_path = root / "fonte.snapshot.json"
            output_path = root / "net-worth.snapshot.json"
            fonte_path.write_text(json.dumps(FONTE_SNAPSHOT), encoding="utf-8")

            result = consolidate_net_worth(fonte_path, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["record_type"], "NetWorthSnapshot")
            self.assertEqual(written["totals"]["assets"], "44243.42")
            self.assertEqual(written["totals"]["liabilities"], "0.00")
            self.assertEqual(written["totals"]["net_worth"], "44243.42")
            self.assertEqual(written["components"][0]["asset_class"], "pension")

    def test_consolidate_net_worth_includes_investments_and_balance_items(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            fonte_path = root / "fonte.snapshot.json"
            investments_path = root / "investments.snapshot.json"
            bank_insurance_path = root / "bank-insurance.snapshot.json"
            output_path = root / "net-worth.snapshot.json"
            fonte_path.write_text(json.dumps(FONTE_SNAPSHOT), encoding="utf-8")
            investments_path.write_text(json.dumps(INVESTMENTS_SNAPSHOT), encoding="utf-8")
            bank_insurance_path.write_text(json.dumps(BANK_INSURANCE_SNAPSHOT), encoding="utf-8")

            result = consolidate_net_worth(
                fonte_path,
                output_path,
                investments_snapshot_path=investments_path,
                bank_insurance_snapshot_path=bank_insurance_path,
            )

            self.assertEqual(result["totals"]["assets"], "45843.89")
            self.assertEqual(result["totals"]["net_worth"], "45843.89")
            self.assertEqual(len(result["components"]), 4)
            self.assertIn("investments", result["sources"])
            self.assertIn("bank_insurance", result["sources"])
            self.assertTrue(
                any("annual_contributions" in gap for gap in result["data_gaps"])
            )
            self.assertTrue(
                any("unsupported_investment_statement" in gap for gap in result["data_gaps"])
            )

    def test_consolidate_net_worth_uses_latest_moneyfarm_statement(self):
        investments_snapshot = {
            "record_type": "InvestmentsSnapshot",
            "positions": [
                {
                    "provider": "Moneyfarm",
                    "description": "Gestione patrimoniale",
                    "instrument_type": "managed_portfolio",
                    "market_value": "1000.00",
                    "currency": "EUR",
                    "statement_date": "2024-12-31",
                    "source": {"filename": "moneyfarm-2024.pdf"},
                },
                {
                    "provider": "Moneyfarm",
                    "description": "Gestione patrimoniale",
                    "instrument_type": "managed_portfolio",
                    "market_value": "1500.00",
                    "currency": "EUR",
                    "statement_date": "2025-12-31",
                    "source": {"filename": "moneyfarm-2025.pdf"},
                },
            ],
            "data_gaps": [],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            fonte_path = root / "fonte.snapshot.json"
            investments_path = root / "investments.snapshot.json"
            output_path = root / "net-worth.snapshot.json"
            fonte_path.write_text(json.dumps(FONTE_SNAPSHOT), encoding="utf-8")
            investments_path.write_text(json.dumps(investments_snapshot), encoding="utf-8")

            result = consolidate_net_worth(
                fonte_path,
                output_path,
                investments_snapshot_path=investments_path,
            )

            moneyfarm_components = [
                component
                for component in result["components"]
                if component["label"] == "Moneyfarm Gestione patrimoniale"
            ]
            self.assertEqual(len(moneyfarm_components), 1)
            self.assertEqual(moneyfarm_components[0]["value"], "1500.00")
            self.assertTrue(
                any("moneyfarm-2024.pdf" in gap for gap in result["data_gaps"])
            )

    def test_consolidate_net_worth_reports_missing_fonte_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_path = root / "net-worth.snapshot.json"

            result = consolidate_net_worth(root / "missing-fonte.json", output_path)

            self.assertEqual(result["totals"]["net_worth"], "0.00")
            self.assertEqual(len(result["data_gaps"]), 1)

    def test_consolidate_net_worth_rejects_fonte_without_position(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            fonte_path = root / "fonte.snapshot.json"
            output_path = root / "net-worth.snapshot.json"
            fonte_path.write_text(
                json.dumps({"record_type": "FonTeSourceBundle"}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(NetWorthError, "no extracted position"):
                consolidate_net_worth(fonte_path, output_path)


if __name__ == "__main__":
    unittest.main()
