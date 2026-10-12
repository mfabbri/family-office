"""Deterministic import and review primitives for local bank expense exports."""

import csv
import hashlib
import json
import re
import unicodedata
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from family_office_engine.ingestion.fonte import _cell_value, _column_index, _shared_strings

SCHEMA_VERSION = "bank-expense-transactions/v1"
REVIEW_SCHEMA_VERSION = "bank-expense-review/v1"
GROUPED_REVIEW_SCHEMA_VERSION = "bank-expense-review/v2"
RULES_SCHEMA_VERSION = "bank-expense-review-rules/v1"
SUPPORTED_SUFFIXES = {".csv", ".xlsx"}


class BankExpensesError(ValueError):
    pass


def import_bank_expense_exports(input_dir: Path, output_path: Path, rules_path: Path | None = None) -> dict[str, Any]:
    if not input_dir.exists() or not input_dir.is_dir():
        raise BankExpensesError(f"Bank expense export directory not found: {input_dir}")
    transactions: list[dict[str, Any]] = []
    data_gaps: list[dict[str, Any]] = []
    documents: list[str] = []
    for path in sorted(input_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            data_gaps.append({"code": "unsupported_bank_expense_file", "filename": path.name, "message": "Only CSV and XLSX exports are supported."})
            continue
        documents.append(path.name)
        try:
            rows = _read_rows(path)
            normalized_rows, skipped_rows = _normalize_rows(rows, path)
            transactions.extend(normalized_rows)
            if skipped_rows:
                data_gaps.append({"code": "incomplete_bank_expense_rows_skipped", "filename": path.name, "count": skipped_rows, "message": "Rows without both date and description were skipped as non-transaction or incomplete rows."})
        except BankExpensesError as exc:
            data_gaps.append({"code": "bank_expense_export_error", "filename": path.name, "message": str(exc)})
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    duplicate_count = 0
    for transaction in transactions:
        if transaction["transaction_id"] in seen:
            duplicate_count += 1
            continue
        seen.add(transaction["transaction_id"])
        unique.append(transaction)
    if rules_path is not None and rules_path.exists():
        rules = _load_rules(rules_path)
        for transaction in unique:
            rule = rules.get("rules_by_merchant", {}).get(transaction["merchant_fingerprint"])
            if rule:
                transaction["category_proposal"] = rule["category"]
                transaction["category_provenance"] = rule["provenance"]
                transaction["rule_applied"] = rule["rule_id"]
    if duplicate_count:
        data_gaps.append({"code": "duplicate_transactions_removed", "count": duplicate_count, "message": "Equivalent transaction rows were deduplicated by deterministic fingerprint."})
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "BankExpenseTransactions",
        "source": {"type": "local-bank-export", "input_dir": str(input_dir), "documents": documents},
        "status": "complete" if unique and not data_gaps else "partial" if unique else "blocked_missing_inputs",
        "transactions": unique,
        "summary": {"transaction_count": len(unique), "expense_count": sum(1 for item in unique if item["include_in_expenses"]), "document_count": len(documents)},
        "data_gaps": data_gaps,
        "notes": "Amounts, dates and aggregation are deterministic. Category proposals and local rules require human review.",
    }
    _write_json(output_path, snapshot)
    return snapshot


def review_bank_expenses_grouped(
    input_path: Path,
    output_path: Path,
    lifecycle_input_path: Path,
    household_id: str,
    as_of_date: str,
    decisions: dict[str, str],
    rules_path: Path | None = None,
) -> dict[str, Any]:
    """Review deterministic merchant/category groups while preserving every raw row."""
    snapshot = _load_snapshot(input_path, SCHEMA_VERSION, "bank expense transactions")
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for transaction in snapshot.get("transactions", []):
        if not transaction.get("include_in_expenses"):
            continue
        item = dict(transaction)
        normalized = str(item.get("merchant_normalized") or _normalize_merchant(str(item.get("description") or "unknown")))
        item["merchant_normalized"] = normalized
        item["merchant_fingerprint"] = str(item.get("merchant_fingerprint") or _merchant_fingerprint(normalized))
        key = (item["merchant_fingerprint"], str(item.get("category_proposal") or "unknown"))
        groups.setdefault(key, []).append(item)
    reviewed: list[dict[str, Any]] = []
    group_records: list[dict[str, Any]] = []
    gaps = list(snapshot.get("data_gaps", []))
    for index, ((fingerprint, proposal), items) in enumerate(sorted(groups.items(), key=lambda pair: _group_sort_key(pair[0], pair[1])), start=1):
        group_id = f"merchant_group_{index:04d}"
        total = sum((abs(Decimal(str(item["amount"]))) for item in items), Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        dates = sorted(str(item["date"]) for item in items)
        reason_codes = []
        if proposal == "unknown":
            reason_codes.append("unknown_category")
        if len(items) == 1:
            reason_codes.append("single_transaction")
        confidence = "high" if proposal != "unknown" and len(items) >= 2 else "review_required"
        decision = decisions.get(group_id)
        approved = decision if decision not in {None, "", "unknown", "skip"} else None
        priority = "high_homogeneity" if proposal != "unknown" and len(items) >= 2 else "exception"
        group = {
            "group_id": group_id,
            "merchant_fingerprint": fingerprint,
            "merchant_normalized": items[0]["merchant_normalized"],
            "category_proposal": proposal,
            "transaction_count": len(items),
            "total": str(total),
            "period": {"from": dates[0], "to": dates[-1]},
            "sample": [{"transaction_id": item["transaction_id"], "date": item["date"], "description": item["description"], "amount": item["amount"]} for item in items[:3]],
            "exception_codes": reason_codes,
            "review_priority": priority,
            "confidence": confidence,
            "provenance": "deterministic:merchant-normalizer-v1;category-proposal-local-heuristic-v1",
            "review_status": "approved" if approved else "unresolved",
            "approved_category": approved,
        }
        group_records.append(group)
        if not approved:
            gaps.append({"code": "unreviewed_expense_group", "group_id": group_id, "message": "Expense merchant group requires human review."})
        for item in items:
            reviewed_item = dict(item)
            reviewed_item["group_id"] = group_id
            reviewed_item["approved_category"] = approved
            reviewed_item["review_status"] = group["review_status"]
            reviewed.append(reviewed_item)
        if approved and approved != proposal and rules_path is not None:
            _upsert_rule(rules_path, fingerprint, approved, group["provenance"])
    aggregated_unknown_transactions = sum(
        int(group["transaction_count"])
        for group in group_records
        if group["category_proposal"] == "unknown" and group["approved_category"] == "other"
    )
    if aggregated_unknown_transactions:
        gaps.append(
            {
                "code": "unknown_expenses_aggregated",
                "count": aggregated_unknown_transactions,
                "message": "Unclassified bank expenses were retained as one other lifecycle total; category detail was not inferred.",
            }
        )
    reviewed_snapshot = {
        "schema_version": GROUPED_REVIEW_SCHEMA_VERSION,
        "record_type": "BankExpenseGroupedReview",
        "source": {"type": "reviewed-bank-expense-groups", "input_path": str(input_path)},
        "status": "complete" if reviewed and not gaps else "partial" if reviewed else "blocked_missing_inputs",
        "groups": group_records,
        "transactions": reviewed,
        "summary": {"group_count": len(group_records), "transaction_count": len(reviewed), "approved_group_count": sum(1 for group in group_records if group["review_status"] == "approved"), "unresolved_group_count": sum(1 for group in group_records if group["review_status"] != "approved")},
        "data_gaps": gaps,
        "notes": "Totals and grouping are deterministic; approval remains human and raw descriptions are preserved.",
    }
    _write_json(output_path, reviewed_snapshot)
    lifecycle = _build_lifecycle_plan(reviewed_snapshot, household_id, as_of_date)
    _write_json(lifecycle_input_path, lifecycle)
    return {"review": reviewed_snapshot, "lifecycle": lifecycle}


def _group_sort_key(key: tuple[str, str], items: list[dict[str, Any]]) -> tuple[int, str, str]:
    fingerprint, proposal = key
    priority = 0 if proposal != "unknown" and len(items) >= 2 else 1
    return priority, str(items[0]["merchant_normalized"]), fingerprint


def _normalize_merchant(description: str) -> str:
    text = _fold(description)
    text = re.sub(r"\b\d{1,4}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _merchant_fingerprint(normalized: str) -> str:
    return hashlib.sha256(f"merchant-normalizer-v1|{normalized}".encode("utf-8")).hexdigest()[:20]


def _load_rules(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BankExpensesError(f"Invalid bank expense rules: {path}") from exc
    if data.get("schema_version") != RULES_SCHEMA_VERSION:
        raise BankExpensesError(f"Unsupported bank expense rules schema: {data.get('schema_version')}")
    return data


def _upsert_rule(path: Path, fingerprint: str, category: str, provenance: str) -> None:
    data = _load_rules(path) if path.exists() else {"schema_version": RULES_SCHEMA_VERSION, "record_type": "BankExpenseReviewRules", "rules_by_merchant": {}}
    rules = data.setdefault("rules_by_merchant", {})
    rule_id = f"merchant_rule_{fingerprint}"
    rules[fingerprint] = {"rule_id": rule_id, "merchant_fingerprint": fingerprint, "category": category, "priority": 100, "provenance": f"human_review:{provenance}"}
    _write_json(path, data)


def review_bank_expenses(
    input_path: Path,
    output_path: Path,
    lifecycle_input_path: Path,
    household_id: str,
    as_of_date: str,
    decisions: dict[str, str],
) -> dict[str, Any]:
    snapshot = _load_snapshot(input_path, SCHEMA_VERSION, "bank expense transactions")
    reviewed: list[dict[str, Any]] = []
    gaps = list(snapshot.get("data_gaps", []))
    for transaction in snapshot.get("transactions", []):
        item = dict(transaction)
        proposal = str(item.get("category_proposal") or "unknown")
        decision = decisions.get(proposal, "unknown")
        item["approved_category"] = decision if decision not in {"", "unknown", "skip"} else None
        item["review_status"] = "approved" if item["approved_category"] else "unresolved"
        if item["include_in_expenses"] and not item["approved_category"]:
            gaps.append({"code": "unreviewed_expense_category", "transaction_id": item["transaction_id"], "message": "Expense category requires human review before lifecycle aggregation."})
        reviewed.append(item)
    reviewed_snapshot = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "record_type": "BankExpenseReview",
        "source": {"type": "reviewed-bank-expense-transactions", "input_path": str(input_path)},
        "status": "complete" if reviewed and not gaps else "partial" if reviewed else "blocked_missing_inputs",
        "transactions": reviewed,
        "summary": {"transaction_count": len(reviewed), "approved_count": sum(1 for item in reviewed if item["review_status"] == "approved"), "unresolved_count": sum(1 for item in reviewed if item["review_status"] != "approved")},
        "data_gaps": gaps,
        "notes": "Categories are approved by the operator; no local model output is authoritative or persisted.",
    }
    _write_json(output_path, reviewed_snapshot)
    lifecycle = _build_lifecycle_plan(reviewed_snapshot, household_id, as_of_date)
    _write_json(lifecycle_input_path, lifecycle)
    return {"review": reviewed_snapshot, "lifecycle": lifecycle}


def _build_lifecycle_plan(snapshot: dict[str, Any], household_id: str, as_of_date: str) -> dict[str, Any]:
    totals: dict[tuple[str, int], Decimal] = {}
    for item in snapshot.get("transactions", []):
        if not item.get("include_in_expenses") or not item.get("approved_category"):
            continue
        year = int(item["date"][:4])
        key = (str(item["approved_category"]), year)
        totals[key] = totals.get(key, Decimal("0")) + abs(Decimal(str(item["amount"])))
    entries = []
    for index, ((category, year), amount) in enumerate(sorted(totals.items()), start=1):
        entries.append({"entry_id": f"bank_expense_{index}", "category": category, "phase": "all_phases", "owner_type": "household", "frequency": "annual", "currency": "EUR", "amount": str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), "annual_inflation_rate": "0.00", "start_year": year, "end_year": year, "provenance": "bank_expense_review:v1"})
    gaps = list(snapshot.get("data_gaps", []))
    if entries:
        gaps.append({"code": "historical_profile_only", "message": "Bank export amounts describe observed years only; no future spending assumption was created."})
    return {"schema_version": "lifecycle-expenses/v1", "record_type": "LifecycleExpensePlan", "household_id": household_id, "as_of_date": as_of_date, "expense_entries": entries, "data_gaps": gaps}


def _read_rows(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".xlsx":
        try:
            sheets = _read_all_xlsx_sheets(path)
        except Exception as exc:
            raise BankExpensesError(f"Invalid XLSX export: {path.name}") from exc
        if not sheets:
            raise BankExpensesError(f"XLSX export contains no rows: {path.name}")
        result: list[dict[str, str]] = []
        for rows in sheets:
            if not rows:
                continue
            headers = [_header(value) for value in rows[0]]
            result.extend(
                dict(zip(headers, row + [""] * (len(headers) - len(row))))
                for row in rows[1:]
                if any(value.strip() for value in row)
            )
        return result
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise BankExpensesError(f"Cannot read export: {path.name}") from exc
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(text.splitlines(), dialect=dialect))
    return [{_header(key): (value or "").strip() for key, value in row.items()} for row in rows]


def _read_all_xlsx_sheets(path: Path) -> list[list[list[str]]]:
    try:
        with zipfile.ZipFile(path) as workbook:
            shared_strings = _shared_strings(workbook)
            sheet_names = sorted(name for name in workbook.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
            if not sheet_names:
                raise BankExpensesError(f"XLSX workbook contains no worksheets: {path.name}")
            sheets: list[list[list[str]]] = []
            for sheet_name in sheet_names:
                root = ElementTree.fromstring(workbook.read(sheet_name))
                rows: list[list[str]] = []
                for row in root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheetData/{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
                    values: list[str] = []
                    for cell in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                        column_index = _column_index(cell.attrib.get("r", ""))
                        while len(values) < column_index:
                            values.append("")
                        values.append(_cell_value(cell, shared_strings))
                    rows.append(values)
                if rows:
                    sheets.append(rows)
            return sheets
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise BankExpensesError(f"Invalid XLSX export: {path.name}") from exc


def _normalize_rows(rows: list[dict[str, str]], path: Path) -> tuple[list[dict[str, Any]], int]:
    if not rows:
        raise BankExpensesError(f"Export contains no transaction rows: {path.name}")
    result = []
    skipped_rows = 0
    for line_number, row in enumerate(rows, start=2):
        date_text = _first(row, "date", "data", "transaction_date", "data_operazione", "data_contabile", "data_valuta")
        description = _first(row, "description", "descrizione", "descrizione_operazione", "merchant", "causale", "causale_abi", "details")
        if _fold(date_text) in {"data", "date"} and _fold(description) in {"causale", "descrizione", "description", "merchant"}:
            continue
        if any(_fold(value) in {"dare", "avere", "importo", "amount", "debit", "credit"} for value in row.values()):
            continue
        if not date_text or not description:
            skipped_rows += 1
            continue
        amount_text = _first(row, "amount", "importo", "value", "valore")
        debit = _first(row, "debit", "debit_amount", "uscite", "dare")
        credit = _first(row, "credit", "credit_amount", "entrate", "avere")
        if not amount_text and not debit and not credit:
            skipped_rows += 1
            continue
        amount = _parse_amount(amount_text) if amount_text else None
        if amount is None and debit:
            amount = -abs(_parse_amount(debit))
        if amount is None and credit:
            amount = abs(_parse_amount(credit))
        if amount is None:
            raise BankExpensesError(f"Missing amount at row {line_number} in {path.name}")
        parsed_date = _parse_date(date_text)
        category, include = _propose_category(description, amount)
        merchant_normalized = _normalize_merchant(description)
        merchant_fingerprint = _merchant_fingerprint(merchant_normalized)
        fingerprint = hashlib.sha256(f"{path.name}|{parsed_date}|{description.strip().lower()}|{amount}|{_first(row, 'currency', 'valuta') or 'EUR'}".encode("utf-8")).hexdigest()[:20]
        result.append({"transaction_id": f"{path.stem}:{fingerprint}", "date": parsed_date, "description": description.strip(), "merchant_normalized": merchant_normalized, "merchant_fingerprint": merchant_fingerprint, "amount": str(amount.quantize(Decimal("0.01"))), "currency": _first(row, "currency", "valuta") or "EUR", "category_proposal": category, "category_provenance": "deterministic:category-proposal-local-heuristic-v1", "include_in_expenses": include, "source": {"filename": path.name, "row": line_number}})
    return result, skipped_rows


def _propose_category(description: str, amount: Decimal) -> tuple[str, bool]:
    text = " ".join(re.sub(r"[^a-z0-9]+", " ", _fold(description)).split())
    if amount >= 0:
        if any(token in text for token in ("stipendio", "salary", "paga")):
            return "income", False
        return "non_expense_credit", False
    non_expense_tokens = (
        "satispay app top up",
        "ricarica satispay",
        "satispay europe",
        "satispay wallet",
        "spese tenuta conto",
        "spese gestione carta",
        "cartabcc addebito e c mensile",
        "carta del credito cooperativo addebito e c mensile",
        "carta di credito cooperativo addebito e c mensile",
        "carta movimento",
        "commissioni",
        "comm messa disposizione fondi",
        "recupero spese invio e c",
        "spese invio e c",
        "ritenuta fiscale",
        "ritenute alla fonte",
        "interessi e competenze",
        "imposta di bollo",
        "addebito bolli",
        "rec bollo",
        "imposte e tasse",
        "delega f24",
        "fondi comuni",
        "sottoscrizione fondi",
        "sottosc fondi",
        "sottosc",
        "sicav",
        "etica sgr",
        "pac etica",
        "coinbase",
        "american express italia srl",
        "decurtazione mutuo",
    )
    if any(token in text for token in non_expense_tokens):
        return "financial_non_expense", False
    explicit_atm_withdrawal = any(
        token in text
        for token in (
            "prelievo atm",
            "prelevamento atm",
            "prelievo bancomat",
            "prelevamento bancomat",
            "prel bancomat",
            "bancomat ns",
            "nostro bancomat",
        )
    )
    card_payment_markers = (
        "pagamento pos",
        "operazione pos",
        "pagamento pagobancomat",
        "operazione pagobancomat",
        "spesa pagobancomat",
        "pagamenti pagobancomat",
        "pagament maestro",
        "maestro vpay",
        "payment pos",
    )
    looks_like_card_payment = any(marker in text for marker in card_payment_markers)
    if explicit_atm_withdrawal and not looks_like_card_payment:
        return "cash_withdrawal", True
    rules = {
        "transfer": ("bonifico", "giroconto", "trasferimento", "ricarica conto"),
        "refund": ("rimborso", "storno", "restituzione"),
        "housing": ("affitto", "canone", "immobiliare"),
        "food": ("supermercato", "esselunga", "conad", "coop", "carrefour", "lidl", "alimentari", "pescheria", "ristorante", "pizzeria", "rist pizz", "sushi", "toki", "chiosco", "buffet", "vecchia malga", "bar", "caffe", "gelateria", "pasticceria", "panificio", "forno", "trattoria", "osteria", "taverna", "mensa", "refezione", "pizza", "kebab", "rosticceria", "macelleria"),
        "utilities": ("enel", "hera", "utenza", "gas", "acqua", "energia", "telefono", "internet", "telecomitalia", "tim", "vodafone", "fastweb"),
        "transport": ("benzina", "carburante", "agip", "lul ticket machine", "trenitalia", "telepass", "autostrada", "parcheggio", "taxi", "psa renting", "officina", "carrozzeria", "gommista", "lavaggio auto"),
        "health": ("farmacia", "medico", "sanitario", "sanitaria", "ausl", "ospedale", "veterinario", "dentista", "ottica", "laboratorio analisi"),
        "insurance": ("assicurazione", "polizza"),
        "leisure": ("cinema", "cinedream", "hotel", "vacanza", "viaggio", "chalet dello sport", "palestra", "piscina", "teatro", "museo", "sport"),
    }
    for category, tokens in rules.items():
        if any(re.search(rf"\b{re.escape(token)}\b", text) for token in tokens):
            return category, category not in {"transfer", "refund"}
    return "unknown", True


def _header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _fold(str(value))).strip("_")


def _fold(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(char))


def _first(row: dict[str, str], *names: str) -> str:
    for name in names:
        if row.get(name, "").strip():
            return row[name].strip()
    return ""


def _parse_date(value: str) -> str:
    value = value.strip()
    if re.fullmatch(r"\d+(?:\.0+)?", value):
        try:
            serial = int(float(value))
            if 1 <= serial <= 100000:
                return (date(1899, 12, 30) + timedelta(days=serial)).isoformat()
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise BankExpensesError(f"Invalid transaction date: {value}")


def _parse_amount(value: str) -> Decimal:
    text = value.strip().replace("€", "").replace("EUR", "").replace(" ", "")
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise BankExpensesError(f"Invalid transaction amount: {value}") from exc
    return -amount if negative else amount


def _load_snapshot(path: Path, schema: str, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise BankExpensesError(f"Invalid or missing {label}: {path}") from exc
    if data.get("schema_version") != schema:
        raise BankExpensesError(f"Unsupported {label} schema: {data.get('schema_version')}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise BankExpensesError(f"Cannot write bank expenses output: {path}") from exc
