import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "it-es-pension-tax-classification/v1"
INPUT_SCHEMA_VERSION = "it-es-pension-tax-classification-input/v1"
INPUT_RECORD_TYPE = "ItEsPensionTaxClassificationInput"
RULE_PACK_SCHEMA_VERSION = "it-es-pension-tax-classification-rule-pack/v1"
SNAPSHOT_RECORD_TYPE = "ItEsPensionTaxClassificationSnapshot"


class ItEsPensionTaxClassificationError(ValueError):
    pass


def classify_it_es_pension_tax(
    input_path: Path,
    pension_income_snapshot_path: Path,
    rule_pack_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    plan_input = _load_json(input_path, "IT-ES pension tax classification input")
    pension_income = _load_json(pension_income_snapshot_path, "pension income snapshot")
    rule_pack = load_it_es_pension_tax_classification_rule_pack(rule_pack_path)

    errors: list[str] = []
    data_gaps: list[dict[str, Any]] = []
    _validate_input(plan_input, errors, data_gaps)
    _validate_pension_income(pension_income)
    if errors:
        raise ItEsPensionTaxClassificationError("; ".join(errors))

    status = "complete"
    rule = _find_rule_for_year(rule_pack, plan_input["tax_year"])
    if rule is None:
        status = "blocked_missing_rule"
        data_gaps.append(
            {
                "code": "tax_year_not_covered",
                "message": f"No IT-ES pension tax classification rule found for year {plan_input['tax_year']}.",
                "tax_year": plan_input["tax_year"],
            }
        )

    classifications: list[dict[str, Any]] = []
    if rule is not None:
        overrides = {item["stream_id"]: item for item in plan_input.get("stream_classifications", [])}
        for stream in pension_income.get("income_streams", []):
            if not isinstance(stream, dict):
                continue
            classifications.append(_classify_stream(stream, overrides.get(stream.get("stream_id")), plan_input, rule_pack))
        if data_gaps or any(item["data_gaps"] for item in classifications):
            status = "partial"
        if not classifications:
            status = "blocked_missing_inputs"
            data_gaps.append({"code": "missing_pension_streams", "message": "Pension income snapshot has no income streams."})

    core = {
        "source": {
            "type": "it-es-pension-tax-classification-input-json",
            "path": str(input_path),
            "pension_income_snapshot_path": str(pension_income_snapshot_path),
        },
        "input": {
            "household_id": plan_input["household_id"],
            "as_of_date": plan_input["as_of_date"],
            "tax_year": plan_input["tax_year"],
            "recipient": plan_input["recipient"],
        },
        "rule_pack": {
            "path": str(rule_pack_path),
            "rule_pack_id": rule_pack["rule_pack_id"],
            "schema_version": rule_pack["schema_version"],
            "status": rule_pack.get("status"),
            "source_refs": rule_pack.get("source_refs", []),
            "limitations": rule_pack.get("limitations", []),
        },
        "classifications": classifications,
        "summary": {
            "stream_count": len(classifications),
            "classified_stream_count": sum(1 for item in classifications if item["classification_status"] == "classified"),
            "data_gap_count": len(data_gaps) + sum(len(item["data_gaps"]) for item in classifications),
            "warning_count": sum(len(item["warnings"]) for item in classifications),
        },
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
            "IT-ES pension tax classification applies treaty classification rules to explicit pension stream facts. "
            "It does not calculate withholding, IRPEF, Spanish IRPF, foreign tax credits, net pension income or refunds."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ItEsPensionTaxClassificationError(f"Cannot write IT-ES pension tax classification snapshot: {output_path}") from exc
    return snapshot


def load_it_es_pension_tax_classification_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    data = _load_json(rule_pack_path, "IT-ES pension tax classification rule pack")
    _validate_rule_pack(data)
    return data


def _classify_stream(
    stream: dict[str, Any],
    override: dict[str, Any] | None,
    plan_input: dict[str, Any],
    rule_pack: dict[str, Any],
) -> dict[str, Any]:
    recipient = plan_input["recipient"]
    residence = recipient["fiscal_residence"]
    nationalities = set(recipient.get("nationalities", []))
    stream_id = stream.get("stream_id", "unknown_stream")
    facts = {
        "stream_id": stream_id,
        "country": stream.get("country"),
        "payer": stream.get("payer"),
        "benefit_type": stream.get("benefit_type"),
        "payer_country": None if override is None else override.get("payer_country"),
        "service_sector": None if override is None else override.get("service_sector"),
        "payer_type": None if override is None else override.get("payer_type"),
        "benefit_origin": None if override is None else override.get("benefit_origin"),
    }
    data_gaps: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    required_documents: list[str] = ["fiscal_residence_certificate", "pension_award_or_payer_statement"]

    if override is None:
        data_gaps.append(
            {
                "code": "missing_stream_classification",
                "message": "No explicit treaty classification facts were provided for this pension stream.",
                "stream_id": stream_id,
            }
        )
    payer_country = facts["payer_country"]
    service_sector = facts["service_sector"]
    if payer_country not in ("IT", "ES"):
        data_gaps.append({"code": "missing_or_unsupported_payer_country", "message": "Payer country must be IT or ES.", "stream_id": stream_id})
    if residence not in ("IT", "ES"):
        data_gaps.append({"code": "missing_or_unsupported_residence", "message": "Recipient fiscal residence must be IT or ES.", "stream_id": stream_id})
    if service_sector not in ("private", "public"):
        data_gaps.append({"code": "missing_service_sector", "message": "Service sector must be private or public.", "stream_id": stream_id})

    result = {
        "stream_id": stream_id,
        "classification_status": "blocked_missing_facts",
        "facts": facts,
        "treaty_article": None,
        "rule_id": None,
        "taxing_power": None,
        "withholding": {"expected": None, "country": None},
        "required_documents": required_documents,
        "warnings": warnings,
        "confidence": "low",
        "data_gaps": data_gaps,
    }
    if data_gaps:
        return result

    if service_sector == "private":
        rule = _rule_by_classification(rule_pack, "private_previous_employment_pension")
        required_documents = rule["required_documents"]
        result.update(
            {
                "classification_status": "classified",
                "treaty_article": rule["treaty_article"],
                "rule_id": rule["rule_id"],
                "taxing_power": {"type": "exclusive", "country": residence, "basis": "recipient_fiscal_residence"},
                "withholding": {"expected": False, "country": payer_country if payer_country != residence else None},
                "required_documents": required_documents,
                "confidence": "medium",
            }
        )
        if payer_country == residence:
            warnings.append(
                {
                    "code": "domestic_pension_not_cross_border",
                    "message": "Payer country matches residence; treaty classification is retained for traceability.",
                }
            )
        return result

    if service_sector == "public" and residence != payer_country and residence in nationalities:
        rule = _rule_by_classification(rule_pack, "public_service_pension_residence_state_national")
        result.update(
            {
                "classification_status": "classified",
                "treaty_article": rule["treaty_article"],
                "rule_id": rule["rule_id"],
                "taxing_power": {"type": "exclusive", "country": residence, "basis": "residence_state_nationality_exception"},
                "withholding": {"expected": False, "country": payer_country},
                "required_documents": rule["required_documents"],
                "confidence": "medium",
            }
        )
        return result

    if service_sector == "public":
        rule = _rule_by_classification(rule_pack, "public_service_pension_source_state")
        if residence != payer_country and not nationalities:
            result["data_gaps"].append(
                {
                    "code": "missing_nationality_for_public_pension",
                    "message": "Nationality is required to test the Article 19.2 residence-state exception.",
                    "stream_id": stream_id,
                }
            )
            return result
        result.update(
            {
                "classification_status": "classified",
                "treaty_article": rule["treaty_article"],
                "rule_id": rule["rule_id"],
                "taxing_power": {"type": "exclusive", "country": payer_country, "basis": "public_service_payer_state"},
                "withholding": {"expected": True, "country": payer_country},
                "required_documents": rule["required_documents"],
                "confidence": "medium",
            }
        )
        return result

    return result


def _validate_input(data: dict[str, Any], errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if data.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append(f"Unsupported IT-ES pension tax classification input schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported IT-ES pension tax classification input record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_string(data, "as_of_date", errors)
    if not isinstance(data.get("tax_year"), int):
        errors.append("tax_year must be an integer")
    recipient = data.get("recipient")
    if not isinstance(recipient, dict):
        errors.append("recipient must be an object")
    else:
        _required_string(recipient, "person_id", errors, prefix="recipient.")
        _required_string(recipient, "fiscal_residence", errors, prefix="recipient.")
        nationalities = recipient.get("nationalities", [])
        if not isinstance(nationalities, list) or any(not isinstance(item, str) or not item for item in nationalities):
            errors.append("recipient.nationalities must be a list of non-empty strings")
    classifications = data.get("stream_classifications", [])
    if not isinstance(classifications, list):
        errors.append("stream_classifications must be a list")
        return
    seen: set[str] = set()
    for index, item in enumerate(classifications):
        if not isinstance(item, dict):
            errors.append(f"stream_classifications[{index}] must be an object")
            continue
        stream_id = _required_string(item, "stream_id", errors, prefix=f"stream_classifications[{index}].")
        if stream_id:
            if stream_id in seen:
                errors.append(f"Duplicate stream_id: {stream_id}")
            seen.add(stream_id)
        _required_string(item, "payer_country", errors, prefix=f"stream_classifications[{index}].")
        _required_string(item, "service_sector", errors, prefix=f"stream_classifications[{index}].")
        _required_string(item, "payer_type", errors, prefix=f"stream_classifications[{index}].")
        _required_string(item, "benefit_origin", errors, prefix=f"stream_classifications[{index}].")
    _validate_declared_gaps(data.get("data_gaps", []), errors, data_gaps)


def _validate_pension_income(data: dict[str, Any]) -> None:
    if data.get("schema_version") != "pension-income/v1":
        raise ItEsPensionTaxClassificationError(
            f"Unsupported pension income schema: {data.get('schema_version')}; expected pension-income/v1"
        )


def _validate_rule_pack(data: dict[str, Any]) -> None:
    required = ("schema_version", "rule_pack_id", "jurisdictions", "rules")
    for field in required:
        if field not in data:
            raise ItEsPensionTaxClassificationError(f"Rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise ItEsPensionTaxClassificationError(f"Unsupported rule pack schema: {data['schema_version']}")
    if sorted(data["jurisdictions"]) != ["ES", "IT"]:
        raise ItEsPensionTaxClassificationError("Rule pack jurisdictions must be IT and ES")
    if not isinstance(data["rules"], list) or not data["rules"]:
        raise ItEsPensionTaxClassificationError("Rule pack must contain at least one rule")
    for rule in data["rules"]:
        for field in ("rule_id", "valid_from", "valid_to", "treaty_article", "classification", "required_documents"):
            if field not in rule:
                raise ItEsPensionTaxClassificationError(f"IT-ES pension tax classification rule missing field: {field}")


def _find_rule_for_year(rule_pack: dict[str, Any], tax_year: int) -> dict[str, Any] | None:
    target = f"{tax_year:04d}"
    for rule in rule_pack["rules"]:
        valid_to = rule["valid_to"][:4] if rule["valid_to"] is not None else "9999"
        if rule["valid_from"][:4] <= target <= valid_to:
            return rule
    return None


def _rule_by_classification(rule_pack: dict[str, Any], classification: str) -> dict[str, Any]:
    for rule in rule_pack["rules"]:
        if rule.get("classification") == classification:
            return rule
    raise ItEsPensionTaxClassificationError(f"Rule pack missing classification: {classification}")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ItEsPensionTaxClassificationError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ItEsPensionTaxClassificationError(f"Invalid JSON in {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise ItEsPensionTaxClassificationError(f"{label} must contain a JSON object")
    return data


def _required_string(data: dict[str, Any], field: str, errors: list[str], prefix: str = "") -> str | None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{field} must be a non-empty string")
        return None
    return value


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


def _content_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _semantic_core(core: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(core))
    result["source"]["path"] = "<input>"
    result["source"]["pension_income_snapshot_path"] = "<pension-income>"
    result["rule_pack"]["path"] = "<rule-pack>"
    return result
