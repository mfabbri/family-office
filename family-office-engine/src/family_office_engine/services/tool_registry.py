from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from family_office_engine.services.citation_index import search_citation_index
from family_office_engine.services.cross_border_it_es_dossier import build_cross_border_it_es_dossier
from family_office_engine.services.estate_plan import build_estate_plan
from family_office_engine.services.it_es_eu_pension_pro_rata import build_it_es_eu_pension_pro_rata
from family_office_engine.services.it_es_foreign_assets import build_it_es_foreign_assets
from family_office_engine.services.it_es_pension_tax_classification import classify_it_es_pension_tax
from family_office_engine.services.liquidity_plan import build_liquidity_plan
from family_office_engine.services.pension_contribution_options import build_pension_contribution_options
from family_office_engine.services.pension_scenario import build_pension_scenario
from family_office_engine.services.protection_gap import build_protection_gap
from family_office_engine.services.real_estate_plan import build_real_estate_plan
from family_office_engine.services.spanish_eu_theoretical_pension import build_spanish_eu_theoretical_pension
from family_office_engine.services.spanish_pension_net_it_resident import build_spanish_pension_net_it_resident
from family_office_engine.services.tax_aware_portfolio import build_tax_aware_portfolio
from family_office_engine.services.wealth_strategy import build_wealth_strategy
from family_office_engine.services.investment_opportunity_comparison import build_investment_opportunity_comparison
from family_office_engine.services.work_exit_feasibility import build_work_exit_feasibility
from family_office_engine.services.guardrails import build_guardrail_assessment

SCHEMA_VERSION = "tool-registry/v1"
SNAPSHOT_RECORD_TYPE = "ToolRegistrySnapshot"
INVOCATION_RECORD_TYPE = "ToolInvocationResult"
SUPPORTED_RISK_LEVELS = {"low", "medium", "high"}
SUPPORTED_AUTHORIZATION = {"read_only", "workspace_write", "rule_pack_required", "professional_review_required"}


class ToolRegistryError(ValueError):
    pass


@dataclass(frozen=True)
class RegisteredTool:
    tool_id: str
    title: str
    callable_ref: Callable[..., dict[str, Any]]
    input_schema_version: str
    output_schema_version: str
    required_parameters: tuple[str, ...]
    optional_parameters: tuple[str, ...]
    prerequisites: tuple[str, ...]
    risk_level: str
    authorization_policy: tuple[str, ...]
    notes: str


TOOL_REGISTRY: tuple[RegisteredTool, ...] = (
    RegisteredTool(
        tool_id="knowledge.citations.search",
        title="Search citation-index/v1",
        callable_ref=search_citation_index,
        input_schema_version="citation-search-query/v1",
        output_schema_version="citation-search/v1",
        required_parameters=("index_path",),
        optional_parameters=("query", "jurisdiction", "topic", "as_of_date", "include_inactive"),
        prerequisites=("citation-index/v1",),
        risk_level="low",
        authorization_policy=("read_only",),
        notes="Returns only catalogued citations with temporal status and explicit corpus gaps.",
    ),
    RegisteredTool(
        tool_id="orchestration.guardrails.evaluate",
        title="Evaluate answer-confidence/v1 guardrails",
        callable_ref=build_guardrail_assessment,
        input_schema_version="guardrail-assessment-input/v1",
        output_schema_version="answer-confidence/v1",
        required_parameters=("input_path", "policy_path", "output_path"),
        optional_parameters=(),
        prerequisites=("orchestration-guardrail-policy/v1", "advisory-response/v1"),
        risk_level="high",
        authorization_policy=("workspace_write", "rule_pack_required", "professional_review_required"),
        notes="Refuses compliance circumvention and escalates evidence gaps; it makes no legal determination.",
    ),
    RegisteredTool(
        tool_id="planning.liquidity_plan.build",
        title="Build liquidity-plan/v1",
        callable_ref=build_liquidity_plan,
        input_schema_version="liquidity-plan-input/v1",
        output_schema_version="liquidity-plan/v1",
        required_parameters=("input_path", "output_path"),
        optional_parameters=("net_worth_snapshot_path", "asset_availability_snapshot_path"),
        prerequisites=("planning-goals/v1", "net-worth/v1", "asset-availability/v1"),
        risk_level="medium",
        authorization_policy=("workspace_write", "professional_review_required"),
        notes="Uses declared liquidity inputs and source snapshots; does not calculate FX or recommendations.",
    ),
    RegisteredTool(
        tool_id="planning.pension_contribution_options.build",
        title="Build pension-contribution-options/v1",
        callable_ref=build_pension_contribution_options,
        input_schema_version="pension-contribution-input/v1",
        output_schema_version="pension-contribution-options/v1",
        required_parameters=("input_path", "rule_pack_path", "output_path"),
        optional_parameters=(),
        prerequisites=("it.pension-contribution-deduction.2026.v1",),
        risk_level="high",
        authorization_policy=("workspace_write", "rule_pack_required", "professional_review_required"),
        notes="Uses a versioned rule pack and declared marginal rate; does not calculate full IRPEF.",
    ),
    RegisteredTool(
        tool_id="planning.tax_aware_portfolio.build",
        title="Build tax-aware-portfolio/v1",
        callable_ref=build_tax_aware_portfolio,
        input_schema_version="tax-aware-portfolio-input/v1",
        output_schema_version="tax-aware-portfolio/v1",
        required_parameters=("input_path", "rule_pack_path", "output_path"),
        optional_parameters=(),
        prerequisites=("it.tax-aware-investment.2026.v1",),
        risk_level="high",
        authorization_policy=("workspace_write", "rule_pack_required", "professional_review_required"),
        notes="Compares declared options using rule-pack rates and costs; does not generate investment advice.",
    ),
    RegisteredTool(
        tool_id="planning.it_es_pension_tax_classification.classify",
        title="Classify it-es-pension-tax-classification/v1",
        callable_ref=classify_it_es_pension_tax,
        input_schema_version="it-es-pension-tax-classification-input/v1",
        output_schema_version="it-es-pension-tax-classification/v1",
        required_parameters=("input_path", "rule_pack_path", "output_path"),
        optional_parameters=(),
        prerequisites=("it-es.pension-tax-classification.2026.v1",),
        risk_level="high",
        authorization_policy=("workspace_write", "rule_pack_required", "professional_review_required"),
        notes="Classifies taxing power qualitatively; does not calculate net tax.",
    ),
    RegisteredTool(
        tool_id="planning.spanish_pension_net_it_resident.build",
        title="Build spanish-pension-net-it-resident/v1",
        callable_ref=build_spanish_pension_net_it_resident,
        input_schema_version="spanish-pension-net-it-resident-input/v1",
        output_schema_version="spanish-pension-net-it-resident/v1",
        required_parameters=("input_path", "rule_pack_path", "output_path"),
        optional_parameters=("pension_income_snapshot_path", "classification_snapshot_path"),
        prerequisites=("pension-income/v1", "it-es-pension-tax-classification/v1"),
        risk_level="high",
        authorization_policy=("workspace_write", "rule_pack_required", "professional_review_required"),
        notes="Calculates declared net flow components with explicit fiscal inputs and gaps.",
    ),
    RegisteredTool(
        tool_id="planning.it_es_foreign_assets.build",
        title="Build it-es-foreign-assets/v1",
        callable_ref=build_it_es_foreign_assets,
        input_schema_version="it-es-foreign-assets-input/v1",
        output_schema_version="it-es-foreign-assets/v1",
        required_parameters=("input_path", "rule_pack_path", "output_path"),
        optional_parameters=(),
        prerequisites=("it-es.foreign-asset-monitoring.2026.v2",),
        risk_level="high",
        authorization_policy=("workspace_write", "rule_pack_required", "professional_review_required"),
        notes="Determines monitoring obligations from declared assets; does not prepare tax returns.",
    ),
    RegisteredTool(
        tool_id="planning.cross_border_it_es.build",
        title="Build cross-border-it-es/v1",
        callable_ref=build_cross_border_it_es_dossier,
        input_schema_version="source-snapshots",
        output_schema_version="cross-border-it-es/v1",
        required_parameters=("output_path",),
        optional_parameters=(
            "pension_scenario_snapshot_path",
            "pension_income_snapshot_path",
            "pension_tax_classification_snapshot_path",
            "spanish_pension_net_snapshot_path",
            "eu_pension_pro_rata_snapshot_path",
            "foreign_assets_snapshot_path",
        ),
        prerequisites=("pension-scenario/v1", "it-es-foreign-assets/v1"),
        risk_level="high",
        authorization_policy=("workspace_write", "professional_review_required"),
        notes="Composes cross-border evidence without recalculating upstream pension or tax values.",
    ),
    RegisteredTool(
        tool_id="planning.pension_scenario.build",
        title="Build pension-scenario/v1",
        callable_ref=build_pension_scenario,
        input_schema_version="pension-scenario/v1",
        output_schema_version="pension-scenario/v1",
        required_parameters=("input_path", "output_path"),
        optional_parameters=(),
        prerequisites=(),
        risk_level="medium",
        authorization_policy=("workspace_write", "professional_review_required"),
        notes="Records explicit future assumptions; does not calculate pensions or taxes.",
    ),
    RegisteredTool(
        tool_id="planning.real_estate_plan.build",
        title="Build real-estate-plan/v1",
        callable_ref=build_real_estate_plan,
        input_schema_version="real-estate-plan/v1",
        output_schema_version="real-estate-plan/v1",
        required_parameters=("input_path", "output_path"),
        optional_parameters=(),
        prerequisites=(),
        risk_level="medium",
        authorization_policy=("workspace_write", "professional_review_required"),
        notes="Compares declared alternatives and costs; taxes are explicit inputs or gaps.",
    ),
    RegisteredTool(
        tool_id="planning.protection_gap.build",
        title="Build protection-gap/v1",
        callable_ref=build_protection_gap,
        input_schema_version="protection-gap/v1",
        output_schema_version="protection-gap/v1",
        required_parameters=("input_path", "output_path"),
        optional_parameters=(),
        prerequisites=(),
        risk_level="medium",
        authorization_policy=("workspace_write", "professional_review_required"),
        notes="Separates risk coverage from investment value; does not provide insurance advice.",
    ),
    RegisteredTool(
        tool_id="planning.estate_plan.build",
        title="Build estate-plan/v2",
        callable_ref=build_estate_plan,
        input_schema_version="estate-plan/v2",
        output_schema_version="estate-plan/v2",
        required_parameters=("input_path", "rule_pack_path", "output_path"),
        optional_parameters=(),
        prerequisites=("it.estate-plan.2026.v2",),
        risk_level="high",
        authorization_policy=("workspace_write", "rule_pack_required", "professional_review_required"),
        notes="Flags civil-law conflicts and tax estimates for covered cases; does not generate legal instruments.",
    ),
    RegisteredTool(
        tool_id="planning.spanish_eu_theoretical_pension.build",
        title="Build spanish-eu-theoretical-pension/v1",
        callable_ref=build_spanish_eu_theoretical_pension,
        input_schema_version="spanish-eu-theoretical-pension-input/v1",
        output_schema_version="spanish-eu-theoretical-pension/v1",
        required_parameters=("input_path", "rule_pack_path", "output_path"),
        optional_parameters=("reconciliation_snapshot_path",),
        prerequisites=("eu.es.spanish-eu-theoretical-pension.2026.v1",),
        risk_level="high",
        authorization_policy=("workspace_write", "rule_pack_required", "professional_review_required"),
        notes="Calculates a planning estimate from versioned rules and declared Spanish bases.",
    ),
    RegisteredTool(
        tool_id="planning.it_es_eu_pension_pro_rata.build",
        title="Build it-es-eu-pension-pro-rata/v1",
        callable_ref=build_it_es_eu_pension_pro_rata,
        input_schema_version="it-es-eu-pension-pro-rata-input/v1",
        output_schema_version="it-es-eu-pension-pro-rata/v1",
        required_parameters=("input_path", "rule_pack_path", "output_path"),
        optional_parameters=("spanish_theoretical_snapshot_path",),
        prerequisites=("eu.it-es.pension-coordination.2026.v2",),
        risk_level="high",
        authorization_policy=("workspace_write", "rule_pack_required", "professional_review_required"),
        notes="Separates national entitlement, EU totalization and Spanish pro-rata share.",
    ),
    RegisteredTool(
        tool_id="planning.work_exit_feasibility.build",
        title="Build work-exit-feasibility/v1",
        callable_ref=build_work_exit_feasibility,
        input_schema_version="work-exit-feasibility-input/v1",
        output_schema_version="work-exit-feasibility/v1",
        required_parameters=("input_path", "rule_pack_path", "output_path"),
        optional_parameters=("inps_snapshot_path", "pro_rata_snapshot_path"),
        prerequisites=("it.inps-theoretical-pension.2026.v1", "it-es-eu-pension-pro-rata/v1"),
        risk_level="high",
        authorization_policy=("workspace_write", "rule_pack_required", "professional_review_required"),
        notes="Finds feasible exit dates from deterministic pension and spending evidence; no LLM calculations.",
    ),
    RegisteredTool(
        tool_id="planning.investment_opportunity_comparison.build",
        title="Build investment-opportunity-comparison/v1",
        callable_ref=build_investment_opportunity_comparison,
        input_schema_version="investment-opportunity-comparison/v1",
        output_schema_version="investment-opportunity-comparison/v1",
        required_parameters=("input_path", "output_path"),
        optional_parameters=(),
        prerequisites=("investment-opportunity/v1",),
        risk_level="high",
        authorization_policy=("workspace_write", "professional_review_required"),
        notes="Compares only declared investment scenarios and benchmarks; does not infer returns, tax treatment or recommendations.",
    ),
    RegisteredTool(
        tool_id="planning.wealth_strategy.build",
        title="Build wealth-strategy/v1",
        callable_ref=build_wealth_strategy,
        input_schema_version="wealth-strategy-input/v1",
        output_schema_version="wealth-strategy/v1",
        required_parameters=("input_path", "output_path"),
        optional_parameters=(
            "planning_goals_snapshot_path",
            "liquidity_plan_snapshot_path",
            "decumulation_strategy_snapshot_path",
            "pension_contribution_options_snapshot_path",
            "tax_aware_portfolio_snapshot_path",
            "cross_border_it_es_snapshot_path",
            "real_estate_plan_snapshot_path",
            "protection_gap_snapshot_path",
            "estate_plan_snapshot_path",
            "work_exit_snapshot_path",
            "investment_opportunity_comparison_snapshot_paths",
        ),
        prerequisites=("liquidity-plan/v1", "tax-aware-portfolio/v1", "estate-plan/v2"),
        risk_level="high",
        authorization_policy=("workspace_write", "professional_review_required"),
        notes="Composes declared strategy packages from V4 evidence; does not create opaque recommendations.",
    ),
)


def build_tool_registry(output_path: Path | None = None) -> dict[str, Any]:
    tools = [_tool_record(tool) for tool in TOOL_REGISTRY]
    _validate_registry_records(tools)
    core = {
        "registry_id": "family-office-local-tools",
        "tool_count": len(tools),
        "tools": tools,
        "policy": {
            "llm_may_invoke_only_registered_tools": True,
            "llm_must_not_calculate_tax_pension_financial_values": True,
            "workspace_writes_require_explicit_output_path": True,
            "professional_review_required_for_high_risk_outputs": True,
        },
        "data_gaps": [],
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "complete",
        **core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(core),
        },
        "notes": (
            "Tool registry V1 exposes deterministic local capabilities for future AI orchestration. "
            "It does not run LLM calculations and does not discover unregistered internal functions."
        ),
    }
    if output_path is not None:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except OSError as exc:
            raise ToolRegistryError(f"Cannot write tool registry snapshot: {output_path}") from exc
    return snapshot


def invoke_registered_tool(tool_id: str, requested_output_schema_version: str, parameters: dict[str, Any]) -> dict[str, Any]:
    tool = get_registered_tool(tool_id)
    if tool.output_schema_version != requested_output_schema_version:
        raise ToolRegistryError(
            f"Tool {tool_id} produces {tool.output_schema_version}, not {requested_output_schema_version}."
        )
    if not isinstance(parameters, dict):
        raise ToolRegistryError("parameters must be a JSON object")
    allowed = set(tool.required_parameters) | set(tool.optional_parameters)
    missing = [name for name in tool.required_parameters if name not in parameters]
    unknown = sorted(set(parameters) - allowed)
    if missing:
        raise ToolRegistryError(f"Missing required parameters for {tool_id}: {', '.join(missing)}")
    if unknown:
        raise ToolRegistryError(f"Unknown parameters for {tool_id}: {', '.join(unknown)}")
    normalized = {name: _coerce_path(value, name) for name, value in parameters.items()}
    output = tool.callable_ref(**normalized)
    if not isinstance(output, dict):
        raise ToolRegistryError(f"Tool {tool_id} returned a non-object result")
    if output.get("schema_version") != tool.output_schema_version:
        raise ToolRegistryError(
            f"Tool {tool_id} returned {output.get('schema_version')}, expected {tool.output_schema_version}"
        )
    return {
        "schema_version": "tool-invocation/v1",
        "record_type": INVOCATION_RECORD_TYPE,
        "status": output.get("status", "complete"),
        "tool": {
            "tool_id": tool.tool_id,
            "requested_output_schema_version": requested_output_schema_version,
            "actual_output_schema_version": output.get("schema_version"),
        },
        "output": output,
        "data_gaps": output.get("data_gaps", []),
    }


def get_registered_tool(tool_id: str) -> RegisteredTool:
    for tool in TOOL_REGISTRY:
        if tool.tool_id == tool_id:
            return tool
    raise ToolRegistryError(f"Unknown registered tool: {tool_id}")


def _tool_record(tool: RegisteredTool) -> dict[str, Any]:
    return {
        "tool_id": tool.tool_id,
        "title": tool.title,
        "input_schema_version": tool.input_schema_version,
        "output_schema_version": tool.output_schema_version,
        "required_parameters": list(tool.required_parameters),
        "optional_parameters": list(tool.optional_parameters),
        "prerequisites": list(tool.prerequisites),
        "risk_level": tool.risk_level,
        "authorization_policy": list(tool.authorization_policy),
        "notes": tool.notes,
    }


def _validate_registry_records(tools: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for tool in tools:
        tool_id = tool["tool_id"]
        if tool_id in seen:
            raise ToolRegistryError(f"Duplicate tool id: {tool_id}")
        seen.add(tool_id)
        if tool["risk_level"] not in SUPPORTED_RISK_LEVELS:
            raise ToolRegistryError(f"Unsupported risk level for {tool_id}: {tool['risk_level']}")
        unsupported = sorted(set(tool["authorization_policy"]) - SUPPORTED_AUTHORIZATION)
        if unsupported:
            raise ToolRegistryError(f"Unsupported authorization policy for {tool_id}: {', '.join(unsupported)}")
        if not tool["output_schema_version"].endswith(("/v1", "/v2")):
            raise ToolRegistryError(f"Unsupported output schema version for {tool_id}: {tool['output_schema_version']}")


def _coerce_path(value: Any, name: str) -> Any:
    if name.endswith("_paths"):
        if not isinstance(value, list) or not all(isinstance(item, (str, Path)) for item in value):
            raise ToolRegistryError(f"{name} must be a list of path strings")
        return [Path(item) for item in value]
    if name.endswith("_path") or name in {"input_path", "output_path", "rule_pack_path"}:
        if not isinstance(value, (str, Path)):
            raise ToolRegistryError(f"{name} must be a path string")
        return Path(value)
    return value


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
