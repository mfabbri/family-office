import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "tax-calculation/v1"
RULE_PACK_SCHEMA_VERSION = "tax-rule-pack/v1"
CENT = Decimal("0.01")


class TaxCalculationError(ValueError):
    pass


def calculate_tax(
    rule_pack_path: Path,
    tax_year: int,
    jurisdiction: str,
    taxable_income: str,
    output_path: Path,
) -> dict[str, Any]:
    try:
        income = _money(taxable_income)
    except TaxCalculationError as exc:
        raise TaxCalculationError(f"Invalid taxable income: {taxable_income}") from exc
    if income < Decimal("0"):
        raise TaxCalculationError("taxable_income must be greater than or equal to zero")

    rule_pack = load_rule_pack(rule_pack_path)
    data_gaps: list[dict[str, Any]] = []
    result: dict[str, Any] | None = None
    status = "complete"

    if rule_pack["jurisdiction"] != jurisdiction:
        status = "blocked_missing_rule"
        data_gaps.append(
            {
                "code": "jurisdiction_not_covered",
                "message": f"Rule pack jurisdiction {rule_pack['jurisdiction']} does not match {jurisdiction}.",
                "requested_jurisdiction": jurisdiction,
                "rule_pack_jurisdiction": rule_pack["jurisdiction"],
            }
        )
    else:
        rule = _find_rule_for_year(rule_pack, tax_year)
        if rule is None:
            status = "blocked_missing_rule"
            data_gaps.append(
                {
                    "code": "tax_year_not_covered",
                    "message": f"No tax rule found for year {tax_year}.",
                    "tax_year": tax_year,
                }
            )
        else:
            result = _calculate_progressive_tax(rule, income, rule_pack)

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "TaxCalculationSnapshot",
        "status": status,
        "input": {
            "tax_year": tax_year,
            "jurisdiction": jurisdiction,
            "taxable_income": _format_money(income),
            "currency": rule_pack["currency"],
        },
        "rule_pack": {
            "path": str(rule_pack_path),
            "rule_pack_id": rule_pack["rule_pack_id"],
            "schema_version": rule_pack["schema_version"],
            "status": rule_pack.get("status"),
            "source_refs": rule_pack.get("source_refs", []),
            "limitations": rule_pack.get("limitations", []),
        },
        "result": result,
        "data_gaps": data_gaps,
        "notes": "Tax calculation is deterministic and rule-pack driven. Synthetic rule packs are not legal advice.",
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise TaxCalculationError(f"Cannot write tax calculation snapshot: {output_path}") from exc
    return snapshot


def load_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(rule_pack_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TaxCalculationError(f"Rule pack not found: {rule_pack_path}") from exc
    except json.JSONDecodeError as exc:
        raise TaxCalculationError(f"Rule pack is not valid JSON: {rule_pack_path}") from exc

    _validate_rule_pack(data)
    return data


def _validate_rule_pack(data: dict[str, Any]) -> None:
    required = ("schema_version", "rule_pack_id", "jurisdiction", "currency", "rules")
    for field in required:
        if field not in data:
            raise TaxCalculationError(f"Rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise TaxCalculationError(f"Unsupported rule pack schema: {data['schema_version']}")
    if not isinstance(data["rules"], list) or not data["rules"]:
        raise TaxCalculationError("Rule pack must contain at least one rule")

    for rule in data["rules"]:
        for field in ("rule_id", "tax_type", "valid_from", "valid_to", "brackets"):
            if field not in rule:
                raise TaxCalculationError(f"Tax rule missing field: {field}")
        _validate_brackets(rule["brackets"], rule["rule_id"])


def _validate_brackets(brackets: list[dict[str, Any]], rule_id: str) -> None:
    if not brackets:
        raise TaxCalculationError(f"Rule {rule_id} must contain brackets")
    expected_from = Decimal("0.00")
    open_ended_seen = False
    for bracket in brackets:
        lower = _money(bracket.get("from"))
        upper = bracket.get("to")
        rate = _rate(bracket.get("rate"))
        if lower != expected_from:
            raise TaxCalculationError(f"Rule {rule_id} has non-contiguous brackets")
        if open_ended_seen:
            raise TaxCalculationError(f"Rule {rule_id} has brackets after an open-ended bracket")
        if upper is None:
            open_ended_seen = True
        else:
            upper_decimal = _money(upper)
            if upper_decimal <= lower:
                raise TaxCalculationError(f"Rule {rule_id} has invalid bracket bounds")
            expected_from = upper_decimal
        if rate < Decimal("0") or rate > Decimal("1"):
            raise TaxCalculationError(f"Rule {rule_id} has invalid rate")


def _find_rule_for_year(rule_pack: dict[str, Any], tax_year: int) -> dict[str, Any] | None:
    target = f"{tax_year:04d}"
    for rule in rule_pack["rules"]:
        if rule["valid_from"][:4] <= target <= rule["valid_to"][:4]:
            return rule
    return None


def _calculate_progressive_tax(
    rule: dict[str, Any],
    income: Decimal,
    rule_pack: dict[str, Any],
) -> dict[str, Any]:
    tax = Decimal("0.00")
    applied_brackets: list[dict[str, Any]] = []
    for bracket in rule["brackets"]:
        lower = _money(bracket["from"])
        upper = None if bracket["to"] is None else _money(bracket["to"])
        rate = _rate(bracket["rate"])
        taxable_slice = _slice_amount(income, lower, upper)
        tax_amount = (taxable_slice * rate).quantize(CENT, rounding=ROUND_HALF_UP)
        if taxable_slice > Decimal("0.00"):
            applied_brackets.append(
                {
                    "from": _format_money(lower),
                    "to": None if upper is None else _format_money(upper),
                    "taxable_amount": _format_money(taxable_slice),
                    "rate": str(rate),
                    "tax_amount": _format_money(tax_amount),
                    "rule_id": rule["rule_id"],
                    "valid_from": rule["valid_from"],
                    "valid_to": rule["valid_to"],
                }
            )
        tax += tax_amount
    return {
        "tax_type": rule["tax_type"],
        "jurisdiction": rule_pack["jurisdiction"],
        "currency": rule_pack["currency"],
        "taxable_income": _format_money(income),
        "tax_due": _format_money(tax),
        "applied_brackets": applied_brackets,
        "explainability": {
            "rule_pack_id": rule_pack["rule_pack_id"],
            "rule_id": rule["rule_id"],
            "valid_from": rule["valid_from"],
            "valid_to": rule["valid_to"],
        },
    }


def _slice_amount(income: Decimal, lower: Decimal, upper: Decimal | None) -> Decimal:
    if income <= lower:
        return Decimal("0.00")
    if upper is None:
        return income - lower
    return min(income, upper) - lower


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(CENT)
    except (InvalidOperation, TypeError) as exc:
        raise TaxCalculationError(f"Invalid money value: {value}") from exc


def _rate(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise TaxCalculationError(f"Invalid rate value: {value}") from exc


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))
