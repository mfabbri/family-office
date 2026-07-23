import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "tax-aware-portfolio/v1"
INPUT_SCHEMA_VERSION = "tax-aware-portfolio-input/v1"
INPUT_RECORD_TYPE = "TaxAwarePortfolioInput"
RULE_PACK_SCHEMA_VERSION = "tax-aware-investment-rule-pack/v1"
SNAPSHOT_RECORD_TYPE = "TaxAwarePortfolioSnapshot"
CENT = Decimal("0.01")
RATIO = Decimal("0.0001")


class TaxAwarePortfolioError(ValueError):
    pass


def build_tax_aware_portfolio(input_path: Path, rule_pack_path: Path, output_path: Path) -> dict[str, Any]:
    plan_input = _load_json(input_path, "tax-aware portfolio input")
    rule_pack = load_tax_aware_investment_rule_pack(rule_pack_path)

    errors: list[str] = []
    data_gaps: list[dict[str, Any]] = []
    _validate_input(plan_input, errors, data_gaps)
    if errors:
        raise TaxAwarePortfolioError("; ".join(errors))

    status = "complete"
    rule = None
    if rule_pack["jurisdiction"] != plan_input["jurisdiction"]:
        status = "blocked_missing_rule"
        data_gaps.append(
            {
                "code": "jurisdiction_not_covered",
                "message": "Rule pack jurisdiction does not match tax-aware portfolio input.",
                "requested_jurisdiction": plan_input["jurisdiction"],
                "rule_pack_jurisdiction": rule_pack["jurisdiction"],
            }
        )
    else:
        rule = _find_rule_for_year(rule_pack, plan_input["tax_year"])
        if rule is None:
            status = "blocked_missing_rule"
            data_gaps.append(
                {
                    "code": "tax_year_not_covered",
                    "message": f"No tax-aware investment rule found for year {plan_input['tax_year']}.",
                    "tax_year": plan_input["tax_year"],
                }
            )

    options: list[dict[str, Any]] = []
    ranking: list[dict[str, Any]] = []
    if rule is not None:
        options = [_evaluate_option(option, plan_input, rule_pack, rule) for option in plan_input["options"]]
        ranking = _ranking(options)
        if data_gaps or any(option["data_gaps"] for option in options):
            status = "partial"

    core = {
        "source": {"type": "tax-aware-portfolio-input-json", "path": str(input_path)},
        "input": {
            "household_id": plan_input["household_id"],
            "as_of_date": plan_input["as_of_date"],
            "tax_year": plan_input["tax_year"],
            "jurisdiction": plan_input["jurisdiction"],
            "base_currency": plan_input["base_currency"],
        },
        "rule_pack": {
            "path": str(rule_pack_path),
            "rule_pack_id": rule_pack["rule_pack_id"],
            "schema_version": rule_pack["schema_version"],
            "status": rule_pack.get("status"),
            "source_refs": rule_pack.get("source_refs", []),
            "limitations": rule_pack.get("limitations", []),
        },
        "options": options,
        "ranking": ranking,
        "summary": {
            "option_count": len(options),
            "best_option_id": ranking[0]["option_id"] if ranking else None,
            "data_gap_count": len(data_gaps) + sum(len(option["data_gaps"]) for option in options),
            "constraint_count": sum(len(option["constraints"]) for option in options),
        },
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
            "Tax-aware portfolio compares explicit portfolio options with a versioned investment tax rule pack. "
            "Expected returns, costs, turnover and loss offsets are declared inputs. The service does not calculate "
            "market forecasts, full tax returns, foreign taxes or investment recommendations."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise TaxAwarePortfolioError(f"Cannot write tax-aware portfolio snapshot: {output_path}") from exc
    return snapshot


def load_tax_aware_investment_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    data = _load_json(rule_pack_path, "tax-aware investment rule pack")
    _validate_rule_pack(data)
    return data


def _evaluate_option(
    option: dict[str, Any],
    plan_input: dict[str, Any],
    rule_pack: dict[str, Any],
    rule: dict[str, Any],
) -> dict[str, Any]:
    regime = option["tax_regime"]
    regime_rule = rule_pack["regimes"][regime]
    losses_available = _money(option.get("available_loss_offset", "0.00"))
    loss_used = Decimal("0.00")
    positions: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    data_gaps: list[dict[str, Any]] = []
    totals = {
        "market_value": Decimal("0.00"),
        "gross_expected_return": Decimal("0.00"),
        "annual_costs": Decimal("0.00"),
        "taxable_realized_gain_before_losses": Decimal("0.00"),
        "taxable_realized_gain_after_losses": Decimal("0.00"),
        "tax_due": Decimal("0.00"),
        "wealth_tax": Decimal("0.00"),
        "deferred_tax_estimate": Decimal("0.00"),
    }
    if regime not in rule_pack["regimes"]:
        data_gaps.append(
            {
                "code": "tax_regime_not_covered",
                "message": "Tax regime is not covered by the rule pack.",
                "tax_regime": regime,
            }
        )
        regime_rule = {"compatible_holding_locations": [], "tax_timing": "realization"}
    else:
        regime_rule = rule_pack["regimes"][regime]

    for index, position in enumerate(option["positions"]):
        holding_location = position["holding_location"]
        if holding_location not in regime_rule["compatible_holding_locations"]:
            constraints.append(
                {
                    "code": "regime_holding_location_incompatible",
                    "message": "Tax regime is not compatible with the declared holding location.",
                    "position_id": position["position_id"],
                    "tax_regime": regime,
                    "holding_location": holding_location,
                }
            )
        tax_category = position["tax_category"]
        if tax_category not in rule["supported_tax_categories"]:
            data_gaps.append(
                {
                    "code": "tax_category_not_covered",
                    "message": "Position tax category is not covered by the rule pack.",
                    "position_id": position["position_id"],
                    "tax_category": tax_category,
                }
            )
            continue
        if tax_category == "government_qualified" and not position.get("tax_category_documented", False):
            data_gaps.append(
                {
                    "code": "government_tax_category_not_documented",
                    "message": "12.5% treatment requires documented upstream classification.",
                    "position_id": position["position_id"],
                }
            )

        market_value = _money(position["market_value"])
        gross_return_rate = _rate(position["expected_gross_return_rate"])
        annual_cost_rate = _rate(position.get("annual_cost_rate", "0"))
        turnover_rate = _rate(position.get("turnover_rate", "0"))
        tax_rate = _rate(rule_pack["tax_rates"][tax_category])
        gross_expected_return = market_value * gross_return_rate
        annual_costs = market_value * annual_cost_rate
        taxable_before_losses = gross_expected_return if regime_rule["tax_timing"] == "annual_result" else gross_expected_return * turnover_rate
        taxable_before_losses = max(Decimal("0.00"), taxable_before_losses)
        offset = min(losses_available - loss_used, taxable_before_losses)
        loss_used += offset
        taxable_after_losses = taxable_before_losses - offset
        tax_due = taxable_after_losses * tax_rate
        unrealized_gain = max(Decimal("0.00"), gross_expected_return - taxable_before_losses)
        deferred_tax = unrealized_gain * tax_rate
        wealth_tax = market_value * _wealth_tax_rate(rule_pack, holding_location)

        totals["market_value"] += market_value
        totals["gross_expected_return"] += gross_expected_return
        totals["annual_costs"] += annual_costs
        totals["taxable_realized_gain_before_losses"] += taxable_before_losses
        totals["taxable_realized_gain_after_losses"] += taxable_after_losses
        totals["tax_due"] += tax_due
        totals["wealth_tax"] += wealth_tax
        totals["deferred_tax_estimate"] += deferred_tax

        positions.append(
            {
                "position_id": position["position_id"],
                "label": position["label"],
                "tax_category": tax_category,
                "holding_location": holding_location,
                "market_value": _format_money(market_value),
                "expected_gross_return_rate": str(gross_return_rate),
                "turnover_rate": str(turnover_rate),
                "gross_expected_return": _format_money(gross_expected_return),
                "annual_costs": _format_money(annual_costs),
                "taxable_realized_gain_before_losses": _format_money(taxable_before_losses),
                "loss_offset_used": _format_money(offset),
                "taxable_realized_gain_after_losses": _format_money(taxable_after_losses),
                "tax_rate": str(tax_rate),
                "tax_due": _format_money(tax_due),
                "wealth_tax": _format_money(wealth_tax),
                "deferred_tax_estimate": _format_money(deferred_tax),
            }
        )

    net_return = totals["gross_expected_return"] - totals["annual_costs"] - totals["tax_due"] - totals["wealth_tax"]
    fiscal_drag = totals["tax_due"] + totals["wealth_tax"]
    net_return_rate = Decimal("0.00") if totals["market_value"] == Decimal("0.00") else net_return / totals["market_value"]
    return {
        "option_id": option["option_id"],
        "label": option["label"],
        "tax_regime": regime,
        "positions": positions,
        "totals": {
            "market_value": _format_money(totals["market_value"]),
            "gross_expected_return": _format_money(totals["gross_expected_return"]),
            "annual_costs": _format_money(totals["annual_costs"]),
            "taxable_realized_gain_before_losses": _format_money(totals["taxable_realized_gain_before_losses"]),
            "available_loss_offset": _format_money(losses_available),
            "loss_offset_used": _format_money(loss_used),
            "taxable_realized_gain_after_losses": _format_money(totals["taxable_realized_gain_after_losses"]),
            "tax_due": _format_money(totals["tax_due"]),
            "wealth_tax": _format_money(totals["wealth_tax"]),
            "fiscal_drag": _format_money(fiscal_drag),
            "deferred_tax_estimate": _format_money(totals["deferred_tax_estimate"]),
            "net_expected_return": _format_money(net_return),
            "net_expected_return_rate": str(net_return_rate.quantize(RATIO, rounding=ROUND_HALF_UP)),
        },
        "constraints": constraints,
        "data_gaps": data_gaps,
    }


def _validate_input(data: dict[str, Any], errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if data.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append(f"Unsupported tax-aware portfolio input schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported tax-aware portfolio input record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_string(data, "as_of_date", errors)
    if not isinstance(data.get("tax_year"), int):
        errors.append("tax_year must be an integer")
    _required_string(data, "jurisdiction", errors)
    _required_string(data, "base_currency", errors)
    options = data.get("options")
    if not isinstance(options, list) or not options:
        errors.append("options must contain at least one option")
        return
    seen: set[str] = set()
    for index, option in enumerate(options):
        if not isinstance(option, dict):
            errors.append(f"options[{index}] must be an object")
            continue
        option_id = _required_string(option, "option_id", errors, prefix=f"options[{index}].")
        if option_id:
            if option_id in seen:
                errors.append(f"Duplicate option_id: {option_id}")
            seen.add(option_id)
        _required_string(option, "label", errors, prefix=f"options[{index}].")
        _required_string(option, "tax_regime", errors, prefix=f"options[{index}].")
        _non_negative_money(option.get("available_loss_offset", "0.00"), f"options[{index}].available_loss_offset", errors)
        positions = option.get("positions")
        if not isinstance(positions, list) or not positions:
            errors.append(f"options[{index}].positions must contain at least one position")
            continue
        for position_index, position in enumerate(positions):
            prefix = f"options[{index}].positions[{position_index}]."
            if not isinstance(position, dict):
                errors.append(f"{prefix[:-1]} must be an object")
                continue
            _required_string(position, "position_id", errors, prefix=prefix)
            _required_string(position, "label", errors, prefix=prefix)
            _required_string(position, "tax_category", errors, prefix=prefix)
            _required_string(position, "holding_location", errors, prefix=prefix)
            _non_negative_money(position.get("market_value"), f"{prefix}market_value", errors)
            _ratio_or_error(position.get("expected_gross_return_rate"), f"{prefix}expected_gross_return_rate", errors)
            _ratio_or_error(position.get("annual_cost_rate", "0"), f"{prefix}annual_cost_rate", errors)
            _ratio_or_error(position.get("turnover_rate", "0"), f"{prefix}turnover_rate", errors)
            if "tax_category_documented" in position and not isinstance(position["tax_category_documented"], bool):
                errors.append(f"{prefix}tax_category_documented must be a boolean")
    _validate_declared_gaps(data.get("data_gaps", []), errors, data_gaps)


def _validate_rule_pack(data: dict[str, Any]) -> None:
    required = ("schema_version", "rule_pack_id", "jurisdiction", "currency", "tax_rates", "wealth_taxes", "regimes", "rules")
    for field in required:
        if field not in data:
            raise TaxAwarePortfolioError(f"Rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise TaxAwarePortfolioError(f"Unsupported rule pack schema: {data['schema_version']}")
    for rate in data["tax_rates"].values():
        _rate(rate)
    for tax in data["wealth_taxes"].values():
        _rate(tax["rate"])
    if not isinstance(data["rules"], list) or not data["rules"]:
        raise TaxAwarePortfolioError("Rule pack must contain at least one rule")
    for rule in data["rules"]:
        for field in ("rule_id", "valid_from", "valid_to", "supported_tax_categories", "supported_holding_locations"):
            if field not in rule:
                raise TaxAwarePortfolioError(f"Tax-aware investment rule missing field: {field}")


def _find_rule_for_year(rule_pack: dict[str, Any], tax_year: int) -> dict[str, Any] | None:
    target = f"{tax_year:04d}"
    for rule in rule_pack["rules"]:
        valid_to = rule["valid_to"][:4] if rule["valid_to"] is not None else "9999"
        if rule["valid_from"][:4] <= target <= valid_to:
            return rule
    return None


def _wealth_tax_rate(rule_pack: dict[str, Any], holding_location: str) -> Decimal:
    for tax_rule in rule_pack["wealth_taxes"].values():
        if tax_rule["applies_to_holding_location"] == holding_location:
            return _rate(tax_rule["rate"])
    return Decimal("0.0000")


def _ranking(options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        options,
        key=lambda option: (
            _money(option["totals"]["net_expected_return"]),
            _rate(option["totals"]["net_expected_return_rate"]),
            option["option_id"],
        ),
        reverse=True,
    )
    return [
        {
            "rank": index + 1,
            "option_id": option["option_id"],
            "net_expected_return": option["totals"]["net_expected_return"],
            "net_expected_return_rate": option["totals"]["net_expected_return_rate"],
            "fiscal_drag": option["totals"]["fiscal_drag"],
            "constraint_count": len(option["constraints"]),
        }
        for index, option in enumerate(ranked)
    ]


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TaxAwarePortfolioError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TaxAwarePortfolioError(f"Invalid JSON in {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise TaxAwarePortfolioError(f"{label} must contain a JSON object")
    return data


def _required_string(data: dict[str, Any], field: str, errors: list[str], prefix: str = "") -> str | None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{field} must be a non-empty string")
        return None
    return value


def _non_negative_money(value: Any, label: str, errors: list[str]) -> None:
    try:
        parsed = _money(value)
    except TaxAwarePortfolioError:
        errors.append(f"{label} must be a money value")
        return
    if parsed < Decimal("0.00"):
        errors.append(f"{label} must be greater than or equal to zero")


def _ratio_or_error(value: Any, label: str, errors: list[str]) -> None:
    try:
        parsed = _rate(value)
    except TaxAwarePortfolioError:
        errors.append(f"{label} must be a decimal rate")
        return
    if parsed < Decimal("0") or parsed > Decimal("1"):
        errors.append(f"{label} must be between 0 and 1")


def _validate_declared_gaps(raw: Any, errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if raw in (None, ""):
        return
    if not isinstance(raw, list):
        errors.append("data_gaps must be a list")
        return
    for index, gap in enumerate(raw):
        if not isinstance(gap, dict):
            errors.append(f"data_gaps[{index}] must be an object")
            continue
        code = gap.get("code")
        message = gap.get("message")
        if not isinstance(code, str) or not code.strip():
            errors.append(f"data_gaps[{index}].code must be a non-empty string")
        if not isinstance(message, str) or not message.strip():
            errors.append(f"data_gaps[{index}].message must be a non-empty string")
        if isinstance(code, str) and isinstance(message, str):
            data_gaps.append(gap)


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(CENT)
    except (InvalidOperation, TypeError) as exc:
        raise TaxAwarePortfolioError(f"Invalid money value: {value}") from exc


def _rate(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(RATIO)
    except (InvalidOperation, TypeError) as exc:
        raise TaxAwarePortfolioError(f"Invalid rate value: {value}") from exc


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _content_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _semantic_core(core: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(core))
    result["source"]["path"] = "<input>"
    result["rule_pack"]["path"] = "<rule-pack>"
    return result
