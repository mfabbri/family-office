import json
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "timeline-events/v1"
SNAPSHOT_RECORD_TYPE = "TimelineEventsSnapshot"
INPUT_RECORD_TYPE = "TimelineEvents"
POLICY_SCHEMA_VERSION = "timeline-overlap-policy/v1"

EVENT_TYPES = {
    "retirement",
    "tax_regime_end",
    "deadline",
    "contribution",
    "extraordinary_expense",
    "succession",
    "residence_change",
    "asset_availability",
    "other",
}
TIMING_TYPES = {"point", "period", "recurring"}
RECURRENCE_FREQUENCIES = {"monthly", "annual"}
DEFAULT_MAX_OCCURRENCES = 120

DEFAULT_POLICY = {
    "schema_version": POLICY_SCHEMA_VERSION,
    "policy_id": "timeline.default-overlap-policy.v1",
    "event_type_priorities": {
        "deadline": 10,
        "tax_regime_end": 20,
        "retirement": 30,
        "residence_change": 40,
        "asset_availability": 50,
        "contribution": 60,
        "extraordinary_expense": 70,
        "succession": 80,
        "other": 90,
    },
    "exclusive_event_types": [
        "retirement",
        "tax_regime_end",
    ],
    "exclusive_period_event_types": [
        "residence_change",
    ],
}


class TimelineEventsError(ValueError):
    pass


def validate_timeline_events(
    data: dict[str, Any],
    household_snapshot: dict[str, Any] | None = None,
    asset_availability_snapshot: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[str] = []
    gaps: list[dict[str, Any]] = []
    resolved_policy = _validate_policy(policy or DEFAULT_POLICY, errors)

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported timeline events schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported timeline events record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_date(data, "as_of_date", errors)

    events = _required_list(data, "events", errors)
    person_ids = _person_ids_from_household(household_snapshot, errors)
    asset_ids = _asset_ids_from_availability(asset_availability_snapshot, errors)
    normalized_events = _validate_events(events, person_ids, asset_ids, resolved_policy, errors, gaps)
    _validate_declared_gaps(data.get("data_gaps", []), errors, gaps)
    _validate_conflicts(normalized_events, resolved_policy, errors)

    occurrences = _build_occurrences(normalized_events, resolved_policy, errors)
    if errors:
        raise TimelineEventsError("; ".join(errors))
    return gaps, occurrences


def import_timeline_events(
    input_path: Path,
    output_path: Path,
    policy_path: Path | None = None,
    household_snapshot_path: Path | None = None,
    asset_availability_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    data = load_timeline_events(input_path)
    policy = _load_policy(policy_path)
    household_snapshot = _load_optional_snapshot(household_snapshot_path, "household")
    asset_availability_snapshot = _load_optional_snapshot(asset_availability_snapshot_path, "asset availability")
    gaps, occurrences = validate_timeline_events(data, household_snapshot, asset_availability_snapshot, policy)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "complete" if not gaps else "partial",
        "source": {
            "type": "timeline-events-json",
            "path": str(input_path),
        },
        "household": {
            "household_id": data["household_id"],
            "as_of_date": data["as_of_date"],
            "household_snapshot_path": str(household_snapshot_path) if household_snapshot_path else None,
            "asset_availability_snapshot_path": (
                str(asset_availability_snapshot_path) if asset_availability_snapshot_path else None
            ),
        },
        "policy": _policy_summary(policy or DEFAULT_POLICY, policy_path),
        "events": data["events"],
        "occurrences": occurrences,
        "data_gaps": gaps,
        "notes": "Timeline events are user-provided facts or assumptions; missing dates remain gaps.",
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise TimelineEventsError(f"Cannot write timeline events snapshot: {output_path}") from exc
    return snapshot


def load_timeline_events(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TimelineEventsError(f"Timeline events file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TimelineEventsError(f"Invalid JSON in timeline events file: {exc}") from exc
    if not isinstance(data, dict):
        raise TimelineEventsError("Timeline events file must contain a JSON object")
    return data


def _load_policy(path: Path | None) -> dict[str, Any]:
    if path is None:
        return DEFAULT_POLICY
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TimelineEventsError(f"Timeline policy file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TimelineEventsError(f"Invalid JSON in timeline policy file: {exc}") from exc
    if not isinstance(data, dict):
        raise TimelineEventsError("Timeline policy file must contain a JSON object")
    return data


def _load_optional_snapshot(path: Path | None, label: str) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TimelineEventsError(f"Invalid JSON in {label} snapshot: {exc}") from exc
    if not isinstance(data, dict):
        raise TimelineEventsError(f"{label.title()} snapshot must contain a JSON object")
    return data


def _validate_policy(policy: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    if policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        errors.append(f"Unsupported timeline policy schema: {policy.get('schema_version')}")
    priorities = policy.get("event_type_priorities")
    if not isinstance(priorities, dict):
        errors.append("Timeline policy event_type_priorities must be an object")
        priorities = {}
    for event_type in EVENT_TYPES:
        priority = priorities.get(event_type)
        if not isinstance(priority, int) or priority < 0:
            errors.append(f"Timeline policy priority missing or invalid for {event_type}")
    for field in ("exclusive_event_types", "exclusive_period_event_types"):
        values = policy.get(field, [])
        if not isinstance(values, list):
            errors.append(f"Timeline policy {field} must be a list")
            continue
        for value in values:
            if value not in EVENT_TYPES:
                errors.append(f"Timeline policy {field} contains unknown event type: {value}")
    return policy


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


def _asset_ids_from_availability(
    asset_availability_snapshot: dict[str, Any] | None,
    errors: list[str],
) -> set[str] | None:
    if asset_availability_snapshot is None:
        return None
    classifications = asset_availability_snapshot.get("classifications")
    if not isinstance(classifications, list):
        errors.append("Asset availability snapshot classifications must be a list")
        return set()
    asset_ids: set[str] = set()
    for index, classification in enumerate(classifications):
        if not isinstance(classification, dict):
            errors.append(f"asset_availability.classifications[{index}] must be an object")
            continue
        asset_id = classification.get("asset_id")
        if isinstance(asset_id, str) and asset_id:
            asset_ids.add(asset_id)
    return asset_ids


def _validate_events(
    events: list[Any],
    person_ids: set[str] | None,
    asset_ids: set[str] | None,
    policy: dict[str, Any],
    errors: list[str],
    gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    event_ids: set[str] = set()
    normalized_events: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"events[{index}] must be an object")
            continue
        event_id = _required_string(event, "event_id", errors, f"events[{index}]")
        if event_id:
            if event_id in event_ids:
                errors.append(f"Duplicate event_id: {event_id}")
            event_ids.add(event_id)
        event_type = event.get("event_type")
        if event_type not in EVENT_TYPES:
            errors.append(f"Invalid event_type for events[{index}]")
        timing_type = event.get("timing_type")
        if timing_type not in TIMING_TYPES:
            errors.append(f"Invalid timing_type for events[{index}]")
        person_id = event.get("subject_person_id")
        _validate_person_reference(person_id, person_ids, errors, f"events[{index}].subject_person_id")
        asset_id = event.get("related_asset_id")
        _validate_asset_reference(asset_id, asset_ids, errors, f"events[{index}].related_asset_id")
        _required_string(event, "provenance", errors, f"events[{index}]")
        start_date, end_date = _validate_timing(event, timing_type, index, errors, gaps)
        priority = _event_priority(event, event_type, policy, errors, f"events[{index}]")
        if event_id and event_type in EVENT_TYPES and timing_type in TIMING_TYPES:
            normalized_events.append(
                {
                    "event_id": event_id,
                    "event_type": event_type,
                    "timing_type": timing_type,
                    "subject_person_id": person_id,
                    "related_asset_id": asset_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "recurrence": event.get("recurrence"),
                    "priority": priority,
                }
            )
    return normalized_events


def _validate_timing(
    event: dict[str, Any],
    timing_type: Any,
    index: int,
    errors: list[str],
    gaps: list[dict[str, Any]],
) -> tuple[date | None, date | None]:
    label = f"events[{index}]"
    start_date_raw = event.get("start_date")
    end_date_raw = event.get("end_date")
    start_date = None
    end_date = None
    if start_date_raw in (None, ""):
        gaps.append(_gap("missing_start_date", event.get("event_id"), "Event start_date is missing."))
    else:
        start_date = _parse_date(start_date_raw, f"{label}.start_date", errors)
    if end_date_raw not in (None, ""):
        end_date = _parse_date(end_date_raw, f"{label}.end_date", errors)
    if timing_type == "point" and end_date is not None:
        errors.append(f"{label}.end_date must be empty for point events")
    if timing_type == "period":
        if end_date is None:
            gaps.append(_gap("missing_end_date", event.get("event_id"), "Period event end_date is missing."))
        elif start_date is not None and end_date < start_date:
            errors.append(f"{label}.end_date must be greater than or equal to start_date")
    if timing_type == "recurring":
        _validate_recurrence(event.get("recurrence"), event.get("event_id"), label, errors, gaps)
    return start_date, end_date


def _validate_recurrence(
    recurrence: Any,
    event_id: Any,
    label: str,
    errors: list[str],
    gaps: list[dict[str, Any]],
) -> None:
    if not isinstance(recurrence, dict):
        gaps.append(_gap("missing_recurrence", event_id, "Recurring event recurrence is missing."))
        return
    frequency = recurrence.get("frequency")
    if frequency not in RECURRENCE_FREQUENCIES:
        errors.append(f"{label}.recurrence.frequency is invalid")
    interval = recurrence.get("interval")
    if not isinstance(interval, int) or interval < 1:
        errors.append(f"{label}.recurrence.interval must be a positive integer")
    count = recurrence.get("count")
    until_date = recurrence.get("until_date")
    if count in (None, "") and until_date in (None, ""):
        gaps.append(_gap("missing_recurrence_end", event_id, "Recurring event needs count or until_date."))
    if count not in (None, "") and (not isinstance(count, int) or count < 1 or count > DEFAULT_MAX_OCCURRENCES):
        errors.append(f"{label}.recurrence.count must be between 1 and {DEFAULT_MAX_OCCURRENCES}")
    if until_date not in (None, ""):
        _parse_date(until_date, f"{label}.recurrence.until_date", errors)


def _event_priority(
    event: dict[str, Any],
    event_type: Any,
    policy: dict[str, Any],
    errors: list[str],
    label: str,
) -> int:
    priority = event.get("priority")
    if priority in (None, ""):
        return int(policy["event_type_priorities"].get(event_type, 999))
    if not isinstance(priority, int) or priority < 0:
        errors.append(f"{label}.priority must be a non-negative integer")
        return 999
    return priority


def _validate_conflicts(
    events: list[dict[str, Any]],
    policy: dict[str, Any],
    errors: list[str],
) -> None:
    exclusive_types = set(policy.get("exclusive_event_types", []))
    exclusive_period_types = set(policy.get("exclusive_period_event_types", []))
    point_keys: dict[tuple[str, str | None], str] = {}
    period_events: list[dict[str, Any]] = []
    duplicate_keys: set[tuple[str, str | None, str | None, date | None]] = set()
    for event in events:
        duplicate_key = (
            event["event_type"],
            event.get("subject_person_id"),
            event.get("related_asset_id"),
            event.get("start_date"),
        )
        if duplicate_key in duplicate_keys:
            errors.append(f"Duplicate timeline event on same subject/date: {event['event_id']}")
        duplicate_keys.add(duplicate_key)
        if event["event_type"] in exclusive_types and event.get("start_date") is not None:
            key = (event["event_type"], event.get("subject_person_id"))
            previous = point_keys.get(key)
            if previous is not None:
                errors.append(f"Conflicting exclusive event {event['event_type']}: {previous} and {event['event_id']}")
            point_keys[key] = event["event_id"]
        if event["event_type"] in exclusive_period_types and event.get("start_date") and event.get("end_date"):
            period_events.append(event)
    for left_index, left in enumerate(period_events):
        for right in period_events[left_index + 1 :]:
            if left["event_type"] != right["event_type"]:
                continue
            if left.get("subject_person_id") != right.get("subject_person_id"):
                continue
            if _periods_overlap(left["start_date"], left["end_date"], right["start_date"], right["end_date"]):
                errors.append(f"Conflicting overlapping period events: {left['event_id']} and {right['event_id']}")


def _build_occurrences(
    events: list[dict[str, Any]],
    policy: dict[str, Any],
    errors: list[str],
) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for event in events:
        if event["start_date"] is None:
            continue
        if event["timing_type"] == "recurring":
            occurrences.extend(_recurring_occurrences(event, errors))
        else:
            occurrences.append(_occurrence(event, event["start_date"], 1))
    occurrences.sort(
        key=lambda item: (
            item["occurrence_date"],
            item["priority"],
            item["event_id"],
            item["sequence"],
        )
    )
    return occurrences


def _recurring_occurrences(event: dict[str, Any], errors: list[str]) -> list[dict[str, Any]]:
    recurrence = event.get("recurrence")
    if not isinstance(recurrence, dict) or event["start_date"] is None:
        return []
    frequency = recurrence.get("frequency")
    interval = recurrence.get("interval")
    if frequency not in RECURRENCE_FREQUENCIES or not isinstance(interval, int) or interval < 1:
        return []
    count = recurrence.get("count")
    until_date_raw = recurrence.get("until_date")
    until_date = None
    if until_date_raw not in (None, ""):
        until_date = _parse_date(until_date_raw, f"events[{event['event_id']}].recurrence.until_date", errors)
    target_count = count if isinstance(count, int) else DEFAULT_MAX_OCCURRENCES
    occurrences: list[dict[str, Any]] = []
    current = event["start_date"]
    for sequence in range(1, target_count + 1):
        if until_date is not None and current > until_date:
            break
        occurrences.append(_occurrence(event, current, sequence))
        current = _add_interval(current, frequency, interval)
    return occurrences


def _occurrence(event: dict[str, Any], occurrence_date: date, sequence: int) -> dict[str, Any]:
    return {
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "occurrence_date": occurrence_date.isoformat(),
        "priority": event["priority"],
        "sequence": sequence,
        "subject_person_id": event.get("subject_person_id"),
        "related_asset_id": event.get("related_asset_id"),
    }


def _add_interval(value: date, frequency: str, interval: int) -> date:
    if frequency == "annual":
        return _safe_date(value.year + interval, value.month, value.day)
    month = value.month + interval
    year = value.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    return _safe_date(year, month, value.day)


def _safe_date(year: int, month: int, day: int) -> date:
    while day > 28:
        try:
            return date(year, month, day)
        except ValueError:
            day -= 1
    return date(year, month, day)


def _periods_overlap(left_start: date, left_end: date, right_start: date, right_end: date) -> bool:
    return left_start <= right_end and right_start <= left_end


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


def _validate_asset_reference(
    asset_id: Any,
    asset_ids: set[str] | None,
    errors: list[str],
    label: str,
) -> None:
    if asset_id in (None, "") or asset_ids is None:
        return
    if asset_id not in asset_ids:
        errors.append(f"{label} references unknown asset: {asset_id}")


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


def _policy_summary(policy: dict[str, Any], policy_path: Path | None) -> dict[str, Any]:
    return {
        "schema_version": policy.get("schema_version"),
        "policy_id": policy.get("policy_id"),
        "path": str(policy_path) if policy_path else None,
        "event_type_priorities": policy.get("event_type_priorities", {}),
        "exclusive_event_types": policy.get("exclusive_event_types", []),
        "exclusive_period_event_types": policy.get("exclusive_period_event_types", []),
    }


def _gap(code: str, event_id: Any, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "event_id": event_id,
        "message": message,
    }
