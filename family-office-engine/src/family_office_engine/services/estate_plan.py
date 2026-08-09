import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "estate-plan/v2"
INPUT_RECORD_TYPE = "EstatePlanInput"
SNAPSHOT_RECORD_TYPE = "EstatePlanSnapshot"
RULE_PACK_SCHEMA_VERSION = "estate-rule-pack/v2"
CENT = Decimal("0.01")
RATIO_QUANT = Decimal("0.0001")


class EstatePlanError(ValueError):
    pass


def build_estate_plan(input_path: Path, rule_pack_path: Path, output_path: Path) -> dict[str, Any]:
    data = _read_json(input_path, "estate plan input")
    rule_pack = load_estate_plan_rule_pack(rule_pack_path)
    errors: list[str] = []
    data_gaps: list[dict[str, Any]] = []
    _validate_input(data, errors, data_gaps)
    if errors:
        raise EstatePlanError("; ".join(errors))

    base_currency = data["base_currency"]
    family_case = _family_case(data["family"])
    reserve_rule = _find_reserve_rule(rule_pack, family_case)
    if reserve_rule is None:
        data_gaps.append(
            {
                "code": "unsupported_forced_heir_case",
                "family_case": family_case,
                "message": "No forced-heir reserve rule is available for this family case.",
            }
        )
    assets = [_normalize_asset(item, index, base_currency, rule_pack, data_gaps) for index, item in enumerate(data["assets"])]
    donations = [_normalize_donation(item, index, base_currency, data_gaps) for index, item in enumerate(data.get("prior_donations", []))]
    policies = [_normalize_policy(item, index, base_currency, data_gaps) for index, item in enumerate(data.get("insurance_policies", []))]
    totals = _totals(assets, donations, policies)
    forced_heirs = _forced_heirs(data["family"], reserve_rule, totals["notional_mass"], data_gaps)
    tax_liquidity = _tax_liquidity(data.get("tax_liquidity"), base_currency, data_gaps)
    scenarios = [
        _scenario(item, index, assets, donations, forced_heirs, tax_liquidity, rule_pack, data_gaps)
        for index, item in enumerate(data.get("scenarios", []))
    ]
    if not scenarios:
        data_gaps.append({"code": "missing_estate_scenarios", "message": "At least one allocation scenario is required for estate-plan/v2."})
    summary = _summary(assets, donations, policies, scenarios, data_gaps, base_currency)
    status = "complete" if not data_gaps and all(scenario["status"] == "complete" for scenario in scenarios) else "partial"
    core = {
        "source": {"type": "estate-plan-input-json", "path": str(input_path)},
        "household": {
            "household_id": data["household_id"],
            "as_of_date": data["as_of_date"],
            "decedent_person_id": data["decedent_person_id"],
        },
        "base_currency": base_currency,
        "rule_pack": {
            "path": str(rule_pack_path),
            "rule_pack_id": rule_pack["rule_pack_id"],
            "schema_version": rule_pack["schema_version"],
            "verified_on": rule_pack.get("verified_on"),
            "source_refs": rule_pack.get("source_refs", []),
            "limitations": rule_pack.get("limitations", []),
        },
        "family_case": family_case,
        "estate_assets": assets,
        "insurance_policies": policies,
        "prior_donations": donations,
        "totals": {key: _format_money(value) for key, value in totals.items()},
        "forced_heirs": forced_heirs,
        "tax_liquidity": tax_liquidity,
        "scenarios": scenarios,
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
            "Estate plan V2 checks declared allocations, prior donations, liquidity and covered Italian "
            "forced-heir/tax rules. It is not legal, tax or notarial advice and does not calculate collation, "
            "reduction actions, cadastral bases, foreign succession law, trusts or recommendations."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise EstatePlanError(f"Cannot write estate plan snapshot: {output_path}") from exc
    return snapshot


def load_estate_plan_rule_pack(rule_pack_path: Path) -> dict[str, Any]:
    data = _read_json(rule_pack_path, "estate plan rule pack")
    required = ("schema_version", "rule_pack_id", "jurisdiction", "currency", "forced_heir_rules", "transfer_tax_rules")
    for field in required:
        if field not in data:
            raise EstatePlanError(f"Estate plan rule pack missing field: {field}")
    if data["schema_version"] != RULE_PACK_SCHEMA_VERSION:
        raise EstatePlanError(f"Unsupported estate plan rule pack schema: {data['schema_version']}")
    if data["jurisdiction"] != "IT":
        raise EstatePlanError("Estate plan V2 currently supports only IT rule packs")
    if not isinstance(data["forced_heir_rules"], list):
        raise EstatePlanError("Estate plan rule pack forced_heir_rules must be a list")
    if not isinstance(data["transfer_tax_rules"], list):
        raise EstatePlanError("Estate plan rule pack transfer_tax_rules must be a list")
    return data


def _validate_input(data: dict[str, Any], errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported estate plan schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported estate plan record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_string(data, "as_of_date", errors)
    _required_string(data, "decedent_person_id", errors)
    base_currency = _required_string(data, "base_currency", errors)
    if base_currency and (len(base_currency) != 3 or base_currency.upper() != base_currency):
        errors.append("base_currency must be an ISO-4217 uppercase code")
    if not isinstance(data.get("family"), dict):
        errors.append("family is required")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        errors.append("At least one estate asset is required")
    elif not all(isinstance(item, dict) for item in assets):
        errors.append("assets must contain objects")
    scenarios = data.get("scenarios", [])
    if scenarios not in (None, "") and (not isinstance(scenarios, list) or not all(isinstance(item, dict) for item in scenarios)):
        errors.append("scenarios must contain objects")
    _validate_declared_gaps(data.get("data_gaps", []), errors, data_gaps)


def _normalize_asset(item: dict[str, Any], index: int, base_currency: str, rule_pack: dict[str, Any], data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    prefix = f"assets[{index}]"
    asset_id = _required_item_text(item, "asset_id", prefix)
    currency = item.get("currency") or base_currency
    if currency != base_currency:
        data_gaps.append({"code": "foreign_currency_asset", "asset_id": asset_id, "currency": currency, "message": "No FX conversion is performed."})
    jurisdiction = item.get("jurisdiction") or rule_pack["jurisdiction"]
    if jurisdiction != rule_pack["jurisdiction"]:
        data_gaps.append({"code": "foreign_succession_review_required", "asset_id": asset_id, "jurisdiction": jurisdiction, "message": "Foreign asset succession treatment is not inferred."})
    gross_value = _non_negative_money(item.get("gross_value"), f"{prefix}.gross_value")
    ownership_share = _ratio_or_gap(item.get("ownership_share"), f"{prefix}.ownership_share", data_gaps, "missing_asset_ownership_share", asset_id)
    estate_value = None if ownership_share is None else (gross_value * ownership_share).quantize(CENT, rounding=ROUND_HALF_UP)
    asset_class = item.get("asset_class") or "other"
    liquidity_class = item.get("liquidity_class") or rule_pack.get("liquidity_classes", {}).get(asset_class, "unknown")
    provenance = item.get("provenance", [])
    if not isinstance(provenance, list) or not provenance:
        data_gaps.append({"code": "missing_asset_provenance", "asset_id": asset_id, "message": "Asset provenance is required."})
    return {
        "asset_id": asset_id,
        "label": item.get("label") or asset_id,
        "asset_class": asset_class,
        "jurisdiction": jurisdiction,
        "currency": currency,
        "gross_value": _format_money(gross_value),
        "ownership_share": _format_optional_ratio(ownership_share),
        "estate_value": _format_optional_money(estate_value),
        "liquidity_class": liquidity_class,
        "provenance": provenance,
    }


def _normalize_donation(item: dict[str, Any], index: int, base_currency: str, data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    prefix = f"prior_donations[{index}]"
    donation_id = _required_item_text(item, "donation_id", prefix)
    currency = item.get("currency") or base_currency
    if currency != base_currency:
        data_gaps.append({"code": "foreign_currency_donation", "donation_id": donation_id, "currency": currency, "message": "No FX conversion is performed for prior donations."})
    amount = _non_negative_money(item.get("amount"), f"{prefix}.amount")
    provenance = item.get("provenance", [])
    if not isinstance(provenance, list) or not provenance:
        data_gaps.append({"code": "missing_donation_provenance", "donation_id": donation_id, "message": "Prior donation provenance is required."})
    return {
        "donation_id": donation_id,
        "beneficiary_person_id": _required_item_text(item, "beneficiary_person_id", prefix),
        "relationship": item.get("relationship") or "unknown",
        "amount": _format_money(amount),
        "currency": currency,
        "include_in_notional_mass": bool(item.get("include_in_notional_mass", True)),
        "provenance": provenance,
    }


def _normalize_policy(item: dict[str, Any], index: int, base_currency: str, data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    prefix = f"insurance_policies[{index}]"
    policy_id = _required_item_text(item, "policy_id", prefix)
    currency = item.get("currency") or base_currency
    if currency != base_currency:
        data_gaps.append({"code": "foreign_currency_policy", "policy_id": policy_id, "currency": currency, "message": "No FX conversion is performed for insurance policies."})
    estate_treatment = item.get("estate_treatment") or "unknown"
    if estate_treatment == "unknown":
        data_gaps.append({"code": "unknown_insurance_estate_treatment", "policy_id": policy_id, "message": "Insurance succession and beneficiary treatment must be documented."})
    beneficiaries = _policy_beneficiaries(item.get("beneficiaries", []), policy_id, data_gaps)
    death_benefit = _optional_non_negative_money(item.get("death_benefit"), f"{prefix}.death_benefit")
    surrender_value = _optional_non_negative_money(item.get("surrender_value"), f"{prefix}.surrender_value")
    provenance = item.get("provenance", [])
    if not isinstance(provenance, list) or not provenance:
        data_gaps.append({"code": "missing_policy_provenance", "policy_id": policy_id, "message": "Insurance policy provenance is required."})
    return {
        "policy_id": policy_id,
        "policy_type": item.get("policy_type") or "unknown",
        "currency": currency,
        "estate_treatment": estate_treatment,
        "death_benefit": _format_optional_money(death_benefit),
        "surrender_value": _format_optional_money(surrender_value),
        "beneficiaries": beneficiaries,
        "provenance": provenance,
    }


def _policy_beneficiaries(value: Any, policy_id: str, data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if value in (None, ""):
        data_gaps.append({"code": "missing_policy_beneficiaries", "policy_id": policy_id, "message": "Policy beneficiaries must be explicit."})
        return []
    if not isinstance(value, list):
        raise EstatePlanError(f"{policy_id}.beneficiaries must be a list")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise EstatePlanError(f"{policy_id}.beneficiaries[{index}] must be an object")
        result.append(
            {
                "beneficiary_person_id": _required_item_text(item, "beneficiary_person_id", f"{policy_id}.beneficiaries[{index}]"),
                "relationship": item.get("relationship") or "unknown",
                "share": _format_ratio(_ratio(item.get("share"), f"{policy_id}.beneficiaries[{index}].share")),
            }
        )
    total = sum((_money(item["share"], "policy beneficiary share") for item in result), Decimal("0.00"))
    if total <= 0 or total > 1:
        raise EstatePlanError("Policy beneficiary shares must be greater than 0 and at most 1 in total")
    if total < 1:
        data_gaps.append({"code": "incomplete_policy_beneficiaries", "policy_id": policy_id, "message": "Known policy beneficiary shares total less than 100%."})
    return result


def _totals(assets: list[dict[str, Any]], donations: list[dict[str, Any]], policies: list[dict[str, Any]]) -> dict[str, Decimal]:
    known_estate = sum((_money(asset["estate_value"], "estate_value") for asset in assets if asset["estate_value"] is not None), Decimal("0.00"))
    illiquid = sum((_money(asset["estate_value"], "estate_value") for asset in assets if asset["estate_value"] is not None and asset["liquidity_class"] == "illiquid"), Decimal("0.00"))
    immediate = sum((_money(asset["estate_value"], "estate_value") for asset in assets if asset["estate_value"] is not None and asset["liquidity_class"] == "immediate"), Decimal("0.00"))
    notional_donations = sum((_money(item["amount"], "donation.amount") for item in donations if item["include_in_notional_mass"]), Decimal("0.00"))
    outside_insurance = sum((_money(policy["death_benefit"], "death_benefit") for policy in policies if policy["death_benefit"] is not None and policy["estate_treatment"] == "outside_estate"), Decimal("0.00"))
    return {
        "known_estate_mass": known_estate,
        "declared_notional_donations": notional_donations,
        "notional_mass": known_estate + notional_donations,
        "illiquid_estate_value": illiquid,
        "immediate_estate_liquidity": immediate,
        "outside_estate_insurance_benefits": outside_insurance,
    }


def _forced_heirs(family: dict[str, Any], rule: dict[str, Any] | None, notional_mass: Decimal, data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if rule is None:
        return []
    heirs: list[dict[str, Any]] = []
    if family.get("has_spouse"):
        spouse_share = _money(rule["spouse_reserved_share"], "spouse_reserved_share")
        if spouse_share > 0:
            heirs.append(_forced_heir("spouse", "spouse", spouse_share, notional_mass, rule))
    children = family.get("children", [])
    if not isinstance(children, list):
        data_gaps.append({"code": "invalid_children_list", "message": "family.children must be a list."})
        return heirs
    children_share = _money(rule["children_reserved_share"], "children_reserved_share")
    if children and children_share > 0:
        child_share = children_share / Decimal(len(children))
        for index, child in enumerate(children, start=1):
            person_id = child.get("person_id") if isinstance(child, dict) else None
            heirs.append(_forced_heir(person_id or f"child_{index}", "child", child_share, notional_mass, rule))
    return heirs


def _forced_heir(person_id: str, relationship: str, share: Decimal, notional_mass: Decimal, rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "beneficiary_person_id": person_id,
        "relationship": relationship,
        "reserved_share": _format_ratio(share),
        "reserved_amount": _format_money((notional_mass * share).quantize(CENT, rounding=ROUND_HALF_UP)),
        "rule_id": rule["rule_id"],
        "source_articles": rule.get("source_articles", []),
    }


def _tax_liquidity(value: Any, base_currency: str, data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(value, dict):
        data_gaps.append({"code": "missing_tax_liquidity", "message": "Immediate liquidity available for transfer taxes must be explicit."})
        return {"available_immediate_liquidity": None, "currency": base_currency, "provenance": []}
    currency = value.get("currency") or base_currency
    if currency != base_currency:
        data_gaps.append({"code": "foreign_currency_tax_liquidity", "currency": currency, "message": "No FX conversion is performed for tax liquidity."})
    amount = _optional_non_negative_money(value.get("available_immediate_liquidity"), "tax_liquidity.available_immediate_liquidity")
    provenance = value.get("provenance", [])
    if not isinstance(provenance, list) or not provenance:
        data_gaps.append({"code": "missing_tax_liquidity_provenance", "message": "Tax liquidity provenance is required."})
    return {"available_immediate_liquidity": _format_optional_money(amount), "currency": currency, "provenance": provenance}


def _scenario(
    item: dict[str, Any],
    index: int,
    assets: list[dict[str, Any]],
    donations: list[dict[str, Any]],
    forced_heirs: list[dict[str, Any]],
    tax_liquidity: dict[str, Any],
    rule_pack: dict[str, Any],
    data_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    prefix = f"scenarios[{index}]"
    scenario_id = _required_item_text(item, "scenario_id", prefix)
    allocation_results, scenario_gaps = _allocations(item.get("allocations", []), scenario_id, assets)
    totals_by_beneficiary: dict[str, dict[str, Any]] = {}
    for allocation in allocation_results:
        entry = totals_by_beneficiary.setdefault(
            allocation["beneficiary_person_id"],
            {"beneficiary_person_id": allocation["beneficiary_person_id"], "relationship": allocation["relationship"], "planned_estate_amount": Decimal("0.00"), "prior_donations": Decimal("0.00")},
        )
        entry["planned_estate_amount"] += _money(allocation["amount"], "allocation.amount")
    for donation in donations:
        entry = totals_by_beneficiary.setdefault(
            donation["beneficiary_person_id"],
            {"beneficiary_person_id": donation["beneficiary_person_id"], "relationship": donation["relationship"], "planned_estate_amount": Decimal("0.00"), "prior_donations": Decimal("0.00")},
        )
        entry["prior_donations"] += _money(donation["amount"], "donation.amount")
    conflicts = _reserve_conflicts(totals_by_beneficiary, forced_heirs)
    tax_estimates, tax_gaps = _tax_estimates(totals_by_beneficiary, rule_pack)
    scenario_gaps.extend(tax_gaps)
    total_tax = sum((_money(item["estimated_tax"], "estimated_tax") for item in tax_estimates), Decimal("0.00"))
    available_liquidity = _optional_money(tax_liquidity.get("available_immediate_liquidity"), "available_immediate_liquidity")
    if available_liquidity is None:
        scenario_gaps.append({"code": "missing_tax_liquidity", "scenario_id": scenario_id, "message": "Cannot check tax liquidity without declared immediate liquidity."})
    elif available_liquidity < total_tax:
        conflicts.append(
            {
                "code": "insufficient_tax_liquidity",
                "scenario_id": scenario_id,
                "required_liquidity": _format_money(total_tax),
                "available_liquidity": _format_money(available_liquidity),
                "message": "Declared immediate liquidity is below estimated transfer taxes.",
            }
        )
    beneficiary_results = [
        {
            "beneficiary_person_id": value["beneficiary_person_id"],
            "relationship": value["relationship"],
            "planned_estate_amount": _format_money(value["planned_estate_amount"]),
            "prior_donations": _format_money(value["prior_donations"]),
            "total_for_reserve_check": _format_money(value["planned_estate_amount"] + value["prior_donations"]),
        }
        for value in sorted(totals_by_beneficiary.values(), key=lambda item: item["beneficiary_person_id"])
    ]
    for gap in scenario_gaps:
        data_gaps.append(gap)
    return {
        "scenario_id": scenario_id,
        "label": item.get("label") or scenario_id,
        "status": "partial" if scenario_gaps else ("conflict" if conflicts else "complete"),
        "allocations": allocation_results,
        "beneficiaries": beneficiary_results,
        "reserve_conflicts": conflicts,
        "tax_estimates": tax_estimates,
        "estimated_transfer_taxes": _format_money(total_tax),
        "operational_flags": _operational_flags(allocation_results, conflicts, scenario_gaps),
        "gap_codes": [gap["code"] for gap in scenario_gaps],
    }


def _allocations(value: Any, scenario_id: str, assets: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(value, list) or not value:
        return [], [{"code": "missing_scenario_allocations", "scenario_id": scenario_id, "message": "Scenario allocations are required."}]
    by_asset = {asset["asset_id"]: asset for asset in assets}
    allocated_shares: dict[str, Decimal] = {}
    results = []
    gaps = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise EstatePlanError(f"{scenario_id}.allocations[{index}] must be an object")
        asset_id = _required_item_text(item, "asset_id", f"{scenario_id}.allocations[{index}]")
        asset = by_asset.get(asset_id)
        if asset is None:
            raise EstatePlanError(f"{scenario_id}.allocations[{index}].asset_id is unknown: {asset_id}")
        share = _ratio(item.get("share"), f"{scenario_id}.allocations[{index}].share")
        allocated_shares[asset_id] = allocated_shares.get(asset_id, Decimal("0.00")) + share
        estate_value = _optional_money(asset["estate_value"], f"{asset_id}.estate_value")
        amount = Decimal("0.00") if estate_value is None else (estate_value * share).quantize(CENT, rounding=ROUND_HALF_UP)
        if estate_value is None:
            gaps.append({"code": "allocation_asset_value_unknown", "scenario_id": scenario_id, "asset_id": asset_id, "message": "Cannot value allocation because asset estate value is unknown."})
        results.append(
            {
                "beneficiary_person_id": _required_item_text(item, "beneficiary_person_id", f"{scenario_id}.allocations[{index}]"),
                "relationship": item.get("relationship") or "unknown",
                "asset_id": asset_id,
                "share": _format_ratio(share),
                "amount": _format_money(amount),
                "liquidity_class": asset["liquidity_class"],
            }
        )
    for asset_id, asset in by_asset.items():
        total_share = allocated_shares.get(asset_id, Decimal("0.00"))
        if total_share == 0:
            gaps.append({"code": "asset_not_allocated", "scenario_id": scenario_id, "asset_id": asset_id, "message": "Asset is not allocated in this scenario."})
        elif total_share != 1:
            gaps.append({"code": "asset_allocation_share_not_full", "scenario_id": scenario_id, "asset_id": asset_id, "allocated_share": _format_ratio(total_share), "message": "Asset allocation shares must total 100%."})
    return results, gaps


def _reserve_conflicts(totals_by_beneficiary: dict[str, dict[str, Any]], forced_heirs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts = []
    for heir in forced_heirs:
        beneficiary_id = heir["beneficiary_person_id"]
        actual = Decimal("0.00")
        if beneficiary_id in totals_by_beneficiary:
            entry = totals_by_beneficiary[beneficiary_id]
            actual = entry["planned_estate_amount"] + entry["prior_donations"]
        reserved = _money(heir["reserved_amount"], "reserved_amount")
        if actual < reserved:
            conflicts.append(
                {
                    "code": "forced_heir_reserved_share_shortfall",
                    "beneficiary_person_id": beneficiary_id,
                    "relationship": heir["relationship"],
                    "reserved_amount": heir["reserved_amount"],
                    "allocated_plus_donations": _format_money(actual),
                    "shortfall": _format_money(reserved - actual),
                    "rule_id": heir["rule_id"],
                    "message": "Declared allocations and prior donations are below the covered forced-heir reserve.",
                }
            )
    return conflicts


def _tax_estimates(totals_by_beneficiary: dict[str, dict[str, Any]], rule_pack: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    estimates = []
    gaps = []
    for entry in totals_by_beneficiary.values():
        relationship = entry["relationship"]
        tax_rule = _find_tax_rule(rule_pack, relationship)
        if tax_rule is None:
            gaps.append({"code": "unsupported_tax_relationship", "beneficiary_person_id": entry["beneficiary_person_id"], "relationship": relationship, "message": "No transfer-tax rule is available for this relationship."})
            continue
        taxable_base = max(Decimal("0.00"), entry["planned_estate_amount"] + entry["prior_donations"] - _money(tax_rule["exemption_per_beneficiary"], "exemption"))
        tax = (taxable_base * _money(tax_rule["rate"], "rate")).quantize(CENT, rounding=ROUND_HALF_UP)
        estimates.append(
            {
                "beneficiary_person_id": entry["beneficiary_person_id"],
                "relationship": relationship,
                "rule_id": tax_rule["rule_id"],
                "gross_transfers": _format_money(entry["planned_estate_amount"] + entry["prior_donations"]),
                "exemption_applied": tax_rule["exemption_per_beneficiary"],
                "taxable_base": _format_money(taxable_base),
                "rate": tax_rule["rate"],
                "estimated_tax": _format_money(tax),
                "source_articles": tax_rule.get("source_articles", []),
            }
        )
    return estimates, gaps


def _operational_flags(allocations: list[dict[str, Any]], conflicts: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> list[dict[str, str]]:
    flags = []
    if any(item["liquidity_class"] == "illiquid" for item in allocations):
        flags.append({"code": "illiquid_asset_allocation_review", "message": "Illiquid assets may require equalization, liquidity or professional review."})
    if conflicts:
        flags.append({"code": "civil_law_conflict_review", "message": "Reserve shortfalls require professional legal review."})
    if any(gap["code"] in {"foreign_succession_review_required", "unsupported_tax_relationship"} for gap in gaps):
        flags.append({"code": "professional_cross_border_or_tax_review", "message": "Unsupported jurisdiction or tax relationship must be reviewed outside the deterministic engine."})
    flags.append({"code": "no_opaque_scheme", "message": "The engine reports conflicts and gaps only; it does not propose opaque structures or avoidance schemes."})
    return flags


def _summary(
    assets: list[dict[str, Any]],
    donations: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
    base_currency: str,
) -> dict[str, Any]:
    return {
        "asset_count": len(assets),
        "prior_donation_count": len(donations),
        "insurance_policy_count": len(policies),
        "scenario_count": len(scenarios),
        "conflict_count": sum(len(item["reserve_conflicts"]) for item in scenarios),
        "data_gap_count": len(data_gaps),
        "base_currency": base_currency,
        "review_required": True,
    }


def _family_case(family: dict[str, Any]) -> str:
    has_spouse = bool(family.get("has_spouse"))
    children = family.get("children", [])
    children_count = len(children) if isinstance(children, list) else 0
    if has_spouse and children_count == 0:
        return "spouse_only"
    if not has_spouse and children_count == 1:
        return "children_only_one"
    if not has_spouse and children_count > 1:
        return "children_only_multiple"
    if has_spouse and children_count == 1:
        return "spouse_one_child"
    if has_spouse and children_count > 1:
        return "spouse_multiple_children"
    return "unsupported_no_spouse_no_children"


def _find_reserve_rule(rule_pack: dict[str, Any], family_case: str) -> dict[str, Any] | None:
    for rule in rule_pack["forced_heir_rules"]:
        if rule.get("family_case") == family_case:
            return rule
    return None


def _find_tax_rule(rule_pack: dict[str, Any], relationship: str) -> dict[str, Any] | None:
    for rule in rule_pack["transfer_tax_rules"]:
        if relationship in rule.get("relationship_categories", []):
            return rule
    return None


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EstatePlanError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EstatePlanError(f"Invalid JSON in {label} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise EstatePlanError(f"{label} must contain a JSON object.")
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
        raise EstatePlanError(f"{prefix}.{field} is required")
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


def _ratio_or_gap(value: Any, label: str, data_gaps: list[dict[str, Any]], code: str, asset_id: str) -> Decimal | None:
    if value in (None, ""):
        data_gaps.append({"code": code, "asset_id": asset_id, "message": f"{label} is required."})
        return None
    return _ratio(value, label)


def _optional_non_negative_money(value: Any, label: str) -> Decimal | None:
    if value in (None, ""):
        return None
    return _non_negative_money(value, label)


def _non_negative_money(value: Any, label: str) -> Decimal:
    amount = _money(value, label)
    if amount < 0:
        raise EstatePlanError(f"{label} must be greater than or equal to 0")
    return amount


def _optional_money(value: Any, label: str) -> Decimal | None:
    if value in (None, ""):
        return None
    return _money(value, label)


def _money(value: Any, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise EstatePlanError(f"{label} must be a decimal") from exc


def _ratio(value: Any, label: str) -> Decimal:
    ratio = _money(value, label)
    if ratio <= 0 or ratio > 1:
        raise EstatePlanError(f"{label} must be greater than 0 and less than or equal to 1")
    return ratio


def _semantic_core(core: dict[str, Any]) -> dict[str, Any]:
    semantic = json.loads(json.dumps(core))
    source = semantic.get("source")
    if isinstance(source, dict):
        source.pop("path", None)
    rule_pack = semantic.get("rule_pack")
    if isinstance(rule_pack, dict):
        rule_pack.pop("path", None)
    return semantic


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _format_optional_money(value: Decimal | None) -> str | None:
    return None if value is None else _format_money(value)


def _format_ratio(value: Decimal) -> str:
    return str(value.quantize(RATIO_QUANT, rounding=ROUND_HALF_UP))


def _format_optional_ratio(value: Decimal | None) -> str | None:
    return None if value is None else _format_ratio(value)
