from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


AUDIT_INTERVAL = 4
ALLOWED_KINDS = {"functional", "audit", "governance", "docs"}
ALLOWED_STATUSES = {"planned", "in_progress", "done", "blocked", "deferred"}
INCREMENT_ID_PATTERN = r"V\d+(?:\.\d+)*(?:[a-z](?:-[a-z])*)?"
HEADER_RE = re.compile(
    rf"^###\s+(?P<increment_id>{INCREMENT_ID_PATTERN})\s+[-\u2013\u2014]\s+(?P<title>.+?)\s*$"
)
STATUS_RE = re.compile(r"^\*\*Stato:\*\*\s+`(?P<value>[^`]+)`\s*$")
KIND_RE = re.compile(r"^\*\*Tipo:\*\*\s+`(?P<value>[^`]+)`\s*$")
CURRENT_STATUS_RE = re.compile(r"^`(?P<value>[^`]+)`\s*$")
CURRENT_ID_RE = re.compile(
    rf"^(?P<increment_id>{INCREMENT_ID_PATTERN})\s+[-\u2013\u2014]\s+.+$"
)
ROADMAP_INDEX_ROW_RE = re.compile(
    r"^\|\s*\d+\s*\|\s*`(?P<path>[^`]+)`\s*\|.*\|\s*`(?P<status>[^`]+)`\s*\|\s*$"
)


class RoadmapAuditCadenceError(ValueError):
    """Raised when roadmap metadata or audit cadence is invalid."""


@dataclass(frozen=True)
class RoadmapIncrement:
    increment_id: str
    title: str
    status: str
    kind: str
    line_number: int


@dataclass(frozen=True)
class CurrentIncrement:
    increment_id: str
    status: str


@dataclass(frozen=True)
class AuditCadenceReport:
    current_increment_id: str
    current_increment_kind: str
    functional_since_last_audit: int
    audit_due: bool
    last_completed_audit_id: str | None


def parse_roadmap(path: Path) -> list[RoadmapIncrement]:
    lines = path.read_text(encoding="utf-8").splitlines()
    headers: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        match = HEADER_RE.match(line)
        if match:
            headers.append((index, match))

    if not headers:
        raise RoadmapAuditCadenceError(f"No roadmap increments found in {path}.")

    increments: list[RoadmapIncrement] = []
    seen_ids: set[str] = set()
    for position, (start, match) in enumerate(headers):
        end = headers[position + 1][0] if position + 1 < len(headers) else len(lines)
        section = lines[start + 1 : end]
        increment_id = match.group("increment_id")
        if increment_id in seen_ids:
            raise RoadmapAuditCadenceError(
                f"Duplicate increment {increment_id} in {path}."
            )
        seen_ids.add(increment_id)
        status = _single_metadata_value(
            section, STATUS_RE, "Stato", increment_id, path
        )
        kind = _single_metadata_value(section, KIND_RE, "Tipo", increment_id, path)
        if status not in ALLOWED_STATUSES:
            raise RoadmapAuditCadenceError(
                f"Increment {increment_id} has unsupported status {status!r}."
            )
        if kind not in ALLOWED_KINDS:
            raise RoadmapAuditCadenceError(
                f"Increment {increment_id} has unsupported type {kind!r}."
            )
        increments.append(
            RoadmapIncrement(
                increment_id=increment_id,
                title=match.group("title"),
                status=status,
                kind=kind,
                line_number=start + 1,
            )
        )
    return increments


def parse_current_increment(path: Path) -> CurrentIncrement:
    lines = path.read_text(encoding="utf-8").splitlines()
    increment_id = _value_after_heading(lines, "## ID e titolo", CURRENT_ID_RE, path)
    status = _value_after_heading(lines, "## Stato", CURRENT_STATUS_RE, path)
    return CurrentIncrement(increment_id=increment_id, status=status)


def validate_audit_cadence(
    roadmap_path: Path,
    current_increment_path: Path,
    *,
    audit_interval: int = AUDIT_INTERVAL,
) -> AuditCadenceReport:
    if audit_interval < 1:
        raise RoadmapAuditCadenceError("Audit interval must be positive.")

    increments = parse_roadmap(roadmap_path)
    current = parse_current_increment(current_increment_path)
    by_id = {increment.increment_id: increment for increment in increments}
    roadmap_current = by_id.get(current.increment_id)
    if roadmap_current is None:
        raise RoadmapAuditCadenceError(
            f"Current increment {current.increment_id} is absent from {roadmap_path}."
        )
    if roadmap_current.status != current.status:
        raise RoadmapAuditCadenceError(
            f"Current increment {current.increment_id} has status {current.status!r} "
            f"in {current_increment_path} and {roadmap_current.status!r} in the roadmap."
        )

    last_audit_index: int | None = None
    for index, increment in enumerate(increments):
        if increment.kind == "audit" and increment.status == "done":
            last_audit_index = index

    relevant = increments[last_audit_index + 1 :] if last_audit_index is not None else increments
    functional_since_last_audit = sum(
        increment.kind == "functional" and increment.status == "done"
        for increment in relevant
    )
    audit_due = functional_since_last_audit >= audit_interval
    if audit_due and not _audit_requirement_allows_current(
        roadmap_current, increments, last_audit_index
    ):
        last_audit_id = (
            increments[last_audit_index].increment_id
            if last_audit_index is not None
            else "none"
        )
        raise RoadmapAuditCadenceError(
            f"Audit due after {functional_since_last_audit} completed functional "
            f"increments since {last_audit_id}; current increment "
            f"{current.increment_id} is {roadmap_current.kind!r}, not 'audit'."
        )

    return AuditCadenceReport(
        current_increment_id=current.increment_id,
        current_increment_kind=roadmap_current.kind,
        functional_since_last_audit=functional_since_last_audit,
        audit_due=audit_due,
        last_completed_audit_id=(
            increments[last_audit_index].increment_id
            if last_audit_index is not None
            else None
        ),
    )


def _audit_requirement_allows_current(
    current: RoadmapIncrement,
    increments: list[RoadmapIncrement],
    last_audit_index: int | None,
) -> bool:
    """Allow the just-completed fourth functional increment to await its audit.

    The audit remains due and a later planned/in-progress functional increment is
    rejected. Without this narrow transition state, marking the fourth item done
    would itself make the validator fail before an audit could be selected.
    """
    if current.kind in {"audit", "governance", "docs"}:
        return True
    if current.kind != "functional" or current.status != "done":
        return False
    relevant = increments[last_audit_index + 1 :] if last_audit_index is not None else increments
    latest_completed_functional = max(
        (increment for increment in relevant if increment.kind == "functional" and increment.status == "done"),
        key=increments.index,
    )
    return latest_completed_functional.increment_id == current.increment_id


def default_paths() -> tuple[Path, Path]:
    repository_root = Path(__file__).resolve().parents[4]
    engine_docs = repository_root / "family-office-engine" / "docs"
    roadmap_index = engine_docs / "roadmap" / "roadmap-index.md"
    return (
        active_roadmap_path(roadmap_index),
        engine_docs / "current-next-increment.md",
    )


def active_roadmap_path(index_path: Path) -> Path:
    active_paths = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        match = ROADMAP_INDEX_ROW_RE.match(line)
        if match and match.group("status") == "in_progress":
            active_paths.append(match.group("path"))
    if len(active_paths) != 1:
        raise RoadmapAuditCadenceError(
            f"Roadmap index {index_path} must declare exactly one in_progress roadmap; "
            f"found {len(active_paths)}."
        )
    return index_path.parent / active_paths[0]


def main(argv: Sequence[str] | None = None) -> int:
    default_roadmap, default_current = default_paths()
    parser = argparse.ArgumentParser(
        description="Validate roadmap code-audit cadence and current selection."
    )
    parser.add_argument("--roadmap", type=Path, default=default_roadmap)
    parser.add_argument("--current", type=Path, default=default_current)
    args = parser.parse_args(argv)
    try:
        report = validate_audit_cadence(args.roadmap, args.current)
    except (OSError, RoadmapAuditCadenceError) as exc:
        parser.exit(1, f"roadmap audit cadence: ERROR: {exc}\n")
    print(
        "roadmap audit cadence: OK "
        f"(current={report.current_increment_id}, "
        f"type={report.current_increment_kind}, "
        f"functional_since_audit={report.functional_since_last_audit}, "
        f"audit_due={str(report.audit_due).lower()})"
    )
    return 0


def _single_metadata_value(
    section: list[str],
    pattern: re.Pattern[str],
    label: str,
    increment_id: str,
    path: Path,
) -> str:
    values = [match.group("value") for line in section if (match := pattern.match(line))]
    if len(values) != 1:
        raise RoadmapAuditCadenceError(
            f"Increment {increment_id} must have exactly one {label} field in {path}; "
            f"found {len(values)}."
        )
    return values[0]


def _value_after_heading(
    lines: list[str],
    heading: str,
    pattern: re.Pattern[str],
    path: Path,
) -> str:
    try:
        heading_index = lines.index(heading)
    except ValueError as exc:
        raise RoadmapAuditCadenceError(f"Missing heading {heading!r} in {path}.") from exc
    for line in lines[heading_index + 1 :]:
        if line.startswith("## "):
            break
        if not line.strip():
            continue
        match = pattern.match(line)
        if not match:
            raise RoadmapAuditCadenceError(
                f"Invalid value after {heading!r} in {path}: {line!r}."
            )
        group_name = "increment_id" if "increment_id" in pattern.groupindex else "value"
        return match.group(group_name)
    raise RoadmapAuditCadenceError(f"Missing value after {heading!r} in {path}.")


if __name__ == "__main__":
    raise SystemExit(main())
