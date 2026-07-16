import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "tax-events/v1"

IMPARTIATI_SOURCE_URL = (
    "https://www.gazzettaufficiale.it/atto/serie_generale/caricaArticolo?"
    "art.codiceRedazionale=23G00222&art.dataPubblicazioneGazzetta=2023-12-28&"
    "art.flagTipoArticolo=0&art.idArticolo=5&art.idGruppo=2&"
    "art.idSottoArticolo=1&art.idSottoArticolo1=10&art.progressivo=0&art.versione=1"
)


class TaxEventsError(ValueError):
    pass


def generate_impatriati_events(
    start_year: int,
    end_year: int,
    taxable_income_share: str,
    regime: str,
    output_path: Path,
) -> dict[str, Any]:
    if end_year < start_year:
        raise TaxEventsError("end_year must be greater than or equal to start_year")

    share = _share(taxable_income_share)
    events = [
        {
            "id": f"impatriati_{year}",
            "type": "tax_regime",
            "jurisdiction": "IT",
            "tax_year": year,
            "regime": regime,
            "taxable_income_share": str(share),
            "status": "planning_assumption_requires_validation",
            "source": {
                "rule_id": "italy.impatriati.current",
                "url": IMPARTIATI_SOURCE_URL,
            },
        }
        for year in range(start_year, end_year + 1)
    ]
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "TaxEventsSnapshot",
        "events": events,
        "metadata": {
            "description": "Regime impatriati represented as annual tax events. No IRPEF calculation is performed.",
            "start_year": start_year,
            "end_year": end_year,
            "regime": regime,
        },
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise TaxEventsError(f"Cannot write tax events snapshot: {output_path}") from exc
    return snapshot


def _share(value: str) -> Decimal:
    try:
        share = Decimal(str(value))
    except InvalidOperation as exc:
        raise TaxEventsError(f"Invalid taxable income share: {value}") from exc
    if share < Decimal("0") or share > Decimal("1"):
        raise TaxEventsError("taxable_income_share must be between 0 and 1")
    return share.quantize(Decimal("0.01"))
