from __future__ import annotations

import hashlib
import json
from typing import Any

from family_office_engine.services.tool_registry import build_tool_registry

CATALOG_SCHEMA_VERSION = "supported-question-catalog/v1"
ASSESSMENT_SCHEMA_VERSION = "question-capability-assessment/v1"


class SupportedQuestionCatalogError(ValueError):
    pass


def build_supported_question_catalog() -> dict[str, Any]:
    """Return the versioned, deterministic V5.3 capability declaration.

    This catalog deliberately accepts intent identifiers rather than natural-language
    questions. Text classification and entity extraction are owned by V5.4.
    """
    tools = build_tool_registry()["tools"]
    intents = _intents()
    _validate_intents(intents, {tool["tool_id"] for tool in tools})
    core = {
        "catalog_id": "family-office-supported-questions",
        "tool_registry_schema_version": "tool-registry/v1",
        "intents": intents,
        "policy": {
            "natural_language_routing": "not_available_until_question-intent/v1",
            "llm_must_not_calculate_tax_pension_financial_values": True,
            "missing_data_must_be_explicit": True,
            "professional_review_is_not_a_tool_invocation": True,
            "planned_capabilities_must_not_be_presented_as_executable": True,
        },
        "data_gaps": [],
    }
    return {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "record_type": "SupportedQuestionCatalog",
        "status": "complete",
        **core,
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": _content_hash(core)},
    }


def assess_question_capability(intent_ids: list[str], provided_data: list[str] | None = None) -> dict[str, Any]:
    """Assess explicitly selected catalog intents without routing or invoking a tool."""
    if not isinstance(intent_ids, list) or not all(isinstance(item, str) for item in intent_ids):
        raise SupportedQuestionCatalogError("intent_ids must be a list of strings")
    if provided_data is not None and (not isinstance(provided_data, list) or not all(isinstance(item, str) for item in provided_data)):
        raise SupportedQuestionCatalogError("provided_data must be a list of strings")

    catalog = build_supported_question_catalog()
    by_id = {intent["intent_id"]: intent for intent in catalog["intents"]}
    normalized_ids = [intent_id.strip() for intent_id in intent_ids if intent_id.strip()]
    selected = [by_id[intent_id] for intent_id in normalized_ids if intent_id in by_id]
    unknown = sorted(set(normalized_ids) - set(by_id))
    duplicates = sorted({intent_id for intent_id in normalized_ids if normalized_ids.count(intent_id) > 1})
    supplied = set(provided_data or [])

    results = []
    for intent in selected:
        missing = sorted(item for item in intent["minimum_data"] if item not in supplied)
        results.append(
            {
                "intent_id": intent["intent_id"],
                "capability_status": intent["capability_status"],
                "required_tools": intent["required_tools"],
                "expected_outputs": intent["expected_outputs"],
                "missing_data": missing,
                "escalation": intent["escalation"],
            }
        )

    problems: list[dict[str, Any]] = []
    if not normalized_ids:
        problems.append({"code": "intent_selection_missing", "severity": "blocking"})
    if unknown:
        problems.append({"code": "intent_unsupported", "severity": "blocking", "intent_ids": unknown})
    if duplicates:
        problems.append({"code": "intent_selection_duplicate", "severity": "blocking", "intent_ids": duplicates})
    collisions = _collisions(selected)
    if collisions:
        problems.append({"code": "intent_overlap_requires_clarification", "severity": "blocking", "pairs": collisions})
    planned = [item["intent_id"] for item in selected if item["capability_status"] == "planned"]
    if planned:
        problems.append({"code": "capability_planned_not_executable", "severity": "blocking", "intent_ids": planned})
    unavailable = [item["intent_id"] for item in selected if item["capability_status"] == "unavailable"]
    if unavailable:
        problems.append({"code": "professional_or_out_of_scope_request", "severity": "blocking", "intent_ids": unavailable})
    missing_data = sorted({item for result in results for item in result["missing_data"]})
    if missing_data:
        problems.append({"code": "minimum_data_missing", "severity": "blocking", "fields": missing_data})

    status = "available" if not problems else "needs_clarification"
    core = {
        "selected_intent_ids": normalized_ids,
        "intent_results": results,
        "problems": problems,
        "executable": status == "available",
        "data_gaps": [problem for problem in problems if problem["code"] == "minimum_data_missing"],
    }
    return {
        "schema_version": ASSESSMENT_SCHEMA_VERSION,
        "record_type": "QuestionCapabilityAssessment",
        "status": status,
        **core,
        "catalog": {"schema_version": CATALOG_SCHEMA_VERSION, "content_hash": catalog["reproducibility"]["content_hash"]},
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": _content_hash(core)},
    }


def _intents() -> list[dict[str, Any]]:
    return [
        _intent("knowledge_and_sources", "Knowledge and source research", "available", ["knowledge.citations.search"], ["citation-index/v1"], ["citation-search/v1"], "low", "Informational only; cite temporal status and corpus gaps."),
        _intent("liquidity_and_cashflow", "Liquidity and cash-flow planning", "available", ["planning.liquidity_plan.build"], ["planning-goals/v1", "net-worth/v1", "asset-availability/v1"], ["liquidity-plan/v1"], "medium", "Professional review required before an action recommendation."),
        _intent("retirement_and_work_exit", "Retirement, pension and work-exit planning", "available", ["planning.pension_scenario.build", "planning.spanish_eu_theoretical_pension.build", "planning.it_es_eu_pension_pro_rata.build", "planning.work_exit_feasibility.build"], ["pension-scenario/v1", "work-exit-feasibility-input/v1", "versioned pension rule pack"], ["pension-scenario/v1", "spanish-eu-theoretical-pension/v1", "it-es-eu-pension-pro-rata/v1", "work-exit-feasibility/v1"], "high", "Use registered pension tools and rule packs; professional review is required."),
        _intent("cross_border_tax_and_reporting", "Italy-Spain tax and reporting", "available", ["planning.it_es_pension_tax_classification.classify", "planning.spanish_pension_net_it_resident.build", "planning.it_es_foreign_assets.build", "planning.cross_border_it_es.build"], ["declared residence", "source snapshots", "versioned rule pack"], ["it-es-pension-tax-classification/v1", "spanish-pension-net-it-resident/v1", "it-es-foreign-assets/v1", "cross-border-it-es/v1"], "high", "No filing or binding legal/tax advice; professional review is required."),
        _intent("portfolio_and_contributions", "Portfolio and pension-contribution options", "available", ["planning.tax_aware_portfolio.build", "planning.pension_contribution_options.build"], ["declared options", "versioned rule pack"], ["tax-aware-portfolio/v1", "pension-contribution-options/v1"], "high", "Declared alternatives only; professional review is required."),
        _intent("wealth_protection_and_estate", "Wealth strategy, protection and estate planning", "available", ["planning.wealth_strategy.build", "planning.protection_gap.build", "planning.estate_plan.build"], ["wealth-strategy-input/v1", "protection-gap-input/v1", "estate-plan-input/v2"], ["wealth-strategy/v1", "protection-gap/v1", "estate-plan/v2"], "high", "Does not create legal instruments; professional review is required."),
        _intent("real_estate_hold_rent_sell", "Real-estate hold, rent or sell comparison", "available", ["planning.real_estate_plan.build"], ["real-estate-plan/v1"], ["real-estate-plan/v1"], "medium", "Uses declared costs and tax inputs/gaps; not an income-property investment analysis."),
        _intent("investment_opportunity", "Income-producing property or rentable movable asset", "planned", [], ["investment-opportunity/v1", "declared assumptions", "tax classification or explicit gap"], ["investment-opportunity/v1", "investment-opportunity-comparison/v1"], "high", "Unavailable until V5.3a-V5.3h; do not infer returns, taxes, occupancy or activity classification."),
        _intent("professional_advice_or_out_of_scope", "Binding professional advice or unsupported request", "unavailable", [], [], [], "high", "Refer to the appropriate professional; no deterministic result is claimed."),
    ]


def _intent(intent_id: str, title: str, capability_status: str, required_tools: list[str], minimum_data: list[str], expected_outputs: list[str], risk_level: str, escalation: str) -> dict[str, Any]:
    return {"intent_id": intent_id, "title": title, "capability_status": capability_status, "required_tools": required_tools, "minimum_data": minimum_data, "expected_outputs": expected_outputs, "risk_level": risk_level, "escalation": escalation}


def _validate_intents(intents: list[dict[str, Any]], registered_tool_ids: set[str]) -> None:
    intent_ids = [intent["intent_id"] for intent in intents]
    if len(intent_ids) != len(set(intent_ids)):
        raise SupportedQuestionCatalogError("Catalog contains duplicate intent ids")
    unknown_tools = sorted({tool for intent in intents for tool in intent["required_tools"] if tool not in registered_tool_ids})
    if unknown_tools:
        raise SupportedQuestionCatalogError(f"Catalog references unregistered tools: {', '.join(unknown_tools)}")
    available_tools = [tool for intent in intents if intent["capability_status"] == "available" for tool in intent["required_tools"]]
    duplicate_tools = sorted({tool for tool in available_tools if available_tools.count(tool) > 1})
    if duplicate_tools:
        raise SupportedQuestionCatalogError(f"Catalog classifies registered tools more than once: {', '.join(duplicate_tools)}")
    covered_tools = set(available_tools)
    missing_tools = sorted(registered_tool_ids - covered_tools)
    if missing_tools:
        raise SupportedQuestionCatalogError(f"Catalog does not classify registered tools: {', '.join(missing_tools)}")
    if any(intent["capability_status"] == "planned" and intent["required_tools"] for intent in intents):
        raise SupportedQuestionCatalogError("Planned capabilities must not expose executable tools")


def _collisions(selected: list[dict[str, Any]]) -> list[list[str]]:
    selected_ids = {intent["intent_id"] for intent in selected}
    pairs = [{"retirement_and_work_exit", "cross_border_tax_and_reporting"}]
    return [sorted(pair) for pair in pairs if pair <= selected_ids]


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
