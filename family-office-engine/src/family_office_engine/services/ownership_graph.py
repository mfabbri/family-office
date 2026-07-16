import json
from datetime import date
from fractions import Fraction
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "ownership-beneficiary-graph/v1"
SNAPSHOT_RECORD_TYPE = "OwnershipBeneficiaryGraphSnapshot"
INPUT_RECORD_TYPE = "OwnershipBeneficiaryGraph"

ASSET_TYPES = {
    "financial_account",
    "pension_fund",
    "real_estate",
    "insurance_policy",
    "company_share",
    "cash",
    "other",
}
SUBJECT_TYPES = {"asset", "debt"}
OWNERSHIP_TYPES = {
    "full_ownership",
    "co_ownership",
    "bare_ownership",
    "usufruct",
    "debtor",
    "guarantor",
    "unknown",
}
OWNERSHIP_SUM_TYPES = {"full_ownership", "co_ownership"}
SEPARATE_RIGHT_TYPES = {"bare_ownership", "usufruct"}
BENEFICIARY_TYPES = {"primary", "contingent", "legal_heir", "other", "unknown"}


class OwnershipGraphError(ValueError):
    pass


def validate_ownership_graph(
    data: dict[str, Any],
    household_snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    errors: list[str] = []
    gaps: list[dict[str, Any]] = []

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported ownership graph schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported ownership graph record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_date(data, "as_of_date", errors)

    assets = _required_list(data, "assets", errors)
    debts = _required_list(data, "debts", errors)
    ownership_interests = _required_list(data, "ownership_interests", errors)
    beneficiaries = _required_list(data, "beneficiaries", errors)

    person_ids = _person_ids_from_household(household_snapshot, errors)
    asset_ids = _validate_assets(assets, errors)
    debt_ids = _validate_debts(debts, asset_ids, errors)
    _validate_ownership_interests(ownership_interests, asset_ids, debt_ids, person_ids, errors, gaps)
    _validate_beneficiaries(beneficiaries, asset_ids, debt_ids, person_ids, errors, gaps)
    _validate_declared_gaps(data.get("data_gaps", []), errors, gaps)

    if errors:
        raise OwnershipGraphError("; ".join(errors))
    return gaps


def import_ownership_graph(
    input_path: Path,
    output_path: Path,
    household_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    data = load_ownership_graph(input_path)
    household_snapshot = _load_optional_household_snapshot(household_snapshot_path)
    gaps = validate_ownership_graph(data, household_snapshot)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "complete" if not gaps else "partial",
        "source": {
            "type": "ownership-beneficiary-graph-json",
            "path": str(input_path),
        },
        "household": {
            "household_id": data["household_id"],
            "as_of_date": data["as_of_date"],
            "household_snapshot_path": str(household_snapshot_path) if household_snapshot_path else None,
        },
        "graph_context": data.get("graph_context", _default_graph_context()),
        "assets": data["assets"],
        "debts": data["debts"],
        "ownership_interests": data["ownership_interests"],
        "beneficiaries": data["beneficiaries"],
        "data_gaps": gaps,
        "notes": "Ownership and beneficiaries are explicit user-provided facts; missing links remain gaps.",
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise OwnershipGraphError(f"Cannot write ownership graph snapshot: {output_path}") from exc
    return snapshot


def load_ownership_graph(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OwnershipGraphError(f"Ownership graph file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OwnershipGraphError(f"Invalid JSON in ownership graph file: {exc}") from exc
    if not isinstance(data, dict):
        raise OwnershipGraphError("Ownership graph file must contain a JSON object")
    return data


def _load_optional_household_snapshot(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OwnershipGraphError(f"Invalid JSON in household snapshot: {exc}") from exc
    if not isinstance(data, dict):
        raise OwnershipGraphError("Household snapshot must contain a JSON object")
    return data


def _person_ids_from_household(household_snapshot: dict[str, Any] | None, errors: list[str]) -> set[str] | None:
    if household_snapshot is None:
        return None
    persons = household_snapshot.get("persons")
    if not isinstance(persons, list):
        errors.append("Household snapshot persons must be a list")
        return set()
    person_ids: set[str] = set()
    for index, person in enumerate(persons):
        if not isinstance(person, dict):
            errors.append(f"household.persons[{index}] must be an object")
            continue
        person_id = person.get("person_id")
        if isinstance(person_id, str) and person_id:
            person_ids.add(person_id)
    return person_ids


def _validate_assets(assets: list[Any], errors: list[str]) -> set[str]:
    asset_ids: set[str] = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            errors.append(f"assets[{index}] must be an object")
            continue
        asset_id = _required_string(asset, "asset_id", errors, f"assets[{index}]")
        if asset_id:
            if asset_id in asset_ids:
                errors.append(f"Duplicate asset_id: {asset_id}")
            asset_ids.add(asset_id)
        if asset.get("asset_type") not in ASSET_TYPES:
            errors.append(f"Invalid asset_type for assets[{index}]")
        _required_string(asset, "provenance", errors, f"assets[{index}]")
    return asset_ids


def _validate_debts(debts: list[Any], asset_ids: set[str], errors: list[str]) -> set[str]:
    debt_ids: set[str] = set()
    for index, debt in enumerate(debts):
        if not isinstance(debt, dict):
            errors.append(f"debts[{index}] must be an object")
            continue
        debt_id = _required_string(debt, "debt_id", errors, f"debts[{index}]")
        if debt_id:
            if debt_id in debt_ids:
                errors.append(f"Duplicate debt_id: {debt_id}")
            debt_ids.add(debt_id)
        linked_asset_id = debt.get("linked_asset_id")
        if linked_asset_id not in (None, "") and linked_asset_id not in asset_ids:
            errors.append(f"debts[{index}].linked_asset_id references unknown asset: {linked_asset_id}")
        _required_string(debt, "provenance", errors, f"debts[{index}]")
    return debt_ids


def _validate_ownership_interests(
    interests: list[Any],
    asset_ids: set[str],
    debt_ids: set[str],
    person_ids: set[str] | None,
    errors: list[str],
    gaps: list[dict[str, Any]],
) -> None:
    interest_ids: set[str] = set()
    asset_shares: dict[tuple[str, str], Fraction] = {}
    seen_assets: set[str] = set()
    for index, interest in enumerate(interests):
        if not isinstance(interest, dict):
            errors.append(f"ownership_interests[{index}] must be an object")
            continue
        interest_id = _required_string(interest, "ownership_id", errors, f"ownership_interests[{index}]")
        if interest_id:
            if interest_id in interest_ids:
                errors.append(f"Duplicate ownership_id: {interest_id}")
            interest_ids.add(interest_id)
        subject_type = interest.get("subject_type")
        subject_id = _required_string(interest, "subject_id", errors, f"ownership_interests[{index}]")
        if subject_type not in SUBJECT_TYPES:
            errors.append(f"Invalid subject_type for ownership_interests[{index}]")
        elif subject_id:
            _validate_subject_reference(subject_type, subject_id, asset_ids, debt_ids, errors, f"ownership_interests[{index}]")
            if subject_type == "asset" and subject_id in asset_ids:
                seen_assets.add(subject_id)
        owner_id = interest.get("owner_person_id")
        _validate_person_reference(owner_id, person_ids, errors, f"ownership_interests[{index}].owner_person_id")
        interest_type = interest.get("interest_type")
        if interest_type not in OWNERSHIP_TYPES:
            errors.append(f"Invalid interest_type for ownership_interests[{index}]")
        if interest_type == "unknown":
            gaps.append(_gap("unknown_ownership", subject_id, "Ownership is explicitly unknown."))
        elif not owner_id:
            errors.append(f"ownership_interests[{index}].owner_person_id is required unless interest_type is unknown")
        share = _optional_share(interest, f"ownership_interests[{index}]", errors)
        if subject_type == "asset" and subject_id and interest_type in OWNERSHIP_SUM_TYPES | SEPARATE_RIGHT_TYPES:
            if share is None:
                gaps.append(_gap("missing_ownership_share", subject_id, "Ownership share is missing."))
            else:
                share_group = "economic_ownership" if interest_type in OWNERSHIP_SUM_TYPES else interest_type
                asset_shares[(subject_id, share_group)] = asset_shares.get((subject_id, share_group), Fraction(0)) + share
        _validate_period(interest, f"ownership_interests[{index}]", errors)
        _required_string(interest, "provenance", errors, f"ownership_interests[{index}]")
    for (asset_id, share_group), total in sorted(asset_shares.items()):
        if total > 1:
            errors.append(f"Ownership shares for {asset_id}/{share_group} exceed 100%")
        elif total < 1:
            gaps.append(_gap("incomplete_ownership_share", asset_id, f"Known {share_group} shares total less than 100%."))
    for asset_id in sorted(asset_ids - seen_assets):
        gaps.append(_gap("missing_asset_ownership", asset_id, "Asset has no ownership interest."))


def _validate_beneficiaries(
    beneficiaries: list[Any],
    asset_ids: set[str],
    debt_ids: set[str],
    person_ids: set[str] | None,
    errors: list[str],
    gaps: list[dict[str, Any]],
) -> None:
    beneficiary_ids: set[str] = set()
    shares: dict[str, Fraction] = {}
    for index, beneficiary in enumerate(beneficiaries):
        if not isinstance(beneficiary, dict):
            errors.append(f"beneficiaries[{index}] must be an object")
            continue
        beneficiary_id = _required_string(beneficiary, "beneficiary_id", errors, f"beneficiaries[{index}]")
        if beneficiary_id:
            if beneficiary_id in beneficiary_ids:
                errors.append(f"Duplicate beneficiary_id: {beneficiary_id}")
            beneficiary_ids.add(beneficiary_id)
        subject_type = beneficiary.get("subject_type")
        subject_id = _required_string(beneficiary, "subject_id", errors, f"beneficiaries[{index}]")
        if subject_type not in SUBJECT_TYPES:
            errors.append(f"Invalid subject_type for beneficiaries[{index}]")
        elif subject_id:
            _validate_subject_reference(subject_type, subject_id, asset_ids, debt_ids, errors, f"beneficiaries[{index}]")
        beneficiary_person_id = beneficiary.get("beneficiary_person_id")
        if beneficiary_person_id in (None, "") and not beneficiary.get("beneficiary_label"):
            gaps.append(_gap("unknown_beneficiary", subject_id, "Beneficiary person or label is missing."))
        _validate_person_reference(beneficiary_person_id, person_ids, errors, f"beneficiaries[{index}].beneficiary_person_id")
        if beneficiary.get("beneficiary_type") not in BENEFICIARY_TYPES:
            errors.append(f"Invalid beneficiary_type for beneficiaries[{index}]")
        share = _optional_share(beneficiary, f"beneficiaries[{index}]", errors)
        if subject_id and share is not None:
            shares[subject_id] = shares.get(subject_id, Fraction(0)) + share
        _validate_period(beneficiary, f"beneficiaries[{index}]", errors)
        _required_string(beneficiary, "provenance", errors, f"beneficiaries[{index}]")
    for subject_id, total in sorted(shares.items()):
        if total > 1:
            errors.append(f"Beneficiary shares for {subject_id} exceed 100%")


def _validate_subject_reference(
    subject_type: str,
    subject_id: str,
    asset_ids: set[str],
    debt_ids: set[str],
    errors: list[str],
    label: str,
) -> None:
    if subject_type == "asset" and subject_id not in asset_ids:
        errors.append(f"{label}.subject_id references unknown asset: {subject_id}")
    if subject_type == "debt" and subject_id not in debt_ids:
        errors.append(f"{label}.subject_id references unknown debt: {subject_id}")


def _validate_person_reference(
    person_id: Any,
    person_ids: set[str] | None,
    errors: list[str],
    label: str,
) -> None:
    if person_id in (None, "") or person_ids is None:
        return
    if person_id not in person_ids:
        errors.append(f"{label} references unknown person: {person_id}")


def _optional_share(item: dict[str, Any], label: str, errors: list[str]) -> Fraction | None:
    numerator = item.get("share_numerator")
    denominator = item.get("share_denominator")
    if numerator in (None, "") and denominator in (None, ""):
        return None
    if not isinstance(numerator, int) or not isinstance(denominator, int):
        errors.append(f"{label}.share_numerator and share_denominator must be integers")
        return None
    if numerator <= 0 or denominator <= 0 or numerator > denominator:
        errors.append(f"{label}.share must be greater than 0 and less than or equal to 1")
        return None
    return Fraction(numerator, denominator)


def _validate_declared_gaps(raw_gaps: Any, errors: list[str], gaps: list[dict[str, Any]]) -> None:
    if raw_gaps in (None, ""):
        return
    if not isinstance(raw_gaps, list):
        errors.append("data_gaps must be a list")
        return
    for index, gap in enumerate(raw_gaps):
        if not isinstance(gap, dict):
            errors.append(f"data_gaps[{index}] must be an object")
            continue
        if not gap.get("code"):
            errors.append(f"data_gaps[{index}].code is required")
            continue
        gaps.append(gap)


def _validate_period(item: dict[str, Any], label: str, errors: list[str]) -> None:
    valid_from = item.get("valid_from")
    valid_to = item.get("valid_to")
    from_date = None
    to_date = None
    if valid_from not in (None, ""):
        from_date = _parse_date(valid_from, f"{label}.valid_from", errors)
    if valid_to not in (None, ""):
        to_date = _parse_date(valid_to, f"{label}.valid_to", errors)
    if from_date is not None and to_date is not None and to_date < from_date:
        errors.append(f"{label}.valid_to must be greater than or equal to valid_from")


def _required_list(data: dict[str, Any], field: str, errors: list[str]) -> list[Any]:
    value = data.get(field)
    if not isinstance(value, list):
        errors.append(f"{field} must be a list")
        return []
    return value


def _required_string(
    data: dict[str, Any],
    field: str,
    errors: list[str],
    prefix: str | None = None,
) -> str | None:
    label = field if prefix is None else f"{prefix}.{field}"
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} is required")
        return None
    return value


def _required_date(
    data: dict[str, Any],
    field: str,
    errors: list[str],
    prefix: str | None = None,
) -> date | None:
    label = field if prefix is None else f"{prefix}.{field}"
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} is required")
        return None
    return _parse_date(value, label, errors)


def _parse_date(value: Any, label: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{label} must be an ISO date string")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label} must be a valid ISO date")
        return None


def _default_graph_context() -> dict[str, str]:
    return {
        "@vocab": "https://family-office.local/ontology/ownership#",
        "person": "household-facts/v1#person",
        "asset": "ownership-beneficiary-graph/v1#asset",
        "debt": "ownership-beneficiary-graph/v1#debt",
    }


def _gap(code: str, subject_id: str | None, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "subject_id": subject_id,
        "message": message,
    }
