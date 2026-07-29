import json
import hashlib
import calendar
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "it-es-eu-pension-pro-rata/v1"
INPUT_SCHEMA_VERSION = "it-es-eu-pension-pro-rata-input/v1"
RECORD_TYPE = "ItEsEuPensionProRataEstimate"
RULE_PACK_SCHEMA_VERSION = "eu-pension-coordination-rule-pack/v1"


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
    entitlement = _spanish_entitlement(periods_result, retirement_date, date_of_birth, recent_anchor, rule_pack)
    theoretical = _spanish_theoretical_amount(data.get("spanish_theoretical_pension"))
    pro_rata = _spanish_pro_rata(theoretical, periods_result, entitlement, rule_pack)
    data_gaps = []
    data_gaps.extend(_declared_data_gaps(data, theoretical))
    data_gaps.extend(input_gaps)
    data_gaps.extend(periods_result["data_gaps"])
    data_gaps.extend(_post_retirement_period_gaps(periods_result, retirement_date))
    data_gaps.extend(entitlement["data_gaps"])
    data_gaps.extend(theoretical["data_gaps"])
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
        "spanish_theoretical_pension": theoretical["result"],
        "spanish_pro_rata_pension": pro_rata["result"],
        "data_gaps": data_gaps,
        "warnings": _warnings(periods_result),
        "notes": (
            "EU periods are aggregated only for entitlement checks. Italian periods are not used as Spanish bases, "
            "and this estimate is not an official P1 decision."
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
    if data["coordination_principles"].get("no_transfer_or_merger_of_contributions") is not True:
        raise ItEsEuPensionProRataError("Rule pack must forbid transfer or merger of contributions")
    if data["pro_rata_method"].get("no_foreign_bases_in_spanish_theoretical_amount") is not True:
        raise ItEsEuPensionProRataError("Rule pack must forbid foreign bases in Spanish theoretical amount")
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
                "aggregation_for_entitlement_only": True,
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


def _spanish_pro_rata(
    theoretical: dict[str, Any],
    periods_result: dict[str, Any],
    entitlement: dict[str, Any],
    rule_pack: dict[str, Any],
) -> dict[str, Any]:
    gaps: list[dict[str, Any]] = []
    theoretical_result = theoretical["result"]
    total = periods_result["summary"]["total_eu_non_overlapping_months"]
    es = periods_result["summary"]["spain_months"]
    minimum_es = int(rule_pack["pro_rata_method"].get("minimum_spanish_period_months_for_pro_rata", 0))
    if entitlement["result"]["status"] == "not_eligible":
        gaps.append({"code": "spanish_entitlement_required_for_pro_rata", "message": "Pro-rata is not calculated when Spanish entitlement is not reached."})
    if theoretical_result is None:
        gaps.append({"code": "missing_theoretical_amount_for_pro_rata", "message": "Cannot calculate pro-rata without a Spanish theoretical amount."})
    if not total:
        gaps.append({"code": "missing_periods_for_pro_rata", "message": "Cannot calculate pro-rata without non-overlapping EU periods."})
    if es < minimum_es:
        gaps.append(
            {
                "code": "spanish_period_under_one_year",
                "message": "Spanish period is below the encoded minimum for a separate pro-rata benefit.",
                "spanish_months": es,
                "required_months": minimum_es,
            }
        )
    if gaps:
        return {"result": {"status": "not_calculable", "method": rule_pack["pro_rata_method"], "amounts": None}, "data_gaps": gaps}

    ratio_decimals = int(rule_pack["pro_rata_method"]["rounding"]["ratio_decimals"])
    ratio = (Decimal(es) / Decimal(total)).quantize(Decimal("1").scaleb(-ratio_decimals))
    monthly = _round_money(_decimal(theoretical_result["monthly_gross_amount"], "monthly_gross_amount") * ratio)
    annual = _round_money(_decimal(theoretical_result["annual_gross_amount"], "annual_gross_amount") * ratio)
    return {
        "result": {
            "status": "calculated",
            "method": rule_pack["pro_rata_method"],
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
                "code": "overlapping_periods_removed_from_total",
                "message": "Overlapping Italy-Spain months are counted once in the EU denominator.",
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
    return any(gap["code"] in {"retirement_date_not_covered_by_rule_pack", "missing_date_of_birth", "missing_recent_contribution_anchor_date", "spanish_ordinary_age_not_reached"} for gap in gaps)


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
    allowed_prefixes = ("https://eur-lex.europa.eu/", "https://europa.eu/", "https://prestaciones.seg-social.es/", "https://www.seg-social.es/")
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
