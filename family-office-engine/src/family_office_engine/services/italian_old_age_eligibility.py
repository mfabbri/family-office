"""Fail-closed screening for the approved Italian ordinary old-age micro-slice."""
from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from family_office_engine.governance.pension_source_freshness import (
    PensionSourceFreshnessError,
    require_fresh_pension_rule_pack,
)


class ItalianOldAgeEligibilityError(ValueError):
    """The dedicated eligibility rule pack cannot be used."""


def assess_italian_old_age_eligibility(
    facts: dict[str, Any], rule_pack_path: Path, as_of_date: str | date | None = None
) -> dict[str, Any]:
    """Assess only ordinary FPLD/AGO employee paths; never calculate amounts or a timeline."""
    pack = _load_pack(rule_pack_path, as_of_date)
    gaps = _scope_gaps(facts, pack["supported_scope"])
    candidate = _date(facts.get("candidate_date"))
    birth = _date(facts.get("date_of_birth"))
    evidence = facts.get("contribution_evidence")
    if candidate is None:
        gaps.append(_gap("candidate_date_missing_or_invalid", "A verified ISO candidate_date is required."))
    elif not date.fromisoformat(pack["valid_from"]) <= candidate <= date.fromisoformat(pack["valid_to"]):
        gaps.append(_gap("rule_pack_period_unsupported", "candidate_date is outside the supported 2026-2028 period."))
    if birth is None:
        gaps.append(_gap("date_of_birth_missing_or_unverified", "A verified ISO date_of_birth is required."))
    elif birth.day == monthrange(birth.year, birth.month)[1]:
        gaps.append(_gap("age_day_semantics_unsupported", "Feb-29 and month-end birth dates require approved age-day semantics."))
    if facts.get("date_of_birth_verified") is not True or not _source_refs(facts.get("date_of_birth_source_refs")):
        gaps.append(_gap("date_of_birth_provenance_missing", "Date of birth must be verified against a declared source."))
    if (not isinstance(evidence, dict) or _date(evidence.get("as_of_date")) is None
            or evidence.get("verified") is not True or not _source_refs(evidence.get("source_refs"))):
        gaps.append(_gap("contribution_evidence_missing_or_undated", "Dated, verified contribution evidence with source references is required."))
        evidence = {}
    cessation = facts.get("cessation_evidence")
    cessation_date = _date(cessation.get("cessation_date")) if isinstance(cessation, dict) else None
    if (facts.get("cessation_required") is False or facts.get("cessation_confirmed") is not True or not isinstance(cessation, dict)
            or cessation.get("verified") is not True or cessation_date is None
            or not _source_refs(cessation.get("source_refs"))):
        gaps.append(_gap("employee_cessation_evidence_missing", "Verified, source-bound employee cessation evidence is required."))
    elif candidate is not None and cessation_date > candidate:
        gaps.append(_gap("employee_cessation_after_candidate", "Employee cessation must occur no later than the candidate date."))
    if isinstance(evidence, dict) and candidate is not None:
        evidence_as_of = _date(evidence.get("as_of_date"))
        evidence_period_end = _date(evidence.get("period_end"))
        if evidence_as_of is not None and (evidence_as_of > candidate or evidence_period_end is None or evidence_period_end > candidate):
            gaps.append(_gap("contribution_evidence_not_applicable_to_candidate", "Contribution evidence must end no later than the candidate date."))
    if gaps:
        return _not_assessed(pack, candidate, gaps)

    first_contribution = _date(evidence.get("first_contribution_date"))
    cohort = facts.get("contribution_cohort")
    cutoff = _date(pack.get("post_1996_cohort_start"))
    if cutoff is None:
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility pack has no valid contribution cohort cutoff")
    derived_cohort = None if first_contribution is None else (
        "before_1996" if first_contribution < cutoff else "on_or_after_1996"
    )
    if facts.get("contribution_cohort_confirmed") is not True or cohort != derived_cohort:
        return _not_assessed(pack, candidate, [_gap(
            "contribution_cohort_unknown", "A confirmed cohort matching the dated first contribution is required."
        )])
    qualifying = _decimal(evidence.get("qualifying_contribution_years"))
    if qualifying is None:
        return _not_assessed(pack, candidate, [_gap("qualifying_contribution_total_missing", "A dated qualifying contribution total is required.")])

    required = pack["requirements_by_year"][str(candidate.year)]
    paths = pack["paths"]
    ordinary = _age_met(birth, candidate, required["ordinary_age"])
    if ordinary is None:
        return _not_assessed(pack, candidate, [_gap("age_day_semantics_unsupported", "The applicable age threshold falls on an unsupported calendar date.")])
    if cohort == "before_1996":
        threshold = _decimal(paths["pre_1996"]["minimum_qualifying_contribution_years"])
        return _assessed(pack, candidate, "pre_1996_ordinary", threshold is not None and ordinary and qualifying >= threshold)

    # The 71-year alternative is independent of the amount threshold on the 20-year path.
    effective = _decimal(evidence.get("effective_contribution_years_excluding_figurative"))
    alternative = _age_met(birth, candidate, required["contributory_alternative_age"])
    if alternative is None:
        return _not_assessed(pack, candidate, [_gap("age_day_semantics_unsupported", "The applicable alternative age threshold falls on an unsupported calendar date.")])
    if alternative and effective is None:
        return _not_assessed(pack, candidate, [_gap("effective_contribution_total_missing", "A dated effective contribution total excluding figurative periods is required for the alternative path.")])
    alternative_threshold = _decimal(paths["post_1996_alternative"]["minimum_effective_contribution_years"])
    if paths["post_1996_alternative"].get("figurative_contribution_counts") is not False:
        return _not_assessed(pack, candidate, [_gap("unsupported_alternative_contribution_rule", "The loaded pack must explicitly exclude figurative contributions from the five-year alternative.")])
    if alternative and alternative_threshold is not None and effective >= alternative_threshold:
        return _assessed(pack, candidate, "post_1996_alternative", True)

    qualifying_threshold = _decimal(paths["post_1996"]["minimum_qualifying_contribution_years"])
    if ordinary and qualifying_threshold is not None and qualifying >= qualifying_threshold:
        amount_evidence = facts.get("monthly_amount_evidence")
        amount_verified = (
            isinstance(amount_evidence, dict)
            and amount_evidence.get("verified") is True
            and _date(amount_evidence.get("as_of_date")) is not None
            and amount_evidence.get("valid_for_year") == candidate.year
            and _date(amount_evidence.get("as_of_date")) <= candidate
            and _source_refs(amount_evidence.get("source_refs"))
        )
        pension = _decimal(facts.get("documented_monthly_pension_amount"))
        allowance = _decimal(facts.get("documented_monthly_social_allowance"))
        if not amount_verified or pension is None or allowance is None:
            return _not_assessed(pack, candidate, [_gap(
                "monthly_amount_evidence_missing", "Documented monthly amount and threshold evidence with source references are required for the 20-year path."
            )])
        threshold_rule = paths["post_1996"].get("minimum_monthly_pension_threshold")
        if threshold_rule != "documented_applicable_monthly_social_allowance":
            return _not_assessed(pack, candidate, [_gap("unsupported_threshold_rule", "The loaded pack declares an unsupported monthly pension threshold rule.")])
        return _assessed(pack, candidate, "post_1996_ordinary_threshold", pension >= allowance)

    if effective is None:
        return _not_assessed(pack, candidate, [_gap("effective_contribution_total_missing", "A dated effective contribution total excluding figurative periods is required for the alternative path.")])
    return _assessed(pack, candidate, "post_1996_alternative", False)


def _load_pack(path: Path, as_of_date: str | date | None) -> dict[str, Any]:
    try:
        require_fresh_pension_rule_pack(path, as_of_date)
        pack = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, PensionSourceFreshnessError) as exc:
        raise ItalianOldAgeEligibilityError(str(exc)) from exc
    if not isinstance(pack, dict) or not all(key in pack for key in ("schema_version", "rule_pack_id", "jurisdiction", "valid_from", "valid_to", "requirements_by_year", "paths", "supported_scope", "post_1996_cohort_start", "source_refs")):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility rule pack is structurally invalid")
    valid_from, valid_to = _date(pack["valid_from"]), _date(pack["valid_to"])
    if (pack["schema_version"] != "inps-old-age-eligibility-rule-pack/v1"
            or pack["rule_pack_id"] != "it.inps-old-age-eligibility.2026-2028.v1"
            or pack["jurisdiction"] != "IT" or valid_from != date(2026, 1, 1) or valid_to != date(2028, 12, 31)
            or _date(pack["post_1996_cohort_start"]) != date(1996, 1, 1)):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility pack version, jurisdiction or legal period is unsupported")
    if (not isinstance(pack["paths"], dict) or not isinstance(pack["requirements_by_year"], dict)
            or not isinstance(pack["supported_scope"], dict)):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility rule pack paths/requirements are invalid")
    for year in ("2026", "2027", "2028"):
        year_rules = pack["requirements_by_year"].get(year)
        if not isinstance(year_rules, dict) or not all(_valid_age_requirement(year_rules.get(key)) for key in ("ordinary_age", "contributory_alternative_age")):
            raise ItalianOldAgeEligibilityError(f"Italian old-age eligibility pack has invalid age requirements for {year}")
    for path_name, field in (("pre_1996", "minimum_qualifying_contribution_years"), ("post_1996", "minimum_qualifying_contribution_years"), ("post_1996_alternative", "minimum_effective_contribution_years")):
        path_rules = pack["paths"].get(path_name)
        threshold = _decimal(path_rules.get(field)) if isinstance(path_rules, dict) else None
        if threshold is None or threshold <= 0:
            raise ItalianOldAgeEligibilityError(f"Italian old-age eligibility pack has invalid threshold {path_name}.{field}")
    if (not isinstance(pack["supported_scope"].get("managements"), list)
            or not pack["supported_scope"]["managements"]
            or any(not isinstance(item, str) for item in pack["supported_scope"]["managements"])
            or not set(pack["supported_scope"]["managements"]).issubset({"FPLD", "AGO"})
            or pack["supported_scope"].get("employment_category") != "employee"
            or pack["supported_scope"].get("ordinary_single_management_profile_required") is not True):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility pack has invalid supported scope")
    if (pack["paths"]["post_1996"].get("minimum_monthly_pension_threshold") != "documented_applicable_monthly_social_allowance"
            or pack["paths"]["post_1996_alternative"].get("figurative_contribution_counts") is not False):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility pack has unsupported path semantics")
    sources = pack["source_refs"]
    if not isinstance(sources, list) or not sources:
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility pack has no legal sources")
    provision_periods: dict[str, list[tuple[str, date, date]]] = {}
    for source in sources:
        periods = source.get("provision_periods") if isinstance(source, dict) else None
        if not isinstance(source, dict) or not isinstance(source.get("provisions"), list) or not source["provisions"] or not isinstance(periods, list) or not periods:
            raise ItalianOldAgeEligibilityError("Italian old-age eligibility source lacks provisions or provision periods")
        for period in periods:
            period_start = _date(period.get("valid_from")) if isinstance(period, dict) else None
            period_end = _date(period.get("valid_to")) if isinstance(period, dict) else None
            provision_id = period.get("provision_id") if isinstance(period, dict) else None
            if (period_start is None or period_end is None or period_start > period_end
                    or not isinstance(provision_id, str) or not provision_id.strip()):
                raise ItalianOldAgeEligibilityError("Italian old-age eligibility source has invalid provision periods")
            provision_periods.setdefault(provision_id, []).append((source.get("source_id"), period_start, period_end))
    inps_page = "inps.pensione-vecchiaia"
    inps_update = "inps.requisiti-2027-2028"
    required_provisions = {
        "ordinary_age_2026": (inps_page, date(2026, 1, 1), date(2026, 12, 31)),
        "ordinary_age_adjustment_2027_2028": (inps_update, date(2027, 1, 1), date(2028, 12, 31)),
        "contribution_threshold": (inps_page, date(2026, 1, 1), date(2028, 12, 31)),
        "post_1996_amount_threshold": (inps_page, date(2026, 1, 1), date(2028, 12, 31)),
        "post_1996_effective_contribution_alternative": (inps_page, date(2026, 1, 1), date(2028, 12, 31)),
        "employee_cessation": (inps_page, date(2026, 1, 1), date(2028, 12, 31)),
    }
    if any(provision_periods.get(provision) != [expected] for provision, expected in required_provisions.items()):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility lacks exact source-owned provision-period coverage")
    return pack


def _scope_gaps(facts: dict[str, Any], supported_scope: dict[str, Any]) -> list[dict[str, str]]:
    gaps = []
    scope_evidence = facts.get("scope_evidence")
    if (not isinstance(scope_evidence, dict) or scope_evidence.get("verified") is not True
            or _date(scope_evidence.get("as_of_date")) is None
            or not _source_refs(scope_evidence.get("source_refs"))):
        gaps.append(_gap("scope_evidence_missing_or_unverified", "Source-bound management, employment and exclusion evidence is required."))
    elif _date(facts.get("candidate_date")) is not None and _date(scope_evidence.get("as_of_date")) > _date(facts.get("candidate_date")):
        gaps.append(_gap("scope_evidence_not_applicable_to_candidate", "Scope evidence must be dated no later than the candidate date."))
    if supported_scope.get("ordinary_single_management_profile_required") is True and facts.get("ordinary_single_management_profile_confirmed") is not True:
        gaps.append(_gap("ordinary_single_management_profile_unconfirmed", "Ordinary single-management profile confirmation is required."))
    allowed_managements = supported_scope.get("managements")
    if not isinstance(allowed_managements, list) or facts.get("management") not in allowed_managements or facts.get("management_confirmed") is not True:
        gaps.append(_gap("management_unsupported_or_unconfirmed", "Only confirmed FPLD or AGO management is supported."))
    if facts.get("employment_category") != supported_scope.get("employment_category"):
        gaps.append(_gap("employment_category_unsupported", "Only employee category is supported."))
    for field, code in (("multiple_managements", "multiple_managements_unsupported"), ("foreign_or_eu_aggregation", "foreign_or_eu_aggregation_unsupported"), ("special_or_excluded_profile", "special_or_excluded_profile_unsupported")):
        if facts.get(field) is not False:
            gaps.append(_gap(code, "This profile must be explicitly confirmed absent; unknown is outside the approved scope."))
    return gaps


def _age_met(birth: date, candidate: date, requirement: dict[str, int]) -> bool | None:
    year, month = birth.year + requirement["years"], birth.month + requirement["months"]
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1
    try:
        threshold = date(year, month, birth.day)
    except ValueError:
        return None
    return candidate >= threshold


def _date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _decimal(value: Any) -> Decimal | None:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() and result >= 0 else None


def _source_refs(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def _valid_age_requirement(value: Any) -> bool:
    return (isinstance(value, dict) and isinstance(value.get("years"), int) and value["years"] >= 0
            and isinstance(value.get("months"), int) and 0 <= value["months"] <= 11)


def _assessed(pack: dict[str, Any], candidate: date, path: str, eligible: bool) -> dict[str, Any]:
    return {"schema_version": "italian-old-age-eligibility/v1", "status": "assessed", "result": "eligible" if eligible else "not_yet_eligible", "candidate_date": candidate.isoformat(), "path": path, "rule_pack_id": pack["rule_pack_id"], "data_gaps": [], "limitations": ["Eligibility screening only; not an INPS decision."]}


def _not_assessed(pack: dict[str, Any], candidate: date | None, gaps: list[dict[str, str]]) -> dict[str, Any]:
    return {"schema_version": "italian-old-age-eligibility/v1", "status": "not_assessed", "result": None, "candidate_date": candidate.isoformat() if candidate else None, "path": None, "rule_pack_id": pack["rule_pack_id"], "data_gaps": gaps, "limitations": ["Eligibility screening only; not an INPS decision."]}


def _gap(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}
