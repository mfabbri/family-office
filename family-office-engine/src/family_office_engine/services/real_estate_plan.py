import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "real-estate-plan/v1"
INPUT_RECORD_TYPE = "RealEstatePlanInput"
SNAPSHOT_RECORD_TYPE = "RealEstatePlanSnapshot"
CENT = Decimal("0.01")
SUPPORTED_STRATEGIES = {"hold", "rent", "sell"}


class RealEstatePlanError(ValueError):
    pass


def build_real_estate_plan(input_path: Path, output_path: Path) -> dict[str, Any]:
    data = _read_json(input_path, "real estate plan input")
    errors: list[str] = []
    data_gaps: list[dict[str, Any]] = []
    _validate_input(data, errors, data_gaps)
    if errors:
        raise RealEstatePlanError("; ".join(errors))

    base_currency = data["base_currency"]
    properties = [_normalize_property(item, index, base_currency, data_gaps) for index, item in enumerate(data["properties"])]
    alternatives = _build_alternatives(properties, data_gaps)
    summary = _summary(alternatives, data_gaps, base_currency)
    status = "complete" if not data_gaps else "partial"
    core = {
        "source": {"type": "real-estate-plan-input-json", "path": str(input_path)},
        "household": {"household_id": data["household_id"], "as_of_date": data["as_of_date"]},
        "base_currency": base_currency,
        "properties": properties,
        "alternatives": alternatives,
        "summary": summary,
        "data_gaps": data_gaps,
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": status,
        **core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(_semantic_core(core)),
        },
        "notes": (
            "Real-estate plan V1 compares explicit hold, rent and sell alternatives. It does not calculate "
            "tax law, inheritance law, appraisals, financing, FX, recommendations or filings."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise RealEstatePlanError(f"Cannot write real estate plan snapshot: {output_path}") from exc
    return snapshot


def _validate_input(data: dict[str, Any], errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported real estate plan schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported real estate plan record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_string(data, "as_of_date", errors)
    base_currency = _required_string(data, "base_currency", errors)
    if base_currency and (len(base_currency) != 3 or base_currency.upper() != base_currency):
        errors.append("base_currency must be an ISO-4217 uppercase code")
    properties = data.get("properties")
    if not isinstance(properties, list) or not properties:
        errors.append("At least one real estate property is required")
    elif not all(isinstance(item, dict) for item in properties):
        errors.append("properties must contain objects")
    _validate_declared_gaps(data.get("data_gaps", []), errors, data_gaps)


def _normalize_property(item: dict[str, Any], index: int, base_currency: str, data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    prefix = f"properties[{index}]"
    property_id = _required_property_text(item, "property_id", prefix)
    currency = item.get("currency") or base_currency
    if currency != base_currency:
        data_gaps.append(
            {
                "code": "foreign_currency_property",
                "property_id": property_id,
                "currency": currency,
                "message": "Property currency differs from base currency; no FX conversion is performed.",
            }
        )
    market_value = _money(item.get("market_value"), f"{prefix}.market_value")
    ownership = _ownership(item.get("ownership"), property_id, data_gaps)
    declared_taxes = _costs(item.get("declared_taxes", []), f"{prefix}.declared_taxes", property_id)
    annual_costs = _costs(item.get("annual_costs", []), f"{prefix}.annual_costs", property_id)
    rent = item.get("rent_assumption") if isinstance(item.get("rent_assumption"), dict) else {}
    sale = item.get("sale_assumption") if isinstance(item.get("sale_assumption"), dict) else {}
    provenance = item.get("provenance", [])
    if not isinstance(provenance, list) or not provenance:
        data_gaps.append({"code": "missing_property_provenance", "property_id": property_id, "message": "Property provenance is required."})
    return {
        "property_id": property_id,
        "asset_id": item.get("asset_id") or property_id,
        "label": item.get("label") or property_id,
        "jurisdiction": item.get("jurisdiction"),
        "currency": currency,
        "market_value": _format_money(market_value),
        "ownership": ownership,
        "annual_costs": [_public_cost(cost) for cost in annual_costs],
        "declared_taxes": [_public_cost(cost) for cost in declared_taxes],
        "rent_assumption": {
            "monthly_gross_rent": _optional_money_text(rent.get("monthly_gross_rent"), f"{prefix}.rent_assumption.monthly_gross_rent"),
            "vacancy_months": _optional_months(rent.get("vacancy_months"), f"{prefix}.rent_assumption.vacancy_months"),
            "letting_costs": [_public_cost(cost) for cost in _costs(rent.get("letting_costs", []), f"{prefix}.rent_assumption.letting_costs", property_id)],
        },
        "sale_assumption": {
            "estimated_sale_price": _optional_money_text(sale.get("estimated_sale_price"), f"{prefix}.sale_assumption.estimated_sale_price"),
            "months_to_liquidity": _optional_months(sale.get("months_to_liquidity"), f"{prefix}.sale_assumption.months_to_liquidity"),
            "selling_costs": [_public_cost(cost) for cost in _costs(sale.get("selling_costs", []), f"{prefix}.sale_assumption.selling_costs", property_id)],
        },
        "provenance": provenance,
    }


def _build_alternatives(properties: list[dict[str, Any]], data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alternatives = []
    for item in properties:
        for strategy in ("hold", "rent", "sell"):
            alternatives.append(_alternative(item, strategy, data_gaps))
    return alternatives


def _alternative(property_data: dict[str, Any], strategy: str, data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    property_id = property_data["property_id"]
    annual_costs = _sum_public_costs(property_data["annual_costs"])
    declared_taxes = _sum_public_costs(property_data["declared_taxes"])
    owned_share = _owned_share(property_data["ownership"])
    market_value = _money(property_data["market_value"], f"{property_id}.market_value")
    value_at_risk = (market_value * owned_share).quantize(CENT, rounding=ROUND_HALF_UP)
    gross_income = Decimal("0.00")
    net_cashflow = -(annual_costs + declared_taxes) * owned_share
    liquidity_amount = Decimal("0.00")
    liquidity_month = None
    gap_codes: list[str] = []

    if not property_data["declared_taxes"]:
        _append_gap(data_gaps, gap_codes, "missing_real_estate_tax_input", property_id, "Real-estate taxes must be explicit or supplied by a deterministic rule pack.")

    if strategy == "rent":
        rent = property_data["rent_assumption"]
        if rent["monthly_gross_rent"] is None:
            _append_gap(data_gaps, gap_codes, "missing_rent_assumption", property_id, "Monthly gross rent is required to compare rental use.")
        if rent["vacancy_months"] is None:
            _append_gap(data_gaps, gap_codes, "missing_vacancy_assumption", property_id, "Vacancy months are required to compare rental use.")
        if rent["monthly_gross_rent"] is not None and rent["vacancy_months"] is not None:
            rented_months = max(Decimal("0"), Decimal("12") - Decimal(rent["vacancy_months"]))
            gross_income = _money(rent["monthly_gross_rent"], f"{property_id}.monthly_gross_rent") * rented_months
            letting_costs = _sum_public_costs(rent["letting_costs"])
            net_cashflow = (gross_income - annual_costs - declared_taxes - letting_costs) * owned_share
    elif strategy == "sell":
        sale = property_data["sale_assumption"]
        if sale["estimated_sale_price"] is None:
            _append_gap(data_gaps, gap_codes, "missing_sale_price", property_id, "Estimated sale price is required to compare sale.")
        if sale["months_to_liquidity"] is None:
            _append_gap(data_gaps, gap_codes, "missing_sale_liquidity_timing", property_id, "Sale liquidity timing must be explicit.")
        if sale["estimated_sale_price"] is not None:
            selling_costs = _sum_public_costs(sale["selling_costs"])
            liquidity_amount = (_money(sale["estimated_sale_price"], f"{property_id}.sale_price") - selling_costs - declared_taxes) * owned_share
            net_cashflow = liquidity_amount
        liquidity_month = sale["months_to_liquidity"]

    return {
        "alternative_id": f"{property_id}_{strategy}",
        "property_id": property_id,
        "strategy": strategy,
        "status": "partial" if gap_codes else "complete",
        "owned_share": _format_ratio(owned_share),
        "value_at_risk": _format_money(value_at_risk),
        "annual_gross_income": _format_money(gross_income),
        "annual_net_cashflow_or_proceeds": _format_money(net_cashflow.quantize(CENT, rounding=ROUND_HALF_UP)),
        "liquidity_amount": _format_money(liquidity_amount.quantize(CENT, rounding=ROUND_HALF_UP)),
        "liquidity_month": liquidity_month,
        "gap_codes": gap_codes,
    }


def _summary(alternatives: list[dict[str, Any]], data_gaps: list[dict[str, Any]], base_currency: str) -> dict[str, Any]:
    complete = [item for item in alternatives if item["status"] == "complete"]
    best_liquidity = max(complete, key=lambda item: _money(item["liquidity_amount"], "liquidity_amount"), default=None)
    best_cashflow = max(complete, key=lambda item: _money(item["annual_net_cashflow_or_proceeds"], "cashflow"), default=None)
    return {
        "property_count": len({item["property_id"] for item in alternatives}),
        "alternative_count": len(alternatives),
        "complete_alternative_count": len(complete),
        "data_gap_count": len(data_gaps),
        "base_currency": base_currency,
        "highest_liquidity_alternative_id": best_liquidity["alternative_id"] if best_liquidity else None,
        "highest_cashflow_alternative_id": best_cashflow["alternative_id"] if best_cashflow else None,
        "review_required": True,
    }


def _ownership(value: Any, property_id: str, data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        data_gaps.append({"code": "missing_property_ownership", "property_id": property_id, "message": "Property ownership shares are required."})
        return []
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RealEstatePlanError(f"ownership[{index}] must be an object")
        share = _ratio(item.get("share"), f"ownership[{index}].share")
        result.append(
            {
                "owner_person_id": item.get("owner_person_id"),
                "relationship": item.get("relationship"),
                "share": _format_ratio(share),
                "provenance": item.get("provenance"),
            }
        )
    total = sum((_money(item["share"], "ownership.share") for item in result), Decimal("0.00"))
    if total <= 0 or total > 1:
        raise RealEstatePlanError("Property ownership shares must be greater than 0 and at most 1 in total")
    if total < 1:
        data_gaps.append({"code": "incomplete_property_ownership", "property_id": property_id, "message": "Known ownership shares total less than 100%."})
    return result


def _costs(value: Any, label: str, property_id: str) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise RealEstatePlanError(f"{label} must be a list")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RealEstatePlanError(f"{label}[{index}] must be an object")
        result.append(
            {
                "code": item.get("code") or f"{property_id}_cost_{index + 1}",
                "label": item.get("label") or item.get("code") or "Declared cost",
                "amount": _money(item.get("amount"), f"{label}[{index}].amount"),
                "provenance": item.get("provenance"),
            }
        )
    return result


def _append_gap(data_gaps: list[dict[str, Any]], gap_codes: list[str], code: str, property_id: str, message: str) -> None:
    gap_codes.append(code)
    data_gaps.append({"code": code, "property_id": property_id, "message": message})


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RealEstatePlanError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RealEstatePlanError(f"Invalid JSON in {label} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RealEstatePlanError(f"{label} must contain a JSON object.")
    return data


def _required_string(data: dict[str, Any], field: str, errors: list[str]) -> str | None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required")
        return None
    return value


def _required_property_text(data: dict[str, Any], field: str, prefix: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RealEstatePlanError(f"{prefix}.{field} is required")
    return value


def _validate_declared_gaps(raw_gaps: Any, errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if raw_gaps in (None, ""):
        return
    if not isinstance(raw_gaps, list):
        errors.append("data_gaps must be a list")
        return
    for index, gap in enumerate(raw_gaps):
        if not isinstance(gap, dict):
            errors.append(f"data_gaps[{index}] must be an object")
        elif not gap.get("code"):
            errors.append(f"data_gaps[{index}].code is required")
        else:
            data_gaps.append(gap)


def _optional_money_text(value: Any, label: str) -> str | None:
    if value in (None, ""):
        return None
    return _format_money(_money(value, label))


def _optional_months(value: Any, label: str) -> int | None:
    if value in (None, ""):
        return None
    if not isinstance(value, int) or value < 0 or value > 12:
        raise RealEstatePlanError(f"{label} must be an integer from 0 to 12")
    return value


def _money(value: Any, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise RealEstatePlanError(f"{label} must be a decimal") from exc


def _ratio(value: Any, label: str) -> Decimal:
    ratio = _money(value, label)
    if ratio <= 0 or ratio > 1:
        raise RealEstatePlanError(f"{label} must be greater than 0 and less than or equal to 1")
    return ratio


def _sum_public_costs(costs: list[dict[str, Any]]) -> Decimal:
    return sum((_money(cost["amount"], "cost.amount") for cost in costs), Decimal("0.00"))


def _owned_share(ownership: list[dict[str, Any]]) -> Decimal:
    return sum((_money(item["share"], "ownership.share") for item in ownership), Decimal("0.00"))


def _public_cost(cost: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": cost["code"],
        "label": cost["label"],
        "amount": _format_money(cost["amount"]),
        "provenance": cost.get("provenance"),
    }


def _semantic_core(core: dict[str, Any]) -> dict[str, Any]:
    semantic = json.loads(json.dumps(core))
    source = semantic.get("source")
    if isinstance(source, dict):
        source.pop("path", None)
    return semantic


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _format_ratio(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
