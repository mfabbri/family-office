import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "estate-baseline/v1"
RULE_PACK_SCHEMA_VERSION = "estate-rule-pack/v1"
CENT = Decimal("0.01")


class EstateBaselineError(ValueError):
    pass


def build_estate_baseline(
    net_worth_snapshot_path: Path,
    rule_pack_path: Path,
    output_path: Path,
    *,
    has_spouse: bool,
    children_count: int,
    prior_donations: str | None = None,
) -> dict[str, Any]:
    if children_count < 0:
        raise EstateBaselineError("children_count must be greater than or equal to zero")
    rule_pack = load_rule_pack(rule_pack_path)
    net_worth = _read_json(net_worth_snapshot_path)
    if net_worth.get("record_type") != "NetWorthSnapshot":
        raise EstateBaselineError(f"Unsupported net worth snapshot record type: {net_worth_snapshot_path}")

    donation_amount = _optional_money(prior_donations, "prior_donations")
    data_gaps: list[dict[str, Any]] = []
    components = _estate_components(net_worth, data_gaps, rule_pack)
    totals = _totals(components, donation_amount)
    heirs = _theoretical_heirs(rule_pack, has_spouse, children_count, totals["known_estate_mass"], data_gaps)
    liquidity = _liquidity_summary(components)
    status = "partial" if data_gaps else "complete"

    if donation_amount is None:
        data_gaps.append(
            {
                "code": "prior_donations_not_provided",
                "message": "Prior donations are unknown; collation, reduction and available share are outside V1.",
            }
        )
        status = "partial"

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "EstateBaselineSnapshot",
        "status": status,
        "input": {
            "net_worth_snapshot": str(net_worth_snapshot_path),
            "has_spouse": has_spouse,
            "children_count": children_count,
            "prior_donations": _format_optional_money(donation_amount),
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
        "estate_components": components,
        "totals": {
            key: _format_money(value)
            for key, value in totals.items()
        },
        "theoretical_heirs": heirs,
        "liquidity": liquidity,
        "data_gaps": data_gaps,
        "notes": (
            "Estate baseline V1 is a deterministic planning snapshot. It is not legal, tax or notarial advice."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise EstateBaselineError(f"Cannot write estate baseline snapshot: {output_path}") from exc
    return snapshot


def load_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    data = _read_json(rule_pack_path)
    required = ("schema_version", "rule_pack_id", "jurisdiction", "currency", "intestate_share_rules")
    for field in required:
        if field not in data:
            raise EstateBaselineError(f"Estate rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise EstateBaselineError(f"Unsupported estate rule pack schema: {data['schema_version']}")
    if not isinstance(data["intestate_share_rules"], list):
        raise EstateBaselineError("Estate rule pack intestate_share_rules must be a list")
    return data


def _estate_components(
    net_worth: dict[str, Any],
    data_gaps: list[dict[str, Any]],
    rule_pack: dict[str, Any],
) -> list[dict[str, Any]]:
    raw_components = net_worth.get("components", [])
    if not isinstance(raw_components, list):
        raise EstateBaselineError("Net worth snapshot components must be a list")
    liquidity_classes = rule_pack.get("liquidity_classes", {})
    components: list[dict[str, Any]] = []
    for index, component in enumerate(raw_components, start=1):
        if not isinstance(component, dict):
            raise EstateBaselineError("Net worth component must be an object")
        component_id = str(component.get("id") or f"component_{index}")
        value = _money(component.get("value"), f"components[{index - 1}].value")
        asset_class = str(component.get("asset_class") or "unknown")
        ownership = component.get("ownership")
        ownership_share = None
        estate_value = None
        if isinstance(ownership, dict) and ownership.get("share") not in (None, ""):
            ownership_share = _share(ownership.get("share"), f"components[{index - 1}].ownership.share")
            estate_value = (value * ownership_share).quantize(CENT, rounding=ROUND_HALF_UP)
        else:
            data_gaps.append(
                {
                    "code": "missing_ownership",
                    "component_id": component_id,
                    "message": "Component ownership share is missing; estate value is not computed for this asset.",
                }
            )
        if str(component.get("currency") or "EUR") != rule_pack["currency"]:
            data_gaps.append(
                {
                    "code": "foreign_currency_or_asset",
                    "component_id": component_id,
                    "message": "Foreign currency or asset requires cross-border succession review.",
                }
            )
        if asset_class in {"insurance", "pension"}:
            data_gaps.append(
                {
                    "code": "beneficiary_review_required",
                    "component_id": component_id,
                    "message": "Insurance and pension beneficiary treatment is not determined in V1.",
                }
            )
        liquidity_class = liquidity_classes.get(asset_class, "unknown")
        components.append(
            {
                "id": component_id,
                "label": component.get("label"),
                "asset_class": asset_class,
                "observed_value": _format_money(value),
                "ownership_share": None if ownership_share is None else str(ownership_share),
                "estate_value": None if estate_value is None else _format_money(estate_value),
                "currency": component.get("currency", rule_pack["currency"]),
                "liquidity_class": liquidity_class,
                "source": component.get("source"),
            }
        )
    return components


def _totals(components: list[dict[str, Any]], prior_donations: Decimal | None) -> dict[str, Decimal]:
    observed = Decimal("0.00")
    known_estate = Decimal("0.00")
    unknown_ownership = Decimal("0.00")
    for component in components:
        observed += _money(component["observed_value"], "observed_value")
        if component["estate_value"] is None:
            unknown_ownership += _money(component["observed_value"], "observed_value")
        else:
            known_estate += _money(component["estate_value"], "estate_value")
    donations = prior_donations or Decimal("0.00")
    return {
        "observed_gross_assets": observed,
        "known_estate_mass": known_estate,
        "unknown_ownership_assets": unknown_ownership,
        "prior_donations_declared": donations,
        "notional_mass_with_declared_donations": known_estate + donations,
    }


def _theoretical_heirs(
    rule_pack: dict[str, Any],
    has_spouse: bool,
    children_count: int,
    known_estate_mass: Decimal,
    data_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    family_case = _family_case(has_spouse, children_count)
    if family_case is None:
        data_gaps.append(
            {
                "code": "family_case_not_supported",
                "message": "V1 supports only spouse and/or children simple intestate cases.",
            }
        )
        return []
    rule = _find_share_rule(rule_pack, family_case)
    if rule is None:
        data_gaps.append(
            {
                "code": "missing_intestate_share_rule",
                "family_case": family_case,
                "message": "No intestate share rule is available for this family case.",
            }
        )
        return []
    heirs: list[dict[str, Any]] = []
    spouse_share = _share(rule["spouse_share"], "spouse_share")
    children_share = _share(rule["children_share"], "children_share")
    if has_spouse and spouse_share > Decimal("0"):
        heirs.append(_heir("spouse", "spouse", spouse_share, known_estate_mass, rule))
    if children_count > 0 and children_share > Decimal("0"):
        child_share = children_share / Decimal(children_count)
        for index in range(1, children_count + 1):
            heirs.append(_heir(f"child_{index}", "child", child_share, known_estate_mass, rule))
    return heirs


def _family_case(has_spouse: bool, children_count: int) -> str | None:
    if has_spouse and children_count == 0:
        return "spouse_only"
    if not has_spouse and children_count > 0:
        return "children_only"
    if has_spouse and children_count == 1:
        return "spouse_one_child"
    if has_spouse and children_count > 1:
        return "spouse_multiple_children"
    return None


def _find_share_rule(rule_pack: dict[str, Any], family_case: str) -> dict[str, Any] | None:
    for rule in rule_pack["intestate_share_rules"]:
        if rule.get("family_case") == family_case:
            return rule
    return None


def _heir(
    heir_id: str,
    relationship: str,
    share: Decimal,
    known_estate_mass: Decimal,
    rule: dict[str, Any],
) -> dict[str, Any]:
    amount = (known_estate_mass * share).quantize(CENT, rounding=ROUND_HALF_UP)
    return {
        "heir_id": heir_id,
        "relationship": relationship,
        "theoretical_share": str(share.quantize(Decimal("0.0000000001"))),
        "known_estate_amount": _format_money(amount),
        "rule_id": rule["rule_id"],
        "source_articles": rule.get("source_articles", []),
    }


def _liquidity_summary(components: list[dict[str, Any]]) -> dict[str, str]:
    totals: dict[str, Decimal] = {}
    for component in components:
        estate_value = component.get("estate_value")
        if estate_value is None:
            continue
        liquidity_class = str(component.get("liquidity_class") or "unknown")
        totals[liquidity_class] = totals.get(liquidity_class, Decimal("0.00")) + _money(estate_value, "estate_value")
    return {key: _format_money(value) for key, value in sorted(totals.items())}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EstateBaselineError(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EstateBaselineError(f"JSON file is not valid: {path}") from exc
    if not isinstance(data, dict):
        raise EstateBaselineError(f"JSON file must contain an object: {path}")
    return data


def _money(value: Any, field_name: str) -> Decimal:
    if value is None:
        raise EstateBaselineError(f"Missing required money value: {field_name}")
    try:
        return Decimal(str(value)).quantize(CENT)
    except (InvalidOperation, TypeError) as exc:
        raise EstateBaselineError(f"Invalid money value for {field_name}: {value}") from exc


def _optional_money(value: str | None, field_name: str) -> Decimal | None:
    if value in (None, ""):
        return None
    amount = _money(value, field_name)
    if amount < Decimal("0.00"):
        raise EstateBaselineError(f"{field_name} must be greater than or equal to zero")
    return amount


def _share(value: Any, field_name: str) -> Decimal:
    try:
        share = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise EstateBaselineError(f"Invalid share value for {field_name}: {value}") from exc
    if share < Decimal("0") or share > Decimal("1"):
        raise EstateBaselineError(f"{field_name} must be between 0 and 1")
    return share


def _format_optional_money(value: Decimal | None) -> str | None:
    return None if value is None else _format_money(value)


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))
