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
        threshold_binding = pack["threshold_bindings"]["post_1996_ordinary"]["by_year"].get(str(candidate.year))
        if not isinstance(threshold_binding, dict) or threshold_binding.get("status") != "supported":
            return _not_assessed(pack, candidate, [_gap(
                "monthly_social_allowance_threshold_not_source_bound",
                "The applicable annual social-allowance threshold is not source-bound for this rule-pack year."
            )])
        rule_amount = _decimal(threshold_binding.get("monthly_amount"))
        if (threshold_binding.get("currency") != "EUR"
                or threshold_binding.get("payments_per_year") != 13
                or rule_amount is None):
            raise ItalianOldAgeEligibilityError("Italian old-age eligibility has invalid annual threshold metadata")
        evidence_items = (
            facts.get("monthly_pension_amount_evidence"),
            facts.get("monthly_social_allowance_evidence"),
        )
        pension_refs = evidence_items[0].get("source_refs") if isinstance(evidence_items[0], dict) else None
        allowance_refs = evidence_items[1].get("source_refs") if isinstance(evidence_items[1], dict) else None
        amount_verified = all(
            isinstance(evidence_item, dict)
            and evidence_item.get("verified") is True
            and _date(evidence_item.get("as_of_date")) is not None
            and evidence_item.get("valid_for_year") == candidate.year
            and _date(evidence_item.get("as_of_date")) <= candidate
            and _source_refs(evidence_item.get("source_refs"))
            for evidence_item in evidence_items
        ) and set(pension_refs or ()) .isdisjoint(set(allowance_refs or ()))
        pension = _decimal(facts.get("documented_monthly_pension_amount"))
        allowance = _decimal(facts.get("documented_monthly_social_allowance"))
        if not amount_verified or pension is None or allowance is None:
            return _not_assessed(pack, candidate, [_gap(
                "monthly_amount_evidence_missing", "Separate documented pension-amount and social-allowance-threshold evidence with source references is required for the 20-year path."
            )])
        if allowance != rule_amount:
            return _not_assessed(pack, candidate, [_gap(
                "monthly_social_allowance_threshold_mismatch",
                "The documented social-allowance amount does not match the source-bound rule-pack threshold."
            )])
        threshold_rule = paths["post_1996"].get("minimum_monthly_pension_threshold")
        if threshold_rule != "documented_applicable_monthly_social_allowance":
            return _not_assessed(pack, candidate, [_gap("unsupported_threshold_rule", "The loaded pack declares an unsupported monthly pension threshold rule.")])
        return _assessed(pack, candidate, "post_1996_ordinary_threshold", pension >= allowance)

    if effective is None:
        return _not_assessed(pack, candidate, [_gap("effective_contribution_total_missing", "A dated effective contribution total excluding figurative periods is required for the alternative path.")])
    return _assessed(pack, candidate, "post_1996_alternative", False)


def search_first_post_1996_alternative_eligibility_month(
    facts: dict[str, Any], monthly_history: list[dict[str, Any]],
    rule_pack_path: Path, as_of_date: str | date | None = None,
) -> dict[str, Any]:
    """Find only the first supported month on the post-1995 five-effective-year path.

    Each history row is a source-bound monthly cumulative snapshot. Its effective
    total must already be reported in years; this function deliberately performs
    no conversion from weeks, days, or months and does not search the 20-year path.
    """
    search_as_of = _date(as_of_date)
    if search_as_of is None:
        return {
            "schema_version": "italian-old-age-eligibility-month-search/v1",
            "status": "not_assessed", "result": None, "path": "post_1996_alternative",
            "first_eligible_month": None, "as_of_date": None,
            "human_review_required": True, "rule_pack_id": None,
            "data_gaps": [_gap("as_of_date_missing_or_invalid", "An explicit ISO as_of_date is required for a reproducible month search.")],
            "limitations": ["First eligible month within observed history and the 2026-2028 pack only; no future contribution is projected."],
        }
    pack = _load_pack(rule_pack_path, search_as_of)
    gaps = _scope_gaps(facts, pack["supported_scope"])
    birth = _date(facts.get("date_of_birth"))
    if birth is None or facts.get("date_of_birth_verified") is not True or not _source_refs(facts.get("date_of_birth_source_refs")):
        gaps.append(_gap("date_of_birth_missing_or_unverified", "A verified, source-bound ISO date of birth is required."))
    elif birth.day == monthrange(birth.year, birth.month)[1]:
        gaps.append(_gap("age_day_semantics_unsupported", "Month-end birth dates require approved age-day semantics."))
    scope = facts.get("scope_evidence")
    scope_as_of = _date(scope.get("as_of_date")) if isinstance(scope, dict) else None
    scope_from = _date(scope.get("coverage_from")) if isinstance(scope, dict) else None
    scope_to = _date(scope.get("coverage_to")) if isinstance(scope, dict) else None
    if (scope_from is None or scope_to is None or scope_from > date(2026, 1, 1)
            or scope_to > search_as_of or scope_as_of is None or scope_as_of > search_as_of
            or scope_to > scope_as_of):
        gaps.append(_gap("scope_evidence_coverage_missing_or_invalid", "Verified scope evidence must explicitly cover the search period and end no later than as_of_date."))
    cessation = facts.get("cessation_evidence")
    cessation_date = _date(cessation.get("cessation_date")) if isinstance(cessation, dict) else None
    cessation_as_of = _date(cessation.get("as_of_date")) if isinstance(cessation, dict) else None
    if (facts.get("cessation_confirmed") is not True or not isinstance(cessation, dict)
            or cessation.get("verified") is not True or cessation_date is None
            or cessation_date > search_as_of or cessation_as_of is None
            or cessation_as_of < cessation_date or cessation_as_of > search_as_of
            or not _source_refs(cessation.get("source_refs"))):
        gaps.append(_gap("employee_cessation_evidence_missing", "Verified, source-bound employee cessation no later than the as-of date is required."))
    evidence = facts.get("contribution_evidence")
    first_contribution = _date(evidence.get("first_contribution_date")) if isinstance(evidence, dict) else None
    cohort_as_of = _date(evidence.get("as_of_date")) if isinstance(evidence, dict) else None
    cohort_period_end = _date(evidence.get("period_end")) if isinstance(evidence, dict) else None
    cutoff = _date(pack.get("post_1996_cohort_start"))
    if (facts.get("contribution_cohort_confirmed") is not True
            or facts.get("contribution_cohort") != "on_or_after_1996"
            or first_contribution is None or cutoff is None or first_contribution < cutoff
            or not isinstance(evidence, dict) or evidence.get("verified") is not True
            or not _source_refs(evidence.get("source_refs"))
            or cohort_as_of is None or cohort_period_end is None
            or cohort_period_end > cohort_as_of or cohort_as_of > search_as_of
            or first_contribution > cohort_period_end or first_contribution > search_as_of):
        gaps.append(_gap("post_1996_cohort_unconfirmed", "A dated, source-bound first contribution on or after 1996-01-01, confirmed by as_of_date and no later than the search as-of date, is required."))
    if not isinstance(monthly_history, list) or not monthly_history:
        gaps.append(_gap("monthly_history_missing", "A complete monthly contribution history is required."))
        monthly_history = []

    # Require one consecutive observation per month, beginning at pack coverage.
    expected_month = date(2026, 1, 1)
    observations: list[tuple[date, Decimal]] = []
    previous_total: Decimal | None = None
    for index, row in enumerate(monthly_history):
        month_text = row.get("month") if isinstance(row, dict) else None
        try:
            month = date.fromisoformat(f"{month_text}-01") if isinstance(month_text, str) else None
        except ValueError:
            month = None
        refs = row.get("source_refs") if isinstance(row, dict) else None
        as_of = _date(row.get("as_of_date")) if isinstance(row, dict) else None
        period_start = _date(row.get("period_start")) if isinstance(row, dict) else None
        period_end = _date(row.get("period_end")) if isinstance(row, dict) else None
        total = _decimal(row.get("effective_contribution_years_excluding_figurative")) if isinstance(row, dict) else None
        original_units = row.get("original_contribution_units") if isinstance(row, dict) else None
        if (not isinstance(original_units, list) or not original_units
                or any(not isinstance(item, str) or not item.strip() for item in original_units)
                or len(original_units) != 1 or original_units[0] != "years"):
            gaps.append(_gap("original_contribution_units_missing_or_unsupported", f"Monthly row {index + 1} must retain one verified original unit ('years'); mixed or converted units are unsupported."))
            break
        row_ok = (
            month is not None and month.day == 1 and month.isoformat()[:7] == month_text
            and month == expected_month and month <= date(2028, 12, 1)
            and isinstance(row, dict) and row.get("verified") is True
            and _source_refs(refs) and row.get("effective_contribution_unit") == "years"
            and isinstance(row.get("original_contribution_types"), list)
            and bool(row.get("original_contribution_types"))
            and all(isinstance(item, str) and item.strip() for item in row["original_contribution_types"])
            and row.get("figurative_excluded") is True and total is not None
            and (previous_total is None or total >= previous_total)
            and as_of is not None and period_start == month and period_end is not None
            and period_end == date(month.year, month.month, monthrange(month.year, month.month)[1])
            and period_end <= as_of <= search_as_of
            and (total == 0 or (first_contribution is not None and first_contribution <= period_end))
        )
        if not row_ok:
            gaps.append(_gap("monthly_history_invalid_or_incomplete", f"Monthly row {index + 1} is missing, non-consecutive, ambiguous, has unsupported original units, or is outside the dated source evidence."))
            break
        observations.append((month, total))
        previous_total = total
        expected_month = date(month.year + (month.month == 12), 1 if month.month == 12 else month.month + 1, 1)
    if gaps:
        return _month_search_not_assessed(pack, gaps, search_as_of)

    last_period_end = date(observations[-1][0].year, observations[-1][0].month,
                           monthrange(observations[-1][0].year, observations[-1][0].month)[1])
    if scope_from > date(2026, 1, 1) or scope_to < last_period_end:
        return _month_search_not_assessed(pack, [_gap(
            "scope_evidence_does_not_cover_history", "Source-bound employment and profile evidence must cover every observed candidate month."
        )], search_as_of)

    path = pack["paths"]["post_1996_alternative"]
    required_years = _decimal(path.get("minimum_effective_contribution_years"))
    if required_years is None or path.get("figurative_contribution_counts") is not False:
        return _month_search_not_assessed(pack, [_gap("unsupported_alternative_contribution_rule", "The loaded pack does not explicitly define the approved five-year non-figurative path.")], search_as_of)
    for month, effective_years in observations:
        month_end = date(month.year, month.month, monthrange(month.year, month.month)[1])
        if cessation_date is not None and cessation_date > month_end:
            continue
        age = _age_met(birth, month_end, pack["requirements_by_year"][str(month.year)]["contributory_alternative_age"])
        if age is None:
            return _month_search_not_assessed(pack, [_gap("age_day_semantics_unsupported", "The applicable alternative age threshold falls on an unsupported calendar date.")], search_as_of)
        if age and effective_years >= required_years:
            return {
                "schema_version": "italian-old-age-eligibility-month-search/v1",
                "status": "assessed", "result": "eligible", "path": "post_1996_alternative",
                "first_eligible_month": month.isoformat()[:7], "as_of_date": search_as_of.isoformat(),
                "human_review_required": True, "rule_pack_id": pack["rule_pack_id"],
                "data_gaps": [],
                "limitations": ["First eligible month within observed history and the 2026-2028 pack only; not the first overall eligibility date, an INPS decision, decorrenza, or payment date.", "Monthly evidence does not establish an exact day; no future contribution is projected."],
            }
    return {
        "schema_version": "italian-old-age-eligibility-month-search/v1",
        "status": "not_assessed", "result": None, "path": "post_1996_alternative",
        "first_eligible_month": None, "as_of_date": search_as_of.isoformat(),
        "human_review_required": True, "rule_pack_id": pack["rule_pack_id"],
        "data_gaps": [_gap("eligibility_not_found_in_observed_history", "No eligible month was established within the complete observed history; this is not a finding of ineligibility.")],
        "limitations": ["First eligible month within observed history and the 2026-2028 pack only; no future contribution is projected."],
    }


def search_first_post_1996_ordinary_threshold_eligibility_month(
    facts: dict[str, Any], monthly_history: list[dict[str, Any]],
    rule_pack_path: Path, as_of_date: str | date | None = None,
) -> dict[str, Any]:
    """Find the first observed month for the approved post-1995 20-year path.

    Contribution totals and pension amounts are snapshots supplied by distinct,
    source-bound records.  This consumer neither converts contribution units nor
    calculates or projects a pension amount, contribution total, or later month.
    """
    search_as_of = _date(as_of_date)
    if search_as_of is None:
        return _ordinary_month_search_not_assessed(None, [_gap(
            "as_of_date_missing_or_invalid", "An explicit ISO as_of_date is required for a reproducible month search."
        )])
    pack = _load_pack(rule_pack_path, search_as_of)
    gaps = _monthly_search_common_gaps(facts, pack, search_as_of)
    birth = _date(facts.get("date_of_birth"))
    evidence = facts.get("contribution_evidence")
    first_contribution = _date(evidence.get("first_contribution_date")) if isinstance(evidence, dict) else None
    cutoff = _date(pack.get("post_1996_cohort_start"))
    if (facts.get("contribution_cohort_confirmed") is not True
            or facts.get("contribution_cohort") != "on_or_after_1996"
            or first_contribution is None or cutoff is None or first_contribution < cutoff
            or not isinstance(evidence, dict) or evidence.get("verified") is not True
            or not _source_refs(evidence.get("source_refs"))
            or _date(evidence.get("as_of_date")) is None
            or _date(evidence.get("period_end")) is None
            or _date(evidence.get("period_end")) > _date(evidence.get("as_of_date"))
            or _date(evidence.get("as_of_date")) > search_as_of
            or first_contribution > _date(evidence.get("period_end"))):
        gaps.append(_gap("post_1996_cohort_unconfirmed", "A dated, source-bound first contribution on or after 1996-01-01 is required."))
    observations, history_gaps = _ordinary_monthly_observations(monthly_history, first_contribution, search_as_of)
    gaps.extend(history_gaps)
    if gaps:
        return _ordinary_month_search_not_assessed(pack, gaps, search_as_of)

    scope = facts["scope_evidence"]
    last_month_end = _month_end(observations[-1][0])
    if _date(scope.get("coverage_from")) > date(2026, 1, 1) or _date(scope.get("coverage_to")) < last_month_end:
        return _ordinary_month_search_not_assessed(pack, [_gap(
            "scope_evidence_does_not_cover_history", "Source-bound FPLD/AGO employee ordinary-profile evidence must cover every observed candidate month."
        )], search_as_of)

    qualifying_threshold = _decimal(pack["paths"]["post_1996"].get("minimum_qualifying_contribution_years"))
    threshold_rule = pack["paths"]["post_1996"].get("minimum_monthly_pension_threshold")
    if qualifying_threshold is None or threshold_rule != "documented_applicable_monthly_social_allowance":
        return _ordinary_month_search_not_assessed(pack, [_gap(
            "unsupported_threshold_rule", "The loaded pack does not define the approved 20-year amount-threshold path."
        )], search_as_of)
    cessation = facts["cessation_evidence"]
    cessation_date = _date(cessation.get("cessation_date"))
    for month, qualifying_years, pension_amount, amount_evidence, contribution_refs in observations:
        month_end = _month_end(month)
        if cessation_date > month_end:
            continue
        age = _age_met(birth, month_end, pack["requirements_by_year"][str(month.year)]["ordinary_age"])
        if age is None:
            return _ordinary_month_search_not_assessed(pack, [_gap(
                "age_day_semantics_unsupported", "The applicable ordinary age threshold falls on an unsupported calendar date."
            )], search_as_of)
        if not age or qualifying_years < qualifying_threshold:
            continue
        threshold_binding = pack["threshold_bindings"]["post_1996_ordinary"]["by_year"].get(str(month.year))
        if not isinstance(threshold_binding, dict) or threshold_binding.get("status") != "supported":
            return _ordinary_month_search_not_assessed(pack, [_gap(
                "monthly_social_allowance_threshold_not_source_bound",
                "The first month with proven age and 20 years has no source-bound annual social-allowance threshold in this rule-pack."
            )], search_as_of)
        rule_amount = _decimal(threshold_binding.get("monthly_amount"))
        if (threshold_binding.get("currency") != "EUR"
                or threshold_binding.get("payments_per_year") != 13 or rule_amount is None):
            raise ItalianOldAgeEligibilityError("Italian old-age eligibility has invalid annual threshold metadata")
        if not _monthly_amount_evidence_applies(amount_evidence, pension_amount, month, month_end, search_as_of, contribution_refs):
            return _ordinary_month_search_not_assessed(pack, [_gap(
                "monthly_pension_amount_evidence_missing_or_not_applicable",
                "A separate, source-bound documented pension amount applicable to the candidate month is required."
            )], search_as_of)
        if pension_amount >= rule_amount:
            return _ordinary_month_search_result(pack, "eligible", month, search_as_of)
    return _ordinary_month_search_not_assessed(pack, [_gap(
        "eligibility_not_found_in_observed_history", "No eligible month was established within the complete observed history; this is not a finding of ineligibility."
    )], search_as_of)


def _monthly_search_common_gaps(facts: dict[str, Any], pack: dict[str, Any], search_as_of: date) -> list[dict[str, str]]:
    gaps = _scope_gaps(facts, pack["supported_scope"])
    birth = _date(facts.get("date_of_birth"))
    if birth is None or facts.get("date_of_birth_verified") is not True or not _source_refs(facts.get("date_of_birth_source_refs")):
        gaps.append(_gap("date_of_birth_missing_or_unverified", "A verified, source-bound ISO date of birth is required."))
    elif birth.day == monthrange(birth.year, birth.month)[1]:
        gaps.append(_gap("age_day_semantics_unsupported", "Month-end birth dates require approved age-day semantics."))
    scope = facts.get("scope_evidence")
    if not isinstance(scope, dict) or any(_date(scope.get(field)) is None for field in ("as_of_date", "coverage_from", "coverage_to")) or not _source_refs(scope.get("source_refs")):
        gaps.append(_gap("scope_evidence_coverage_missing_or_invalid", "Verified scope evidence must cover the observed history."))
    elif (_date(scope.get("coverage_to")) > search_as_of or _date(scope.get("as_of_date")) > search_as_of
          or _date(scope.get("coverage_to")) > _date(scope.get("as_of_date"))):
        gaps.append(_gap("scope_evidence_coverage_missing_or_invalid", "Scope evidence cannot extend beyond its date or the search as-of date."))
    cessation = facts.get("cessation_evidence")
    if (facts.get("cessation_confirmed") is not True or not isinstance(cessation, dict)
            or cessation.get("verified") is not True or _date(cessation.get("cessation_date")) is None
            or _date(cessation.get("as_of_date")) is None or _date(cessation.get("cessation_date")) > search_as_of
            or _date(cessation.get("as_of_date")) > search_as_of
            or _date(cessation.get("as_of_date")) < _date(cessation.get("cessation_date"))
            or not _source_refs(cessation.get("source_refs"))):
        gaps.append(_gap("employee_cessation_evidence_missing", "Verified, source-bound employee cessation evidence is required."))
    return gaps


def _ordinary_monthly_observations(monthly_history: Any, first_contribution: date | None, search_as_of: date) -> tuple[list[tuple[date, Decimal, Decimal, dict[str, Any], list[str]]], list[dict[str, str]]]:
    if not isinstance(monthly_history, list) or not monthly_history:
        return [], [_gap("monthly_history_missing", "A complete monthly contribution history is required.")]
    observations = []
    expected_month = date(2026, 1, 1)
    previous_total: Decimal | None = None
    for index, row in enumerate(monthly_history):
        month_text = row.get("month") if isinstance(row, dict) else None
        try:
            month = date.fromisoformat(f"{month_text}-01") if isinstance(month_text, str) else None
        except ValueError:
            month = None
        total = _decimal(row.get("qualifying_contribution_years")) if isinstance(row, dict) else None
        pension = _decimal(row.get("documented_monthly_pension_amount")) if isinstance(row, dict) else None
        refs = row.get("source_refs") if isinstance(row, dict) else None
        row_ok = (
            isinstance(row, dict) and month is not None and month.isoformat()[:7] == month_text
            and month == expected_month and month <= date(2028, 12, 1) and row.get("verified") is True
            and _source_refs(refs) and row.get("qualifying_contribution_unit") == "years"
            and row.get("original_contribution_units") == ["years"]
            and isinstance(row.get("original_contribution_types"), list) and bool(row["original_contribution_types"])
            and all(isinstance(item, str) and item.strip() for item in row["original_contribution_types"])
            and total is not None and pension is not None and (previous_total is None or total >= previous_total)
            and _date(row.get("as_of_date")) is not None and _date(row.get("period_start")) == month
            and _date(row.get("period_end")) == _month_end(month) and _date(row.get("period_end")) <= _date(row.get("as_of_date")) <= search_as_of
            and (total == 0 or (first_contribution is not None and first_contribution <= _month_end(month)))
        )
        if not row_ok:
            return [], [_gap("monthly_history_invalid_or_incomplete", f"Monthly row {index + 1} is missing, non-consecutive, non-monotonic, converted, or outside dated source evidence.")]
        observations.append((month, total, pension, row.get("monthly_pension_amount_evidence"), refs))
        previous_total = total
        expected_month = date(month.year + (month.month == 12), 1 if month.month == 12 else month.month + 1, 1)
    return observations, []


def _monthly_amount_evidence_applies(evidence: Any, pension_amount: Decimal, month: date, month_end: date, search_as_of: date, contribution_refs: list[str]) -> bool:
    if not isinstance(evidence, dict) or evidence.get("verified") is not True or not _source_refs(evidence.get("source_refs")):
        return False
    evidence_as_of = _date(evidence.get("as_of_date"))
    if (not set(evidence["source_refs"]).isdisjoint(set(contribution_refs))
            or evidence_as_of is None or evidence_as_of < month_end or evidence_as_of > search_as_of
            or _decimal(evidence.get("documented_monthly_pension_amount")) != pension_amount):
        return False
    valid_for_month = evidence.get("valid_for_month")
    if valid_for_month == month.isoformat()[:7]:
        return True
    valid_from, valid_to = _date(evidence.get("valid_from")), _date(evidence.get("valid_to"))
    return valid_for_month is None and valid_from is not None and valid_to is not None and valid_from <= month and valid_to >= month_end


def _month_end(month: date) -> date:
    return date(month.year, month.month, monthrange(month.year, month.month)[1])


def _ordinary_month_search_result(pack: dict[str, Any], result: str, month: date, search_as_of: date) -> dict[str, Any]:
    return {"schema_version": "italian-old-age-eligibility-month-search/v1", "status": "assessed", "result": result,
            "path": "post_1996_ordinary_threshold", "first_eligible_month": month.isoformat()[:7] if result == "eligible" else None,
            "as_of_date": search_as_of.isoformat(), "human_review_required": True, "rule_pack_id": pack["rule_pack_id"], "data_gaps": [],
            "limitations": ["First assessed month within observed history and the 2026-2028 pack only; not the first overall eligibility date, an INPS decision, decorrenza, or payment date.", "No contribution or pension amount is converted, calculated, or projected."]}


def _ordinary_month_search_not_assessed(pack: dict[str, Any] | None, gaps: list[dict[str, str]], as_of_date: date | None = None) -> dict[str, Any]:
    return {"schema_version": "italian-old-age-eligibility-month-search/v1", "status": "not_assessed", "result": None,
            "path": "post_1996_ordinary_threshold", "first_eligible_month": None,
            "as_of_date": as_of_date.isoformat() if as_of_date else None, "human_review_required": True,
            "rule_pack_id": pack["rule_pack_id"] if pack else None, "data_gaps": gaps,
            "limitations": ["First assessed month within observed history and the 2026-2028 pack only; no future contribution or pension amount is projected."]}


def _month_search_not_assessed(
    pack: dict[str, Any], gaps: list[dict[str, str]], as_of_date: date | None = None
) -> dict[str, Any]:
    return {
        "schema_version": "italian-old-age-eligibility-month-search/v1",
        "status": "not_assessed", "result": None, "path": "post_1996_alternative",
        "first_eligible_month": None,
        "as_of_date": as_of_date.isoformat() if as_of_date is not None else None,
        "human_review_required": True, "rule_pack_id": pack["rule_pack_id"],
        "data_gaps": gaps,
        "limitations": ["First eligible month within observed history and the 2026-2028 pack only; no future contribution is projected."],
    }


def _load_pack(path: Path, as_of_date: str | date | None) -> dict[str, Any]:
    try:
        require_fresh_pension_rule_pack(path, as_of_date)
        pack = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, PensionSourceFreshnessError) as exc:
        raise ItalianOldAgeEligibilityError(str(exc)) from exc
    if not isinstance(pack, dict) or not all(key in pack for key in ("schema_version", "rule_pack_id", "jurisdiction", "valid_from", "valid_to", "requirements_by_year", "paths", "supported_scope", "post_1996_cohort_start", "source_refs")):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility rule pack is structurally invalid")
    valid_from, valid_to = _date(pack["valid_from"]), _date(pack["valid_to"])
    if (pack["schema_version"] != "inps-old-age-eligibility-rule-pack/v2"
            or pack["rule_pack_id"] != "it.inps-old-age-eligibility.2026-2028.v2"
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
            or pack["supported_scope"].get("management_scope") != "FPLD_employee_only"
            or pack["supported_scope"]["managements"] != ["FPLD"]
            or not isinstance(pack["supported_scope"].get("excluded_management_categories"), list)
            or pack["supported_scope"].get("employment_category") != "employee"
            or pack["supported_scope"].get("ordinary_single_management_profile_required") is not True):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility pack has invalid supported scope")
    if (pack["paths"]["post_1996"].get("minimum_monthly_pension_threshold") != "documented_applicable_monthly_social_allowance"
            or pack["paths"]["post_1996_alternative"].get("figurative_contribution_counts") is not False):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility pack has unsupported path semantics")
    threshold_binding = pack.get("threshold_bindings", {}).get("post_1996_ordinary")
    if (not isinstance(threshold_binding, dict)
            or threshold_binding.get("rule") != "documented_monthly_pension_amount_gte_applicable_monthly_social_allowance"
            or threshold_binding.get("source_ids") != ["normattiva.dl-201-2011.art24", "inps.pensione-vecchiaia", "inps.assegno-sociale-2026"]
            or not isinstance(threshold_binding.get("by_year"), dict)
            or threshold_binding["by_year"].get("2026", {}).get("status") != "supported"
            or threshold_binding["by_year"].get("2026", {}).get("monthly_amount") != "546.24"
            or threshold_binding["by_year"].get("2026", {}).get("currency") != "EUR"
            or threshold_binding["by_year"].get("2026", {}).get("payments_per_year") != 13
            or threshold_binding["by_year"].get("2027", {}).get("status") != "gap"
            or threshold_binding["by_year"].get("2028", {}).get("status") != "gap"):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility lacks source-bound threshold metadata")
    sources = pack["source_refs"]
    if not isinstance(sources, list) or not sources:
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility pack has no legal sources")
    provision_periods: dict[str, list[tuple[str, date | None, date | None, date, date]]] = {}
    adjustment_months_by_provision: dict[str, list[tuple[str, int | None]]] = {}
    source_ids: list[str] = []
    for source in sources:
        periods = source.get("provision_periods") if isinstance(source, dict) else None
        if not isinstance(source, dict) or not isinstance(source.get("provisions"), list) or not source["provisions"] or not isinstance(periods, list) or not periods:
            raise ItalianOldAgeEligibilityError("Italian old-age eligibility source lacks provisions or provision periods")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ItalianOldAgeEligibilityError("Italian old-age eligibility source has invalid source ID")
        source_ids.append(source_id)
        for period in periods:
            legal_start = _date(period.get("legal_effective_from")) if isinstance(period, dict) and period.get("legal_effective_from") is not None else None
            legal_end = _date(period.get("legal_effective_to")) if isinstance(period, dict) and period.get("legal_effective_to") is not None else None
            legal_start_raw = period.get("legal_effective_from") if isinstance(period, dict) else None
            legal_end_raw = period.get("legal_effective_to") if isinstance(period, dict) else None
            coverage_start = _date(period.get("pack_coverage_from")) if isinstance(period, dict) else None
            coverage_end = _date(period.get("pack_coverage_to")) if isinstance(period, dict) else None
            provision_id = period.get("provision_id") if isinstance(period, dict) else None
            adjustment_months = period.get("adjustment_months") if isinstance(period, dict) else None
            if (coverage_start is None or coverage_end is None or coverage_start > coverage_end
                    or (legal_start_raw is not None and legal_start is None)
                    or (legal_end_raw is not None and legal_end is None)
                    or (legal_start is None and legal_end is not None)
                    or (legal_start is not None and legal_end is not None and legal_start > legal_end)
                    or (adjustment_months is not None and (not isinstance(adjustment_months, int) or isinstance(adjustment_months, bool) or adjustment_months < 0))
                    or not isinstance(provision_id, str) or not provision_id.strip()):
                raise ItalianOldAgeEligibilityError("Italian old-age eligibility source has invalid provision periods")
            provision_periods.setdefault(provision_id, []).append((source_id, legal_start, legal_end, coverage_start, coverage_end))
            adjustment_months_by_provision.setdefault(provision_id, []).append((source_id, adjustment_months))
    if len(source_ids) != len(set(source_ids)):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility pack has duplicate source IDs")
    required_source_roles = {
        "inps.pensione-vecchiaia": "administrative_guidance",
        "normattiva.dl-201-2011.art24": "primary_legislation",
        "normattiva.l199-2025.art1.c185": "primary_legislation",
        "gazzetta.decreto-19-12-2025.25a07010": "binding_implementing_act",
        "gazzetta.decreto-06-12-2011.11a16083": "binding_implementing_act",
        "gazzetta.decreto-16-12-2014.14a09922": "binding_implementing_act",
        "gazzetta.decreto-05-12-2017.17a08386": "binding_implementing_act",
        "gazzetta.decreto-05-11-2019.19a07047": "binding_implementing_act",
        "gazzetta.decreto-27-10-2021.21a06556": "binding_implementing_act",
        "gazzetta.decreto-18-07-2023.23a05661": "binding_implementing_act",
        "inps.circolare-62-2018": "administrative_guidance",
        "inps.requisiti-2027-2028": "administrative_guidance",
    }
    sources_by_id = {source.get("source_id"): source for source in sources if isinstance(source, dict)}
    allowance_source = sources_by_id.get("inps.assegno-sociale-2026")
    if (not isinstance(allowance_source, dict)
            or allowance_source.get("jurisdiction") != "IT"
            or allowance_source.get("legal_role") != "administrative_guidance"
            or allowance_source.get("url") != "https://www.inps.it/it/it/dettaglio-scheda.it.schede-servizio-strumento.schede-servizi.assegno-sociale-50184.assegno-sociale.html"
            or provision_periods.get("social_allowance_amount_2026") != [("inps.assegno-sociale-2026", date(2026, 1, 1), date(2026, 12, 31), date(2026, 1, 1), date(2026, 12, 31))]):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility lacks exact social-allowance source binding")
    for source_id, legal_role in required_source_roles.items():
        source = sources_by_id.get(source_id)
        if source is None or source.get("legal_role") != legal_role:
            raise ItalianOldAgeEligibilityError("Italian old-age eligibility lacks required source hierarchy metadata")
    inps_page = "inps.pensione-vecchiaia"
    inps_update = "inps.requisiti-2027-2028"
    source_age_schedule: dict[str, Any] = {}
    expected_source_years = {inps_page: {"2026"}, inps_update: {"2027", "2028"}}
    for source_id, expected_years in expected_source_years.items():
        source_schedule = sources_by_id[source_id].get("requirements_by_year")
        if not isinstance(source_schedule, dict) or set(source_schedule) != expected_years:
            raise ItalianOldAgeEligibilityError("Italian old-age eligibility source lacks its age schedule")
        source_age_schedule.update(source_schedule)
    if source_age_schedule != pack["requirements_by_year"]:
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility age schedule conflicts with its source-bound schedule")
    coverage_2026_2028 = (date(2026, 1, 1), date(2028, 12, 31))
    required_provisions = {
        "ordinary_age_2026": (inps_page, None, None, date(2026, 1, 1), date(2026, 12, 31)),
        "ordinary_age_adjustment_2027_2028": (inps_update, None, None, date(2027, 1, 1), date(2028, 12, 31)),
        "contribution_threshold": (inps_page, None, None, *coverage_2026_2028),
        "post_1996_amount_threshold": (inps_page, None, None, *coverage_2026_2028),
        "post_1996_effective_contribution_alternative": (inps_page, None, None, *coverage_2026_2028),
        "employee_cessation": (inps_page, None, None, *coverage_2026_2028),
        "ordinary_and_contributory_old_age_base": ("normattiva.dl-201-2011.art24", date(2011, 12, 6), None, *coverage_2026_2028),
        "historic_adjustment_2013": ("gazzetta.decreto-06-12-2011.11a16083", date(2013, 1, 1), None, *coverage_2026_2028),
        "historic_adjustment_2016": ("gazzetta.decreto-16-12-2014.14a09922", date(2016, 1, 1), None, *coverage_2026_2028),
        "historic_adjustment_2019": ("gazzetta.decreto-05-12-2017.17a08386", date(2019, 1, 1), None, *coverage_2026_2028),
        "historic_age_schedule_from_2019": ("inps.circolare-62-2018", None, None, *coverage_2026_2028),
        "historic_pause_2021": ("gazzetta.decreto-05-11-2019.19a07047", date(2021, 1, 1), date(2022, 12, 31), *coverage_2026_2028),
        "historic_pause_2023_2024": ("gazzetta.decreto-27-10-2021.21a06556", date(2023, 1, 1), date(2024, 12, 31), *coverage_2026_2028),
        "historic_pause_2025_2026": ("gazzetta.decreto-18-07-2023.23a05661", date(2025, 1, 1), date(2026, 12, 31), *coverage_2026_2028),
        "2027_adjustment_modulation": ("normattiva.l199-2025.art1.c185", date(2025, 12, 30), None, date(2027, 1, 1), date(2028, 12, 31)),
        "2027_2028_life_expectancy_adjustment": ("gazzetta.decreto-19-12-2025.25a07010", date(2027, 1, 1), None, date(2027, 1, 1), date(2028, 12, 31)),
    }
    if any(provision_periods.get(provision) != [expected] for provision, expected in required_provisions.items()):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility lacks exact source-owned provision-period coverage")
    required_adjustments = {
        "historic_adjustment_2013": ("gazzetta.decreto-06-12-2011.11a16083", 3),
        "historic_adjustment_2016": ("gazzetta.decreto-16-12-2014.14a09922", 4),
        "historic_adjustment_2019": ("gazzetta.decreto-05-12-2017.17a08386", 5),
    }
    if any(adjustment_months_by_provision.get(provision) != [expected] for provision, expected in required_adjustments.items()):
        raise ItalianOldAgeEligibilityError("Italian old-age eligibility lacks exact cumulative adjustment metadata")
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
