import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.ingestion.investments import (
    InvestmentsImportError,
    _decode_pdf_unicode_tokens,
    _extract_pdf_content_stream_text,
    import_investments,
    parse_investment_text,
)


AMUNDI_TEXT = """
Amundi Societa di Gestione del Risparmio S.p.A.
Quanto hai finora maturato nella tua posizione individuale
EUR + =
EUR 6.000,00 EUR 0,00 EUR 916,35 EUR 6.916,35
Hai versato(1)Hai gia richiesto Risultato netto della gestione(2)Posizione individuale al
31/12/2025
"""

MONEYFARM_TEXT = """
Moneyfarm
Data Rendiconto: 31/12/2024
TOTALE PATRIMONIO FINALE
30/09/2024 28.634,58
29.689,70
RISULTATO DI GESTIONE
"""

KUTXABANK_TEXT = """
Kutxabank
Ejercicio: 2025
CUENTAS ALAVISTA
Saldo medio 4 trimestre
Saldo a31-12
CUENTA DEAHORRO 910919158-3 2 265,06 350,22
Guztira
=Total
265,06
350,22
FONDOS DEINVERSION GESTIONADOS PORKUTXABANK GESTION
Producto
ISIN
Cuenta
N titulares
Participaciones
al31-12
Valor participacion
al31-12
Valor liquidativo
al31-12
KBGARENDIMIENTO EXTRA ES0114390000 944467285-9 2 2.593,118593 25,930045 67.239,68
Guztira
=Total
67.239,68
"""

KUTXABANK_PENSION_TEXT = """
/UNIC004B/UNIC0075/UNIC0074/UNIC0078/UNIC0061/UNIC0062/UNIC0061/UNIC006E/UNIC006B
/LK020000/LU020000/LT020000/LX020000/LA020000/LB020000/LA020000/LN020000/SP010000/LP020000/LE020000/LN020000/LS020000/LI020000/LO020000/LN020000/LE020000/LS020000
KUTXABANK PENSIONES, S.A.U.
ENTIDAD GESTORA DE FONDOS DE PENSIONES
31 12 25 SALDO AL FINAL DEL PERIODO     13 699 97 EUR      8 932887 EURKB RV MIXTO 60 PP
KUTXABANK RV MIXTO 60 F.P.
"""

KUTXABANK_GESTION_STANDALONE_TEXT = """
DATOS PARA SU DECLARACIÓN FISCAL
Kutxabank Gestión SGIIC SAU
NRO. PARTICIPACIONES
AL 31-12
VALOR LIQUIDATIVO AL 31-12
VALOR PARTICIPACIÓN
AL 31-12
18/03/2026 9444672859 21025       25 93101045      67 239 68    2 593 118593
KUTXABANK GESTION ACTIVA RENDIMIENTO FI
"""


CONSULTINVEST_TEXT = """
Rendiconto del servizio di Riferimento
Consultinvest
Mandato:
000/0000000-CONSULENZA FINANZIARIA
Periodo di riferimento:
01/01/2026 - 31/03/2026
Prospetto riassuntivo al 31/03/2026 - CONSULENZA FINANZIARIA
Patrimonio iniziale
28.672,65
Patrimonio finale
28.288,40
"""

DIRECTA_TEXT = """
Oggetto: Situazione Patrimoniale alla data Operazione31/12/2025 Pag. 1
Conto n.Z0000Intestato aSYNTHETIC HOLDER
TOTALE LIQUIDITA':             17.725,26
PORTAFOGLIO TITOLI QUANTITA'/VALORE NOMINALE PREZZO VALORE EURO
_____________________ TOTALE TITOLI EURO
                 0,00
DIRECTA S.I.M.p.A.
"""

ETICA_BALANCE_CERTIFICATE_TEXT = """
Milano, 10/07/2024
Oggetto: Attestazione saldo al 29/12/2023
Controvalore del suo investimento al 29/12/2023
Codice rapporto:
 00000000
Fondo
Numero Quote
Valore Quota
Controvalore
ETICA AZIONARIO CL.R
987,296
€
13,968
€
13.790,55
ETICA RENDITA BILANCIATA CL. R
-
-
-
"""


class InvestmentsTest(unittest.TestCase):
    def test_decode_pdf_layout_tokens(self):
        result = _decode_pdf_unicode_tokens(
            "/LK020000/LB020000/SP010000/ND010000/ND030000/SL760000/ND020000/ND050000"
        )

        self.assertEqual(result, "KB 13/25")

    def test_parse_amundi_position(self):
        result = parse_investment_text(AMUNDI_TEXT, "IT", "amundi.pdf")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["provider"], "Amundi")
        self.assertEqual(result["positions"][0]["market_value"], "6916.35")
        self.assertEqual(result["positions"][0]["statement_date"], "2025-12-31")

    def test_parse_moneyfarm_position(self):
        result = parse_investment_text(MONEYFARM_TEXT, "IT", "moneyfarm.pdf")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["provider"], "Moneyfarm")
        self.assertEqual(result["positions"][0]["market_value"], "29689.70")
        self.assertEqual(result["positions"][0]["statement_date"], "2024-12-31")

    def test_parse_consultinvest_position(self):
        result = parse_investment_text(CONSULTINVEST_TEXT, "IT", "consultinvest.pdf")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["provider"], "Consultinvest")
        self.assertEqual(result["positions"][0]["instrument_type"], "managed_portfolio")
        self.assertEqual(result["positions"][0]["market_value"], "28288.40")
        self.assertEqual(result["positions"][0]["statement_date"], "2026-03-31")
        self.assertEqual(result["positions"][0]["account"], "0000000000")

    def test_parse_directa_cash_position(self):
        result = parse_investment_text(DIRECTA_TEXT, "IT", "directa.pdf")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["provider"], "Directa")
        self.assertEqual(len(result["positions"]), 1)
        self.assertEqual(result["positions"][0]["instrument_type"], "cash_account")
        self.assertEqual(result["positions"][0]["market_value"], "17725.26")
        self.assertEqual(result["positions"][0]["statement_date"], "2025-12-31")
        self.assertEqual(result["positions"][0]["account"], "Z0000")

    def test_parse_etica_balance_certificate_position(self):
        result = parse_investment_text(ETICA_BALANCE_CERTIFICATE_TEXT, "IT", "etica.pdf")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["provider"], "Etica")
        self.assertEqual(len(result["positions"]), 1)
        self.assertEqual(result["positions"][0]["instrument_type"], "investment_fund")
        self.assertEqual(result["positions"][0]["description"], "ETICA AZIONARIO CL.R")
        self.assertEqual(result["positions"][0]["market_value"], "13790.55")
        self.assertEqual(result["positions"][0]["statement_date"], "2023-12-29")
        self.assertEqual(result["positions"][0]["account"], "00000000")

    def test_extract_pdf_content_stream_uses_to_unicode_map(self):
        result = _extract_pdf_content_stream_text(_FakeReader())

        self.assertEqual(result, "AB\nOK")

    def test_parse_kutxabank_tax_data_cash_position(self):
        result = parse_investment_text(KUTXABANK_TEXT, "ES", "kutxabank.pdf")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["provider"], "Kutxabank")
        self.assertEqual(result["positions"][0]["instrument_type"], "cash_account")
        self.assertEqual(result["positions"][0]["market_value"], "350.22")

    def test_parse_kutxabank_tax_data_fund_position(self):
        result = parse_investment_text(KUTXABANK_TEXT, "ES", "kutxabank.pdf")

        self.assertEqual(len(result["positions"]), 2)
        self.assertEqual(result["positions"][1]["instrument_type"], "investment_fund")
        self.assertEqual(result["positions"][1]["market_value"], "67239.68")
        self.assertIn("ES0114390000", result["positions"][1]["description"])

    def test_parse_kutxabank_pension_plan_final_balance(self):
        result = parse_investment_text(KUTXABANK_PENSION_TEXT, "ES", "kutxabank-pension.pdf")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["provider"], "Kutxabank")
        self.assertEqual(result["positions"][0]["instrument_type"], "pension_plan")
        self.assertEqual(result["positions"][0]["description"], "KB RV MIXTO 60 PP")
        self.assertEqual(result["positions"][0]["market_value"], "13699.97")
        self.assertEqual(result["positions"][0]["statement_date"], "2025-12-31")

    def test_parse_kutxabank_gestion_standalone_fund_statement(self):
        result = parse_investment_text(KUTXABANK_GESTION_STANDALONE_TEXT, "ES", "kutxabank-fund.pdf")

        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["provider"], "Kutxabank")
        self.assertEqual(result["positions"][0]["instrument_type"], "investment_fund")
        self.assertEqual(result["positions"][0]["description"], "KUTXABANK GESTION ACTIVA RENDIMIENTO FI")
        self.assertEqual(result["positions"][0]["market_value"], "67239.68")
        self.assertEqual(result["positions"][0]["account"], "9444672859")

    def test_parse_unsupported_document_reports_gap(self):
        result = parse_investment_text("Documento non riconosciuto", "IT", "unknown.pdf")

        self.assertEqual(result["status"], "unsupported_format")
        self.assertEqual(result["data_gaps"][0]["code"], "unsupported_investment_statement")

    def test_import_writes_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            italy_dir = root / "documents" / "investimenti" / "italia"
            spain_dir = root / "documents" / "investimenti" / "spagna"
            directa_dir = root / "documents" / "investimenti" / "directa"
            italy_dir.mkdir(parents=True)
            spain_dir.mkdir(parents=True)
            directa_dir.mkdir(parents=True)
            (italy_dir / "amundi.pdf").write_text("placeholder", encoding="utf-8")
            (spain_dir / "a-kutxabank-tax.pdf").write_text("placeholder", encoding="utf-8")
            (spain_dir / "b-kutxabank-fund.pdf").write_text("placeholder", encoding="utf-8")
            (spain_dir / "c-kutxabank-pension.pdf").write_text("placeholder", encoding="utf-8")
            output_path = root / "snapshots" / "investments.snapshot.json"

            with patch(
                "family_office_engine.ingestion.investments._extract_pdf_text",
                side_effect=[
                    AMUNDI_TEXT,
                    KUTXABANK_TEXT,
                    KUTXABANK_GESTION_STANDALONE_TEXT,
                    KUTXABANK_PENSION_TEXT,
                ],
            ):
                result = import_investments(italy_dir, spain_dir, output_path, directa_dir)

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(result["schema_version"], "investments/v1")
            self.assertEqual(written["record_type"], "InvestmentsSnapshot")
            self.assertEqual(written["source"]["directa_path"], str(directa_dir))
            self.assertEqual(len(written["positions"]), 4)
            self.assertEqual(written["documents"][2]["status"], "duplicate_position")
            self.assertEqual(written["documents"][2]["data_gaps"][0]["code"], "duplicate_investment_position")

    def test_import_rejects_missing_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            spain_dir = root / "spain"
            spain_dir.mkdir()

            with self.assertRaisesRegex(InvestmentsImportError, "directory not found"):
                import_investments(root / "missing", spain_dir, root / "snapshot.json")


class _FakeReader:
    def __init__(self):
        self.pages = [_FakePage()]


class _FakePage:
    def get(self, key):
        if key == "/Resources":
            return {"/Font": _FakeRef({"/F": _FakeRef(_FakeFont())})}
        return None

    def get_contents(self):
        data = b"/F 8 Tf\n(" + bytes([0, 1, 0, 2]) + b")Tj\n/F1 8 Tf\n(OK)Tj"
        return _FakeContent(data)


class _FakeContent:
    def __init__(self, data):
        self._data = data

    def get_data(self):
        return self._data


class _FakeFont(dict):
    def __init__(self):
        super().__init__({"/ToUnicode": _FakeRef(_FakeCMap())})


class _FakeCMap:
    def get_data(self):
        return b"""
beginbfrange
<0001> <0002> [<0041> <0042>]
endbfrange
"""


class _FakeRef:
    def __init__(self, value):
        self._value = value

    def get_object(self):
        return self._value


if __name__ == "__main__":
    unittest.main()
