import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

RULE_PACK_SCHEMA_VERSION = "spanish-statutory-pension-rule-pack/v1"


class SpanishPensionRulesError(ValueError):
    pass


def load_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(rule_pack_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpanishPensionRulesError(f"Spanish pension rule pack not found: {rule_pack_path}") from exc
    except json.JSONDecodeError as exc:
        raise SpanishPensionRulesError(f"Spanish pension rule pack is not valid JSON: {rule_pack_path}") from exc
    _validate_rule_pack(data)
    return data


def ordinary_retirement_age(rule_pack: dict[str, Any], year: int, contribution_months: int) -> dict[str, Any]:
    rule = _find_year_rule(rule_pack["ordinary_retirement_age_schedule"], year)
    if rule is None:
        raise SpanishPensionRulesError(f"No ordinary retirement age rule found for year {year}")
    minimum_months = int(rule["minimum_contribution_months_for_age_65"])
    age = rule["age_if_minimum_met"] if contribution_months >= minimum_months else rule["standard_age"]
    return {
        "year": year,
        "contribution_months": contribution_months,
        "age": dict(age),
        "matched_rule": {
            "from_year": rule["from_year"],
            "to_year": rule["to_year"],
            "source_provision": rule["source_provision"],
        },
    }


def base_reguladora_parameters(rule_pack: dict[str, Any], year: int) -> dict[str, Any]:
    rule = _find_year_rule(rule_pack["base_reguladora_transition"], year)
    if rule is None:
        raise SpanishPensionRulesError(f"No base reguladora transition rule found for year {year}")
    return dict(rule)


def accrued_pension_percentage(rule_pack: dict[str, Any], year: int, contribution_months: int) -> dict[str, Any]:
    percentage = rule_pack["pension_percentage"]
    first_months = int(percentage["first_15_years_months"])
    first_rate = _decimal(percentage["first_15_years_rate"], "first_15_years_rate")
    maximum_rate = _decimal(percentage["maximum_rate"], "maximum_rate")

    if contribution_months <= 0:
        rate = Decimal("0")
        additional_months = 0
        applied_segments: list[dict[str, Any]] = []
    else:
        rate = first_rate if contribution_months >= first_months else Decimal("0")
        additional_months = max(0, contribution_months - first_months)
        applied_segments = _apply_additional_percentage_schedule(percentage, year, additional_months)
        for segment in applied_segments:
            rate += Decimal(segment["applied_rate"])

    if rate > maximum_rate:
        rate = maximum_rate

    return {
        "year": year,
        "contribution_months": contribution_months,
        "percentage": _format_decimal(rate),
        "additional_months": additional_months,
        "applied_segments": applied_segments,
        "source_provision": percentage["source_provision"],
    }


def _validate_rule_pack(data: dict[str, Any]) -> None:
    required = (
        "schema_version",
        "rule_pack_id",
        "jurisdiction",
        "currency",
        "source_refs",
        "scope",
        "eligibility",
        "ordinary_retirement_age_schedule",
        "base_reguladora_transition",
        "pension_percentage",
        "payment_schedule",
        "limitations",
    )
    for field in required:
        if field not in data:
            raise SpanishPensionRulesError(f"Spanish pension rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise SpanishPensionRulesError(f"Unsupported Spanish pension rule pack schema: {data['schema_version']}")
    if data["jurisdiction"] != "ES":
        raise SpanishPensionRulesError("Spanish pension rule pack jurisdiction must be ES")
    if data["currency"] != "EUR":
        raise SpanishPensionRulesError("Spanish pension rule pack currency must be EUR")
    _validate_source_refs(data["source_refs"])
    _validate_limitations(data["limitations"])
    _validate_eligibility(data["eligibility"])
    _validate_age_schedule(data["ordinary_retirement_age_schedule"])
    _validate_base_reguladora_transition(data["base_reguladora_transition"])
    _validate_percentage(data["pension_percentage"])
    _validate_payment_schedule(data["payment_schedule"])


def _validate_source_refs(source_refs: Any) -> None:
    if not isinstance(source_refs, list) or not source_refs:
        raise SpanishPensionRulesError("Spanish pension rule pack must contain at least one source_ref")
    for source_ref in source_refs:
        for field in ("source_id", "title", "url", "retrieved_on", "provisions"):
            if field not in source_ref:
                raise SpanishPensionRulesError(f"Spanish pension source_ref missing field: {field}")
        if not (
            str(source_ref["url"]).startswith("https://www.boe.es/")
            or str(source_ref["url"]).startswith("https://www.seg-social.es/")
        ):
            raise SpanishPensionRulesError("Spanish pension source_ref must use an official BOE or Seguridad Social URL")
        if not isinstance(source_ref["provisions"], list) or not source_ref["provisions"]:
            raise SpanishPensionRulesError("Spanish pension source_ref provisions must be a non-empty list")


def _validate_limitations(limitations: Any) -> None:
    if not isinstance(limitations, list) or len(limitations) < 3:
        raise SpanishPensionRulesError("Spanish pension rule pack must contain explicit limitations")
    joined = " ".join(str(item).lower() for item in limitations)
    for phrase in ("ordinary retirement", "eu coordination", "taxation", "not an official"):
        if phrase not in joined:
            raise SpanishPensionRulesError(f"Spanish pension limitations must mention: {phrase}")


def _validate_eligibility(eligibility: dict[str, Any]) -> None:
    for field in (
        "minimum_total_contribution_months",
        "specific_contribution_months_within_lookback",
        "specific_contribution_lookback_months",
    ):
        if field not in eligibility:
            raise SpanishPensionRulesError(f"Spanish pension eligibility missing field: {field}")
        if int(eligibility[field]) <= 0:
            raise SpanishPensionRulesError(f"Spanish pension eligibility field must be positive: {field}")


def _validate_age_schedule(schedule: Any) -> None:
    if not isinstance(schedule, list) or not schedule:
        raise SpanishPensionRulesError("Spanish pension age schedule must contain at least one rule")
    for rule in schedule:
        for field in (
            "from_year",
            "to_year",
            "minimum_contribution_months_for_age_65",
            "age_if_minimum_met",
            "standard_age",
            "source_provision",
        ):
            if field not in rule:
                raise SpanishPensionRulesError(f"Spanish pension age rule missing field: {field}")
        _validate_year_rule_bounds(rule, "Spanish pension age rule")
        if int(rule["minimum_contribution_months_for_age_65"]) <= 0:
            raise SpanishPensionRulesError("Spanish pension age rule contribution threshold must be positive")
        _validate_age(rule["age_if_minimum_met"], "age_if_minimum_met")
        _validate_age(rule["standard_age"], "standard_age")


def _validate_base_reguladora_transition(transition: Any) -> None:
    if not isinstance(transition, list) or not transition:
        raise SpanishPensionRulesError("Spanish pension base reguladora transition must contain at least one rule")
    for rule in transition:
        for field in ("from_year", "to_year", "lookback_months", "selected_highest_bases", "divisor", "source_provision"):
            if field not in rule:
                raise SpanishPensionRulesError(f"Spanish pension base reguladora rule missing field: {field}")
        _validate_year_rule_bounds(rule, "Spanish pension base reguladora rule")
        lookback_months = int(rule["lookback_months"])
        selected_highest_bases = int(rule["selected_highest_bases"])
        if lookback_months <= 0 or selected_highest_bases <= 0:
            raise SpanishPensionRulesError("Spanish pension base reguladora months must be positive")
        if selected_highest_bases > lookback_months:
            raise SpanishPensionRulesError("Spanish pension selected bases cannot exceed lookback months")
        if _decimal(rule["divisor"], "divisor") <= Decimal("0"):
            raise SpanishPensionRulesError("Spanish pension base reguladora divisor must be positive")


def _validate_percentage(percentage: dict[str, Any]) -> None:
    for field in ("first_15_years_rate", "first_15_years_months", "additional_month_schedule", "maximum_rate", "source_provision"):
        if field not in percentage:
            raise SpanishPensionRulesError(f"Spanish pension percentage missing field: {field}")
    rate = _decimal(percentage["first_15_years_rate"], "first_15_years_rate")
    if rate <= Decimal("0") or rate > Decimal("1"):
        raise SpanishPensionRulesError("Spanish pension percentage rate must be between 0 and 1")
    if int(percentage["first_15_years_months"]) != 180:
        raise SpanishPensionRulesError("Spanish pension first 15 years must be encoded as 180 months")
    maximum_rate = _decimal(percentage["maximum_rate"], "maximum_rate")
    if maximum_rate != Decimal("1.00"):
        raise SpanishPensionRulesError("Spanish pension maximum percentage must be encoded as 1.00")
    _validate_additional_percentage_schedule(percentage["additional_month_schedule"])


def _validate_payment_schedule(payment_schedule: dict[str, Any]) -> None:
    for field in ("ordinary_payments_per_year", "ordinary_monthly_payments", "extra_payment_months", "source_provision"):
        if field not in payment_schedule:
            raise SpanishPensionRulesError(f"Spanish pension payment schedule missing field: {field}")
    if int(payment_schedule["ordinary_payments_per_year"]) != 14:
        raise SpanishPensionRulesError("Spanish pension ordinary payments per year must be encoded as 14")
    if int(payment_schedule["ordinary_monthly_payments"]) != 12:
        raise SpanishPensionRulesError("Spanish pension ordinary monthly payments must be encoded as 12")
    extra_months = payment_schedule["extra_payment_months"]
    if not isinstance(extra_months, list) or sorted(int(month) for month in extra_months) != [6, 11]:
        raise SpanishPensionRulesError("Spanish pension extra payment months must be June and November")


def _validate_additional_percentage_schedule(schedule: Any) -> None:
    if not isinstance(schedule, list) or not schedule:
        raise SpanishPensionRulesError("Spanish pension additional month schedule must contain at least one rule")
    for rule in schedule:
        for field in ("from_year", "to_year", "segments", "source_provision"):
            if field not in rule:
                raise SpanishPensionRulesError(f"Spanish pension additional month rule missing field: {field}")
        _validate_year_rule_bounds(rule, "Spanish pension additional month rule")
        if not isinstance(rule["segments"], list) or not rule["segments"]:
            raise SpanishPensionRulesError("Spanish pension additional month rule must contain segments")
        expected_from = 1
        for segment in rule["segments"]:
            for field in ("from_additional_month", "to_additional_month", "monthly_rate"):
                if field not in segment:
                    raise SpanishPensionRulesError(f"Spanish pension additional month segment missing field: {field}")
            from_month = int(segment["from_additional_month"])
            to_month = int(segment["to_additional_month"])
            if from_month != expected_from or to_month < from_month:
                raise SpanishPensionRulesError("Spanish pension additional month segments must be contiguous")
            if _decimal(segment["monthly_rate"], "monthly_rate") <= Decimal("0"):
                raise SpanishPensionRulesError("Spanish pension additional month rate must be positive")
            expected_from = to_month + 1


def _apply_additional_percentage_schedule(
    percentage: dict[str, Any], year: int, additional_months: int
) -> list[dict[str, Any]]:
    if additional_months == 0:
        return []
    rule = _find_year_rule(percentage["additional_month_schedule"], year)
    if rule is None:
        raise SpanishPensionRulesError(f"No Spanish pension percentage rule found for year {year}")

    remaining_months = additional_months
    applied_segments = []
    for segment in rule["segments"]:
        if remaining_months <= 0:
            break
        segment_from = int(segment["from_additional_month"])
        segment_to = int(segment["to_additional_month"])
        segment_capacity = segment_to - segment_from + 1
        applied_months = min(remaining_months, segment_capacity)
        monthly_rate = _decimal(segment["monthly_rate"], "monthly_rate")
        applied_rate = monthly_rate * Decimal(applied_months)
        applied_segments.append(
            {
                "from_additional_month": segment_from,
                "to_additional_month": segment_from + applied_months - 1,
                "applied_months": applied_months,
                "monthly_rate": str(monthly_rate),
                "applied_rate": _format_decimal(applied_rate),
                "source_provision": rule["source_provision"],
            }
        )
        remaining_months -= applied_months
    return applied_segments


def _validate_year_rule_bounds(rule: dict[str, Any], label: str) -> None:
    from_year = int(rule["from_year"])
    to_year = rule["to_year"]
    if to_year is not None and int(to_year) < from_year:
        raise SpanishPensionRulesError(f"{label} has invalid year bounds")


def _validate_age(age: Any, field: str) -> None:
    if not isinstance(age, dict) or "years" not in age or "months" not in age:
        raise SpanishPensionRulesError(f"Spanish pension age field must contain years and months: {field}")
    years = int(age["years"])
    months = int(age["months"])
    if years <= 0 or months < 0 or months > 11:
        raise SpanishPensionRulesError(f"Spanish pension age field has invalid values: {field}")


def _find_year_rule(rules: list[dict[str, Any]], year: int) -> dict[str, Any] | None:
    for rule in rules:
        from_year = int(rule["from_year"])
        to_year = rule["to_year"]
        if year >= from_year and (to_year is None or year <= int(to_year)):
            return rule
    return None


def _decimal(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise SpanishPensionRulesError(f"Invalid decimal value for {field}: {value}") from exc


def _format_decimal(value: Decimal) -> str:
    return format(value.normalize(), "f")
