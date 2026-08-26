"""Deterministic V5.5 planner; it validates plans but never invokes tools."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from family_office_engine.services.supported_question_catalog import build_supported_question_catalog
from family_office_engine.services.tool_registry import build_tool_registry
from family_office_engine.services.question_intent import route_question_intent

INPUT_SCHEMA_VERSION = "execution-plan-input/v1"
SCHEMA_VERSION = "execution-plan/v1"
RECORD_TYPE = "ExecutionPlan"
_BINDING_SOURCES = {"workspace_path", "rule_pack", "prior_node_output", "citation_index"}
_SENSITIVITY = {"ordinary", "sensitive"}
_SENSITIVE_AUTHORIZATION = "explicit_user_consent"


class ExecutionPlanError(ValueError):
    pass


def build_execution_plan(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Read a declared plan input, validate it and write an inspectable plan.

    This boundary intentionally does not import or call the registry invocation
    adapter. Execution is owned by the later executor increment.
    """
    data = _read_json(input_path)
    snapshot = plan_execution(data)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ExecutionPlanError(f"Cannot write execution plan: {output_path}") from exc
    return snapshot


def plan_execution(data: dict[str, Any]) -> dict[str, Any]:
    """Validate a catalog-authorized DAG without executing any node."""
    if not isinstance(data, dict):
        raise ExecutionPlanError("execution plan input must be a JSON object")
    if data.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise ExecutionPlanError(f"schema_version must be {INPUT_SCHEMA_VERSION}")
    if data.get("record_type") != "ExecutionPlanInput":
        raise ExecutionPlanError("record_type must be ExecutionPlanInput")
    plan_id = _required_text(data, "plan_id")
    question_intent = _validate_question_intent(data.get("question_intent"))
    registry = build_tool_registry()
    catalog = build_supported_question_catalog()
    _validate_catalog_lineage(question_intent, catalog)
    tools = {item["tool_id"]: item for item in registry["tools"]}
    allowed_tools = _allowed_tools(question_intent["selected_intent_ids"], catalog)
    nodes = _validate_nodes(data.get("nodes"), tools, allowed_tools)
    ordered_node_ids = _topological_order(nodes)
    node_by_id = {node["node_id"]: node for node in nodes}
    planned_nodes = [_planned_node(node_by_id[node_id], tools[node_by_id[node_id]["tool_id"]]) for node_id in ordered_node_ids]
    core = {
        "plan_id": plan_id,
        "question_intent": {
            "schema_version": question_intent["schema_version"],
            "content_hash": question_intent["reproducibility"]["content_hash"],
            "selected_intent_ids": question_intent["selected_intent_ids"],
        },
        "catalog": {"schema_version": catalog["schema_version"], "content_hash": catalog["reproducibility"]["content_hash"]},
        "tool_registry": {"schema_version": registry["schema_version"], "content_hash": registry["reproducibility"]["content_hash"]},
        "nodes": planned_nodes,
        "execution_order": ordered_node_ids,
        "policy": {
            "registered_tools_only": True,
            "planner_invokes_tools": False,
            "planner_calculates_tax_pension_financial_values": False,
            "sensitive_inputs_require_explicit_user_consent": True,
            "raw_input_values_are_not_accepted": True,
        },
        "data_gaps": [],
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "status": "ready",
        **core,
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": _content_hash(core)},
    }


def demo_execution_plan_input() -> dict[str, Any]:
    """Return a synthetic, routed retirement DAG for the short CLI smoke path."""
    question_intent = route_question_intent(
        "Pensione e uscita dal lavoro",
        provided_data=["pension-scenario/v1", "work-exit-feasibility-input/v1", "versioned pension rule pack"],
    )
    return {
        "schema_version": INPUT_SCHEMA_VERSION,
        "record_type": "ExecutionPlanInput",
        "plan_id": "synthetic-retirement-work-exit-plan",
        "question_intent": question_intent,
        "nodes": [
            _demo_node("pension_scenario", "planning.pension_scenario.build", [], ["input_path", "output_path"]),
            _demo_node("spanish_theoretical", "planning.spanish_eu_theoretical_pension.build", [], ["input_path", "rule_pack_path", "output_path"]),
            _demo_node(
                "eu_pro_rata",
                "planning.it_es_eu_pension_pro_rata.build",
                ["spanish_theoretical"],
                ["input_path", "rule_pack_path", "output_path"],
                prior_output_parameter="spanish_theoretical_snapshot_path",
                prior_node_id="spanish_theoretical",
            ),
            _demo_node(
                "work_exit",
                "planning.work_exit_feasibility.build",
                ["eu_pro_rata"],
                ["input_path", "rule_pack_path", "output_path"],
                prior_output_parameter="pro_rata_snapshot_path",
                prior_node_id="eu_pro_rata",
            ),
        ],
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExecutionPlanError(f"Cannot read execution plan input: {path}") from exc
    if not isinstance(value, dict):
        raise ExecutionPlanError("execution plan input must be a JSON object")
    return value


def _demo_node(
    node_id: str,
    tool_id: str,
    depends_on: list[str],
    parameters: list[str],
    *,
    prior_output_parameter: str | None = None,
    prior_node_id: str | None = None,
) -> dict[str, Any]:
    bindings = {
        parameter: {
            "source": "rule_pack" if parameter == "rule_pack_path" else "workspace_path",
            "reference": f"planning/{node_id}-{parameter}.json",
            "sensitivity": "ordinary",
        }
        for parameter in parameters
    }
    if prior_output_parameter is not None and prior_node_id is not None:
        bindings[prior_output_parameter] = {
            "source": "prior_node_output",
            "reference": f"{prior_node_id}.output",
            "node_id": prior_node_id,
            "sensitivity": "ordinary",
        }
    return {"node_id": node_id, "tool_id": tool_id, "depends_on": depends_on, "input_bindings": bindings}


def _validate_question_intent(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ExecutionPlanError("question_intent must be a question-intent/v1 object")
    if value.get("schema_version") != "question-intent/v1":
        raise ExecutionPlanError("question_intent must use question-intent/v1")
    if value.get("status") != "routed":
        raise ExecutionPlanError("question_intent must be routed before planning")
    selected = value.get("selected_intent_ids")
    if not isinstance(selected, list) or not selected or not all(isinstance(item, str) and item for item in selected):
        raise ExecutionPlanError("question_intent must declare selected_intent_ids")
    if value.get("tool_invocations") not in (None, []):
        raise ExecutionPlanError("question_intent must not contain tool invocations")
    policy = value.get("policy")
    if not isinstance(policy, dict) or policy.get("tool_invocation_allowed") is not False:
        raise ExecutionPlanError("question_intent policy must keep tool invocation disabled")
    reproducibility = value.get("reproducibility")
    if not isinstance(reproducibility, dict) or not _is_hash(reproducibility.get("content_hash")):
        raise ExecutionPlanError("question_intent must declare a reproducibility content_hash")
    return value


def _validate_catalog_lineage(question_intent: dict[str, Any], catalog: dict[str, Any]) -> None:
    source_catalog = question_intent.get("catalog")
    if not isinstance(source_catalog, dict):
        raise ExecutionPlanError("question_intent must declare catalog lineage")
    if source_catalog.get("schema_version") != catalog["schema_version"] or source_catalog.get("content_hash") != catalog["reproducibility"]["content_hash"]:
        raise ExecutionPlanError("question_intent catalog lineage is stale; route the question again")


def _allowed_tools(intent_ids: list[str], catalog: dict[str, Any]) -> set[str]:
    by_id = {intent["intent_id"]: intent for intent in catalog["intents"]}
    unknown = sorted(set(intent_ids) - set(by_id))
    if unknown:
        raise ExecutionPlanError(f"question_intent contains unsupported intents: {', '.join(unknown)}")
    return {tool_id for intent_id in intent_ids for tool_id in by_id[intent_id]["required_tools"]}


def _validate_nodes(value: Any, tools: dict[str, dict[str, Any]], allowed_tools: set[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ExecutionPlanError("nodes must be a non-empty list")
    nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for node in value:
        if not isinstance(node, dict):
            raise ExecutionPlanError("each node must be a JSON object")
        node_id = _required_text(node, "node_id")
        if node_id in node_ids:
            raise ExecutionPlanError(f"duplicate node_id: {node_id}")
        node_ids.add(node_id)
        tool_id = _required_text(node, "tool_id")
        if tool_id not in tools:
            raise ExecutionPlanError(f"tool is not registered: {tool_id}")
        if tool_id not in allowed_tools:
            raise ExecutionPlanError(f"tool is outside selected catalog intents: {tool_id}")
        depends_on = node.get("depends_on", [])
        if not isinstance(depends_on, list) or not all(isinstance(item, str) and item for item in depends_on):
            raise ExecutionPlanError(f"depends_on must be a list of node ids for {node_id}")
        if len(depends_on) != len(set(depends_on)) or node_id in depends_on:
            raise ExecutionPlanError(f"invalid dependency declaration for {node_id}")
        bindings = node.get("input_bindings")
        _validate_bindings(node_id, bindings, tools[tool_id])
        nodes.append({"node_id": node_id, "tool_id": tool_id, "depends_on": sorted(depends_on), "input_bindings": bindings})
    known = {node["node_id"] for node in nodes}
    missing = sorted({dependency for node in nodes for dependency in node["depends_on"] if dependency not in known})
    if missing:
        raise ExecutionPlanError(f"dependencies reference missing nodes: {', '.join(missing)}")
    for node in nodes:
        for binding in node["input_bindings"].values():
            if binding["source"] == "prior_node_output" and binding.get("node_id") not in node["depends_on"]:
                raise ExecutionPlanError(f"prior_node_output binding must depend on its source node for {node['node_id']}")
    return nodes


def _validate_bindings(node_id: str, value: Any, tool: dict[str, Any]) -> None:
    if not isinstance(value, dict):
        raise ExecutionPlanError(f"input_bindings must be an object for {node_id}")
    allowed = set(tool["required_parameters"]) | set(tool["optional_parameters"])
    missing = sorted(set(tool["required_parameters"]) - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        raise ExecutionPlanError(f"missing declared input bindings for {node_id}: {', '.join(missing)}")
    if unknown:
        raise ExecutionPlanError(f"unknown input bindings for {node_id}: {', '.join(unknown)}")
    for parameter, binding in value.items():
        if not isinstance(binding, dict) or set(binding) - {"source", "reference", "sensitivity", "authorization", "node_id"}:
            raise ExecutionPlanError(f"input binding {parameter} for {node_id} must declare only metadata")
        source = binding.get("source")
        if source not in _BINDING_SOURCES:
            raise ExecutionPlanError(f"input binding {parameter} for {node_id} has unsupported source")
        _required_text(binding, "reference")
        sensitivity = binding.get("sensitivity", "ordinary")
        if sensitivity not in _SENSITIVITY:
            raise ExecutionPlanError(f"input binding {parameter} for {node_id} has unsupported sensitivity")
        if sensitivity == "sensitive" and binding.get("authorization") != _SENSITIVE_AUTHORIZATION:
            raise ExecutionPlanError(f"sensitive input is not authorized for {node_id}.{parameter}")
        if source == "prior_node_output" and not isinstance(binding.get("node_id"), str):
            raise ExecutionPlanError(f"prior_node_output binding requires node_id for {node_id}.{parameter}")


def _topological_order(nodes: list[dict[str, Any]]) -> list[str]:
    remaining = {node["node_id"]: set(node["depends_on"]) for node in nodes}
    order: list[str] = []
    while remaining:
        ready = sorted(node_id for node_id, dependencies in remaining.items() if not dependencies)
        if not ready:
            raise ExecutionPlanError("execution plan contains a dependency cycle")
        order.extend(ready)
        for node_id in ready:
            del remaining[node_id]
        for dependencies in remaining.values():
            dependencies.difference_update(ready)
    return order


def _planned_node(node: dict[str, Any], tool: dict[str, Any]) -> dict[str, Any]:
    return {
        **node,
        "input_schema_version": tool["input_schema_version"],
        "output_schema_version": tool["output_schema_version"],
        "risk_level": tool["risk_level"],
        "authorization_policy": tool["authorization_policy"],
        "execution_state": "not_executed",
        "checks": [
            "tool_registered",
            "catalog_intent_authorized",
            "required_inputs_declared",
            "dependencies_resolved",
            "sensitive_inputs_authorized",
        ],
        "stop_criteria": [
            "missing_declared_input",
            "dependency_not_ready",
            "authorization_required",
            "tool_contract_changed",
        ],
    }


def _required_text(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ExecutionPlanError(f"{field} must be a non-empty string")
    return value.strip()


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
