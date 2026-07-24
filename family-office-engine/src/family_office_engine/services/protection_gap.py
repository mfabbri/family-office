import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "protection-gap/v1"
INPUT_RECORD_TYPE = "ProtectionGapInput"
SNAPSHOT_RECORD_TYPE = "ProtectionGapSnapshot"
CENT = Decimal("0.01")
RATIO_QUANT = Decimal("0.0001")
PROTECTION_POLICY_TYPES = {"risk_life", "disability", "mixed"}
SUPPORTED_POLICY_TYPES = PROTECTION_POLICY_TYPES | {"investment"}


class ProtectionGapError(ValueError):
    pass


def build_protection_gap(input_path: Path, output_path: Path) -> dict[str, Any]:
    data = _read_json(input_path, "protection gap input")
    errors: list[str] = []
    data_gaps: list[dict[str, Any]] = []
    _validate_input(data, errors, data_gaps)
    if errors:
        raise ProtectionGapError("; ".join(errors))

    base_currency = data["base_currency"]
    needs = [_normalize_need(item, index, base_currency, data_gaps) for index, item in enumerate(data["family_needs"])]
    policies = [_normalize_policy(item, index, base_currency, data_gaps) for index, item in enumerate(data["policies"])]
    protection_gaps = _build_protection_gaps(needs, policies)
    summary = _summary(needs, policies, protection_gaps, data_gaps, base_currency)
    status = "complete" if not data_gaps else "partial"
    core = {
        "source": {"type": "protection-gap-input-json", "path": str(input_path)},
        "household": {"household_id": data["household_id"], "as_of_date": data["as_of_date"]},
        "base_currency": base_currency,
        "family_needs": needs,
        "policies": policies,
        "protection_gaps": protection_gaps,
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
            "Protection gap V1 compares explicit family needs and insurance policies. It separates risk "
            "coverage from investment surrender value and does not calculate legal, tax, actuarial, health, "
            "underwriting or insurance recommendations."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ProtectionGapError(f"Cannot write protection gap snapshot: {output_path}") from exc
    return snapshot


def _validate_input(data: dict[str, Any], errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported protection gap schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported protection gap record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_string(data, "as_of_date", errors)
    base_currency = _required_string(data, "base_currency", errors)
    if base_currency and (len(base_currency) != 3 or base_currency.upper() != base_currency):
        errors.append("base_currency must be an ISO-4217 uppercase code")
    needs = data.get("family_needs")
    if not isinstance(needs, list) or not needs:
        errors.append("At least one family need is required")
    elif not all(isinstance(item, dict) for item in needs):
        errors.append("family_needs must contain objects")
    policies = data.get("policies")
    if not isinstance(policies, list) or not policies:
        errors.append("At least one insurance policy is required")
    elif not all(isinstance(item, dict) for item in policies):
        errors.append("policies must contain objects")
    _validate_declared_gaps(data.get("data_gaps", []), errors, data_gaps)


def _normalize_need(item: dict[str, Any], index: int, base_currency: str, data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    prefix = f"family_needs[{index}]"
    need_id = _required_item_text(item, "need_id", prefix)
    event_type = _required_item_text(item, "event_type", prefix)
    currency = item.get("currency") or base_currency
    if currency != base_currency:
        data_gaps.append(
            {
                "code": "foreign_currency_family_need",
                "need_id": need_id,
                "currency": currency,
                "message": "Family need currency differs from base currency; no FX conversion is performed.",
            }
        )
    required_capital = _money(item.get("required_capital"), f"{prefix}.required_capital")
    if required_capital < 0:
        raise ProtectionGapError(f"{prefix}.required_capital must be greater than or equal to 0")
    provenance = item.get("provenance", [])
    if not isinstance(provenance, list) or not provenance:
        data_gaps.append({"code": "missing_family_need_provenance", "need_id": need_id, "message": "Family need provenance is required."})
    return {
        "need_id": need_id,
        "label": item.get("label") or need_id,
        "event_type": event_type,
        "currency": currency,
        "required_capital": _format_money(required_capital),
        "covered_person_ids": _string_list(item.get("covered_person_ids", []), f"{prefix}.covered_person_ids"),
        "provenance": provenance,
    }


def _normalize_policy(item: dict[str, Any], index: int, base_currency: str, data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    prefix = f"policies[{index}]"
    policy_id = _required_item_text(item, "policy_id", prefix)
    policy_type = _required_item_text(item, "policy_type", prefix)
    if policy_type not in SUPPORTED_POLICY_TYPES:
        raise ProtectionGapError(f"{prefix}.policy_type must be one of {sorted(SUPPORTED_POLICY_TYPES)}")
    currency = item.get("currency") or base_currency
    if currency != base_currency:
        data_gaps.append(
            {
                "code": "foreign_currency_policy",
                "policy_id": policy_id,
                "currency": currency,
                "message": "Policy currency differs from base currency; no FX conversion is performed.",
            }
        )
    beneficiaries = _beneficiaries(item.get("beneficiaries", []), policy_id, policy_type, data_gaps)
    coverage_events = _coverage_events(item.get("coverage_events", []), policy_id, policy_type)
    annual_premium = _optional_non_negative_money(item.get("annual_premium"), f"{prefix}.annual_premium")
    surrender_value = _optional_non_negative_money(item.get("surrender_value"), f"{prefix}.surrender_value")
    provenance = item.get("provenance", [])
    if not isinstance(provenance, list) or not provenance:
        data_gaps.append({"code": "missing_policy_provenance", "policy_id": policy_id, "message": "Policy provenance is required."})
    if policy_type in PROTECTION_POLICY_TYPES and not coverage_events:
        data_gaps.append({"code": "missing_policy_coverage", "policy_id": policy_id, "message": "Protection policies require explicit covered events and insured capital."})
    if policy_type == "investment" and coverage_events:
        data_gaps.append({"code": "investment_policy_coverage_not_counted", "policy_id": policy_id, "message": "Investment policy coverage events are not counted as risk protection."})
    return {
        "policy_id": policy_id,
        "label": item.get("label") or policy_id,
        "policy_type": policy_type,
        "policyholder_person_id": item.get("policyholder_person_id"),
        "insured_person_ids": _string_list(item.get("insured_person_ids", []), f"{prefix}.insured_person_ids"),
        "currency": currency,
        "annual_premium": _format_optional_money(annual_premium),
        "surrender_value": _format_optional_money(surrender_value),
        "beneficiaries": beneficiaries,
        "coverage_events": coverage_events,
        "provenance": provenance,
    }


def _beneficiaries(value: Any, policy_id: str, policy_type: str, data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if value in (None, ""):
        value = []
    if not isinstance(value, list):
        raise ProtectionGapError(f"{policy_id}.beneficiaries must be a list")
    if policy_type in PROTECTION_POLICY_TYPES and not value:
        data_gaps.append({"code": "missing_policy_beneficiary", "policy_id": policy_id, "message": "Protection policy beneficiaries must be explicit."})
        return []
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ProtectionGapError(f"{policy_id}.beneficiaries[{index}] must be an object")
        share = _ratio(item.get("share"), f"{policy_id}.beneficiaries[{index}].share")
        result.append(
            {
                "beneficiary_person_id": item.get("beneficiary_person_id"),
                "relationship": item.get("relationship"),
                "share": _format_ratio(share),
                "provenance": item.get("provenance"),
            }
        )
    total = sum((_money(item["share"], "beneficiary.share") for item in result), Decimal("0.00"))
    if total <= 0 or total > 1:
        raise ProtectionGapError("Policy beneficiary shares must be greater than 0 and at most 1 in total")
    if total < 1 and policy_type in PROTECTION_POLICY_TYPES:
        data_gaps.append({"code": "incomplete_policy_beneficiaries", "policy_id": policy_id, "message": "Known beneficiary shares total less than 100%."})
    return result


def _coverage_events(value: Any, policy_id: str, policy_type: str) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ProtectionGapError(f"{policy_id}.coverage_events must be a list")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ProtectionGapError(f"{policy_id}.coverage_events[{index}] must be an object")
        insured_capital = _money(item.get("insured_capital"), f"{policy_id}.coverage_events[{index}].insured_capital")
        if insured_capital < 0:
            raise ProtectionGapError(f"{policy_id}.coverage_events[{index}].insured_capital must be greater than or equal to 0")
        counted_as_protection = policy_type in PROTECTION_POLICY_TYPES
        result.append(
            {
                "event_type": _required_item_text(item, "event_type", f"{policy_id}.coverage_events[{index}]"),
                "insured_capital": _format_money(insured_capital),
                "counted_as_protection": counted_as_protection,
                "provenance": item.get("provenance"),
            }
        )
    return result


def _build_protection_gaps(needs: list[dict[str, Any]], policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for need in needs:
        matching_events = []
        total_coverage = Decimal("0.00")
        for policy in policies:
            for event in policy["coverage_events"]:
                if event["event_type"] == need["event_type"] and event["counted_as_protection"]:
                    amount = _money(event["insured_capital"], "insured_capital")
                    total_coverage += amount
                    matching_events.append(
                        {
                            "policy_id": policy["policy_id"],
                            "event_type": event["event_type"],
                            "insured_capital": event["insured_capital"],
                        }
                    )
        required = _money(need["required_capital"], "required_capital")
        shortfall = max(Decimal("0.00"), required - total_coverage)
        surplus = max(Decimal("0.00"), total_coverage - required)
        status = "covered" if shortfall == 0 else "shortfall"
        results.append(
            {
                "need_id": need["need_id"],
                "event_type": need["event_type"],
                "status": status,
                "required_capital": need["required_capital"],
                "protection_coverage": _format_money(total_coverage),
                "shortfall": _format_money(shortfall),
                "surplus": _format_money(surplus),
                "matching_policy_events": matching_events,
            }
        )
    return results


def _summary(
    needs: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    protection_gaps: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
    base_currency: str,
) -> dict[str, Any]:
    annual_premiums = sum(
        (_money(policy["annual_premium"], "annual_premium") for policy in policies if policy["annual_premium"] is not None),
        Decimal("0.00"),
    )
    surrender_values = sum(
        (_money(policy["surrender_value"], "surrender_value") for policy in policies if policy["surrender_value"] is not None),
        Decimal("0.00"),
    )
    total_required = sum((_money(need["required_capital"], "required_capital") for need in needs), Decimal("0.00"))
    total_coverage = sum((_money(gap["protection_coverage"], "protection_coverage") for gap in protection_gaps), Decimal("0.00"))
    total_shortfall = sum((_money(gap["shortfall"], "shortfall") for gap in protection_gaps), Decimal("0.00"))
    return {
        "need_count": len(needs),
        "policy_count": len(policies),
        "protection_policy_count": len([policy for policy in policies if policy["policy_type"] in PROTECTION_POLICY_TYPES]),
        "investment_policy_count": len([policy for policy in policies if policy["policy_type"] == "investment"]),
        "total_required_capital": _format_money(total_required),
        "total_protection_coverage": _format_money(total_coverage),
        "total_shortfall": _format_money(total_shortfall),
        "annual_premiums": _format_money(annual_premiums),
        "investment_surrender_value": _format_money(surrender_values),
        "data_gap_count": len(data_gaps),
        "base_currency": base_currency,
        "review_required": True,
    }


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProtectionGapError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProtectionGapError(f"Invalid JSON in {label} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProtectionGapError(f"{label} must contain a JSON object.")
    return data


def _required_string(data: dict[str, Any], field: str, errors: list[str]) -> str | None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required")
        return None
    return value


def _required_item_text(data: dict[str, Any], field: str, prefix: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ProtectionGapError(f"{prefix}.{field} is required")
    return value


def _validate_declared_gaps(raw_gaps: Any, errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if raw_gaps in (None, ""):
        return
    if not isinstance(raw_gaps, list):
        errors.append("data_gaps must be a list")
        return
    for index, gap in enumerate(raw_gaps):
        if not isinstance(gap, dict):
            errors.append(f"data_gaps[{index}] must be an object")
        elif not gap.get("code"):
            errors.append(f"data_gaps[{index}].code is required")
        else:
            data_gaps.append(gap)


def _string_list(value: Any, label: str) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ProtectionGapError(f"{label} must be a list of strings")
    return value


def _optional_non_negative_money(value: Any, label: str) -> Decimal | None:
    if value in (None, ""):
        return None
    amount = _money(value, label)
    if amount < 0:
        raise ProtectionGapError(f"{label} must be greater than or equal to 0")
    return amount


def _money(value: Any, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ProtectionGapError(f"{label} must be a decimal") from exc


def _ratio(value: Any, label: str) -> Decimal:
    ratio = _money(value, label)
    if ratio <= 0 or ratio > 1:
        raise ProtectionGapError(f"{label} must be greater than 0 and less than or equal to 1")
    return ratio


def _semantic_core(core: dict[str, Any]) -> dict[str, Any]:
    semantic = json.loads(json.dumps(core))
    source = semantic.get("source")
    if isinstance(source, dict):
        source.pop("path", None)
    return semantic


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _format_optional_money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _format_money(value)


def _format_ratio(value: Decimal) -> str:
    return str(value.quantize(RATIO_QUANT, rounding=ROUND_HALF_UP))
