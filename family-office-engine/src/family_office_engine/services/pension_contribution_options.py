import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "pension-contribution-options/v1"
INPUT_SCHEMA_VERSION = "pension-contribution-input/v1"
INPUT_RECORD_TYPE = "PensionContributionInput"
RULE_PACK_SCHEMA_VERSION = "pension-contribution-rule-pack/v1"
SNAPSHOT_RECORD_TYPE = "PensionContributionOptionsSnapshot"
CENT = Decimal("0.01")
RATIO = Decimal("0.0001")


class PensionContributionOptionsError(ValueError):
    pass


def validate_pension_contribution_input(data: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[str] = []
    data_gaps: list[dict[str, Any]] = []
    _validate_input(data, errors, data_gaps)
    if errors:
        raise PensionContributionOptionsError("; ".join(errors))
    return data_gaps


def build_pension_contribution_options(
    input_path: Path,
    rule_pack_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    plan_input = _load_json(input_path, "pension contribution input")
    rule_pack = load_pension_contribution_rule_pack(rule_pack_path)

    errors: list[str] = []
    data_gaps: list[dict[str, Any]] = []
    _validate_input(plan_input, errors, data_gaps)
    if errors:
        raise PensionContributionOptionsError("; ".join(errors))

    status = "complete"
    rule = None
    if rule_pack["jurisdiction"] != plan_input["jurisdiction"]:
        status = "blocked_missing_rule"
        data_gaps.append(
            {
                "code": "jurisdiction_not_covered",
                "message": "Rule pack jurisdiction does not match pension contribution input.",
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
                    "message": f"No pension contribution rule found for year {plan_input['tax_year']}.",
                    "tax_year": plan_input["tax_year"],
                }
            )

    options: list[dict[str, Any]] = []
    ranking: list[dict[str, Any]] = []
    if rule is not None:
        options = [_evaluate_option(option, plan_input, rule) for option in plan_input["options"]]
        ranking = _ranking(options)
        if data_gaps or any(option["data_gaps"] for option in options):
            status = "partial"

    core = {
        "source": {"type": "pension-contribution-input-json", "path": str(input_path)},
        "input": {
            "household_id": plan_input["household_id"],
            "as_of_date": plan_input["as_of_date"],
            "tax_year": plan_input["tax_year"],
            "jurisdiction": plan_input["jurisdiction"],
            "marginal_tax_rate": plan_input["marginal_tax_rate"],
            "already_deducted_contributions": _format_money(_money(plan_input["already_deducted_contributions"])),
            "first_employment_extra_deduction_room": _format_money(
                _money(plan_input.get("first_employment_extra_deduction_room", "0.00"))
            ),
            "available_liquidity": _optional_money_string(plan_input.get("available_liquidity")),
            "minimum_liquidity_after_contributions": _optional_money_string(
                plan_input.get("minimum_liquidity_after_contributions")
            ),
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
            "Pension contribution options compare explicit contribution choices with a versioned deduction rule pack. "
            "Tax benefit uses only the declared marginal tax rate. The service does not calculate full IRPEF, "
            "fund returns, legal advice or investment recommendations."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise PensionContributionOptionsError(f"Cannot write pension contribution options snapshot: {output_path}") from exc
    return snapshot


def load_pension_contribution_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    data = _load_json(rule_pack_path, "pension contribution rule pack")
    _validate_rule_pack(data)
    return data


def _evaluate_option(option: dict[str, Any], plan_input: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    employee = _money(option.get("employee_contribution", "0.00"))
    employer = _money(option.get("employer_contribution", "0.00"))
    tfr = _money(option.get("tfr_transfer", "0.00"))
    already_deducted = _money(plan_input["already_deducted_contributions"])
    ordinary_limit = _money(rule["ordinary_annual_deduction_limit"])
    annual_extra_limit = _money(rule["first_employment"]["annual_extra_deduction_limit"])
    declared_extra_room = _money(plan_input.get("first_employment_extra_deduction_room", "0.00"))
    extra_room = min(declared_extra_room, annual_extra_limit)
    ordinary_room = max(Decimal("0.00"), ordinary_limit - already_deducted)
    marginal_rate = _rate(plan_input["marginal_tax_rate"])
    opportunity_rate = _rate(option.get("opportunity_cost_rate", "0"))
    horizon_years = option.get("horizon_years", 1)
    deductible_candidate = employee + employer
    ordinary_deductible = min(deductible_candidate, ordinary_room)
    extra_deductible = min(max(Decimal("0.00"), deductible_candidate - ordinary_deductible), extra_room)
    deductible = ordinary_deductible + extra_deductible
    non_deductible = max(Decimal("0.00"), deductible_candidate - deductible)
    tax_benefit = deductible * marginal_rate
    liquidity_outflow = employee + tfr
    opportunity_cost = liquidity_outflow * opportunity_rate * Decimal(str(horizon_years))
    net_value = tax_benefit + employer - opportunity_cost
    constraints: list[dict[str, Any]] = []
    data_gaps: list[dict[str, Any]] = []

    if non_deductible > Decimal("0.00"):
        constraints.append(
            {
                "code": "deduction_limit_exceeded",
                "message": "Part of employee/employer contributions is above the available deduction room.",
                "non_deductible_amount": _format_money(non_deductible),
            }
        )
    if tfr > Decimal("0.00"):
        constraints.append(
            {
                "code": "tfr_transfer_locked",
                "message": "TFR transfer is tracked as locked pension funding, not as immediate deductible contribution.",
                "tfr_transfer": _format_money(tfr),
            }
        )
    available = _optional_money(plan_input.get("available_liquidity"))
    minimum = _optional_money(plan_input.get("minimum_liquidity_after_contributions"))
    liquidity_after = None
    if available is not None:
        liquidity_after = available - liquidity_outflow
        if minimum is not None and liquidity_after < minimum:
            constraints.append(
                {
                    "code": "liquidity_floor_breached",
                    "message": "Liquidity after employee contribution and TFR transfer is below the declared floor.",
                    "liquidity_after": _format_money(liquidity_after),
                    "minimum_liquidity": _format_money(minimum),
                }
            )
    elif liquidity_outflow > Decimal("0.00"):
        data_gaps.append(
            {
                "code": "available_liquidity_not_declared",
                "message": "Available liquidity was not declared, so liquidity impact cannot be checked.",
            }
        )

    return {
        "option_id": option["option_id"],
        "label": option["label"],
        "contributions": {
            "employee": _format_money(employee),
            "employer": _format_money(employer),
            "tfr_transfer": _format_money(tfr),
            "deductible_candidate": _format_money(deductible_candidate),
            "ordinary_deductible": _format_money(ordinary_deductible),
            "first_employment_extra_deductible": _format_money(extra_deductible),
            "deductible_total": _format_money(deductible),
            "non_deductible": _format_money(non_deductible),
        },
        "estimated_tax_benefit": {
            "marginal_tax_rate": str(marginal_rate),
            "amount": _format_money(tax_benefit),
            "method": "deductible_total * declared_marginal_tax_rate",
        },
        "liquidity": {
            "immediate_outflow": _format_money(liquidity_outflow),
            "liquidity_after": None if liquidity_after is None else _format_money(liquidity_after),
        },
        "opportunity_cost": {
            "rate": str(opportunity_rate),
            "horizon_years": horizon_years,
            "amount": _format_money(opportunity_cost),
        },
        "net_estimated_value": _format_money(net_value),
        "constraints": constraints,
        "data_gaps": data_gaps,
    }


def _validate_input(data: dict[str, Any], errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if data.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append(f"Unsupported pension contribution input schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported pension contribution input record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_string(data, "as_of_date", errors)
    if not isinstance(data.get("tax_year"), int):
        errors.append("tax_year must be an integer")
    _required_string(data, "jurisdiction", errors)
    _ratio_or_error(data.get("marginal_tax_rate"), "marginal_tax_rate", errors)
    _non_negative_money(data.get("already_deducted_contributions"), "already_deducted_contributions", errors)
    _optional_non_negative_money(data.get("first_employment_extra_deduction_room"), "first_employment_extra_deduction_room", errors)
    _optional_non_negative_money(data.get("available_liquidity"), "available_liquidity", errors)
    _optional_non_negative_money(
        data.get("minimum_liquidity_after_contributions"),
        "minimum_liquidity_after_contributions",
        errors,
    )
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
        for field in ("employee_contribution", "employer_contribution", "tfr_transfer"):
            _non_negative_money(option.get(field, "0.00"), f"options[{index}].{field}", errors)
        _ratio_or_error(option.get("opportunity_cost_rate", "0"), f"options[{index}].opportunity_cost_rate", errors)
        horizon = option.get("horizon_years", 1)
        if not isinstance(horizon, int) or horizon < 0:
            errors.append(f"options[{index}].horizon_years must be a non-negative integer")
    _validate_declared_gaps(data.get("data_gaps", []), errors, data_gaps)


def _validate_rule_pack(data: dict[str, Any]) -> None:
    required = ("schema_version", "rule_pack_id", "jurisdiction", "currency", "rules")
    for field in required:
        if field not in data:
            raise PensionContributionOptionsError(f"Rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise PensionContributionOptionsError(f"Unsupported rule pack schema: {data['schema_version']}")
    if not isinstance(data["rules"], list) or not data["rules"]:
        raise PensionContributionOptionsError("Rule pack must contain at least one rule")
    for rule in data["rules"]:
        for field in ("rule_id", "valid_from", "valid_to", "ordinary_annual_deduction_limit", "first_employment"):
            if field not in rule:
                raise PensionContributionOptionsError(f"Pension contribution rule missing field: {field}")
        _money(rule["ordinary_annual_deduction_limit"])
        first_employment = rule["first_employment"]
        if not isinstance(first_employment, dict):
            raise PensionContributionOptionsError("first_employment must be an object")
        _money(first_employment.get("first_five_years_reference_amount"))
        _money(first_employment.get("annual_extra_deduction_limit"))


def _find_rule_for_year(rule_pack: dict[str, Any], tax_year: int) -> dict[str, Any] | None:
    target = f"{tax_year:04d}"
    for rule in rule_pack["rules"]:
        valid_to = rule["valid_to"][:4] if rule["valid_to"] is not None else "9999"
        if rule["valid_from"][:4] <= target <= valid_to:
            return rule
    return None


def _ranking(options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        options,
        key=lambda option: (
            _money(option["net_estimated_value"]),
            _money(option["estimated_tax_benefit"]["amount"]),
            option["option_id"],
        ),
        reverse=True,
    )
    return [
        {
            "rank": index + 1,
            "option_id": option["option_id"],
            "net_estimated_value": option["net_estimated_value"],
            "estimated_tax_benefit": option["estimated_tax_benefit"]["amount"],
            "constraint_count": len(option["constraints"]),
        }
        for index, option in enumerate(ranked)
    ]


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PensionContributionOptionsError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PensionContributionOptionsError(f"Invalid JSON in {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise PensionContributionOptionsError(f"{label} must contain a JSON object")
    return data


def _required_string(data: dict[str, Any], field: str, errors: list[str], prefix: str = "") -> str | None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{field} must be a non-empty string")
        return None
    return value


def _non_negative_money(value: Any, label: str, errors: list[str]) -> None:
    parsed = _optional_money_or_error(value, label, errors)
    if parsed is not None and parsed < Decimal("0.00"):
        errors.append(f"{label} must be greater than or equal to zero")


def _optional_non_negative_money(value: Any, label: str, errors: list[str]) -> None:
    if value in (None, ""):
        return
    _non_negative_money(value, label, errors)


def _ratio_or_error(value: Any, label: str, errors: list[str]) -> None:
    parsed = _optional_rate_or_error(value, label, errors)
    if parsed is not None and (parsed < Decimal("0") or parsed > Decimal("1")):
        errors.append(f"{label} must be between 0 and 1")


def _optional_money_or_error(value: Any, label: str, errors: list[str]) -> Decimal | None:
    try:
        return _money(value)
    except PensionContributionOptionsError:
        errors.append(f"{label} must be a money value")
        return None


def _optional_rate_or_error(value: Any, label: str, errors: list[str]) -> Decimal | None:
    try:
        return _rate(value)
    except PensionContributionOptionsError:
        errors.append(f"{label} must be a decimal rate")
        return None


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


def _optional_money(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    return _money(value)


def _optional_money_string(value: Any) -> str | None:
    parsed = _optional_money(value)
    return None if parsed is None else _format_money(parsed)


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(CENT)
    except (InvalidOperation, TypeError) as exc:
        raise PensionContributionOptionsError(f"Invalid money value: {value}") from exc


def _rate(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(RATIO)
    except (InvalidOperation, TypeError) as exc:
        raise PensionContributionOptionsError(f"Invalid rate value: {value}") from exc


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
