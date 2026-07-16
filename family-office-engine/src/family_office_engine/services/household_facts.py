import json
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "household-facts/v1"
SNAPSHOT_RECORD_TYPE = "HouseholdFactsSnapshot"
INPUT_RECORD_TYPE = "HouseholdFacts"

PERSON_ROLES = {"self", "spouse", "child", "dependent", "other"}
RELATIONSHIP_TYPES = {"spouse", "parent", "child", "dependent", "other"}
ECONOMIC_ROLES = {
    "primary_earner",
    "secondary_earner",
    "dependent",
    "retired",
    "student",
    "asset_owner",
    "beneficiary",
    "other",
}
DATE_TYPES = {
    "birth",
    "target_retirement",
    "public_pension_eligibility",
    "residence_start",
    "tax_regime_end",
    "dependency_end",
    "other",
}


class HouseholdFactsError(ValueError):
    pass


def validate_household_facts(data: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[str] = []
    gaps: list[dict[str, Any]] = []

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported household facts schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported household facts record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_date(data, "as_of_date", errors)

    persons = _required_list(data, "persons", errors)
    relationships = _required_list(data, "relationships", errors)
    tax_residences = _required_list(data, "tax_residences", errors)
    economic_roles = _required_list(data, "economic_roles", errors)
    relevant_dates = _required_list(data, "relevant_dates", errors)

    person_ids = _validate_persons(persons, errors, gaps)
    _validate_relationships(relationships, person_ids, errors)
    _validate_tax_residences(tax_residences, person_ids, errors, gaps)
    _validate_economic_roles(economic_roles, person_ids, errors)
    _validate_relevant_dates(relevant_dates, person_ids, errors)
    _validate_declared_gaps(data.get("data_gaps", []), errors, gaps)

    if errors:
        raise HouseholdFactsError("; ".join(errors))
    return gaps


def import_household_facts(input_path: Path, output_path: Path) -> dict[str, Any]:
    data = load_household_facts(input_path)
    gaps = validate_household_facts(data)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "complete" if not gaps else "partial",
        "source": {
            "type": "household-facts-json",
            "path": str(input_path),
        },
        "household": {
            "household_id": data["household_id"],
            "as_of_date": data["as_of_date"],
        },
        "persons": data["persons"],
        "relationships": data["relationships"],
        "tax_residences": data["tax_residences"],
        "economic_roles": data["economic_roles"],
        "relevant_dates": data["relevant_dates"],
        "data_gaps": gaps,
        "notes": "Household facts are user-provided facts; missing facts remain gaps and are not inferred.",
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise HouseholdFactsError(f"Cannot write household facts snapshot: {output_path}") from exc
    return snapshot


def load_household_facts(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HouseholdFactsError(f"Household facts file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise HouseholdFactsError(f"Invalid JSON in household facts file: {exc}") from exc
    if not isinstance(data, dict):
        raise HouseholdFactsError("Household facts file must contain a JSON object")
    return data


def _validate_persons(
    persons: list[Any],
    errors: list[str],
    gaps: list[dict[str, Any]],
) -> set[str]:
    person_ids: set[str] = set()
    self_count = 0
    for index, person in enumerate(persons):
        if not isinstance(person, dict):
            errors.append(f"persons[{index}] must be an object")
            continue
        person_id = _required_string(person, "person_id", errors, f"persons[{index}]")
        role = person.get("role")
        if role not in PERSON_ROLES:
            errors.append(f"Invalid role for persons[{index}].role")
        if role == "self":
            self_count += 1
        if person_id:
            if person_id in person_ids:
                errors.append(f"Duplicate person_id: {person_id}")
            person_ids.add(person_id)
        birth_date = person.get("birth_date")
        birth_year = person.get("birth_year")
        if birth_date not in (None, ""):
            _parse_date(birth_date, f"persons[{index}].birth_date", errors)
        if birth_year is not None and (not isinstance(birth_year, int) or birth_year < 1900 or birth_year > 2100):
            errors.append(f"Invalid birth_year for persons[{index}]")
        if birth_date in (None, "") and birth_year is None:
            gaps.append(
                {
                    "code": "missing_birth_date_or_year",
                    "person_id": person_id,
                    "message": "Person has neither birth_date nor birth_year.",
                }
            )
    if self_count != 1:
        errors.append("Exactly one person with role self is required")
    return person_ids


def _validate_relationships(relationships: list[Any], person_ids: set[str], errors: list[str]) -> None:
    relationship_ids: set[str] = set()
    for index, relationship in enumerate(relationships):
        if not isinstance(relationship, dict):
            errors.append(f"relationships[{index}] must be an object")
            continue
        relationship_id = _required_string(relationship, "relationship_id", errors, f"relationships[{index}]")
        if relationship_id:
            if relationship_id in relationship_ids:
                errors.append(f"Duplicate relationship_id: {relationship_id}")
            relationship_ids.add(relationship_id)
        from_id = _required_string(relationship, "from_person_id", errors, f"relationships[{index}]")
        to_id = _required_string(relationship, "to_person_id", errors, f"relationships[{index}]")
        if from_id and from_id not in person_ids:
            errors.append(f"relationships[{index}].from_person_id references unknown person: {from_id}")
        if to_id and to_id not in person_ids:
            errors.append(f"relationships[{index}].to_person_id references unknown person: {to_id}")
        if from_id and to_id and from_id == to_id:
            errors.append(f"relationships[{index}] cannot point to the same person")
        if relationship.get("relationship_type") not in RELATIONSHIP_TYPES:
            errors.append(f"Invalid relationship_type for relationships[{index}]")
        _validate_period(relationship, f"relationships[{index}]", errors)


def _validate_tax_residences(
    tax_residences: list[Any],
    person_ids: set[str],
    errors: list[str],
    gaps: list[dict[str, Any]],
) -> None:
    covered_person_ids: set[str] = set()
    for index, residence in enumerate(tax_residences):
        if not isinstance(residence, dict):
            errors.append(f"tax_residences[{index}] must be an object")
            continue
        person_id = _required_string(residence, "person_id", errors, f"tax_residences[{index}]")
        if person_id:
            if person_id not in person_ids:
                errors.append(f"tax_residences[{index}].person_id references unknown person: {person_id}")
            covered_person_ids.add(person_id)
        country = _required_string(residence, "country", errors, f"tax_residences[{index}]")
        if country and len(country) != 2:
            errors.append(f"tax_residences[{index}].country must be an ISO-3166 alpha-2 code")
        _validate_period(residence, f"tax_residences[{index}]", errors)
    for person_id in sorted(person_ids - covered_person_ids):
        gaps.append(
            {
                "code": "missing_tax_residence",
                "person_id": person_id,
                "message": "No tax residence period declared for this person.",
            }
        )


def _validate_economic_roles(economic_roles: list[Any], person_ids: set[str], errors: list[str]) -> None:
    for index, role in enumerate(economic_roles):
        if not isinstance(role, dict):
            errors.append(f"economic_roles[{index}] must be an object")
            continue
        person_id = _required_string(role, "person_id", errors, f"economic_roles[{index}]")
        if person_id and person_id not in person_ids:
            errors.append(f"economic_roles[{index}].person_id references unknown person: {person_id}")
        if role.get("role") not in ECONOMIC_ROLES:
            errors.append(f"Invalid role for economic_roles[{index}]")
        _validate_period(role, f"economic_roles[{index}]", errors)


def _validate_relevant_dates(relevant_dates: list[Any], person_ids: set[str], errors: list[str]) -> None:
    date_ids: set[str] = set()
    for index, relevant_date in enumerate(relevant_dates):
        if not isinstance(relevant_date, dict):
            errors.append(f"relevant_dates[{index}] must be an object")
            continue
        date_id = _required_string(relevant_date, "date_id", errors, f"relevant_dates[{index}]")
        if date_id:
            if date_id in date_ids:
                errors.append(f"Duplicate date_id: {date_id}")
            date_ids.add(date_id)
        person_id = relevant_date.get("person_id")
        if person_id not in (None, "") and person_id not in person_ids:
            errors.append(f"relevant_dates[{index}].person_id references unknown person: {person_id}")
        if relevant_date.get("date_type") not in DATE_TYPES:
            errors.append(f"Invalid date_type for relevant_dates[{index}]")
        _required_date(relevant_date, "date", errors, f"relevant_dates[{index}]")


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
