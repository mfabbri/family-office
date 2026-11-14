import json
import calendar
from decimal import Decimal, InvalidOperation
from datetime import date
from pathlib import Path
from typing import Any

from family_office_engine.governance.pension_source_freshness import (
    PensionSourceFreshnessError,
    require_fresh_pension_rule_pack,
)

RULE_PACK_SCHEMA_VERSION = "spanish-statutory-pension-rule-pack/v1"
ORDINARY_RG_DAILY_CONTRACT_VERSION = "rd453-article-3.1-domestic-filing/v1"
_ARTICLE_3_2_EXCLUSIONS = ("3.2.a", "3.2.b", "3.2.c", "3.2.d", "3.2.e")
_ORDINARY_RG_SOURCE_BINDINGS = {
    "boe.rd-453-2022.official-publication": (
        "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2022-9850",
        "primary_publication",
        ("Articulo 3.1", "Articulo 3.2.a-e", "Articulo 3.3", "Disposicion transitoria unica", "Disposicion final decima"),
    ),
    "boe.codigo-civil.official-publication": (
        "https://www.boe.es/buscar/act.php?id=BOE-A-1889-4763",
        "official_consolidated_consultation",
        ("Articulo 5.1",),
    ),
    "boe.lgss.rdl-8-2015.official-publication": (
        "https://www.boe.es/boe/dias/2015/10/31/pdfs/BOE-A-2015-11724.pdf",
        "primary_publication",
        ("Articulos 165-166", "Articulo 205.1(b)", "Articulo 205.3", "Articulo 144.4"),
    ),
    "boe.lgss.rdl-8-2015.current-consolidated-2026-11-14": (
        "https://www.boe.es/buscar/act.php?id=BOE-A-2015-11724",
        "official_consolidated_consultation",
        ("Articulos 165-166", "Articulo 205.1(b)", "Articulo 205.3", "Articulo 144.4"),
    ),
    "boe.rdl-31-2026.official-publication": (
        "https://www.boe.es/eli/es/rdl/2026/10/20/31",
        "primary_publication_currentness_delta",
        ("Articulo primero.Dos (modifies LGSS 144.4)", "Disposicion final cuarta.2"),
    ),
    "boe.rdl-35-2026.official-publication": (
        "https://www.boe.es/eli/es/rdl/2026/11/10/35",
        "primary_publication_currentness_delta",
        ("Disposicion final tercera", "Disposicion final decima"),
    ),
}


class SpanishPensionRulesError(ValueError):
    pass


def load_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    try:
        require_fresh_pension_rule_pack(rule_pack_path)
    except PensionSourceFreshnessError as exc:
        raise SpanishPensionRulesError(str(exc)) from exc
    try:
        data = json.loads(rule_pack_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpanishPensionRulesError(f"Spanish pension rule pack not found: {rule_pack_path}") from exc
    except json.JSONDecodeError as exc:
        raise SpanishPensionRulesError(f"Spanish pension rule pack is not valid JSON: {rule_pack_path}") from exc
    _validate_rule_pack(data)
    return data


def validate_ordinary_rg_daily_contract(
    rule_pack: dict[str, Any], evidence: dict[str, Any], as_of_date: str | date
) -> dict[str, Any]:
    """Validate only the bounded art. 3.1 evidence contract; never assess a person."""
    gaps: list[dict[str, str]] = []
    contract = rule_pack.get("ordinary_rg_daily_contract") if isinstance(rule_pack, dict) else None
    if not isinstance(contract, dict) or contract.get("contract_version") != ORDINARY_RG_DAILY_CONTRACT_VERSION:
        gaps.append(_contract_gap("contract_version_unsupported", "The approved daily contract is missing or unsupported."))
        contract = {}
    else:
        try:
            _validate_ordinary_rg_daily_contract(contract, contract.get("source_refs"))
        except (SpanishPensionRulesError, TypeError, ValueError) as exc:
            gaps.append(_contract_gap("contract_definition_invalid", str(exc)))

    try:
        as_of = _contract_date(as_of_date, "as_of_date")
    except ValueError as exc:
        as_of = None
        gaps.append(_contract_gap("as_of_date_invalid", str(exc)))

    contract_interval = _check_contract_currentness(contract, as_of, gaps)
    if not isinstance(evidence, dict):
        evidence = {}
        gaps.append(_contract_gap("evidence_record_missing", "Evidence must be an object."))

    candidate = _read_contract_date(evidence, "candidate_date", gaps)
    filing = _read_contract_date(evidence, "authoritative_filing_date", gaps)
    _require_evidence_ref(evidence.get("filing_evidence_ref"), "filing_evidence_ref", gaps)
    if filing is not None and as_of is not None and filing > as_of:
        gaps.append(_contract_gap("authoritative_filing_date_after_as_of", "An authoritative filing date after as_of_date is not established as an actual filing."))
    filing_conflicting = evidence.get("filing_conflicting")
    if filing_conflicting is not False:
        code = "authoritative_filing_evidence_conflicting" if filing_conflicting is True else "authoritative_filing_conflict_status_unknown"
        gaps.append(_contract_gap(code, "The authoritative filing evidence must explicitly state that it is non-conflicting."))

    if evidence.get("application_kind") != "actual":
        gaps.append(_contract_gap("actual_application_required", "Only an evidenced actual application is in this contract."))
    if evidence.get("filing_country") != "ES" or evidence.get("filing_scope") != "domestic":
        gaps.append(_contract_gap("domestic_filing_required", "International or non-domestic filing is outside this contract."))
    if evidence.get("international_filing") is not False:
        gaps.append(_contract_gap("international_filing_status_unknown", "Evidence must affirmatively exclude an international filing route."))
    _require_evidence_ref(evidence.get("filing_scope_evidence_ref"), "filing_scope_evidence_ref", gaps)

    if candidate is not None:
        if candidate < date(2022, 6, 16):
            gaps.append(_contract_gap("candidate_before_contract_start", "Candidate predates RD 453/2022 applicability for this path."))
        if as_of is not None and candidate > as_of:
            gaps.append(_contract_gap("candidate_outside_currentness", "Candidate is outside the exact reviewed contract interval or after as_of_date."))
        if contract_interval is not None:
            valid_from, valid_to = contract_interval
            if candidate < valid_from or candidate >= valid_to:
                gaps.append(_contract_gap("candidate_outside_currentness", "Candidate is outside the exact reviewed contract interval or after as_of_date."))

    if candidate is not None and filing is not None:
        lower = _shift_calendar_months(filing, -3)
        upper = _shift_calendar_months(filing, 3)
        if not lower <= candidate <= upper:
            gaps.append(_contract_gap("candidate_outside_inclusive_three_month_window", "Candidate is outside the inclusive date-to-date three-calendar-month window."))

    scope = evidence.get("ordinary_rg_scope")
    if not isinstance(scope, dict) or scope.get("assertion") != "ordinary_rg":
        gaps.append(_contract_gap("ordinary_rg_scope_unknown", "Ordinary RG scope requires explicit individual evidence."))
    if not isinstance(scope, dict) or not _require_evidence_ref(scope.get("evidence_ref"), "ordinary_rg_scope.evidence_ref", gaps):
        pass

    exclusions = evidence.get("article_3_2_exclusions")
    if not isinstance(exclusions, dict):
        exclusions = {}
    for branch in _ARTICLE_3_2_EXCLUSIONS:
        item = exclusions.get(branch)
        if not isinstance(item, dict):
            gaps.append(_contract_gap(f"article_{branch.replace('.', '_')}_evidence_unknown", f"Individual evidence for exclusion {branch} is missing."))
            continue
        if item.get("finding") != "not_applicable":
            gaps.append(_contract_gap(f"article_{branch.replace('.', '_')}_evidence_unknown", f"Exclusion {branch} is applicable, conflicting, or not assessed."))
        if item.get("provision") != branch or item.get("conflicting") is not False:
            gaps.append(_contract_gap(f"article_{branch.replace('.', '_')}_evidence_conflicting", f"Exclusion evidence must be branch-specific and non-conflicting for {branch}."))
        if not _require_evidence_ref(item.get("evidence_ref"), f"article_3_2_exclusions.{branch}.evidence_ref", gaps):
            continue

    article_3_3 = evidence.get("article_3_3_exclusion")
    if not isinstance(article_3_3, dict) or article_3_3.get("finding") != "not_applicable":
        gaps.append(_contract_gap("article_3_3_evidence_unknown", "Individual evidence that art. 3.3 is not applicable is required."))
    if not isinstance(article_3_3, dict) or article_3_3.get("provision") != "Articulo 3.3" or article_3_3.get("conflicting") is not False:
        gaps.append(_contract_gap("article_3_3_evidence_conflicting", "Art. 3.3 evidence must be source-bound, specific, and non-conflicting."))
    if isinstance(article_3_3, dict):
        _require_evidence_ref(article_3_3.get("evidence_ref"), "article_3_3_exclusion.evidence_ref", gaps)

    if evidence.get("eu_periods_status") != "none_proven":
        code = "eu_coordination_out_of_scope" if evidence.get("eu_periods_status") == "present" else "eu_periods_unknown"
        gaps.append(_contract_gap(code, "EU/foreign periods must be explicitly absent; unknown and present periods are out of scope."))
    if evidence.get("eu_periods_status") == "none_proven":
        _require_evidence_ref(evidence.get("eu_periods_evidence_ref"), "eu_periods_evidence_ref", gaps)
    if any(key in evidence for key in ("eu_periods", "eu_aggregation", "pro_rata")):
        gaps.append(_contract_gap("eu_coordination_out_of_scope", "EU periods, aggregation and pro-rata are excluded."))

    blocking_gaps = list(gaps)
    gaps.extend([
        _contract_gap("individual_eligibility_not_assessed", "This validator does not determine individual eligibility."),
        _contract_gap("status_and_obligation_not_assessed", "Individual legal status and contribution obligation remain not assessed."),
        _contract_gap("lgss_205_1_b_anchor_not_assessed", "The individual LGSS 205.1(b) anchor remains unknown without status, obligation and cessation evidence."),
        _contract_gap("hecho_causante_not_assessed", "The candidate date is not emitted as an individual's hecho causante."),
        _contract_gap("article_4_outcomes_not_assessed", "Recognition, economic effects and payment are outside this contract."),
    ])
    status = "contract_valid" if not blocking_gaps else "unknown"
    return {
        "contract_version": ORDINARY_RG_DAILY_CONTRACT_VERSION,
        "contract_validation_status": status,
        "candidate_date": candidate.isoformat() if candidate else None,
        "authoritative_filing_date": filing.isoformat() if filing else None,
        "eligibility": "not_assessed",
        "legal_status": "not_assessed",
        "contribution_obligation": "not_assessed",
        "lgss_205_1_b_anchor": "not_assessed",
        "hecho_causante": {"status": "not_assessed", "date": None},
        "recognition": "not_assessed",
        "economic_effect": "not_assessed",
        "payment": "not_assessed",
        "human_review_required": True,
        "data_gaps": gaps,
    }


def _check_contract_currentness(
    contract: dict[str, Any], as_of: date | None, gaps: list[dict[str, str]]
) -> tuple[date, date] | None:
    try:
        valid_from = _contract_date(contract.get("valid_from"), "contract.valid_from")
        valid_to = _contract_date(contract.get("valid_to"), "contract.valid_to")
        reviewed_through = _contract_date(contract.get("reviewed_through"), "contract.reviewed_through")
        source_evidence_as_of = _contract_date(contract.get("source_evidence_as_of"), "contract.source_evidence_as_of")
    except ValueError as exc:
        gaps.append(_contract_gap("contract_currentness_unknown", str(exc)))
        return None
    if valid_from >= valid_to or reviewed_through >= valid_to:
        gaps.append(_contract_gap("contract_currentness_invalid", "The contract interval or review cutoff is inconsistent."))
    if source_evidence_as_of != reviewed_through:
        gaps.append(_contract_gap("contract_currentness_invalid", "The source evidence cutoff must match reviewed_through."))
    if as_of is not None and as_of < source_evidence_as_of:
        gaps.append(_contract_gap("contract_source_evidence_cutoff_gap", "as_of_date predates the reviewed source evidence cutoff."))
    if as_of is not None and (as_of < valid_from or as_of >= valid_to or as_of > reviewed_through):
        gaps.append(_contract_gap("contract_currentness_gap", "as_of_date is outside the explicitly reviewed half-open interval."))
    return valid_from, valid_to


def _read_contract_date(evidence: dict[str, Any], field: str, gaps: list[dict[str, str]]) -> date | None:
    try:
        return _contract_date(evidence.get(field), field)
    except ValueError as exc:
        gaps.append(_contract_gap(f"{field}_unknown", str(exc)))
        return None


def _contract_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must use canonical ISO date format")
    return parsed


def _shift_calendar_months(value: date, months: int) -> date:
    absolute_month = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(absolute_month, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _require_evidence_ref(value: Any, field: str, gaps: list[dict[str, str]]) -> bool:
    if not isinstance(value, str) or not value.strip():
        gaps.append(_contract_gap("evidence_reference_missing", f"{field} must identify the supporting evidence."))
        return False
    return True


def _contract_gap(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


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
    contract = data.get("ordinary_rg_daily_contract")
    _validate_ordinary_rg_daily_contract(contract, contract.get("source_refs") if isinstance(contract, dict) else None)


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


def _validate_ordinary_rg_daily_contract(contract: Any, source_refs: Any) -> None:
    if not isinstance(contract, dict):
        raise SpanishPensionRulesError("Spanish pension rule pack missing ordinary_rg_daily_contract")
    if contract.get("contract_version") != ORDINARY_RG_DAILY_CONTRACT_VERSION:
        raise SpanishPensionRulesError("Unsupported ordinary RG daily contract version")
    if contract.get("path") != "RD_453_2022_ARTICLE_3_1" or contract.get("status") != "validator_only_not_individual_eligibility":
        raise SpanishPensionRulesError("Daily contract path/status must remain non-decisional art. 3.1")
    if contract.get("validity_semantics") != "half_open":
        raise SpanishPensionRulesError("Daily contract validity must explicitly be half-open")
    try:
        start = _contract_date(contract.get("valid_from"), "ordinary_rg_daily_contract.valid_from")
        end = _contract_date(contract.get("valid_to"), "ordinary_rg_daily_contract.valid_to")
        reviewed = _contract_date(contract.get("reviewed_through"), "ordinary_rg_daily_contract.reviewed_through")
        minimum_candidate = _contract_date(contract.get("minimum_candidate_date"), "ordinary_rg_daily_contract.minimum_candidate_date")
    except ValueError as exc:
        raise SpanishPensionRulesError(str(exc)) from exc
    try:
        source_evidence_as_of = _contract_date(contract.get("source_evidence_as_of"), "ordinary_rg_daily_contract.source_evidence_as_of")
    except ValueError as exc:
        raise SpanishPensionRulesError("Daily contract source evidence cutoff must be a valid ISO date") from exc
    if not (start < end and reviewed < end and reviewed.toordinal() + 1 == end.toordinal()):
        raise SpanishPensionRulesError("Daily contract half-open interval must end the day after reviewed_through")
    if source_evidence_as_of != reviewed:
        raise SpanishPensionRulesError("Daily contract source evidence cutoff must match reviewed_through")
    if minimum_candidate != date(2022, 6, 16):
        raise SpanishPensionRulesError("Daily contract minimum candidate date must match RD 453/2022 entry into force")
    application = contract.get("application")
    if not isinstance(application, dict) or application.get("window_months") != 3 or application.get("window_boundary") != "inclusive" or application.get("month_arithmetic") != "codigo_civil_article_5_1_date_to_date_last_day_when_no_equivalent":
        raise SpanishPensionRulesError("Daily contract must bind the inclusive three-month window to Código Civil art. 5.1")
    if application.get("must_be_actual") is not True or application.get("filing_scope") != "domestic_only":
        raise SpanishPensionRulesError("Daily contract requires an actual domestic filing")
    expected_application_fields = {"candidate_date", "authoritative_filing_date", "filing_evidence_ref", "filing_conflicting"}
    application_fields = application.get("required_fields")
    if (
        not isinstance(application_fields, list)
        or len(application_fields) != len(expected_application_fields)
        or set(application_fields) != expected_application_fields
        or application.get("conflict_flag_required") is not True
    ):
        raise SpanishPensionRulesError("Daily contract must require an explicit authoritative filing conflict flag")
    if contract.get("article_3_2_exclusion_branches") != list(_ARTICLE_3_2_EXCLUSIONS) or contract.get("generic_no_special_case_boolean_is_insufficient") is not True:
        raise SpanishPensionRulesError("Daily contract must require individual evidence for every art. 3.2(a-e) exclusion")
    if contract.get("article_3_2_exclusion_conflict_flag_required") is not True:
        raise SpanishPensionRulesError("Daily contract must require an explicit conflict flag for every art. 3.2 exclusion")
    article_3_3 = contract.get("article_3_3_exclusion")
    if article_3_3 != {
        "source_provision": "Articulo 3.3",
        "required_finding": "not_applicable",
        "conflict_flag_required": True,
        "required_evidence_ref": True,
    }:
        raise SpanishPensionRulesError("Daily contract must require explicit source-bound non-conflicting art. 3.3 exclusion evidence")
    if contract.get("human_review_required") is not True:
        raise SpanishPensionRulesError("Daily contract must require human review")
    required_roles = contract.get("required_source_roles")
    if not isinstance(source_refs, list) or not isinstance(required_roles, list) or not required_roles:
        raise SpanishPensionRulesError("Daily contract source roles and source refs are required")
    expected_source_ids = set(_ORDINARY_RG_SOURCE_BINDINGS)
    expected_required_provisions = {
        source_id: list(expected[2]) for source_id, expected in _ORDINARY_RG_SOURCE_BINDINGS.items()
    }
    expected_roles_by_id = {
        source_id: expected[1] for source_id, expected in _ORDINARY_RG_SOURCE_BINDINGS.items()
    }
    expected_roles = set(expected_roles_by_id.values())
    if len(source_refs) != len(expected_source_ids):
        raise SpanishPensionRulesError("Daily contract source_refs must contain the exact approved source cardinality")
    _validate_source_refs(source_refs)
    source_ids = [source.get("source_id") for source in source_refs if isinstance(source, dict)]
    if len(source_ids) != len(source_refs) or any(not isinstance(source_id, str) or not source_id for source_id in source_ids):
        raise SpanishPensionRulesError("Daily contract source_refs must use non-empty source IDs")
    if len(source_ids) != len(set(source_ids)):
        raise SpanishPensionRulesError("Daily contract source IDs must be unique")
    if set(source_ids) != expected_source_ids:
        raise SpanishPensionRulesError("Daily contract source IDs must match the exact approved manifest")
    for source in source_refs:
        source_id = source["source_id"]
        expected_url, expected_role, expected_provisions = _ORDINARY_RG_SOURCE_BINDINGS[source_id]
        if not str(source.get("url")).startswith("https://www.boe.es/"):
            raise SpanishPensionRulesError("Daily contract sources must use official BOE URLs")
        if source.get("authority") != "Agencia Estatal Boletin Oficial del Estado":
            raise SpanishPensionRulesError("Daily contract sources must identify the official BOE authority")
        if source.get("jurisdiction") != "ES":
            raise SpanishPensionRulesError("Daily contract sources must have ES jurisdiction")
        if source.get("url") != expected_url:
            raise SpanishPensionRulesError(f"Daily contract source URL does not match the approved locator: {source_id}")
        if source.get("source_role") != expected_role:
            raise SpanishPensionRulesError(f"Daily contract source role does not match the approved role: {source_id}")
        provisions = source.get("provisions")
        if not isinstance(provisions, list) or len(provisions) != len(expected_provisions) or set(provisions) != set(expected_provisions):
            raise SpanishPensionRulesError(f"Daily contract source provisions do not match the approved set: {source_id}")
        try:
            retrieved = _contract_date(source.get("retrieved_on"), "contract_source.retrieved_on")
            source_reviewed = _contract_date(source.get("reviewed_on"), "contract_source.reviewed_on")
            review_due = _contract_date(source.get("next_review_due"), "contract_source.next_review_due")
        except ValueError as exc:
            raise SpanishPensionRulesError(str(exc)) from exc
        if retrieved > source_reviewed or source_reviewed > reviewed or review_due <= source_reviewed:
            raise SpanishPensionRulesError("Daily contract source review dates are inconsistent with the reviewed-through cutoff")
    actual_roles = {source.get("source_role") for source in source_refs if isinstance(source, dict)}
    if len(required_roles) != len(set(required_roles)) or set(required_roles) != expected_roles or actual_roles != expected_roles:
        raise SpanishPensionRulesError("Daily contract source roles must match the exact approved role set")
    required_sources = contract.get("required_source_provisions")
    if required_sources != expected_required_provisions:
        raise SpanishPensionRulesError("Daily contract required source provisions must match the exact approved manifest")
    required_source_ids = contract.get("required_source_ids")
    if not isinstance(required_source_ids, list) or len(required_source_ids) != len(expected_source_ids) or set(required_source_ids) != expected_source_ids:
        raise SpanishPensionRulesError("Daily contract must enumerate the exact approved source IDs")
    by_id = {source.get("source_id"): source for source in source_refs if isinstance(source, dict)}
    roles_by_id = contract.get("required_source_roles_by_id")
    if roles_by_id != expected_roles_by_id:
        raise SpanishPensionRulesError("Daily contract source roles by ID must match the exact approved manifest")
    for source_id, provisions in expected_required_provisions.items():
        source = by_id.get(source_id)
        if not isinstance(source, dict) or not isinstance(provisions, list) or not set(provisions).issubset(set(source.get("provisions", []))):
            raise SpanishPensionRulesError(f"Daily contract source/provision binding is incomplete: {source_id}")
        if source.get("source_role") != roles_by_id[source_id]:
            raise SpanishPensionRulesError(f"Daily contract source role does not match required role for {source_id}")


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
