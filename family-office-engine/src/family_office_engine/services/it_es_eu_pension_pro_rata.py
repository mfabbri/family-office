import json
import hashlib
import calendar
import math
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from family_office_engine.governance.pension_source_freshness import (
    PensionSourceFreshnessError,
    require_fresh_pension_rule_pack,
)

SCHEMA_VERSION = "it-es-eu-pension-pro-rata/v1"
INPUT_SCHEMA_VERSION = "it-es-eu-pension-pro-rata-input/v1"
RECORD_TYPE = "ItEsEuPensionProRataEstimate"
RULE_PACK_SCHEMA_VERSION = "eu-pension-coordination-rule-pack/v2"


class ItEsEuPensionProRataError(ValueError):
    pass


def build_it_es_eu_pension_pro_rata(
    input_path: Path,
    rule_pack_path: Path,
    output_path: Path,
    spanish_theoretical_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    data = _read_json(input_path, "IT-ES EU pension pro-rata input")
    rule_pack = load_rule_pack(rule_pack_path)
    if data.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise ItEsEuPensionProRataError(f"Unsupported IT-ES EU pension pro-rata input schema: {data.get('schema_version')}")
    if spanish_theoretical_snapshot_path is not None:
        data = dict(data)
        data["spanish_theoretical_pension"] = _theoretical_from_snapshot(spanish_theoretical_snapshot_path)

    retirement_date = _retirement_date(data)
    date_of_birth = data.get("date_of_birth")
    recent_anchor = data.get("recent_contribution_anchor_date")
    periods_result = _normalize_periods(data.get("insurance_periods"))
    input_gaps = _input_readiness_gaps(data)
    entitlement = _spanish_entitlement(
        periods_result,
        retirement_date,
        date_of_birth,
        recent_anchor,
        data.get("spanish_insured_or_equivalent_status"),
        rule_pack,
    )
    theoretical = _spanish_theoretical_amount(data.get("spanish_theoretical_pension"))
    article_57 = _article_57_assessment(data.get("article_57_assessment"), rule_pack)
    pro_rata = _spanish_pro_rata(theoretical, periods_result, entitlement, rule_pack, article_57)
    data_gaps = []
    data_gaps.extend(_declared_data_gaps(data, theoretical))
    data_gaps.extend(input_gaps)
    data_gaps.extend(periods_result["data_gaps"])
    data_gaps.extend(_post_retirement_period_gaps(periods_result, retirement_date))
    data_gaps.extend(entitlement["data_gaps"])
    data_gaps.extend(theoretical["data_gaps"])
    data_gaps.extend(article_57["data_gaps"])
    data_gaps.extend(pro_rata["data_gaps"])

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "status": _status(entitlement, pro_rata, data_gaps),
        "retirement_date": retirement_date,
        "scenario": data.get("scenario", "ordinary"),
        "rule_pack": {
            "path": str(rule_pack_path),
            "rule_pack_id": rule_pack["rule_pack_id"],
            "schema_version": rule_pack["schema_version"],
            "sha256": _file_sha256(rule_pack_path),
            "valid_from": rule_pack["spanish_ordinary_entitlement"]["valid_from"],
            "valid_to": rule_pack["spanish_ordinary_entitlement"]["valid_to"],
            "source_refs": rule_pack["source_refs"],
            "limitations": rule_pack["limitations"],
        },
        "sources": data.get("sources", []),
        "periods": periods_result["summary"],
        "overlaps": periods_result["overlaps"],
        "spanish_entitlement": entitlement["result"],
        "article_57": article_57["result"],
        "spanish_theoretical_pension": theoretical["result"],
        "spanish_pro_rata_pension": pro_rata["result"],
        "data_gaps": data_gaps,
        "warnings": _warnings(periods_result),
        "notes": (
            "EU coordination can aggregate periods for entitlement and theoretical/pro-rata calculation under the "
            "rule pack. Italian periods are not transferred, merged, or used as Spanish contribution bases, and "
            "this candidate-only estimate is not an official P1 decision, recognition, or payment determination."
        ),
    }
    return _write_snapshot(snapshot, output_path)


def _declared_data_gaps(data: dict[str, Any], theoretical: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = data.get("data_gaps", []) if isinstance(data.get("data_gaps"), list) else []
    if theoretical.get("result") is None:
        return list(gaps)
    resolved_by_theoretical_snapshot = {
        "missing_spanish_theoretical_amount",
        "missing_spanish_theoretical_pension",
    }
    return [gap for gap in gaps if gap.get("code") not in resolved_by_theoretical_snapshot]


def load_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    data = _read_json(rule_pack_path, "EU pension coordination rule pack")
    required = (
        "schema_version",
        "rule_pack_id",
        "jurisdictions",
        "source_refs",
        "coordination_principles",
        "spanish_ordinary_entitlement",
        "pro_rata_method",
        "limitations",
    )
    for field in required:
        if field not in data:
            raise ItEsEuPensionProRataError(f"EU pension coordination rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise ItEsEuPensionProRataError(f"Unsupported EU pension coordination rule pack schema: {data['schema_version']}")
    if set(data["jurisdictions"]) != {"IT", "ES", "EU"}:
        raise ItEsEuPensionProRataError("EU pension coordination jurisdictions must be IT, ES and EU")
    _validate_source_refs(data["source_refs"])
    try:
        require_fresh_pension_rule_pack(rule_pack_path)
    except PensionSourceFreshnessError as exc:
        raise ItEsEuPensionProRataError(str(exc)) from exc
    if data["coordination_principles"].get("no_transfer_or_merger_of_contributions") is not True:
        raise ItEsEuPensionProRataError("Rule pack must forbid transfer or merger of contributions")
    if data["coordination_principles"].get("aggregation_for_entitlement_and_theoretical_calculation") is not True:
        raise ItEsEuPensionProRataError(
            "Rule pack must explicitly allow aggregation for entitlement and theoretical calculation"
        )
    if data["pro_rata_method"].get("no_foreign_bases_in_spanish_theoretical_amount") is not True:
        raise ItEsEuPensionProRataError("Rule pack must forbid foreign bases in Spanish theoretical amount")
    article_57 = data["pro_rata_method"].get("article_57_source_bound")
    if not isinstance(article_57, dict):
        raise ItEsEuPensionProRataError("Rule pack must define pro_rata_method.article_57_source_bound")
    if article_57.get("contract_schema_version") != "v0.25" or article_57.get("canonicalization_profile") != "fo-art57-c14n-v4":
        raise ItEsEuPensionProRataError("Rule pack Article 57 contract must be v0.25/fo-art57-c14n-v4")
    if article_57.get("human_review_required") is not True:
        raise ItEsEuPensionProRataError("Rule pack Article 57 contract must require human review")
    last_state_policy = article_57.get("last_state_attestation")
    if (
        not isinstance(last_state_policy, dict)
        or last_state_policy.get("malformed_input_action") != "not_assessed_with_data_gaps"
        or last_state_policy.get("registry_binding_required") is not True
        or last_state_policy.get("does_not_emit_legal_last_state_output") is not True
        or last_state_policy.get("registry_controls_are_internal_provenance_not_legal_presumptions") is not True
        or last_state_policy.get("required_evidence_categories") != ["selection", "conditions", "comparability", "event", "applicable_legislation", "institutional_records"]
    ):
        raise ItEsEuPensionProRataError("Rule pack Article 57 last-State fail-closed registry policy is required")
    annex_policy = article_57.get("annex_viii_part_2")
    if (
        not isinstance(annex_policy, dict)
        or not _canonical_string(annex_policy.get("applicable_annex_part_2_version"))
        or not _iso_date(annex_policy.get("applicable_annex_part_2_valid_from"))
        or (annex_policy.get("applicable_annex_part_2_valid_to") is not None and not _iso_date(annex_policy.get("applicable_annex_part_2_valid_to")))
    ):
        raise ItEsEuPensionProRataError("Rule pack Article 57 Annex VIII applicability version and ISO validity dates are required")
    overlap_policy = data["pro_rata_method"].get("overlap_policy")
    if not isinstance(overlap_policy, dict):
        raise ItEsEuPensionProRataError("Rule pack must define pro_rata_method.overlap_policy")
    return data


def _normalize_periods(periods: Any) -> dict[str, Any]:
    if not isinstance(periods, list) or not periods:
        return {
            "summary": _empty_period_summary(),
            "months": {"IT": set(), "ES": set(), "EU": set()},
            "overlaps": [],
            "data_gaps": [{"code": "missing_dated_insurance_periods", "message": "Dated insurance periods are required."}],
        }

    country_months = {"IT": set(), "ES": set()}
    provenance: dict[str, set[str]] = {"IT": set(), "ES": set()}
    data_gaps: list[dict[str, Any]] = []
    for index, period in enumerate(periods):
        if not isinstance(period, dict):
            raise ItEsEuPensionProRataError(f"Insurance period at index {index} must be an object.")
        country = period.get("country")
        if country not in country_months:
            raise ItEsEuPensionProRataError(f"Unsupported insurance period country at index {index}: {country}")
        source = period.get("source_document") or period.get("source") or "explicit-input"
        period_type = period.get("period_type", "unknown")
        if period_type == "unknown":
            data_gaps.append(
                {
                    "code": "missing_period_type",
                    "message": "Insurance period type is required to review overlap priority.",
                    "period_index": index,
                    "country": country,
                }
            )
        months = _months_between(period.get("start_date"), period.get("end_date"), index)
        if not months:
            data_gaps.append(
                {
                    "code": "empty_insurance_period",
                    "message": "Insurance period does not cover any month.",
                    "period_index": index,
                    "country": country,
                }
            )
        country_months[country].update(months)
        provenance[country].add(str(source))

    total_months = country_months["IT"] | country_months["ES"]
    overlapping = sorted(country_months["IT"] & country_months["ES"])
    if overlapping:
        data_gaps.append(
            {
                "code": "unclassified_it_es_period_overlap",
                "message": (
                    "Italy-Spain overlapping periods require type, order, and institutional classification under "
                    "Regulation 987/2009 Article 12; monthly de-duplication alone is not sufficient."
                ),
                "overlap_month_count": len(overlapping),
            }
        )
    return {
        "summary": {
            "status": "normalized",
            "italy_months": len(country_months["IT"]),
            "spain_months": len(country_months["ES"]),
            "total_eu_non_overlapping_months": len(total_months),
            "overlap_month_count": len(overlapping),
            "ratio_inputs": {
                "ES": {
                    "numerator_months": len(country_months["ES"]),
                    "denominator_months": len(total_months),
                }
            },
            "provenance": {country: sorted(values) for country, values in provenance.items()},
        },
        "months": {"IT": country_months["IT"], "ES": country_months["ES"], "EU": total_months},
        "overlaps": [{"month": month, "countries": ["IT", "ES"]} for month in overlapping],
        "data_gaps": data_gaps,
    }


def _spanish_entitlement(
    periods_result: dict[str, Any],
    retirement_date: str,
    date_of_birth: Any,
    recent_anchor: Any,
    spanish_insured_or_equivalent_status: Any,
    rule_pack: dict[str, Any],
) -> dict[str, Any]:
    params = rule_pack["spanish_ordinary_entitlement"]
    es_months = periods_result["months"]["ES"]
    eu_months = periods_result["months"]["EU"]
    lookback_months = int(params["specific_contribution_lookback_months"])
    required_total = int(params["minimum_total_contribution_months"])
    required_recent = int(params["specific_contribution_months_within_lookback"])
    gaps: list[dict[str, Any]] = []
    retirement_year = int(retirement_date[:4])
    if not _date_in_rule_period(retirement_date, params):
        gaps.append(
            {
                "code": "retirement_date_not_covered_by_rule_pack",
                "message": "Retirement date is outside the encoded Spanish ordinary entitlement period.",
                "retirement_date": retirement_date,
                "valid_from": params["valid_from"],
                "valid_to": params["valid_to"],
            }
        )
    if not isinstance(date_of_birth, str):
        gaps.append({"code": "missing_date_of_birth", "message": "Date of birth is required for Spanish ordinary age checks."})
    if not isinstance(recent_anchor, str):
        gaps.append(
            {
                "code": "missing_recent_contribution_anchor_date",
                "message": "A declared anchor date is required for the Spanish recent-contribution lookback.",
            }
        )
    if params.get("insured_or_equivalent_status_required") is True:
        if spanish_insured_or_equivalent_status is None:
            gaps.append(
                {
                    "code": "missing_spanish_insured_or_equivalent_status",
                    "message": "Spanish insured-or-equivalent status is required for the encoded Article 205 specific-period check.",
                }
            )
        elif spanish_insured_or_equivalent_status is not True:
            gaps.append(
                {
                    "code": "spanish_insured_or_equivalent_status_not_confirmed",
                    "message": "Spanish insured-or-equivalent status is not confirmed for the encoded Article 205 specific-period check.",
                }
            )
    if periods_result["overlaps"]:
        gaps.append(
            {
                "code": "unclassified_it_es_period_overlap",
                "message": "Italy-Spain overlap requires Article 12 institutional classification before entitlement or pro-rata determination.",
                "overlap_month_count": len(periods_result["overlaps"]),
            }
        )
    lookback_anchor = recent_anchor[:7] if isinstance(recent_anchor, str) else retirement_date
    lookback = set(_lookback_window(lookback_anchor, lookback_months))
    es_recent = len(es_months & lookback)
    eu_recent = len(eu_months & lookback)
    age_check = _ordinary_age_check(date_of_birth, retirement_date, len(eu_months), params)
    if not age_check["eligible"]:
        gaps.append(age_check["gap"])
    autonomous = len(es_months) >= required_total and es_recent >= required_recent and age_check["eligible"] and not _blocking_rule_gap(gaps)
    totalized = len(eu_months) >= required_total and eu_recent >= required_recent and age_check["eligible"] and not _blocking_rule_gap(gaps)
    if not totalized and not _blocking_rule_gap(gaps):
        gaps.append(
            {
                "code": "spanish_entitlement_not_reached_even_with_totalization",
                "message": "Spanish ordinary entitlement thresholds are not met with non-overlapping EU periods.",
                "total_eu_months": len(eu_months),
                "required_total_months": required_total,
                "recent_eu_months": eu_recent,
                "required_recent_months": required_recent,
            }
        )

    return {
        "result": {
            "status": "eligible_autonomous" if autonomous else "eligible_by_totalization" if totalized else "not_eligible",
            "autonomous": {
                "eligible": autonomous,
                "spanish_months": len(es_months),
                "recent_spanish_months": es_recent,
            },
            "totalized": {
                "eligible": totalized,
                "total_eu_months": len(eu_months),
                "recent_eu_months": eu_recent,
                "aggregation_for_entitlement_and_theoretical_calculation": True,
            },
            "thresholds": {
                "minimum_total_contribution_months": required_total,
                "specific_contribution_months_within_lookback": required_recent,
                "specific_contribution_lookback_months": lookback_months,
            },
            "age_check": age_check["result"],
            "recent_contribution_anchor_date": recent_anchor,
        },
        "data_gaps": gaps,
    }


def _spanish_theoretical_amount(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "result": None,
            "data_gaps": [
                {
                    "code": "missing_spanish_theoretical_pension",
                    "message": "Spanish theoretical pension amount is required for pro-rata calculation.",
                }
            ],
        }
    monthly = value.get("monthly_gross_amount")
    annual = value.get("annual_gross_amount")
    payments = value.get("payments_per_year")
    source_country = value.get("source_country")
    basis = value.get("basis")
    gaps = value.get("data_gaps", []) if isinstance(value.get("data_gaps"), list) else []
    if source_country != "ES":
        gaps.append(
            {
                "code": "spanish_theoretical_source_country_not_es",
                "message": "Spanish theoretical amount must declare source_country ES.",
            }
        )
    if basis != "spanish_only_bases":
        gaps.append(
            {
                "code": "spanish_theoretical_basis_not_spanish_only",
                "message": "Spanish theoretical amount must declare basis spanish_only_bases.",
            }
        )
    if payments is None:
        gaps.append({"code": "missing_payments_per_year", "message": "payments_per_year is required."})
    if monthly is None and annual is None:
        return {
            "result": None,
            "data_gaps": gaps + [
                {
                    "code": "missing_spanish_theoretical_amount",
                    "message": "At least monthly or annual Spanish theoretical gross amount is required.",
                }
            ],
        }
    monthly_decimal = _decimal(monthly, "spanish_theoretical_pension.monthly_gross_amount") if monthly is not None else None
    annual_decimal = _decimal(annual, "spanish_theoretical_pension.annual_gross_amount") if annual is not None else None
    if payments is None:
        payments = 1
    if monthly_decimal is None:
        monthly_decimal = annual_decimal / _decimal(payments, "payments_per_year")
    if annual_decimal is None:
        annual_decimal = monthly_decimal * _decimal(payments, "payments_per_year")
    if monthly is not None and annual is not None:
        expected = _round_money(monthly_decimal * _decimal(payments, "payments_per_year"))
        if expected != _round_money(annual_decimal):
            gaps.append(
                {
                    "code": "inconsistent_theoretical_monthly_annual_amounts",
                    "message": "Monthly amount times payments_per_year does not match annual amount.",
                }
            )
    return {
        "result": {
            "monthly_gross_amount": _money(monthly_decimal),
            "annual_gross_amount": _money(annual_decimal),
            "currency": value.get("currency", "EUR"),
            "payments_per_year": int(payments),
            "source": value.get("source", "explicit_input"),
            "source_country": source_country,
            "basis": basis,
        },
        "data_gaps": gaps,
    }


def _theoretical_from_snapshot(snapshot_path: Path) -> dict[str, Any]:
    snapshot = _read_json(snapshot_path, "Spanish EU theoretical pension snapshot")
    if snapshot.get("schema_version") != "spanish-eu-theoretical-pension/v1":
        raise ItEsEuPensionProRataError(f"Unsupported Spanish theoretical pension snapshot schema: {snapshot.get('schema_version')}")
    theoretical = snapshot.get("spanish_theoretical_pension")
    if snapshot.get("status") == "complete" and isinstance(theoretical, dict):
        return dict(theoretical)
    return {
        "source": str(snapshot_path),
        "source_country": "ES",
        "basis": "spanish_only_bases",
        "data_gaps": [
            {
                "code": "spanish_theoretical_snapshot_not_complete",
                "message": "Spanish EU theoretical pension snapshot is not complete.",
                "source_status": snapshot.get("status"),
            }
        ],
    }


def _article_57_assessment(value: Any, rule_pack: dict[str, Any]) -> dict[str, Any]:
    policy = rule_pack["pro_rata_method"]["article_57_source_bound"]
    base = {
        "human_review_required": True,
        "national_eligibility_status": "not_assessed",
        "article_57_exception_status": "not_assessed",
        "theoretical_amount_period_inclusion": "not_assessed",
        "pro_rata_amount_status": "not_assessed",
        "national_payment_obligation_status": "not_assessed",
    }
    if not isinstance(value, dict):
        return _article_57_not_assessed(base, "missing_article_57_source_bound_assessment", "A v0.25/fo-art57-c14n-v4 source-bound Article 57 assessment is required.")
    _validate_article_57_contract(value, policy)
    manifest = _article_57_coordination_manifest(value.get("coordination_manifest"))
    institutions = _article_57_institutional_records(value.get("concerned_institutions"), manifest)
    if manifest is None or institutions is None:
        gaps = _article_57_duration_binding_gaps(value)
        gaps.append(_article_57_gap("missing_article_57_multi_institution_evidence", "A valid manifest and institutional Article 57(1) records are required."))
        return {"result": base, "data_gaps": gaps}
    if manifest["contingency_date"] != value["risk_materialization_date"] or manifest["as_of_date"] != value["assessment_date"]:
        return _article_57_not_assessed(base, "inconsistent_article_57_coordination_manifest", "The manifest must bind the root dates.")
    institution_refs = sorted((record["institution_ref"] for record in institutions), key=lambda item: item.encode("utf-8"))
    perimeter_gap = _article_57_full_perimeter_scope_gap(value.get("institution_scope_evidence"), manifest, institution_refs, value.get("evidence_registry"))
    if perimeter_gap is not None:
        return {"result": base, "data_gaps": [perimeter_gap]}
    institutional_registry_gap = _article_57_institutional_registry_binding_gap(
        institutions, manifest, institution_refs, value.get("evidence_registry")
    )
    if institutional_registry_gap is not None:
        return {"result": base, "data_gaps": [institutional_registry_gap]}
    if _transitional_result(value["transitional_applicability"], value["member_state"], value["risk_materialization_date"]) is None:
        return _article_57_not_assessed(base, "missing_article_57_transitional_applicability", "A decisive transitional applicability record is not assessed.")
    duration_binding_gaps = _article_57_duration_binding_gaps(value)
    duration = value.get("duration_strictly_less_than_one_year")
    if duration is None:
        duration_binding_gaps.append(_article_57_gap("missing_article_57_legal_duration", "Legal duration and comparator evidence do not establish the Article 57 result."))
    autonomous = _source_bound_result(value.get("autonomous_right_from_state_periods_only"), "autonomous_right_from_state_periods_only", policy, value)
    annex = _source_bound_result(value.get("annex_viii_part_2_applicability"), "annex_viii_part_2_applicability", policy, value)
    if duration_binding_gaps or annex["result"] is None:
        gaps = list(duration_binding_gaps)
        if annex["result"] is None:
            gaps.append(_article_57_gap("missing_article_57_annex_viii_part_2_catalogue", "A complete, applicable, machine-readable Annex VIII part 2 validity catalogue is required; no match or non-match is inferred."))
        return {"result": base, "data_gaps": gaps}
    root_record = next((record for record in institutions if record["institution_ref"] == value["root_institution_ref"]), None)
    if root_record is None or not _article_57_root_reconciles(value, root_record, autonomous["result"]):
        return _article_57_not_assessed(base, "inconsistent_article_57_root_institution_binding", "Root predicates must match the source-bound institution record.")
    if annex["result"] is True:
        base.update({
            "article_57_exception_status": "excluded_by_57_4",
            "theoretical_amount_period_inclusion": "not_triggered",
            "pro_rata_amount_status": "downstream_not_assessed",
            "national_payment_obligation_status": "not_assessed",
        })
        return {"result": base, "data_gaps": []}
    if duration is False or autonomous["result"] is True:
        base.update({
            "article_57_exception_status": "does_not_apply",
            "theoretical_amount_period_inclusion": "not_triggered",
            "pro_rata_amount_status": "downstream_not_assessed",
            "national_payment_obligation_status": "ordinary_article_52",
        })
        return {"result": base, "data_gaps": []}
    gaps = []
    if duration is None:
        gaps.append(_article_57_gap("missing_article_57_legal_duration", "Legal duration and comparator evidence do not establish the Article 57 result."))
    if autonomous["result"] is None:
        gaps.append(_article_57_gap("missing_article_57_autonomous_right_evidence", "Autonomous-right evidence is required for Article 57."))
    if gaps:
        return {"result": base, "data_gaps": gaps}
    # At this point the three Art. 57(1) predicates are source-bound and true/false.
    base.update({
        "article_57_exception_status": "applies",
        "theoretical_amount_period_inclusion": "required_by_57_2",
        "pro_rata_amount_status": "downstream_not_assessed",
        "national_payment_obligation_status": "not_assessed",
    })
    if not all(record["article_57_1_relief_result"] for record in institutions):
        return {"result": base, "data_gaps": []}
    last_state = value.get("last_state_attestation")
    last_state_gap = _article_57_last_state_registry_binding_gap(
        last_state, manifest, institutions, institution_refs, value["assessment_date"], value.get("evidence_registry")
    )
    if last_state_gap is not None:
        base.update({
            "article_57_exception_status": "not_assessed",
            "theoretical_amount_period_inclusion": "not_assessed",
            "pro_rata_amount_status": "not_assessed",
            "national_payment_obligation_status": "not_assessed",
        })
        return {"result": base, "data_gaps": [last_state_gap]}
    base["national_payment_obligation_status"] = "not_assessed"
    return {"result": base, "data_gaps": []}


def _validate_article_57_contract(value: dict[str, Any], policy: dict[str, Any]) -> None:
    allowed = {
        "contract_schema_version", "canonicalization_profile", "human_review_required", "member_state", "benefit_id", "benefit_type", "scheme_id", "competent_institution", "root_institution_ref", "root_local_claim_ref", "root_local_benefit_ref",
        "applicable_legislation_id", "applicable_legislation_version", "applicable_legislation_valid_from", "applicable_legislation_valid_to", "risk_materialization_date", "assessment_date",
        "transitional_applicability", "legal_duration_for_article_57", "one_year_comparator", "duration_basis", "duration_assessment_evidence_refs", "duration_strictly_less_than_one_year",
        "duration_source_segment", "autonomous_right_from_state_periods_only", "annex_viii_part_2_applicability", "coordination_manifest", "concerned_institutions", "institution_scope_evidence",
        "last_state_attestation", "evidence_registry",
    }
    if "schema_version" in value or set(value) - allowed:
        raise ItEsEuPensionProRataError("Article 57 assessment has forbidden root schema_version or fields.")
    if value.get("contract_schema_version") != policy["contract_schema_version"] or value.get("canonicalization_profile") != policy["canonicalization_profile"]:
        raise ItEsEuPensionProRataError("Article 57 assessment must use v0.25/fo-art57-c14n-v4; legacy contracts are rejected.")
    if value.get("human_review_required") is not True:
        raise ItEsEuPensionProRataError("Article 57 assessment must require human review.")
    required_root_strings = (
        "member_state", "benefit_id", "benefit_type", "scheme_id", "competent_institution", "root_institution_ref",
        "applicable_legislation_id", "applicable_legislation_version",
    )
    if any(not _canonical_string(value.get(field)) for field in required_root_strings):
        raise ItEsEuPensionProRataError("Article 57 assessment requires canonical root member-state, benefit, scheme, institution, and legislation bindings.")
    if not _article_57_local_reference(value.get("root_local_claim_ref"), value["root_institution_ref"]) or not _article_57_local_reference(value.get("root_local_benefit_ref"), value["root_institution_ref"]):
        raise ItEsEuPensionProRataError("Article 57 assessment requires source-bound root local claim and benefit references.")
    for field in ("risk_materialization_date", "assessment_date", "applicable_legislation_valid_from"):
        if not _iso_date(value.get(field)):
            raise ItEsEuPensionProRataError(f"Article 57 assessment requires ISO {field}.")
    valid_to = value.get("applicable_legislation_valid_to")
    if valid_to is not None and not _iso_date(valid_to):
        raise ItEsEuPensionProRataError("Article 57 assessment requires ISO applicable_legislation_valid_to or null.")
    if not _date_in_range(value["risk_materialization_date"], value["applicable_legislation_valid_from"], valid_to):
        raise ItEsEuPensionProRataError("Article 57 risk materialization date is outside the bound legislation validity period.")
    if not isinstance(value.get("transitional_applicability"), dict):
        raise ItEsEuPensionProRataError("Article 57 assessment requires a transitional applicability record.")
    for field in ("legal_duration_for_article_57", "one_year_comparator"):
        record = value.get(field)
        if not isinstance(record, dict) or not record.get("unit") or "value" not in record:
            raise ItEsEuPensionProRataError(f"Article 57 assessment missing source-bound {field}.")
    if not isinstance(value.get("duration_basis"), str) or not isinstance(value.get("duration_assessment_evidence_refs"), list) or not value["duration_assessment_evidence_refs"]:
        raise ItEsEuPensionProRataError("Article 57 assessment requires duration basis and evidence.")
    if type(value.get("duration_strictly_less_than_one_year")) not in {bool, type(None)}:
        raise ItEsEuPensionProRataError("Article 57 duration result must be true, false, or null.")


def _article_57_duration_binding_gaps(value: dict[str, Any]) -> list[dict[str, Any]]:
    duration = value["legal_duration_for_article_57"]
    comparator = value["one_year_comparator"]
    duration_value = _rational_value(duration.get("value"))
    comparator_value = _rational_value(comparator.get("value"))
    segment = value.get("duration_source_segment")
    if duration_value is None or comparator_value is None or duration.get("unit") != comparator.get("unit"):
        return [_article_57_gap("invalid_article_57_duration_comparator_binding", "Legal duration and one-year comparator must be canonical rationals in the same source-bound unit.")]
    if not isinstance(comparator.get("legal_basis_refs"), list) or not comparator["legal_basis_refs"]:
        return [_article_57_gap("missing_article_57_comparator_legal_basis", "The one-year comparator requires legal-basis references.")]
    if not isinstance(segment, dict) or set(segment) != {"segment_id", "preimage"} or not isinstance(segment.get("segment_id"), str) or not isinstance(segment.get("preimage"), dict):
        return [_article_57_gap("missing_article_57_duration_source_segment", "The legal duration requires a v0.20 canonical source-segment preimage and hash.")]
    source_duration = _c14n_v4_duration_source_bound(segment["preimage"])
    if source_duration is None:
        return [_article_57_gap("invalid_article_57_duration_source_segment", "The Article 57 segment must satisfy the c14n-v4 duration grammar.")]
    expected = "sha256:" + hashlib.sha256(
        json.dumps(segment["preimage"], ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    if segment["segment_id"] != expected or duration.get("source_segment_id") != expected or source_duration != (duration_value, duration.get("unit")):
        return [_article_57_gap("invalid_article_57_duration_source_segment", "The legal duration must bind to the matching canonical v0.20 segment hash.")]
    predicate = value["duration_strictly_less_than_one_year"]
    comparison = _rational_less_than(duration_value, comparator_value)
    if predicate is not None and predicate is not comparison:
        return [_article_57_gap("inconsistent_article_57_duration_predicate", "The supplied ternary duration predicate conflicts with its source-bound duration and comparator.")]
    return []


def _rational_value(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        return None
    numerator, denominator = value["numerator"], value["denominator"]
    if isinstance(numerator, bool) or isinstance(denominator, bool) or not isinstance(numerator, int) or not isinstance(denominator, int) or numerator < 0 or denominator <= 0:
        return None
    if numerator == 0:
        return (0, 1) if denominator == 1 else None
    if math.gcd(numerator, denominator) != 1:
        return None
    return numerator, denominator


def _rational_less_than(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] * right[1] < right[0] * left[1]


def _c14n_v4_duration_source_bound(preimage: dict[str, Any]) -> tuple[tuple[int, int], str] | None:
    if set(preimage) != {"canonicalization_profile", "parent_period_refs", "schema_version", "source_bounds"}:
        return None
    if preimage.get("schema_version") != "v0.19" or preimage.get("canonicalization_profile") != "fo-art57-c14n-v4":
        return None
    parent_refs = preimage.get("parent_period_refs")
    bounds = preimage.get("source_bounds")
    if not _canonical_string_list(parent_refs) or len(parent_refs) != 1 or parent_refs != sorted(parent_refs, key=lambda item: item.encode("utf-8")) or not isinstance(bounds, list) or len(bounds) != 1:
        return None
    bound = bounds[0]
    if not isinstance(bound, dict) or set(bound) != {"native_duration", "native_end", "native_start", "period_ref"} or bound.get("period_ref") != parent_refs[0] or bound.get("native_start") is not None or bound.get("native_end") is not None:
        return None
    native_duration = bound.get("native_duration")
    if not isinstance(native_duration, dict) or set(native_duration) != {"precision", "unit", "value"} or native_duration.get("precision") != "exact" or not _canonical_string(native_duration.get("unit")):
        return None
    rational = _rational_value(native_duration.get("value"))
    return (rational, native_duration["unit"]) if rational is not None else None


def _article_57_coordination_manifest(value: Any) -> dict[str, Any] | None:
    required = {"manifest_ref", "case_ref", "coordinated_benefit_ref", "contingency_date", "issuer_institution_ref", "as_of_date", "evidence_refs"}
    if not isinstance(value, dict) or set(value) != required:
        return None
    if any(not _canonical_string(value[field]) for field in ("manifest_ref", "case_ref", "coordinated_benefit_ref", "issuer_institution_ref")):
        return None
    if not _iso_date(value["contingency_date"]) or not _iso_date(value["as_of_date"]) or not _nonempty_string_list(value["evidence_refs"]):
        return None
    return value


def _article_57_local_reference(value: Any, institution_ref: str) -> bool:
    return isinstance(value, dict) and set(value) == {"issuer_institution_ref", "namespace", "value", "evidence_refs"} and value["issuer_institution_ref"] == institution_ref and all(_canonical_string(value[field]) for field in ("issuer_institution_ref", "namespace", "value")) and _nonempty_string_list(value["evidence_refs"])


def _article_57_full_perimeter_scope(value: Any, manifest: dict[str, Any], institution_refs: list[str], registry: Any) -> bool:
    return _article_57_full_perimeter_scope_gap(value, manifest, institution_refs, registry) is None


def _article_57_full_perimeter_scope_gap(value: Any, manifest: dict[str, Any], institution_refs: list[str], registry: Any) -> dict[str, Any] | None:
    required = {"manifest_ref", "case_ref", "coordinated_benefit_ref", "contingency_date", "issuer_institution_ref", "as_of_date", "temporal_coverage_from", "temporal_coverage_to", "procedural_coverage_ref", "institution_refs", "full_perimeter_status", "operator_verification_status", "resolved_source_refs"}
    if not isinstance(value, dict) or set(value) != required or value.get("manifest_ref") != manifest["manifest_ref"] or value.get("case_ref") != manifest["case_ref"] or value.get("coordinated_benefit_ref") != manifest["coordinated_benefit_ref"] or value.get("contingency_date") != manifest["contingency_date"] or value.get("as_of_date") != manifest["as_of_date"]:
        return _article_57_gap("missing_article_57_verified_institution_scope", "A verified full-perimeter scope bound to the coordination manifest is required.")
    if not _canonical_string(value.get("issuer_institution_ref")) or value.get("issuer_institution_ref") != manifest["issuer_institution_ref"] or value.get("institution_refs") != institution_refs or value.get("full_perimeter_status") != "source_bound_full_perimeter" or value.get("operator_verification_status") != "verified" or not _nonempty_string_list(value.get("resolved_source_refs")):
        return _article_57_gap("missing_article_57_verified_institution_scope", "A verified full-perimeter scope must bind its issuer and every concerned institution.")
    if len(set(value["resolved_source_refs"])) != len(value["resolved_source_refs"]):
        return _article_57_gap("inconsistent_article_57_3_registry_binding", "Full-perimeter registry references must be unique.")
    if not _iso_date(value.get("temporal_coverage_from")) or not _iso_date(value.get("temporal_coverage_to")) or value["temporal_coverage_from"] > manifest["contingency_date"] or value["temporal_coverage_to"] < manifest["contingency_date"] or not _canonical_string(value.get("procedural_coverage_ref")):
        return _article_57_gap("missing_article_57_verified_institution_scope", "A verified full-perimeter scope must cover the contingency date and procedural scope.")
    if not isinstance(registry, list) or not registry:
        return _article_57_gap("missing_article_57_3_registry_evidence", "The evidence registry required by the full-perimeter scope is missing or empty.")
    entries: dict[str, dict[str, Any]] = {}
    for entry in registry:
        if not isinstance(entry, dict) or set(entry) != {"evidence_id", "issuer_institution_ref", "content_utf8", "content_digest", "coverage", "verified"}:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Evidence registry entries must use the canonical integrity shape.")
        evidence_id = entry.get("evidence_id")
        if not _canonical_string(evidence_id) or evidence_id in entries:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Evidence registry identifiers must be canonical and unique.")
        if not _canonical_string(entry.get("issuer_institution_ref")) or not isinstance(entry.get("content_utf8"), str) or not isinstance(entry.get("content_digest"), str) or re.fullmatch(r"sha256:[0-9a-f]{64}", entry["content_digest"]) is None:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Evidence registry content requires a canonical issuer and strict lowercase SHA-256 digest.")
        try:
            digest = "sha256:" + hashlib.sha256(entry["content_utf8"].encode("utf-8")).hexdigest()
        except UnicodeEncodeError:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Evidence registry content must be UTF-8 encodable.")
        if entry["content_digest"] != digest:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Evidence registry digest does not match its UTF-8 content.")
        if not isinstance(entry, dict) or entry.get("issuer_institution_ref") != value.get("issuer_institution_ref") or entry.get("verified") is not True:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Evidence registry issuer or verification status does not match the manifest-bound scope.")
        coverage = entry.get("coverage")
        coverage_fields = {"manifest_ref", "case_ref", "coordinated_benefit_ref", "contingency_date", "as_of_date", "temporal_coverage_from", "temporal_coverage_to", "procedural_coverage_ref", "institution_refs"}
        legislation_coverage_fields = {"applicable_legislation_valid_from", "applicable_legislation_valid_to"}
        if not isinstance(coverage, dict) or (set(coverage) != coverage_fields and set(coverage) != coverage_fields | legislation_coverage_fields) or any(coverage.get(key) != value.get(key) for key in ("manifest_ref", "case_ref", "coordinated_benefit_ref", "contingency_date", "as_of_date", "procedural_coverage_ref", "institution_refs")):
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Evidence registry coverage does not match the coordinated manifest, institution set or procedure.")
        if not _iso_date(coverage.get("temporal_coverage_from")) or not _iso_date(coverage.get("temporal_coverage_to")) or coverage["temporal_coverage_from"] > value["temporal_coverage_from"] or coverage["temporal_coverage_to"] < value["temporal_coverage_to"]:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Evidence registry coverage does not contain the declared full-perimeter interval.")
        if set(coverage) == coverage_fields | legislation_coverage_fields:
            valid_from = coverage.get("applicable_legislation_valid_from")
            valid_to = coverage.get("applicable_legislation_valid_to")
            if not _iso_date(valid_from) or (valid_to is not None and (not _iso_date(valid_to) or valid_to < valid_from)):
                return _article_57_gap("inconsistent_article_57_3_registry_binding", "Evidence registry applicable-legislation coverage dates are invalid.")
        entries[evidence_id] = entry
    if not set(value["resolved_source_refs"]).issubset(entries):
        return _article_57_gap("missing_article_57_3_registry_evidence", "A full-perimeter evidence reference does not resolve to a registry entry.")
    return None


def _article_57_per_institution_evidence(value: Any, record: dict[str, Any]) -> bool:
    required = {"pertinent_period_refs", "total_duration", "one_year_comparator", "applicable_legislation", "autonomous_right_determination", "source_evidence_refs"}
    if not isinstance(value, dict) or set(value) != required or not _nonempty_string_list(value.get("pertinent_period_refs")) or not _nonempty_canonical_string_list(value.get("source_evidence_refs")):
        return False
    duration, comparator, legislation, autonomous = (value[name] for name in ("total_duration", "one_year_comparator", "applicable_legislation", "autonomous_right_determination"))
    if (
        not isinstance(duration, dict) or set(duration) != {"value", "unit", "legal_basis_refs"}
        or _rational_value(duration.get("value")) is None or not _canonical_string(duration.get("unit")) or not _nonempty_string_list(duration.get("legal_basis_refs"))
        or not isinstance(comparator, dict) or set(comparator) != {"value", "unit", "legal_basis_refs"}
        or _rational_value(comparator.get("value")) is None or comparator.get("unit") != duration.get("unit") or not _nonempty_string_list(comparator.get("legal_basis_refs"))
        or not isinstance(legislation, dict) or set(legislation) != {"id", "version", "valid_from", "valid_to", "source_refs"}
        or legislation.get("id") != record["applicable_legislation_id"] or legislation.get("version") != record["applicable_legislation_version"] or legislation.get("valid_from") != record["applicable_legislation_valid_from"] or legislation.get("valid_to") != record["applicable_legislation_valid_to"] or not _nonempty_string_list(legislation.get("source_refs"))
        or not isinstance(autonomous, dict) or set(autonomous) != {"result", "national_rule_pack_id", "national_rule_version", "risk_materialization_date", "evidence_refs"}
        or type(autonomous.get("result")) is not bool or not _canonical_string(autonomous.get("national_rule_pack_id")) or not _canonical_string(autonomous.get("national_rule_version")) or autonomous.get("risk_materialization_date") != record["risk_materialization_date"] or not _nonempty_string_list(autonomous.get("evidence_refs"))
    ):
        return False
    relief = _rational_less_than(_rational_value(duration["value"]), _rational_value(comparator["value"])) and not autonomous["result"]
    return record["article_57_1_relief_result"] is relief


def _article_57_institutional_registry_binding_gap(
    institutions: list[dict[str, Any]],
    manifest: dict[str, Any],
    institution_refs: list[str],
    registry: Any,
) -> dict[str, Any] | None:
    """Bind technical Art. 57(1) record references without deciding legal entitlement."""
    if not isinstance(registry, list) or not registry:
        return _article_57_gap("missing_article_57_3_registry_evidence", "Institutional Article 57(1) evidence references require a verified registry.")
    entries: dict[str, dict[str, Any]] = {}
    for entry in registry:
        if not isinstance(entry, dict) or set(entry) != {"evidence_id", "issuer_institution_ref", "content_utf8", "content_digest", "coverage", "verified"}:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Institutional Article 57(1) registry entries must use the canonical integrity shape.")
        evidence_id = entry.get("evidence_id")
        if not _canonical_string(evidence_id) or evidence_id in entries:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Institutional Article 57(1) registry identifiers must be canonical and unique.")
        entries[evidence_id] = entry
    for record in institutions:
        evidence = record["article_57_1_evidence"]
        for references in (evidence["source_evidence_refs"], record["evidence_refs"]):
            if not _nonempty_canonical_string_list(references) or len(set(references)) != len(references):
                return _article_57_gap("inconsistent_article_57_3_registry_binding", "Institutional Article 57(1) evidence-reference identifiers must be unique within each list.")
            if any(reference not in entries for reference in references):
                return _article_57_gap("missing_article_57_3_registry_evidence", "Each institutional Article 57(1) evidence reference must resolve to one verified registry entry.")
            for reference in references:
                entry = entries[reference]
                content = entry.get("content_utf8")
                try:
                    expected_digest = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest() if isinstance(content, str) else None
                except UnicodeEncodeError:
                    return _article_57_gap("inconsistent_article_57_3_registry_binding", "Institutional Article 57(1) registry content must be UTF-8 encodable.")
                if (
                    entry.get("issuer_institution_ref") != manifest["issuer_institution_ref"]
                    or entry.get("verified") is not True
                    or not isinstance(entry.get("content_utf8"), str)
                    or not isinstance(entry.get("content_digest"), str)
                    or re.fullmatch(r"sha256:[0-9a-f]{64}", entry["content_digest"]) is None
                    or entry["content_digest"] != expected_digest
                ):
                    return _article_57_gap("inconsistent_article_57_3_registry_binding", "Institutional Article 57(1) registry content, digest, verification and issuer must match the coordination manifest.")
                coverage = entry.get("coverage")
                required_coverage = {"manifest_ref", "case_ref", "coordinated_benefit_ref", "contingency_date", "as_of_date", "temporal_coverage_from", "temporal_coverage_to", "procedural_coverage_ref", "institution_refs", "applicable_legislation_valid_from", "applicable_legislation_valid_to"}
                if not isinstance(coverage, dict) or set(coverage) != required_coverage:
                    return _article_57_gap("inconsistent_article_57_3_registry_binding", "Institutional Article 57(1) registry coverage must bind the manifest, institutions, dates and applicable legislation.")
                if (
                    any(coverage[key] != manifest[key] for key in ("manifest_ref", "case_ref", "coordinated_benefit_ref", "contingency_date", "as_of_date"))
                    or coverage.get("institution_refs") != institution_refs
                    or coverage.get("applicable_legislation_valid_from") != record["applicable_legislation_valid_from"]
                    or coverage.get("applicable_legislation_valid_to") != record["applicable_legislation_valid_to"]
                    or not _iso_date(coverage.get("temporal_coverage_from"))
                    or not _iso_date(coverage.get("temporal_coverage_to"))
                    or coverage["temporal_coverage_from"] > min(record["contingency_date"], record["risk_materialization_date"], record["assessment_date"])
                    or coverage["temporal_coverage_to"] < max(record["contingency_date"], record["risk_materialization_date"], record["assessment_date"])
                ):
                    return _article_57_gap("inconsistent_article_57_3_registry_binding", "Institutional Article 57(1) registry coverage does not match the coordinated case, benefit, institution set, legislation or dates.")
    return None


def _article_57_root_reconciles(root: dict[str, Any], record: dict[str, Any], autonomous: bool | None) -> bool:
    evidence = record["article_57_1_evidence"]
    if any(record[field] != root[field] for field in ("member_state", "benefit_type", "scheme_id", "competent_institution", "applicable_legislation_id", "applicable_legislation_version", "applicable_legislation_valid_from", "applicable_legislation_valid_to", "risk_materialization_date", "assessment_date")):
        return False
    if record["local_claim_ref"] != root["root_local_claim_ref"] or record["local_benefit_ref"] != root["root_local_benefit_ref"]:
        return False
    for root_key, evidence_key in (("legal_duration_for_article_57", "total_duration"), ("one_year_comparator", "one_year_comparator")):
        left, right = root[root_key], evidence[evidence_key]
        if left.get("unit") != right["unit"] or _rational_value(left.get("value")) != _rational_value(right["value"]):
            return False
    determination = evidence["autonomous_right_determination"]
    source = root.get("autonomous_right_from_state_periods_only")
    if autonomous is None or not isinstance(source, dict) or autonomous != determination["result"] or any(source.get(a) != determination[b] for a, b in (("national_benefit_rule_pack_id", "national_rule_pack_id"), ("national_rule_version", "national_rule_version"), ("risk_materialization_date", "risk_materialization_date"))):
        return False
    duration = root.get("duration_strictly_less_than_one_year")
    return type(duration) is bool and record["article_57_1_relief_result"] is (duration and not autonomous)


def _article_57_last_state_registry_binding_gap(
    value: Any,
    manifest: dict[str, Any],
    institutions: list[dict[str, Any]],
    institution_refs: list[str],
    assessment_date: str,
    registry: Any,
) -> dict[str, Any] | None:
    # This type check is deliberately before every mapping access: public input may be a truthy scalar or list.
    if not isinstance(value, dict):
        return _article_57_gap("invalid_article_57_3_last_state_attestation", "Article 57(3) last-State attestation must be a canonical object; no legal last State or payer is inferred.")
    required = {"manifest_ref", "case_ref", "coordinated_benefit_ref", "contingency_date", "institution_ref", "member_state", "applicable_legislation", "conditions_satisfied", "conditions_satisfied_on", "conditions_event_ref", "candidate_institution_refs", "candidate_conditions_comparability_status", "last_state_selection_status", "selection_evidence_refs", "conditions_evidence_refs", "comparability_evidence_refs", "institutional_record_evidence_refs"}
    if set(value) != required:
        return _article_57_gap("invalid_article_57_3_last_state_attestation", "Article 57(3) last-State attestation must use the canonical object shape.")
    reference_fields = ("selection_evidence_refs", "conditions_evidence_refs", "comparability_evidence_refs", "institutional_record_evidence_refs")
    legislation = value.get("applicable_legislation")
    if (
        any(not isinstance(value.get(field), list) or not value[field] or any(not _canonical_string(item) for item in value[field]) for field in reference_fields)
        or not _canonical_string(value.get("conditions_event_ref"))
        or not isinstance(legislation, dict)
        or not isinstance(legislation.get("source_refs"), list)
        or not legislation["source_refs"]
        or any(not _canonical_string(item) for item in legislation["source_refs"])
    ):
        return _article_57_gap("missing_article_57_3_registry_evidence", "Each Article 57(3) selection, conditions, comparability, event, legislation and institutional-record category requires non-empty evidence references.")
    if any(len(set(value[field])) != len(value[field]) for field in reference_fields) or len(set(legislation["source_refs"])) != len(legislation["source_refs"]):
        return _article_57_gap("inconsistent_article_57_3_registry_binding", "Article 57(3) evidence-reference identifiers must be unique within each category.")
    record = next((item for item in institutions if item["institution_ref"] == value.get("institution_ref")), None)
    if record is None or not _article_57_last_state_evidence(value, manifest, record, institution_refs, assessment_date):
        return _article_57_gap("invalid_article_57_3_last_state_attestation", "Article 57(3) last-State attestation must bind the manifest, selected record, conditions, event and comparability without determining a payer.")
    references = [
        *value["selection_evidence_refs"],
        *value["conditions_evidence_refs"],
        *value["comparability_evidence_refs"],
        value["conditions_event_ref"],
        *value["applicable_legislation"]["source_refs"],
        *value["institutional_record_evidence_refs"],
    ]
    if not isinstance(registry, list) or not registry:
        return _article_57_gap("missing_article_57_3_registry_evidence", "Each Article 57(3) selection, conditions, comparability, event, legislation and institutional-record reference requires a registry entry.")
    if len(set(references)) != len(references):
        return _article_57_gap("inconsistent_article_57_3_registry_binding", "Article 57(3) evidence-reference identifiers must be distinct across categories.")
    entries: dict[str, dict[str, Any]] = {}
    for entry in registry:
        if not isinstance(entry, dict) or set(entry) != {"evidence_id", "issuer_institution_ref", "content_utf8", "content_digest", "coverage", "verified"}:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Article 57(3) evidence registry entries must use the canonical integrity shape.")
        evidence_id = entry.get("evidence_id")
        if not _canonical_string(evidence_id) or evidence_id in entries:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Article 57(3) evidence registry identifiers must be unique.")
        if not isinstance(entry.get("content_utf8"), str) or not isinstance(entry.get("content_digest"), str) or re.fullmatch(r"sha256:[0-9a-f]{64}", entry["content_digest"]) is None:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Article 57(3) evidence registry content requires a strict SHA-256 UTF-8 digest.")
        try:
            digest = "sha256:" + hashlib.sha256(entry["content_utf8"].encode("utf-8")).hexdigest()
        except UnicodeEncodeError:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Article 57(3) evidence registry content must be UTF-8 encodable.")
        if entry["content_digest"] != digest or entry.get("verified") is not True or entry.get("issuer_institution_ref") != manifest["issuer_institution_ref"]:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Article 57(3) registry content, verification and issuer must match the coordination manifest.")
        entries[evidence_id] = entry
    if any(reference not in entries for reference in references):
        return _article_57_gap("missing_article_57_3_registry_evidence", "Each Article 57(3) evidence reference must resolve to one verified registry entry.")
    legislation = value["applicable_legislation"]
    for reference in references:
        coverage = entries[reference].get("coverage")
        required = {"manifest_ref", "case_ref", "coordinated_benefit_ref", "contingency_date", "as_of_date", "temporal_coverage_from", "temporal_coverage_to", "procedural_coverage_ref", "institution_refs", "applicable_legislation_valid_from", "applicable_legislation_valid_to"}
        if not isinstance(coverage, dict) or set(coverage) != required:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Article 57(3) registry coverage must bind manifest, institutions, dates and applicable legislation.")
        if any(coverage[key] != manifest[key] for key in ("manifest_ref", "case_ref", "coordinated_benefit_ref", "contingency_date", "as_of_date")) or coverage.get("institution_refs") != institution_refs or coverage.get("applicable_legislation_valid_from") != legislation["valid_from"] or coverage.get("applicable_legislation_valid_to") != legislation["valid_to"]:
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Article 57(3) registry coverage does not match the coordinated case, benefit, institution set or applicable legislation.")
        if not _iso_date(coverage.get("temporal_coverage_from")) or not _iso_date(coverage.get("temporal_coverage_to")) or coverage["temporal_coverage_from"] > min(manifest["contingency_date"], assessment_date, value["conditions_satisfied_on"]) or coverage["temporal_coverage_to"] < max(manifest["contingency_date"], assessment_date, value["conditions_satisfied_on"]):
            return _article_57_gap("inconsistent_article_57_3_registry_binding", "Article 57(3) registry coverage must include the contingency, event and assessment dates.")
    return None


def _article_57_last_state_evidence(value: dict[str, Any], manifest: dict[str, Any], record: dict[str, Any], institution_refs: list[str], assessment_date: str) -> bool:
    required = {"manifest_ref", "case_ref", "coordinated_benefit_ref", "contingency_date", "institution_ref", "member_state", "applicable_legislation", "conditions_satisfied", "conditions_satisfied_on", "conditions_event_ref", "candidate_institution_refs", "candidate_conditions_comparability_status", "last_state_selection_status", "selection_evidence_refs", "conditions_evidence_refs", "comparability_evidence_refs", "institutional_record_evidence_refs"}
    if not isinstance(value, dict) or set(value) != required:
        return False
    legislation = value.get("applicable_legislation")
    return (
        all(value.get(field) == manifest[field] for field in ("manifest_ref", "case_ref", "coordinated_benefit_ref", "contingency_date"))
        and value.get("institution_ref") == record["institution_ref"] and value.get("member_state") == record["member_state"]
        and isinstance(legislation, dict) and set(legislation) == {"id", "version", "valid_from", "valid_to", "source_refs"}
        and all(legislation.get(key) == record[f"applicable_legislation_{key}"] for key in ("id", "version", "valid_from", "valid_to")) and _nonempty_string_list(legislation.get("source_refs"))
        and value.get("conditions_satisfied") is True and _iso_date(value.get("conditions_satisfied_on")) and value["conditions_satisfied_on"] <= assessment_date and _date_in_range(value["conditions_satisfied_on"], legislation["valid_from"], legislation["valid_to"]) and _canonical_string(value.get("conditions_event_ref"))
        and value.get("candidate_institution_refs") == institution_refs
        and value.get("candidate_conditions_comparability_status") == "verified_comparable"
        and value.get("last_state_selection_status") == "operator_verified_unique_last_state"
        and all(_nonempty_string_list(value.get(field)) for field in ("selection_evidence_refs", "conditions_evidence_refs", "comparability_evidence_refs", "institutional_record_evidence_refs"))
        and set(value["institutional_record_evidence_refs"]).issubset(set(record["evidence_refs"]))
    )


def _article_57_institutional_records(value: Any, manifest: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    if not isinstance(value, list) or not value:
        return None
    records: list[dict[str, Any]] = []
    for record in value:
        if not isinstance(record, dict) or set(record) != {"institution_ref", "member_state", "coordination_manifest_ref", "coordination_case_ref", "coordinated_benefit_ref", "contingency_date", "local_claim_ref", "local_benefit_ref", "benefit_type", "scheme_id", "competent_institution", "applicable_legislation_id", "applicable_legislation_version", "applicable_legislation_valid_from", "applicable_legislation_valid_to", "risk_materialization_date", "assessment_date", "transitional_applicability", "article_57_1_relief_result", "article_57_1_evidence", "evidence_refs"}:
            return None
        if (
            manifest is None
            or not _canonical_string(record["institution_ref"])
            or not _canonical_string(record["member_state"])
            or any(record[field] != manifest[manifest_field] for field, manifest_field in (("coordination_manifest_ref", "manifest_ref"), ("coordination_case_ref", "case_ref"), ("coordinated_benefit_ref", "coordinated_benefit_ref"), ("contingency_date", "contingency_date")))
            or not _article_57_local_reference(record["local_claim_ref"], record["institution_ref"])
            or not _article_57_local_reference(record["local_benefit_ref"], record["institution_ref"])
            or any(not _canonical_string(record[field]) for field in ("benefit_type", "scheme_id", "competent_institution", "applicable_legislation_id", "applicable_legislation_version"))
            or not _iso_date(record["risk_materialization_date"])
            or not _iso_date(record["assessment_date"])
            or not _iso_date(record["applicable_legislation_valid_from"])
            or (record["applicable_legislation_valid_to"] is not None and not _iso_date(record["applicable_legislation_valid_to"]))
            or not _date_in_range(record["risk_materialization_date"], record["applicable_legislation_valid_from"], record["applicable_legislation_valid_to"])
            or _transitional_result(record["transitional_applicability"], record["member_state"], record["risk_materialization_date"]) is None
            or record["risk_materialization_date"] != manifest["contingency_date"]
            or record["assessment_date"] != manifest["as_of_date"]
            or type(record["article_57_1_relief_result"]) is not bool
            or not _article_57_per_institution_evidence(record["article_57_1_evidence"], record)
            or not _nonempty_canonical_string_list(record["evidence_refs"])
        ):
            return None
        records.append(record)
    if len({record["institution_ref"] for record in records}) != len(records):
        return None
    return records


def _nonempty_string_list(value: Any) -> bool:
    return _canonical_string_list(value)


def _nonempty_canonical_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_canonical_string(item) for item in value)


def _canonical_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == unicodedata.normalize("NFC", value)


def _canonical_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_canonical_string(item) for item in value) and len(set(value)) == len(value)


def _iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _date_in_range(value: str, valid_from: str, valid_to: str | None) -> bool:
    return value >= valid_from and (valid_to is None or value <= valid_to)


def _source_bound_result(value: Any, label: str, policy: dict[str, Any] | None = None, root: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"result": None}
    result = value.get("result")
    if type(result) not in {bool, type(None)}:
        raise ItEsEuPensionProRataError(f"{label}.result must be true, false, or null.")
    if result is None:
        return {"result": None}
    required = ("evidence_refs",) if label == "autonomous_right_from_state_periods_only" else ()
    if label == "autonomous_right_from_state_periods_only":
        required += ("national_benefit_rule_pack_id", "national_rule_version", "risk_materialization_date")
    else:
        required += ("catalogue_id", "catalogue_schema_version", "catalogue_digest", "catalogue_valid_from", "annex_consolidation_version", "annex_validity_or_applicability_date", "scheme_match_status", "annex_evidence_refs")
    if any(field not in value or value.get(field) is None for field in required) or (label == "annex_viii_part_2_applicability" and "catalogue_valid_to" not in value):
        return {"result": None}
    if label == "autonomous_right_from_state_periods_only" and (not _iso_date(value["risk_materialization_date"]) or root is None or value["risk_materialization_date"] != root["risk_materialization_date"]):
        return {"result": None}
    if label == "annex_viii_part_2_applicability":
        annex_policy = policy["annex_viii_part_2"] if policy else {}
        catalogue_entries = annex_policy.get("catalogue_entry_ids")
        if (
            annex_policy.get("machine_readable_validity_catalogue_status") != "available"
            or not _canonical_string_list(catalogue_entries)
            or not _iso_date(value.get("catalogue_valid_from"))
            or (value.get("catalogue_valid_to") is not None and not _iso_date(value.get("catalogue_valid_to")))
        ):
            return {"result": None}
        annex_date = value["annex_validity_or_applicability_date"]
        if (
            not _iso_date(annex_date)
            or value.get("annex_consolidation_version") != annex_policy.get("applicable_annex_part_2_version")
            or annex_date != (root or {}).get("risk_materialization_date")
            or not _date_in_range(annex_date, annex_policy.get("applicable_annex_part_2_valid_from", "9999-12-31"), annex_policy.get("applicable_annex_part_2_valid_to"))
            or any(value.get(field) != annex_policy.get(field) for field in ("catalogue_id", "catalogue_schema_version", "catalogue_digest", "catalogue_valid_from", "catalogue_valid_to"))
            or value.get("scheme_match_status") not in {"matched", "not_matched", "not_assessed"}
            or not _nonempty_string_list(value.get("annex_evidence_refs"))
        ):
            return {"result": None}
        if value["scheme_match_status"] == "matched" and (
            not _canonical_string(value.get("matched_scheme_entry"))
            or value["matched_scheme_entry"] not in catalogue_entries
        ):
            return {"result": None}
        if value["scheme_match_status"] in {"not_matched", "not_assessed"} and value.get("matched_scheme_entry") is not None:
            return {"result": None}
        if (result is True and value["scheme_match_status"] != "matched") or (result is False and value["scheme_match_status"] != "not_matched") or (result is None and value["scheme_match_status"] != "not_assessed"):
            return {"result": None}
    return {"result": result}


def _transitional_result(value: Any, member_state: str, risk_date: str) -> bool | None:
    if not isinstance(value, dict) or set(value) != {"basic_regulation_883_87", "implementing_regulation_987_93", "regulation_465_2012_883_87a", "pension_transitional_987_94_1"}:
        return None
    basic = value["basic_regulation_883_87"]
    if not isinstance(basic, dict) or set(basic) != {"member_state", "territorial_application_date", "contingency_date", "pre_application_period_refs", "result", "evidence_refs", "data_gaps"}:
        return None
    territorial = basic["territorial_application_date"]
    if (
        basic["member_state"] != member_state
        or basic["contingency_date"] != risk_date
        or basic["result"] not in {"applicable", "not_applicable", "not_assessed"}
        or not isinstance(territorial, dict)
        or set(territorial) != {"date", "legal_source_ref"}
        or not _iso_date(territorial["date"])
        or not _canonical_string(territorial["legal_source_ref"])
        or not isinstance(basic["pre_application_period_refs"], list)
        or any(not _canonical_string(ref) for ref in basic["pre_application_period_refs"])
        or len(set(basic["pre_application_period_refs"])) != len(basic["pre_application_period_refs"])
        or not _nonempty_string_list(basic["evidence_refs"])
        or not isinstance(basic["data_gaps"], list)
        or (basic["result"] == "not_assessed" and not basic["data_gaps"])
    ):
        return None

    implementing = value["implementing_regulation_987_93"]
    if (
        not isinstance(implementing, dict)
        or set(implementing) != {"result", "evidence_refs", "data_gaps"}
        or implementing["result"] not in {"applicable", "not_applicable", "not_assessed"}
        or not _nonempty_string_list(implementing["evidence_refs"])
        or not isinstance(implementing["data_gaps"], list)
        or (implementing["result"] == "not_assessed" and not implementing["data_gaps"])
    ):
        return None

    title_ii = value["regulation_465_2012_883_87a"]
    title_ii_fields = {
        "title_ii_change_caused_by_465_2012", "legislation_before_change", "legislation_after_change",
        "relevant_situation_unchanged", "within_ten_year_limit", "opt_out_request_date",
        "opt_out_effective_date", "result", "evidence_refs", "data_gaps",
    }
    if (
        not isinstance(title_ii, dict)
        or set(title_ii) != title_ii_fields
        or title_ii["result"] not in {"old_legislation_continues", "new_legislation_applies", "not_applicable", "not_assessed"}
        or type(title_ii["title_ii_change_caused_by_465_2012"]) not in {bool, type(None)}
        or type(title_ii["relevant_situation_unchanged"]) not in {bool, type(None)}
        or type(title_ii["within_ten_year_limit"]) not in {bool, type(None)}
        or any(title_ii[field] is not None and not _canonical_string(title_ii[field]) for field in ("legislation_before_change", "legislation_after_change"))
        or any(title_ii[field] is not None and not _iso_date(title_ii[field]) for field in ("opt_out_request_date", "opt_out_effective_date"))
        or not _nonempty_string_list(title_ii["evidence_refs"])
        or not isinstance(title_ii["data_gaps"], list)
        or (title_ii["result"] in {"old_legislation_continues", "new_legislation_applies"} and (
            title_ii["title_ii_change_caused_by_465_2012"] is not True
            or title_ii["relevant_situation_unchanged"] is None
            or title_ii["within_ten_year_limit"] is None
            or not _canonical_string(title_ii["legislation_before_change"])
            or not _canonical_string(title_ii["legislation_after_change"])
        ))
        or (title_ii["result"] == "not_assessed" and not title_ii["data_gaps"])
    ):
        return None

    pension = value["pension_transitional_987_94_1"]
    pension_fields = {
        "benefits_due_for_pre_application_period", "contingency_pre_application", "claim_awarded_before_application_date",
        "prior_leg", "basic_regulation_leg", "comparison", "preserved_result", "result", "data_gaps",
    }
    if (
        not isinstance(pension, dict)
        or set(pension) != pension_fields
        or pension["result"] not in {"both_legs_assessed", "not_applicable", "not_assessed"}
        or any(type(pension[field]) not in {bool, type(None)} for field in ("benefits_due_for_pre_application_period", "contingency_pre_application", "claim_awarded_before_application_date"))
        or pension["comparison"] not in {"prior_higher", "basic_higher", "equal", "not_assessed", "not_applicable"}
        or pension["preserved_result"] not in {"prior_leg", "basic_regulation_leg", "not_assessed", "not_applicable"}
        or not isinstance(pension["data_gaps"], list)
    ):
        return None
    if pension["result"] == "both_legs_assessed":
        leg_fields = {"legal_basis", "period", "amount_result_ref", "evidence_refs"}
        for field in ("prior_leg", "basic_regulation_leg"):
            leg = pension[field]
            if (
                not isinstance(leg, dict)
                or set(leg) != leg_fields
                or not _canonical_string(leg["legal_basis"])
                or not _canonical_string(leg["amount_result_ref"])
                or not _nonempty_string_list(leg["evidence_refs"])
            ):
                return None
        if (
            any(type(pension[field]) is not bool for field in ("benefits_due_for_pre_application_period", "contingency_pre_application", "claim_awarded_before_application_date"))
            or pension["comparison"] not in {"prior_higher", "basic_higher", "equal"}
            or pension["preserved_result"] != ("prior_leg" if pension["comparison"] == "prior_higher" else "basic_regulation_leg")
        ):
            return None
    elif pension["result"] == "not_assessed" and not pension["data_gaps"]:
        return None

    if any(value[name]["result"] == "not_assessed" for name in value):
        return None
    return True


def _article_57_not_assessed(base: dict[str, Any], code: str, message: str) -> dict[str, Any]:
    return {"result": base, "data_gaps": [_article_57_gap(code, message)]}


def _article_57_gap(code: str, message: str) -> dict[str, Any]:
    return {"code": code, "message": message, "article_57_contract": "v0.25/fo-art57-c14n-v4", "human_review_required": True}


def _spanish_pro_rata(
    theoretical: dict[str, Any],
    periods_result: dict[str, Any],
    entitlement: dict[str, Any],
    rule_pack: dict[str, Any],
    article_57: dict[str, Any],
) -> dict[str, Any]:
    gaps: list[dict[str, Any]] = []
    theoretical_result = theoretical["result"]
    total = periods_result["summary"]["total_eu_non_overlapping_months"]
    es = periods_result["summary"]["spain_months"]
    article_57_result = article_57["result"]
    if entitlement["result"]["status"] == "not_eligible":
        gaps.append({"code": "spanish_entitlement_required_for_pro_rata", "message": "Pro-rata is not calculated when Spanish entitlement is not reached."})
    if theoretical_result is None:
        gaps.append({"code": "missing_theoretical_amount_for_pro_rata", "message": "Cannot calculate pro-rata without a Spanish theoretical amount."})
    if any(
        gap.get("code") in {
            "missing_spanish_insured_or_equivalent_status",
            "spanish_insured_or_equivalent_status_not_confirmed",
            "unclassified_it_es_period_overlap",
        }
        for gap in entitlement["data_gaps"]
    ):
        gaps.append(
            {
                "code": "spanish_insured_or_equivalent_status_required_for_pro_rata",
                "message": "Pro-rata is not calculated until the required Spanish insured-or-equivalent status is confirmed.",
            }
        )
    if not total:
        gaps.append({"code": "missing_periods_for_pro_rata", "message": "Cannot calculate pro-rata without non-overlapping EU periods."})
    if periods_result["overlaps"]:
        gaps.append(
            {
                "code": "unclassified_it_es_period_overlap",
                "message": "Pro-rata is not calculable until Article 12 overlap classification is supplied by the competent institutions.",
                "overlap_month_count": len(periods_result["overlaps"]),
            }
        )
    gaps.extend(article_57["data_gaps"])
    if article_57_result["article_57_exception_status"] == "applies":
        gaps.append(_article_57_gap("article_57_pro_rata_downstream_not_assessed", "Article 57 applies; theoretical inclusion and payment obligation are preserved separately, while pro-rata remains downstream not assessed."))
    if gaps:
        return {"result": {"status": "not_calculable", "method": rule_pack["pro_rata_method"], "article_57": article_57_result, "amounts": None}, "data_gaps": gaps}

    ratio_decimals = int(rule_pack["pro_rata_method"]["rounding"]["ratio_decimals"])
    ratio = (Decimal(es) / Decimal(total)).quantize(Decimal("1").scaleb(-ratio_decimals))
    monthly = _round_money(_decimal(theoretical_result["monthly_gross_amount"], "monthly_gross_amount") * ratio)
    annual = _round_money(_decimal(theoretical_result["annual_gross_amount"], "annual_gross_amount") * ratio)
    return {
        "result": {
            "status": "calculated",
            "method": rule_pack["pro_rata_method"],
            "article_57": article_57_result,
            "ratio": {
                "spain_months": es,
                "total_eu_non_overlapping_months": total,
                "value": format(ratio, "f"),
            },
            "amounts": {
                "monthly_gross_amount": _money(monthly),
                "annual_gross_amount": _money(annual),
                "currency": theoretical_result["currency"],
                "payments_per_year": theoretical_result["payments_per_year"],
            },
        },
        "data_gaps": [],
    }


def _status(entitlement: dict[str, Any], pro_rata: dict[str, Any], data_gaps: list[dict[str, Any]]) -> str:
    if entitlement["result"]["status"] == "not_eligible":
        return "blocked_not_eligible"
    if pro_rata["result"]["status"] != "calculated":
        return "blocked_missing_inputs"
    blocking_codes = {
        "incomplete_inps_dated_history",
        "missing_future_contribution_assumptions",
        "missing_dated_insurance_periods",
        "insurance_period_after_retirement_date",
        "spanish_theoretical_source_country_not_es",
        "spanish_theoretical_basis_not_spanish_only",
        "inconsistent_theoretical_monthly_annual_amounts",
        "missing_payments_per_year",
    }
    if any(gap.get("code") in blocking_codes for gap in data_gaps):
        return "blocked_missing_inputs"
    if data_gaps:
        return "partial"
    return "complete"


def _warnings(periods_result: dict[str, Any]) -> list[dict[str, Any]]:
    warnings = [
        {
            "code": "not_official_p1_decision",
            "message": "Internal estimate only; the competent institutions decide official entitlement and amounts.",
        }
    ]
    if periods_result["overlaps"]:
        warnings.append(
            {
                "code": "overlapping_periods_require_institutional_classification",
                "message": "Overlapping Italy-Spain months are not automatically de-duplicated for pro-rata calculation.",
                "overlap_month_count": len(periods_result["overlaps"]),
            }
        )
    return warnings


def _retirement_date(data: dict[str, Any]) -> str:
    value = data.get("retirement_date")
    if not isinstance(value, str) or len(value) != 7 or value[4] != "-":
        raise ItEsEuPensionProRataError("retirement_date must be YYYY-MM.")
    year, month = value.split("-")
    if not year.isdigit() or not month.isdigit() or int(month) < 1 or int(month) > 12:
        raise ItEsEuPensionProRataError("retirement_date must be YYYY-MM.")
    return value


def _input_readiness_gaps(data: dict[str, Any]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    if data.get("inps_history_status") != "complete_dated_history":
        gaps.append(
            {
                "code": "incomplete_inps_dated_history",
                "message": "A complete dated INPS contribution history is required before closing a personal estimate.",
            }
        )
    if data.get("future_assumptions_status") != "explicit":
        gaps.append(
            {
                "code": "missing_future_contribution_assumptions",
                "message": "Future contribution assumptions must be explicit; they are not inferred.",
            }
        )
    return gaps


def _post_retirement_period_gaps(periods_result: dict[str, Any], retirement_date: str) -> list[dict[str, Any]]:
    months = periods_result.get("months", {})
    all_months = months.get("EU", set()) if isinstance(months, dict) else set()
    invalid = sorted(month for month in all_months if month >= retirement_date)
    if not invalid:
        return []
    return [
        {
            "code": "insurance_period_after_retirement_date",
            "message": "Insurance periods at or after the declared retirement month are not used for this estimate.",
            "months": invalid,
        }
    ]


def _months_between(start_date: Any, end_date: Any, index: int) -> set[str]:
    if not _is_full_month_start(start_date):
        raise ItEsEuPensionProRataError(f"Insurance period start must be first day of month at index {index}.")
    if not _is_full_month_end(end_date):
        raise ItEsEuPensionProRataError(f"Insurance period end must be last day of month at index {index}.")
    start = _month_index(start_date, f"insurance_periods[{index}].start_date")
    end = _month_index(end_date, f"insurance_periods[{index}].end_date")
    if end < start:
        raise ItEsEuPensionProRataError(f"Insurance period end precedes start at index {index}.")
    return {_month_from_index(value) for value in range(start, end + 1)}


def _lookback_window(retirement_date: str, months: int) -> list[str]:
    retirement_index = _month_index(f"{retirement_date}-01", "retirement_date")
    start = retirement_index - months
    end = retirement_index - 1
    return [_month_from_index(value) for value in range(start, end + 1)]


def _ordinary_age_check(date_of_birth: Any, retirement_date: str, totalized_months: int, params: dict[str, Any]) -> dict[str, Any]:
    long_career = params["ordinary_age_if_long_career"]
    required_age = long_career if totalized_months >= int(long_career["minimum_contribution_months"]) else params["standard_ordinary_age"]
    result = {"required_age": required_age, "eligible": False}
    if not isinstance(date_of_birth, str):
        return {"eligible": False, "result": result, "gap": {"code": "missing_date_of_birth", "message": "Date of birth is required."}}
    age_months = _month_index(f"{retirement_date}-01", "retirement_date") - _month_index(date_of_birth, "date_of_birth")
    required_months = int(required_age["years"]) * 12 + int(required_age.get("months", 0))
    result.update({"age_months": age_months, "required_age_months": required_months, "eligible": age_months >= required_months})
    return {
        "eligible": result["eligible"],
        "result": result,
        "gap": {
            "code": "spanish_ordinary_age_not_reached",
            "message": "Declared retirement date does not satisfy encoded Spanish ordinary retirement age.",
            "age_months": age_months,
            "required_age_months": required_months,
        },
    }


def _date_in_rule_period(retirement_date: str, params: dict[str, Any]) -> bool:
    candidate = f"{retirement_date}-01"
    valid_from = params["valid_from"]
    valid_to = params.get("valid_to")
    return candidate >= valid_from and (valid_to is None or candidate <= valid_to)


def _blocking_rule_gap(gaps: list[dict[str, Any]]) -> bool:
    return any(
        gap["code"]
        in {
            "retirement_date_not_covered_by_rule_pack",
            "missing_date_of_birth",
            "missing_recent_contribution_anchor_date",
            "spanish_ordinary_age_not_reached",
            "missing_spanish_insured_or_equivalent_status",
            "spanish_insured_or_equivalent_status_not_confirmed",
            "unclassified_it_es_period_overlap",
        }
        for gap in gaps
    )


def _month_index(date_value: Any, field: str) -> int:
    if not isinstance(date_value, str) or len(date_value) < 7:
        raise ItEsEuPensionProRataError(f"{field} must be YYYY-MM or YYYY-MM-DD.")
    year = date_value[:4]
    month = date_value[5:7]
    if not year.isdigit() or not month.isdigit() or date_value[4] != "-":
        raise ItEsEuPensionProRataError(f"{field} must be YYYY-MM or YYYY-MM-DD.")
    month_number = int(month)
    if month_number < 1 or month_number > 12:
        raise ItEsEuPensionProRataError(f"{field} has invalid month: {date_value}")
    return int(year) * 12 + month_number - 1


def _is_full_month_start(date_value: Any) -> bool:
    if isinstance(date_value, str) and len(date_value) == 7:
        return True
    return isinstance(date_value, str) and len(date_value) >= 10 and date_value[8:10] == "01"


def _is_full_month_end(date_value: Any) -> bool:
    if isinstance(date_value, str) and len(date_value) == 7:
        return True
    if not isinstance(date_value, str) or len(date_value) < 10:
        return False
    year = int(date_value[:4])
    month = int(date_value[5:7])
    return int(date_value[8:10]) == calendar.monthrange(year, month)[1]


def _month_from_index(index: int) -> str:
    year = index // 12
    month = index % 12 + 1
    return f"{year:04d}-{month:02d}"


def _empty_period_summary() -> dict[str, Any]:
    return {
        "status": "missing",
        "italy_months": 0,
        "spain_months": 0,
        "total_eu_non_overlapping_months": 0,
        "overlap_month_count": 0,
        "ratio_inputs": {},
        "provenance": {},
    }


def _validate_source_refs(source_refs: Any) -> None:
    if not isinstance(source_refs, list) or not source_refs:
        raise ItEsEuPensionProRataError("EU pension coordination rule pack must contain source_refs")
    allowed_prefixes = ("https://eur-lex.europa.eu/", "https://europa.eu/", "https://prestaciones.seg-social.es/", "https://www.seg-social.es/", "https://www.boe.es/")
    for source_ref in source_refs:
        for field in ("source_id", "title", "url", "retrieved_on", "provisions"):
            if field not in source_ref:
                raise ItEsEuPensionProRataError(f"EU pension coordination source_ref missing field: {field}")
        if not str(source_ref["url"]).startswith(allowed_prefixes):
            raise ItEsEuPensionProRataError("EU pension coordination source_ref must use an official EU or Spanish URL")


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ItEsEuPensionProRataError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ItEsEuPensionProRataError(f"Invalid {label} JSON: {path}") from exc


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_snapshot(snapshot: dict[str, Any], output_path: Path) -> dict[str, Any]:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ItEsEuPensionProRataError(f"Cannot write IT-ES EU pension pro-rata snapshot: {output_path}") from exc
    return snapshot


def _decimal(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ItEsEuPensionProRataError(f"Invalid decimal value for {field}: {value}") from exc


def _money(value: Decimal) -> str:
    return f"{_round_money(value)}"


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
