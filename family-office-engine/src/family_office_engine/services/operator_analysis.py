"""Question-first, deterministic operator diagnosis over workspace metadata."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from family_office_engine.services.question_intent import QuestionIntentError, route_question_intent
from family_office_engine.services.local_intent_assist import LocalIntentAssistError, propose_local_intents
from family_office_engine.services.supported_question_catalog import assess_question_capability, build_supported_question_catalog

SCHEMA_VERSION = "operator-analysis/v1"


class OperatorAnalysisError(ValueError):
    """Raised when a question or workspace cannot be assessed safely."""


def analyze_operator_question(
    question: str,
    workspace_root: Path,
    *,
    local_intent_assist: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Diagnose a family-office question without running tools or saving its text."""
    workspace = workspace_root.resolve()
    if not workspace.is_dir():
        raise OperatorAnalysisError(f"workspace path is not a directory: {workspace_root}")
    available = _available_snapshot_versions(workspace)
    try:
        intent = route_question_intent(question, provided_data=available)
    except QuestionIntentError as exc:
        raise OperatorAnalysisError(str(exc)) from exc

    blocking = [problem for problem in intent["problems"] if problem.get("severity") == "blocking"]
    status = "ready_for_analysis" if intent["status"] == "routed" else "needs_information"
    if any(problem["code"] in {"question_unsupported", "prompt_injection_or_tool_instruction"} for problem in blocking):
        status = "not_supported"
    data_gaps = [
        {"code": "required_source_missing", "source": value}
        for value in intent["missing_data"]
    ]
    presentation = _presentation(intent, status, data_gaps)
    core = {
        "question_fingerprint": intent["question_fingerprint"],
        "status": status,
        "selected_intents": intent["selected_intent_ids"],
        "available_facts": [{"schema_version": value, "provenance": "workspace_snapshot"} for value in available],
        "required_tools": sorted({tool for result in _intent_results(intent) for tool in result["required_tools"]}),
        "assumptions": ["Only the presence of relevant workspace data is checked; its contents are not read."],
        "data_gaps": data_gaps,
        "presentation": presentation,
        "limitations": _limitations(intent, status),
        "next_action": _next_action(status, data_gaps),
        "provenance": {
            "question_intent": {
                "schema_version": intent["schema_version"],
                "content_hash": intent["reproducibility"]["content_hash"],
            },
            "catalog": intent["catalog"],
            "workspace_snapshot_schema_versions": available,
        },
        "policy": {
            "question_persisted_verbatim": False,
            "registered_tools_invoked": False,
            "calculates_tax_pension_financial_values": False,
            "workspace_facts_are_metadata_only": True,
        },
        "intent_assist": _intent_assist(question, intent, local_intent_assist),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "OperatorAnalysis",
        **core,
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": _hash(core)},
    }


def _available_snapshot_versions(workspace: Path) -> list[str]:
    snapshots = workspace / "snapshots"
    if not snapshots.is_dir():
        return []
    versions: set[str] = set()
    for path in sorted(snapshots.rglob("*.json")):
        try:
            path.resolve().relative_to(workspace)
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and isinstance(value.get("schema_version"), str):
            versions.add(value["schema_version"])
    return sorted(versions)


def _intent_results(intent: dict[str, Any]) -> list[dict[str, Any]]:
    assessment = intent.get("problems")
    if assessment is None:
        return []
    if not intent["selected_intent_ids"]:
        return []
    return assess_question_capability(intent["selected_intent_ids"], intent["provided_data"])["intent_results"]


def _limitations(intent: dict[str, Any], status: str) -> list[str]:
    limitations = ["This journey diagnoses readiness; it does not execute planning, tax, pension, or financial tools."]
    if status != "ready_for_analysis":
        limitations.append("A deterministic analysis cannot start until blocking gaps are resolved.")
    if any(problem["code"] == "question_unsupported" for problem in intent["problems"]):
        limitations.append("The requested question is outside the registered deterministic capabilities.")
    return limitations


def _next_action(status: str, data_gaps: list[dict[str, str]]) -> str:
    if status == "ready_for_analysis":
        return "No separate analysis-plan command is available in this CLI yet; no calculation has been run."
    if status == "not_supported":
        return "Ask a supported family-office question or request qualified professional review."
    missing = ", ".join(_fact_label(gap["source"]) for gap in data_gaps)
    return f"Add or import the missing sources ({missing}), then rerun 'fo ask'."


def _presentation(intent: dict[str, Any], status: str, data_gaps: list[dict[str, str]]) -> dict[str, Any]:
    catalog = {item["intent_id"]: item for item in build_supported_question_catalog()["intents"]}
    selected = [catalog[item] for item in intent["selected_intent_ids"] if item in catalog]
    required = sorted({source for item in selected for source in item["minimum_data"]})
    available = set(intent["provided_data"])
    facts = [{"label": _fact_label(source), "available": source in available} for source in required]
    if status == "ready_for_analysis":
        status_message = "Your question is understood and the minimum data is available. No analysis or calculation has been run."
    elif status == "not_supported":
        status_message = "This request cannot be handled as a supported family-office decision."
    else:
        status_message = "Your question is understood, but required information is missing. No analysis or calculation has been run."
    return {
        "decision": "; ".join(item["title"] for item in selected) or "No supported family-office decision was recognized.",
        "status_message": status_message,
        "relevant_facts": facts,
        "missing_facts": [_fact_label(gap["source"]) for gap in data_gaps],
        "analysis_executed": False,
        "provenance_summary": "Deterministic question router and supported capability catalog.",
    }


def _fact_label(source: str) -> str:
    labels = {
        "planning-goals/v1": "your planning goals",
        "net-worth/v1": "your current net-worth summary",
        "asset-availability/v1": "availability of your assets",
        "declared residence": "your declared tax residence",
        "source snapshots": "the relevant source snapshots",
        "versioned rule pack": "the applicable versioned rule pack",
        "wealth-strategy-input/v1": "your wealth-strategy inputs",
        "protection-gap-input/v1": "your protection-gap inputs",
        "estate-plan-input/v2": "your estate-plan inputs",
        "real-estate-plan/v1": "your real-estate plan",
        "investment-opportunity-comparison/v1": "your declared investment comparison",
        "tax classification or explicit gap": "the tax classification or an explicit tax gap",
        "household constraints or explicit gap": "the household constraints or an explicit gap",
    }
    return labels.get(source, source.replace("-", " ").replace("/v1", "").replace("/v2", ""))


def _hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _intent_assist(question: str, intent: dict[str, Any], configuration: dict[str, Any] | None) -> dict[str, Any]:
    fallback = {"router": "question-intent/v1", "selected_intent_ids": intent["selected_intent_ids"]}
    if configuration is None:
        return {"enabled": False, "status": "not_requested", "fallback": fallback}
    if any(problem["code"] == "prompt_injection_or_tool_instruction" for problem in intent["problems"]):
        return {"enabled": True, "status": "rejected_injection", "fallback": fallback}
    try:
        proposal = propose_local_intents(question, **configuration)
    except LocalIntentAssistError as exc:
        return {"enabled": True, "status": "unavailable_or_invalid", "reason": str(exc), "fallback": fallback}
    assessment = assess_question_capability(proposal.intent_ids, intent["provided_data"])
    matches_router = proposal.intent_ids == intent["selected_intent_ids"]
    status = "validated" if matches_router and assessment["status"] == "available" else "conflicts_deterministic_route"
    return {
        "enabled": True,
        "status": status,
        "proposal": {"intent_ids": proposal.intent_ids, "confidence": proposal.confidence},
        "deterministic_validation": {
            "catalog_schema_version": assessment["catalog"]["schema_version"],
            "catalog_content_hash": assessment["catalog"]["content_hash"],
            "matches_lexical_router": matches_router,
            "capability_status": assessment["status"],
            "tool_invocation_allowed": False,
        },
        "fallback": fallback,
    }
