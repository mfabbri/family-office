"""Deterministic, workspace-local refresh DAG for operational snapshots."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from family_office_engine.services.document_inventory import build_document_inventory

SCHEMA_VERSION = "pipeline-run/v1"
PIPELINE_ID = "workspace-refresh/default"


class PipelineRefreshError(ValueError):
    """Raised after a failed step; the attached run keeps failure state visible."""

    def __init__(self, message: str, run: dict[str, Any]) -> None:
        super().__init__(message)
        self.run = run


def refresh_pipeline(
    workspace_root: Path,
    manifest_path: Path | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Refresh changed workspace-derived snapshots and persist a successful manifest only.

    The initial DAG is deliberately small and declarative.  It does not execute shell
    commands or infer financial inputs; later increments can register further safe actions.
    """
    workspace = workspace_root.resolve()
    if not workspace.is_dir():
        raise ValueError(f"Workspace path is not a directory: {workspace_root}")
    manifest = (manifest_path or workspace / "snapshots" / "pipeline-run.manifest.json").resolve()
    _require_within(workspace, manifest, "manifest")
    baseline = _load_baseline(manifest)
    steps = _step_definitions(workspace)
    run_steps: list[dict[str, Any]] = []
    fingerprints: dict[str, str] = {}

    for step in steps:
        dependency_fingerprints = {dependency: fingerprints[dependency] for dependency in step["depends_on"]}
        input_hash = _hash_json(
            {
                "action_version": step["action_version"],
                "sources": _source_hashes(step["inputs"]),
                "dependencies": dependency_fingerprints,
            }
        )
        fingerprints[step["step_id"]] = input_hash
        previous = _baseline_step(baseline, step["step_id"])
        output_exists = step["output"].is_file()
        dependency_ran = any(item["step_id"] in step["depends_on"] and item["status"] == "executed" for item in run_steps)
        needs_run = (
            previous is None
            or previous.get("input_hash") != input_hash
            or not output_exists
            or dependency_ran
        )
        record = {
            "step_id": step["step_id"],
            "action_version": step["action_version"],
            "depends_on": step["depends_on"],
            "input_hash": input_hash,
            "output_path": step["output"].relative_to(workspace).as_posix(),
            "status": "planned" if dry_run and needs_run else ("skipped" if not needs_run else "executed"),
        }
        run_steps.append(record)
        if not needs_run or dry_run:
            continue
        try:
            step["execute"]()
        except Exception as exc:  # preserve the typed state at the orchestration boundary
            record["status"] = "failed"
            record["error"] = str(exc)
            run = _run_snapshot(workspace, manifest, run_steps, dry_run=dry_run)
            raise PipelineRefreshError(f"Pipeline step {step['step_id']} failed: {exc}", run) from exc

    run = _run_snapshot(workspace, manifest, run_steps, dry_run=dry_run)
    if not dry_run:
        _write_atomic(manifest, run)
    return run


def _step_definitions(workspace: Path) -> list[dict[str, Any]]:
    inbox = workspace / "inbox"
    inventory = workspace / "snapshots" / "document-inventory.snapshot.json"
    catalog = workspace / "snapshots" / "pipeline-catalog.snapshot.json"
    for path, label in ((inbox, "inbox"), (inventory, "document inventory"), (catalog, "pipeline catalog")):
        _require_within(workspace, path.resolve(), label)
    return [
        {
            "step_id": "document_inventory",
            "action_version": "document-inventory/v1",
            "depends_on": [],
            "inputs": [inbox],
            "output": inventory,
            "execute": lambda: build_document_inventory(inbox, inventory),
        },
        {
            "step_id": "snapshot_catalog",
            "action_version": "pipeline-catalog/v1",
            "depends_on": ["document_inventory"],
            "inputs": [inventory],
            "output": catalog,
            "execute": lambda: _build_snapshot_catalog(inventory, catalog),
        },
    ]


def _build_snapshot_catalog(inventory_path: Path, output_path: Path) -> None:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if not isinstance(inventory, dict) or inventory.get("schema_version") != "document-inventory/v1":
        raise ValueError(f"Document inventory has unexpected schema: {inventory_path}")
    summary = inventory.get("summary", {})
    if not isinstance(summary, dict):
        raise ValueError(f"Document inventory has invalid summary: {inventory_path}")
    payload = {
        "schema_version": "pipeline-catalog/v1",
        "record_type": "PipelineCatalogSnapshot",
        "document_inventory_sha256": _hash_file(inventory_path),
        "document_count": summary.get("document_count"),
    }
    _write_atomic(output_path, payload)


def _run_snapshot(workspace: Path, manifest: Path, steps: list[dict[str, Any]], *, dry_run: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "PipelineRun",
        "pipeline_id": PIPELINE_ID,
        "status": "dry_run" if dry_run else "complete",
        "workspace_relative_manifest_path": manifest.relative_to(workspace).as_posix(),
        "steps": steps,
        "summary": {
            "executed": sum(step["status"] == "executed" for step in steps),
            "skipped": sum(step["status"] == "skipped" for step in steps),
            "failed": sum(step["status"] == "failed" for step in steps),
        },
    }


def _source_hashes(paths: list[Path]) -> dict[str, str]:
    return {path.name: _hash_path(path) for path in paths}


def _hash_path(path: Path) -> str:
    if not path.exists():
        # A missing produced artifact is a normal stale condition in a dry run.
        # Source validation remains the responsibility of the concrete step.
        return _hash_json({"missing_path": path.name})
    if path.is_file():
        return _hash_file(path)
    digest = hashlib.sha256()
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        digest.update(_hash_file(child).encode("ascii"))
    return digest.hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_json(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _load_baseline(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read pipeline baseline manifest: {path}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Pipeline baseline has unexpected schema: {path}")
    return payload


def _baseline_step(baseline: dict[str, Any] | None, step_id: str) -> dict[str, Any] | None:
    if baseline is None or not isinstance(baseline.get("steps"), list):
        return None
    return next((step for step in baseline["steps"] if isinstance(step, dict) and step.get("step_id") == step_id), None)


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    except OSError as exc:
        raise ValueError(f"Cannot write pipeline artifact: {path}") from exc


def _require_within(workspace: Path, path: Path, label: str) -> None:
    try:
        path.relative_to(workspace)
    except ValueError as exc:
        raise ValueError(f"Pipeline {label} path is outside workspace: {path}") from exc
