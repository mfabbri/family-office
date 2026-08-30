"""Workspace-local artifact lineage and deterministic freshness checks."""
from __future__ import annotations
import hashlib
import json
import os
from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Any

SCHEMA_VERSION = "artifact-lineage/v1"

class ArtifactLineageError(ValueError):
    """Raised when a lineage sidecar is malformed or escapes its workspace."""

def build_artifact_lineage(input_path: Path, output_path: Path, workspace_root: Path) -> dict[str, Any]:
    workspace = _workspace(workspace_root); _within(workspace, input_path.resolve(), "input"); _within(workspace, output_path.resolve(), "output")
    data = _read(input_path, "lineage input")
    if data.get("schema_version") != "artifact-lineage-input/v1": raise ArtifactLineageError("lineage input requires schema_version artifact-lineage-input/v1")
    as_of = _date(data.get("as_of_date"), "as_of_date")
    artifact = _path(workspace, data.get("artifact_path"), "artifact_path")
    if not artifact.is_file(): raise ArtifactLineageError(f"artifact path not found: {artifact}")
    producer = data.get("producer_version")
    if not isinstance(producer, str) or not producer: raise ArtifactLineageError("producer_version is required")
    policy = data.get("freshness_policy")
    if not isinstance(policy, dict) or not isinstance(policy.get("max_age_days"), int) or isinstance(policy["max_age_days"], bool) or policy["max_age_days"] < 0: raise ArtifactLineageError("freshness_policy.max_age_days must be a non-negative integer")
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources: raise ArtifactLineageError("sources must be a non-empty list")
    records = [_source(workspace, source, as_of) for source in sources]
    if len({item["source_id"] for item in records}) != len(records): raise ArtifactLineageError("source_id values must be unique")
    core = {"artifact": {"path": _relative(workspace, artifact), "sha256": _sha(artifact)}, "producer_version": producer, "observed_at": as_of.isoformat(), "freshness_policy": {"max_age_days": policy["max_age_days"]}, "sources": sorted(records, key=lambda item:item["source_id"])}
    result = {"schema_version": SCHEMA_VERSION, "record_type": "ArtifactLineage", "status": "recorded", **core, "reproducibility": {"hash_algorithm":"sha256", "content_hash": _hash(core)}}
    _write_atomic(output_path, result)
    return result

def check_artifact_freshness(lineage_path: Path, workspace_root: Path, as_of_date: str) -> dict[str, Any]:
    workspace = _workspace(workspace_root); _within(workspace, lineage_path.resolve(), "lineage")
    lineage = _read(lineage_path, "lineage")
    if lineage.get("schema_version") != SCHEMA_VERSION: raise ArtifactLineageError("lineage requires schema_version artifact-lineage/v1")
    today = _date(as_of_date, "as_of_date"); observed = _date(lineage.get("observed_at"), "observed_at")
    artifact_record = lineage.get("artifact")
    if not isinstance(artifact_record, dict):
        raise ArtifactLineageError("artifact must be an object")
    sources = lineage.get("sources")
    if not isinstance(sources, list):
        raise ArtifactLineageError("sources must be a list")
    policy = lineage.get("freshness_policy")
    max_age_days = policy.get("max_age_days") if isinstance(policy, dict) else None
    if not isinstance(max_age_days, int) or isinstance(max_age_days, bool) or max_age_days < 0:
        raise ArtifactLineageError("freshness_policy.max_age_days must be a non-negative integer")
    issues=[]; artifact = _path(workspace, artifact_record.get("path"), "artifact.path")
    if not artifact.is_file(): issues.append({"code":"artifact_missing"})
    elif _sha(artifact) != artifact_record.get("sha256"): issues.append({"code":"artifact_changed"})
    for source in sources:
        _validate_lineage_source(source)
        path=_path(workspace, source.get("path"), f"source {source.get('source_id')}")
        if not path.is_file(): issues.append({"code":"source_missing","source_id":source.get("source_id")})
        elif _sha(path)!=source.get("sha256"): issues.append({"code":"rule_pack_changed" if source.get("kind")=="rule_pack" else "source_changed","source_id":source.get("source_id")})
    if (today-observed).days > max_age_days: issues.append({"code":"artifact_stale","age_days":(today-observed).days})
    return {"schema_version":"artifact-freshness-report/v1","record_type":"ArtifactFreshnessReport","status":"fresh" if not issues else "stale","as_of_date":today.isoformat(),"lineage_hash":lineage.get("reproducibility",{}).get("content_hash"),"issues":issues}

def _source(workspace:Path, raw:Any, observed:date)->dict[str,Any]:
    if not isinstance(raw,dict): raise ArtifactLineageError("source must be an object")
    sid,kind,version=raw.get("source_id"),raw.get("kind"),raw.get("version")
    if not isinstance(sid,str) or not sid or kind not in {"input","rule_pack"} or not isinstance(version,str) or not version: raise ArtifactLineageError("source requires source_id, kind input|rule_pack and version")
    path=_path(workspace,raw.get("path"),f"source {sid}")
    if not path.is_file(): raise ArtifactLineageError(f"source path not found: {path}")
    return {"source_id":sid,"kind":kind,"version":version,"path":_relative(workspace,path),"sha256":_sha(path),"observed_at":observed.isoformat()}
def _validate_lineage_source(source:Any)->None:
    if not isinstance(source, dict): raise ArtifactLineageError("source must be an object")
    if not isinstance(source.get("source_id"), str) or not source["source_id"]:
        raise ArtifactLineageError("source_id is required")
    if source.get("kind") not in {"input", "rule_pack"}:
        raise ArtifactLineageError("source kind must be input or rule_pack")
    if not isinstance(source.get("version"), str) or not source["version"]:
        raise ArtifactLineageError("source version is required")
    if not isinstance(source.get("sha256"), str) or len(source["sha256"]) != 64:
        raise ArtifactLineageError("source sha256 is required")
def _workspace(root:Path)->Path:
    value=root.resolve()
    if not value.is_dir(): raise ArtifactLineageError(f"workspace path is not a directory: {root}")
    return value
def _path(workspace:Path, raw:Any, label:str)->Path:
    if not isinstance(raw,str) or not raw: raise ArtifactLineageError(f"{label} must be a relative path")
    if Path(raw).is_absolute() or PureWindowsPath(raw).is_absolute(): raise ArtifactLineageError(f"{label} must be a relative path")
    candidate=(workspace / Path(raw.replace('\\','/'))).resolve(); _within(workspace,candidate,label); return candidate
def _within(workspace:Path,path:Path,label:str)->None:
    try:path.relative_to(workspace)
    except ValueError as exc: raise ArtifactLineageError(f"{label} path is outside workspace: {path}") from exc
def _relative(workspace:Path,path:Path)->str:return path.resolve().relative_to(workspace).as_posix()
def _read(path:Path,label:str)->dict[str,Any]:
    try:value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise ArtifactLineageError(f"cannot read {label}: {path}") from exc
    if not isinstance(value,dict): raise ArtifactLineageError(f"{label} must be an object")
    return value
def _date(value:Any,label:str)->date:
    if not isinstance(value,str): raise ArtifactLineageError(f"{label} must be an ISO date")
    try:return date.fromisoformat(value)
    except ValueError as exc: raise ArtifactLineageError(f"{label} must be an ISO date") from exc
def _sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def _hash(value:Any)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def _write_atomic(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    except OSError as exc:
        raise ArtifactLineageError(f"cannot write lineage sidecar: {path}") from exc
