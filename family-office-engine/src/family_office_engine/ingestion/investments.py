import contextlib
import io
import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "investments/v1"


class InvestmentsImportError(ValueError):
    pass


def import_investments(
    italy_dir: Path,
    spain_dir: Path,
    output_path: Path,
    directa_dir: Path | None = None,
) -> dict[str, Any]:
    documents = load_investment_documents(italy_dir, "IT") + load_investment_documents(spain_dir, "ES")
    if directa_dir is not None:
        documents.extend(load_investment_documents(directa_dir, "IT"))
    _deduplicate_document_positions(documents)
    positions = [
        position
        for document in documents
        for position in document.get("positions", [])
    ]
    data_gaps = [
        gap
        for document in documents
        for gap in document.get("data_gaps", [])
    ]

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "InvestmentsSnapshot",
        "source": {
            "type": "classified-investment-documents",
            "italy_path": str(italy_dir),
            "spain_path": str(spain_dir),
            "directa_path": str(directa_dir) if directa_dir is not None else None,
        },
        "extraction_status": "extracted" if positions and not data_gaps else "partial_extracted",
        "documents": documents,
        "positions": positions,
        "data_gaps": data_gaps,
        "notes": "Investment statements parsed deterministically; no valuation is estimated.",
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise InvestmentsImportError(f"Cannot write investments snapshot: {output_path}") from exc
    return snapshot


def load_investment_documents(input_dir: Path, country: str) -> list[dict[str, Any]]:
    if not input_dir.exists():
        raise InvestmentsImportError(f"Investment input directory not found: {input_dir}")
    if not input_dir.is_dir():
        raise InvestmentsImportError(f"Investment input path is not a directory: {input_dir}")

    pdf_paths = sorted(input_dir.glob("*.pdf"))
    documents = [_load_investment_pdf(path, country) for path in pdf_paths]
    return documents


def parse_investment_text(text: str, country: str, filename: str) -> dict[str, Any]:
    normalized = _decode_pdf_unicode_tokens(_normalize_text(text))
    parsers = (
        _parse_directa,
        _parse_consultinvest,
        _parse_etica_balance_certificate,
        _parse_kutxabank_pensiones,
        _parse_amundi,
        _parse_moneyfarm,
        _parse_kutxabank_tax_data,
        _parse_kutxabank_gestion_fund_statement,
    )
    for parser in parsers:
        positions = parser(normalized, country, filename)
        if positions:
            return {
                "status": "extracted",
                "provider": positions[0]["provider"],
                "positions": positions,
                "data_gaps": [],
            }

    return {
        "status": "unsupported_format",
        "provider": _guess_provider(normalized, filename),
        "positions": [],
        "data_gaps": [
            {
                "code": "unsupported_investment_statement",
                "message": "No deterministic parser matched this investment document.",
                "filename": filename,
            }
        ],
    }


def _load_investment_pdf(path: Path, country: str) -> dict[str, Any]:
    try:
        text = _extract_pdf_text(path)
        parsed = parse_investment_text(text, country, path.name)
    except InvestmentsImportError as exc:
        parsed = {
            "status": "pdf_text_error",
            "provider": _guess_provider("", path.name),
            "positions": [],
            "data_gaps": [
                {
                    "code": "pdf_text_error",
                    "message": str(exc),
                    "filename": path.name,
                }
            ],
        }

    parsed.update(
        {
            "filename": path.name,
            "path": str(path),
            "country": country,
        }
    )
    for position in parsed.get("positions", []):
        position["source"] = {
            "filename": path.name,
            "path": str(path),
        }
    return parsed


def _extract_pdf_text(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise InvestmentsImportError("PyPDF2 is required to extract investment PDF text") from exc

    try:
        with contextlib.redirect_stderr(io.StringIO()):
            reader = PdfReader(str(path))
        page_texts: list[str] = []
        extraction_errors: list[Exception] = []
        for page in reader.pages:
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    page_texts.append(page.extract_text() or "")
            except Exception as exc:  # PyPDF2 can fail on custom encoded text streams.
                extraction_errors.append(exc)
                page_texts.append("")
        text = "\n".join(page_texts)
        if text.strip():
            return text
        fallback_text = _extract_pdf_content_stream_text(reader)
        if fallback_text.strip():
            return fallback_text
        if extraction_errors:
            raise extraction_errors[0]
        return text
    except Exception as exc:
        raise InvestmentsImportError(f"Cannot extract text from investment PDF: {path}") from exc


def _extract_pdf_content_stream_text(reader: Any) -> str:
    chunks: list[str] = []
    for page in reader.pages:
        resources = page.get("/Resources") or {}
        font_maps = _page_to_unicode_maps(resources)
        current_font: str | None = None
        try:
            contents = page.get_contents()
            if contents is None:
                continue
            data = contents.get_data()
        except Exception:
            continue
        for token in re.finditer(rb"/([A-Za-z][A-Za-z0-9]*)\s+[0-9.]+\s+Tf|\((.*?)\)\s*Tj", data, flags=re.DOTALL):
            if token.group(1):
                current_font = "/" + token.group(1).decode("latin1")
                continue
            raw = _decode_pdf_literal_bytes(token.group(2) or b"")
            chunks.append(_decode_pdf_text_bytes(raw, font_maps.get(current_font or "")))
    return "\n".join(chunk for chunk in chunks if chunk)


def _page_to_unicode_maps(resources: Any) -> dict[str, dict[int, str]]:
    fonts = resources.get("/Font") if hasattr(resources, "get") else None
    if fonts is None:
        return {}
    try:
        font_objects = fonts.get_object()
    except Exception:
        return {}
    maps: dict[str, dict[int, str]] = {}
    for name, font_ref in font_objects.items():
        try:
            font = font_ref.get_object()
            to_unicode = font.get("/ToUnicode")
            if to_unicode:
                maps[str(name)] = _parse_to_unicode_cmap(to_unicode.get_object().get_data())
        except Exception:
            continue
    return maps


def _parse_to_unicode_cmap(data: bytes) -> dict[int, str]:
    text = data.decode("latin1", errors="ignore")
    mapping: dict[int, str] = {}
    for source, target in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", _bfchar_sections(text)):
        decoded = _decode_hex_unicode(target)
        if decoded is not None:
            mapping[int(source, 16)] = decoded
    for start, _end, targets in re.findall(
        r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]",
        _bfrange_sections(text),
        flags=re.DOTALL,
    ):
        source = int(start, 16)
        for offset, target in enumerate(re.findall(r"<([0-9A-Fa-f]+)>", targets)):
            decoded = _decode_hex_unicode(target)
            if decoded is not None:
                mapping[source + offset] = decoded
    return mapping


def _bfchar_sections(text: str) -> str:
    return "\n".join(re.findall(r"beginbfchar(.*?)endbfchar", text, flags=re.DOTALL))


def _bfrange_sections(text: str) -> str:
    return "\n".join(re.findall(r"beginbfrange(.*?)endbfrange", text, flags=re.DOTALL))


def _decode_hex_unicode(value: str) -> str | None:
    try:
        raw = bytes.fromhex(value)
    except ValueError:
        return None
    encoding = "utf-16-be" if len(raw) % 2 == 0 else "latin1"
    return raw.decode(encoding, errors="ignore")


def _decode_pdf_literal_bytes(value: bytes) -> bytes:
    output = bytearray()
    index = 0
    escapes = {
        ord("n"): ord("\n"),
        ord("r"): ord("\r"),
        ord("t"): ord("\t"),
        ord("b"): ord("\b"),
        ord("f"): ord("\f"),
        ord("("): ord("("),
        ord(")"): ord(")"),
        ord("\\"): ord("\\"),
    }
    while index < len(value):
        current = value[index]
        if current == ord("\\") and index + 1 < len(value):
            next_byte = value[index + 1]
            if next_byte in escapes:
                output.append(escapes[next_byte])
                index += 2
                continue
        output.append(current)
        index += 1
    return bytes(output)


def _decode_pdf_text_bytes(value: bytes, to_unicode: dict[int, str] | None) -> str:
    if to_unicode:
        chars: list[str] = []
        for index in range(0, len(value) - 1, 2):
            chars.append(to_unicode.get(int.from_bytes(value[index:index + 2], "big"), ""))
        return "".join(chars)
    return value.decode("latin1", errors="ignore")


def _parse_consultinvest(text: str, country: str, filename: str) -> list[dict[str, Any]]:
    if "Consultinvest" not in text or "Patrimonio finale" not in text:
        return []

    statement_date = _search_date(text, r"Prospetto riassuntivo al\s*(\d{2}/\d{2}/\d{4})")
    if statement_date is None:
        statement_date = _search_date(text, r"\d{2}/\d{2}/\d{4}\s*-\s*(\d{2}/\d{2}/\d{4})")
    final_value = _search_last_amount(text, r"Patrimonio finale\s+(-?\d[\d.]*,\d{2})")
    if final_value is None:
        return []
    account = _search_value(text, r"Mandato:\s*(?:\n|\s)+([0-9/]+)-CONSULENZA FINANZIARIA")

    position = {
        "provider": "Consultinvest",
        "country": country,
        "instrument_type": "managed_portfolio",
        "description": "Consulenza finanziaria",
        "statement_date": statement_date,
        "market_value": _normalize_decimal(final_value),
        "currency": "EUR",
        "confidence": "parsed_from_statement",
    }
    if account is not None:
        position["account"] = _normalize_account_id(account)
    return [position]


def _parse_directa(text: str, country: str, filename: str) -> list[dict[str, Any]]:
    if "DIRECTA" not in text.upper() or "TOTALE LIQUIDITA" not in text.upper():
        return []

    statement_date = _search_date(text, r"Operazione\s*(\d{2}/\d{2}/\d{4})")
    liquidity = _search_value(text, r"TOTALE LIQUIDITA['’]?:\s*(-?\d[\d.]*,\d{2})")
    securities = _search_value(text, r"TOTALE TITOLI EURO\s+(-?\d[\d.]*,\d{2})")
    if liquidity is None:
        return []
    account = _search_value(text, r"Conto n\.?\s*([A-Z][0-9]+)")

    positions = [
        {
            "provider": "Directa",
            "country": country,
            "instrument_type": "cash_account",
            "description": "Situazione patrimoniale liquidita",
            "statement_date": statement_date,
            "market_value": _normalize_decimal(liquidity),
            "currency": "EUR",
            "confidence": "parsed_from_statement",
        }
    ]
    if account is not None:
        positions[0]["account"] = account
    if securities is not None and _normalize_decimal(securities) != "0.00":
        security_position = {
            "provider": "Directa",
            "country": country,
            "instrument_type": "brokerage_portfolio",
            "description": "Situazione patrimoniale titoli",
            "statement_date": statement_date,
            "market_value": _normalize_decimal(securities),
            "currency": "EUR",
            "confidence": "parsed_from_statement",
        }
        if account is not None:
            security_position["account"] = account
        positions.append(security_position)
    return positions


def _parse_etica_balance_certificate(text: str, country: str, filename: str) -> list[dict[str, Any]]:
    if "Etica" not in text and "ETICA" not in text:
        return []
    if "Attestazione saldo" not in text or "Controvalore del suo investimento" not in text:
        return []

    statement_date = _search_date(text, r"saldo al\s*(\d{2}/\d{2}/\d{4})")
    account = _search_value(text, r"Codice rapporto:\s*([0-9]+)")
    positions: list[dict[str, Any]] = []
    for fund_name, value in re.findall(
        r"(ETICA [A-Z0-9 .'\-]+?)\s+[\d.,]+\s+€?\s*[\d.,]+\s+€?\s*(\d[\d.]*,\d{2})",
        text,
        flags=re.IGNORECASE,
    ):
        position = {
            "provider": "Etica",
            "country": country,
            "instrument_type": "investment_fund",
            "description": re.sub(r"\s+", " ", fund_name).strip(),
            "statement_date": statement_date,
            "market_value": _normalize_decimal(value),
            "currency": "EUR",
            "confidence": "parsed_from_balance_certificate",
        }
        if account is not None:
            position["account"] = account
        positions.append(position)
    return positions


def _parse_amundi(text: str, country: str, filename: str) -> list[dict[str, Any]]:
    if "Amundi" not in text or "Posizione individuale al" not in text:
        return []

    date = _search_date(text, r"Posizione individuale al\s*(\d{2}/\d{2}/\d{4})")
    section_match = re.search(
        r"Quanto hai finora maturato.*?Hai versato",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not section_match:
        return []
    amounts = re.findall(r"(\d[\d.]*,\d{2})", section_match.group(0))
    if not amounts:
        return []

    return [
        {
            "provider": "Amundi",
            "country": country,
            "instrument_type": "pension_fund",
            "description": "SecondaPensione position",
            "statement_date": date,
            "market_value": _normalize_decimal(amounts[-1]),
            "currency": "EUR",
            "confidence": "parsed_from_statement",
        }
    ]


def _parse_moneyfarm(text: str, country: str, filename: str) -> list[dict[str, Any]]:
    if "Moneyfarm" not in text and "MFM Investment" not in text:
        return []

    section_match = re.search(
        r"TOTALE PATRIMONIO FINALE.*?RISULTATO DI GESTIONE",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not section_match:
        return []
    amounts = re.findall(r"(-?\d[\d.]*,\d{2})", section_match.group(0))
    if not amounts:
        return []

    statement_date = _search_date(text, r"Data Rendiconto:\s*(\d{2}/\d{2}/\d{4})")
    if statement_date is None:
        statement_date = _search_compact_date(text)

    return [
        {
            "provider": "Moneyfarm",
            "country": country,
            "instrument_type": "managed_portfolio",
            "description": "Gestione patrimoniale",
            "statement_date": statement_date,
            "market_value": _normalize_decimal(amounts[-1]),
            "currency": "EUR",
            "confidence": "parsed_from_statement",
        }
    ]


def _parse_kutxabank_pensiones(text: str, country: str, filename: str) -> list[dict[str, Any]]:
    if "KUTXABANK PENSIONES" not in text or "SALDO AL FINAL DEL PERIODO" not in text:
        return []

    final_balance = re.search(
        r"SALDO AL FINAL DEL PERIODO\s+((?:\d+\s+){1,4}\d{2})\s+EUR",
        text,
        flags=re.IGNORECASE,
    )
    if not final_balance:
        return []

    full_plan_name = _search_value(text, r"KUTXABANK\s+([A-Z0-9\s]+?)\s+F\.P\.")
    if full_plan_name is not None:
        plan_name = f"KB {full_plan_name} PP"
    else:
        plan_name = _search_value(text, r"(KB\s+[A-Z0-9\s]+?\s+PP)")
    if plan_name is None:
        plan_name = "Kutxabank pension plan"

    return [
        {
            "provider": "Kutxabank",
            "country": country,
            "instrument_type": "pension_plan",
            "description": re.sub(r"\s+", " ", plan_name).strip(),
            "statement_date": _kutxabank_pension_statement_date(text),
            "market_value": _normalize_spaced_decimal(final_balance.group(1)),
            "currency": "EUR",
            "confidence": "parsed_from_pension_statement",
        }
    ]


def _parse_kutxabank_tax_data(text: str, country: str, filename: str) -> list[dict[str, Any]]:
    if "Kutxabank" not in text or "Saldo a31-12" not in text:
        return []

    positions: list[dict[str, Any]] = []
    statement_date = _search_year_end_date(text)
    account_section = re.search(
        r"CUENTAS ALAVISTA.*?Guztira\s*=Total\s*([\d.]+,\d{2})\s*([\d.]+,\d{2})",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if account_section:
        positions.append(
            {
                "provider": "Kutxabank",
                "country": country,
                "instrument_type": "cash_account",
                "description": "Saldo cuenta a 31-12",
                "statement_date": statement_date,
                "market_value": _normalize_decimal(account_section.group(2)),
                "currency": "EUR",
                "confidence": "parsed_from_tax_data",
            }
        )
    fund_section = re.search(
        r"FONDOS DE\s*INVERSI\S+\s+GESTIONADOS POR\s*KUTXABANK GESTI\S+"
        r".*?([A-Z][A-Z\s]+)\s+(ES[0-9A-Z]+)\s+(\S+)\s+\d+\s+"
        r"[\d.]+,\d{2,6}\s+[\d.]+,\d{2,6}\s+([\d.]+,\d{2})",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fund_section:
        fund_name = re.sub(r"\s+", " ", fund_section.group(1)).strip()
        isin = fund_section.group(2).strip()
        account = _normalize_account_id(fund_section.group(3))
        positions.append(
            {
                "provider": "Kutxabank",
                "country": country,
                "instrument_type": "investment_fund",
                "description": f"{fund_name} ({isin})",
                "statement_date": statement_date,
                "market_value": _normalize_decimal(fund_section.group(4)),
                "currency": "EUR",
                "account": account,
                "confidence": "parsed_from_tax_data",
            }
        )
    return positions


def _parse_kutxabank_gestion_fund_statement(text: str, country: str, filename: str) -> list[dict[str, Any]]:
    normalized_heading = text.upper().replace("Ó", "O")
    if "KUTXABANK GESTION" not in normalized_heading or "DATOS PARA SU DECLARACION FISCAL" not in normalized_heading:
        return []

    fund_name = _search_value(text, r"(KUTXABANK\s+GESTION\s+[A-Z\s]+?\s+FI)")
    fund_row = re.search(
        r"\b(\d{9,10})\s+21025\s+\d+\s+\d+\s+((?:\d+\s+){2}\d{2})\s+\d+\s+\d+",
        text,
        flags=re.IGNORECASE,
    )
    if fund_name is None or not fund_row:
        return []

    return [
        {
            "provider": "Kutxabank",
            "country": country,
            "instrument_type": "investment_fund",
            "description": re.sub(r"\s+", " ", fund_name).strip(),
            "statement_date": "2025-12-31",
            "market_value": _normalize_spaced_decimal(fund_row.group(2)),
            "currency": "EUR",
            "account": _normalize_account_id(fund_row.group(1)),
            "confidence": "parsed_from_fund_tax_statement",
        }
    ]


def _deduplicate_document_positions(documents: list[dict[str, Any]]) -> None:
    seen: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for document in documents:
        unique_positions = []
        for position in document.get("positions", []):
            key = _position_dedupe_key(position)
            if key is None or key not in seen:
                unique_positions.append(position)
                if key is not None:
                    seen[key] = position
                continue

            document.setdefault("data_gaps", []).append(
                {
                    "code": "duplicate_investment_position",
                    "filename": document.get("filename", ""),
                    "message": "Position already represented by another source document.",
                    "duplicate_of": seen[key].get("source", {}).get("filename", ""),
                }
            )
        document["positions"] = unique_positions
        if not unique_positions and any(
            gap.get("code") == "duplicate_investment_position"
            for gap in document.get("data_gaps", [])
            if isinstance(gap, dict)
        ):
            document["status"] = "duplicate_position"


def _position_dedupe_key(position: dict[str, Any]) -> tuple[str, str, str, str, str] | None:
    account = position.get("account")
    if not account:
        return None
    return (
        str(position.get("provider", "")),
        str(position.get("instrument_type", "")),
        str(account),
        str(position.get("statement_date", "")),
        str(position.get("market_value", "")),
    )


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\xa0", " ")).replace("Ó", "O")


def _decode_pdf_unicode_tokens(text: str) -> str:
    text = re.sub(
        r"/UNIC([0-9A-Fa-f]{4})",
        lambda match: chr(int(match.group(1), 16)),
        text,
    )
    text = re.sub(r"/L([A-Z])\d{6}", lambda match: match.group(1), text)
    text = re.sub(r"/ND(\d{2})\d{4}", lambda match: str(int(match.group(1))), text)
    text = re.sub(r"/SP\d{6}", " ", text)
    text = re.sub(r"/SL760000", "/", text)
    return text


def _search_date(text: str, pattern: str) -> str | None:
    value = _search_value(text, pattern)
    if value is None:
        return None
    day, month, year = value.split("/")
    return f"{year}-{month}-{day}"


def _search_compact_date(text: str) -> str | None:
    match = re.search(r"Data Rendiconto:\s*/(\d{4})/(\d{2})(\d{2})", text, flags=re.IGNORECASE)
    if not match:
        return None
    year, month, day = match.groups()
    return f"{year}-{month}-{day}"


def _search_year_end_date(text: str) -> str | None:
    year = _search_value(text, r"Ejercicio:\s*(\d{4})")
    if year is None:
        return None
    return f"{year}-12-31"


def _kutxabank_pension_statement_date(text: str) -> str | None:
    if re.search(r"31\s+12\s+\d{0,2}25", text):
        return "2025-12-31"
    return _search_year_end_date(text)


def _search_value(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _search_last_amount(text: str, pattern: str) -> str | None:
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    if not matches:
        return None
    return matches[-1]


def _normalize_decimal(value: str) -> str:
    return value.replace(".", "").replace(",", ".")


def _normalize_spaced_decimal(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) < 3:
        raise InvestmentsImportError(f"Invalid spaced decimal value: {value}")
    return f"{int(digits[:-2])}.{digits[-2:]}"


def _normalize_account_id(value: str) -> str:
    return re.sub(r"\D", "", value)


def _guess_provider(text: str, filename: str) -> str:
    haystack = f"{filename}\n{text}".lower()
    if "amundi" in haystack or "secondapensione" in haystack:
        return "Amundi"
    if "moneyfarm" in haystack or "mfm investment" in haystack:
        return "Moneyfarm"
    if "consultinvest" in haystack:
        return "Consultinvest"
    if "kutxabank" in haystack:
        return "Kutxabank"
    if "etica" in haystack:
        return "Etica"
    return "unknown"
