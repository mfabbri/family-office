import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "spanish-eu-theoretical-pension/v1"
RECORD_TYPE = "SpanishEuTheoreticalPensionEstimate"
RULE_PACK_SCHEMA_VERSION = "spanish-eu-theoretical-pension-rule-pack/v1"
PRO_RATA_INPUT_SCHEMA_VERSION = "it-es-eu-pension-pro-rata-input/v1"
RECONCILIATION_SCHEMA_VERSION = "spanish-contribution-reconciliation/v1"


class SpanishEuTheoreticalPensionError(ValueError):
    pass


def build_spanish_eu_theoretical_pension(
    pro_rata_input_path: Path,
    reconciliation_snapshot_path: Path,
    rule_pack_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    pro_rata_input = _read_json(pro_rata_input_path, "IT-ES EU pension pro-rata input")
    reconciliation = _read_json(reconciliation_snapshot_path, "Spanish contribution reconciliation snapshot")
    rule_pack = load_spanish_eu_theoretical_rule_pack(rule_pack_path)
    _validate_inputs(pro_rata_input, reconciliation)

    retirement_date = _retirement_date(pro_rata_input)
    effective_rules = _effective_rules(rule_pack, retirement_date)
    periods = _period_months(pro_rata_input.get("insurance_periods"), retirement_date)
    rule_gaps = _rule_period_gaps(effective_rules, retirement_date)
    base_inputs = _base_inputs(reconciliation, periods, effective_rules, retirement_date)
    percentage = _accrued_percentage(effective_rules, len(periods["EU"]))

    data_gaps: list[dict[str, Any]] = []
    data_gaps.extend(_upstream_gaps(pro_rata_input))
    data_gaps.extend(periods["data_gaps"])
    data_gaps.extend(rule_gaps)
    data_gaps.extend(base_inputs["data_gaps"])

    snapshot = _base_snapshot(pro_rata_input_path, reconciliation_snapshot_path, rule_pack_path, rule_pack, effective_rules, retirement_date)
    snapshot.update(
        {
            "status": "complete" if not data_gaps else "blocked_missing_inputs",
            "periods": {
                "spain_months": len(periods["ES"]),
                "foreign_eu_months": len(periods["foreign_eu"]),
                "total_eu_non_overlapping_months": len(periods["EU"]),
            },
            "base_reguladora": base_inputs["result"] if not data_gaps else None,
            "accrued_percentage": percentage,
            "spanish_theoretical_pension": None,
            "data_gaps": data_gaps,
            "warnings": _warnings(rule_pack, effective_rules),
        }
    )
    if not data_gaps:
        base_total = sum((_decimal(item["base_amount"], "base_amount") for item in base_inputs["selected_bases"]), Decimal("0.00"))
        divisor = _decimal(effective_rules["base_reguladora"]["divisor"], "base_reguladora.divisor")
        base_reguladora = _round_money(base_total / divisor)
        rate = _decimal(percentage["percentage"], "accrued_percentage.percentage")
        monthly = _round_money(base_reguladora * rate)
        payments = int(effective_rules["payment_schedule"]["ordinary_payments_per_year"])
        annual = _round_money(monthly * Decimal(payments))
        snapshot["base_reguladora"].update(
            {
                "amount": _money(base_reguladora),
                "selected_base_total": _money(base_total),
            }
        )
        snapshot["spanish_theoretical_pension"] = {
            "monthly_gross_amount": _money(monthly),
            "annual_gross_amount": _money(annual),
            "currency": rule_pack["currency"],
            "payments_per_year": payments,
            "source": f"{SCHEMA_VERSION}:{output_path.name}",
            "source_country": "ES",
            "basis": "spanish_only_bases",
            "method": rule_pack["theoretical_amount_method"],
        }
    return _write_snapshot(snapshot, output_path)


def load_spanish_eu_theoretical_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    data = _read_json(rule_pack_path, "Spanish EU theoretical pension rule pack")
    required = (
        "schema_version",
        "rule_pack_id",
        "jurisdictions",
        "currency",
        "valid_from",
        "valid_to",
        "source_refs",
        "theoretical_amount_method",
        "base_reguladora",
        "pension_percentage",
        "payment_schedule",
        "ipc_index",
        "limitations",
    )
    for field in required:
        if field not in data:
            raise SpanishEuTheoreticalPensionError(f"Spanish EU theoretical rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise SpanishEuTheoreticalPensionError(f"Unsupported Spanish EU theoretical rule pack schema: {data['schema_version']}")
    if set(data["jurisdictions"]) != {"ES", "EU"}:
        raise SpanishEuTheoreticalPensionError("Spanish EU theoretical rule pack jurisdictions must be ES and EU")
    if data["currency"] != "EUR":
        raise SpanishEuTheoreticalPensionError("Spanish EU theoretical rule pack currency must be EUR")
    if data["theoretical_amount_method"].get("italian_periods_used_as_spanish_bases") is not False:
        raise SpanishEuTheoreticalPensionError("Rule pack must forbid using Italian periods as Spanish bases")
    _validate_source_refs(data["source_refs"])
    return data


def _base_inputs(
    reconciliation: dict[str, Any],
    periods: dict[str, Any],
    effective_rules: dict[str, Any],
    retirement_date: str,
) -> dict[str, Any]:
    params = effective_rules["base_reguladora"]
    window = _lookback_window(retirement_date, int(params["lookback_months"]))
    spanish_bases = _official_spanish_bases(reconciliation)
    selected_candidates: list[dict[str, Any]] = []
    missing: list[str] = []
    spanish_base_missing: list[str] = []
    nearest_missing: list[str] = []
    ipc_missing: list[dict[str, str]] = []

    for month in window:
        if month in spanish_bases:
            selected_candidates.append({**spanish_bases[month], "basis_source": "official_spanish_base"})
            continue
        if month in periods["ES"]:
            spanish_base_missing.append(month)
            continue
        if month not in periods["foreign_eu"]:
            missing.append(month)
            continue
        nearest = _nearest_spanish_base(month, spanish_bases)
        if nearest is None:
            nearest_missing.append(month)
            continue
        factor = _ipc_factor(effective_rules, nearest["month"], month)
        if factor is None:
            ipc_missing.append({"source_month": nearest["month"], "target_month": month})
            continue
        amount = _round_money(_decimal(nearest["base_amount"], "nearest.base_amount") * factor)
        selected_candidates.append(
            {
                "month": month,
                "base_amount": _money(amount),
                "currency": nearest.get("currency", "EUR"),
                "basis_source": "nearest_spanish_base_updated_by_ipc",
                "nearest_spanish_base_month": nearest["month"],
                "ipc_factor": format(factor, "f"),
                "source_documents": nearest.get("source_documents", []),
            }
        )

    required = int(params["selected_highest_bases"])
    data_gaps: list[dict[str, Any]] = []
    if missing:
        data_gaps.append({"code": "missing_eu_periods_in_base_window", "message": "Every base window month must be covered by ES or foreign EU periods.", "months": missing})
    if spanish_base_missing:
        data_gaps.append(
            {
                "code": "missing_spanish_official_base_months",
                "message": "Spanish months in the base window require official Spanish contribution bases.",
                "months": spanish_base_missing,
            }
        )
    if nearest_missing:
        data_gaps.append({"code": "missing_spanish_base_for_foreign_months", "message": "Foreign EU months require at least one real Spanish contribution base.", "months": nearest_missing})
    if ipc_missing:
        data_gaps.append({"code": "missing_ipc_for_foreign_months", "message": "Foreign EU months require versioned IPC from the nearest Spanish base month to the target month.", "pairs": ipc_missing})
    if len(selected_candidates) < required:
        data_gaps.append(
            {
                "code": "insufficient_base_reguladora_months",
                "message": "Not enough usable Spanish/UE theoretical base months in the encoded base reguladora window.",
                "available_months": len(selected_candidates),
                "required_months": required,
                "lookback_months": int(params["lookback_months"]),
            }
        )

    selected = sorted(selected_candidates, key=lambda item: _decimal(item["base_amount"], "base_amount"), reverse=True)[:required]
    selected = sorted(selected, key=lambda item: item["month"])
    return {
        "result": {
            "amount": None,
                "currency": effective_rules["currency"],
            "selected_base_total": None,
            "selected_base_count": len(selected),
            "parameters": params,
            "selected_bases": selected,
            "candidate_month_count": len(selected_candidates),
        },
        "selected_bases": selected,
        "data_gaps": data_gaps,
    }


def _official_spanish_bases(reconciliation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for month in reconciliation.get("months", []):
        if not isinstance(month, dict) or not month.get("usable_for_estimator"):
            continue
        selected = month.get("selected_base") if isinstance(month.get("selected_base"), dict) else None
        if selected and selected.get("source_type") == "official_bases":
            month_key = str(month["month"])
            result[month_key] = {
                "month": month_key,
                "base_amount": _money(_decimal(selected["base_amount"], "selected_base.base_amount")),
                "currency": selected.get("currency", "EUR"),
                "source_documents": selected.get("source_documents", []),
            }
    return result


def _period_months(periods: Any, retirement_date: str) -> dict[str, Any]:
    result = {"ES": set(), "foreign_eu": set(), "EU": set(), "data_gaps": []}
    if not isinstance(periods, list) or not periods:
        result["data_gaps"].append({"code": "missing_dated_insurance_periods", "message": "Dated IT/ES periods are required."})
        return result
    for index, period in enumerate(periods):
        if not isinstance(period, dict):
            raise SpanishEuTheoreticalPensionError(f"Insurance period at index {index} must be an object.")
        country = period.get("country")
        if country not in {"IT", "ES"}:
            raise SpanishEuTheoreticalPensionError(f"Unsupported insurance period country at index {index}: {country}")
        months = {month for month in _months_between(period.get("start_date"), period.get("end_date"), index) if month < retirement_date}
        if country == "ES":
            result["ES"].update(months)
        else:
            result["foreign_eu"].update(months)
        result["EU"].update(months)
    return result


def _nearest_spanish_base(month: str, spanish_bases: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if not spanish_bases:
        return None
    target = _month_index(month)
    return min(spanish_bases.values(), key=lambda item: (abs(_month_index(item["month"]) - target), item["month"]))


def _ipc_factor(rule_pack: dict[str, Any], source_month: str, target_month: str) -> Decimal | None:
    source = _ipc_value(rule_pack, source_month)
    target = _ipc_value(rule_pack, target_month)
    if source is None or target is None or source == Decimal("0"):
        return None
    return target / source


def _ipc_value(effective_rules: dict[str, Any], month: str) -> Decimal | None:
    ipc = effective_rules["ipc_index"]
    values = ipc.get("values", {}) if isinstance(ipc.get("values"), dict) else {}
    if month in values:
        return _decimal(values[month], f"ipc_index.values.{month}")
    for range_item in ipc.get("identity_ranges", []) if isinstance(ipc.get("identity_ranges"), list) else []:
        if range_item.get("from_month") <= month <= range_item.get("to_month"):
            return _decimal(ipc.get("base_value", "1.000000"), "ipc_index.base_value")
    projection = ipc.get("projection") if isinstance(ipc.get("projection"), dict) else None
    if projection and projection.get("from_month") <= month <= projection.get("to_month"):
        base_value = _decimal(projection.get("base_value", "1.000000"), "ipc_projection.base_value")
        annual_rate = _decimal(projection["annual_rate"], "ipc_projection.annual_rate")
        monthly_rate = (Decimal("1.00") + annual_rate) ** (Decimal("1.00") / Decimal("12")) - Decimal("1.00")
        months = _month_index(month) - _month_index(projection["from_month"])
        return base_value * ((Decimal("1.00") + monthly_rate) ** Decimal(months))
    return None


def _accrued_percentage(effective_rules: dict[str, Any], contribution_months: int) -> dict[str, Any]:
    percentage = effective_rules["pension_percentage"]
    first_months = int(percentage["first_15_years_months"])
    rate = _decimal(percentage["first_15_years_rate"], "first_15_years_rate") if contribution_months >= first_months else Decimal("0")
    additional = max(0, contribution_months - first_months)
    applied = []
    remaining = additional
    schedule = percentage["additional_month_schedule"][0]
    for segment in schedule["segments"]:
        if remaining <= 0:
            break
        capacity = int(segment["to_additional_month"]) - int(segment["from_additional_month"]) + 1
        months = min(remaining, capacity)
        segment_rate = _decimal(segment["monthly_rate"], "monthly_rate")
        applied_rate = segment_rate * Decimal(months)
        rate += applied_rate
        applied.append({"applied_months": months, "monthly_rate": str(segment_rate), "applied_rate": format(applied_rate.normalize(), "f")})
        remaining -= months
    maximum = _decimal(percentage["maximum_rate"], "maximum_rate")
    if rate > maximum:
        rate = maximum
    return {"contribution_months": contribution_months, "percentage": format(rate.normalize(), "f"), "additional_months": additional, "applied_segments": applied}


def _base_snapshot(
    pro_rata_input_path: Path,
    reconciliation_snapshot_path: Path,
    rule_pack_path: Path,
    rule_pack: dict[str, Any],
    effective_rules: dict[str, Any],
    retirement_date: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "retirement_date": retirement_date,
        "sources": {
            "pro_rata_input": {"path": str(pro_rata_input_path), "schema_version": PRO_RATA_INPUT_SCHEMA_VERSION},
            "spanish_reconciliation": {"path": str(reconciliation_snapshot_path), "schema_version": RECONCILIATION_SCHEMA_VERSION},
        },
        "rule_pack": {
            "path": str(rule_pack_path),
            "rule_pack_id": rule_pack["rule_pack_id"],
            "schema_version": rule_pack["schema_version"],
            "sha256": _file_sha256(rule_pack_path),
            "valid_from": rule_pack["valid_from"],
            "valid_to": rule_pack["valid_to"],
            "source_refs": rule_pack["source_refs"],
            "limitations": rule_pack["limitations"],
            "calculation_mode": effective_rules["calculation_mode"],
            "projection": effective_rules.get("projection_summary"),
        },
        "notes": "Internal EU theoretical Spanish pension estimate; not an official Seguridad Social or P1 decision.",
    }


def _validate_inputs(pro_rata_input: dict[str, Any], reconciliation: dict[str, Any]) -> None:
    if pro_rata_input.get("schema_version") != PRO_RATA_INPUT_SCHEMA_VERSION:
        raise SpanishEuTheoreticalPensionError(f"Unsupported pro-rata input schema: {pro_rata_input.get('schema_version')}")
    if reconciliation.get("schema_version") != RECONCILIATION_SCHEMA_VERSION:
        raise SpanishEuTheoreticalPensionError(f"Unsupported Spanish reconciliation schema: {reconciliation.get('schema_version')}")
    if not isinstance(reconciliation.get("months"), list):
        raise SpanishEuTheoreticalPensionError("Spanish reconciliation months must be a list.")


def _upstream_gaps(pro_rata_input: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = pro_rata_input.get("data_gaps")
    if not isinstance(gaps, list):
        return []
    return [
        gap
        for gap in gaps
        if isinstance(gap, dict) and gap.get("code") != "missing_spanish_theoretical_amount"
    ]


def _effective_rules(rule_pack: dict[str, Any], retirement_date: str) -> dict[str, Any]:
    candidate = f"{retirement_date}-01"
    if rule_pack["valid_from"] <= candidate <= rule_pack["valid_to"]:
        return {
            "calculation_mode": "official_encoded_rule_pack",
            "currency": rule_pack["currency"],
            "base_reguladora": rule_pack["base_reguladora"],
            "pension_percentage": rule_pack["pension_percentage"],
            "payment_schedule": rule_pack["payment_schedule"],
            "ipc_index": rule_pack["ipc_index"],
        }
    projection = rule_pack.get("planning_projection") if isinstance(rule_pack.get("planning_projection"), dict) else None
    if projection and projection.get("valid_from") <= candidate <= projection.get("valid_to"):
        ipc_index = dict(rule_pack["ipc_index"])
        ipc_index["projection"] = projection["ipc_projection"]
        return {
            "calculation_mode": projection["status"],
            "currency": rule_pack["currency"],
            "base_reguladora": projection["base_reguladora"],
            "pension_percentage": rule_pack["pension_percentage"],
            "payment_schedule": rule_pack["payment_schedule"],
            "ipc_index": ipc_index,
            "projection_summary": {
                "source": projection["source"],
                "valid_from": projection["valid_from"],
                "valid_to": projection["valid_to"],
                "limitations": projection["limitations"],
                "ipc_projection": projection["ipc_projection"],
            },
        }
    return {
        "calculation_mode": "not_covered",
        "currency": rule_pack["currency"],
        "base_reguladora": rule_pack["base_reguladora"],
        "pension_percentage": rule_pack["pension_percentage"],
        "payment_schedule": rule_pack["payment_schedule"],
        "ipc_index": rule_pack["ipc_index"],
    }


def _rule_period_gaps(effective_rules: dict[str, Any], retirement_date: str) -> list[dict[str, Any]]:
    if effective_rules["calculation_mode"] == "not_covered":
        return [{"code": "retirement_date_not_covered_by_rule_pack", "message": "Retirement date is outside the Spanish EU theoretical rule pack period.", "retirement_date": retirement_date}]
    return []


def _warnings(rule_pack: dict[str, Any], effective_rules: dict[str, Any]) -> list[dict[str, Any]]:
    warnings = [{"code": "not_official_p1_decision", "message": "Internal estimate only; competent institutions decide official entitlement and amounts."}]
    if (
        rule_pack["ipc_index"].get("status") == "synthetic_regression_only"
        and effective_rules["calculation_mode"] != "planning_projection_not_official_future_law"
    ):
        warnings.append({"code": "synthetic_ipc_index", "message": "Rule pack IPC index is suitable for regression tests only; personal use requires official IPC values."})
    if effective_rules["calculation_mode"] == "planning_projection_not_official_future_law":
        warnings.append(
            {
                "code": "planning_projection_not_official_future_law",
                "message": "Future Spanish rules and IPC are planning assumptions, not official 2039 law or inflation data.",
            }
        )
        warnings.append(
            {
                "code": "projected_ipc_assumption",
                "message": "IPC after the last Spanish base is estimated from the declared annual projection rate.",
            }
        )
    return warnings


def _lookback_window(retirement_date: str, months: int) -> list[str]:
    end = _month_index(retirement_date) - 1
    start = end - months + 1
    return [_month_from_index(index) for index in range(start, end + 1)]


def _months_between(start_date: Any, end_date: Any, index: int) -> set[str]:
    start = _month_index(_date_prefix(start_date, f"insurance_periods[{index}].start_date"))
    end = _month_index(_date_prefix(end_date, f"insurance_periods[{index}].end_date"))
    if end < start:
        raise SpanishEuTheoreticalPensionError(f"Insurance period end precedes start at index {index}.")
    return {_month_from_index(value) for value in range(start, end + 1)}


def _date_prefix(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) < 7 or value[4] != "-":
        raise SpanishEuTheoreticalPensionError(f"{field} must be YYYY-MM or YYYY-MM-DD.")
    return value[:7]


def _retirement_date(data: dict[str, Any]) -> str:
    value = data.get("retirement_date")
    if not isinstance(value, str) or len(value) != 7 or value[4] != "-":
        raise SpanishEuTheoreticalPensionError("retirement_date must be YYYY-MM.")
    _month_index(value)
    return value


def _month_index(month: str) -> int:
    if len(month) != 7 or month[4] != "-":
        raise SpanishEuTheoreticalPensionError(f"Invalid month: {month}")
    year, month_number = month.split("-")
    if not year.isdigit() or not month_number.isdigit() or not 1 <= int(month_number) <= 12:
        raise SpanishEuTheoreticalPensionError(f"Invalid month: {month}")
    return int(year) * 12 + int(month_number) - 1


def _month_from_index(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _validate_source_refs(source_refs: Any) -> None:
    if not isinstance(source_refs, list) or not source_refs:
        raise SpanishEuTheoreticalPensionError("Rule pack must contain source_refs")
    allowed = ("https://eur-lex.europa.eu/", "https://www.seg-social.es/", "https://boe.es/", "https://www.boe.es/")
    for source_ref in source_refs:
        for field in ("source_id", "title", "url", "retrieved_on", "provisions"):
            if field not in source_ref:
                raise SpanishEuTheoreticalPensionError(f"Rule pack source_ref missing field: {field}")
        if not str(source_ref["url"]).startswith(allowed):
            raise SpanishEuTheoreticalPensionError("Rule pack source_ref must use official EU, BOE or Seguridad Social URL")


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpanishEuTheoreticalPensionError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SpanishEuTheoreticalPensionError(f"Invalid {label} JSON: {path}") from exc


def _write_snapshot(snapshot: dict[str, Any], output_path: Path) -> dict[str, Any]:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise SpanishEuTheoreticalPensionError(f"Cannot write Spanish EU theoretical pension snapshot: {output_path}") from exc
    return snapshot


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decimal(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise SpanishEuTheoreticalPensionError(f"Invalid decimal value for {field}: {value}") from exc


def _money(value: Decimal) -> str:
    return f"{_round_money(value)}"


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
