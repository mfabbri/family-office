import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "eu-pension-coordination-it-es/v1"
RECORD_TYPE = "EuPensionCoordinationItEsSnapshot"
RULE_PACK_SCHEMA_VERSION = "eu-pension-coordination-rule-pack/v1"


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
    data_gaps = []
    data_gaps.extend(italian["data_gaps"])
    data_gaps.extend(spanish_entitlement["data_gaps"])

    period_summary = _period_summary(italian, spanish_entitlement)
    pro_rata = _pro_rata_diagnostics(italian, spanish_entitlement, period_summary)
    status = _status(italian, spanish_entitlement, period_summary)

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "status": status,
        "rule_pack": {
            "path": str(rule_pack_path),
            "rule_pack_id": rule_pack["rule_pack_id"],
            "schema_version": rule_pack["schema_version"],
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
            "Italian and Spanish entitlements remain separate and are paid by their respective institutions.",
        ],
        "notes": (
            "EU coordination aggregates periods only where needed for entitlement and pro-rata diagnostics. "
            "It does not transfer, merge or recalculate national contributions."
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
    _validate_source_refs(data["source_refs"])
    _validate_principles(data["coordination_principles"])
    if not isinstance(data["limitations"], list) or not data["limitations"]:
        raise EuPensionCoordinationError("EU pension coordination rule pack must contain limitations")
    return data


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


def _status(italian: dict[str, Any], spanish: dict[str, Any], period_summary: dict[str, Any]) -> str:
    has_it = italian["entitlement"]["status"] != "missing_projection"
    has_es = spanish["entitlement"]["status"] != "not_calculable"
    if not has_it and not has_es:
        return "blocked_missing_inputs"
    if period_summary["status"] == "normalized" and has_it and has_es:
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
        "aggregation_for_entitlement_only",
        "no_transfer_or_merger_of_contributions",
        "compare_independent_and_pro_rata_when_calculable",
        "separate_payment_by_country",
    ):
        if principles.get(field) is not True:
            raise EuPensionCoordinationError(f"EU pension coordination principle must be true: {field}")


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
