import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "net-worth/v1"


class NetWorthError(ValueError):
    pass


def consolidate_net_worth(
    fonte_snapshot_path: Path,
    output_path: Path,
    assumptions_snapshot_path: Path | None = None,
    investments_snapshot_path: Path | None = None,
    bank_insurance_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    data_gaps: list[str] = []
    sources: dict[str, str] = {}

    if fonte_snapshot_path.exists():
        fonte_snapshot = _read_json(fonte_snapshot_path)
        components.append(_fonte_component(fonte_snapshot, fonte_snapshot_path))
        sources["fonte"] = str(fonte_snapshot_path)
    else:
        data_gaps.append(f"Missing Fon.Te snapshot: {fonte_snapshot_path}")

    if investments_snapshot_path is not None:
        if investments_snapshot_path.exists():
            investments_snapshot = _read_json(investments_snapshot_path)
            investment_components, investment_gaps = _investment_components(
                investments_snapshot,
                investments_snapshot_path,
            )
            components.extend(investment_components)
            data_gaps.extend(investment_gaps)
            data_gaps.extend(
                _snapshot_data_gaps("investments", investments_snapshot)
            )
            sources["investments"] = str(investments_snapshot_path)
        else:
            data_gaps.append(f"Missing investments snapshot: {investments_snapshot_path}")

    if bank_insurance_snapshot_path is not None:
        if bank_insurance_snapshot_path.exists():
            bank_insurance_snapshot = _read_json(bank_insurance_snapshot_path)
            bank_components, bank_gaps = _bank_insurance_components(
                bank_insurance_snapshot,
                bank_insurance_snapshot_path,
            )
            components.extend(bank_components)
            data_gaps.extend(bank_gaps)
            data_gaps.extend(
                _snapshot_data_gaps("bank_insurance", bank_insurance_snapshot)
            )
            sources["bank_insurance"] = str(bank_insurance_snapshot_path)
        else:
            data_gaps.append(
                f"Missing bank-insurance snapshot: {bank_insurance_snapshot_path}"
            )

    if assumptions_snapshot_path is not None:
        if assumptions_snapshot_path.exists():
            sources["manual_assumptions"] = str(assumptions_snapshot_path)
        else:
            data_gaps.append(f"Missing manual assumptions snapshot: {assumptions_snapshot_path}")

    totals = _totals(components)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "NetWorthSnapshot",
        "currency": "EUR",
        "sources": sources,
        "components": components,
        "totals": totals,
        "data_gaps": data_gaps,
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise NetWorthError(f"Cannot write net worth snapshot: {output_path}") from exc
    return snapshot


def _fonte_component(snapshot: dict[str, Any], source_path: Path) -> dict[str, Any]:
    if snapshot.get("record_type") != "FonTeSourceBundle":
        raise NetWorthError(f"Unsupported Fon.Te snapshot record type: {source_path}")

    position = snapshot.get("position")
    if not isinstance(position, dict):
        raise NetWorthError(f"Fon.Te snapshot has no extracted position: {source_path}")

    return {
        "id": "fonte_position",
        "label": "Fon.Te pension fund position",
        "type": "asset",
        "asset_class": "pension",
        "value": _decimal_string(position.get("position_value"), "position.position_value"),
        "currency": "EUR",
        "valuation_date": position.get("statement_date"),
        "source": {
            "snapshot": str(source_path),
            "field": "position.position_value",
        },
    }


def _investment_components(snapshot: dict[str, Any], source_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if snapshot.get("record_type") != "InvestmentsSnapshot":
        raise NetWorthError(f"Unsupported investments snapshot record type: {source_path}")

    positions = snapshot.get("positions", [])
    if not isinstance(positions, list):
        raise NetWorthError(f"Investments snapshot positions must be a list: {source_path}")

    current_positions, excluded_positions = _latest_net_worth_positions(positions)
    components: list[dict[str, Any]] = []
    for position in current_positions:
        if not isinstance(position, dict):
            raise NetWorthError(f"Investments position must be an object: {source_path}")
        index = positions.index(position) + 1
        provider = str(position.get("provider") or "unknown")
        instrument_type = str(position.get("instrument_type") or "investment")
        components.append(
            {
                "id": f"investment_{index}",
                "label": f"{provider} {position.get('description') or instrument_type}",
                "type": "asset",
                "asset_class": _investment_asset_class(instrument_type),
                "value": _decimal_string(
                    position.get("market_value"),
                    f"positions[{index - 1}].market_value",
                ),
                "currency": position.get("currency", "EUR"),
                "valuation_date": position.get("statement_date"),
                "source": {
                    "snapshot": str(source_path),
                    "field": f"positions[{index - 1}].market_value",
                    "document": position.get("source"),
                },
            }
        )
    data_gaps = [
        "Excluded older investment statement from net worth because a newer valuation exists: "
        f"{position.get('provider', 'unknown')} {position.get('description') or position.get('instrument_type', 'investment')} "
        f"{position.get('statement_date', 'unknown date')} ({position.get('source', {}).get('filename', 'unknown file')})"
        for position in excluded_positions
    ]
    return components, data_gaps


def _latest_net_worth_positions(positions: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    latest_by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    passthrough: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for position in positions:
        if not isinstance(position, dict):
            passthrough.append(position)
            continue
        key = _latest_position_key(position)
        if key is None:
            passthrough.append(position)
            continue

        current = latest_by_key.get(key)
        if current is None:
            latest_by_key[key] = position
            continue
        if str(position.get("statement_date") or "") > str(current.get("statement_date") or ""):
            excluded.append(current)
            latest_by_key[key] = position
        else:
            excluded.append(position)

    latest_positions = set(id(position) for position in latest_by_key.values())
    current_positions: list[dict[str, Any]] = []
    for position in positions:
        if not isinstance(position, dict):
            current_positions.append(position)
            continue
        key = _latest_position_key(position)
        if key is None or id(position) in latest_positions:
            current_positions.append(position)
    return current_positions, excluded


def _latest_position_key(position: dict[str, Any]) -> tuple[str, str, str, str] | None:
    provider = str(position.get("provider") or "")
    instrument_type = str(position.get("instrument_type") or "")
    if provider != "Moneyfarm" or instrument_type != "managed_portfolio":
        return None
    return (
        provider,
        instrument_type,
        str(position.get("description") or ""),
        str(position.get("currency") or "EUR"),
    )


def _bank_insurance_components(
    snapshot: dict[str, Any],
    source_path: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    if snapshot.get("record_type") != "BankInsuranceSnapshot":
        raise NetWorthError(f"Unsupported bank-insurance snapshot record type: {source_path}")

    items = snapshot.get("items", [])
    if not isinstance(items, list):
        raise NetWorthError(f"Bank-insurance snapshot items must be a list: {source_path}")

    components: list[dict[str, Any]] = []
    data_gaps: list[str] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise NetWorthError(f"Bank-insurance item must be an object: {source_path}")

        amount_type = str(item.get("amount_type") or "")
        if not _is_balance_amount(amount_type):
            data_gaps.append(
                "Excluded bank-insurance item from net worth because amount_type "
                f"is not a balance/value: {item.get('provider', 'unknown')} {amount_type}"
            )
            continue

        provider = str(item.get("provider") or "unknown")
        document_group = str(item.get("document_group") or "bank")
        components.append(
            {
                "id": f"bank_insurance_{index}",
                "label": f"{provider} {item.get('description') or amount_type}",
                "type": "asset",
                "asset_class": _bank_insurance_asset_class(document_group),
                "value": _decimal_string(
                    item.get("amount"),
                    f"items[{index - 1}].amount",
                ),
                "currency": item.get("currency", "EUR"),
                "valuation_date": item.get("statement_date") or item.get("period_year"),
                "source": {
                    "snapshot": str(source_path),
                    "field": f"items[{index - 1}].amount",
                    "document": item.get("source"),
                },
            }
        )
    return components, data_gaps


def _investment_asset_class(instrument_type: str) -> str:
    if instrument_type in {"cash_account", "bank_account"}:
        return "cash"
    if "pension" in instrument_type:
        return "pension"
    return "investment"


def _bank_insurance_asset_class(document_group: str) -> str:
    if document_group == "insurance":
        return "insurance"
    return "cash"


def _is_balance_amount(amount_type: str) -> bool:
    return amount_type in {
        "account_balance",
        "cash_balance",
        "current_value",
        "market_value",
        "policy_value",
        "surrender_value",
    }


def _totals(components: list[dict[str, Any]]) -> dict[str, str]:
    assets = Decimal("0.00")
    liabilities = Decimal("0.00")

    for component in components:
        value = Decimal(component["value"])
        if component["type"] == "asset":
            assets += value
        elif component["type"] == "liability":
            liabilities += value

    net_worth = assets - liabilities
    return {
        "assets": _quantize(assets),
        "liabilities": _quantize(liabilities),
        "net_worth": _quantize(net_worth),
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NetWorthError(f"Cannot read JSON snapshot: {path}") from exc
    if not isinstance(data, dict):
        raise NetWorthError(f"Snapshot must be a JSON object: {path}")
    return data


def _snapshot_data_gaps(source_name: str, snapshot: dict[str, Any]) -> list[str]:
    gaps = snapshot.get("data_gaps", [])
    if not isinstance(gaps, list):
        raise NetWorthError(f"{source_name} snapshot data_gaps must be a list")
    return [f"{source_name}: {_format_gap(gap)}" for gap in gaps]


def _format_gap(gap: Any) -> str:
    if isinstance(gap, dict):
        code = gap.get("code", "data_gap")
        filename = gap.get("filename")
        message = gap.get("message", "")
        if filename:
            return f"{code} ({filename}): {message}"
        return f"{code}: {message}"
    return str(gap)


def _decimal_string(value: Any, field_name: str) -> str:
    if value is None:
        raise NetWorthError(f"Missing required value: {field_name}")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise NetWorthError(f"Invalid decimal value for {field_name}: {value}") from exc
    return _quantize(amount)


def _quantize(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))
