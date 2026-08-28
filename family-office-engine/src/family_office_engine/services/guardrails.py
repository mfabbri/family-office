"""Versioned deterministic V5.9 safety guardrails; no legal determinations."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

INPUT_SCHEMA_VERSION = "guardrail-assessment-input/v1"
SCHEMA_VERSION = "answer-confidence/v1"


class GuardrailError(ValueError):
    pass


def build_guardrail_assessment(input_path: Path, policy_path: Path, output_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardrailError("Cannot read guardrail input or policy") from exc
    snapshot = assess_guardrails(data, policy)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise GuardrailError(f"Cannot write guardrail assessment: {output_path}") from exc
    return snapshot


def assess_guardrails(data: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema_version") != INPUT_SCHEMA_VERSION or data.get("record_type") != "GuardrailAssessmentInput":
        raise GuardrailError(f"input must be {INPUT_SCHEMA_VERSION} GuardrailAssessmentInput")
    _validate_policy(policy)
    assessment_id = _text(data, "assessment_id")
    request_text = _text(data, "request_text")
    requested_kind = _text(data, "requested_kind")
    if requested_kind not in {"informational", "simulation", "recommendation"}:
        raise GuardrailError("requested_kind must be informational, simulation or recommendation")
    response = data.get("advisory_response")
    if not isinstance(response, dict) or response.get("schema_version") != "advisory-response/v1":
        raise GuardrailError("advisory_response must be advisory-response/v1")
    normalized = " ".join(request_text.casefold().split())
    matches = sorted(term for term in policy["blocked_request_terms"] if term in normalized)
    limitations = list(response.get("limitations", [])) + [{"source": "advisory_response", "kind": "conflict", "detail": item} for item in response.get("conflicts", [])]
    critical = sorted({item.get("detail", {}).get("code") for item in limitations if isinstance(item.get("detail"), dict) and item["detail"].get("code") in policy["critical_gap_codes"]})
    inactive = [citation.get("citation_id") for item in response.get("items", []) for citation in item.get("citations", []) if citation.get("temporal_status") != "active"]
    flags = []
    if matches:
        flags.append({"code": "circumvention_request", "severity": "blocking", "matched_policy_terms": matches})
    if inactive:
        flags.append({"code": "inactive_or_missing_citation", "severity": "blocking", "citation_ids": sorted(set(inactive))})
    if critical:
        flags.append({"code": "critical_evidence_gap", "severity": "high", "gap_codes": critical})
    if matches or inactive:
        status, response_kind, level = "blocked", "refusal", "none"
    elif critical:
        status, response_kind, level = "escalated", "informational_with_limits", "low"
    elif requested_kind == "recommendation":
        status, response_kind, level = "review_required", "recommendation_requires_professional_review", "medium"
    else:
        status, response_kind, level = "allowed", requested_kind, "high" if not limitations else "medium"
    core = {"assessment_id": assessment_id, "request_fingerprint": _hash(normalized), "requested_kind": requested_kind, "response_kind": response_kind, "status": status, "confidence": {"level": level, "facts_count": len(response.get("items", [])), "assumptions_count": sum(item.get("section") == "assumption" for item in response.get("items", [])), "limitations_count": len(limitations), "requires_professional_review": status in {"blocked", "escalated", "review_required"}}, "policy": {"policy_id": policy["policy_id"], "schema_version": policy["schema_version"], "source_refs": policy["source_refs"], "valid_from": policy["valid_from"]}, "flags": flags, "limitations": limitations, "review": {"required": status in {"blocked", "escalated", "review_required"}, "reason": "compliance_or_evidence_review" if status != "allowed" else None}, "data_gaps": [item for item in limitations if item.get("kind") in {"data_gap", "citation_gap"}]}
    return {"schema_version": SCHEMA_VERSION, "record_type": "AnswerConfidence", **core, "reproducibility": {"hash_algorithm": "sha256", "content_hash": _hash(core)}}


def _validate_policy(policy: Any) -> None:
    required = {"schema_version", "record_type", "policy_id", "jurisdictions", "valid_from", "verified_at", "source_refs", "blocked_request_terms", "critical_gap_codes", "limitations"}
    if not isinstance(policy, dict) or policy.get("schema_version") != "orchestration-guardrail-policy/v1" or policy.get("record_type") != "OrchestrationGuardrailPolicy" or not required.issubset(policy):
        raise GuardrailError("invalid orchestration-guardrail-policy/v1")
    if not all(isinstance(policy[field], list) and policy[field] for field in ("source_refs", "blocked_request_terms", "critical_gap_codes")):
        raise GuardrailError("guardrail policy lists must be non-empty")


def _text(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise GuardrailError(f"{field} must be a non-empty string")
    return value.strip()


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
