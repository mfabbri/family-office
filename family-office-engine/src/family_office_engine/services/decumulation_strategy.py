import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "decumulation-strategy/v1"
INPUT_SCHEMA_VERSION = "decumulation-policy-set/v1"
INPUT_RECORD_TYPE = "DecumulationPolicySet"
SNAPSHOT_RECORD_TYPE = "DecumulationStrategySnapshot"
NET_WORTH_SCHEMA_VERSION = "net-worth/v1"
LIQUIDITY_PLAN_SCHEMA_VERSION = "liquidity-plan/v1"
PENSION_INCOME_SCHEMA_VERSION = "pension-income/v1"
RITA_OPTIONS_SCHEMA_VERSION = "rita-options/v1"
CENT = Decimal("0.01")
RATIO = Decimal("0.0001")


class DecumulationStrategyError(ValueError):
    pass


def build_decumulation_strategy(
    input_path: Path,
    output_path: Path,
    *,
    net_worth_snapshot_path: Path | None = None,
    liquidity_plan_snapshot_path: Path | None = None,
    pension_income_snapshot_path: Path | None = None,
    rita_options_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    policy_set = _load_json(input_path, "decumulation policy set")
    net_worth = _load_optional_snapshot(net_worth_snapshot_path, "net worth", NET_WORTH_SCHEMA_VERSION)
    liquidity_plan = _load_optional_snapshot(liquidity_plan_snapshot_path, "liquidity plan", LIQUIDITY_PLAN_SCHEMA_VERSION)
    pension_income = _load_optional_snapshot(
        pension_income_snapshot_path,
        "pension income",
        PENSION_INCOME_SCHEMA_VERSION,
    )
    rita_options = _load_optional_snapshot(rita_options_snapshot_path, "rita options", RITA_OPTIONS_SCHEMA_VERSION)

    errors: list[str] = []
    data_gaps: list[dict[str, Any]] = []
    _validate_input(policy_set, errors, data_gaps)
    if errors:
        raise DecumulationStrategyError("; ".join(errors))

    household = {
        "household_id": policy_set["household_id"],
        "as_of_date": policy_set["as_of_date"],
        "current_age": policy_set["current_age"],
        "net_worth_snapshot_path": str(net_worth_snapshot_path) if net_worth_snapshot_path else None,
        "liquidity_plan_snapshot_path": str(liquidity_plan_snapshot_path) if liquidity_plan_snapshot_path else None,
        "pension_income_snapshot_path": str(pension_income_snapshot_path) if pension_income_snapshot_path else None,
        "rita_options_snapshot_path": str(rita_options_snapshot_path) if rita_options_snapshot_path else None,
    }
    base_currency = policy_set["base_currency"]
    asset_pool = _asset_pool(net_worth, liquidity_plan, base_currency, data_gaps)
    pension_gross = _pension_gross_annual(pension_income, data_gaps)
    rita_bridge = _rita_bridge(rita_options, data_gaps)

    policies = [
        _simulate_policy(policy, policy_set["current_age"], base_currency, asset_pool, pension_gross, rita_bridge)
        for policy in policy_set["policies"]
    ]
    ranking = _ranking(policies)
    summary = {
        "policy_count": len(policies),
        "complete_policy_count": sum(1 for policy in policies if policy["status"] == "complete"),
        "best_ranked_policy_id": ranking[0]["policy_id"] if ranking else None,
        "data_gap_count": len(data_gaps) + sum(len(policy["data_gaps"]) for policy in policies),
    }
    strategy_core = {
        "source": {"type": "decumulation-policy-set-json", "path": str(input_path)},
        "household": household,
        "base_currency": base_currency,
        "asset_pool": _public_asset_pool(asset_pool, base_currency),
        "policies": policies,
        "ranking": ranking,
        "summary": summary,
        "data_gaps": data_gaps,
    }
    status = "complete" if policies and summary["data_gap_count"] == 0 else "partial" if policies else "blocked_missing_inputs"
    if net_worth is None:
        status = "blocked_missing_inputs"
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": status,
        **strategy_core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(_semantic_strategy_core(strategy_core)),
        },
        "notes": (
            "Decumulation strategy V1 compares explicit withdrawal policies with deterministic cashflows. Net metrics "
            "use only rates declared in the policy input. It does not calculate statutory taxes, FX conversion, "
            "portfolio optimization or investment recommendations."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise DecumulationStrategyError(f"Cannot write decumulation strategy snapshot: {output_path}") from exc
    return snapshot


def _validate_input(data: dict[str, Any], errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if data.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append(f"Unsupported decumulation policy set schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported decumulation policy set record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_string(data, "as_of_date", errors)
    _required_string(data, "base_currency", errors)
    if isinstance(data.get("base_currency"), str) and (
        len(data["base_currency"]) != 3 or data["base_currency"].upper() != data["base_currency"]
    ):
        errors.append("base_currency must be an ISO-4217 uppercase code")
    current_age = data.get("current_age")
    if not isinstance(current_age, int) or current_age < 0:
        errors.append("current_age must be a non-negative integer")
    policies = data.get("policies")
    if not isinstance(policies, list) or not policies:
        errors.append("policies must contain at least one policy")
        return
    policy_ids: set[str] = set()
    for index, policy in enumerate(policies):
        if not isinstance(policy, dict):
            errors.append(f"policies[{index}] must be an object")
            continue
        policy_id = _required_string(policy, "policy_id", errors, prefix=f"policies[{index}].")
        if policy_id:
            if policy_id in policy_ids:
                errors.append(f"Duplicate policy_id: {policy_id}")
            policy_ids.add(policy_id)
        _required_string(policy, "label", errors, prefix=f"policies[{index}].")
        retirement_age = _required_int(policy, "retirement_age", errors, prefix=f"policies[{index}].")
        end_age = _required_int(policy, "end_age", errors, prefix=f"policies[{index}].")
        if isinstance(retirement_age, int) and isinstance(current_age, int) and retirement_age < current_age:
            errors.append(f"policies[{index}].retirement_age cannot be before current_age")
        if isinstance(end_age, int) and isinstance(retirement_age, int) and end_age < retirement_age:
            errors.append(f"policies[{index}].end_age cannot be before retirement_age")
        _positive_decimal(policy.get("annual_spending_need"), f"policies[{index}].annual_spending_need", errors)
        _non_negative_decimal(policy.get("cash_buffer_target"), f"policies[{index}].cash_buffer_target", errors)
        _ratio_decimal(policy.get("withdrawal_tax_rate", "0"), f"policies[{index}].withdrawal_tax_rate", errors)
        _ratio_decimal(policy.get("pension_tax_rate", "0"), f"policies[{index}].pension_tax_rate", errors)
        _ratio_decimal(policy.get("rita_tax_rate", "0"), f"policies[{index}].rita_tax_rate", errors)
        if not isinstance(policy.get("withdrawal_order"), list) or not policy.get("withdrawal_order"):
            errors.append(f"policies[{index}].withdrawal_order must contain at least one asset id")
        if not isinstance(policy.get("annual_return_sequence"), list) or not policy.get("annual_return_sequence"):
            errors.append(f"policies[{index}].annual_return_sequence must contain at least one decimal return")
        else:
            for seq_index, value in enumerate(policy["annual_return_sequence"]):
                _decimal_or_error(value, f"policies[{index}].annual_return_sequence[{seq_index}]", errors)
    _validate_declared_gaps(data.get("data_gaps", []), errors, data_gaps)


def _asset_pool(
    net_worth: dict[str, Any] | None,
    liquidity_plan: dict[str, Any] | None,
    base_currency: str,
    data_gaps: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if net_worth is None:
        data_gaps.append({"code": "missing_net_worth_snapshot", "message": "Net worth snapshot is not available."})
        return {}
    components = net_worth.get("components")
    if not isinstance(components, list):
        raise DecumulationStrategyError("Net worth snapshot components must be a list")
    liquidity_by_asset = _liquidity_by_asset(liquidity_plan, data_gaps)
    pool: dict[str, dict[str, Any]] = {}
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            raise DecumulationStrategyError(f"net_worth.components[{index}] must be an object")
        if component.get("type") != "asset":
            continue
        asset_id = _asset_id(component, index)
        value = _decimal(component.get("value"), f"net_worth.components[{index}].value")
        currency = str(component.get("currency") or base_currency)
        liquidity = liquidity_by_asset.get(asset_id)
        bucket = liquidity.get("bucket") if isinstance(liquidity, dict) else "unclassified"
        if currency != base_currency:
            data_gaps.append(
                {
                    "code": "foreign_currency_asset",
                    "asset_id": asset_id,
                    "currency": currency,
                    "message": "Asset currency differs from base currency; no FX conversion is performed.",
                }
            )
            continue
        if bucket in {"restricted", "unclassified"}:
            data_gaps.append(
                {
                    "code": "asset_not_decumulable",
                    "asset_id": asset_id,
                    "bucket": bucket,
                    "message": "Asset is not available for decumulation under the liquidity plan.",
                }
            )
            continue
        pool[asset_id] = {
            "asset_id": asset_id,
            "label": component.get("label") or asset_id,
            "asset_class": component.get("asset_class"),
            "bucket": bucket,
            "starting_value": value,
        }
    return pool


def _liquidity_by_asset(
    liquidity_plan: dict[str, Any] | None,
    data_gaps: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if liquidity_plan is None:
        data_gaps.append({"code": "missing_liquidity_plan_snapshot", "message": "Liquidity plan snapshot is not available."})
        return {}
    assignments = liquidity_plan.get("asset_assignments")
    if not isinstance(assignments, list):
        raise DecumulationStrategyError("Liquidity plan asset_assignments must be a list")
    return {
        assignment["asset_id"]: assignment
        for assignment in assignments
        if isinstance(assignment, dict) and isinstance(assignment.get("asset_id"), str)
    }


def _pension_gross_annual(snapshot: dict[str, Any] | None, data_gaps: list[dict[str, Any]]) -> Decimal:
    if snapshot is None:
        data_gaps.append({"code": "missing_pension_income_snapshot", "message": "Pension income snapshot is not available."})
        return Decimal("0.00")
    summary = snapshot.get("summary") if isinstance(snapshot.get("summary"), dict) else {}
    total = summary.get("gross_annual_recurring_total")
    currency = summary.get("gross_annual_recurring_total_currency")
    if total in (None, ""):
        data_gaps.append(
            {
                "code": "missing_pension_gross_annual_recurring_total",
                "message": "Pension income snapshot does not expose a recurring gross annual total.",
            }
        )
        return Decimal("0.00")
    if currency != "EUR":
        data_gaps.append(
            {
                "code": "unsupported_pension_income_currency",
                "currency": currency,
                "message": "Only EUR recurring pension income is used by decumulation V1.",
            }
        )
        return Decimal("0.00")
    return _decimal(total, "gross_annual_recurring_total")


def _rita_bridge(snapshot: dict[str, Any] | None, data_gaps: list[dict[str, Any]]) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    options = snapshot.get("options")
    if not isinstance(options, list):
        raise DecumulationStrategyError("RITA options snapshot options must be a list")
    complete_options = [option for option in options if isinstance(option, dict) and option.get("gross_monthly_amount") not in (None, "")]
    if not complete_options:
        data_gaps.append({"code": "missing_rita_option_amount", "message": "No RITA option exposes a gross monthly amount."})
        return None
    selected = complete_options[0]
    return {
        "option_id": selected.get("option_id", "option"),
        "gross_monthly_amount": _decimal(selected.get("gross_monthly_amount"), "rita gross_monthly_amount"),
        "duration_months": int(selected.get("duration_months") or 0),
    }


def _simulate_policy(
    policy: dict[str, Any],
    current_age: int,
    base_currency: str,
    asset_pool: dict[str, dict[str, Any]],
    pension_gross_annual: Decimal,
    rita_bridge: dict[str, Any] | None,
) -> dict[str, Any]:
    policy_gaps: list[dict[str, Any]] = []
    balances = {asset_id: asset["starting_value"] for asset_id, asset in asset_pool.items()}
    missing_order_assets = [asset_id for asset_id in policy["withdrawal_order"] if asset_id not in balances]
    for asset_id in missing_order_assets:
        policy_gaps.append(
            {
                "code": "withdrawal_order_asset_unavailable",
                "asset_id": asset_id,
                "message": "Policy withdrawal order references an unavailable asset.",
            }
        )
    ordered_asset_ids = [asset_id for asset_id in policy["withdrawal_order"] if asset_id in balances]
    unordered_asset_ids = [asset_id for asset_id in balances if asset_id not in ordered_asset_ids]
    withdrawal_order = ordered_asset_ids + unordered_asset_ids
    if not withdrawal_order:
        policy_gaps.append({"code": "no_decumulable_assets", "message": "No assets are available for decumulation."})

    annual_spending_need = _decimal(policy["annual_spending_need"], "annual_spending_need")
    cash_buffer_target = _decimal(policy.get("cash_buffer_target", "0"), "cash_buffer_target")
    withdrawal_tax_rate = _decimal(policy.get("withdrawal_tax_rate", "0"), "withdrawal_tax_rate")
    pension_tax_rate = _decimal(policy.get("pension_tax_rate", "0"), "pension_tax_rate")
    rita_tax_rate = _decimal(policy.get("rita_tax_rate", "0"), "rita_tax_rate")
    sequence = [_decimal(value, "annual_return_sequence") for value in policy["annual_return_sequence"]]
    retirement_age = int(policy["retirement_age"])
    end_age = int(policy["end_age"])
    include_rita = bool(policy.get("include_rita", False))

    annual_cashflows: list[dict[str, Any]] = []
    total_net_spending_funded = Decimal("0.00")
    total_shortfall = Decimal("0.00")
    total_gross_withdrawals = Decimal("0.00")
    total_pension_net = Decimal("0.00")
    total_rita_net = Decimal("0.00")
    depletion_age: int | None = None
    shortfall_years = 0
    rita_remaining_months = rita_bridge["duration_months"] if include_rita and rita_bridge else 0
    if include_rita and rita_bridge is None:
        policy_gaps.append({"code": "rita_requested_but_missing", "message": "Policy includes RITA but no RITA option is available."})

    for year_index, age in enumerate(range(current_age, end_age + 1)):
        start_balance = sum(balances.values(), Decimal("0.00"))
        retired = age >= retirement_age
        pension_net = pension_gross_annual * (Decimal("1") - pension_tax_rate) if retired else Decimal("0.00")
        rita_months = min(12, rita_remaining_months) if retired else 0
        rita_gross = (rita_bridge["gross_monthly_amount"] * Decimal(rita_months)) if rita_bridge and rita_months else Decimal("0.00")
        rita_net = rita_gross * (Decimal("1") - rita_tax_rate)
        rita_remaining_months -= rita_months
        need_after_income = max(annual_spending_need - pension_net - rita_net, Decimal("0.00")) if retired else Decimal("0.00")
        gross_needed = _gross_from_net(need_after_income, withdrawal_tax_rate)
        gross_withdrawn = _withdraw_from_assets(balances, withdrawal_order, gross_needed)
        net_from_assets = gross_withdrawn * (Decimal("1") - withdrawal_tax_rate)
        net_funded = min(annual_spending_need, pension_net + rita_net + net_from_assets) if retired else Decimal("0.00")
        shortfall = max(annual_spending_need - pension_net - rita_net - net_from_assets, Decimal("0.00")) if retired else Decimal("0.00")
        if shortfall > 0:
            shortfall_years += 1
            if depletion_age is None:
                depletion_age = age
        if retired:
            total_net_spending_funded += net_funded
            total_shortfall += shortfall
            total_gross_withdrawals += gross_withdrawn
            total_pension_net += pension_net
            total_rita_net += rita_net
        return_rate = sequence[min(year_index, len(sequence) - 1)]
        _apply_return(balances, return_rate)
        end_balance = sum(balances.values(), Decimal("0.00"))
        annual_cashflows.append(
            {
                "age": age,
                "retired": retired,
                "start_balance": _format_money(start_balance),
                "pension_net": _format_money(pension_net),
                "rita_net": _format_money(rita_net),
                "asset_withdrawal_gross": _format_money(gross_withdrawn),
                "asset_withdrawal_net": _format_money(net_from_assets),
                "net_spending_funded": _format_money(net_funded),
                "shortfall": _format_money(shortfall),
                "return_rate": _format_ratio(return_rate),
                "end_balance": _format_money(end_balance),
            }
        )

    final_balance = sum(balances.values(), Decimal("0.00"))
    warnings = _policy_warnings(policy, final_balance, cash_buffer_target, shortfall_years, sequence)
    return {
        "policy_id": policy["policy_id"],
        "label": policy["label"],
        "status": "complete" if not policy_gaps else "partial",
        "parameters": {
            "retirement_age": retirement_age,
            "end_age": end_age,
            "annual_spending_need": _format_money(annual_spending_need),
            "cash_buffer_target": _format_money(cash_buffer_target),
            "include_rita": include_rita,
            "withdrawal_order": withdrawal_order,
            "base_currency": base_currency,
        },
        "metrics": {
            "final_balance": _format_money(final_balance),
            "depletion_age": depletion_age,
            "shortfall_year_count": shortfall_years,
            "total_shortfall": _format_money(total_shortfall),
            "total_net_spending_funded": _format_money(total_net_spending_funded),
            "total_gross_asset_withdrawals": _format_money(total_gross_withdrawals),
            "total_pension_net_used": _format_money(total_pension_net),
            "total_rita_net_used": _format_money(total_rita_net),
            "cash_buffer_target_met_at_end": final_balance >= cash_buffer_target,
        },
        "annual_cashflows": annual_cashflows,
        "warnings": warnings,
        "data_gaps": policy_gaps,
    }


def _withdraw_from_assets(balances: dict[str, Decimal], withdrawal_order: list[str], amount: Decimal) -> Decimal:
    remaining = amount
    withdrawn = Decimal("0.00")
    for asset_id in withdrawal_order:
        if remaining <= 0:
            break
        available = balances.get(asset_id, Decimal("0.00"))
        draw = min(available, remaining)
        balances[asset_id] = available - draw
        remaining -= draw
        withdrawn += draw
    return withdrawn


def _apply_return(balances: dict[str, Decimal], return_rate: Decimal) -> None:
    for asset_id, balance in list(balances.items()):
        balances[asset_id] = max(Decimal("0.00"), balance * (Decimal("1") + return_rate))


def _gross_from_net(net_amount: Decimal, tax_rate: Decimal) -> Decimal:
    if net_amount <= 0:
        return Decimal("0.00")
    denominator = Decimal("1") - tax_rate
    if denominator <= 0:
        raise DecumulationStrategyError("tax rates must be less than 1")
    return net_amount / denominator


def _policy_warnings(
    policy: dict[str, Any],
    final_balance: Decimal,
    cash_buffer_target: Decimal,
    shortfall_years: int,
    sequence: list[Decimal],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if final_balance < cash_buffer_target:
        warnings.append(
            {
                "code": "cash_buffer_below_target",
                "message": "Final balance is below the declared cash buffer target.",
            }
        )
    if shortfall_years:
        warnings.append(
            {
                "code": "spending_shortfall",
                "year_count": shortfall_years,
                "message": "Policy cannot fund the declared net spending need in every retirement year.",
            }
        )
    if any(rate < 0 for rate in sequence):
        warnings.append(
            {
                "code": "negative_return_sequence",
                "message": "Policy includes at least one negative annual return assumption.",
            }
        )
    if int(policy["end_age"]) >= 95:
        warnings.append(
            {
                "code": "longevity_horizon_high",
                "message": "Policy horizon reaches age 95 or later.",
            }
        )
    return warnings


def _ranking(policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_policies = sorted(
        policies,
        key=lambda policy: (
            int(policy["metrics"]["shortfall_year_count"]),
            _decimal(policy["metrics"]["total_shortfall"], "total_shortfall"),
            -_decimal(policy["metrics"]["final_balance"], "final_balance"),
        ),
    )
    return [
        {
            "rank": index + 1,
            "policy_id": policy["policy_id"],
            "label": policy["label"],
            "shortfall_year_count": policy["metrics"]["shortfall_year_count"],
            "final_balance": policy["metrics"]["final_balance"],
        }
        for index, policy in enumerate(sorted_policies)
    ]


def _public_asset_pool(asset_pool: dict[str, dict[str, Any]], base_currency: str) -> dict[str, Any]:
    total = sum((asset["starting_value"] for asset in asset_pool.values()), Decimal("0.00"))
    return {
        "total_starting_value": _format_money(total),
        "currency": base_currency,
        "assets": [
            {
                "asset_id": asset["asset_id"],
                "label": asset["label"],
                "asset_class": asset["asset_class"],
                "bucket": asset["bucket"],
                "starting_value": _format_money(asset["starting_value"]),
            }
            for asset in asset_pool.values()
        ],
    }


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DecumulationStrategyError(f"{label.title()} file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DecumulationStrategyError(f"Invalid JSON in {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise DecumulationStrategyError(f"{label.title()} must contain a JSON object")
    return data


def _load_optional_snapshot(path: Path | None, label: str, expected_schema: str) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    data = _load_json(path, f"{label} snapshot")
    if data.get("schema_version") != expected_schema:
        raise DecumulationStrategyError(f"Unsupported {label} snapshot schema: {data.get('schema_version')}")
    return data


def _validate_declared_gaps(raw_gaps: Any, errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if raw_gaps in (None, ""):
        return
    if not isinstance(raw_gaps, list):
        errors.append("data_gaps must be a list")
        return
    for index, gap in enumerate(raw_gaps):
        if not isinstance(gap, dict):
            errors.append(f"data_gaps[{index}] must be an object")
            continue
        if not gap.get("code"):
            errors.append(f"data_gaps[{index}].code is required")
            continue
        data_gaps.append(gap)


def _required_string(data: dict[str, Any], field: str, errors: list[str], *, prefix: str = "") -> str | None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{field} is required")
        return None
    return value


def _required_int(data: dict[str, Any], field: str, errors: list[str], *, prefix: str = "") -> int | None:
    value = data.get(field)
    if not isinstance(value, int):
        errors.append(f"{prefix}{field} must be an integer")
        return None
    return value


def _positive_decimal(value: Any, label: str, errors: list[str]) -> Decimal | None:
    decimal = _decimal_or_error(value, label, errors)
    if decimal is not None and decimal <= 0:
        errors.append(f"{label} must be positive")
    return decimal


def _non_negative_decimal(value: Any, label: str, errors: list[str]) -> Decimal | None:
    decimal = _decimal_or_error(value, label, errors)
    if decimal is not None and decimal < 0:
        errors.append(f"{label} must be non-negative")
    return decimal


def _ratio_decimal(value: Any, label: str, errors: list[str]) -> Decimal | None:
    decimal = _decimal_or_error(value, label, errors)
    if decimal is not None and (decimal < 0 or decimal >= 1):
        errors.append(f"{label} must be greater than or equal to 0 and less than 1")
    return decimal


def _decimal_or_error(value: Any, label: str, errors: list[str]) -> Decimal | None:
    if value in (None, ""):
        errors.append(f"{label} is required")
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        errors.append(f"{label} must be a decimal")
        return None


def _decimal(value: Any, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise DecumulationStrategyError(f"{label} must be a decimal") from exc


def _asset_id(component: dict[str, Any], index: int) -> str:
    for field in ("asset_id", "id"):
        value = component.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return f"net_worth_asset_{index + 1}"


def _semantic_strategy_core(strategy_core: dict[str, Any]) -> dict[str, Any]:
    semantic = json.loads(json.dumps(strategy_core))
    source = semantic.get("source")
    if isinstance(source, dict):
        source.pop("path", None)
    household = semantic.get("household")
    if isinstance(household, dict):
        household.pop("net_worth_snapshot_path", None)
        household.pop("liquidity_plan_snapshot_path", None)
        household.pop("pension_income_snapshot_path", None)
        household.pop("rita_options_snapshot_path", None)
    return semantic


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT))


def _format_ratio(value: Decimal) -> str:
    return str(value.quantize(RATIO))
