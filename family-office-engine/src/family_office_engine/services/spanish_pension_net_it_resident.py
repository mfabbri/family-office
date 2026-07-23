import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "spanish-pension-net-it-resident/v1"
INPUT_SCHEMA_VERSION = "spanish-pension-net-it-resident-input/v1"
INPUT_RECORD_TYPE = "SpanishPensionNetItResidentInput"
RULE_PACK_SCHEMA_VERSION = "spanish-pension-net-it-resident-rule-pack/v1"
SNAPSHOT_RECORD_TYPE = "SpanishPensionNetItResidentSnapshot"
CENT = Decimal("0.01")


class SpanishPensionNetItResidentError(ValueError):
    pass


def build_spanish_pension_net_it_resident(
    input_path: Path,
    pension_income_snapshot_path: Path,
    classification_snapshot_path: Path,
    rule_pack_path: Path,
    irpef_rule_pack_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    plan_input = _load_json(input_path, "Spanish pension net IT resident input")
    pension_income = _load_json(pension_income_snapshot_path, "pension income snapshot")
    classification = _load_json(classification_snapshot_path, "IT-ES pension tax classification snapshot")
    rule_pack = load_spanish_pension_net_it_resident_rule_pack(rule_pack_path)
    irpef_rule_pack = _load_json(irpef_rule_pack_path, "IRPEF rule pack")

    errors: list[str] = []
    data_gaps: list[dict[str, Any]] = []
    _validate_input(plan_input, errors, data_gaps)
    _validate_pension_income(pension_income)
    _validate_classification(classification)
    _validate_irpef_rule_pack(irpef_rule_pack)
    if errors:
        raise SpanishPensionNetItResidentError("; ".join(errors))

    status = "complete"
    rule = _find_rule_for_year(rule_pack, plan_input["tax_year"])
    irpef_rule = _find_rule_for_year(irpef_rule_pack, plan_input["tax_year"])
    if rule is None or irpef_rule is None:
        status = "blocked_missing_rule"
        if rule is None:
            data_gaps.append(
                {
                    "code": "net_rule_year_not_covered",
                    "message": f"No Spanish pension net rule found for year {plan_input['tax_year']}.",
                    "tax_year": plan_input["tax_year"],
                }
            )
        if irpef_rule is None:
            data_gaps.append(
                {
                    "code": "irpef_rule_year_not_covered",
                    "message": f"No IRPEF rule found for year {plan_input['tax_year']}.",
                    "tax_year": plan_input["tax_year"],
                }
            )

    streams: list[dict[str, Any]] = []
    if rule is not None and irpef_rule is not None:
        pension_streams = {stream["stream_id"]: stream for stream in pension_income.get("income_streams", []) if isinstance(stream, dict)}
        classifications = {
            item["stream_id"]: item
            for item in classification.get("classifications", [])
            if isinstance(item, dict) and isinstance(item.get("stream_id"), str)
        }
        stream_inputs = {item["stream_id"]: item for item in plan_input.get("streams", [])}
        for stream_id, stream_input in stream_inputs.items():
            streams.append(
                _evaluate_stream(
                    stream_input,
                    pension_streams.get(stream_id),
                    classifications.get(stream_id),
                    plan_input,
                    rule_pack,
                    irpef_rule_pack,
                    irpef_rule,
                )
            )
        if not streams:
            status = "blocked_missing_inputs"
            data_gaps.append({"code": "missing_stream_inputs", "message": "Input must declare at least one Spanish pension stream."})
        elif data_gaps or any(stream["data_gaps"] for stream in streams):
            status = "partial"

    summary = _summary(streams, data_gaps)
    core = {
        "source": {
            "type": "spanish-pension-net-it-resident-input-json",
            "path": str(input_path),
            "pension_income_snapshot_path": str(pension_income_snapshot_path),
            "classification_snapshot_path": str(classification_snapshot_path),
        },
        "input": {
            "household_id": plan_input["household_id"],
            "as_of_date": plan_input["as_of_date"],
            "tax_year": plan_input["tax_year"],
            "resident_country": plan_input["resident_country"],
            "other_italian_taxable_income": _format_money(_money(plan_input["other_italian_taxable_income"])),
        },
        "rule_pack": {
            "path": str(rule_pack_path),
            "rule_pack_id": rule_pack["rule_pack_id"],
            "schema_version": rule_pack["schema_version"],
            "status": rule_pack.get("status"),
            "source_refs": rule_pack.get("source_refs", []),
            "limitations": rule_pack.get("limitations", []),
        },
        "irpef_rule_pack": {
            "path": str(irpef_rule_pack_path),
            "rule_pack_id": irpef_rule_pack["rule_pack_id"],
            "schema_version": irpef_rule_pack["schema_version"],
            "status": irpef_rule_pack.get("status"),
        },
        "streams": streams,
        "summary": summary,
        "data_gaps": data_gaps,
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": status,
        **core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(_semantic_core(core)),
        },
        "notes": (
            "Spanish pension net for Italian resident uses explicit gross pension, treaty classification and Italian "
            "national IRPEF rule packs. It does not calculate deductions, surtaxes, Spanish withholding from rates, "
            "refunds, advance payments or full tax returns."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise SpanishPensionNetItResidentError(f"Cannot write Spanish pension net snapshot: {output_path}") from exc
    return snapshot


def load_spanish_pension_net_it_resident_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    data = _load_json(rule_pack_path, "Spanish pension net IT resident rule pack")
    _validate_rule_pack(data)
    return data


def _evaluate_stream(
    stream_input: dict[str, Any],
    pension_stream: dict[str, Any] | None,
    classification: dict[str, Any] | None,
    plan_input: dict[str, Any],
    rule_pack: dict[str, Any],
    irpef_rule_pack: dict[str, Any],
    irpef_rule: dict[str, Any],
) -> dict[str, Any]:
    stream_id = stream_input["stream_id"]
    gaps: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    gross_annual = _money(stream_input.get("gross_annual_amount"))
    if gross_annual == Decimal("0.00") and pension_stream is not None:
        gross = pension_stream.get("gross") if isinstance(pension_stream.get("gross"), dict) else {}
        gross_annual = _money(gross.get("annual_amount", "0.00"))
    if gross_annual == Decimal("0.00"):
        gaps.append({"code": "missing_gross_annual_amount", "message": "Gross annual pension amount is required.", "stream_id": stream_id})
    if pension_stream is None:
        gaps.append({"code": "missing_pension_income_stream", "message": "Stream is not present in pension-income/v1.", "stream_id": stream_id})
    if classification is None or classification.get("classification_status") != "classified":
        gaps.append(
            {
                "code": "missing_or_blocked_tax_classification",
                "message": "A classified it-es-pension-tax-classification/v1 stream is required.",
                "stream_id": stream_id,
            }
        )

    foreign_withholding = _money(stream_input.get("spanish_tax_withheld", "0.00"))
    definitive = bool(stream_input.get("spanish_tax_definitive", False))
    credit_applicable = bool(stream_input.get("foreign_tax_credit_applicable", False))
    credit_capacity = _optional_money(stream_input.get("declared_credit_capacity"))
    other_income = _money(plan_input["other_italian_taxable_income"])
    result = {
        "stream_id": stream_id,
        "status": "blocked_missing_inputs",
        "gross": {"annual_amount": _format_money(gross_annual), "currency": "EUR"},
        "classification": _classification_summary(classification),
        "spanish_tax": {
            "withheld": _format_money(foreign_withholding),
            "definitive": definitive,
        },
        "italian_tax": None,
        "foreign_tax_credit": None,
        "net": None,
        "confidence": "low",
        "warnings": warnings,
        "data_gaps": gaps,
    }
    if gaps:
        return result

    taxing_country = classification["taxing_power"]["country"]
    taxable_in_italy = taxing_country == "IT"
    if taxing_country not in ("IT", "ES"):
        result["data_gaps"].append({"code": "unsupported_taxing_power_country", "message": "Taxing power country must be IT or ES.", "stream_id": stream_id})
        return result

    tax_before = _calculate_progressive_tax(irpef_rule, other_income)
    tax_after = _calculate_progressive_tax(irpef_rule, other_income + gross_annual) if taxable_in_italy else tax_before
    incremental_tax = tax_after - tax_before
    total_taxable_income = other_income + gross_annual if taxable_in_italy else other_income
    art165_limit = Decimal("0.00")
    credit = Decimal("0.00")
    credit_status = "not_applicable"
    if taxable_in_italy:
        art165_limit = _art165_limit(tax_after, gross_annual, total_taxable_income)
        if foreign_withholding > Decimal("0.00"):
            if definitive and credit_applicable:
                credit_limit_values = [foreign_withholding, incremental_tax, art165_limit]
                if credit_capacity is not None:
                    credit_limit_values.append(credit_capacity)
                credit = min(credit_limit_values)
                credit_status = "applied" if credit > Decimal("0.00") else "not_usable"
            else:
                credit_status = "blocked_not_definitive_or_not_applicable"
                result["data_gaps"].append(
                    {
                        "code": "foreign_tax_credit_not_supported_by_input",
                        "message": "Foreign tax credit requires definitive foreign tax and explicit applicability.",
                        "stream_id": stream_id,
                    }
                )
    elif foreign_withholding == Decimal("0.00"):
        warnings.append(
            {
                "code": "source_state_taxing_power_without_declared_withholding",
                "message": "Classification assigns taxing power to Spain but no Spanish withholding was declared.",
            }
        )

    italian_net_tax = max(Decimal("0.00"), incremental_tax - credit)
    net = gross_annual - foreign_withholding - italian_net_tax
    result.update(
        {
            "status": "complete" if not result["data_gaps"] else "partial",
            "italian_tax": {
                "taxable_in_italy": taxable_in_italy,
                "other_taxable_income": _format_money(other_income),
                "total_taxable_income": _format_money(total_taxable_income),
                "gross_irpef_before_pension": _format_money(tax_before),
                "gross_irpef_after_pension": _format_money(tax_after),
                "incremental_tax_on_pension": _format_money(incremental_tax),
                "method": "national_gross_irpef_incremental",
                "rule_pack_id": irpef_rule_pack["rule_pack_id"],
            },
            "foreign_tax_credit": {
                "status": credit_status,
                "art165_limit": _format_money(art165_limit),
                "declared_credit_capacity": None if credit_capacity is None else _format_money(credit_capacity),
                "amount": _format_money(credit),
                "method": rule_pack["credit_method"]["method_id"],
            },
            "net": {
                "annual_amount": _format_money(net),
                "currency": "EUR",
                "method": "gross - declared_spanish_tax_withheld - italian_incremental_tax_after_credit",
            },
            "confidence": "medium" if not result["data_gaps"] else "low",
        }
    )
    return result


def _summary(streams: list[dict[str, Any]], data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    gross_total = Decimal("0.00")
    net_total = Decimal("0.00")
    complete_ids: list[str] = []
    for stream in streams:
        if stream.get("status") == "complete" and stream.get("net"):
            complete_ids.append(stream["stream_id"])
            gross_total += _money(stream["gross"]["annual_amount"])
            net_total += _money(stream["net"]["annual_amount"])
    return {
        "stream_count": len(streams),
        "complete_stream_count": len(complete_ids),
        "complete_stream_ids": complete_ids,
        "gross_annual_total": _format_money(gross_total) if complete_ids else None,
        "net_annual_total": _format_money(net_total) if complete_ids else None,
        "data_gap_count": len(data_gaps) + sum(len(stream.get("data_gaps", [])) for stream in streams),
        "warning_count": sum(len(stream.get("warnings", [])) for stream in streams),
    }


def _classification_summary(classification: dict[str, Any] | None) -> dict[str, Any] | None:
    if classification is None:
        return None
    return {
        "classification_status": classification.get("classification_status"),
        "treaty_article": classification.get("treaty_article"),
        "rule_id": classification.get("rule_id"),
        "taxing_power": classification.get("taxing_power"),
        "withholding": classification.get("withholding"),
    }


def _validate_input(data: dict[str, Any], errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if data.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append(f"Unsupported Spanish pension net input schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported Spanish pension net input record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_string(data, "as_of_date", errors)
    if not isinstance(data.get("tax_year"), int):
        errors.append("tax_year must be an integer")
    _required_string(data, "resident_country", errors)
    _non_negative_money(data.get("other_italian_taxable_income"), "other_italian_taxable_income", errors)
    streams = data.get("streams")
    if not isinstance(streams, list) or not streams:
        errors.append("streams must contain at least one stream")
        return
    seen: set[str] = set()
    for index, stream in enumerate(streams):
        if not isinstance(stream, dict):
            errors.append(f"streams[{index}] must be an object")
            continue
        stream_id = _required_string(stream, "stream_id", errors, prefix=f"streams[{index}].")
        if stream_id:
            if stream_id in seen:
                errors.append(f"Duplicate stream_id: {stream_id}")
            seen.add(stream_id)
        _optional_non_negative_money(stream.get("gross_annual_amount"), f"streams[{index}].gross_annual_amount", errors)
        _non_negative_money(stream.get("spanish_tax_withheld", "0.00"), f"streams[{index}].spanish_tax_withheld", errors)
        _optional_non_negative_money(stream.get("declared_credit_capacity"), f"streams[{index}].declared_credit_capacity", errors)
        if "spanish_tax_definitive" in stream and not isinstance(stream["spanish_tax_definitive"], bool):
            errors.append(f"streams[{index}].spanish_tax_definitive must be a boolean")
        if "foreign_tax_credit_applicable" in stream and not isinstance(stream["foreign_tax_credit_applicable"], bool):
            errors.append(f"streams[{index}].foreign_tax_credit_applicable must be a boolean")
    _validate_declared_gaps(data.get("data_gaps", []), errors, data_gaps)


def _validate_pension_income(data: dict[str, Any]) -> None:
    if data.get("schema_version") != "pension-income/v1":
        raise SpanishPensionNetItResidentError(f"Unsupported pension income schema: {data.get('schema_version')}")


def _validate_classification(data: dict[str, Any]) -> None:
    if data.get("schema_version") != "it-es-pension-tax-classification/v1":
        raise SpanishPensionNetItResidentError(f"Unsupported classification schema: {data.get('schema_version')}")


def _validate_irpef_rule_pack(data: dict[str, Any]) -> None:
    if data.get("schema_version") != "tax-rule-pack/v1":
        raise SpanishPensionNetItResidentError(f"Unsupported IRPEF rule pack schema: {data.get('schema_version')}")
    if data.get("jurisdiction") != "IT":
        raise SpanishPensionNetItResidentError("IRPEF rule pack jurisdiction must be IT")


def _validate_rule_pack(data: dict[str, Any]) -> None:
    required = ("schema_version", "rule_pack_id", "jurisdiction", "source_country", "credit_method", "rules")
    for field in required:
        if field not in data:
            raise SpanishPensionNetItResidentError(f"Rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise SpanishPensionNetItResidentError(f"Unsupported rule pack schema: {data['schema_version']}")
    if data["jurisdiction"] != "IT" or data["source_country"] != "ES":
        raise SpanishPensionNetItResidentError("Rule pack must cover IT resident and ES source country")
    if not isinstance(data["rules"], list) or not data["rules"]:
        raise SpanishPensionNetItResidentError("Rule pack must contain at least one rule")
    for rule in data["rules"]:
        for field in ("rule_id", "valid_from", "valid_to", "resident_country", "source_country"):
            if field not in rule:
                raise SpanishPensionNetItResidentError(f"Spanish pension net rule missing field: {field}")


def _find_rule_for_year(rule_pack: dict[str, Any], tax_year: int) -> dict[str, Any] | None:
    target = f"{tax_year:04d}"
    for rule in rule_pack["rules"]:
        valid_to = rule["valid_to"][:4] if rule["valid_to"] is not None else "9999"
        if rule["valid_from"][:4] <= target <= valid_to:
            return rule
    return None


def _calculate_progressive_tax(rule: dict[str, Any], income: Decimal) -> Decimal:
    tax = Decimal("0.00")
    for bracket in rule["brackets"]:
        lower = _money(bracket["from"])
        upper = None if bracket["to"] is None else _money(bracket["to"])
        rate = _rate(bracket["rate"])
        taxable_slice = _slice_amount(income, lower, upper)
        tax += (taxable_slice * rate).quantize(CENT, rounding=ROUND_HALF_UP)
    return tax


def _slice_amount(income: Decimal, lower: Decimal, upper: Decimal | None) -> Decimal:
    if income <= lower:
        return Decimal("0.00")
    if upper is None:
        return income - lower
    return min(income, upper) - lower


def _art165_limit(italian_tax_after_pension: Decimal, foreign_income: Decimal, total_taxable_income: Decimal) -> Decimal:
    if total_taxable_income <= Decimal("0.00"):
        return Decimal("0.00")
    return (italian_tax_after_pension * foreign_income / total_taxable_income).quantize(CENT, rounding=ROUND_HALF_UP)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpanishPensionNetItResidentError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SpanishPensionNetItResidentError(f"Invalid JSON in {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise SpanishPensionNetItResidentError(f"{label} must contain a JSON object")
    return data


def _required_string(data: dict[str, Any], field: str, errors: list[str], prefix: str = "") -> str | None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{field} must be a non-empty string")
        return None
    return value


def _non_negative_money(value: Any, label: str, errors: list[str]) -> None:
    try:
        parsed = _money(value)
    except SpanishPensionNetItResidentError:
        errors.append(f"{label} must be a money value")
        return
    if parsed < Decimal("0.00"):
        errors.append(f"{label} must be greater than or equal to zero")


def _optional_non_negative_money(value: Any, label: str, errors: list[str]) -> None:
    if value in (None, ""):
        return
    _non_negative_money(value, label, errors)


def _optional_money(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    return _money(value)


def _validate_declared_gaps(raw: Any, errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if raw in (None, ""):
        return
    if not isinstance(raw, list):
        errors.append("data_gaps must be a list")
        return
    for index, gap in enumerate(raw):
        if not isinstance(gap, dict):
            errors.append(f"data_gaps[{index}] must be an object")
            continue
        code = gap.get("code")
        message = gap.get("message")
        if not isinstance(code, str) or not code.strip():
            errors.append(f"data_gaps[{index}].code must be a non-empty string")
        if not isinstance(message, str) or not message.strip():
            errors.append(f"data_gaps[{index}].message must be a non-empty string")
        if isinstance(code, str) and isinstance(message, str):
            data_gaps.append(gap)


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(CENT)
    except (InvalidOperation, TypeError) as exc:
        raise SpanishPensionNetItResidentError(f"Invalid money value: {value}") from exc


def _rate(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise SpanishPensionNetItResidentError(f"Invalid rate value: {value}") from exc


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _content_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _semantic_core(core: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(core))
    result["source"]["path"] = "<input>"
    result["source"]["pension_income_snapshot_path"] = "<pension-income>"
    result["source"]["classification_snapshot_path"] = "<classification>"
    result["rule_pack"]["path"] = "<rule-pack>"
    result["irpef_rule_pack"]["path"] = "<irpef-rule-pack>"
    return result
