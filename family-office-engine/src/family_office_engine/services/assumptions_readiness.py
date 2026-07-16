import json
from pathlib import Path
from typing import Any

from family_office_engine.ingestion.manual_assumptions import (
    AssumptionsImportError,
    load_assumptions,
)

SCHEMA_VERSION = "assumptions-readiness/v1"


class AssumptionsReadinessError(ValueError):
    pass


def check_assumptions_readiness(
    input_path: Path,
    template_path: Path,
    snapshot_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    data_gaps: list[dict[str, str]] = []
    next_actions: list[str] = []

    template_exists = template_path.exists()
    input_exists = input_path.exists()
    snapshot_exists = snapshot_path.exists()

    checks.append(_check("template_file", template_path, template_exists))
    checks.append(_check("assumptions_input", input_path, input_exists))
    checks.append(_check("manual_assumptions_snapshot", snapshot_path, snapshot_exists))

    status = "ready"

    if not template_exists:
        status = "missing_template"
        data_gaps.append(
            {
                "code": "missing_assumptions_template",
                "path": str(template_path),
                "message": "Assumptions template file is missing.",
            }
        )

    if not input_exists:
        status = "missing_input"
        data_gaps.append(
            {
                "code": "missing_assumptions_input",
                "path": str(input_path),
                "message": "Private assumptions input file is missing.",
            }
        )
        next_actions.append(
            "Run fo assumptions prepare, then create base-assumptions.json with reviewed real assumptions."
        )
    else:
        try:
            load_assumptions(input_path)
        except AssumptionsImportError as exc:
            status = "invalid_input"
            data_gaps.append(
                {
                    "code": "invalid_assumptions_input",
                    "path": str(input_path),
                    "message": str(exc),
                }
            )
            next_actions.append(
                "Fix the private assumptions input, then run fo assumptions import."
            )

    if input_exists and status != "invalid_input" and not snapshot_exists:
        status = "missing_snapshot"
        data_gaps.append(
            {
                "code": "missing_manual_assumptions_snapshot",
                "path": str(snapshot_path),
                "message": "Validated assumptions have not been normalized yet.",
            }
        )
        next_actions.append("Run fo assumptions import to create the normalized snapshot.")

    if status == "ready":
        next_actions.append("Run fo net-worth consolidate, then fo retirement simulate.")

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "AssumptionsReadinessSnapshot",
        "status": status,
        "paths": {
            "template": str(template_path),
            "input": str(input_path),
            "snapshot": str(snapshot_path),
        },
        "checks": checks,
        "data_gaps": data_gaps,
        "next_actions": next_actions,
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise AssumptionsReadinessError(f"Cannot write readiness snapshot: {output_path}") from exc

    return snapshot


def _check(name: str, path: Path, exists: bool) -> dict[str, str]:
    return {
        "name": name,
        "path": str(path),
        "status": "present" if exists else "missing",
    }
