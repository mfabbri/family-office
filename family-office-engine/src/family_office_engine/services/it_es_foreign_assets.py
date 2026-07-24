import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "it-es-foreign-assets/v1"
INPUT_SCHEMA_VERSION = "it-es-foreign-assets-input/v1"
INPUT_RECORD_TYPE = "ItEsForeignAssetsInput"
RULE_PACK_SCHEMA_VERSION = "it-es-foreign-asset-monitoring-rule-pack/v2"
SNAPSHOT_RECORD_TYPE = "ItEsForeignAssetsSnapshot"
CENT = Decimal("0.01")
RATIO = Decimal("0.0001")


class ItEsForeignAssetsError(ValueError):
    pass


def build_it_es_foreign_assets(input_path: Path, rule_pack_path: Path, output_path: Path) -> dict[str, Any]:
    plan_input = _load_json(input_path, "IT-ES foreign assets input")
    rule_pack = load_it_es_foreign_asset_rule_pack(rule_pack_path)
    rule_pack_digest = _file_sha256(rule_pack_path)

    errors: list[str] = []
    data_gaps: list[dict[str, Any]] = []
    _validate_input(plan_input, errors, data_gaps)
    if errors:
        raise ItEsForeignAssetsError("; ".join(errors))

    status = "complete"
    rule = _find_rule_for_year(rule_pack, plan_input["tax_year"])
    if rule is None:
        status = "blocked_missing_rule"
        data_gaps.append(
            {
                "code": "tax_year_not_covered",
                "message": f"No IT-ES foreign asset monitoring rule found for year {plan_input['tax_year']}.",
                "tax_year": plan_input["tax_year"],
            }
        )
    if plan_input["base_currency"] != rule_pack["currency"]:
        status = "blocked_missing_inputs"
        data_gaps.append(
            {
                "code": "currency_not_covered",
                "message": "Input base currency must match the rule pack currency; FX conversion must be documented upstream.",
                "base_currency": plan_input["base_currency"],
                "rule_pack_currency": rule_pack["currency"],
            }
        )
    if rule is not None and _year(plan_input["as_of_date"]) != plan_input["tax_year"]:
        status = "blocked_missing_inputs"
        data_gaps.append(
            {
                "code": "as_of_date_tax_year_mismatch",
                "message": "as_of_date year must match tax_year for this deterministic contract.",
                "as_of_date": plan_input["as_of_date"],
                "tax_year": plan_input["tax_year"],
            }
        )

    assets: list[dict[str, Any]] = []
    applied_rule_id = None
    if rule is not None and status != "blocked_missing_inputs":
        applied_rule_id = rule["rule_id"]
        bank_context = _bank_context(plan_input["assets"], rule_pack)
        assets = [_evaluate_asset(asset, plan_input, rule_pack, rule, bank_context) for asset in plan_input["assets"]]
        if data_gaps or any(item["data_gaps"] for item in assets):
            status = "partial"

    totals = _totals(assets, status)
    core = {
        "source": {"type": "it-es-foreign-assets-input-json", "path": str(input_path)},
        "input": {
            "household_id": plan_input["household_id"],
            "as_of_date": plan_input["as_of_date"],
            "tax_year": plan_input["tax_year"],
            "base_currency": plan_input["base_currency"],
            "taxpayer": plan_input["taxpayer"],
        },
        "rule_pack": {
            "path": str(rule_pack_path),
            "rule_pack_id": rule_pack["rule_pack_id"],
            "schema_version": rule_pack["schema_version"],
            "content_hash": rule_pack_digest,
            "applied_rule_id": applied_rule_id,
            "status": rule_pack.get("status"),
            "source_refs": rule_pack.get("source_refs", []),
            "limitations": rule_pack.get("limitations", []),
        },
        "assets": assets,
        "totals": totals,
        "summary": {
            "asset_count": len(assets),
            "rw_required_count": sum(1 for item in assets if item["rw_monitoring"]["required"] is True),
            "ivafe_due": totals["ivafe_due"],
            "ivie_due": totals["ivie_due"],
            "data_gap_count": len(data_gaps) + sum(len(item["data_gaps"]) for item in assets),
            "warning_count": sum(len(item["warnings"]) for item in assets),
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
            "IT-ES foreign assets applies versioned RW, IVAFE and IVIE rules to explicit asset facts. "
            "It does not prepare a tax return, classify unsupported assets, calculate foreign income taxes, "
            "or infer exemptions without documented input."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ItEsForeignAssetsError(f"Cannot write IT-ES foreign assets snapshot: {output_path}") from exc
    return snapshot


def load_it_es_foreign_asset_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    data = _load_json(rule_pack_path, "IT-ES foreign asset monitoring rule pack")
    _validate_rule_pack(data)
    return data


def _evaluate_asset(
    asset: dict[str, Any],
    plan_input: dict[str, Any],
    rule_pack: dict[str, Any],
    rule: dict[str, Any],
    bank_context: dict[str, Any],
) -> dict[str, Any]:
    data_gaps: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    asset_id = asset["asset_id"]
    asset_type = asset["asset_type"]
    asset_rule = rule_pack["asset_type_rules"].get(asset_type)
    declared_values = _declared_values(asset)

    if asset["jurisdiction"] != rule["asset_jurisdiction"]:
        data_gaps.append({"code": "asset_jurisdiction_not_covered", "message": "Asset jurisdiction is not covered by this rule pack.", "asset_id": asset_id})
    if plan_input["taxpayer"]["fiscal_residence"] != rule["taxpayer_residence"]:
        data_gaps.append({"code": "taxpayer_residence_not_covered", "message": "Taxpayer residence is not covered by this rule pack.", "asset_id": asset_id})
    if asset_rule is None:
        data_gaps.append({"code": "asset_type_not_classified", "message": "Asset type is not covered by the IT-ES foreign asset rule pack.", "asset_id": asset_id, "asset_type": asset_type})
    else:
        _validate_asset_evidence(asset, asset_rule, data_gaps)
        _validate_pension_classification(asset, asset_rule, data_gaps)
        if asset_type == "foreign_real_estate":
            _validate_real_estate_credit_gap(asset, data_gaps)
        if asset_type == "foreign_bank_account" and bank_context["requires_declared_aggregate"] and not bank_context["documented"]:
            data_gaps.append(
                {
                    "code": "missing_bank_account_aggregate_values",
                    "message": "Multiple foreign bank accounts require documented aggregate maximum value and average balance.",
                    "asset_id": asset_id,
                }
            )

    ownership_share = _rate(asset["ownership_share"])
    wealth_tax = {"tax_type": None, "amount": None, "calculation_status": "blocked_missing_facts"}
    rw_required: bool | None = None
    rw_reason = "blocked_missing_facts"

    if not data_gaps and asset_rule is not None:
        if _has_domestic_intermediary_exemption(asset, asset_rule, rule_pack):
            rw_required = False
            rw_reason = "documented_italian_intermediary_conditions_met"
            wealth_tax = {"tax_type": "domestic_intermediary_review", "amount": "0.00", "calculation_status": "not_calculated_exemption_documented"}
        elif asset.get("intermediary_residence") == "IT" and asset_type in rule_pack["monitoring"]["domestic_intermediary_exemption"]["allowed_asset_types"]:
            data_gaps.append(
                {
                    "code": "domestic_intermediary_exemption_not_documented",
                    "message": "Italian intermediary exclusion requires all documented conditions from the rule pack.",
                    "asset_id": asset_id,
                }
            )
        else:
            tax_rule_key = asset_rule["wealth_tax_rule"]
            if tax_rule_key == "ivafe_bank_account":
                wealth_tax, rw_required, rw_reason = _bank_account_result(asset, rule_pack, ownership_share, bank_context)
            elif tax_rule_key == "ivie_real_estate":
                wealth_tax = _ivie_result(asset, rule_pack, ownership_share)
                rw_required = True
                rw_reason = "foreign_real_estate_subject_to_monitoring"
            else:
                wealth_tax = _proportional_financial_tax(asset, rule_pack["wealth_taxes"][tax_rule_key], ownership_share)
                rw_required = True
                rw_reason = "foreign_financial_asset_subject_to_monitoring"

    return {
        "asset_id": asset_id,
        "label": asset["label"],
        "asset_type": asset_type,
        "jurisdiction": asset["jurisdiction"],
        "intermediary_residence": asset.get("intermediary_residence"),
        "ownership_share": str(ownership_share),
        "days_held": asset["days_held"],
        "declared_values": declared_values,
        "rw_monitoring": {
            "required": rw_required,
            "reason": rw_reason,
            "category": None if asset_rule is None else asset_rule["rw_category"],
        },
        "wealth_tax": wealth_tax,
        "required_documents": [] if asset_rule is None else asset_rule.get("required_documents", []),
        "source_document_types": asset.get("source_document_types", []),
        "source_documents": asset.get("source_documents", []),
        "tax_events": _tax_events(asset, warnings, data_gaps),
        "warnings": warnings,
        "data_gaps": data_gaps,
    }


def _validate_asset_evidence(asset: dict[str, Any], asset_rule: dict[str, Any], data_gaps: list[dict[str, Any]]) -> None:
    for field in asset_rule.get("required_value_fields", []):
        if field not in asset or asset.get(field) in (None, ""):
            data_gaps.append({"code": "missing_value_field", "message": "Required asset value field is missing.", "asset_id": asset["asset_id"], "field": field})
    source_types = set(asset.get("source_document_types", []))
    missing_docs = [doc for doc in asset_rule.get("required_documents", []) if doc not in source_types]
    if missing_docs:
        data_gaps.append(
            {
                "code": "missing_required_document_types",
                "message": "Required document evidence types are missing for this asset.",
                "asset_id": asset["asset_id"],
                "missing_document_types": missing_docs,
            }
        )
    if asset["asset_type"] == "foreign_real_estate" and not asset.get("valuation_basis"):
        data_gaps.append({"code": "missing_real_estate_valuation_basis", "message": "Real estate valuation basis must be explicit.", "asset_id": asset["asset_id"]})


def _validate_pension_classification(asset: dict[str, Any], asset_rule: dict[str, Any], data_gaps: list[dict[str, Any]]) -> None:
    if not asset_rule.get("requires_structured_classification"):
        return
    classification = asset.get("classification")
    if not isinstance(classification, dict):
        data_gaps.append({"code": "pension_plan_classification_not_documented", "message": "Foreign pension plan requires a structured classification object.", "asset_id": asset["asset_id"]})
        return
    required = ("outcome", "plan_nature", "source_ref", "classified_on", "valid_for_tax_year", "documented")
    missing = [field for field in required if field not in classification]
    if missing or classification.get("documented") is not True or classification.get("valid_for_tax_year") is not True:
        data_gaps.append(
            {
                "code": "pension_plan_classification_not_documented",
                "message": "Foreign pension plan classification must be documented and valid for the tax year.",
                "asset_id": asset["asset_id"],
                "missing_fields": missing,
            }
        )
    if classification.get("outcome") not in ("monitorable_financial_product", "documented_exempt"):
        data_gaps.append({"code": "pension_plan_classification_uncertain", "message": "Foreign pension plan classification outcome is not supported.", "asset_id": asset["asset_id"]})


def _validate_real_estate_credit_gap(asset: dict[str, Any], data_gaps: list[dict[str, Any]]) -> None:
    has_foreign_property_tax = any(event.get("event_type") == "foreign_property_tax_paid" for event in asset.get("tax_events", []) if isinstance(event, dict))
    if has_foreign_property_tax and "foreign_property_tax_credit" not in asset:
        data_gaps.append(
            {
                "code": "possible_ivie_credit_not_declared",
                "message": "Foreign property tax was declared as an event, but no IVIE credit amount was explicitly provided.",
                "asset_id": asset["asset_id"],
            }
        )


def _has_domestic_intermediary_exemption(asset: dict[str, Any], asset_rule: dict[str, Any], rule_pack: dict[str, Any]) -> bool:
    exemption = rule_pack["monitoring"]["domestic_intermediary_exemption"]
    if asset["asset_type"] not in exemption["allowed_asset_types"]:
        return False
    if asset.get("intermediary_residence") != "IT":
        return False
    evidence = asset.get("domestic_intermediary_evidence", {})
    if not isinstance(evidence, dict):
        return False
    return all(evidence.get(field) is True for field in exemption["required_true_fields"])


def _bank_context(assets: list[dict[str, Any]], rule_pack: dict[str, Any]) -> dict[str, Any]:
    accounts = [
        asset
        for asset in assets
        if isinstance(asset, dict)
        and asset.get("asset_type") == "foreign_bank_account"
        and not _has_domestic_intermediary_exemption(asset, rule_pack["asset_type_rules"]["foreign_bank_account"], rule_pack)
    ]
    aggregate = rule_pack["monitoring"].get("bank_account_aggregation_required_when_count_gt", 1)
    requires_declared = len(accounts) > aggregate
    declared = None
    if accounts:
        declared = accounts[0].get("bank_account_aggregate")
    if requires_declared:
        documented = isinstance(declared, dict) and declared.get("documented") is True
        max_value = _money(declared["max_value"]) if documented and "max_value" in declared else None
        average_balance = _money(declared["average_balance"]) if documented and "average_balance" in declared else None
    elif accounts:
        documented = True
        max_value = _money(accounts[0]["max_value"])
        average_balance = _money(accounts[0]["average_balance"])
    else:
        documented = True
        max_value = Decimal("0.00")
        average_balance = Decimal("0.00")
    return {
        "count": len(accounts),
        "requires_declared_aggregate": requires_declared,
        "documented": documented,
        "max_value": max_value,
        "average_balance": average_balance,
    }


def _bank_account_result(
    asset: dict[str, Any], rule_pack: dict[str, Any], ownership_share: Decimal, bank_context: dict[str, Any]
) -> tuple[dict[str, Any], bool, str]:
    tax_rule = rule_pack["wealth_taxes"]["ivafe_bank_account"]
    max_threshold = _money(rule_pack["monitoring"]["bank_account_max_value_threshold"])
    average_threshold = _money(tax_rule["average_balance_threshold"])
    aggregate_average = bank_context["average_balance"]
    aggregate_max = bank_context["max_value"]
    ivafe_due = aggregate_average > average_threshold
    days_factor = Decimal(asset["days_held"]) / Decimal("365")
    amount = _money(tax_rule["fixed_amount"]) * ownership_share * days_factor if ivafe_due else Decimal("0.00")
    rw_required = aggregate_max > max_threshold or ivafe_due
    reason = "aggregate_max_value_or_ivafe_threshold_met" if rw_required else "below_aggregate_bank_account_monitoring_and_ivafe_thresholds"
    return (
        {
            "tax_type": tax_rule["tax_type"],
            "method": "fixed",
            "amount": _format_money(amount),
            "calculation_status": "calculated",
            "aggregate_max_value": _format_money(aggregate_max),
            "aggregate_average_balance": _format_money(aggregate_average),
        },
        rw_required,
        reason,
    )


def _proportional_financial_tax(asset: dict[str, Any], tax_rule: dict[str, Any], ownership_share: Decimal) -> dict[str, Any]:
    amount = _money(asset["period_end_value"]) * _rate(tax_rule["rate"]) * ownership_share * Decimal(asset["days_held"]) / Decimal("365")
    return {
        "tax_type": tax_rule["tax_type"],
        "method": "proportional",
        "rate": tax_rule["rate"],
        "amount": _format_money(amount),
        "calculation_status": "calculated",
    }


def _ivie_result(asset: dict[str, Any], rule_pack: dict[str, Any], ownership_share: Decimal) -> dict[str, Any]:
    tax_rule = rule_pack["wealth_taxes"]["ivie_real_estate"]
    value = _money(asset["period_end_value"])
    if asset.get("primary_residence") is True and asset.get("luxury_cadastral_category") is not True:
        return {
            "tax_type": tax_rule["tax_type"],
            "method": "proportional",
            "amount": "0.00",
            "calculation_status": "not_due_primary_residence_non_luxury",
            "valuation_basis": asset.get("valuation_basis"),
        }
    rate = _rate(tax_rule["primary_residence_luxury_rate"] if asset.get("primary_residence") is True else tax_rule["ordinary_rate"])
    gross_full_year_before_share = value * rate
    threshold = _money(tax_rule["payment_threshold_before_share_period_and_credits"])
    if gross_full_year_before_share <= threshold:
        return {
            "tax_type": tax_rule["tax_type"],
            "method": "proportional",
            "rate": str(rate),
            "amount": "0.00",
            "calculation_status": "below_payment_threshold",
            "gross_full_year_before_share": _format_money(gross_full_year_before_share),
            "valuation_basis": asset.get("valuation_basis"),
        }
    months_factor = Decimal(asset["months_held"]) / Decimal("12")
    deduction = _money(tax_rule["primary_residence_luxury_deduction"]) if asset.get("primary_residence") is True else Decimal("0.00")
    credit = _money(asset.get("foreign_property_tax_credit", "0.00"))
    amount_before_credit = max(Decimal("0.00"), (gross_full_year_before_share * ownership_share * months_factor) - deduction)
    amount = max(Decimal("0.00"), amount_before_credit - min(credit, amount_before_credit))
    return {
        "tax_type": tax_rule["tax_type"],
        "method": "proportional",
        "rate": str(rate),
        "amount": _format_money(amount),
        "calculation_status": "calculated",
        "months_held": asset["months_held"],
        "gross_full_year_before_share": _format_money(gross_full_year_before_share),
        "credit_applied": _format_money(min(credit, amount_before_credit)),
        "valuation_basis": asset.get("valuation_basis"),
    }


def _tax_events(asset: dict[str, Any], warnings: list[dict[str, Any]], data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events = []
    for index, event in enumerate(asset.get("tax_events", [])):
        if not isinstance(event, dict):
            continue
        event_id = event.get("event_id", f"event_{index}")
        documented = bool(event.get("documented", False))
        if not documented:
            warnings.append({"code": "tax_event_not_documented", "message": "Tax event is retained but not treated as verified.", "asset_id": asset["asset_id"], "event_id": event_id})
        if "amount" in event:
            try:
                _money(event["amount"])
            except ItEsForeignAssetsError:
                data_gaps.append({"code": "invalid_tax_event_amount", "message": "Tax event amount must be a money value.", "asset_id": asset["asset_id"], "event_id": event_id})
        events.append(
            {
                "event_id": event_id,
                "event_type": event.get("event_type"),
                "amount": event.get("amount"),
                "currency": event.get("currency", "EUR"),
                "documented": documented,
                "requires_income_tax_review": event.get("event_type") not in ("foreign_property_tax_paid", None),
            }
        )
    return events


def _totals(assets: list[dict[str, Any]], status: str) -> dict[str, str | None]:
    if status.startswith("blocked") and not assets:
        return {"ivafe_due": None, "ivie_due": None, "total_wealth_tax_due": None}
    ivafe = Decimal("0.00")
    ivie = Decimal("0.00")
    for asset in assets:
        tax = asset["wealth_tax"]
        if tax.get("calculation_status") not in ("calculated", "below_payment_threshold"):
            continue
        amount = _money(tax["amount"])
        if tax["tax_type"] == "IVAFE":
            ivafe += amount
        if tax["tax_type"] == "IVIE":
            ivie += amount
    return {"ivafe_due": _format_money(ivafe), "ivie_due": _format_money(ivie), "total_wealth_tax_due": _format_money(ivafe + ivie)}


def _declared_values(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        field: asset[field]
        for field in ("period_end_value", "max_value", "average_balance", "months_held", "valuation_basis", "foreign_property_tax_credit")
        if field in asset
    }


def _validate_input(data: dict[str, Any], errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if data.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append(f"Unsupported IT-ES foreign assets input schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported IT-ES foreign assets input record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_string(data, "as_of_date", errors)
    _required_string(data, "base_currency", errors)
    if not isinstance(data.get("tax_year"), int):
        errors.append("tax_year must be an integer")
    taxpayer = data.get("taxpayer")
    if not isinstance(taxpayer, dict):
        errors.append("taxpayer must be an object")
    else:
        _required_string(taxpayer, "person_id", errors, prefix="taxpayer.")
        _required_string(taxpayer, "fiscal_residence", errors, prefix="taxpayer.")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        errors.append("assets must contain at least one asset")
        return
    seen: set[str] = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            errors.append(f"assets[{index}] must be an object")
            continue
        prefix = f"assets[{index}]."
        asset_id = _required_string(asset, "asset_id", errors, prefix=prefix)
        if asset_id:
            if asset_id in seen:
                errors.append(f"Duplicate asset_id: {asset_id}")
            seen.add(asset_id)
        _required_string(asset, "label", errors, prefix=prefix)
        _required_string(asset, "asset_type", errors, prefix=prefix)
        _required_string(asset, "jurisdiction", errors, prefix=prefix)
        _required_string(asset, "intermediary_residence", errors, prefix=prefix)
        _ratio_or_error(asset.get("ownership_share"), f"{prefix}ownership_share", errors)
        if not isinstance(asset.get("days_held"), int) or asset["days_held"] < 1 or asset["days_held"] > 365:
            errors.append(f"{prefix}days_held must be an integer between 1 and 365")
        if "months_held" in asset and (not isinstance(asset["months_held"], int) or asset["months_held"] < 0 or asset["months_held"] > 12):
            errors.append(f"{prefix}months_held must be an integer between 0 and 12")
        for field in ("period_end_value", "max_value", "average_balance", "foreign_property_tax_credit"):
            if field in asset and asset[field] not in (None, ""):
                _non_negative_money(asset[field], f"{prefix}{field}", errors)
        if "source_document_types" in asset and (
            not isinstance(asset["source_document_types"], list) or any(not isinstance(item, str) or not item for item in asset["source_document_types"])
        ):
            errors.append(f"{prefix}source_document_types must be a list of non-empty strings")
    _validate_declared_gaps(data.get("data_gaps", []), errors, data_gaps)


def _validate_rule_pack(data: dict[str, Any]) -> None:
    required = ("schema_version", "rule_pack_id", "jurisdictions", "currency", "source_refs", "monitoring", "wealth_taxes", "asset_type_rules", "rules")
    for field in required:
        if field not in data:
            raise ItEsForeignAssetsError(f"Rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise ItEsForeignAssetsError(f"Unsupported rule pack schema: {data['schema_version']}")
    if sorted(data["jurisdictions"]) != ["ES", "IT"]:
        raise ItEsForeignAssetsError("Rule pack jurisdictions must be IT and ES")
    if not isinstance(data["source_refs"], list) or not data["source_refs"]:
        raise ItEsForeignAssetsError("Rule pack must include source_refs")
    _money(data["monitoring"]["bank_account_max_value_threshold"])
    exemption = data["monitoring"].get("domestic_intermediary_exemption")
    if not isinstance(exemption, dict) or not exemption.get("required_true_fields"):
        raise ItEsForeignAssetsError("Rule pack must define domestic intermediary exemption conditions")
    for tax_rule in data["wealth_taxes"].values():
        if tax_rule["method"] == "fixed":
            _money(tax_rule["fixed_amount"])
            _money(tax_rule["average_balance_threshold"])
        if tax_rule["method"] == "proportional":
            for field in ("rate", "ordinary_rate", "primary_residence_luxury_rate"):
                if field in tax_rule:
                    _rate(tax_rule[field])
            if "payment_threshold_before_share_period_and_credits" in tax_rule:
                _money(tax_rule["payment_threshold_before_share_period_and_credits"])
    if not isinstance(data["rules"], list) or not data["rules"]:
        raise ItEsForeignAssetsError("Rule pack must contain at least one rule")
    for rule in data["rules"]:
        for field in ("rule_id", "valid_from", "valid_to", "taxpayer_residence", "asset_jurisdiction", "supported_asset_types"):
            if field not in rule:
                raise ItEsForeignAssetsError(f"IT-ES foreign asset monitoring rule missing field: {field}")


def _find_rule_for_year(rule_pack: dict[str, Any], tax_year: int) -> dict[str, Any] | None:
    target = f"{tax_year:04d}"
    matches = []
    for rule in rule_pack["rules"]:
        valid_to = rule["valid_to"][:4] if rule["valid_to"] is not None else "9999"
        if rule["valid_from"][:4] <= target <= valid_to:
            matches.append(rule)
    if len(matches) > 1:
        raise ItEsForeignAssetsError(f"Multiple IT-ES foreign asset monitoring rules found for year {tax_year}")
    return matches[0] if matches else None


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ItEsForeignAssetsError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ItEsForeignAssetsError(f"Invalid JSON in {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise ItEsForeignAssetsError(f"{label} must contain a JSON object")
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
    except ItEsForeignAssetsError:
        errors.append(f"{label} must be a money value")
        return
    if parsed < Decimal("0.00"):
        errors.append(f"{label} must be greater than or equal to zero")


def _ratio_or_error(value: Any, label: str, errors: list[str]) -> None:
    try:
        parsed = _rate(value)
    except ItEsForeignAssetsError:
        errors.append(f"{label} must be a decimal rate")
        return
    if parsed < Decimal("0") or parsed > Decimal("1"):
        errors.append(f"{label} must be between 0 and 1")


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


def _year(value: str) -> int | None:
    try:
        return date.fromisoformat(value).year
    except ValueError:
        return None


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(CENT)
    except (InvalidOperation, TypeError) as exc:
        raise ItEsForeignAssetsError(f"Invalid money value: {value}") from exc


def _rate(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(RATIO)
    except (InvalidOperation, TypeError) as exc:
        raise ItEsForeignAssetsError(f"Invalid rate value: {value}") from exc


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ItEsForeignAssetsError(f"Cannot read rule pack for digest: {path}") from exc


def _content_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _semantic_core(core: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(core))
    result["source"]["path"] = "<input>"
    result["rule_pack"]["path"] = "<rule-pack>"
    return result
