"""Deterministic local release gate for engine, rules and knowledge contracts."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from family_office_engine.services.orchestration_evaluation import evaluate_orchestration

SCHEMA_VERSION = "release-gate/v1"
REPORT_TYPE = "ReleaseGateReport"


class ReleaseGovernanceError(ValueError):
    """Raised when a release gate cannot produce a trustworthy result."""


def build_release_gate(
    repository_root: Path,
    *,
    candidate_id: str,
    output_path: Path | None = None,
    baseline_path: Path | None = None,
    run_tests: bool = True,
    rollback_strategy: str = "operator_restore_previous_release",
) -> dict[str, Any]:
    root = repository_root.resolve()
    if not root.is_dir() or not candidate_id.strip():
        raise ReleaseGovernanceError("repository_root and candidate_id are required")
    if not rollback_strategy.strip():
        raise ReleaseGovernanceError("rollback_strategy is required")
    matrix = _version_matrix(root)
    checks = []
    if run_tests:
        checks.append(_run_check(root, "unit_regression", [sys.executable, "-m", "unittest", "discover", "-s", "tests/unit", "-p", "test_*.py"]))
    checks.extend([
        _run_check(root, "compileall", [sys.executable, "-m", "compileall", "-q", "src", "tests"]),
        _run_check(root, "dependencies", [sys.executable, "-m", "pip", "check"]),
        _run_check(root.parent, "roadmap_audit", [sys.executable, str(root / "src" / "family_office_engine" / "governance" / "roadmap_audit.py")]),
    ])
    evaluation = _run_evaluation(root, baseline_path)
    checks.append({"check_id": "orchestration_evaluation", "status": "passed" if evaluation["release_gate"]["passed"] else "failed"})
    failures = [item["check_id"] for item in checks if item["status"] != "passed"]
    if not evaluation["release_gate"]["passed"]:
        failures.append("orchestration_evaluation")
    baseline = _read_baseline(baseline_path) if baseline_path else None
    if baseline is not None and not _compatible_version_matrix(matrix, baseline.get("version_matrix", [])):
        failures.append("schema_incompatibility")
    if baseline is not None and baseline.get("release_gate", {}).get("passed") and failures:
        failures.append("baseline_regression")
    report = {
        "schema_version": SCHEMA_VERSION,
        "record_type": REPORT_TYPE,
        "candidate_id": candidate_id.strip(),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version_matrix": matrix,
        "checks": checks,
        "evaluation": evaluation,
        "rollback_plan": {"strategy": rollback_strategy.strip(), "requires_operator_approval": True, "automatic_execution": False, "previous_release_reference": baseline.get("candidate_id") if baseline else None},
        "release_gate": {"passed": not failures, "failures": sorted(set(failures)), "network_used": False, "workspace_data_used": False, "llm_used": False},
    }
    report["reproducibility"] = {"hash_algorithm": "sha256", "content_hash": _hash({key: value for key, value in report.items() if key != "reproducibility"})}
    if output_path is not None:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except OSError as exc:
            raise ReleaseGovernanceError(f"Cannot write release gate report: {output_path}") from exc
    return report


def _compatible_version_matrix(current: list[dict[str, Any]], baseline: list[dict[str, Any]]) -> bool:
    previous = {item.get("path"): item.get("schema_version") for item in baseline if isinstance(item, dict)}
    for item in current:
        path = item.get("path")
        if path in previous and previous[path] != item.get("schema_version"):
            return False
    return True


def _version_matrix(root: Path) -> list[dict[str, Any]]:
    sources = [root / "pyproject.toml", root / "evaluations" / "v5.11-orchestration-evaluation.json", root.parent / "family-office-rules" / "compliance" / "guardrail-policy-v1.json"]
    matrix = []
    for path in sources:
        if not path.is_file():
            raise ReleaseGovernanceError(f"release source is missing: {path}")
        raw = path.read_bytes()
        entry: dict[str, Any] = {"path": path.relative_to(root.parent).as_posix(), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
        if path.suffix == ".json":
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ReleaseGovernanceError(f"release source is invalid JSON: {path}") from exc
            entry["schema_version"] = value.get("schema_version")
        elif path.name == "pyproject.toml":
            entry["project_version"] = next((line.split("=", 1)[1].strip().strip('"') for line in raw.decode().splitlines() if line.startswith("version=")), None)
        matrix.append(entry)
    return matrix


def _run_evaluation(root: Path, baseline_path: Path | None) -> dict[str, Any]:
    try:
        dataset = json.loads((root / "evaluations" / "v5.11-orchestration-evaluation.json").read_text(encoding="utf-8"))
        policy = json.loads((root.parent / "family-office-rules" / "compliance" / "guardrail-policy-v1.json").read_text(encoding="utf-8"))
        baseline = _read_baseline(baseline_path).get("evaluation") if baseline_path else None
        return evaluate_orchestration(dataset, policy, candidate_id="release-gate", baseline=baseline)
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ReleaseGovernanceError("release evaluation inputs are invalid") from exc


def _run_check(root: Path, check_id: str, command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"check_id": check_id, "status": "failed", "error": type(exc).__name__}
    return {"check_id": check_id, "status": "passed" if completed.returncode == 0 else "failed", "return_code": completed.returncode}


def _read_baseline(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseGovernanceError("baseline release report is invalid") from exc
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ReleaseGovernanceError("baseline release report has an unsupported schema")
    return value


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
