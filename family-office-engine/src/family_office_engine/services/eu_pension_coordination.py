import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from family_office_engine.governance.pension_source_freshness import (
    PensionSourceFreshnessError,
    require_fresh_pension_rule_pack,
)

SCHEMA_VERSION = "eu-pension-coordination-it-es/v1"
RECORD_TYPE = "EuPensionCoordinationItEsSnapshot"
RULE_PACK_SCHEMA_VERSION = "eu-pension-coordination-rule-pack/v2"


class EuPensionCoordinationError(ValueError):
    pass


def coordinate_it_es_pensions(
    inps_snapshot_path: Path,
    spanish_pension_snapshot_path: Path,
    rule_pack_path: Path,
    output_path: Path,
    italian_contribution_months: int | None = None,
) -> dict[str, Any]:
    inps = _read_json(inps_snapshot_path, "INPS pension snapshot")
    spanish = _read_json(spanish_pension_snapshot_path, "Spanish statutory pension snapshot")
    rule_pack = load_rule_pack(rule_pack_path)
    _validate_snapshot_schema(inps, "inps-pension/v1", "INPS pension")
    _validate_snapshot_schema(spanish, "spanish-statutory-pension/v1", "Spanish statutory pension")

    italian = _italian_entitlement(inps, italian_contribution_months)
    spanish_entitlement = _spanish_entitlement(spanish)
    rule_period_gaps = _rule_period_gaps(inps, spanish, rule_pack)
    for country_result, country in ((italian, "IT"), (spanish_entitlement, "ES")):
        gaps = rule_period_gaps[country]
        country_result["data_gaps"].extend(gaps)
        if gaps:
            country_result["entitlement"]["status"] = "not_assessed_rule_pack_period"
    data_gaps = []
    data_gaps.extend(italian["data_gaps"])
    data_gaps.extend(spanish_entitlement["data_gaps"])

    period_summary = _period_summary(italian, spanish_entitlement)
    pro_rata = _pro_rata_diagnostics(italian, spanish_entitlement, period_summary)
    status = _status(italian, spanish_entitlement, period_summary, rule_period_gaps)

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "status": status,
        "rule_pack": {
            "path": str(rule_pack_path),
            "rule_pack_id": rule_pack["rule_pack_id"],
            "schema_version": rule_pack["schema_version"],
            "valid_from": rule_pack["valid_from"],
            "valid_to": rule_pack["valid_to"],
            "source_refs": rule_pack["source_refs"],
            "limitations": rule_pack["limitations"],
        },
        "sources": {
            "italy": {"path": str(inps_snapshot_path), "schema_version": inps.get("schema_version")},
            "spain": {"path": str(spanish_pension_snapshot_path), "schema_version": spanish.get("schema_version")},
        },
        "coordination_principles": rule_pack["coordination_principles"],
        "period_summary": period_summary,
        "national_entitlements": [italian["entitlement"], spanish_entitlement["entitlement"]],
        "pro_rata_diagnostics": pro_rata,
        "data_gaps": data_gaps,
        "warnings": [
            "This is an internal coordination dossier, not an official P1 decision.",
            "This dossier does not assess any Article 57 payment obligation or payer without a source-bound Article 57 assessment and institutional records.",
        ],
        "notes": (
            "EU coordination aggregates periods for entitlement and theoretical/pro-rata calculation under the rule "
            "pack. It does not transfer, merge, or recalculate national contribution bases, and it does not determine "
            "official recognition, payment obligation, or payer."
        ),
    }
    return _write_snapshot(snapshot, output_path)


def load_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    data = _read_json(rule_pack_path, "EU pension coordination rule pack")
    required = (
        "schema_version",
        "rule_pack_id",
        "jurisdictions",
        "currency",
        "valid_from",
        "valid_to",
        "source_refs",
        "coordination_principles",
        "required_inputs",
        "calculation_limits",
        "limitations",
    )
    for field in required:
        if field not in data:
            raise EuPensionCoordinationError(f"EU pension coordination rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise EuPensionCoordinationError(f"Unsupported EU pension coordination rule pack schema: {data['schema_version']}")
    if set(data["jurisdictions"]) != {"IT", "ES", "EU"}:
        raise EuPensionCoordinationError("EU pension coordination jurisdictions must be IT, ES and EU")
    valid_from = _candidate_month(data["valid_from"])
    valid_to = _candidate_month(data["valid_to"])
    if valid_from is None or valid_to is None or valid_from > valid_to:
        raise EuPensionCoordinationError("EU pension coordination rule pack must have a valid ordered validity period")
    _validate_source_refs(data["source_refs"])
    try:
        require_fresh_pension_rule_pack(rule_pack_path)
    except PensionSourceFreshnessError as exc:
        raise EuPensionCoordinationError(str(exc)) from exc
    _validate_principles(data["coordination_principles"])
    if not isinstance(data.get("pro_rata_method"), dict):
        raise EuPensionCoordinationError("EU pension coordination rule pack must contain pro_rata_method")
    article_57 = data["pro_rata_method"].get("article_57_source_bound")
    if not isinstance(article_57, dict):
        raise EuPensionCoordinationError("EU pension coordination rule pack must define article_57_source_bound")
    if article_57.get("contract_schema_version") != "v0.17" or article_57.get("canonicalization_profile") != "fo-art57-c14n-v4":
        raise EuPensionCoordinationError("EU pension coordination Article 57 contract must be v0.17/fo-art57-c14n-v4")
    if article_57.get("human_review_required") is not True:
        raise EuPensionCoordinationError("EU pension coordination Article 57 contract must require human review")
    annex_policy = article_57.get("annex_viii_part_2")
    if not isinstance(annex_policy, dict) or not isinstance(annex_policy.get("applicable_annex_part_2_version"), str) or not annex_policy.get("applicable_annex_part_2_version"):
        raise EuPensionCoordinationError("EU pension coordination Article 57 Annex VIII applicability version is required")
    if not _iso_date(annex_policy.get("applicable_annex_part_2_valid_from")) or (annex_policy.get("applicable_annex_part_2_valid_to") is not None and not _iso_date(annex_policy.get("applicable_annex_part_2_valid_to"))):
        raise EuPensionCoordinationError("EU pension coordination Article 57 Annex VIII validity dates must be ISO dates")
    if not isinstance(data["pro_rata_method"].get("overlap_policy"), dict):
        raise EuPensionCoordinationError("EU pension coordination rule pack must define overlap_policy")
    if not isinstance(data["limitations"], list) or not data["limitations"]:
        raise EuPensionCoordinationError("EU pension coordination rule pack must contain limitations")
    return data


def _rule_period_gaps(
    inps: dict[str, Any], spanish: dict[str, Any], rule_pack: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    valid_from = rule_pack["valid_from"][:7]
    valid_to = rule_pack["valid_to"][:7]
    projection = inps.get("projection", {}) if isinstance(inps.get("projection"), dict) else {}
    candidates = {
        "IT": (projection.get("retirement_date"), "INPS projection"),
        "ES": (spanish.get("retirement_date"), "Spanish statutory pension snapshot"),
    }
    result: dict[str, list[dict[str, Any]]] = {"IT": [], "ES": []}
    for country, (candidate, source_label) in candidates.items():
        candidate_month = _candidate_month(candidate)
        if candidate_month is None:
            result[country].append(
                {
                    "code": "missing_or_invalid_retirement_date_for_rule_pack_period",
                    "message": f"{source_label} must provide a valid retirement date before the coordination rule pack can be applied.",
                    "country": country,
                }
            )
        elif not valid_from <= candidate_month <= valid_to:
            result[country].append(
                {
                    "code": "retirement_date_outside_rule_pack_period",
                    "message": f"{source_label} retirement date is outside the coordination rule pack validity period.",
                    "country": country,
                    "retirement_date": candidate,
                    "valid_from": rule_pack["valid_from"],
                    "valid_to": rule_pack["valid_to"],
                }
            )
    return result


def _candidate_month(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 7:
            date.fromisoformat(f"{value}-01")
            return value
        if len(value) == 10:
            parsed = date.fromisoformat(value)
            return parsed.strftime("%Y-%m")
    except ValueError:
        return None
    return None


def _italian_entitlement(inps: dict[str, Any], italian_contribution_months: int | None) -> dict[str, Any]:
    projection = inps.get("projection", {}) if isinstance(inps.get("projection"), dict) else {}
    contribution_position = (
        inps.get("contribution_position", {}) if isinstance(inps.get("contribution_position"), dict) else {}
    )
    gaps: list[dict[str, Any]] = []
    monthly = projection.get("monthly_gross_pension")
    if monthly is None:
        gaps.append({"code": "missing_italian_projected_pension", "message": "INPS projected monthly gross pension is missing."})
    if italian_contribution_months is None:
        gaps.append(
            {
                "code": "missing_italian_periods_normalized_months",
                "message": "Italian contribution periods are not normalized in months for EU coordination.",
            }
        )
    elif italian_contribution_months < 0:
        raise EuPensionCoordinationError("Italian contribution months cannot be negative.")

    return {
        "months": italian_contribution_months,
        "data_gaps": gaps,
        "entitlement": {
            "country": "IT",
            "source_type": "inps-pension/v1",
            "status": "documentary_projection" if monthly is not None else "missing_projection",
            "independent_benefit": {
                "monthly_gross_amount": monthly,
                "currency": "EUR" if monthly is not None else None,
                "retirement_date": projection.get("retirement_date"),
                "prices_year": projection.get("prices_year"),
                "source": "INPS projection document",
            },
            "periods": {
                "normalized_months": italian_contribution_months,
                "raw_pension_weeks": contribution_position.get("pension_contribution_weeks"),
                "raw_separate_management_weeks": contribution_position.get("separate_management_weeks"),
                "normalization_status": "explicit_input" if italian_contribution_months is not None else "missing",
            },
            "data_gaps": gaps,
        },
    }


def _spanish_entitlement(spanish: dict[str, Any]) -> dict[str, Any]:
    gaps: list[dict[str, Any]] = []
    eligibility = spanish.get("eligibility", {}) if isinstance(spanish.get("eligibility"), dict) else {}
    months = eligibility.get("contribution_months")
    if months is None:
        gaps.append(
            {
                "code": "missing_spanish_periods_normalized_months",
                "message": "Spanish statutory pension snapshot does not expose contribution months.",
            }
        )
    gross = spanish.get("gross_pension") if isinstance(spanish.get("gross_pension"), dict) else None
    if spanish.get("status") != "complete":
        gaps.append(
            {
                "code": "spanish_pension_not_calculable",
                "message": "Spanish statutory pension is not complete; coordination keeps the Spanish gap separate.",
                "source_status": spanish.get("status"),
            }
        )

    return {
        "months": int(months) if months is not None else None,
        "data_gaps": gaps,
        "entitlement": {
            "country": "ES",
            "source_type": "spanish-statutory-pension/v1",
            "status": "internal_estimate" if spanish.get("status") == "complete" else "not_calculable",
            "independent_benefit": {
                "monthly_gross_amount": gross.get("monthly_amount") if gross else None,
                "annual_gross_amount": gross.get("annual_amount") if gross else None,
                "currency": gross.get("currency") if gross else None,
                "retirement_date": spanish.get("retirement_date"),
                "source": "Spanish statutory pension internal estimate",
            },
            "periods": {
                "normalized_months": int(months) if months is not None else None,
                "normalization_status": "from_spanish_statutory_pension_snapshot" if months is not None else "missing",
            },
            "source_data_gaps": spanish.get("data_gaps", []),
            "data_gaps": gaps,
        },
    }


def _period_summary(italian: dict[str, Any], spanish: dict[str, Any]) -> dict[str, Any]:
    it_months = italian["months"]
    es_months = spanish["months"]
    if it_months is None or es_months is None:
        return {
            "status": "not_normalized",
            "italy_months": it_months,
            "spain_months": es_months,
            "total_eu_months": None,
            "ratios": {},
        }
    total = it_months + es_months
    ratios = {}
    if total > 0:
        ratios = {
            "IT": _decimal_ratio(Decimal(it_months), Decimal(total)),
            "ES": _decimal_ratio(Decimal(es_months), Decimal(total)),
        }
    return {
        "status": "normalized",
        "italy_months": it_months,
        "spain_months": es_months,
        "total_eu_months": total,
        "ratios": ratios,
    }


def _pro_rata_diagnostics(
    italian: dict[str, Any],
    spanish: dict[str, Any],
    period_summary: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "method": "Regulation 883/2004 Article 52 theoretical amount and pro-rata benefit",
        "periods_usable": period_summary["status"] == "normalized",
        "countries": [],
    }
    for country, source in (("IT", italian), ("ES", spanish)):
        missing = []
        if period_summary["status"] != "normalized":
            missing.append("normalized_periods")
        missing.append("national_theoretical_amount")
        base["countries"].append(
            {
                "country": country,
                "period_ratio": period_summary.get("ratios", {}).get(country),
                "pro_rata_status": "not_calculable",
                "missing_inputs": missing,
                "message": "Pro-rata is documented as method but not calculated until theoretical national amount is available.",
            }
        )
    return base


def _status(
    italian: dict[str, Any],
    spanish: dict[str, Any],
    period_summary: dict[str, Any],
    rule_period_gaps: dict[str, list[dict[str, Any]]],
) -> str:
    has_it = italian["entitlement"]["status"] != "missing_projection"
    has_es = spanish["entitlement"]["status"] != "not_calculable"
    if not has_it and not has_es:
        return "blocked_missing_inputs"
    if period_summary["status"] == "normalized" and has_it and has_es and not any(rule_period_gaps.values()):
        return "complete"
    return "partial"


def _validate_source_refs(source_refs: Any) -> None:
    if not isinstance(source_refs, list) or not source_refs:
        raise EuPensionCoordinationError("EU pension coordination rule pack must contain source_refs")
    allowed_prefixes = (
        "https://eur-lex.europa.eu/",
        "https://europa.eu/",
        "https://prestaciones.seg-social.es/",
        "https://www.seg-social.es/",
        "https://www.boe.es/",
    )
    for source_ref in source_refs:
        for field in ("source_id", "title", "url", "retrieved_on", "provisions"):
            if field not in source_ref:
                raise EuPensionCoordinationError(f"EU pension coordination source_ref missing field: {field}")
        if not str(source_ref["url"]).startswith(allowed_prefixes):
            raise EuPensionCoordinationError("EU pension coordination source_ref must use an official EU or Spanish URL")
        if not isinstance(source_ref["provisions"], list) or not source_ref["provisions"]:
            raise EuPensionCoordinationError("EU pension coordination source_ref provisions must be non-empty")


def _validate_principles(principles: dict[str, Any]) -> None:
    for field in (
        "separate_national_entitlements",
        "aggregation_for_entitlement_and_theoretical_calculation",
        "no_transfer_or_merger_of_contributions",
        "compare_independent_and_pro_rata_when_calculable",
        "payment_obligation_not_assessed_without_article_57_evidence",
    ):
        if principles.get(field) is not True:
            raise EuPensionCoordinationError(f"EU pension coordination principle must be true: {field}")


def _iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _validate_snapshot_schema(data: dict[str, Any], expected: str, label: str) -> None:
    if data.get("schema_version") != expected:
        raise EuPensionCoordinationError(f"Unsupported {label} schema: {data.get('schema_version')}")


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EuPensionCoordinationError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EuPensionCoordinationError(f"Invalid {label} JSON: {path}") from exc


def _write_snapshot(snapshot: dict[str, Any], output_path: Path) -> dict[str, Any]:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise EuPensionCoordinationError(f"Cannot write EU pension coordination snapshot: {output_path}") from exc
    return snapshot


def _decimal_ratio(numerator: Decimal, denominator: Decimal) -> str:
    try:
        return format((numerator / denominator).quantize(Decimal("0.0001")), "f")
    except (InvalidOperation, ZeroDivisionError) as exc:
        raise EuPensionCoordinationError("Invalid period ratio calculation") from exc
