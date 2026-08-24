import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


INPUT_SCHEMA_VERSION = "work-transition-scenario-input/v1"
READINESS_SCHEMA_VERSION = "work-transition-readiness/v1"
SCHEMA_VERSION = "work-transition-scenario/v1"
POLICY_VERSION = "work-transition-monthly-phases/v1"

WORK_STATUSES = {"full_time", "part_time", "not_working"}


class WorkTransitionScenarioError(ValueError):
    pass


def build_work_transition_scenario(input_path: Path, readiness_snapshot_path: Path, output_path: Path) -> dict[str, Any]:
    scenario_input = _read_json(input_path, "work-transition scenario input")
    readiness = _read_json(readiness_snapshot_path, "work-transition readiness snapshot")
    if scenario_input.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise WorkTransitionScenarioError(
            f"Unsupported work-transition scenario input schema: {scenario_input.get('schema_version')}"
        )
    if scenario_input.get("record_type") != "WorkTransitionScenarioInput":
        raise WorkTransitionScenarioError(
            f"Unsupported work-transition scenario input record type: {scenario_input.get('record_type')}"
        )
    _reject_unknown_keys(
        scenario_input,
        {
            "schema_version",
            "record_type",
            "household_id",
            "as_of_date",
            "plan_start_date",
            "plan_end_date",
            "work_phases",
            "declared_timeline_gaps",
        },
        "scenario input",
    )
    if readiness.get("schema_version") != READINESS_SCHEMA_VERSION:
        raise WorkTransitionScenarioError(
            f"Unsupported work-transition readiness schema: {readiness.get('schema_version')}"
        )
    if readiness.get("record_type") != "WorkTransitionReadinessSnapshot":
        raise WorkTransitionScenarioError("readiness snapshot must be WorkTransitionReadinessSnapshot")
    _validate_readiness_integrity(readiness)

    household_id = _required_string(scenario_input, "household_id")
    if readiness.get("household_id") != household_id:
        raise WorkTransitionScenarioError("scenario household_id must match readiness household_id")
    as_of_date = _required_date(scenario_input.get("as_of_date"), "as_of_date")
    if readiness.get("as_of_date") != as_of_date.isoformat():
        raise WorkTransitionScenarioError("scenario as_of_date must match readiness as_of_date")
    members = _household_members(readiness.get("household_members"))
    plan_start = _required_month_start(scenario_input.get("plan_start_date"), "plan_start_date")
    plan_end = _required_month_start(scenario_input.get("plan_end_date"), "plan_end_date")
    if plan_start > plan_end:
        raise WorkTransitionScenarioError("plan_start_date must not be after plan_end_date")

    phases = _work_phases(scenario_input.get("work_phases"), members, plan_start, plan_end)
    declared_gaps = _declared_gaps(scenario_input.get("declared_timeline_gaps", []), members, plan_start, plan_end)
    timelines, summaries, data_gaps = _build_member_timelines(phases, declared_gaps, members, plan_start, plan_end)
    blocking_count = sum(1 for gap in data_gaps if gap["blocking"])
    status = "blocked" if blocking_count else "ready"
    core = {
        "household_id": household_id,
        "as_of_date": as_of_date.isoformat(),
        "status": status,
        "readiness_snapshot": {
            "path": str(readiness_snapshot_path).replace("\\", "/"),
            "schema_version": readiness.get("schema_version"),
            "status": readiness.get("status"),
            "content_hash": readiness.get("reproducibility", {}).get("content_hash"),
        },
        "policy": {
            "policy_version": POLICY_VERSION,
            "primary_granularity": "monthly",
            "phase_period_inclusivity": "inclusive_start_month_inclusive_end_month",
            "income_projection": "not_calculated_in_v4_12",
            "pension_dates": "not_derived_in_v4_12",
        },
        "household_members": sorted(members),
        "plan_period": {"start_date": plan_start.isoformat(), "end_date": plan_end.isoformat()},
        "derived_dates": {
            "full_time_exit_date_by_member": {
                member: summaries[member]["full_time_exit_date"] for member in sorted(summaries)
            },
            "work_cessation_date_by_member": {
                member: summaries[member]["work_cessation_date"] for member in sorted(summaries)
            },
            "pension_entitlement_date_by_member": {member: None for member in sorted(summaries)},
            "pension_payment_start_date_by_member": {member: None for member in sorted(summaries)},
        },
        "member_summaries": [summaries[member] for member in sorted(summaries)],
        "work_phases": sorted(phases, key=lambda item: (item["member_id"], item["start_date"], item["phase_id"])),
        "monthly_timeline": [timelines[member] for member in sorted(timelines)],
        "declared_timeline_gaps": declared_gaps,
        "data_gaps": sorted(data_gaps, key=lambda gap: (not gap["blocking"], gap["member_id"], gap["code"], gap["start_date"])),
        "summary": {
            "member_count": len(members),
            "phase_count": len(phases),
            "timeline_month_count": sum(len(item["months"]) for item in timelines.values()),
            "blocking_gap_count": blocking_count,
            "warning_count": len(data_gaps) - blocking_count,
        },
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "WorkTransitionScenarioSnapshot",
        **core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(core),
        },
        "notes": (
            "Scenario phases define monthly FTE and policy references only. V4.12 does not calculate net income, "
            "taxes, contributions, TFR, RITA, pensions, investment returns or optimal exit dates."
        ),
    }
    _assert_output_scope(output_path)
    return _write_snapshot(snapshot, output_path)


def _work_phases(value: Any, members: set[str], plan_start: date, plan_end: date) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise WorkTransitionScenarioError("work_phases must contain at least one phase")
    result = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise WorkTransitionScenarioError(f"work_phases[{index}] must be an object")
        _reject_unknown_keys(
            item,
            {
                "phase_id",
                "member_id",
                "start_date",
                "end_date",
                "status",
                "fte",
                "compensation_policy_ref",
                "contribution_benefit_policy_ref",
                "contractual_constraints",
                "provenance",
            },
            f"work_phases[{index}]",
        )
        phase_id = _required_string(item, "phase_id", f"work_phases[{index}]")
        if phase_id in seen:
            raise WorkTransitionScenarioError(f"Duplicate phase id: {phase_id}")
        seen.add(phase_id)
        member_id = _required_string(item, "member_id", phase_id)
        if member_id not in members:
            raise WorkTransitionScenarioError(f"Unknown household member in phase {phase_id}: {member_id}")
        start = _required_month_start(item.get("start_date"), f"{phase_id}.start_date")
        end = _required_month_start(item.get("end_date"), f"{phase_id}.end_date")
        if start > end:
            raise WorkTransitionScenarioError(f"{phase_id} has zero or negative duration")
        if start < plan_start or end > plan_end:
            raise WorkTransitionScenarioError(f"{phase_id} must stay inside the plan period")
        status = _required_string(item, "status", phase_id)
        if status not in WORK_STATUSES:
            raise WorkTransitionScenarioError(f"Unsupported work status for {phase_id}: {status}")
        fte = _required_fte(item.get("fte"), f"{phase_id}.fte")
        _validate_status_fte(phase_id, status, fte)
        result.append(
            {
                "phase_id": phase_id,
                "member_id": member_id,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "status": status,
                "fte": fte,
                "compensation_policy_ref": _required_string(item, "compensation_policy_ref", phase_id),
                "contribution_benefit_policy_ref": _required_string(
                    item, "contribution_benefit_policy_ref", phase_id
                ),
                "contractual_constraints": _constraints(item.get("contractual_constraints"), phase_id),
                "provenance": _provenance(item.get("provenance"), phase_id),
            }
        )
    return result


def _declared_gaps(value: Any, members: set[str], plan_start: date, plan_end: date) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise WorkTransitionScenarioError("declared_timeline_gaps must be an array")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise WorkTransitionScenarioError(f"declared_timeline_gaps[{index}] must be an object")
        _reject_unknown_keys(
            item,
            {"member_id", "start_date", "end_date", "reason"},
            f"declared_timeline_gaps[{index}]",
        )
        member_id = _required_string(item, "member_id", f"declared_timeline_gaps[{index}]")
        if member_id not in members:
            raise WorkTransitionScenarioError(f"Unknown household member in declared gap: {member_id}")
        start = _required_month_start(item.get("start_date"), f"declared_timeline_gaps[{index}].start_date")
        end = _required_month_start(item.get("end_date"), f"declared_timeline_gaps[{index}].end_date")
        if start > end:
            raise WorkTransitionScenarioError("declared timeline gap has zero or negative duration")
        if start < plan_start or end > plan_end:
            raise WorkTransitionScenarioError("declared timeline gap must stay inside the plan period")
        result.append(
            {
                "member_id": member_id,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "reason": _required_string(item, "reason", f"declared_timeline_gaps[{index}]"),
            }
        )
    return sorted(result, key=lambda item: (item["member_id"], item["start_date"]))


def _build_member_timelines(
    phases: list[dict[str, Any]],
    declared_gaps: list[dict[str, Any]],
    members: set[str],
    plan_start: date,
    plan_end: date,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    timelines = {}
    summaries = {}
    data_gaps = []
    for member in sorted(members):
        member_phases = sorted(
            (item for item in phases if item["member_id"] == member),
            key=lambda item: (item["start_date"], item["phase_id"]),
        )
        member_gaps = [item for item in declared_gaps if item["member_id"] == member]
        _append_sequence_gaps(member, member_phases, member_gaps, plan_start, plan_end, data_gaps)
        months = _month_records(member_phases)
        member_blocked = any(gap["member_id"] == member and gap["blocking"] for gap in data_gaps)
        full_time_exit = None if member_blocked else _first_month_after_full_time(months, lambda item: item["fte"] < 1.0)
        work_cessation = None if member_blocked else _first_month_after_work(months, lambda item: item["fte"] == 0.0)
        summaries[member] = {
            "member_id": member,
            "first_month": months[0]["month"] if months else None,
            "last_month": months[-1]["month"] if months else None,
            "full_time_exit_date": full_time_exit,
            "work_cessation_date": work_cessation,
            "pension_entitlement_date": None,
            "pension_payment_start_date": None,
            "status_sequence": _status_sequence(member_phases),
        }
        timelines[member] = {"member_id": member, "months": months}
    return timelines, summaries, data_gaps


def _append_sequence_gaps(
    member: str,
    phases: list[dict[str, Any]],
    declared_gaps: list[dict[str, Any]],
    plan_start: date,
    plan_end: date,
    data_gaps: list[dict[str, Any]],
) -> None:
    if not phases:
        data_gaps.append(_gap("missing_member_timeline", member, plan_start, plan_end, True, "No work phase declared."))
        return
    cursor = plan_start
    previous_end: date | None = None
    for phase in phases:
        start = date.fromisoformat(phase["start_date"])
        end = date.fromisoformat(phase["end_date"])
        if previous_end is not None and start <= previous_end:
            data_gaps.append(_gap("overlapping_phases", member, start, end, True, f"Phase {phase['phase_id']} overlaps."))
        if start > cursor:
            gap_end = _previous_month(start)
            data_gaps.append(_timeline_gap(member, cursor, gap_end, declared_gaps))
        cursor = _next_month(end)
        previous_end = max(previous_end, end) if previous_end else end
    if cursor <= plan_end:
        data_gaps.append(_timeline_gap(member, cursor, plan_end, declared_gaps))


def _month_records(phases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    months = []
    for phase in phases:
        current = date.fromisoformat(phase["start_date"])
        end = date.fromisoformat(phase["end_date"])
        while current <= end:
            months.append(
                {
                    "month": current.isoformat(),
                    "phase_id": phase["phase_id"],
                    "status": phase["status"],
                    "fte": phase["fte"],
                    "compensation_policy_ref": phase["compensation_policy_ref"],
                    "contribution_benefit_policy_ref": phase["contribution_benefit_policy_ref"],
                }
            )
            current = _next_month(current)
    return sorted(months, key=lambda item: item["month"])


def _first_month_after_full_time(months: list[dict[str, Any]], predicate: Any) -> str | None:
    seen_full_time = False
    for month in months:
        if seen_full_time and predicate(month):
            return month["month"]
        if month["fte"] == 1.0:
            seen_full_time = True
    return None


def _first_month_after_work(months: list[dict[str, Any]], predicate: Any) -> str | None:
    seen_work = False
    for month in months:
        if seen_work and predicate(month):
            return month["month"]
        if month["fte"] > 0.0:
            seen_work = True
    return None


def _status_sequence(phases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "phase_id": phase["phase_id"],
            "start_date": phase["start_date"],
            "end_date": phase["end_date"],
            "status": phase["status"],
            "fte": phase["fte"],
        }
        for phase in phases
    ]


def _timeline_gap(member: str, start: date, end: date, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    declared = any(
        gap["member_id"] == member and gap["start_date"] <= start.isoformat() and gap["end_date"] >= end.isoformat()
        for gap in gaps
    )
    if declared:
        return _gap("declared_timeline_gap", member, start, end, True, "Declared timeline gap has no monthly work phase.")
    return _gap("undeclared_timeline_gap", member, start, end, True, "Timeline gap is not declared.")


def _validate_readiness_integrity(readiness: dict[str, Any]) -> None:
    required_core_fields = {
        "household_id",
        "as_of_date",
        "status",
        "optimization_allowed",
        "policy",
        "household_members",
        "input_selections",
        "sources",
        "data_gaps",
        "summary",
    }
    missing = sorted(required_core_fields - set(readiness))
    if missing:
        raise WorkTransitionScenarioError(f"readiness snapshot is missing required fields: {', '.join(missing)}")
    status = readiness.get("status")
    optimization_allowed = readiness.get("optimization_allowed")
    if status == "blocked" or optimization_allowed is not True:
        raise WorkTransitionScenarioError("readiness snapshot is blocked; scenario construction is not allowed")
    if status not in {"ready", "partial"}:
        raise WorkTransitionScenarioError(f"Unsupported readiness status: {status}")
    data_gaps = readiness.get("data_gaps")
    if not isinstance(data_gaps, list):
        raise WorkTransitionScenarioError("readiness data_gaps must be an array")
    if any(isinstance(gap, dict) and gap.get("blocking") is True for gap in data_gaps):
        raise WorkTransitionScenarioError("readiness snapshot contains blocking data gaps")
    summary = readiness.get("summary")
    if not isinstance(summary, dict) or summary.get("blocking_gap_count") != 0:
        raise WorkTransitionScenarioError("readiness summary must report zero blocking gaps")
    warning_count = summary.get("warning_count")
    if not isinstance(warning_count, int) or isinstance(warning_count, bool) or warning_count != len(data_gaps):
        raise WorkTransitionScenarioError("readiness warning_count must match non-blocking data gaps")
    if status == "ready" and data_gaps:
        raise WorkTransitionScenarioError("readiness status ready must not include warning gaps")
    if status == "partial" and not data_gaps:
        raise WorkTransitionScenarioError("readiness status partial must include warning gaps")
    reproducibility = readiness.get("reproducibility")
    if not isinstance(reproducibility, dict) or reproducibility.get("hash_algorithm") != "sha256":
        raise WorkTransitionScenarioError("readiness reproducibility hash is required")
    declared_hash = reproducibility.get("content_hash")
    if not isinstance(declared_hash, str) or not declared_hash:
        raise WorkTransitionScenarioError("readiness reproducibility content_hash is required")
    readiness_core = {key: readiness[key] for key in required_core_fields}
    if _content_hash(readiness_core) != declared_hash:
        raise WorkTransitionScenarioError("readiness content_hash does not match snapshot content")


def _constraints(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise WorkTransitionScenarioError(f"{label}.contractual_constraints must be an array")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise WorkTransitionScenarioError(f"{label}.contractual_constraints[{index}] must be an object")
        _reject_unknown_keys(
            item,
            {"constraint_id", "constraint_type", "description", "binding"},
            f"{label}.contractual_constraints[{index}]",
        )
        result.append(
            {
                "constraint_id": _required_string(item, "constraint_id", f"{label}.contractual_constraints[{index}]"),
                "constraint_type": _required_string(item, "constraint_type", f"{label}.contractual_constraints[{index}]"),
                "description": _required_string(item, "description", f"{label}.contractual_constraints[{index}]"),
                "binding": item.get("binding", "declared"),
            }
        )
    return result


def _provenance(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WorkTransitionScenarioError(f"{label}.provenance.origin is required")
    _reject_unknown_keys(value, {"origin"}, f"{label}.provenance")
    result = dict(value)
    result["origin"] = _required_text(result.get("origin"), f"{label}.provenance.origin")
    return result


def _reject_unknown_keys(data: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise WorkTransitionScenarioError(f"{label} contains unsupported fields: {', '.join(unknown)}")


def _validate_status_fte(phase_id: str, status: str, fte: float) -> None:
    if status == "full_time" and fte != 1.0:
        raise WorkTransitionScenarioError(f"{phase_id}.fte must be 1.0 for full_time")
    if status == "part_time" and not 0.0 < fte < 1.0:
        raise WorkTransitionScenarioError(f"{phase_id}.fte must be between 0 and 1 for part_time")
    if status == "not_working" and fte != 0.0:
        raise WorkTransitionScenarioError(f"{phase_id}.fte must be 0.0 for not_working")


def _household_members(value: Any) -> set[str]:
    if not isinstance(value, list) or not value:
        raise WorkTransitionScenarioError("readiness household_members must contain at least one member id")
    return {_required_text(item, f"household_members[{index}]") for index, item in enumerate(value)}


def _required_fte(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WorkTransitionScenarioError(f"{label} must be a number between 0 and 1")
    fte = float(value)
    if fte < 0.0 or fte > 1.0:
        raise WorkTransitionScenarioError(f"{label} must be a number between 0 and 1")
    return round(fte, 4)


def _required_month_start(value: Any, label: str) -> date:
    parsed = _required_date(value, label)
    if parsed.day != 1:
        raise WorkTransitionScenarioError(f"{label} must be the first day of a month")
    return parsed


def _required_date(value: Any, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise WorkTransitionScenarioError(f"{label} must be an ISO date") from exc


def _next_month(value: date) -> date:
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    return date(year, month, 1)


def _previous_month(value: date) -> date:
    year = value.year - (1 if value.month == 1 else 0)
    month = 12 if value.month == 1 else value.month - 1
    return date(year, month, 1)


def _gap(code: str, member_id: str, start: date, end: date, blocking: bool, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "member_id": member_id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "blocking": blocking,
        "message": message,
    }


def _required_string(data: dict[str, Any], key: str, label: str | None = None) -> str:
    return _required_text(data.get(key), f"{label + '.' if label else ''}{key}")


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkTransitionScenarioError(f"{label} must be a non-empty string")
    return value.strip()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkTransitionScenarioError(f"Cannot read {label}: {path}") from exc
    if not isinstance(data, dict):
        raise WorkTransitionScenarioError(f"{label} must be a JSON object")
    return data


def _write_snapshot(snapshot: dict[str, Any], output_path: Path) -> dict[str, Any]:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise WorkTransitionScenarioError(f"Cannot write work-transition scenario snapshot: {output_path}") from exc
    return snapshot


def _assert_output_scope(output_path: Path) -> None:
    workspace_root = _workspace_root()
    try:
        output_path.resolve().relative_to(workspace_root.resolve())
    except ValueError as exc:
        raise WorkTransitionScenarioError("Work-transition scenario output must stay inside family-office-workspace.") from exc


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[4] / "family-office-workspace"


def _content_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
