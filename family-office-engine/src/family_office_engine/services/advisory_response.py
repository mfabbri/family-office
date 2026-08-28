"""Deterministic V5.8 composer from evidence and indexed citations only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

INPUT_SCHEMA_VERSION = "response-composition-input/v1"
SCHEMA_VERSION = "advisory-response/v1"
_SECTIONS = {"executive_summary", "alternative", "motivation", "number", "assumption", "risk", "action"}


class AdvisoryResponseError(ValueError):
    pass


def build_advisory_response(input_path: Path, output_path: Path) -> dict[str, Any]:
    try:
        value = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdvisoryResponseError(f"Cannot read response composition input: {input_path}") from exc
    snapshot = compose_advisory_response(value)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise AdvisoryResponseError(f"Cannot write advisory response: {output_path}") from exc
    return snapshot


def compose_advisory_response(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise AdvisoryResponseError(f"schema_version must be {INPUT_SCHEMA_VERSION}")
    if data.get("record_type") != "ResponseCompositionInput":
        raise AdvisoryResponseError("record_type must be ResponseCompositionInput")
    response_id = _required_text(data, "response_id")
    evidence = _validate_evidence(data.get("evidence_bundle"))
    citations = _validate_citations(data.get("citation_search"))
    items = _compose_items(data.get("items"), evidence, citations)
    conflicts = _conflicts(items)
    limitations = _limitations(evidence, data["citation_search"])
    status = "complete" if not limitations and not conflicts else "complete_with_limitations"
    core = {
        "response_id": response_id,
        "evidence_bundle": {"execution_id": evidence["execution_id"], "content_hash": evidence["reproducibility"]["content_hash"]},
        "citation_search": {"content_hash": data["citation_search"]["reproducibility"]["content_hash"], "source_index": data["citation_search"].get("source_index", {})},
        "items": items,
        "conflicts": conflicts,
        "limitations": limitations,
        "policy": {
            "evidence_bundle_only": True,
            "indexed_active_citations_only": True,
            "numbers_are_resolved_from_evidence": True,
            "composer_calculates_tax_pension_financial_values": False,
        },
    }
    return {"schema_version": SCHEMA_VERSION, "record_type": "AdvisoryResponse", "status": status, **core, "reproducibility": {"hash_algorithm": "sha256", "content_hash": _hash(core)}}


def _validate_evidence(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != "evidence-bundle/v1" or value.get("record_type") != "EvidenceBundle":
        raise AdvisoryResponseError("evidence_bundle must be evidence-bundle/v1")
    if not isinstance(value.get("reproducibility"), dict) or not _is_hash(value["reproducibility"].get("content_hash")):
        raise AdvisoryResponseError("evidence_bundle must declare a reproducibility content_hash")
    if not isinstance(value.get("execution_id"), str) or not isinstance(value.get("nodes"), list):
        raise AdvisoryResponseError("evidence_bundle lacks execution evidence")
    return value


def _validate_citations(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict) or value.get("schema_version") != "citation-search/v1":
        raise AdvisoryResponseError("citation_search must be citation-search/v1")
    if not isinstance(value.get("reproducibility"), dict) or not _is_hash(value["reproducibility"].get("content_hash")):
        raise AdvisoryResponseError("citation_search must declare a reproducibility content_hash")
    records = value.get("citations")
    if not isinstance(records, list):
        raise AdvisoryResponseError("citation_search citations must be a list")
    citations: dict[str, dict[str, Any]] = {}
    for citation in records:
        if not isinstance(citation, dict) or not isinstance(citation.get("citation_id"), str):
            raise AdvisoryResponseError("citation_search contains an invalid citation")
        if citation.get("temporal_status") != "active":
            raise AdvisoryResponseError(f"citation is not active: {citation['citation_id']}")
        citations[citation["citation_id"]] = citation
    return citations


def _compose_items(value: Any, evidence: dict[str, Any], citations: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise AdvisoryResponseError("items must be a non-empty list")
    result: list[dict[str, Any]] = []
    ids: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {"item_id", "section", "label", "evidence", "citation_ids"}:
            raise AdvisoryResponseError("each item must declare only item_id, section, label, evidence and citation_ids")
        item_id, section, label = _required_text(item, "item_id"), _required_text(item, "section"), _required_text(item, "label")
        if item_id in ids or section not in _SECTIONS:
            raise AdvisoryResponseError("item_id must be unique and section supported")
        ids.add(item_id)
        evidence_ref = item["evidence"]
        if not isinstance(evidence_ref, dict) or set(evidence_ref) != {"node_id", "pointer"}:
            raise AdvisoryResponseError(f"item {item_id} must identify node_id and JSON pointer")
        node_id, pointer = _required_text(evidence_ref, "node_id"), _required_text(evidence_ref, "pointer")
        node = next((node for node in evidence["nodes"] if node.get("node_id") == node_id), None)
        if not isinstance(node, dict) or node.get("execution_state") != "succeeded" or "output" not in node:
            raise AdvisoryResponseError(f"item {item_id} references unavailable evidence node: {node_id}")
        resolved = _json_pointer(node["output"], pointer)
        citation_ids = item["citation_ids"]
        if not isinstance(citation_ids, list) or len(citation_ids) != len(set(citation_ids)) or not all(isinstance(citation_id, str) for citation_id in citation_ids):
            raise AdvisoryResponseError(f"item {item_id} citation_ids must be a unique list")
        if section != "assumption" and not citation_ids:
            raise AdvisoryResponseError(f"item {item_id} requires a specific active citation")
        missing = sorted(set(citation_ids) - set(citations))
        if missing:
            raise AdvisoryResponseError(f"item {item_id} references unavailable citations: {', '.join(missing)}")
        result.append({"item_id": item_id, "section": section, "descriptor": {"text": label, "status": "unverified_descriptor"}, "value": resolved, "evidence": {"node_id": node_id, "pointer": pointer, "output_hash": node.get("output_hash")}, "citations": [_citation_record(citations[citation_id]) for citation_id in citation_ids]})
    return result


def _limitations(evidence: dict[str, Any], citation_search: dict[str, Any]) -> list[dict[str, Any]]:
    limitations: list[dict[str, Any]] = []
    for gap in evidence.get("data_gaps", []):
        limitations.append({"source": "evidence_bundle", "kind": "data_gap", "detail": gap})
    for error in evidence.get("errors", []):
        limitations.append({"source": "evidence_bundle", "kind": "execution_error", "detail": error})
    for gap in citation_search.get("data_gaps", []):
        limitations.append({"source": "citation_search", "kind": "citation_gap", "detail": gap})
    return limitations


def _conflicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_label: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_label.setdefault(item["descriptor"]["text"], []).append(item)
    conflicts = []
    for label, matches in by_label.items():
        serialized_values = {json.dumps(item["value"], sort_keys=True, ensure_ascii=True) for item in matches}
        if len(serialized_values) > 1:
            conflicts.append({"descriptor": label, "item_ids": [item["item_id"] for item in matches], "reason": "conflicting_evidence_values"})
    return conflicts


def _citation_record(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value.get(key) for key in ("citation_id", "title", "url", "official_reference", "authority_level", "temporal_status")}


def _json_pointer(value: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise AdvisoryResponseError("evidence pointer must be a JSON Pointer starting with /")
    current = value
    for part in pointer[1:].split("/"):
        token = part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            raise AdvisoryResponseError(f"evidence pointer does not resolve: {pointer}")
    return current


def _required_text(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise AdvisoryResponseError(f"{field} must be a non-empty string")
    return value.strip()


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
