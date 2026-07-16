import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "rita-options/v1"
RULE_PACK_SCHEMA_VERSION = "rita-rule-pack/v1"
CENT = Decimal("0.01")


class RitaOptionsError(ValueError):
    pass


def optimize_rita_options(
    rule_pack_path: Path,
    output_path: Path,
    *,
    age: int | None = None,
    years_to_public_pension: str | None = None,
    employment_status: str | None = None,
    unemployed_months: int | None = None,
    mandatory_contribution_years: str | None = None,
    complementary_pension_years: str | None = None,
    complementary_balance: str | None = None,
    duration_months: int | None = None,
    monthly_need: str | None = None,
) -> dict[str, Any]:
    rule_pack = load_rule_pack(rule_pack_path)
    data_gaps = _input_gaps(
        age=age,
        years_to_public_pension=years_to_public_pension,
        employment_status=employment_status,
        complementary_pension_years=complementary_pension_years,
    )
    parsed = _parse_inputs(
        years_to_public_pension=years_to_public_pension,
        mandatory_contribution_years=mandatory_contribution_years,
        complementary_pension_years=complementary_pension_years,
        complementary_balance=complementary_balance,
        monthly_need=monthly_need,
    )

    eligibility = None
    options: list[dict[str, Any]] = []
    status = "blocked_missing_inputs" if data_gaps else "complete"

    if not data_gaps:
        eligibility = _evaluate_eligibility(
            rule_pack,
            age=age,
            years_to_public_pension=parsed["years_to_public_pension"],
            employment_status=employment_status or "",
            unemployed_months=unemployed_months,
            mandatory_contribution_years=parsed["mandatory_contribution_years"],
            complementary_pension_years=parsed["complementary_pension_years"],
        )
        if not eligibility["eligible"]:
            status = "not_eligible"
        else:
            option_gaps = _option_gaps(
                complementary_balance=complementary_balance,
                duration_months=duration_months,
            )
            data_gaps.extend(option_gaps)
            if option_gaps:
                status = "blocked_missing_inputs"
            else:
                options.append(
                    _straight_line_option(
                        rule_pack,
                        eligibility,
                        parsed["complementary_balance"],
                        duration_months or 0,
                        parsed["monthly_need"],
                    )
                )

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "RitaOptionsSnapshot",
        "status": status,
        "input": {
            "age": age,
            "years_to_public_pension": _format_optional_decimal(parsed["years_to_public_pension"]),
            "employment_status": employment_status,
            "unemployed_months": unemployed_months,
            "mandatory_contribution_years": _format_optional_decimal(parsed["mandatory_contribution_years"]),
            "complementary_pension_years": _format_optional_decimal(parsed["complementary_pension_years"]),
            "complementary_balance": _format_optional_money(parsed["complementary_balance"]),
            "duration_months": duration_months,
            "monthly_need": _format_optional_money(parsed["monthly_need"]),
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
        "eligibility": eligibility,
        "options": options,
        "data_gaps": data_gaps,
        "notes": (
            "RITA options V1 checks deterministic minimum requirements and simple gross drawdown only; "
            "it does not calculate taxes, public pension entitlement, fund fees or investment returns."
        ),
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise RitaOptionsError(f"Cannot write RITA options snapshot: {output_path}") from exc
    return snapshot


def load_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(rule_pack_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RitaOptionsError(f"RITA rule pack not found: {rule_pack_path}") from exc
    except json.JSONDecodeError as exc:
        raise RitaOptionsError(f"RITA rule pack must be JSON-compatible YAML: {rule_pack_path}") from exc
    _validate_rule_pack(data)
    return data


def _validate_rule_pack(data: dict[str, Any]) -> None:
    required = ("schema_version", "rule_pack_id", "jurisdiction", "currency", "requirements")
    for field in required:
        if field not in data:
            raise RitaOptionsError(f"RITA rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise RitaOptionsError(f"Unsupported RITA rule pack schema: {data['schema_version']}")
    requirements = data["requirements"]
    for field in ("accepted_non_working_statuses", "minimum_complementary_pension_years", "ordinary", "long_unemployment"):
        if field not in requirements:
            raise RitaOptionsError(f"RITA requirements missing field: {field}")


def _input_gaps(**values: Any) -> list[dict[str, Any]]:
    labels = {
        "age": "Age is required.",
        "years_to_public_pension": "Years to public old-age pension is required.",
        "employment_status": "Employment status is required.",
        "complementary_pension_years": "Complementary pension participation years are required.",
    }
    return [
        {"code": f"missing_{field}", "message": message}
        for field, message in labels.items()
        if values[field] in (None, "")
    ]


def _option_gaps(complementary_balance: str | None, duration_months: int | None) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    if complementary_balance in (None, ""):
        gaps.append({"code": "missing_complementary_balance", "message": "Complementary pension balance is required for option amounts."})
    if duration_months is None:
        gaps.append({"code": "missing_duration_months", "message": "Duration in months is required for option amounts."})
    elif duration_months <= 0:
        raise RitaOptionsError("duration_months must be greater than zero")
    return gaps


def _parse_inputs(**values: str | None) -> dict[str, Decimal | None]:
    decimal_fields = {
        "years_to_public_pension",
        "mandatory_contribution_years",
        "complementary_pension_years",
        "complementary_balance",
        "monthly_need",
    }
    parsed: dict[str, Decimal | None] = {}
    for field in decimal_fields:
        value = values[field]
        parsed[field] = None if value in (None, "") else _decimal(value, field)
    return parsed


def _evaluate_eligibility(
    rule_pack: dict[str, Any],
    *,
    age: int | None,
    years_to_public_pension: Decimal | None,
    employment_status: str,
    unemployed_months: int | None,
    mandatory_contribution_years: Decimal | None,
    complementary_pension_years: Decimal | None,
) -> dict[str, Any]:
    requirements = rule_pack["requirements"]
    statuses = set(requirements["accepted_non_working_statuses"])
    checks: list[dict[str, Any]] = []

    non_working = employment_status in statuses
    complementary_ok = complementary_pension_years is not None and complementary_pension_years >= _decimal(
        requirements["minimum_complementary_pension_years"],
        "minimum_complementary_pension_years",
    )
    ordinary = requirements["ordinary"]
    ordinary_ok = (
        non_working
        and complementary_ok
        and years_to_public_pension is not None
        and years_to_public_pension <= _decimal(ordinary["max_years_to_public_pension"], "ordinary.max_years_to_public_pension")
        and mandatory_contribution_years is not None
        and mandatory_contribution_years >= _decimal(
            ordinary["minimum_mandatory_contribution_years"],
            "ordinary.minimum_mandatory_contribution_years",
        )
    )
    checks.append(
        {
            "rule_id": ordinary["rule_id"],
            "eligible": ordinary_ok,
            "reason": "ordinary_requirements_met" if ordinary_ok else "ordinary_requirements_not_met",
        }
    )

    unemployment = requirements["long_unemployment"]
    long_unemployment_ok = (
        non_working
        and complementary_ok
        and years_to_public_pension is not None
        and years_to_public_pension <= _decimal(
            unemployment["max_years_to_public_pension"],
            "long_unemployment.max_years_to_public_pension",
        )
        and unemployed_months is not None
        and unemployed_months > int(unemployment["minimum_unemployed_months_exclusive"])
    )
    checks.append(
        {
            "rule_id": unemployment["rule_id"],
            "eligible": long_unemployment_ok,
            "reason": "long_unemployment_requirements_met" if long_unemployment_ok else "long_unemployment_requirements_not_met",
        }
    )

    eligible_check = next((check for check in checks if check["eligible"]), None)
    return {
        "eligible": eligible_check is not None,
        "matched_rule_id": None if eligible_check is None else eligible_check["rule_id"],
        "age": age,
        "checks": checks,
        "explainability": {
            "rule_pack_id": rule_pack["rule_pack_id"],
            "valid_from": rule_pack.get("valid_from"),
            "valid_to": rule_pack.get("valid_to"),
        },
    }


def _straight_line_option(
    rule_pack: dict[str, Any],
    eligibility: dict[str, Any],
    balance: Decimal | None,
    duration_months: int,
    monthly_need: Decimal | None,
) -> dict[str, Any]:
    if balance is None:
        raise RitaOptionsError("complementary_balance is required")
    if balance < Decimal("0.00"):
        raise RitaOptionsError("complementary_balance must be greater than or equal to zero")
    monthly_gross = (balance / Decimal(duration_months)).quantize(CENT, rounding=ROUND_HALF_UP)
    coverage = None if monthly_need in (None, Decimal("0.00")) else (monthly_gross / monthly_need).quantize(Decimal("0.0001"))
    return {
        "option_id": "straight_line_gross_drawdown",
        "rule_id": eligibility["matched_rule_id"],
        "duration_months": duration_months,
        "gross_monthly_amount": _format_money(monthly_gross),
        "gross_total_amount": _format_money(balance),
        "estimated_residual_balance": "0.00",
        "monthly_need_coverage_ratio": None if coverage is None else str(coverage),
        "currency": rule_pack["currency"],
        "assumptions": [
            "straight_line_gross_drawdown",
            "no_tax_calculation",
            "no_investment_return",
            "no_fund_fee",
        ],
    }


def _decimal(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise RitaOptionsError(f"Invalid decimal value for {field}: {value}") from exc


def _format_optional_decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _format_optional_money(value: Decimal | None) -> str | None:
    return None if value is None else _format_money(value)


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))
