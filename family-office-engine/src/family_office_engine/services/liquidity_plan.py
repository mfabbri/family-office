import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "liquidity-plan/v1"
INPUT_SCHEMA_VERSION = "liquidity-plan-input/v1"
INPUT_RECORD_TYPE = "LiquidityPlanInput"
SNAPSHOT_RECORD_TYPE = "LiquidityPlanSnapshot"
NET_WORTH_SCHEMA_VERSION = "net-worth/v1"
ASSET_AVAILABILITY_SCHEMA_VERSION = "asset-availability/v1"
PLANNING_GOALS_SCHEMA_VERSION = "planning-goals/v1"
CENT = Decimal("0.01")

BUCKETS = ("emergency_reserve", "short_term", "medium_term", "long_term", "restricted")
CURRENT_SPENDING_BLOCKING_CONSTRAINTS = {
    "pension_lock",
    "policy_terms",
    "mortgage_or_lien",
    "co_ownership",
    "sale_process",
    "unknown",
}


class LiquidityPlanError(ValueError):
    pass


def build_liquidity_plan(
    input_path: Path,
    output_path: Path,
    *,
    net_worth_snapshot_path: Path | None = None,
    asset_availability_snapshot_path: Path | None = None,
    planning_goals_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    plan_input = _load_json(input_path, "liquidity plan input")
    net_worth = _load_optional_snapshot(net_worth_snapshot_path, "net worth", NET_WORTH_SCHEMA_VERSION)
    availability = _load_optional_snapshot(
        asset_availability_snapshot_path,
        "asset availability",
        ASSET_AVAILABILITY_SCHEMA_VERSION,
    )
    planning_goals = _load_optional_snapshot(planning_goals_snapshot_path, "planning goals", PLANNING_GOALS_SCHEMA_VERSION)

    errors: list[str] = []
    data_gaps: list[dict[str, Any]] = []
    _validate_input(plan_input, errors, data_gaps)
    if errors:
        raise LiquidityPlanError("; ".join(errors))

    base_currency = plan_input["base_currency"]
    as_of_date = _parse_date(plan_input["as_of_date"], "as_of_date")
    monthly_expenses = _decimal(plan_input["monthly_expenses"], "monthly_expenses")
    reserve_months = _reserve_months(plan_input, planning_goals, data_gaps)
    reserve_target = monthly_expenses * Decimal(reserve_months)
    concentration_threshold = _decimal(plan_input.get("concentration_threshold", "0.50"), "concentration_threshold")

    assignments = _assign_assets(
        net_worth,
        availability,
        base_currency,
        as_of_date,
        concentration_threshold,
        data_gaps,
    )
    buckets = _bucket_summary(assignments)
    funded = buckets["emergency_reserve"]["total_value"]
    reserve = {
        "monthly_expenses": _format_money(monthly_expenses),
        "reserve_months": reserve_months,
        "target_amount": _format_money(reserve_target),
        "funded_amount": _format_money(funded),
        "shortfall": _format_money(max(Decimal("0.00"), reserve_target - funded)),
        "currency": base_currency,
    }
    warnings = _warnings(assignments, reserve_target, concentration_threshold)
    if reserve_target > funded:
        data_gaps.append(
            {
                "code": "emergency_reserve_shortfall",
                "message": "Emergency reserve funded amount is below the declared target.",
                "target_amount": _format_money(reserve_target),
                "funded_amount": _format_money(funded),
                "currency": base_currency,
            }
        )

    plan_core = {
        "source": {
            "type": "liquidity-plan-input-json",
            "path": str(input_path),
        },
        "household": {
            "household_id": plan_input["household_id"],
            "as_of_date": plan_input["as_of_date"],
            "net_worth_snapshot_path": str(net_worth_snapshot_path) if net_worth_snapshot_path else None,
            "asset_availability_snapshot_path": (
                str(asset_availability_snapshot_path) if asset_availability_snapshot_path else None
            ),
            "planning_goals_snapshot_path": str(planning_goals_snapshot_path) if planning_goals_snapshot_path else None,
        },
        "base_currency": base_currency,
        "emergency_reserve": reserve,
        "buckets": {
            bucket: {
                "total_value": _format_money(summary["total_value"]),
                "asset_count": summary["asset_count"],
                "currency": base_currency,
            }
            for bucket, summary in buckets.items()
        },
        "asset_assignments": [_public_assignment(assignment) for assignment in assignments],
        "blocked_current_spending_assets": [
            _public_assignment(assignment) for assignment in assignments if assignment["blocks_current_spending"]
        ],
        "warnings": warnings,
        "data_gaps": data_gaps,
    }
    status = "complete" if not data_gaps else "partial"
    if net_worth is None or availability is None:
        status = "blocked_missing_inputs"
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": status,
        **plan_core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(_semantic_plan_core(plan_core)),
        },
        "notes": (
            "Liquidity plan V1 classifies explicit asset values into liquidity buckets. It does not calculate "
            "returns, taxes, FX conversion, optimization, scoring or investment recommendations."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise LiquidityPlanError(f"Cannot write liquidity plan snapshot: {output_path}") from exc
    return snapshot


def _validate_input(data: dict[str, Any], errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if data.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append(f"Unsupported liquidity plan input schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported liquidity plan input record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_string(data, "as_of_date", errors)
    _required_string(data, "base_currency", errors)
    if isinstance(data.get("base_currency"), str) and (
        len(data["base_currency"]) != 3 or data["base_currency"].upper() != data["base_currency"]
    ):
        errors.append("base_currency must be an ISO-4217 uppercase code")
    monthly_expenses = _optional_decimal(data.get("monthly_expenses"), "monthly_expenses", errors)
    if monthly_expenses is not None and monthly_expenses <= 0:
        errors.append("monthly_expenses must be positive")
    reserve_months = data.get("minimum_reserve_months")
    if reserve_months not in (None, "") and (not isinstance(reserve_months, int) or reserve_months < 0):
        errors.append("minimum_reserve_months must be a non-negative integer")
    concentration = _optional_decimal(data.get("concentration_threshold", "0.50"), "concentration_threshold", errors)
    if concentration is not None and (concentration <= 0 or concentration > 1):
        errors.append("concentration_threshold must be greater than 0 and less than or equal to 1")
    _validate_declared_gaps(data.get("data_gaps", []), errors, data_gaps)


def _assign_assets(
    net_worth: dict[str, Any] | None,
    availability: dict[str, Any] | None,
    base_currency: str,
    as_of_date: date,
    concentration_threshold: Decimal,
    data_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if net_worth is None:
        data_gaps.append({"code": "missing_net_worth_snapshot", "message": "Net worth snapshot is not available."})
        return []
    components = net_worth.get("components")
    if not isinstance(components, list):
        raise LiquidityPlanError("Net worth snapshot components must be a list")
    availability_by_asset = _availability_by_asset(availability, data_gaps)
    assignments: list[dict[str, Any]] = []
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            raise LiquidityPlanError(f"net_worth.components[{index}] must be an object")
        if component.get("type") != "asset":
            continue
        asset_id = _asset_id(component, index)
        value = _decimal(component.get("value"), f"net_worth.components[{index}].value")
        currency = str(component.get("currency") or base_currency)
        classification = availability_by_asset.get(asset_id)
        assignment = _assignment_for_component(component, asset_id, value, currency, classification, base_currency, as_of_date)
        if classification is None:
            data_gaps.append(
                {
                    "code": "missing_asset_availability",
                    "asset_id": asset_id,
                    "message": "Asset has no availability classification and is treated as restricted.",
                }
            )
        if currency != base_currency:
            data_gaps.append(
                {
                    "code": "foreign_currency_asset",
                    "asset_id": asset_id,
                    "currency": currency,
                    "message": "Asset currency differs from base currency; no FX conversion is performed.",
                }
            )
        if assignment["concentration_ratio"] > concentration_threshold:
            assignment["reason_codes"].append("concentration_above_threshold")
        assignments.append(assignment)
    return assignments


def _assignment_for_component(
    component: dict[str, Any],
    asset_id: str,
    value: Decimal,
    currency: str,
    classification: dict[str, Any] | None,
    base_currency: str,
    as_of_date: date,
) -> dict[str, Any]:
    reason_codes: list[str] = []
    blocks_current_spending = False
    if classification is None:
        return {
            "asset_id": asset_id,
            "label": component.get("label") or asset_id,
            "value": value,
            "currency": currency,
            "bucket": "restricted",
            "blocks_current_spending": True,
            "reason_codes": ["missing_availability"],
            "concentration_ratio": Decimal("0"),
        }

    liquidity_tier = classification.get("liquidity_tier")
    constraints = classification.get("constraints") if isinstance(classification.get("constraints"), list) else []
    risk_level = classification.get("risk_level")
    first_available_date = _optional_date(classification.get("first_available_date"))
    blocking_constraints = sorted(set(constraints) & CURRENT_SPENDING_BLOCKING_CONSTRAINTS)
    if blocking_constraints:
        blocks_current_spending = True
        reason_codes.extend(f"blocking_constraint:{constraint}" for constraint in blocking_constraints)
    if currency != base_currency:
        blocks_current_spending = True
        reason_codes.append("foreign_currency_no_fx")

    if liquidity_tier == "immediate" and first_available_date is not None and first_available_date <= as_of_date:
        bucket = "emergency_reserve"
        reason_codes.append("immediate_liquidity")
    elif liquidity_tier in {"short_term", "notice_required"}:
        bucket = "short_term"
        reason_codes.append(f"liquidity_tier:{liquidity_tier}")
    elif liquidity_tier == "locked_until_date" and first_available_date is not None:
        days_until_available = (first_available_date - as_of_date).days
        if days_until_available <= 365:
            bucket = "short_term"
        elif days_until_available <= 1095:
            bucket = "medium_term"
        else:
            bucket = "long_term"
        blocks_current_spending = True
        reason_codes.append("locked_until_date")
    elif liquidity_tier == "illiquid":
        bucket = "restricted"
        blocks_current_spending = True
        reason_codes.append("illiquid")
    else:
        bucket = "restricted"
        blocks_current_spending = True
        reason_codes.append("unknown_liquidity")

    if bucket == "emergency_reserve" and risk_level not in {"low", "medium"}:
        bucket = "short_term"
        blocks_current_spending = True
        reason_codes.append("volatile_not_emergency_reserve")
    if blocks_current_spending and "blocked_for_current_spending" not in reason_codes:
        reason_codes.append("blocked_for_current_spending")

    return {
        "asset_id": asset_id,
        "label": component.get("label") or asset_id,
        "value": value,
        "currency": currency,
        "bucket": bucket if not blocking_constraints else "restricted",
        "blocks_current_spending": blocks_current_spending,
        "reason_codes": reason_codes,
        "concentration_ratio": Decimal("0"),
    }


def _bucket_summary(assignments: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    total = sum((assignment["value"] for assignment in assignments), Decimal("0.00"))
    summaries = {bucket: {"total_value": Decimal("0.00"), "asset_count": 0} for bucket in BUCKETS}
    for assignment in assignments:
        summaries[assignment["bucket"]]["total_value"] += assignment["value"]
        summaries[assignment["bucket"]]["asset_count"] += 1
        assignment["concentration_ratio"] = assignment["value"] / total if total else Decimal("0")
    return summaries


def _warnings(
    assignments: list[dict[str, Any]],
    reserve_target: Decimal,
    concentration_threshold: Decimal,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for assignment in assignments:
        if assignment["blocks_current_spending"]:
            warnings.append(
                {
                    "code": "blocked_current_spending_asset",
                    "asset_id": assignment["asset_id"],
                    "bucket": assignment["bucket"],
                    "message": "Asset is not available for current spending.",
                }
            )
        if assignment["concentration_ratio"] > concentration_threshold:
            warnings.append(
                {
                    "code": "asset_concentration",
                    "asset_id": assignment["asset_id"],
                    "ratio": _format_ratio(assignment["concentration_ratio"]),
                    "threshold": _format_ratio(concentration_threshold),
                    "message": "Single asset concentration is above the declared threshold.",
                }
            )
    emergency_funded = sum(
        (assignment["value"] for assignment in assignments if assignment["bucket"] == "emergency_reserve"),
        Decimal("0.00"),
    )
    if reserve_target > emergency_funded:
        warnings.append(
            {
                "code": "emergency_reserve_shortfall",
                "message": "Emergency reserve is below the declared target.",
            }
        )
    return warnings


def _availability_by_asset(
    availability: dict[str, Any] | None,
    data_gaps: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if availability is None:
        data_gaps.append(
            {"code": "missing_asset_availability_snapshot", "message": "Asset availability snapshot is not available."}
        )
        return {}
    classifications = availability.get("classifications")
    if not isinstance(classifications, list):
        raise LiquidityPlanError("Asset availability snapshot classifications must be a list")
    by_asset: dict[str, dict[str, Any]] = {}
    for index, classification in enumerate(classifications):
        if not isinstance(classification, dict):
            raise LiquidityPlanError(f"asset_availability.classifications[{index}] must be an object")
        asset_id = classification.get("asset_id")
        if isinstance(asset_id, str) and asset_id:
            by_asset[asset_id] = classification
    return by_asset


def _reserve_months(
    plan_input: dict[str, Any],
    planning_goals: dict[str, Any] | None,
    data_gaps: list[dict[str, Any]],
) -> int:
    if planning_goals is not None:
        liquidity_policy = planning_goals.get("liquidity_policy")
        if isinstance(liquidity_policy, dict) and isinstance(liquidity_policy.get("minimum_reserve_months"), int):
            return liquidity_policy["minimum_reserve_months"]
        data_gaps.append(
            {
                "code": "missing_planning_goals_reserve_months",
                "message": "Planning goals snapshot does not declare minimum reserve months.",
            }
        )
    elif plan_input.get("minimum_reserve_months") in (None, ""):
        data_gaps.append(
            {
                "code": "missing_planning_goals_snapshot",
                "message": "Planning goals snapshot is not available; input minimum_reserve_months is used if present.",
            }
        )
    reserve_months = plan_input.get("minimum_reserve_months")
    return reserve_months if isinstance(reserve_months, int) else 0


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LiquidityPlanError(f"{label.title()} file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LiquidityPlanError(f"Invalid JSON in {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise LiquidityPlanError(f"{label.title()} must contain a JSON object")
    return data


def _load_optional_snapshot(path: Path | None, label: str, expected_schema: str) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    data = _load_json(path, f"{label} snapshot")
    if data.get("schema_version") != expected_schema:
        raise LiquidityPlanError(f"Unsupported {label} snapshot schema: {data.get('schema_version')}")
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


def _required_string(data: dict[str, Any], field: str, errors: list[str]) -> str | None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required")
        return None
    return value


def _optional_decimal(value: Any, label: str, errors: list[str]) -> Decimal | None:
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
        raise LiquidityPlanError(f"{label} must be a decimal") from exc


def _parse_date(value: Any, label: str) -> date:
    if not isinstance(value, str):
        raise LiquidityPlanError(f"{label} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise LiquidityPlanError(f"{label} must be a valid ISO date") from exc


def _optional_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _asset_id(component: dict[str, Any], index: int) -> str:
    for field in ("asset_id", "id"):
        value = component.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return f"net_worth_asset_{index + 1}"


def _public_assignment(assignment: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": assignment["asset_id"],
        "label": assignment["label"],
        "value": _format_money(assignment["value"]),
        "currency": assignment["currency"],
        "bucket": assignment["bucket"],
        "blocks_current_spending": assignment["blocks_current_spending"],
        "concentration_ratio": _format_ratio(assignment["concentration_ratio"]),
        "reason_codes": assignment["reason_codes"],
    }


def _semantic_plan_core(plan_core: dict[str, Any]) -> dict[str, Any]:
    semantic = json.loads(json.dumps(plan_core))
    source = semantic.get("source")
    if isinstance(source, dict):
        source.pop("path", None)
    household = semantic.get("household")
    if isinstance(household, dict):
        household.pop("net_worth_snapshot_path", None)
        household.pop("asset_availability_snapshot_path", None)
        household.pop("planning_goals_snapshot_path", None)
    return semantic


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT))


def _format_ratio(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001")))
