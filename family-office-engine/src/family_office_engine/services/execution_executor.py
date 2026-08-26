"""Deterministic V5.7 execution of registered plans with reproducible evidence."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from family_office_engine.services.tool_registry import ToolRegistryError, build_tool_registry, invoke_registered_tool

INPUT_SCHEMA_VERSION = "execution-request/v1"
SCHEMA_VERSION = "evidence-bundle/v1"


class ExecutionExecutorError(ValueError):
    pass


def build_evidence_bundle(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Execute a private request and write only its evidence bundle."""
    try:
        value = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExecutionExecutorError(f"Cannot read execution request: {input_path}") from exc
    snapshot = execute_plan(value)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ExecutionExecutorError(f"Cannot write evidence bundle: {output_path}") from exc
    return snapshot


def execute_plan(request: dict[str, Any]) -> dict[str, Any]:
    """Execute a ready plan in topological order through the registry only."""
    if not isinstance(request, dict) or request.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise ExecutionExecutorError(f"schema_version must be {INPUT_SCHEMA_VERSION}")
    if request.get("record_type") != "ExecutionRequest":
        raise ExecutionExecutorError("record_type must be ExecutionRequest")
    execution_id = _required_text(request, "execution_id")
    plan = _validate_plan(request.get("execution_plan"))
    registry = build_tool_registry()
    if plan["tool_registry"] != _lineage(registry):
        raise ExecutionExecutorError("execution plan tool registry lineage is stale; build a new plan")
    _validate_node_contracts(plan["nodes"], registry)
    grants = _validate_grants(request.get("authorization_grants"))
    policy = _validate_policy(request.get("execution_policy", {}))
    values = request.get("binding_values")
    if not isinstance(values, dict):
        raise ExecutionExecutorError("binding_values must be an object")

    records: list[dict[str, Any]] = []
    completed: dict[str, dict[str, Any]] = {}
    source_manifest: list[dict[str, str]] = []
    for node in plan["nodes"]:
        node_id = node["node_id"]
        unmet = [dependency for dependency in node["depends_on"] if completed.get(dependency, {}).get("execution_state") != "succeeded"]
        if unmet:
            record = _skipped_record(node, f"dependency_not_ready: {', '.join(unmet)}")
        elif not set(node["authorization_policy"]).issubset(set(grants.get(node_id, []))):
            record = _skipped_record(node, "authorization_required")
        else:
            parameters, manifest = _resolve_parameters(node, values.get(node_id), completed)
            source_manifest.extend(manifest)
            record = _invoke_node(node, parameters, policy)
        records.append(record)
        completed[node_id] = record

    data_gaps = [gap for record in records for gap in record.get("data_gaps", [])]
    errors = [record["error"] for record in records if "error" in record]
    state_set = {record["execution_state"] for record in records}
    status = "complete" if state_set == {"succeeded"} else "failed" if "succeeded" not in state_set else "partial"
    core = {
        "execution_id": execution_id,
        "execution_plan": {"plan_id": plan["plan_id"], "content_hash": plan["reproducibility"]["content_hash"]},
        "tool_registry": _lineage(registry),
        "policy": {"registered_tools_only": True, "raw_binding_values_persisted": False, "retry_only_read_only_tools": True},
        "sources": sorted(source_manifest, key=lambda item: (item["node_id"], item["parameter"])),
        "nodes": records,
        "errors": errors,
        "data_gaps": data_gaps,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "EvidenceBundle",
        "status": status,
        **core,
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": _hash(core)},
    }


def _validate_plan(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != "execution-plan/v1" or value.get("status") != "ready":
        raise ExecutionExecutorError("execution_plan must be a ready execution-plan/v1")
    if not isinstance(value.get("reproducibility"), dict) or not _is_hash(value["reproducibility"].get("content_hash")):
        raise ExecutionExecutorError("execution_plan must declare a reproducibility content_hash")
    nodes = value.get("nodes")
    if not isinstance(nodes, list) or not nodes or value.get("execution_order") != [node.get("node_id") for node in nodes]:
        raise ExecutionExecutorError("execution_plan nodes must be in declared execution_order")
    if not isinstance(value.get("tool_registry"), dict) or not isinstance(value.get("plan_id"), str):
        raise ExecutionExecutorError("execution_plan lacks registry lineage or plan_id")
    for node in nodes:
        required = {"node_id", "tool_id", "depends_on", "input_bindings", "output_schema_version", "authorization_policy"}
        if not isinstance(node, dict) or not required.issubset(node) or not isinstance(node["depends_on"], list):
            raise ExecutionExecutorError("execution_plan contains an invalid node")
    return value


def _validate_grants(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict) or not all(isinstance(key, str) and isinstance(item, list) and all(isinstance(grant, str) for grant in item) for key, item in value.items()):
        raise ExecutionExecutorError("authorization_grants must map node ids to policy grants")
    return value


def _validate_node_contracts(nodes: list[dict[str, Any]], registry: dict[str, Any]) -> None:
    registered = {tool["tool_id"]: tool for tool in registry["tools"]}
    for node in nodes:
        tool = registered.get(node["tool_id"])
        if tool is None:
            raise ExecutionExecutorError(f"execution plan references unregistered tool: {node['tool_id']}")
        if node["output_schema_version"] != tool["output_schema_version"]:
            raise ExecutionExecutorError(f"execution plan tool contract changed: {node['tool_id']}")
        if node["authorization_policy"] != tool["authorization_policy"]:
            raise ExecutionExecutorError(f"execution plan authorization policy changed: {node['tool_id']}")


def _validate_policy(value: Any) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) - {"max_attempts", "timeout_seconds"}:
        raise ExecutionExecutorError("execution_policy supports only max_attempts and timeout_seconds")
    max_attempts, timeout_seconds = value.get("max_attempts", 1), value.get("timeout_seconds", 30)
    if not isinstance(max_attempts, int) or not 1 <= max_attempts <= 3 or not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 300:
        raise ExecutionExecutorError("execution policy limits are invalid")
    return {"max_attempts": max_attempts, "timeout_seconds": timeout_seconds}


def _resolve_parameters(node: dict[str, Any], supplied: Any, completed: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    if supplied is not None and not isinstance(supplied, dict):
        raise ExecutionExecutorError(f"binding_values.{node['node_id']} must be an object")
    supplied = supplied or {}
    parameters: dict[str, Any] = {}
    manifest: list[dict[str, str]] = []
    for parameter, binding in node["input_bindings"].items():
        source, reference = binding["source"], binding["reference"]
        if source == "prior_node_output":
            prior = completed.get(binding["node_id"])
            if not prior or prior.get("execution_state") != "succeeded":
                raise ExecutionExecutorError(f"prior output is unavailable for {node['node_id']}.{parameter}")
            value = prior["resolved_output_path"]
        else:
            entry = supplied.get(parameter)
            if not isinstance(entry, dict) or set(entry) != {"reference", "value"} or entry["reference"] != reference:
                raise ExecutionExecutorError(f"binding value must match declared reference for {node['node_id']}.{parameter}")
            value = entry["value"]
        parameters[parameter] = value
        manifest.append({"node_id": node["node_id"], "parameter": parameter, "source": source, "reference": reference, "value_hash": _hash(value)})
    if set(supplied) - {name for name, binding in node["input_bindings"].items() if binding["source"] != "prior_node_output"}:
        raise ExecutionExecutorError(f"binding_values contains undeclared inputs for {node['node_id']}")
    return parameters, manifest


def _invoke_node(node: dict[str, Any], parameters: dict[str, Any], policy: dict[str, int]) -> dict[str, Any]:
    max_attempts = policy["max_attempts"] if "read_only" in node["authorization_policy"] else 1
    errors: list[dict[str, str]] = []
    for attempt in range(1, max_attempts + 1):
        started = time.monotonic()
        try:
            invocation = invoke_registered_tool(node["tool_id"], node["output_schema_version"], parameters)
        except (ToolRegistryError, ValueError, OSError) as exc:
            errors.append({"attempt": str(attempt), "type": type(exc).__name__, "message": str(exc)})
            continue
        elapsed_ms = int((time.monotonic() - started) * 1000)
        if elapsed_ms > policy["timeout_seconds"] * 1000:
            return {"node_id": node["node_id"], "tool_id": node["tool_id"], "execution_state": "timed_out", "attempts": attempt, "error": {"type": "Timeout", "message": "declared timeout exceeded"}, "data_gaps": invocation.get("data_gaps", [])}
        output = invocation["output"]
        return {"node_id": node["node_id"], "tool_id": node["tool_id"], "execution_state": "succeeded", "attempts": attempt, "output": output, "output_hash": _hash(output), "resolved_output_path": str(parameters.get("output_path", "")), "data_gaps": invocation.get("data_gaps", [])}
    return {"node_id": node["node_id"], "tool_id": node["tool_id"], "execution_state": "failed", "attempts": max_attempts, "error": errors[-1], "attempt_errors": errors, "data_gaps": []}


def _skipped_record(node: dict[str, Any], reason: str) -> dict[str, Any]:
    return {"node_id": node["node_id"], "tool_id": node["tool_id"], "execution_state": "skipped", "attempts": 0, "error": {"type": "Skipped", "message": reason}, "data_gaps": []}


def _lineage(registry: dict[str, Any]) -> dict[str, str]:
    return {"schema_version": registry["schema_version"], "content_hash": registry["reproducibility"]["content_hash"]}


def _required_text(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ExecutionExecutorError(f"{field} must be a non-empty string")
    return value.strip()


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
