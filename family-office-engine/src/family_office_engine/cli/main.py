import argparse
import calendar
import hashlib
import json
import os
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Mapping

from family_office_engine.ingestion.manual_assumptions import (
    AssumptionsImportError,
    import_assumptions,
    prepare_assumptions_input,
)
from family_office_engine.ingestion.fonte import (
    FonteImportError,
    import_fonte,
    import_fonte_source_bundle,
)
from family_office_engine.ingestion.inps_pension import (
    InpsPensionImportError,
    import_inps_pension,
)
from family_office_engine.ingestion.spanish_contribution_history import (
    SpanishContributionHistoryImportError,
    import_spanish_contribution_history,
)
from family_office_engine.ingestion.investments import (
    InvestmentsImportError,
    import_investments,
)
from family_office_engine.ingestion.bank_insurance import (
    BankInsuranceImportError,
    import_bank_insurance,
)
from family_office_engine.ingestion.payroll import (
    PayrollImportError,
    diagnose_payroll_input,
    import_payroll,
)
from family_office_engine.ingestion.tax_documents import (
    TaxDocumentsImportError,
    diagnose_tax_documents,
    import_tax_documents,
)
from family_office_engine.services.net_worth import NetWorthError, consolidate_net_worth
from family_office_engine.services.earned_income_cashflow import (
    EarnedIncomeCashflowError,
    build_earned_income_cashflow,
)
from family_office_engine.services.assumptions_readiness import (
    AssumptionsReadinessError,
    check_assumptions_readiness,
)
from family_office_engine.services.document_inventory import (
    DocumentInventoryError,
    DocumentOrganizationError,
    build_document_inventory,
    organize_documents,
)
from family_office_engine.services.tax_events import TaxEventsError, generate_impatriati_events
from family_office_engine.services.tax_calculation import TaxCalculationError, calculate_tax
from family_office_engine.services.tax_reconciliation import (
    TaxReconciliationError,
    reconcile_tax_sources,
)
from family_office_engine.services.spanish_contribution_reconciliation import (
    SpanishContributionReconciliationError,
    reconcile_spanish_contributions,
)
from family_office_engine.services.spanish_statutory_pension import (
    SpanishStatutoryPensionError,
    estimate_spanish_statutory_pension,
)
from family_office_engine.services.eu_pension_coordination import (
    EuPensionCoordinationError,
    coordinate_it_es_pensions,
)
from family_office_engine.services.it_es_eu_pension_pro_rata import (
    ItEsEuPensionProRataError,
    build_it_es_eu_pension_pro_rata,
)
from family_office_engine.services.spanish_eu_theoretical_pension import (
    SpanishEuTheoreticalPensionError,
    build_spanish_eu_theoretical_pension,
)
from family_office_engine.services.pension_income import (
    PensionIncomeError,
    compose_pension_income,
)
from family_office_engine.services.lifecycle_expenses import (
    LifecycleExpensesError,
    build_lifecycle_expenses,
)
from family_office_engine.services.decision_scenario import (
    DecisionScenarioError,
    compose_decision_scenario,
)
from family_office_engine.services.decision_outcome import (
    DecisionOutcomeError,
    build_decision_outcome,
)
from family_office_engine.services.sensitivity_analysis import (
    SensitivityAnalysisError,
    build_sensitivity_analysis,
)
from family_office_engine.services.decision_score import (
    DecisionScoreError,
    build_decision_score,
)
from family_office_engine.services.decision_dossier import (
    DecisionDossierError,
    build_decision_dossier,
)
from family_office_engine.services.rita_options import RitaOptionsError, optimize_rita_options
from family_office_engine.services.estate_baseline import EstateBaselineError, build_estate_baseline
from family_office_engine.services.estate_plan import EstatePlanError, build_estate_plan
from family_office_engine.services.household_facts import HouseholdFactsError, import_household_facts
from family_office_engine.services.ownership_graph import OwnershipGraphError, import_ownership_graph
from family_office_engine.services.asset_availability import (
    AssetAvailabilityError,
    import_asset_availability,
    validate_asset_availability,
)
from family_office_engine.services.timeline_events import TimelineEventsError, import_timeline_events
from family_office_engine.services.planning_goals import PlanningGoalsError, import_planning_goals, validate_planning_goals
from family_office_engine.services.liquidity_plan import (
    LiquidityPlanError,
    build_liquidity_plan,
    validate_liquidity_plan_input,
)
from family_office_engine.services.decumulation_strategy import (
    DecumulationStrategyError,
    build_decumulation_strategy,
    validate_decumulation_policy_set,
)
from family_office_engine.services.pension_contribution_options import (
    PensionContributionOptionsError,
    build_pension_contribution_options,
    validate_pension_contribution_input,
)
from family_office_engine.services.tax_aware_portfolio import (
    TaxAwarePortfolioError,
    build_tax_aware_portfolio,
)
from family_office_engine.services.it_es_pension_tax_classification import (
    ItEsPensionTaxClassificationError,
    classify_it_es_pension_tax,
)
from family_office_engine.services.spanish_pension_net_it_resident import (
    SpanishPensionNetItResidentError,
    build_spanish_pension_net_it_resident,
)
from family_office_engine.services.it_es_foreign_assets import (
    ItEsForeignAssetsError,
    build_it_es_foreign_assets,
)
from family_office_engine.services.cross_border_it_es_dossier import (
    CrossBorderItEsDossierError,
    build_cross_border_it_es_dossier,
)
from family_office_engine.services.pension_scenario import (
    PensionScenarioError,
    build_pension_scenario,
)
from family_office_engine.services.real_estate_plan import (
    RealEstatePlanError,
    build_real_estate_plan,
)
from family_office_engine.services.protection_gap import (
    ProtectionGapError,
    build_protection_gap,
)
from family_office_engine.services.work_exit_feasibility import (
    WorkExitFeasibilityError,
    build_work_exit_feasibility,
)
from family_office_engine.services.wealth_strategy import WealthStrategyError, build_wealth_strategy
from family_office_engine.services.tool_registry import (
    ToolRegistryError,
    build_tool_registry,
)
from family_office_engine.simulation.retirement import (
    RetirementSimulationError,
    simulate_retirement,
)
from family_office_engine.simulation.monte_carlo import (
    DEFAULT_SEED as DEFAULT_MONTE_CARLO_SEED,
    DEFAULT_SIMULATIONS as DEFAULT_MONTE_CARLO_SIMULATIONS,
    MonteCarloSimulationError,
    simulate_monte_carlo,
)
from family_office_engine.simulation.scenario_comparison import (
    DEFAULT_TARGET_AGES as DEFAULT_SCENARIO_TARGET_AGES,
    ScenarioComparisonError,
    compare_retirement_scenarios,
)
from family_office_engine.reporting.report import ReportBuildError, build_retirement_report
from family_office_engine.reporting.dashboard import DashboardBuildError, build_decision_dashboard

REPOS = {
    "bootstrap": "family-office-bootstrap",
    "engine": "family-office-engine",
    "rules": "family-office-rules",
    "knowledge": "family-office-knowledge",
    "workspace": "family-office-workspace",
}

ENGINE_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_ROOT = ENGINE_ROOT.parent


def default_assumptions_input() -> Path:
    return resolve_repo("workspace") / "assumptions" / "base-assumptions.json"


def default_assumptions_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "manual-assumptions.snapshot.json"


def default_assumptions_template() -> Path:
    return resolve_repo("workspace") / "assumptions" / "base-assumptions.template.json"


def default_assumptions_draft() -> Path:
    return resolve_repo("workspace") / "assumptions" / "base-assumptions.draft.json"


def default_assumptions_checklist() -> Path:
    return resolve_repo("workspace") / "assumptions" / "assumptions-input-checklist.md"


def default_assumptions_readiness_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "assumptions-readiness.snapshot.json"


def default_fonte_input() -> Path:
    return resolve_repo("workspace") / "inbox" / "fonte.csv"


def default_inbox_path() -> Path:
    return resolve_repo("workspace") / "inbox"


def default_document_inventory_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "document-inventory.snapshot.json"


def default_documents_path() -> Path:
    return resolve_repo("workspace") / "documents"


def default_document_manifest_output() -> Path:
    return resolve_repo("workspace") / "documents" / "manifest.json"


def default_inps_pension_input() -> Path:
    documents_path = resolve_repo("workspace") / "documents" / "pensione" / "inps"
    if documents_path.exists():
        return documents_path
    return resolve_repo("workspace") / "inbox" / "pensione"


def default_inps_pension_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "inps-pension.snapshot.json"


def default_spanish_pension_input() -> Path:
    documents_path = resolve_repo("workspace") / "documents" / "pensione" / "spagna"
    if documents_path.exists():
        return documents_path
    return resolve_repo("workspace") / "inbox" / "pensione" / "spagna"


def default_spanish_pension_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "spanish-contribution-history.snapshot.json"


def default_spanish_contribution_reconciliation_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "spanish-contribution-reconciliation.snapshot.json"


def default_spanish_statutory_pension_rule_pack() -> Path:
    return resolve_repo("rules") / "spain" / "statutory-retirement-general.json"


def default_spanish_statutory_pension_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "spanish-statutory-pension.snapshot.json"


def default_eu_pension_coordination_rule_pack() -> Path:
    return resolve_repo("rules") / "cross-border" / "eu-pension-coordination-it-es.json"


def default_it_es_pension_tax_classification_rule_pack() -> Path:
    return resolve_repo("rules") / "cross-border" / "it-es-pension-tax-classification.json"


def default_spanish_pension_net_it_resident_rule_pack() -> Path:
    return resolve_repo("rules") / "cross-border" / "spanish-pension-net-it-resident.json"


def default_it_es_foreign_assets_rule_pack() -> Path:
    return resolve_repo("rules") / "cross-border" / "it-es-foreign-asset-monitoring-v2.json"


def default_cross_border_it_es_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cross-border-it-es.snapshot.json"


def default_cross_border_it_es_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-cross-border-it-es.synthetic.snapshot.json"


def default_pension_scenario_input() -> Path:
    return resolve_repo("workspace") / "planning" / "pension-scenario.json"


def default_pension_scenario_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "pension-scenario-sample.json"


def default_pension_scenario_sample_snapshot() -> Path:
    return resolve_repo("engine") / "examples" / "pension-scenario-snapshot-sample.json"


def default_pension_scenario_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "pension-scenario.snapshot.json"


def default_pension_scenario_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-pension-scenario.synthetic.snapshot.json"


def default_real_estate_plan_input() -> Path:
    return resolve_repo("workspace") / "planning" / "real-estate-plan.json"


def default_real_estate_plan_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "real-estate-plan-sample.json"


def default_real_estate_plan_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "real-estate-plan.snapshot.json"


def default_real_estate_plan_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-real-estate-plan.synthetic.snapshot.json"


def default_protection_gap_input() -> Path:
    return resolve_repo("workspace") / "planning" / "protection-gap.json"


def default_protection_gap_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "protection-gap-sample.json"


def default_protection_gap_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "protection-gap.snapshot.json"


def default_protection_gap_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-protection-gap.synthetic.snapshot.json"


def default_eu_pension_coordination_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "eu-pension-coordination-it-es.snapshot.json"


def default_it_es_eu_pension_pro_rata_input() -> Path:
    return resolve_repo("workspace") / "planning" / "it-es-eu-pension-pro-rata-input.json"


def default_it_es_eu_pension_pro_rata_draft() -> Path:
    return resolve_repo("workspace") / "planning" / "it-es-eu-pension-pro-rata-input.draft.json"


def default_it_es_eu_pension_pro_rata_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "it-es-eu-pension-pro-rata-input-sample.json"


def default_it_es_eu_pension_pro_rata_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "it-es-eu-pension-pro-rata.snapshot.json"


def default_it_es_eu_pension_pro_rata_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-it-es-eu-pension-pro-rata.synthetic.snapshot.json"


def default_spanish_eu_theoretical_pension_rule_pack() -> Path:
    return resolve_repo("rules") / "cross-border" / "spanish-eu-theoretical-pension.json"


def default_spanish_eu_theoretical_pension_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "spanish-eu-theoretical-pension-pro-rata-input-sample.json"


def default_spanish_eu_theoretical_pension_sample_reconciliation() -> Path:
    return resolve_repo("engine") / "examples" / "spanish-eu-theoretical-pension-reconciliation-sample.json"


def default_spanish_eu_theoretical_pension_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "spanish-eu-theoretical-pension.snapshot.json"


def default_spanish_eu_theoretical_pension_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-spanish-eu-theoretical-pension.synthetic.snapshot.json"


def default_or_existing_spanish_theoretical_snapshot(explicit_path: Path | None) -> Path | None:
    if explicit_path is not None:
        return explicit_path
    default_path = default_spanish_eu_theoretical_pension_output()
    return default_path if default_path.exists() else None


def default_pension_income_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "pension-income.snapshot.json"


def default_work_exit_input() -> Path:
    return resolve_repo("workspace") / "planning" / "work-exit-feasibility.json"


def default_work_exit_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "work-exit-feasibility-sample.json"


def default_work_exit_rule_pack() -> Path:
    return resolve_repo("rules") / "italy" / "2026" / "inps-theoretical-pension.json"


def default_work_exit_sample_inps_snapshot() -> Path:
    return resolve_repo("engine") / "examples" / "work-exit-inps-snapshot-sample.json"


def default_work_exit_sample_pro_rata_snapshot() -> Path:
    return resolve_repo("engine") / "examples" / "work-exit-pro-rata-sample.json"


def default_work_exit_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "work-exit-feasibility.snapshot.json"


def default_work_exit_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-work-exit.synthetic.snapshot.json"


def default_lifecycle_expenses_input() -> Path:
    return resolve_repo("workspace") / "household" / "lifecycle-expenses.json"


def default_lifecycle_expenses_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "lifecycle-expenses.snapshot.json"


def default_investments_italy_input() -> Path:
    return resolve_repo("workspace") / "documents" / "investimenti" / "italia"


def default_investments_spain_input() -> Path:
    return resolve_repo("workspace") / "documents" / "investimenti" / "spagna"


def default_investments_directa_input() -> Path:
    return resolve_repo("workspace") / "documents" / "investimenti" / "directa"


def default_investments_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "investments.snapshot.json"


def default_bank_documents_input() -> Path:
    return resolve_repo("workspace") / "documents" / "banca"


def default_insurance_documents_input() -> Path:
    return resolve_repo("workspace") / "documents" / "polizze"


def default_bank_insurance_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "bank-insurance.snapshot.json"


def default_payroll_input() -> Path:
    documents_path = resolve_repo("workspace") / "documents" / "redditi" / "buste-paga"
    if documents_path.exists():
        return documents_path
    return resolve_repo("workspace") / "inbox" / "bustepaga"


def default_payroll_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "payroll.snapshot.json"


def default_earned_income_cashflow_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "earned-income-cashflow.snapshot.json"


def default_investments_snapshot() -> Path:
    return default_investments_output()


def default_bank_insurance_snapshot() -> Path:
    return default_bank_insurance_output()


def default_fonte_position_pdf() -> Path:
    return default_fonte_documents_dir() / "posizione-generale.pdf"


def default_fonte_contributions_xlsx() -> Path:
    return default_fonte_documents_dir() / "importi-versati.xlsx"


def default_fonte_inbox_dir() -> Path:
    return resolve_repo("workspace") / "inbox" / "fonte"


def default_fonte_documents_dir() -> Path:
    documents_path = resolve_repo("workspace") / "documents" / "fonte"
    if documents_path.exists():
        return documents_path
    legacy_case_path = resolve_repo("workspace") / "documents" / "Fonte"
    if legacy_case_path.exists():
        return legacy_case_path
    return default_fonte_inbox_dir()


def default_fonte_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "fonte.snapshot.json"


def default_net_worth_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "net-worth.snapshot.json"


def default_tax_events_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "tax-events.snapshot.json"


def default_italy_tax_rule_pack() -> Path:
    return resolve_repo("rules") / "italy" / "2026" / "irpef-national.json"


def default_pension_contribution_rule_pack() -> Path:
    return resolve_repo("rules") / "italy" / "2026" / "pension-contribution-deduction.json"


def default_tax_aware_investment_rule_pack() -> Path:
    return resolve_repo("rules") / "italy" / "2026" / "tax-aware-investment.json"


def default_tax_calculation_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "tax-calculation.snapshot.json"


def default_tax_documents_cu_input() -> Path:
    documents_path = resolve_repo("workspace") / "documents" / "redditi" / "cu"
    if documents_path.exists():
        return documents_path
    return resolve_repo("workspace") / "inbox" / "cu"


def default_tax_documents_declarations_input() -> Path:
    documents_path = resolve_repo("workspace") / "documents" / "dichiarazioni"
    if documents_path.exists():
        return documents_path
    return resolve_repo("workspace") / "inbox" / "dichiarazioni"


def default_tax_documents_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "tax-documents.snapshot.json"


def default_tax_reconciliation_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "tax-reconciliation.snapshot.json"


def default_rita_rule_pack() -> Path:
    return resolve_repo("rules") / "italy" / "current" / "rita.yaml"


def default_rita_options_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "rita-options.snapshot.json"


def default_estate_rule_pack() -> Path:
    return resolve_repo("rules") / "succession" / "italy-current.json"


def default_estate_plan_rule_pack() -> Path:
    return resolve_repo("rules") / "succession" / "italy-2026-v2.json"


def default_estate_baseline_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "estate-baseline.snapshot.json"


def default_estate_plan_input() -> Path:
    return resolve_repo("workspace") / "planning" / "estate-plan.json"


def default_estate_plan_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "estate-plan-sample.json"


def default_estate_plan_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "estate-plan.snapshot.json"


def default_estate_plan_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-estate-plan.synthetic.snapshot.json"


def default_wealth_strategy_input() -> Path:
    return resolve_repo("workspace") / "planning" / "wealth-strategy-input.json"


def default_wealth_strategy_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "wealth-strategy-input-sample.json"


def default_wealth_strategy_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "wealth-strategy.snapshot.json"


def default_wealth_strategy_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-wealth-strategy.synthetic.snapshot.json"


def default_tool_registry_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "tool-registry.snapshot.json"


def default_household_facts_input() -> Path:
    return resolve_repo("workspace") / "household" / "household-facts.json"


def default_household_facts_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "household-facts-sample.json"


def default_household_facts_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "household-facts.snapshot.json"


def default_ownership_graph_input() -> Path:
    return resolve_repo("workspace") / "household" / "ownership-beneficiaries.json"


def default_ownership_graph_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "ownership-beneficiary-graph.snapshot.json"


def default_asset_availability_input() -> Path:
    return resolve_repo("workspace") / "household" / "asset-availability.json"


def default_asset_availability_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "asset-availability-sample.json"


def default_asset_availability_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "asset-availability.snapshot.json"


def default_timeline_events_input() -> Path:
    return resolve_repo("workspace") / "household" / "timeline-events.json"


def default_timeline_events_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "timeline-events-sample.json"


def default_timeline_events_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "timeline-events.snapshot.json"


def default_timeline_events_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-timeline-events.synthetic.snapshot.json"


def default_timeline_policy() -> Path:
    return resolve_repo("rules") / "timeline" / "default-overlap-policy.json"


def default_planning_goals_input() -> Path:
    return resolve_repo("workspace") / "household" / "planning-goals.json"


def default_planning_goals_draft() -> Path:
    return resolve_repo("workspace") / "household" / "planning-goals.draft.json"


def default_planning_goals_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "planning-goals-sample.json"


def default_planning_goals_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "planning-goals.snapshot.json"


def default_planning_goals_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-planning-goals.synthetic.snapshot.json"


def default_liquidity_plan_input() -> Path:
    return resolve_repo("workspace") / "planning" / "liquidity-plan-input.json"


def default_liquidity_plan_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "liquidity-plan-input-sample.json"


def default_liquidity_plan_sample_net_worth() -> Path:
    return resolve_repo("engine") / "examples" / "liquidity-plan-net-worth-sample.json"


def default_liquidity_plan_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "liquidity-plan.snapshot.json"


def default_liquidity_plan_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-liquidity-plan.synthetic.snapshot.json"


def default_decumulation_policy_set_input() -> Path:
    return resolve_repo("workspace") / "planning" / "decumulation-policy-set.json"


def default_pension_contribution_input() -> Path:
    return resolve_repo("workspace") / "planning" / "pension-contribution-input.json"


def default_pension_contribution_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "pension-contribution-input-sample.json"


def default_pension_contribution_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "pension-contribution-options.snapshot.json"


def default_pension_contribution_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-pension-contribution-options.synthetic.snapshot.json"


def default_tax_aware_portfolio_input() -> Path:
    return resolve_repo("workspace") / "planning" / "tax-aware-portfolio-input.json"


def default_tax_aware_portfolio_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "tax-aware-portfolio-input-sample.json"


def default_tax_aware_portfolio_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "tax-aware-portfolio.snapshot.json"


def default_tax_aware_portfolio_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-tax-aware-portfolio.synthetic.snapshot.json"


def default_it_es_pension_tax_classification_input() -> Path:
    return resolve_repo("workspace") / "planning" / "it-es-pension-tax-classification-input.json"


def default_it_es_pension_tax_classification_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "it-es-pension-tax-classification-input-sample.json"


def default_it_es_pension_income_sample() -> Path:
    return resolve_repo("engine") / "examples" / "it-es-pension-income-sample.json"


def default_it_es_pension_tax_classification_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "it-es-pension-tax-classification.snapshot.json"


def default_it_es_pension_tax_classification_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-it-es-pension-tax-classification.synthetic.snapshot.json"


def default_spanish_pension_net_it_resident_input() -> Path:
    return resolve_repo("workspace") / "planning" / "spanish-pension-net-it-resident-input.json"


def default_spanish_pension_net_it_resident_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "spanish-pension-net-it-resident-input-sample.json"


def default_spanish_pension_net_it_resident_sample_classification() -> Path:
    return resolve_repo("engine") / "examples" / "spanish-pension-net-it-es-classification-sample.json"


def default_spanish_pension_net_it_resident_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "spanish-pension-net-it-resident.snapshot.json"


def default_spanish_pension_net_it_resident_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-spanish-pension-net-it-resident.synthetic.snapshot.json"


def default_it_es_foreign_assets_input() -> Path:
    return resolve_repo("workspace") / "planning" / "it-es-foreign-assets-input.json"


def default_it_es_foreign_assets_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "it-es-foreign-assets-input-sample.json"


def default_it_es_foreign_assets_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "it-es-foreign-assets.snapshot.json"


def default_it_es_foreign_assets_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-it-es-foreign-assets.synthetic.snapshot.json"


def default_cross_border_it_es_sample_net() -> Path:
    return resolve_repo("engine") / "examples" / "cross-border-spanish-pension-net-sample.json"


def default_cross_border_it_es_sample_pro_rata() -> Path:
    return resolve_repo("engine") / "examples" / "cross-border-it-es-eu-pension-pro-rata-sample.json"


def default_cross_border_it_es_sample_foreign_assets() -> Path:
    return resolve_repo("engine") / "examples" / "cross-border-it-es-foreign-assets-sample.json"


def default_decumulation_policy_set_sample_input() -> Path:
    return resolve_repo("engine") / "examples" / "decumulation-policy-set-sample.json"


def default_decumulation_sample_net_worth() -> Path:
    return resolve_repo("engine") / "examples" / "decumulation-net-worth-sample.json"


def default_decumulation_sample_liquidity_plan() -> Path:
    return resolve_repo("engine") / "examples" / "decumulation-liquidity-plan-sample.json"


def default_decumulation_sample_pension_income() -> Path:
    return resolve_repo("engine") / "examples" / "decumulation-pension-income-sample.json"


def default_decumulation_sample_rita_options() -> Path:
    return resolve_repo("engine") / "examples" / "decumulation-rita-options-sample.json"


def default_decumulation_strategy_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "decumulation-strategy.snapshot.json"


def default_decumulation_strategy_demo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "cli-check-decumulation-strategy.synthetic.snapshot.json"


def default_retirement_simulation_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "retirement-simulation.snapshot.json"


def default_monte_carlo_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "monte-carlo.snapshot.json"


def default_scenario_comparison_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "scenario-comparison.snapshot.json"


def default_decision_scenario_input() -> Path:
    return resolve_repo("workspace") / "scenarios" / "decision-scenario-v2.json"


def default_decision_scenario_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "decision-scenario-v2.snapshot.json"


def default_decision_outcome_input() -> Path:
    return resolve_repo("workspace") / "scenarios" / "decision-outcome.json"


def default_decision_outcome_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "decision-outcome.snapshot.json"


def default_sensitivity_analysis_input() -> Path:
    return resolve_repo("workspace") / "scenarios" / "sensitivity-analysis.json"


def default_sensitivity_analysis_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "sensitivity-analysis.snapshot.json"


def default_decision_score_input() -> Path:
    return resolve_repo("workspace") / "scenarios" / "decision-score.json"


def default_decision_score_policy() -> Path:
    return resolve_repo("rules") / "decision" / "score-policy-v1.json"


def default_decision_score_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "decision-score.snapshot.json"


def default_decision_dossier_input() -> Path:
    return resolve_repo("workspace") / "scenarios" / "decision-dossier.json"


def default_decision_dossier_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "decision-dossier.snapshot.json"


def default_decision_dossier_report_output() -> Path:
    return resolve_repo("workspace") / "reports" / "decision-dossier.md"


def default_decision_dashboard_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "decision-dashboard.snapshot.json"


def default_retirement_report_output() -> Path:
    return resolve_repo("workspace") / "reports" / "retirement-report.md"


def resolve_fonte_source_paths(
    position_pdf: Path | None,
    contributions_xlsx: Path | None,
) -> tuple[Path, Path]:
    resolved_pdf = position_pdf or _find_single_fonte_source("*.pdf", default_fonte_position_pdf())
    resolved_xlsx = contributions_xlsx or _find_single_fonte_source("*.xlsx", default_fonte_contributions_xlsx())
    return resolved_pdf, resolved_xlsx


def _find_single_fonte_source(pattern: str, preferred_path: Path) -> Path:
    if preferred_path.exists():
        return preferred_path

    candidates = _dedupe_same_content(sorted(default_fonte_documents_dir().glob(pattern)))
    if not candidates and default_fonte_documents_dir() != default_fonte_inbox_dir():
        candidates = _dedupe_same_content(sorted(default_fonte_inbox_dir().glob(pattern)))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        return preferred_path
    raise FonteImportError(
        f"Multiple Fon.Te files match {pattern}; pass an explicit path"
    )


def _dedupe_same_content(paths: list[Path]) -> list[Path]:
    if len(paths) <= 1:
        return paths
    by_hash: dict[str, Path] = {}
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        by_hash.setdefault(digest, path)
    return sorted(by_hash.values())


def resolve_repo(name: str, environ: Mapping[str, str] | None = None) -> Path:
    if name not in REPOS:
        raise KeyError(f"Unknown repository: {name}")

    env_source = os.environ if environ is None else environ
    env = env_source.get(f"FO_{name.upper()}_PATH")
    if env:
        return Path(env).expanduser()
    if name == "engine":
        return ENGINE_ROOT
    return WORKSPACE_ROOT / REPOS[name]


def validate(environ: Mapping[str, str] | None = None) -> dict[str, bool]:
    return {name: resolve_repo(name, environ).exists() for name in REPOS}


def print_validate(status: Mapping[str, bool], environ: Mapping[str, str] | None = None) -> None:
    for name, ok in status.items():
        path = resolve_repo(name, environ)
        state = "OK" if ok else "MISSING"
        print(f"{name}: {state} ({path})")


def prepare_planning_goals_input(draft_path: Path, input_path: Path, overwrite: bool = False) -> dict[str, str]:
    if not draft_path.exists():
        raise PlanningGoalsError(f"Planning goals draft not found: {draft_path}")
    if input_path.exists() and not overwrite:
        raise PlanningGoalsError(f"Planning goals input already exists: {input_path}; use --overwrite to replace it")
    try:
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text(draft_path.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError as exc:
        raise PlanningGoalsError(f"Cannot prepare planning goals input: {input_path}") from exc
    return {
        "status": "prepared",
        "draft_path": str(draft_path),
        "input_path": str(input_path),
    }


def prepare_it_es_eu_pension_pro_rata_input(template_path: Path, draft_path: Path, overwrite: bool = False) -> dict[str, str]:
    if not template_path.exists():
        raise ItEsEuPensionProRataError(f"IT-ES EU pension pro-rata template not found: {template_path}")
    if draft_path.exists() and not overwrite:
        raise ItEsEuPensionProRataError(
            f"IT-ES EU pension pro-rata draft already exists: {draft_path}; use --overwrite to replace it"
        )
    try:
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError as exc:
        raise ItEsEuPensionProRataError(f"Cannot prepare IT-ES EU pension pro-rata draft: {draft_path}") from exc
    return {
        "status": "prepared",
        "template_path": str(template_path),
        "draft_path": str(draft_path),
    }


def run_it_es_eu_pension_wizard(input_path: Path, overwrite: bool = False) -> dict[str, Any]:
    existing = _read_optional_wizard_json(input_path, ItEsEuPensionProRataError, "IT-ES EU pension pro-rata input")
    if existing is not None and not overwrite:
        return {"status": "existing", "input_path": str(input_path), "data_gap_count": len(existing.get("data_gaps", []))}

    defaults = _it_es_eu_pension_wizard_defaults(existing)
    print("planning it-es-eu-pension wizard: crea un input personale esplicito, senza usare fixture sintetiche.")
    print("planning it-es-eu-pension wizard: i contributi italiani servono solo per il diritto UE, non come basi spagnole.")
    print(
        "contesto spagnolo riconciliato: "
        f"mesi_ES={defaults['spain_months']}, ultimo_mese_ES={defaults['spain_end_month']}"
    )
    retirement_date = _prompt_month("Mese pensionamento da verificare (YYYY-MM)", defaults["retirement_date"])
    date_of_birth = _prompt_date("Data di nascita (YYYY-MM-DD)", defaults["date_of_birth"])
    recent_anchor = _prompt_date(
        "Data anchor requisito recente spagnolo; di solito mese pensionamento o ultima contribuzione utile",
        defaults["recent_contribution_anchor_date"],
    )
    italy_months = _prompt_int("Mesi contributivi italiani normalizzati da includere per totalizzazione UE", defaults["italy_months"])
    italy_end_month = _prompt_month("Ultimo mese contributivo italiano incluso (YYYY-MM)", defaults["italy_end_month"])
    spain_months = _prompt_int("Mesi contributivi spagnoli documentati/assunti", defaults["spain_months"])
    spain_end_month = _prompt_month("Ultimo mese contributivo spagnolo incluso (YYYY-MM)", defaults["spain_end_month"])
    no_future_es = _prompt_bool("Confermi nessun contributo spagnolo futuro dopo quel mese?", defaults["no_future_spanish_contributions"])
    monthly_theoretical = _prompt_decimal_text(
        "Pensione teorica spagnola lorda mensile da sole basi ES; 0.00 se non nota",
        defaults["spanish_theoretical_monthly"],
    )
    payments_per_year = _prompt_int("Mensilita annue della pensione teorica spagnola", defaults["payments_per_year"])

    data = _it_es_eu_pension_input_data(
        {
            "retirement_date": retirement_date,
            "date_of_birth": date_of_birth,
            "recent_contribution_anchor_date": recent_anchor,
            "italy_months": italy_months,
            "italy_end_month": italy_end_month,
            "spain_months": spain_months,
            "spain_end_month": spain_end_month,
            "no_future_spanish_contributions": no_future_es,
            "spanish_theoretical_monthly": monthly_theoretical,
            "payments_per_year": payments_per_year,
        }
    )
    _write_wizard_json(input_path, data, True, ItEsEuPensionProRataError, "IT-ES EU pension pro-rata input")
    return {"status": "prepared", "input_path": str(input_path), "data_gap_count": len(data.get("data_gaps", []))}


def run_planning_goals_wizard(input_path: Path, overwrite: bool = False) -> dict[str, Any]:
    existing = _read_optional_wizard_json(input_path, PlanningGoalsError, "planning goals")
    if existing is not None and not overwrite:
        return {"status": "existing", "input_path": str(input_path), "data_gap_count": len(existing.get("data_gaps", []))}

    defaults = _planning_goals_wizard_defaults(existing)
    if existing is None:
        print("planning goals wizard: rispondi solo con dati dichiarati; lascia invio se un valore e' incerto.")
    else:
        print("planning goals wizard: uso i dati esistenti come default; premi invio per mantenerli.")
    household_id = _prompt_text("Nome tecnico del nucleo/caso", defaults["household_id"])
    _save_planning_goals_progress(input_path, defaults | {"household_id": household_id}, "household_id")
    as_of_date = _prompt_text("Data di riferimento (YYYY-MM-DD)", defaults["as_of_date"])
    _save_planning_goals_progress(input_path, defaults | {"household_id": household_id, "as_of_date": as_of_date}, "as_of_date")
    start_year = _prompt_int("Anno iniziale della pianificazione", defaults["start_year"])
    _save_planning_goals_progress(
        input_path,
        defaults | {"household_id": household_id, "as_of_date": as_of_date, "start_year": start_year},
        "start_year",
    )
    end_year = _prompt_int("Anno finale della pianificazione", defaults["end_year"] or start_year + 30)
    _save_planning_goals_progress(
        input_path,
        defaults
        | {"household_id": household_id, "as_of_date": as_of_date, "start_year": start_year, "end_year": end_year},
        "end_year",
    )
    risk_capacity = _prompt_choice(
        "Capacita di sopportare perdite (low/medium/high/unknown)",
        defaults["risk_capacity"],
        {"low", "medium", "high", "unknown"},
    )
    _save_planning_goals_progress(
        input_path,
        defaults
        | {
            "household_id": household_id,
            "as_of_date": as_of_date,
            "start_year": start_year,
            "end_year": end_year,
            "risk_capacity": risk_capacity,
        },
        "risk_capacity",
    )
    risk_tolerance = _prompt_choice(
        "Tolleranza personale al rischio (low/medium/high/unknown)",
        defaults["risk_tolerance"],
        {"low", "medium", "high", "unknown"},
    )
    _save_planning_goals_progress(
        input_path,
        defaults
        | {
            "household_id": household_id,
            "as_of_date": as_of_date,
            "start_year": start_year,
            "end_year": end_year,
            "risk_capacity": risk_capacity,
            "risk_tolerance": risk_tolerance,
        },
        "risk_tolerance",
    )
    max_loss_ratio = _prompt_decimal_text("Perdita massima accettabile, come quota del patrimonio", defaults["max_loss_ratio"])
    _save_planning_goals_progress(
        input_path,
        defaults
        | {
            "household_id": household_id,
            "as_of_date": as_of_date,
            "start_year": start_year,
            "end_year": end_year,
            "risk_capacity": risk_capacity,
            "risk_tolerance": risk_tolerance,
            "max_loss_ratio": max_loss_ratio,
        },
        "max_loss_ratio",
    )
    reserve_months = _prompt_int("Mesi minimi di riserva di emergenza", defaults["reserve_months"])
    _save_planning_goals_progress(
        input_path,
        defaults
        | {
            "household_id": household_id,
            "as_of_date": as_of_date,
            "start_year": start_year,
            "end_year": end_year,
            "risk_capacity": risk_capacity,
            "risk_tolerance": risk_tolerance,
            "max_loss_ratio": max_loss_ratio,
            "reserve_months": reserve_months,
        },
        "reserve_months",
    )
    current_monthly_spending = _prompt_decimal_text(
        "Spesa netta mensile attuale da usare come base",
        defaults["current_monthly_spending"],
    )
    _save_planning_goals_progress(
        input_path,
        defaults
        | {
            "household_id": household_id,
            "as_of_date": as_of_date,
            "start_year": start_year,
            "end_year": end_year,
            "risk_capacity": risk_capacity,
            "risk_tolerance": risk_tolerance,
            "max_loss_ratio": max_loss_ratio,
            "reserve_months": reserve_months,
            "current_monthly_spending": current_monthly_spending,
        },
        "current_monthly_spending",
    )
    annual_cost_growth = _prompt_decimal_text(
        "Crescita annua attesa del costo della vita, come quota",
        defaults["annual_cost_growth"],
    )
    _save_planning_goals_progress(
        input_path,
        defaults
        | {
            "household_id": household_id,
            "as_of_date": as_of_date,
            "start_year": start_year,
            "end_year": end_year,
            "risk_capacity": risk_capacity,
            "risk_tolerance": risk_tolerance,
            "max_loss_ratio": max_loss_ratio,
            "reserve_months": reserve_months,
            "current_monthly_spending": current_monthly_spending,
            "annual_cost_growth": annual_cost_growth,
        },
        "annual_cost_growth",
    )
    target_year = _prompt_int("Anno obiettivo per il reddito pensionistico", defaults["target_year"] or max(start_year, 2035))
    _save_planning_goals_progress(
        input_path,
        defaults
        | {
            "household_id": household_id,
            "as_of_date": as_of_date,
            "start_year": start_year,
            "end_year": end_year,
            "risk_capacity": risk_capacity,
            "risk_tolerance": risk_tolerance,
            "max_loss_ratio": max_loss_ratio,
            "reserve_months": reserve_months,
            "current_monthly_spending": current_monthly_spending,
            "annual_cost_growth": annual_cost_growth,
            "target_year": target_year,
        },
        "target_year",
    )
    annual_need = _project_annual_need(current_monthly_spending, annual_cost_growth, max(0, target_year - start_year))

    gaps = _wizard_gaps(
        [
            (risk_capacity == "unknown", "unknown_risk_capacity", "Risk capacity was left unknown in the wizard."),
            (risk_tolerance == "unknown", "unknown_risk_tolerance", "Risk tolerance was left unknown in the wizard."),
            (current_monthly_spending == "0.00", "unknown_current_spending", "Current spending must be reviewed."),
            (annual_need == "0.00", "unknown_retirement_need", "Retirement income target must be reviewed."),
        ]
    )
    data = {
        "schema_version": "planning-goals/v1",
        "record_type": "PlanningGoals",
        "household_id": household_id,
        "as_of_date": as_of_date,
        "planning_horizon": {"start_year": start_year, "end_year": end_year},
        "risk_profile": {
            "capacity": risk_capacity,
            "tolerance": risk_tolerance,
            "max_loss_ratio": max_loss_ratio,
        },
        "liquidity_policy": {
            "minimum_reserve_months": reserve_months,
            "preferred_bucket": "emergency_reserve",
        },
        "objectives": [
            {
                "objective_id": "objective_emergency_reserve",
                "label": "Maintain emergency reserve",
                "category": "liquidity",
                "priority": 1,
                "target": {"metric": "reserve_months", "operator": "min", "value": reserve_months, "unit": "months"},
                "time_horizon_year": start_year,
            },
            {
                "objective_id": "objective_retirement_income",
                "label": "Sustain retirement income",
                "category": "retirement_income",
                "priority": 2,
                "target": {
                    "metric": "annual_net_need",
                    "operator": "target",
                    "value": annual_need,
                    "unit": "EUR/year",
                    "basis": "current_monthly_spending_projected_with_explicit_cost_growth",
                    "current_monthly_spending": current_monthly_spending,
                    "annual_cost_growth": annual_cost_growth,
                    "projection_years": max(0, target_year - start_year),
                },
                "time_horizon_year": target_year,
            },
        ],
        "constraints": [
            {
                "constraint_id": "constraint_emergency_reserve",
                "label": "Keep emergency reserve available",
                "constraint_type": "liquidity",
                "severity": "hard",
                "priority": 1,
                "applies_to_objective_ids": ["objective_emergency_reserve", "objective_retirement_income"],
                "threshold": {"metric": "reserve_months", "operator": "min", "value": reserve_months, "unit": "months"},
            }
        ],
        "data_gaps": gaps,
    }
    validate_planning_goals(data, None)
    _write_wizard_json(input_path, data, True, PlanningGoalsError, "planning goals")
    return {"status": "prepared", "input_path": str(input_path), "data_gap_count": len(gaps)}


def run_liquidity_plan_wizard(input_path: Path, overwrite: bool = False) -> dict[str, Any]:
    existing = _read_optional_wizard_json(input_path, LiquidityPlanError, "liquidity plan input")
    if existing is not None and not overwrite:
        return {"status": "existing", "input_path": str(input_path), "data_gap_count": len(existing.get("data_gaps", []))}

    if existing is None:
        print("planning liquidity wizard: inserisci solo valori dichiarati; lascia invio se un valore e' incerto.")
    else:
        print("planning liquidity wizard: uso nucleo, data e valuta gia salvati; modifica solo i parametri della riserva.")
    household_id = str((existing or {}).get("household_id") or "household_private")
    as_of_date = str((existing or {}).get("as_of_date") or "2026-01-01")
    base_currency = str((existing or {}).get("base_currency") or "EUR").upper()
    print(f"contesto: nucleo={household_id}, data={as_of_date}, valuta={base_currency}")
    monthly_expenses = _prompt_decimal_text("Spese mensili correnti dichiarate", str((existing or {}).get("monthly_expenses") or "0.00"))
    reserve_months = _prompt_int("Mesi minimi di riserva di emergenza", int((existing or {}).get("minimum_reserve_months") or 12))
    concentration_threshold = _prompt_decimal_text(
        "Soglia concentrazione singolo asset, come quota",
        str((existing or {}).get("concentration_threshold") or "0.60"),
    )
    gaps = _wizard_gaps(
        [(monthly_expenses == "0.00", "unknown_monthly_expenses", "Monthly expenses must be reviewed.")]
    )
    if existing is not None:
        gaps.extend(_non_placeholder_gaps(existing.get("data_gaps", [])))
    data = {
        "schema_version": "liquidity-plan-input/v1",
        "record_type": "LiquidityPlanInput",
        "household_id": household_id,
        "as_of_date": as_of_date,
        "base_currency": base_currency,
        "monthly_expenses": monthly_expenses,
        "minimum_reserve_months": reserve_months,
        "concentration_threshold": concentration_threshold,
        "data_gaps": gaps,
    }
    validate_liquidity_plan_input(data)
    _write_wizard_json(input_path, data, overwrite, LiquidityPlanError, "liquidity plan input")
    return {"status": "prepared", "input_path": str(input_path), "data_gap_count": len(gaps)}


def run_asset_availability_wizard(
    input_path: Path,
    net_worth_snapshot_path: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    existing = _read_optional_wizard_json(input_path, AssetAvailabilityError, "asset availability")
    if existing is not None and not overwrite:
        return {"status": "existing", "input_path": str(input_path), "data_gap_count": len(existing.get("data_gaps", []))}
    net_worth = _read_optional_wizard_json(net_worth_snapshot_path, AssetAvailabilityError, "net worth snapshot")
    if net_worth is None:
        raise AssetAvailabilityError(f"Net worth snapshot not found: {net_worth_snapshot_path}")
    components = net_worth.get("components")
    if not isinstance(components, list):
        raise AssetAvailabilityError("Net worth snapshot components must be a list")

    print("household availability wizard: classifica la disponibilita' degli asset; premi invio per accettare i default.")
    household_default = str((existing or {}).get("household_id") or net_worth.get("household_id") or "household_private")
    as_of_default = str((existing or {}).get("as_of_date") or "2026-01-01")
    household_id = _prompt_text("Nome tecnico del nucleo/caso", household_default)
    as_of_date = _prompt_date("Data di riferimento disponibilita' (YYYY-MM-DD)", as_of_default)
    existing_by_asset = {
        item["asset_id"]: item
        for item in _existing_availability_classifications(existing)
        if isinstance(item.get("asset_id"), str)
    }
    classifications: list[dict[str, Any]] = []
    _save_asset_availability_progress(input_path, household_id, as_of_date, classifications)
    seen_asset_ids: set[str] = set()
    for component in components:
        if not isinstance(component, dict) or component.get("type") != "asset":
            continue
        asset_id = str(component.get("asset_id") or component.get("id") or "")
        if not asset_id:
            continue
        seen_asset_ids.add(asset_id)
        label = str(component.get("label") or asset_id)
        value = component.get("value", "n/a")
        currency = str(component.get("currency") or "EUR")
        asset_class = _asset_availability_class(str(component.get("asset_class") or component.get("class") or "other"))
        defaults = _asset_availability_defaults(asset_class, currency, as_of_date) | _asset_availability_existing_defaults(
            existing_by_asset.get(asset_id)
        )
        print(f"\nasset: {label} ({asset_id}) value={value} {currency}")
        if asset_id in existing_by_asset and not _prompt_bool("Asset gia classificato: rivederlo? (yes/no)", False):
            classifications.append(existing_by_asset[asset_id])
            _save_asset_availability_progress(input_path, household_id, as_of_date, classifications)
            continue
        include = _prompt_bool("Classificare questo asset? (yes/no)", True)
        if not include:
            continue
        liquidity_tier = _prompt_choice(
            "Disponibilita' (immediate/short_term/notice_required/locked_until_date/illiquid/unknown)",
            defaults["liquidity_tier"],
            {"immediate", "short_term", "notice_required", "locked_until_date", "illiquid", "unknown"},
        )
        risk_level = _prompt_choice(
            "Rischio/liquidabilita' economica (low/medium/high/illiquid/unknown)",
            defaults["risk_level"],
            {"low", "medium", "high", "illiquid", "unknown"},
        )
        constraints = _prompt_list(
            "Vincoli, separati da virgola (none/pension_lock/policy_terms/co_ownership/foreign_reporting/sale_process/unknown)",
            defaults["constraints"],
        )
        first_available_date = _prompt_date_or_unknown(
            "Prima data di disponibilita' (YYYY-MM-DD oppure unknown)",
            defaults["first_available_date"],
        )
        jurisdiction = _prompt_country_code("Paese dell'asset (IT/ES/...)", defaults["jurisdiction"])
        tax_treatment = _prompt_choice(
            "Trattamento fiscale dichiarativo",
            defaults["tax_treatment"],
            {
                "ordinary_taxable",
                "tax_deferred",
                "pension_taxation",
                "insurance_wrapper",
                "real_estate_taxation",
                "foreign_asset_reporting",
                "unknown",
            },
        )
        classifications.append(
            {
                "classification_id": f"availability_{asset_id}",
                "asset_id": asset_id,
                "asset_class": asset_class,
                "availability_as_of_date": as_of_date,
                "currency": currency,
                "first_available_date": first_available_date,
                "jurisdiction": jurisdiction,
                "liquidity_tier": liquidity_tier,
                "constraints": constraints,
                "risk_level": risk_level,
                "tax_treatment": tax_treatment,
                "notes": "Prepared by household availability wizard.",
                "provenance": "user wizard input",
            }
        )
        _save_asset_availability_progress(input_path, household_id, as_of_date, classifications)
    for asset_id, classification in existing_by_asset.items():
        if asset_id not in seen_asset_ids:
            classifications.append(classification)
    data = {
        "schema_version": "asset-availability/v1",
        "record_type": "AssetAvailability",
        "household_id": household_id,
        "as_of_date": as_of_date,
        "classifications": classifications,
        "data_gaps": [],
    }
    gaps = validate_asset_availability(data, None)
    _write_wizard_json(input_path, data, True, AssetAvailabilityError, "asset availability")
    return {"status": "prepared", "input_path": str(input_path), "classification_count": len(classifications), "data_gap_count": len(gaps)}


def run_decumulation_policy_wizard(input_path: Path, overwrite: bool = False) -> dict[str, Any]:
    existing = _read_optional_wizard_json(input_path, DecumulationStrategyError, "decumulation policy set")
    if existing is not None and not overwrite:
        return {"status": "existing", "input_path": str(input_path), "data_gap_count": len(existing.get("data_gaps", []))}

    defaults = _decumulation_wizard_defaults(existing)
    if existing is None:
        print("planning decumulation wizard: uso goals/liquidita' gia salvati come contesto.")
        print("planning decumulation wizard: rendimenti e aliquote restano assunzioni esplicite da rivedere.")
    else:
        print("planning decumulation wizard: uso i dati esistenti come default; premi invio per mantenerli.")
    print(
        "contesto: "
        f"nucleo={defaults['household_id']}, data={defaults['as_of_date']}, valuta={defaults['base_currency']}"
    )
    if defaults["withdrawal_order"]:
        print("asset prelevabili proposti: " + ", ".join(defaults["withdrawal_order"]))
    current_age = _prompt_int("Eta attuale della persona su cui simulare il decumulo", defaults["current_age"])
    _save_decumulation_progress(input_path, defaults | {"current_age": current_age}, "current_age")
    retirement_age = _prompt_int("Eta prevista di inizio decumulo/pensione", defaults["retirement_age"] or max(current_age, 67))
    _save_decumulation_progress(
        input_path,
        defaults | {"current_age": current_age, "retirement_age": retirement_age},
        "retirement_age",
    )
    end_age = _prompt_int("Eta finale fino a cui verificare la sostenibilita'", defaults["end_age"] or max(retirement_age, 95))
    _save_decumulation_progress(
        input_path,
        defaults | {"current_age": current_age, "retirement_age": retirement_age, "end_age": end_age},
        "end_age",
    )
    annual_spending_need = _prompt_decimal_text("Spesa netta annua da coprire, proposta dai goals", defaults["annual_spending_need"])
    _save_decumulation_progress(
        input_path,
        defaults
        | {
            "current_age": current_age,
            "retirement_age": retirement_age,
            "end_age": end_age,
            "annual_spending_need": annual_spending_need,
        },
        "annual_spending_need",
    )
    cash_buffer_target = _prompt_decimal_text("Cuscinetto minimo di liquidita' da preservare", defaults["cash_buffer_target"])
    _save_decumulation_progress(
        input_path,
        defaults
        | {
            "current_age": current_age,
            "retirement_age": retirement_age,
            "end_age": end_age,
            "annual_spending_need": annual_spending_need,
            "cash_buffer_target": cash_buffer_target,
        },
        "cash_buffer_target",
    )
    withdrawal_order = _prompt_list(
        "Ordine asset da usare se serve vendere/prelevare, separati da virgola",
        defaults["withdrawal_order"],
    )
    _save_decumulation_progress(
        input_path,
        defaults
        | {
            "current_age": current_age,
            "retirement_age": retirement_age,
            "end_age": end_age,
            "annual_spending_need": annual_spending_need,
            "cash_buffer_target": cash_buffer_target,
            "withdrawal_order": withdrawal_order,
        },
        "withdrawal_order",
    )
    include_rita = _prompt_bool("Includere ponte RITA? (yes/no)", defaults["include_rita"])
    _save_decumulation_progress(
        input_path,
        defaults
        | {
            "current_age": current_age,
            "retirement_age": retirement_age,
            "end_age": end_age,
            "annual_spending_need": annual_spending_need,
            "cash_buffer_target": cash_buffer_target,
            "withdrawal_order": withdrawal_order,
            "include_rita": include_rita,
        },
        "include_rita",
    )
    annual_returns = _prompt_list("Rendimenti annui ipotizzati, decimali separati da virgola", defaults["annual_returns"])
    _save_decumulation_progress(
        input_path,
        defaults
        | {
            "current_age": current_age,
            "retirement_age": retirement_age,
            "end_age": end_age,
            "annual_spending_need": annual_spending_need,
            "cash_buffer_target": cash_buffer_target,
            "withdrawal_order": withdrawal_order,
            "include_rita": include_rita,
            "annual_returns": annual_returns,
        },
        "annual_returns",
    )
    withdrawal_tax_rate = _prompt_decimal_text(
        "Aliquota media stimata sui prelievi da asset; lascia 0.00 se non la sai ora",
        defaults["withdrawal_tax_rate"],
    )
    _save_decumulation_progress(
        input_path,
        defaults
        | {
            "current_age": current_age,
            "retirement_age": retirement_age,
            "end_age": end_age,
            "annual_spending_need": annual_spending_need,
            "cash_buffer_target": cash_buffer_target,
            "withdrawal_order": withdrawal_order,
            "include_rita": include_rita,
            "annual_returns": annual_returns,
            "withdrawal_tax_rate": withdrawal_tax_rate,
        },
        "withdrawal_tax_rate",
    )
    pension_tax_rate = _prompt_decimal_text(
        "Aliquota media stimata sui flussi pensionistici; lascia 0.00 se non la sai ora",
        defaults["pension_tax_rate"],
    )
    _save_decumulation_progress(
        input_path,
        defaults
        | {
            "current_age": current_age,
            "retirement_age": retirement_age,
            "end_age": end_age,
            "annual_spending_need": annual_spending_need,
            "cash_buffer_target": cash_buffer_target,
            "withdrawal_order": withdrawal_order,
            "include_rita": include_rita,
            "annual_returns": annual_returns,
            "withdrawal_tax_rate": withdrawal_tax_rate,
            "pension_tax_rate": pension_tax_rate,
        },
        "pension_tax_rate",
    )
    rita_tax_rate = _prompt_decimal_text(
        "Aliquota media stimata RITA; lascia 0.00 se non la sai ora",
        defaults["rita_tax_rate"],
    )
    gaps = _wizard_gaps(
        [
            (annual_spending_need == "0.00", "unknown_annual_spending_need", "Annual spending need must be reviewed."),
            (cash_buffer_target == "0.00", "unknown_cash_buffer_target", "Cash buffer target must be reviewed."),
            (annual_returns == ["0.00"], "unknown_return_assumption", "Return sequence must be reviewed."),
            (
                withdrawal_tax_rate == "0.00",
                "unknown_withdrawal_tax_rate",
                "Average tax rate on asset withdrawals must be estimated or reviewed.",
            ),
            (
                pension_tax_rate == "0.00",
                "unknown_pension_tax_rate",
                "Average tax rate on pension cashflows must be estimated or reviewed.",
            ),
            (
                include_rita and rita_tax_rate == "0.00",
                "unknown_rita_tax_rate",
                "Average RITA tax rate must be estimated or reviewed.",
            ),
            (
                not withdrawal_order or withdrawal_order == ["review_withdrawal_order"],
                "unknown_withdrawal_order",
                "Withdrawal order must be reviewed.",
            ),
        ]
    )
    data = _decumulation_policy_data(
        defaults
        | {
            "current_age": current_age,
            "retirement_age": retirement_age,
            "end_age": end_age,
            "annual_spending_need": annual_spending_need,
            "cash_buffer_target": cash_buffer_target,
            "withdrawal_order": withdrawal_order,
            "include_rita": include_rita,
            "annual_returns": annual_returns,
            "withdrawal_tax_rate": withdrawal_tax_rate,
            "pension_tax_rate": pension_tax_rate,
            "rita_tax_rate": rita_tax_rate,
        },
        gaps,
    )
    validate_decumulation_policy_set(data)
    _write_wizard_json(input_path, data, True, DecumulationStrategyError, "decumulation policy set")
    return {"status": "prepared", "input_path": str(input_path), "data_gap_count": len(gaps)}


def run_pension_contribution_wizard(input_path: Path, overwrite: bool = False) -> dict[str, Any]:
    existing = _read_optional_wizard_json(input_path, PensionContributionOptionsError, "pension contribution input")
    if existing is not None and not overwrite:
        return {"status": "existing", "input_path": str(input_path), "data_gap_count": len(existing.get("data_gaps", []))}

    defaults = _pension_contribution_wizard_defaults(existing)
    if existing is None:
        print("planning pension-contributions wizard: uso liquidita' gia salvata come contesto.")
        print("planning pension-contributions wizard: fiscalita' e contributi restano assunzioni esplicite da rivedere.")
    else:
        print("planning pension-contributions wizard: uso i dati esistenti come default; premi invio per mantenerli.")
    print(
        "contesto: "
        f"nucleo={defaults['household_id']}, data={defaults['as_of_date']}, "
        f"tax_year={defaults['tax_year']}, giurisdizione={defaults['jurisdiction']}"
    )
    print(
        "liquidita': "
        f"disponibile={defaults['available_liquidity']}, minimo da preservare={defaults['minimum_liquidity_after_contributions']}"
    )
    marginal_tax_rate = _prompt_decimal_text(
        "Aliquota marginale IRPEF stimata; lascia 0.00 se non la sai ora",
        defaults["marginal_tax_rate"],
    )
    _save_pension_contribution_progress(input_path, defaults | {"marginal_tax_rate": marginal_tax_rate}, "marginal_tax_rate")
    already_deducted = _prompt_decimal_text(
        "Contributi pensione complementare gia dedotti/conteggiati quest'anno",
        defaults["already_deducted_contributions"],
    )
    _save_pension_contribution_progress(
        input_path,
        defaults | {"marginal_tax_rate": marginal_tax_rate, "already_deducted_contributions": already_deducted},
        "already_deducted_contributions",
    )
    extra_room = _prompt_decimal_text(
        "Extra deducibilita primo impiego disponibile; lascia 0.00 se non applicabile o incerta",
        defaults["first_employment_extra_deduction_room"],
    )
    _save_pension_contribution_progress(
        input_path,
        defaults
        | {
            "marginal_tax_rate": marginal_tax_rate,
            "already_deducted_contributions": already_deducted,
            "first_employment_extra_deduction_room": extra_room,
        },
        "first_employment_extra_deduction_room",
    )
    employee_contribution = _prompt_decimal_text(
        "Versamento volontario annuo che vuoi testare",
        defaults["employee_contribution"],
    )
    _save_pension_contribution_progress(
        input_path,
        defaults
        | {
            "marginal_tax_rate": marginal_tax_rate,
            "already_deducted_contributions": already_deducted,
            "first_employment_extra_deduction_room": extra_room,
            "employee_contribution": employee_contribution,
        },
        "employee_contribution",
    )
    employer_contribution = _prompt_decimal_text(
        "Contributo datore/azienda collegato a quel versamento; 0.00 se assente o incerto",
        defaults["employer_contribution"],
    )
    _save_pension_contribution_progress(
        input_path,
        defaults
        | {
            "marginal_tax_rate": marginal_tax_rate,
            "already_deducted_contributions": already_deducted,
            "first_employment_extra_deduction_room": extra_room,
            "employee_contribution": employee_contribution,
            "employer_contribution": employer_contribution,
        },
        "employer_contribution",
    )
    tfr_transfer = _prompt_decimal_text(
        "TFR annuo da destinare al fondo; 0.00 se non vuoi testarlo ora",
        defaults["tfr_transfer"],
    )
    opportunity_cost_rate = _prompt_decimal_text(
        "Rendimento alternativo annuo perso sulla liquidita versata; lascia 0.00 se incerto",
        defaults["opportunity_cost_rate"],
    )
    gaps = _wizard_gaps(
        [
            (marginal_tax_rate == "0.00", "unknown_marginal_tax_rate", "Marginal tax rate must be estimated or reviewed."),
            (
                already_deducted == "0.00",
                "unknown_already_deducted_contributions",
                "Already deducted complementary pension contributions must be confirmed.",
            ),
            (
                employee_contribution == "0.00" and employer_contribution == "0.00" and tfr_transfer == "0.00",
                "missing_contribution_option",
                "At least one non-zero contribution scenario should be reviewed.",
            ),
            (
                opportunity_cost_rate == "0.00",
                "unknown_opportunity_cost_rate",
                "Opportunity cost rate must be estimated or reviewed.",
            ),
        ]
    )
    data = _pension_contribution_input_data(
        defaults
        | {
            "marginal_tax_rate": marginal_tax_rate,
            "already_deducted_contributions": already_deducted,
            "first_employment_extra_deduction_room": extra_room,
            "employee_contribution": employee_contribution,
            "employer_contribution": employer_contribution,
            "tfr_transfer": tfr_transfer,
            "opportunity_cost_rate": opportunity_cost_rate,
        },
        gaps,
    )
    validate_pension_contribution_input(data)
    _write_wizard_json(input_path, data, True, PensionContributionOptionsError, "pension contribution input")
    return {"status": "prepared", "input_path": str(input_path), "data_gap_count": len(gaps)}


def _write_wizard_json(
    path: Path,
    data: dict[str, Any],
    overwrite: bool,
    error_type: type[ValueError],
    label: str,
) -> None:
    if path.exists() and not overwrite:
        raise error_type(f"{label} already exists: {path}; use --overwrite to replace it")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise error_type(f"Cannot write {label}: {path}") from exc


def _save_planning_goals_progress(path: Path, values: dict[str, Any], last_answered: str) -> None:
    target_year = _int_or_default(values.get("target_year"), 2035)
    start_year = _int_or_default(values.get("start_year"), 2026)
    current_monthly_spending = str(values.get("current_monthly_spending") or "0.00")
    annual_cost_growth = str(values.get("annual_cost_growth") or "0.02")
    try:
        annual_need = _project_annual_need(current_monthly_spending, annual_cost_growth, max(0, target_year - start_year))
    except PlanningGoalsError:
        annual_need = str(values.get("annual_need") or "0.00")
    progress = {
        "schema_version": "planning-goals/v1",
        "record_type": "PlanningGoals",
        "household_id": values.get("household_id"),
        "as_of_date": values.get("as_of_date"),
        "planning_horizon": {
            "start_year": values.get("start_year"),
            "end_year": values.get("end_year"),
        },
        "risk_profile": {
            "capacity": values.get("risk_capacity", "unknown"),
            "tolerance": values.get("risk_tolerance", "unknown"),
            "max_loss_ratio": values.get("max_loss_ratio"),
        },
        "liquidity_policy": {
            "minimum_reserve_months": values.get("reserve_months"),
            "preferred_bucket": "emergency_reserve",
        },
        "objectives": [
            {
                "objective_id": "objective_emergency_reserve",
                "label": "Maintain emergency reserve",
                "category": "liquidity",
                "priority": 1,
                "target": {
                    "metric": "reserve_months",
                    "operator": "min",
                    "value": values.get("reserve_months"),
                    "unit": "months",
                },
                "time_horizon_year": values.get("start_year"),
            },
            {
                "objective_id": "objective_retirement_income",
                "label": "Sustain retirement income",
                "category": "retirement_income",
                "priority": 2,
                "target": {
                    "metric": "annual_net_need",
                    "operator": "target",
                    "value": annual_need,
                    "unit": "EUR/year",
                    "basis": "current_monthly_spending_projected_with_explicit_cost_growth",
                    "current_monthly_spending": current_monthly_spending,
                    "annual_cost_growth": annual_cost_growth,
                    "projection_years": max(0, target_year - start_year),
                },
                "time_horizon_year": values.get("target_year"),
            },
        ],
        "constraints": [
            {
                "constraint_id": "constraint_emergency_reserve",
                "label": "Keep emergency reserve available",
                "constraint_type": "liquidity",
                "severity": "hard",
                "priority": 1,
                "applies_to_objective_ids": ["objective_emergency_reserve", "objective_retirement_income"],
                "threshold": {
                    "metric": "reserve_months",
                    "operator": "min",
                    "value": values.get("reserve_months"),
                    "unit": "months",
                },
            }
        ],
        "data_gaps": [
            {
                "code": "wizard_incomplete",
                "message": "Planning goals wizard was interrupted before final validation.",
                "last_answered": last_answered,
            }
        ],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise PlanningGoalsError(f"Cannot save planning goals wizard progress: {path}") from exc


def _existing_availability_classifications(existing: dict[str, Any] | None) -> list[dict[str, Any]]:
    if existing is None:
        return []
    classifications = existing.get("classifications")
    if not isinstance(classifications, list):
        return []
    return [item for item in classifications if isinstance(item, dict)]


def _save_asset_availability_progress(
    path: Path,
    household_id: str,
    as_of_date: str,
    classifications: list[dict[str, Any]],
) -> None:
    progress = {
        "schema_version": "asset-availability/v1",
        "record_type": "AssetAvailability",
        "household_id": household_id,
        "as_of_date": as_of_date,
        "classifications": classifications,
        "data_gaps": [
            {
                "code": "wizard_incomplete",
                "message": "Asset availability wizard was interrupted before final validation.",
                "classified_asset_count": len(classifications),
            }
        ],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise AssetAvailabilityError(f"Cannot save asset availability wizard progress: {path}") from exc


def _save_decumulation_progress(path: Path, values: dict[str, Any], last_answered: str) -> None:
    data = _decumulation_policy_data(
        values,
        data_gaps=[
            {
                "code": "wizard_incomplete",
                "message": "Decumulation wizard was interrupted before final validation.",
                "last_answered": last_answered,
            }
        ],
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise DecumulationStrategyError(f"Cannot save decumulation wizard progress: {path}") from exc


def _save_pension_contribution_progress(path: Path, values: dict[str, Any], last_answered: str) -> None:
    data = _pension_contribution_input_data(
        values,
        [
            {
                "code": "wizard_incomplete",
                "message": "Pension contribution wizard was interrupted before final validation.",
                "last_answered": last_answered,
            }
        ],
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise PensionContributionOptionsError(f"Cannot save pension contribution wizard progress: {path}") from exc


def _read_optional_wizard_json(path: Path, error_type: type[ValueError], label: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise error_type(f"Invalid JSON in existing {label}: {path}: {exc}") from exc
    except OSError as exc:
        raise error_type(f"Cannot read existing {label}: {path}") from exc
    if not isinstance(data, dict):
        raise error_type(f"Existing {label} must contain a JSON object: {path}")
    return data


def _planning_goals_wizard_defaults(existing: dict[str, Any] | None) -> dict[str, Any]:
    liquidity_defaults = _liquidity_input_defaults()
    if existing is None:
        return {
            "household_id": "household_private",
            "as_of_date": "2026-01-01",
            "start_year": 2026,
            "end_year": 2056,
            "risk_capacity": "unknown",
            "risk_tolerance": "unknown",
            "max_loss_ratio": "0.20",
            "reserve_months": 12,
            "annual_need": "0.00",
            "current_monthly_spending": liquidity_defaults.get("monthly_expenses", "0.00"),
            "annual_cost_growth": "0.02",
            "target_year": 2035,
        }
    horizon = existing.get("planning_horizon") if isinstance(existing.get("planning_horizon"), dict) else {}
    risk = existing.get("risk_profile") if isinstance(existing.get("risk_profile"), dict) else {}
    liquidity = existing.get("liquidity_policy") if isinstance(existing.get("liquidity_policy"), dict) else {}
    annual_need, target_year, current_monthly_spending, annual_cost_growth = _retirement_income_defaults(existing)
    start_year = _int_or_default(horizon.get("start_year"), 2026)
    return {
        "household_id": str(existing.get("household_id") or "household_private"),
        "as_of_date": str(existing.get("as_of_date") or "2026-01-01"),
        "start_year": start_year,
        "end_year": _int_or_default(horizon.get("end_year"), start_year + 30),
        "risk_capacity": str(risk.get("capacity") or "unknown"),
        "risk_tolerance": str(risk.get("tolerance") or "unknown"),
        "max_loss_ratio": str(risk.get("max_loss_ratio") or "0.20"),
        "reserve_months": _int_or_default(liquidity.get("minimum_reserve_months"), 12),
        "annual_need": annual_need,
        "current_monthly_spending": current_monthly_spending or liquidity_defaults.get("monthly_expenses", "0.00"),
        "annual_cost_growth": annual_cost_growth,
        "target_year": target_year,
    }


def _retirement_income_defaults(existing: dict[str, Any]) -> tuple[str, int, str | None, str]:
    objectives = existing.get("objectives")
    if isinstance(objectives, list):
        for objective in objectives:
            if not isinstance(objective, dict):
                continue
            target = objective.get("target") if isinstance(objective.get("target"), dict) else {}
            if target.get("metric") == "annual_net_need":
                return (
                    str(target.get("value") or "0.00"),
                    _int_or_default(objective.get("time_horizon_year"), 2035),
                    str(target.get("current_monthly_spending")) if target.get("current_monthly_spending") not in (None, "") else None,
                    str(target.get("annual_cost_growth") or "0.02"),
                )
    return "0.00", 2035, None, "0.02"


def _liquidity_input_defaults() -> dict[str, str]:
    path = default_liquidity_plan_input()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    monthly_expenses = data.get("monthly_expenses")
    return {"monthly_expenses": str(monthly_expenses)} if monthly_expenses not in (None, "") else {}


def _asset_availability_class(asset_class: str) -> str:
    allowed = {"cash", "deposit", "brokerage", "pension_fund", "insurance_policy", "real_estate", "company_share", "other"}
    mapping = {
        "bank_account": "cash",
        "current_account": "cash",
        "cash": "cash",
        "deposit": "deposit",
        "investment": "brokerage",
        "fund": "brokerage",
        "brokerage": "brokerage",
        "pension": "pension_fund",
        "pension_fund": "pension_fund",
        "insurance": "insurance_policy",
        "insurance_policy": "insurance_policy",
        "real_estate": "real_estate",
        "company_share": "company_share",
    }
    mapped = mapping.get(asset_class, asset_class)
    return mapped if mapped in allowed else "other"


def _asset_availability_defaults(asset_class: str, currency: str, as_of_date: str) -> dict[str, Any]:
    defaults = {
        "liquidity_tier": "unknown",
        "risk_level": "unknown",
        "constraints": ["unknown"],
        "first_available_date": as_of_date,
        "jurisdiction": "IT" if currency == "EUR" else "unknown",
        "tax_treatment": "unknown",
    }
    if asset_class == "cash":
        defaults.update({"liquidity_tier": "immediate", "risk_level": "low", "constraints": ["none"], "tax_treatment": "ordinary_taxable"})
    elif asset_class in {"deposit", "brokerage"}:
        defaults.update({"liquidity_tier": "short_term", "risk_level": "medium", "constraints": ["none"], "tax_treatment": "ordinary_taxable"})
    elif asset_class == "pension_fund":
        defaults.update({"liquidity_tier": "locked_until_date", "risk_level": "medium", "constraints": ["pension_lock"], "tax_treatment": "pension_taxation"})
    elif asset_class == "insurance_policy":
        defaults.update({"liquidity_tier": "notice_required", "risk_level": "medium", "constraints": ["policy_terms"], "tax_treatment": "insurance_wrapper"})
    elif asset_class == "real_estate":
        defaults.update({"liquidity_tier": "illiquid", "risk_level": "illiquid", "constraints": ["sale_process"], "tax_treatment": "real_estate_taxation"})
    return defaults


def _asset_availability_existing_defaults(existing: dict[str, Any] | None) -> dict[str, Any]:
    if existing is None:
        return {}
    defaults: dict[str, Any] = {}
    for field in (
        "liquidity_tier",
        "risk_level",
        "constraints",
        "first_available_date",
        "jurisdiction",
        "tax_treatment",
    ):
        value = existing.get(field)
        if value not in (None, ""):
            defaults[field] = value
    return defaults


def _decumulation_wizard_defaults(existing: dict[str, Any] | None) -> dict[str, Any]:
    context = _decumulation_context_defaults()
    policy: dict[str, Any] = {}
    if existing is not None and isinstance(existing.get("policies"), list) and existing["policies"]:
        first_policy = existing["policies"][0]
        if isinstance(first_policy, dict):
            policy = first_policy
    current_age = _int_or_default((existing or {}).get("current_age"), context["current_age"])
    retirement_age = _int_or_default(policy.get("retirement_age"), max(current_age, context["retirement_age"]))
    return {
        "household_id": str((existing or {}).get("household_id") or context["household_id"]),
        "as_of_date": str((existing or {}).get("as_of_date") or context["as_of_date"]),
        "base_currency": str((existing or {}).get("base_currency") or context["base_currency"]),
        "current_age": current_age,
        "retirement_age": retirement_age,
        "end_age": _int_or_default(policy.get("end_age"), max(retirement_age, 95)),
        "annual_spending_need": str(policy.get("annual_spending_need") or context["annual_spending_need"]),
        "cash_buffer_target": str(policy.get("cash_buffer_target") or context["cash_buffer_target"]),
        "withdrawal_order": _list_or_default(policy.get("withdrawal_order"), context["withdrawal_order"]),
        "include_rita": bool(policy.get("include_rita", False)),
        "annual_returns": _list_or_default(policy.get("annual_return_sequence"), ["0.00"]),
        "withdrawal_tax_rate": str(policy.get("withdrawal_tax_rate") or "0.00"),
        "pension_tax_rate": str(policy.get("pension_tax_rate") or "0.00"),
        "rita_tax_rate": str(policy.get("rita_tax_rate") or "0.00"),
    }


def _decumulation_context_defaults() -> dict[str, Any]:
    liquidity_input = _read_optional_json(default_liquidity_plan_input())
    liquidity_snapshot = _read_optional_json(default_liquidity_plan_output())
    goals_snapshot = _read_optional_json(default_planning_goals_output()) or _read_optional_json(default_planning_goals_input())
    household = {}
    if isinstance(liquidity_snapshot.get("household") if isinstance(liquidity_snapshot, dict) else None, dict):
        household = liquidity_snapshot["household"]
    annual_need = _annual_spending_need_from_goals(goals_snapshot)
    cash_buffer = _cash_buffer_from_liquidity(liquidity_input, liquidity_snapshot)
    return {
        "household_id": str(
            (liquidity_input or {}).get("household_id")
            or household.get("household_id")
            or (goals_snapshot or {}).get("household_id")
            or "household_private"
        ),
        "as_of_date": str(
            (liquidity_input or {}).get("as_of_date")
            or household.get("as_of_date")
            or (goals_snapshot or {}).get("as_of_date")
            or "2026-01-01"
        ),
        "base_currency": str((liquidity_input or {}).get("base_currency") or (liquidity_snapshot or {}).get("base_currency") or "EUR"),
        "current_age": 60,
        "retirement_age": 67,
        "annual_spending_need": annual_need,
        "cash_buffer_target": cash_buffer,
        "withdrawal_order": _withdrawal_order_from_liquidity(liquidity_snapshot),
    }


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _annual_spending_need_from_goals(goals: dict[str, Any]) -> str:
    objectives = goals.get("objectives")
    if isinstance(objectives, list):
        for objective in objectives:
            if not isinstance(objective, dict):
                continue
            target = objective.get("target") if isinstance(objective.get("target"), dict) else {}
            if target.get("metric") == "annual_net_need" and target.get("value") not in (None, ""):
                return str(target["value"])
    return "0.00"


def _cash_buffer_from_liquidity(liquidity_input: dict[str, Any], liquidity_snapshot: dict[str, Any]) -> str:
    reserve = liquidity_snapshot.get("emergency_reserve") if isinstance(liquidity_snapshot.get("emergency_reserve"), dict) else {}
    if reserve.get("target_amount") not in (None, ""):
        return str(reserve["target_amount"])
    try:
        monthly = Decimal(str(liquidity_input.get("monthly_expenses")))
        months = Decimal(str(liquidity_input.get("minimum_reserve_months")))
    except (InvalidOperation, TypeError):
        return "0.00"
    return _format_cli_money(monthly * months)


def _withdrawal_order_from_liquidity(liquidity_snapshot: dict[str, Any]) -> list[str]:
    assignments = liquidity_snapshot.get("asset_assignments")
    if not isinstance(assignments, list):
        return ["review_withdrawal_order"]
    bucket_rank = {"short_term": 0, "medium_term": 1, "long_term": 2, "emergency_reserve": 3}
    usable: list[tuple[int, str]] = []
    for assignment in assignments:
        if not isinstance(assignment, dict) or assignment.get("blocks_current_spending"):
            continue
        bucket = str(assignment.get("bucket") or "")
        asset_id = assignment.get("asset_id")
        if bucket not in bucket_rank or not asset_id:
            continue
        usable.append((bucket_rank[bucket], str(asset_id)))
    if not usable:
        return ["review_withdrawal_order"]
    return [asset_id for _, asset_id in sorted(usable)]


def _decumulation_policy_data(values: dict[str, Any], data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "decumulation-policy-set/v1",
        "record_type": "DecumulationPolicySet",
        "household_id": values["household_id"],
        "as_of_date": values["as_of_date"],
        "base_currency": str(values["base_currency"]).upper(),
        "current_age": _int_or_default(values.get("current_age"), 60),
        "policies": [
            {
                "policy_id": "wizard_policy",
                "label": "Wizard policy",
                "retirement_age": _int_or_default(values.get("retirement_age"), 67),
                "end_age": _int_or_default(values.get("end_age"), 95),
                "annual_spending_need": str(values.get("annual_spending_need") or "0.00"),
                "cash_buffer_target": str(values.get("cash_buffer_target") or "0.00"),
                "withdrawal_order": _list_or_default(values.get("withdrawal_order"), ["review_withdrawal_order"]),
                "include_rita": bool(values.get("include_rita", False)),
                "annual_return_sequence": _list_or_default(values.get("annual_returns"), ["0.00"]),
                "withdrawal_tax_rate": str(values.get("withdrawal_tax_rate") or "0.00"),
                "pension_tax_rate": str(values.get("pension_tax_rate") or "0.00"),
                "rita_tax_rate": str(values.get("rita_tax_rate") or "0.00"),
            }
        ],
        "data_gaps": data_gaps,
    }


def _pension_contribution_wizard_defaults(existing: dict[str, Any] | None) -> dict[str, Any]:
    context = _pension_contribution_context_defaults()
    if existing is None:
        return context
    options = existing.get("options") if isinstance(existing.get("options"), list) else []
    first_nonzero = _first_nonzero_pension_contribution_option(options)
    return {
        "household_id": str(existing.get("household_id") or context["household_id"]),
        "as_of_date": str(existing.get("as_of_date") or context["as_of_date"]),
        "tax_year": _int_or_default(existing.get("tax_year"), context["tax_year"]),
        "jurisdiction": str(existing.get("jurisdiction") or context["jurisdiction"]),
        "marginal_tax_rate": str(existing.get("marginal_tax_rate") or context["marginal_tax_rate"]),
        "already_deducted_contributions": str(
            existing.get("already_deducted_contributions") or context["already_deducted_contributions"]
        ),
        "first_employment_extra_deduction_room": str(
            existing.get("first_employment_extra_deduction_room") or context["first_employment_extra_deduction_room"]
        ),
        "available_liquidity": str(existing.get("available_liquidity") or context["available_liquidity"]),
        "minimum_liquidity_after_contributions": str(
            existing.get("minimum_liquidity_after_contributions") or context["minimum_liquidity_after_contributions"]
        ),
        "employee_contribution": str(first_nonzero.get("employee_contribution") or context["employee_contribution"]),
        "employer_contribution": str(first_nonzero.get("employer_contribution") or context["employer_contribution"]),
        "tfr_transfer": str(first_nonzero.get("tfr_transfer") or context["tfr_transfer"]),
        "opportunity_cost_rate": str(first_nonzero.get("opportunity_cost_rate") or context["opportunity_cost_rate"]),
    }


def _pension_contribution_context_defaults() -> dict[str, Any]:
    liquidity_input = _read_optional_json(default_liquidity_plan_input())
    liquidity_snapshot = _read_optional_json(default_liquidity_plan_output())
    as_of_date = str(liquidity_input.get("as_of_date") or "2026-01-01")
    try:
        tax_year = date.fromisoformat(as_of_date).year
    except ValueError:
        tax_year = 2026
    return {
        "household_id": str(liquidity_input.get("household_id") or "household_private"),
        "as_of_date": as_of_date,
        "tax_year": tax_year,
        "jurisdiction": "IT",
        "marginal_tax_rate": "0.00",
        "already_deducted_contributions": "0.00",
        "first_employment_extra_deduction_room": "0.00",
        "available_liquidity": _available_liquidity_from_liquidity_snapshot(liquidity_snapshot),
        "minimum_liquidity_after_contributions": _cash_buffer_from_liquidity(liquidity_input, liquidity_snapshot),
        "employee_contribution": "0.00",
        "employer_contribution": "0.00",
        "tfr_transfer": "0.00",
        "opportunity_cost_rate": "0.00",
    }


def _first_nonzero_pension_contribution_option(options: Any) -> dict[str, Any]:
    if not isinstance(options, list):
        return {}
    for option in options:
        if not isinstance(option, dict):
            continue
        if any(str(option.get(field) or "0.00") != "0.00" for field in ("employee_contribution", "employer_contribution", "tfr_transfer")):
            return option
    return {}


def _available_liquidity_from_liquidity_snapshot(liquidity_snapshot: dict[str, Any]) -> str:
    buckets = liquidity_snapshot.get("buckets") if isinstance(liquidity_snapshot.get("buckets"), dict) else {}
    total = Decimal("0.00")
    for bucket in ("emergency_reserve", "short_term"):
        summary = buckets.get(bucket) if isinstance(buckets.get(bucket), dict) else {}
        total += _decimal_or_zero(summary.get("total_value"))
    return _format_cli_money(total)


def _pension_contribution_input_data(values: dict[str, Any], data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    employee = str(values.get("employee_contribution") or "0.00")
    employer = str(values.get("employer_contribution") or "0.00")
    tfr = str(values.get("tfr_transfer") or "0.00")
    opportunity = str(values.get("opportunity_cost_rate") or "0.00")
    options = [
        {
            "option_id": "no_additional_contribution",
            "label": "No additional contribution",
            "employee_contribution": "0.00",
            "employer_contribution": "0.00",
            "tfr_transfer": "0.00",
            "opportunity_cost_rate": opportunity,
            "horizon_years": 1,
        }
    ]
    if employee != "0.00" or employer != "0.00":
        options.append(
            {
                "option_id": "declared_employee_contribution",
                "label": "Declared employee contribution",
                "employee_contribution": employee,
                "employer_contribution": "0.00",
                "tfr_transfer": "0.00",
                "opportunity_cost_rate": opportunity,
                "horizon_years": 1,
            }
        )
    if employer != "0.00":
        options.append(
            {
                "option_id": "declared_employee_plus_employer",
                "label": "Declared employee contribution plus employer match",
                "employee_contribution": employee,
                "employer_contribution": employer,
                "tfr_transfer": "0.00",
                "opportunity_cost_rate": opportunity,
                "horizon_years": 1,
            }
        )
    if tfr != "0.00":
        options.append(
            {
                "option_id": "declared_employee_plus_tfr",
                "label": "Declared employee contribution plus TFR transfer",
                "employee_contribution": employee,
                "employer_contribution": "0.00",
                "tfr_transfer": tfr,
                "opportunity_cost_rate": opportunity,
                "horizon_years": 1,
            }
        )
    return {
        "schema_version": "pension-contribution-input/v1",
        "record_type": "PensionContributionInput",
        "household_id": values["household_id"],
        "as_of_date": values["as_of_date"],
        "tax_year": _int_or_default(values.get("tax_year"), 2026),
        "jurisdiction": str(values.get("jurisdiction") or "IT").upper(),
        "marginal_tax_rate": str(values.get("marginal_tax_rate") or "0.00"),
        "already_deducted_contributions": str(values.get("already_deducted_contributions") or "0.00"),
        "first_employment_extra_deduction_room": str(values.get("first_employment_extra_deduction_room") or "0.00"),
        "available_liquidity": str(values.get("available_liquidity") or "0.00"),
        "minimum_liquidity_after_contributions": str(values.get("minimum_liquidity_after_contributions") or "0.00"),
        "options": options,
        "data_gaps": data_gaps,
    }


def _it_es_eu_pension_wizard_defaults(existing: dict[str, Any] | None) -> dict[str, Any]:
    reconciliation = _read_optional_wizard_json(
        default_spanish_contribution_reconciliation_output(),
        ItEsEuPensionProRataError,
        "Spanish contribution reconciliation snapshot",
    )
    es_months = _reconciliation_covered_months(reconciliation)
    if existing:
        periods = existing.get("insurance_periods") if isinstance(existing.get("insurance_periods"), list) else []
        it_period = next((item for item in periods if isinstance(item, dict) and item.get("country") == "IT"), {})
        es_period = next((item for item in periods if isinstance(item, dict) and item.get("country") == "ES"), {})
        theoretical = existing.get("spanish_theoretical_pension") if isinstance(existing.get("spanish_theoretical_pension"), dict) else {}
        return {
            "retirement_date": str(existing.get("retirement_date") or "2035-12"),
            "date_of_birth": str(existing.get("date_of_birth") or "1968-01-01"),
            "recent_contribution_anchor_date": str(existing.get("recent_contribution_anchor_date") or "2035-12-01"),
            "italy_months": _period_month_count(it_period, 180),
            "italy_end_month": str(it_period.get("end_date", "2035-12")[:7]),
            "spain_months": _period_month_count(es_period, len(es_months) or 1),
            "spain_end_month": str(es_period.get("end_date", (max(es_months) if es_months else "2019-04"))[:7]),
            "no_future_spanish_contributions": True,
            "spanish_theoretical_monthly": str(theoretical.get("monthly_gross_amount") or "0.00"),
            "payments_per_year": _int_or_default(theoretical.get("payments_per_year"), 14),
        }
    return {
        "retirement_date": "2035-12",
        "date_of_birth": "1968-01-01",
        "recent_contribution_anchor_date": "2035-12-01",
        "italy_months": 180,
        "italy_end_month": "2035-12",
        "spain_months": len(es_months) or 1,
        "spain_end_month": max(es_months) if es_months else "2019-04",
        "no_future_spanish_contributions": True,
        "spanish_theoretical_monthly": "0.00",
        "payments_per_year": 14,
    }


def _it_es_eu_pension_input_data(values: dict[str, Any]) -> dict[str, Any]:
    italy_months = max(0, int(values["italy_months"]))
    spain_months = max(0, int(values["spain_months"]))
    data_gaps = _wizard_gaps(
        [
            (italy_months <= 0, "missing_italian_contribution_months", "Italian contribution months must be declared."),
            (spain_months <= 0, "missing_spanish_contribution_months", "Spanish contribution months must be declared."),
            (
                values["no_future_spanish_contributions"] is not True,
                "future_spanish_contributions_not_confirmed",
                "Future Spanish contribution assumption must be explicitly confirmed.",
            ),
            (
                str(values["spanish_theoretical_monthly"]) == "0.00",
                "missing_spanish_theoretical_amount",
                "Spanish theoretical pension from Spanish-only bases must be supplied before pro-rata can be calculated.",
            ),
        ]
    )
    periods = []
    if italy_months > 0:
        periods.append(_wizard_period("IT", italy_months, values["italy_end_month"], "explicit-italian-contribution-history"))
    if spain_months > 0:
        periods.append(_wizard_period("ES", spain_months, values["spain_end_month"], "reconciled-spanish-contribution-history"))

    data: dict[str, Any] = {
        "schema_version": "it-es-eu-pension-pro-rata-input/v1",
        "scenario": "ordinary",
        "retirement_date": values["retirement_date"],
        "date_of_birth": values["date_of_birth"],
        "recent_contribution_anchor_date": values["recent_contribution_anchor_date"],
        "inps_history_status": "complete_dated_history" if italy_months > 0 else "missing",
        "future_assumptions_status": "explicit" if values["no_future_spanish_contributions"] else "missing",
        "sources": [
            {"source_id": "it-es-eu-pension-wizard", "type": "user_declared_assumptions"},
            {"source_id": "no-future-spanish-contributions", "type": "explicit_future_assumption"},
        ],
        "insurance_periods": periods,
        "data_gaps": data_gaps,
    }
    if str(values["spanish_theoretical_monthly"]) != "0.00":
        monthly = Decimal(str(values["spanish_theoretical_monthly"]))
        payments = int(values["payments_per_year"])
        data["spanish_theoretical_pension"] = {
            "monthly_gross_amount": str(monthly.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "annual_gross_amount": str((monthly * Decimal(payments)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "currency": "EUR",
            "payments_per_year": payments,
            "source": "explicit user input or professional estimate",
            "source_country": "ES",
            "basis": "spanish_only_bases",
        }
    return data


def _wizard_period(country: str, months: int, end_month: str, source_document: str) -> dict[str, Any]:
    start_month = _add_months(end_month, -(months - 1))
    return {
        "country": country,
        "start_date": f"{start_month}-01",
        "end_date": _month_end_date(end_month),
        "period_type": "compulsory",
        "source_document": source_document,
    }


def _reconciliation_covered_months(reconciliation: dict[str, Any] | None) -> list[str]:
    if not reconciliation:
        return []
    months = reconciliation.get("months")
    if not isinstance(months, list):
        return []
    result = [
        str(item["month"])
        for item in months
        if isinstance(item, dict) and item.get("covered_by_vida_laboral") and isinstance(item.get("month"), str)
    ]
    return sorted(result)


def _period_month_count(period: dict[str, Any], default: int) -> int:
    start = period.get("start_date")
    end = period.get("end_date")
    if not isinstance(start, str) or not isinstance(end, str):
        return default
    return max(1, _month_index_cli(end[:7]) - _month_index_cli(start[:7]) + 1)


def _add_months(month: str, delta: int) -> str:
    index = _month_index_cli(month) + delta
    year = index // 12
    month_number = index % 12 + 1
    return f"{year:04d}-{month_number:02d}"


def _month_index_cli(month: str) -> int:
    if len(month) != 7 or month[4] != "-" or not month[:4].isdigit() or not month[5:7].isdigit():
        raise ItEsEuPensionProRataError(f"Month must be YYYY-MM: {month}")
    month_number = int(month[5:7])
    if month_number < 1 or month_number > 12:
        raise ItEsEuPensionProRataError(f"Month must be YYYY-MM: {month}")
    return int(month[:4]) * 12 + month_number - 1


def _month_end_date(month: str) -> str:
    year = int(month[:4])
    month_number = int(month[5:7])
    return f"{month}-{calendar.monthrange(year, month_number)[1]:02d}"


def _int_or_default(value: Any, default: int) -> int:
    return value if isinstance(value, int) else default


def _list_or_default(value: Any, default: list[str]) -> list[str]:
    if isinstance(value, list) and value:
        return [str(item) for item in value]
    return default


def _project_annual_need(current_monthly_spending: str, annual_cost_growth: str, years: int) -> str:
    try:
        monthly = Decimal(str(current_monthly_spending))
        growth = Decimal(str(annual_cost_growth))
    except (InvalidOperation, TypeError) as exc:
        raise PlanningGoalsError("Spesa mensile e crescita annua del costo della vita devono essere numeri.") from exc
    if monthly < 0:
        raise PlanningGoalsError("La spesa mensile non puo' essere negativa.")
    if growth < Decimal("-1"):
        raise PlanningGoalsError("La crescita annua del costo della vita non puo' essere inferiore a -1.")
    factor = (Decimal("1") + growth) ** years
    return str((monthly * Decimal("12") * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _prompt_text(label: str, default: str) -> str:
    value = input(f"{label} [{default}]: ").strip()
    return value or default


def _prompt_country_code(label: str, default: str) -> str:
    while True:
        value = _prompt_text(label, default).upper()
        if len(value) == 2 and value.isalpha():
            return value
        print("Valore non valido: inserisci un codice paese ISO a 2 lettere, ad esempio IT o ES.")


def _prompt_date(label: str, default: str) -> str:
    while True:
        value = _prompt_text(label, default)
        try:
            date.fromisoformat(value)
        except ValueError:
            print("Valore non valido: inserisci una data YYYY-MM-DD.")
            continue
        return value


def _prompt_month(label: str, default: str) -> str:
    while True:
        value = _prompt_text(label, default)
        try:
            _month_index_cli(value)
        except ItEsEuPensionProRataError:
            print("Valore non valido: inserisci un mese YYYY-MM.")
            continue
        return value


def _prompt_date_or_unknown(label: str, default: str) -> str:
    while True:
        value = _prompt_text(label, default)
        if value == "unknown":
            return value
        try:
            date.fromisoformat(value)
        except ValueError:
            print("Valore non valido: inserisci una data YYYY-MM-DD oppure unknown.")
            continue
        return value


def _prompt_int(label: str, default: int) -> int:
    value = input(f"{label} [{default}]: ").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _prompt_decimal_text(label: str, default: str) -> str:
    value = input(f"{label} [{default}]: ").strip()
    return value or default


def _prompt_choice(label: str, default: str, choices: set[str]) -> str:
    value = input(f"{label} [{default}]: ").strip().lower()
    return value if value in choices else default


def _prompt_bool(label: str, default: bool) -> bool:
    default_label = "yes" if default else "no"
    value = input(f"{label} [{default_label}]: ").strip().lower()
    if value in {"yes", "y", "true", "1"}:
        return True
    if value in {"no", "n", "false", "0"}:
        return False
    return default


def _prompt_list(label: str, default: list[str]) -> list[str]:
    value = input(f"{label} [{', '.join(default)}]: ").strip()
    if not value:
        return default
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or default


def _wizard_gaps(items: list[tuple[bool, str, str]]) -> list[dict[str, str]]:
    return [{"code": code, "message": message} for condition, code, message in items if condition]


def _non_placeholder_gaps(raw_gaps: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_gaps, list):
        return []
    return [
        gap
        for gap in raw_gaps
        if isinstance(gap, dict) and gap.get("code") not in {"replace_with_known_gap_or_remove", "draft_not_completed"}
    ]


def planning_goals_status(input_path: Path, draft_path: Path, output_path: Path, timeline_path: Path) -> dict[str, str]:
    if output_path.exists():
        return {
            "status": "snapshot_ready",
            "message": f"snapshot exists: {output_path}",
            "next_action": "run `fo planning goals validate` after changing goals, or continue with the next V4 workflow",
        }
    if input_path.exists() and _is_unedited_planning_goals_draft(input_path):
        return {
            "status": "draft_needs_editing",
            "message": f"input exists but is still an unedited draft: {input_path}",
            "next_action": "run `fo planning goals wizard --overwrite` to answer guided questions, then `fo planning goals validate`",
        }
    if input_path.exists():
        if timeline_path.exists():
            next_action = "run `fo planning goals validate`"
        else:
            next_action = "run `fo household timeline validate`, then `fo planning goals validate`"
        return {
            "status": "input_ready",
            "message": f"input exists: {input_path}",
            "next_action": next_action,
        }
    if draft_path.exists():
        return {
            "status": "input_missing",
            "message": f"private input is missing; draft exists: {draft_path}",
            "next_action": "run `fo planning goals prepare`, edit planning-goals.json, then validate",
        }
    return {
        "status": "draft_missing",
        "message": f"private input and draft are missing: {input_path}",
        "next_action": "run `fo planning goals demo` for a synthetic smoke check",
    }


def print_planning_goals_status(status: Mapping[str, str]) -> None:
    print(f"planning goals status: {status['status']}")
    print(f"message: {status['message']}")
    print(f"next: {status['next_action']}")


def print_liquidity_plan_summary(snapshot: Mapping[str, Any], output_path: Path, prefix: str = "planning liquidity") -> None:
    reserve = snapshot["emergency_reserve"]
    blocked_assets = snapshot.get("blocked_current_spending_assets", [])
    gaps = snapshot.get("data_gaps", [])
    buckets = snapshot.get("buckets", {})
    print(f"{prefix}: {snapshot['status']} ({output_path})")
    print(
        "reserve: "
        f"funded {reserve['funded_amount']} / target {reserve['target_amount']} "
        f"(shortfall {reserve['shortfall']} {reserve['currency']})"
    )
    print(
        "assets: "
        f"{len(snapshot.get('asset_assignments', []))} total, "
        f"{len(blocked_assets)} not usable for current spending"
    )
    if isinstance(buckets, dict) and buckets:
        bucket_parts = [
            f"{bucket}={summary.get('total_value', '0.00')}"
            for bucket, summary in buckets.items()
            if isinstance(summary, dict)
        ]
        print("buckets: " + ", ".join(bucket_parts))
    if gaps:
        print(f"gaps: {len(gaps)} total")
        for gap in gaps[:5]:
            if not isinstance(gap, dict):
                continue
            asset = f" asset={gap['asset_id']}" if gap.get("asset_id") else ""
            print(f"- {gap.get('code', 'gap')}{asset}: {gap.get('message', '')}")
        if len(gaps) > 5:
            print(f"- ... {len(gaps) - 5} more gaps in the snapshot")
    if any(isinstance(gap, dict) and gap.get("code") == "missing_asset_availability" for gap in gaps):
        print("next: run `fo household availability wizard`, then `fo household availability validate`, then rerun `fo planning liquidity build`.")
    elif reserve.get("shortfall") not in {None, "0.00"}:
        print("next: review emergency reserve funding or reduce the declared reserve target.")


def load_liquidity_plan_snapshot(snapshot_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LiquidityPlanError(
            f"Liquidity plan snapshot not found: {snapshot_path}. Run `fo planning liquidity build` first."
        ) from exc
    except json.JSONDecodeError as exc:
        raise LiquidityPlanError(f"Invalid JSON in liquidity plan snapshot: {exc}") from exc
    if not isinstance(data, dict):
        raise LiquidityPlanError("Liquidity plan snapshot must contain a JSON object")
    if data.get("schema_version") != "liquidity-plan/v1":
        raise LiquidityPlanError(f"Unsupported liquidity plan snapshot schema: {data.get('schema_version')}")
    return data


def print_liquidity_plan_explain(snapshot: Mapping[str, Any], snapshot_path: Path) -> None:
    assignments = [item for item in snapshot.get("asset_assignments", []) if isinstance(item, dict)]
    blocked_assets = [item for item in assignments if item.get("blocks_current_spending")]
    usable_assets = [item for item in assignments if not item.get("blocks_current_spending")]
    print(f"planning liquidity explain: {snapshot.get('status', 'unknown')} ({snapshot_path})")
    print(
        "summary: "
        f"{len(assignments)} asset, {len(usable_assets)} utilizzabili per spese correnti, "
        f"{len(blocked_assets)} non utilizzabili"
    )
    if blocked_assets:
        print("non utilizzabili per spese correnti:")
        for asset in blocked_assets:
            print(_format_liquidity_asset_explanation(asset))
    else:
        print("non utilizzabili per spese correnti: nessuno")
    if usable_assets:
        print("utilizzabili:")
        for bucket in ("emergency_reserve", "short_term", "medium_term", "long_term"):
            bucket_assets = [asset for asset in usable_assets if asset.get("bucket") == bucket]
            if not bucket_assets:
                continue
            total = sum((_decimal_or_zero(asset.get("value")) for asset in bucket_assets), Decimal("0.00"))
            print(f"- {bucket}: {_format_cli_money(total)} {snapshot.get('base_currency', 'EUR')} ({len(bucket_assets)} asset)")
            for asset in bucket_assets:
                print(f"  - {_asset_label(asset)}: {asset.get('value', '0.00')} {asset.get('currency', '')}".rstrip())
    gaps = snapshot.get("data_gaps", [])
    if isinstance(gaps, list) and gaps:
        print(f"data gaps: {len(gaps)} ancora da chiarire")
    print("next: per cambiare queste assegnazioni usa `fo household availability wizard --overwrite`, poi `fo planning liquidity build`.")


def _format_liquidity_asset_explanation(asset: Mapping[str, Any]) -> str:
    reasons = asset.get("reason_codes", [])
    if not isinstance(reasons, list):
        reasons = []
    readable_reasons = [_explain_liquidity_reason(str(reason)) for reason in reasons]
    readable_reasons = [reason for reason in readable_reasons if reason]
    reason_text = "; ".join(readable_reasons) if readable_reasons else "motivo non specificato nello snapshot"
    return (
        f"- {_asset_label(asset)}: {asset.get('value', '0.00')} {asset.get('currency', '')} "
        f"-> {asset.get('bucket', 'bucket sconosciuto')}; {reason_text}"
    ).rstrip()


def _asset_label(asset: Mapping[str, Any]) -> str:
    label = str(asset.get("label") or asset.get("asset_id") or "asset senza nome")
    asset_id = asset.get("asset_id")
    if asset_id and asset_id != label:
        return f"{label} [{asset_id}]"
    return label


def _explain_liquidity_reason(reason: str) -> str:
    if reason == "blocked_for_current_spending":
        return "non considerato disponibile per spese correnti"
    if reason == "unknown_liquidity":
        return "liquidabilita non dichiarata o incerta"
    if reason == "locked_until_date":
        return "prima disponibilita futura"
    if reason == "illiquid":
        return "asset illiquido"
    if reason == "immediate_liquidity":
        return "liquidita immediata"
    if reason == "volatile_not_emergency_reserve":
        return "troppo volatile per la riserva di emergenza"
    if reason == "foreign_currency_no_fx":
        return "valuta diversa senza cambio FX dichiarato"
    if reason == "missing_availability":
        return "classificazione di disponibilita mancante"
    if reason == "concentration_above_threshold":
        return "concentrazione sopra la soglia dichiarata"
    if reason.startswith("blocking_constraint:"):
        constraint = reason.split(":", 1)[1]
        labels = {
            "pension_lock": "vincolo pensionistico",
            "policy_terms": "vincoli contrattuali o di polizza",
            "mortgage_or_lien": "ipoteca, pegno o altro vincolo",
            "co_ownership": "comproprieta",
            "sale_process": "serve processo di vendita",
            "unknown": "vincolo non chiarito",
        }
        return labels.get(constraint, f"vincolo: {constraint}")
    if reason.startswith("liquidity_tier:"):
        tier = reason.split(":", 1)[1]
        labels = {
            "immediate": "liquidita immediata",
            "short_term": "liquidabile nel breve termine",
            "notice_required": "richiede preavviso o pratica",
            "medium_term": "liquidabile nel medio termine",
            "long_term": "liquidabile nel lungo termine",
            "illiquid": "illiquido",
            "unknown": "liquidabilita non dichiarata",
        }
        return labels.get(tier, f"liquidabilita: {tier}")
    return reason.replace("_", " ")


def _decimal_or_zero(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _format_cli_money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def format_asset_availability_error(exc: AssetAvailabilityError) -> str:
    message = str(exc)
    if "references unknown asset" not in message:
        return message
    unknown_assets: list[str] = []
    for part in message.split(";"):
        marker = "references unknown asset:"
        if marker in part:
            unknown_assets.append(part.split(marker, 1)[1].strip())
    preview = ", ".join(unknown_assets[:5])
    extra = f" and {len(unknown_assets) - 5} more" if len(unknown_assets) > 5 else ""
    return (
        "Asset availability refers to asset ids that are not present in the ownership graph "
        f"({preview}{extra}). This usually means you classified net-worth assets before updating ownership. "
        "For the liquidity plan, run `fo household availability validate --skip-ownership-check`; "
        "to change classifications, run `fo household availability wizard --overwrite`."
    )


def format_planning_goals_error(exc: PlanningGoalsError, input_path: Path) -> str:
    message = str(exc)
    if "Planning goals file not found:" in message:
        return (
            f"{message}. Run `fo planning goals prepare` to create the editable private input, "
            "or `fo planning goals demo` for a synthetic smoke check."
        )
    if _is_unedited_planning_goals_draft(input_path):
        return (
            f"Planning goals input is still the starter draft: {input_path}. "
            "Run `fo planning goals wizard --overwrite` to answer guided questions using that draft as a base; "
            "then run `fo planning goals validate`."
        )
    return message


def format_pension_contribution_error(exc: PensionContributionOptionsError, input_path: Path) -> str:
    message = str(exc)
    if "pension contribution input not found:" in message:
        return f"{message}. Run `fo planning pension-contributions wizard`, then `fo planning pension-contributions build`."
    return message


def _is_unedited_planning_goals_draft(input_path: Path) -> bool:
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    gaps = data.get("data_gaps", [])
    if not isinstance(gaps, list):
        return False
    return any(isinstance(gap, dict) and gap.get("code") == "draft_not_completed" for gap in gaps)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fo", description="Family Office engine CLI")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("validate", help="Verify the expected multi-repository layout")
    assumptions = subparsers.add_parser("assumptions", help="Manage manual assumptions")
    assumptions_subparsers = assumptions.add_subparsers(dest="assumptions_command")
    prepare_parser = assumptions_subparsers.add_parser(
        "prepare",
        help="Prepare a private assumptions draft and checklist",
    )
    prepare_parser.add_argument(
        "--template",
        type=Path,
        default=default_assumptions_template(),
        help="Assumptions template JSON path",
    )
    prepare_parser.add_argument(
        "--draft",
        type=Path,
        default=default_assumptions_draft(),
        help="Output draft JSON path",
    )
    prepare_parser.add_argument(
        "--checklist",
        type=Path,
        default=default_assumptions_checklist(),
        help="Output checklist Markdown path",
    )
    prepare_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing draft/checklist files",
    )
    import_parser = assumptions_subparsers.add_parser(
        "import",
        help="Validate and normalize manual assumptions from JSON",
    )
    import_parser.add_argument(
        "--input",
        type=Path,
        default=default_assumptions_input(),
        help="Input assumptions JSON path",
    )
    import_parser.add_argument(
        "--output",
        type=Path,
        default=default_assumptions_output(),
        help="Output normalized snapshot JSON path",
    )
    check_parser = assumptions_subparsers.add_parser(
        "check",
        help="Check whether manual assumptions are ready for simulations",
    )
    check_parser.add_argument(
        "--input",
        type=Path,
        default=default_assumptions_input(),
        help="Private assumptions JSON path",
    )
    check_parser.add_argument(
        "--template",
        type=Path,
        default=default_assumptions_template(),
        help="Assumptions template JSON path",
    )
    check_parser.add_argument(
        "--snapshot",
        type=Path,
        default=default_assumptions_output(),
        help="Normalized manual assumptions snapshot JSON path",
    )
    check_parser.add_argument(
        "--output",
        type=Path,
        default=default_assumptions_readiness_output(),
        help="Output readiness snapshot JSON path",
    )
    documents = subparsers.add_parser("documents", help="Inspect workspace documents")
    documents_subparsers = documents.add_subparsers(dest="documents_command")
    inventory_parser = documents_subparsers.add_parser(
        "inventory",
        help="Build a deterministic inventory of inbox documents",
    )
    inventory_parser.add_argument(
        "--inbox",
        type=Path,
        default=default_inbox_path(),
        help="Workspace inbox directory",
    )
    inventory_parser.add_argument(
        "--output",
        type=Path,
        default=default_document_inventory_output(),
        help="Output document inventory snapshot JSON path",
    )
    organize_parser = documents_subparsers.add_parser(
        "organize",
        help="Plan or apply organization from inbox to documents",
    )
    organize_parser.add_argument(
        "--inbox",
        type=Path,
        default=default_inbox_path(),
        help="Workspace inbox directory",
    )
    organize_parser.add_argument(
        "--documents",
        type=Path,
        default=default_documents_path(),
        help="Workspace classified documents directory",
    )
    organize_parser.add_argument(
        "--manifest",
        type=Path,
        default=default_document_manifest_output(),
        help="Output document organization manifest JSON path",
    )
    organize_parser.add_argument(
        "--apply",
        action="store_true",
        help="Move files after writing planned operations",
    )
    pension = subparsers.add_parser("pension", help="Import pension sources")
    pension_subparsers = pension.add_subparsers(dest="pension_command")
    inps_parser = pension_subparsers.add_parser(
        "import-inps",
        help="Import INPS pension simulation PDFs",
    )
    inps_parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_inps_pension_input(),
        help="Input directory containing INPS pension PDFs",
    )
    inps_parser.add_argument(
        "--output",
        type=Path,
        default=default_inps_pension_output(),
        help="Output INPS pension snapshot JSON path",
    )
    spanish_parser = pension_subparsers.add_parser(
        "import-spain",
        help="Import Spanish contribution history documents",
    )
    spanish_parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_spanish_pension_input(),
        help="Input directory containing Spanish contribution history PDFs, text files or CSV files",
    )
    spanish_parser.add_argument(
        "--output",
        type=Path,
        default=default_spanish_pension_output(),
        help="Output Spanish contribution history snapshot JSON path",
    )
    spanish_reconcile_parser = pension_subparsers.add_parser(
        "reconcile-spain",
        help="Reconcile Spanish contribution history sources",
    )
    spanish_reconcile_parser.add_argument(
        "--history-snapshot",
        type=Path,
        default=default_spanish_pension_output(),
        help="Input Spanish contribution history snapshot JSON path",
    )
    spanish_reconcile_parser.add_argument(
        "--output",
        type=Path,
        default=default_spanish_contribution_reconciliation_output(),
        help="Output Spanish contribution reconciliation snapshot JSON path",
    )
    spanish_estimate_parser = pension_subparsers.add_parser(
        "estimate-spain",
        help="Estimate ordinary Spanish statutory pension from reconciled contribution bases",
    )
    spanish_estimate_parser.add_argument(
        "--reconciliation-snapshot",
        type=Path,
        default=default_spanish_contribution_reconciliation_output(),
        help="Input Spanish contribution reconciliation snapshot JSON path",
    )
    spanish_estimate_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_spanish_statutory_pension_rule_pack(),
        help="Input Spanish statutory pension rule pack JSON path",
    )
    spanish_estimate_parser.add_argument(
        "--retirement-year",
        type=int,
        required=True,
        help="Retirement year used to select statutory rules",
    )
    spanish_estimate_parser.add_argument(
        "--retirement-month",
        type=int,
        default=12,
        help="Retirement month used to select the base reguladora lookback window",
    )
    spanish_estimate_parser.add_argument(
        "--scenario",
        choices=["ordinary"],
        default="ordinary",
        help="Spanish statutory pension scenario to estimate",
    )
    spanish_estimate_parser.add_argument(
        "--output",
        type=Path,
        default=default_spanish_statutory_pension_output(),
        help="Output Spanish statutory pension estimate snapshot JSON path",
    )
    eu_coordination_parser = pension_subparsers.add_parser(
        "coordinate-it-es",
        help="Build an EU pension coordination dossier for Italy and Spain",
    )
    eu_coordination_parser.add_argument(
        "--inps-snapshot",
        type=Path,
        default=default_inps_pension_output(),
        help="Input INPS pension snapshot JSON path",
    )
    eu_coordination_parser.add_argument(
        "--spanish-pension-snapshot",
        type=Path,
        default=default_spanish_statutory_pension_output(),
        help="Input Spanish statutory pension estimate snapshot JSON path",
    )
    eu_coordination_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_eu_pension_coordination_rule_pack(),
        help="Input EU pension coordination rule pack JSON path",
    )
    eu_coordination_parser.add_argument(
        "--italian-contribution-months",
        type=int,
        help="Explicit normalized Italian contribution months for EU coordination",
    )
    eu_coordination_parser.add_argument(
        "--output",
        type=Path,
        default=default_eu_pension_coordination_output(),
        help="Output EU pension coordination snapshot JSON path",
    )
    pension_income_parser = pension_subparsers.add_parser(
        "compose-income",
        help="Compose pension income streams from available pension snapshots",
    )
    pension_income_parser.add_argument(
        "--inps-snapshot",
        type=Path,
        default=default_inps_pension_output(),
        help="Input INPS pension snapshot JSON path",
    )
    pension_income_parser.add_argument(
        "--spanish-pension-snapshot",
        type=Path,
        default=default_spanish_statutory_pension_output(),
        help="Input Spanish statutory pension estimate snapshot JSON path",
    )
    pension_income_parser.add_argument(
        "--rita-options-snapshot",
        type=Path,
        default=default_rita_options_output(),
        help="Input RITA options snapshot JSON path",
    )
    pension_income_parser.add_argument(
        "--eu-coordination-snapshot",
        type=Path,
        default=default_eu_pension_coordination_output(),
        help="Input EU pension coordination snapshot JSON path",
    )
    pension_income_parser.add_argument(
        "--no-rita",
        action="store_true",
        help="Exclude RITA options from the composed pension income snapshot",
    )
    pension_income_parser.add_argument(
        "--output",
        type=Path,
        default=default_pension_income_output(),
        help="Output pension income snapshot JSON path",
    )
    expenses = subparsers.add_parser("expenses", help="Build expense planning snapshots")
    expenses_subparsers = expenses.add_subparsers(dest="expenses_command")
    lifecycle_expenses_parser = expenses_subparsers.add_parser(
        "build-lifecycle",
        help="Build lifecycle expense yearly cashflow from an explicit plan",
    )
    lifecycle_expenses_parser.add_argument(
        "--input",
        type=Path,
        default=default_lifecycle_expenses_input(),
        help="Input lifecycle expense plan JSON path",
    )
    lifecycle_expenses_parser.add_argument(
        "--household-snapshot",
        type=Path,
        default=default_household_facts_output(),
        help="Input household facts snapshot JSON path",
    )
    lifecycle_expenses_parser.add_argument(
        "--timeline-snapshot",
        type=Path,
        default=default_timeline_events_output(),
        help="Input timeline events snapshot JSON path",
    )
    lifecycle_expenses_parser.add_argument(
        "--output",
        type=Path,
        default=default_lifecycle_expenses_output(),
        help="Output lifecycle expenses snapshot JSON path",
    )
    investments = subparsers.add_parser("investments", help="Import investment statements")
    investments_subparsers = investments.add_subparsers(dest="investments_command")
    investments_import_parser = investments_subparsers.add_parser(
        "import",
        help="Import classified Italy/Spain investment statements",
    )
    investments_import_parser.add_argument(
        "--italy-dir",
        type=Path,
        default=default_investments_italy_input(),
        help="Classified Italian investment documents directory",
    )
    investments_import_parser.add_argument(
        "--spain-dir",
        type=Path,
        default=default_investments_spain_input(),
        help="Classified Spanish investment documents directory",
    )
    investments_import_parser.add_argument(
        "--directa-dir",
        type=Path,
        default=default_investments_directa_input(),
        help="Classified Directa investment documents directory",
    )
    investments_import_parser.add_argument(
        "--output",
        type=Path,
        default=default_investments_output(),
        help="Output investments snapshot JSON path",
    )
    bank_insurance = subparsers.add_parser("bank-insurance", help="Import bank and insurance documents")
    bank_insurance_subparsers = bank_insurance.add_subparsers(dest="bank_insurance_command")
    bank_insurance_import_parser = bank_insurance_subparsers.add_parser(
        "import",
        help="Import classified bank balances and insurance policy documents",
    )
    bank_insurance_import_parser.add_argument(
        "--bank-dir",
        type=Path,
        default=default_bank_documents_input(),
        help="Classified bank documents directory",
    )
    bank_insurance_import_parser.add_argument(
        "--insurance-dir",
        type=Path,
        default=default_insurance_documents_input(),
        help="Classified insurance documents directory",
    )
    bank_insurance_import_parser.add_argument(
        "--output",
        type=Path,
        default=default_bank_insurance_output(),
        help="Output bank-insurance snapshot JSON path",
    )
    payroll = subparsers.add_parser("payroll", help="Import payroll documents")
    payroll_subparsers = payroll.add_subparsers(dest="payroll_command")
    payroll_import_parser = payroll_subparsers.add_parser(
        "import",
        help="Import classified payslip documents",
    )
    payroll_import_parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_payroll_input(),
        help="Input directory containing payroll PDFs",
    )
    payroll_import_parser.add_argument(
        "--output",
        type=Path,
        default=default_payroll_output(),
        help="Output payroll snapshot JSON path",
    )
    payroll_diagnose_parser = payroll_subparsers.add_parser(
        "diagnose",
        help="Diagnose payroll input documents without writing a snapshot",
    )
    payroll_diagnose_parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_payroll_input(),
        help="Input directory containing payroll PDFs",
    )
    payroll_diagnose_parser.add_argument(
        "--json",
        action="store_true",
        help="Print full diagnostics as JSON",
    )
    cashflow = subparsers.add_parser("cashflow", help="Build cashflow snapshots")
    cashflow_subparsers = cashflow.add_subparsers(dest="cashflow_command")
    earned_income_parser = cashflow_subparsers.add_parser(
        "earned-income",
        help="Build earned income cashflow from payroll snapshot",
    )
    earned_income_parser.add_argument(
        "--payroll-snapshot",
        type=Path,
        default=default_payroll_output(),
        help="Input payroll snapshot JSON path",
    )
    earned_income_parser.add_argument(
        "--assumptions-snapshot",
        type=Path,
        default=default_assumptions_output(),
        help="Optional manual assumptions snapshot JSON path used for duplication checks",
    )
    earned_income_parser.add_argument(
        "--output",
        type=Path,
        default=default_earned_income_cashflow_output(),
        help="Output earned income cashflow snapshot JSON path",
    )
    fonte = subparsers.add_parser("fonte", help="Import Fon.Te pension fund data")
    fonte_subparsers = fonte.add_subparsers(dest="fonte_command")
    fonte_import_parser = fonte_subparsers.add_parser(
        "import",
        help="Validate and normalize Fon.Te CSV data",
    )
    fonte_import_parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Input Fon.Te CSV path for synthetic fixtures or legacy normalized exports",
    )
    fonte_import_parser.add_argument(
        "--position-pdf",
        type=Path,
        default=None,
        help="Input Fon.Te general position PDF path",
    )
    fonte_import_parser.add_argument(
        "--contributions-xlsx",
        type=Path,
        default=None,
        help="Input Fon.Te contributions Excel path",
    )
    fonte_import_parser.add_argument(
        "--output",
        type=Path,
        default=default_fonte_output(),
        help="Output normalized snapshot JSON path",
    )
    net_worth = subparsers.add_parser("net-worth", help="Consolidate net worth snapshots")
    net_worth_subparsers = net_worth.add_subparsers(dest="net_worth_command")
    consolidate_parser = net_worth_subparsers.add_parser(
        "consolidate",
        help="Build a consolidated net worth snapshot",
    )
    consolidate_parser.add_argument(
        "--fonte-snapshot",
        type=Path,
        default=default_fonte_output(),
        help="Input Fon.Te snapshot JSON path",
    )
    consolidate_parser.add_argument(
        "--assumptions-snapshot",
        type=Path,
        default=default_assumptions_output(),
        help="Optional manual assumptions snapshot JSON path",
    )
    consolidate_parser.add_argument(
        "--investments-snapshot",
        type=Path,
        default=default_investments_snapshot(),
        help="Input investments snapshot JSON path",
    )
    consolidate_parser.add_argument(
        "--bank-insurance-snapshot",
        type=Path,
        default=default_bank_insurance_snapshot(),
        help="Input bank-insurance snapshot JSON path",
    )
    consolidate_parser.add_argument(
        "--output",
        type=Path,
        default=default_net_worth_output(),
        help="Output net worth snapshot JSON path",
    )
    tax_events = subparsers.add_parser("tax-events", help="Generate deterministic tax event snapshots")
    tax_events_subparsers = tax_events.add_subparsers(dest="tax_events_command")
    impatriati_parser = tax_events_subparsers.add_parser(
        "impatriati",
        help="Generate annual impatriati regime events",
    )
    impatriati_parser.add_argument("--start-year", type=int, default=2026)
    impatriati_parser.add_argument("--end-year", type=int, default=2029)
    impatriati_parser.add_argument("--regime", default="legacy_pre_2024")
    impatriati_parser.add_argument("--taxable-income-share", default="0.30")
    impatriati_parser.add_argument(
        "--output",
        type=Path,
        default=default_tax_events_output(),
        help="Output tax events snapshot JSON path",
    )
    tax = subparsers.add_parser("tax", help="Run deterministic tax rule calculations")
    tax_subparsers = tax.add_subparsers(dest="tax_command")
    tax_calculate_parser = tax_subparsers.add_parser(
        "calculate",
        help="Calculate tax from a versioned rule pack",
    )
    tax_calculate_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_italy_tax_rule_pack(),
        help="Input tax rule pack JSON path",
    )
    tax_calculate_parser.add_argument("--tax-year", type=int, default=2026)
    tax_calculate_parser.add_argument("--jurisdiction", default="IT")
    tax_calculate_parser.add_argument("--taxable-income", required=True)
    tax_calculate_parser.add_argument(
        "--output",
        type=Path,
        default=default_tax_calculation_output(),
        help="Output tax calculation snapshot JSON path",
    )
    tax_reconcile_parser = tax_subparsers.add_parser(
        "reconcile",
        help="Reconcile payroll and fiscal document snapshots",
    )
    tax_reconcile_parser.add_argument(
        "--payroll-snapshot",
        type=Path,
        default=default_payroll_output(),
        help="Input payroll snapshot JSON path",
    )
    tax_reconcile_parser.add_argument(
        "--tax-documents-snapshot",
        type=Path,
        default=default_tax_documents_output(),
        help="Input tax documents snapshot JSON path",
    )
    tax_reconcile_parser.add_argument(
        "--output",
        type=Path,
        default=default_tax_reconciliation_output(),
        help="Output tax reconciliation snapshot JSON path",
    )
    rita = subparsers.add_parser("rita", help="Evaluate deterministic RITA options")
    rita_subparsers = rita.add_subparsers(dest="rita_command")
    rita_optimize_parser = rita_subparsers.add_parser(
        "optimize",
        help="Build a RITA options V1 snapshot from explicit inputs",
    )
    rita_optimize_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_rita_rule_pack(),
        help="Input RITA rule pack path",
    )
    rita_optimize_parser.add_argument("--age", type=int, required=True)
    rita_optimize_parser.add_argument("--years-to-public-pension", required=True)
    rita_optimize_parser.add_argument(
        "--employment-status",
        required=True,
        help="Use ceased, unemployed or not_employed for non-working RITA checks",
    )
    rita_optimize_parser.add_argument("--unemployed-months", type=int)
    rita_optimize_parser.add_argument("--mandatory-contribution-years")
    rita_optimize_parser.add_argument("--complementary-pension-years", required=True)
    rita_optimize_parser.add_argument("--complementary-balance")
    rita_optimize_parser.add_argument("--duration-months", type=int)
    rita_optimize_parser.add_argument("--monthly-need")
    rita_optimize_parser.add_argument(
        "--output",
        type=Path,
        default=default_rita_options_output(),
        help="Output RITA options snapshot JSON path",
    )
    estate = subparsers.add_parser("estate", help="Build succession planning baselines")
    estate_subparsers = estate.add_subparsers(dest="estate_command")
    estate_baseline_parser = estate_subparsers.add_parser(
        "baseline",
        help="Build an estate baseline V1 snapshot",
    )
    estate_baseline_parser.add_argument(
        "--net-worth-snapshot",
        type=Path,
        default=default_net_worth_output(),
        help="Input net worth snapshot JSON path",
    )
    estate_baseline_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_estate_rule_pack(),
        help="Input estate rule pack JSON path",
    )
    estate_baseline_parser.add_argument(
        "--has-spouse",
        action="store_true",
        help="Declare spouse as present for simple intestate share rules",
    )
    estate_baseline_parser.add_argument(
        "--children-count",
        type=int,
        default=0,
        help="Number of children for simple intestate share rules",
    )
    estate_baseline_parser.add_argument(
        "--prior-donations",
        help="Optional declared prior donations amount used only as an explicit notional input",
    )
    estate_baseline_parser.add_argument(
        "--output",
        type=Path,
        default=default_estate_baseline_output(),
        help="Output estate baseline snapshot JSON path",
    )
    household = subparsers.add_parser("household", help="Validate household facts")
    household_subparsers = household.add_subparsers(dest="household_command")
    household_validate_parser = household_subparsers.add_parser(
        "validate",
        help="Validate and normalize household facts",
    )
    household_validate_parser.add_argument(
        "--input",
        type=Path,
        default=default_household_facts_input(),
        help="Input household facts JSON path",
    )
    household_validate_parser.add_argument(
        "--output",
        type=Path,
        default=default_household_facts_output(),
        help="Output household facts snapshot JSON path",
    )
    household_ownership_parser = household_subparsers.add_parser(
        "ownership",
        help="Validate and normalize ownership and beneficiary graph",
    )
    household_ownership_subparsers = household_ownership_parser.add_subparsers(dest="household_ownership_command")
    household_ownership_validate_parser = household_ownership_subparsers.add_parser(
        "validate",
        help="Validate and normalize ownership and beneficiary graph",
    )
    household_ownership_validate_parser.add_argument(
        "--input",
        type=Path,
        default=default_ownership_graph_input(),
        help="Input ownership graph JSON path",
    )
    household_ownership_validate_parser.add_argument(
        "--household-snapshot",
        type=Path,
        default=default_household_facts_output(),
        help="Optional household facts snapshot used to validate person references",
    )
    household_ownership_validate_parser.add_argument(
        "--output",
        type=Path,
        default=default_ownership_graph_output(),
        help="Output ownership graph snapshot JSON path",
    )
    household_availability_parser = household_subparsers.add_parser(
        "availability",
        help="Validate and normalize asset classification and availability",
    )
    household_availability_subparsers = household_availability_parser.add_subparsers(
        dest="household_availability_command"
    )
    household_availability_validate_parser = household_availability_subparsers.add_parser(
        "validate",
        help="Validate and normalize asset classification and availability",
    )
    household_availability_validate_parser.add_argument(
        "--input",
        type=Path,
        default=default_asset_availability_input(),
        help="Input asset availability JSON path",
    )
    household_availability_validate_parser.add_argument(
        "--ownership-snapshot",
        type=Path,
        default=default_ownership_graph_output(),
        help="Optional ownership graph snapshot used to validate asset references",
    )
    household_availability_validate_parser.add_argument(
        "--skip-ownership-check",
        action="store_true",
        help="Do not validate asset ids against ownership graph; useful when classifying net-worth assets first",
    )
    household_availability_validate_parser.add_argument(
        "--output",
        type=Path,
        default=default_asset_availability_output(),
        help="Output asset availability snapshot JSON path",
    )
    household_availability_wizard_parser = household_availability_subparsers.add_parser(
        "wizard",
        help="Interactively classify asset availability from net-worth/v1",
    )
    household_availability_wizard_parser.add_argument(
        "--input",
        type=Path,
        default=default_asset_availability_input(),
        help="Output editable private asset availability JSON path",
    )
    household_availability_wizard_parser.add_argument(
        "--net-worth-snapshot",
        type=Path,
        default=default_net_worth_output(),
        help="Input net-worth/v1 snapshot JSON path used to list assets",
    )
    household_availability_wizard_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing asset availability input file",
    )
    household_timeline_parser = household_subparsers.add_parser(
        "timeline",
        help="Validate and normalize household timeline events",
    )
    household_timeline_subparsers = household_timeline_parser.add_subparsers(dest="household_timeline_command")
    household_timeline_validate_parser = household_timeline_subparsers.add_parser(
        "validate",
        help="Validate and normalize household timeline events",
    )
    household_timeline_validate_parser.add_argument(
        "--input",
        type=Path,
        default=default_timeline_events_input(),
        help="Input timeline events JSON path",
    )
    household_timeline_validate_parser.add_argument(
        "--policy",
        type=Path,
        default=default_timeline_policy(),
        help="Timeline overlap policy JSON path",
    )
    household_timeline_validate_parser.add_argument(
        "--household-snapshot",
        type=Path,
        default=default_household_facts_output(),
        help="Optional household facts snapshot used to validate person references",
    )
    household_timeline_validate_parser.add_argument(
        "--asset-availability-snapshot",
        type=Path,
        default=default_asset_availability_output(),
        help="Optional asset availability snapshot used to validate asset references",
    )
    household_timeline_validate_parser.add_argument(
        "--output",
        type=Path,
        default=default_timeline_events_output(),
        help="Output timeline events snapshot JSON path",
    )
    planning = subparsers.add_parser("planning", help="Validate planning contracts")
    planning_subparsers = planning.add_subparsers(dest="planning_command")
    planning_goals_parser = planning_subparsers.add_parser(
        "goals",
        help="Validate and normalize planning goals and constraints",
    )
    planning_goals_subparsers = planning_goals_parser.add_subparsers(dest="planning_goals_command")
    planning_goals_prepare_parser = planning_goals_subparsers.add_parser(
        "prepare",
        help="Create the editable private planning goals input from the workspace draft",
    )
    planning_goals_prepare_parser.add_argument(
        "--draft",
        type=Path,
        default=default_planning_goals_draft(),
        help="Planning goals draft JSON path",
    )
    planning_goals_prepare_parser.add_argument(
        "--input",
        type=Path,
        default=default_planning_goals_input(),
        help="Output editable private planning goals JSON path",
    )
    planning_goals_prepare_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing planning goals input file",
    )
    planning_goals_wizard_parser = planning_goals_subparsers.add_parser(
        "wizard",
        help="Interactively create a private planning goals JSON input",
    )
    planning_goals_wizard_parser.add_argument(
        "--input",
        type=Path,
        default=default_planning_goals_input(),
        help="Output editable private planning goals JSON path",
    )
    planning_goals_wizard_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing planning goals input file",
    )
    planning_goals_status_parser = planning_goals_subparsers.add_parser(
        "status",
        help="Show planning goals workflow status and next action",
    )
    planning_goals_status_parser.add_argument(
        "--input",
        type=Path,
        default=default_planning_goals_input(),
        help="Planning goals JSON path",
    )
    planning_goals_status_parser.add_argument(
        "--draft",
        type=Path,
        default=default_planning_goals_draft(),
        help="Planning goals draft JSON path",
    )
    planning_goals_status_parser.add_argument(
        "--timeline-snapshot",
        type=Path,
        default=default_timeline_events_output(),
        help="Timeline events snapshot path",
    )
    planning_goals_status_parser.add_argument(
        "--output",
        type=Path,
        default=default_planning_goals_output(),
        help="Planning goals snapshot JSON path",
    )
    planning_goals_validate_parser = planning_goals_subparsers.add_parser(
        "validate",
        help="Validate and normalize planning goals and constraints",
    )
    planning_goals_validate_parser.add_argument(
        "--input",
        type=Path,
        default=default_planning_goals_input(),
        help="Input planning goals JSON path",
    )
    planning_goals_validate_parser.add_argument(
        "--timeline-snapshot",
        type=Path,
        default=default_timeline_events_output(),
        help="Optional timeline events snapshot used to validate event references",
    )
    planning_goals_validate_parser.add_argument(
        "--output",
        type=Path,
        default=default_planning_goals_output(),
        help="Output planning goals snapshot JSON path",
    )
    planning_goals_demo_parser = planning_goals_subparsers.add_parser(
        "demo",
        help="Run the synthetic planning goals check with bundled examples",
    )
    planning_goals_demo_parser.add_argument(
        "--timeline-output",
        type=Path,
        default=default_timeline_events_demo_output(),
        help="Output synthetic timeline events snapshot JSON path",
    )
    planning_goals_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_planning_goals_demo_output(),
        help="Output synthetic planning goals snapshot JSON path",
    )
    planning_liquidity_parser = planning_subparsers.add_parser(
        "liquidity",
        help="Build liquidity buckets and emergency reserve plan",
    )
    planning_liquidity_subparsers = planning_liquidity_parser.add_subparsers(dest="planning_liquidity_command")
    planning_liquidity_build_parser = planning_liquidity_subparsers.add_parser(
        "build",
        help="Build liquidity-plan/v1 from explicit snapshots",
    )
    planning_liquidity_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_liquidity_plan_input(),
        help="Input liquidity plan JSON path",
    )
    planning_liquidity_build_parser.add_argument(
        "--net-worth-snapshot",
        type=Path,
        default=default_net_worth_output(),
        help="Input net worth snapshot JSON path",
    )
    planning_liquidity_build_parser.add_argument(
        "--asset-availability-snapshot",
        type=Path,
        default=default_asset_availability_output(),
        help="Input asset availability snapshot JSON path",
    )
    planning_liquidity_build_parser.add_argument(
        "--planning-goals-snapshot",
        type=Path,
        default=default_planning_goals_output(),
        help="Input planning goals snapshot JSON path",
    )
    planning_liquidity_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_liquidity_plan_output(),
        help="Output liquidity plan snapshot JSON path",
    )
    planning_liquidity_explain_parser = planning_liquidity_subparsers.add_parser(
        "explain",
        help="Explain liquidity bucket assignments from an existing snapshot",
    )
    planning_liquidity_explain_parser.add_argument(
        "--snapshot",
        type=Path,
        default=default_liquidity_plan_output(),
        help="Input liquidity plan snapshot JSON path",
    )
    planning_liquidity_wizard_parser = planning_liquidity_subparsers.add_parser(
        "wizard",
        help="Interactively create a private liquidity-plan-input/v1 JSON",
    )
    planning_liquidity_wizard_parser.add_argument(
        "--input",
        type=Path,
        default=default_liquidity_plan_input(),
        help="Output editable private liquidity plan input JSON path",
    )
    planning_liquidity_wizard_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing liquidity plan input file",
    )
    planning_liquidity_demo_parser = planning_liquidity_subparsers.add_parser(
        "demo",
        help="Run the synthetic liquidity plan check with bundled examples",
    )
    planning_liquidity_demo_parser.add_argument(
        "--planning-goals-output",
        type=Path,
        default=default_planning_goals_demo_output(),
        help="Output synthetic planning goals snapshot JSON path",
    )
    planning_liquidity_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_liquidity_plan_demo_output(),
        help="Output synthetic liquidity plan snapshot JSON path",
    )
    planning_decumulation_parser = planning_subparsers.add_parser(
        "decumulation",
        help="Compare retirement decumulation policies",
    )
    planning_decumulation_subparsers = planning_decumulation_parser.add_subparsers(
        dest="planning_decumulation_command"
    )
    planning_decumulation_build_parser = planning_decumulation_subparsers.add_parser(
        "build",
        help="Build decumulation-strategy/v1 from explicit snapshots",
    )
    planning_decumulation_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_decumulation_policy_set_input(),
        help="Input decumulation policy set JSON path",
    )
    planning_decumulation_build_parser.add_argument(
        "--net-worth-snapshot",
        type=Path,
        default=default_net_worth_output(),
        help="Input net worth snapshot JSON path",
    )
    planning_decumulation_build_parser.add_argument(
        "--liquidity-plan-snapshot",
        type=Path,
        default=default_liquidity_plan_output(),
        help="Input liquidity plan snapshot JSON path",
    )
    planning_decumulation_build_parser.add_argument(
        "--pension-income-snapshot",
        type=Path,
        default=default_pension_income_output(),
        help="Input pension income snapshot JSON path",
    )
    planning_decumulation_build_parser.add_argument(
        "--rita-options-snapshot",
        type=Path,
        default=default_rita_options_output(),
        help="Optional RITA options snapshot JSON path",
    )
    planning_decumulation_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_decumulation_strategy_output(),
        help="Output decumulation strategy snapshot JSON path",
    )
    planning_decumulation_wizard_parser = planning_decumulation_subparsers.add_parser(
        "wizard",
        help="Interactively create a private decumulation-policy-set/v1 JSON",
    )
    planning_decumulation_wizard_parser.add_argument(
        "--input",
        type=Path,
        default=default_decumulation_policy_set_input(),
        help="Output editable private decumulation policy set JSON path",
    )
    planning_decumulation_wizard_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing decumulation policy set input file",
    )
    planning_decumulation_demo_parser = planning_decumulation_subparsers.add_parser(
        "demo",
        help="Run the synthetic decumulation strategy check with bundled examples",
    )
    planning_decumulation_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_decumulation_strategy_demo_output(),
        help="Output synthetic decumulation strategy snapshot JSON path",
    )
    planning_pension_contributions_parser = planning_subparsers.add_parser(
        "pension-contributions",
        help="Compare complementary pension contribution options",
    )
    planning_pension_contributions_subparsers = planning_pension_contributions_parser.add_subparsers(
        dest="planning_pension_contributions_command"
    )
    planning_pension_contributions_build_parser = planning_pension_contributions_subparsers.add_parser(
        "build",
        help="Build pension-contribution-options/v1 from explicit input and rule pack",
    )
    planning_pension_contributions_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_pension_contribution_input(),
        help="Input pension contribution options JSON path",
    )
    planning_pension_contributions_build_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_pension_contribution_rule_pack(),
        help="Input pension contribution rule pack JSON path",
    )
    planning_pension_contributions_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_pension_contribution_output(),
        help="Output pension contribution options snapshot JSON path",
    )
    planning_pension_contributions_wizard_parser = planning_pension_contributions_subparsers.add_parser(
        "wizard",
        help="Interactively create a private pension-contribution-input/v1 JSON",
    )
    planning_pension_contributions_wizard_parser.add_argument(
        "--input",
        type=Path,
        default=default_pension_contribution_input(),
        help="Output editable private pension contribution input JSON path",
    )
    planning_pension_contributions_wizard_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing pension contribution input file",
    )
    planning_pension_contributions_demo_parser = planning_pension_contributions_subparsers.add_parser(
        "demo",
        help="Run the synthetic pension contribution options check with bundled examples",
    )
    planning_pension_contributions_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_pension_contribution_demo_output(),
        help="Output synthetic pension contribution options snapshot JSON path",
    )
    planning_tax_aware_portfolio_parser = planning_subparsers.add_parser(
        "tax-aware-portfolio",
        help="Compare tax-aware portfolio options",
    )
    planning_tax_aware_portfolio_subparsers = planning_tax_aware_portfolio_parser.add_subparsers(
        dest="planning_tax_aware_portfolio_command"
    )
    planning_tax_aware_portfolio_build_parser = planning_tax_aware_portfolio_subparsers.add_parser(
        "build",
        help="Build tax-aware-portfolio/v1 from explicit input and rule pack",
    )
    planning_tax_aware_portfolio_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_tax_aware_portfolio_input(),
        help="Input tax-aware portfolio JSON path",
    )
    planning_tax_aware_portfolio_build_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_tax_aware_investment_rule_pack(),
        help="Input tax-aware investment rule pack JSON path",
    )
    planning_tax_aware_portfolio_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_tax_aware_portfolio_output(),
        help="Output tax-aware portfolio snapshot JSON path",
    )
    planning_tax_aware_portfolio_demo_parser = planning_tax_aware_portfolio_subparsers.add_parser(
        "demo",
        help="Run the synthetic tax-aware portfolio check with bundled examples",
    )
    planning_tax_aware_portfolio_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_tax_aware_portfolio_demo_output(),
        help="Output synthetic tax-aware portfolio snapshot JSON path",
    )
    planning_it_es_pension_tax_parser = planning_subparsers.add_parser(
        "it-es-pension-tax",
        help="Classify Italy-Spain pension tax treaty treatment",
    )
    planning_it_es_pension_tax_subparsers = planning_it_es_pension_tax_parser.add_subparsers(
        dest="planning_it_es_pension_tax_command"
    )
    planning_it_es_pension_tax_classify_parser = planning_it_es_pension_tax_subparsers.add_parser(
        "classify",
        help="Build it-es-pension-tax-classification/v1 from explicit stream facts",
    )
    planning_it_es_pension_tax_classify_parser.add_argument(
        "--input",
        type=Path,
        default=default_it_es_pension_tax_classification_input(),
        help="Input IT-ES pension tax classification JSON path",
    )
    planning_it_es_pension_tax_classify_parser.add_argument(
        "--pension-income-snapshot",
        type=Path,
        default=default_pension_income_output(),
        help="Input pension income snapshot JSON path",
    )
    planning_it_es_pension_tax_classify_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_it_es_pension_tax_classification_rule_pack(),
        help="Input IT-ES pension tax classification rule pack JSON path",
    )
    planning_it_es_pension_tax_classify_parser.add_argument(
        "--output",
        type=Path,
        default=default_it_es_pension_tax_classification_output(),
        help="Output IT-ES pension tax classification snapshot JSON path",
    )
    planning_it_es_pension_tax_demo_parser = planning_it_es_pension_tax_subparsers.add_parser(
        "demo",
        help="Run the synthetic IT-ES pension tax classification check with bundled examples",
    )
    planning_it_es_pension_tax_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_it_es_pension_tax_classification_demo_output(),
        help="Output synthetic IT-ES pension tax classification snapshot JSON path",
    )
    planning_spanish_pension_net_parser = planning_subparsers.add_parser(
        "spanish-pension-net",
        help="Build net Spanish pension for an Italian tax resident",
    )
    planning_spanish_pension_net_subparsers = planning_spanish_pension_net_parser.add_subparsers(
        dest="planning_spanish_pension_net_command"
    )
    planning_spanish_pension_net_build_parser = planning_spanish_pension_net_subparsers.add_parser(
        "build",
        help="Build spanish-pension-net-it-resident/v1 from explicit tax inputs",
    )
    planning_spanish_pension_net_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_spanish_pension_net_it_resident_input(),
        help="Input Spanish pension net JSON path",
    )
    planning_spanish_pension_net_build_parser.add_argument(
        "--pension-income-snapshot",
        type=Path,
        default=default_pension_income_output(),
        help="Input pension income snapshot JSON path",
    )
    planning_spanish_pension_net_build_parser.add_argument(
        "--classification-snapshot",
        type=Path,
        default=default_it_es_pension_tax_classification_output(),
        help="Input IT-ES pension tax classification snapshot JSON path",
    )
    planning_spanish_pension_net_build_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_spanish_pension_net_it_resident_rule_pack(),
        help="Input Spanish pension net rule pack JSON path",
    )
    planning_spanish_pension_net_build_parser.add_argument(
        "--irpef-rule-pack",
        type=Path,
        default=default_italy_tax_rule_pack(),
        help="Input Italian IRPEF rule pack JSON path",
    )
    planning_spanish_pension_net_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_spanish_pension_net_it_resident_output(),
        help="Output Spanish pension net snapshot JSON path",
    )
    planning_spanish_pension_net_demo_parser = planning_spanish_pension_net_subparsers.add_parser(
        "demo",
        help="Run the synthetic Spanish pension net check with bundled examples",
    )
    planning_spanish_pension_net_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_spanish_pension_net_it_resident_demo_output(),
        help="Output synthetic Spanish pension net snapshot JSON path",
    )
    planning_it_es_foreign_assets_parser = planning_subparsers.add_parser(
        "it-es-foreign-assets",
        help="Build Italy-Spain RW, IVAFE and IVIE foreign asset monitoring",
    )
    planning_it_es_foreign_assets_subparsers = planning_it_es_foreign_assets_parser.add_subparsers(
        dest="planning_it_es_foreign_assets_command"
    )
    planning_it_es_foreign_assets_build_parser = planning_it_es_foreign_assets_subparsers.add_parser(
        "build",
        help="Build it-es-foreign-assets/v1 from explicit asset facts and rule pack",
    )
    planning_it_es_foreign_assets_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_it_es_foreign_assets_input(),
        help="Input IT-ES foreign assets JSON path",
    )
    planning_it_es_foreign_assets_build_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_it_es_foreign_assets_rule_pack(),
        help="Input IT-ES foreign asset monitoring rule pack JSON path",
    )
    planning_it_es_foreign_assets_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_it_es_foreign_assets_output(),
        help="Output IT-ES foreign assets snapshot JSON path",
    )
    planning_it_es_foreign_assets_demo_parser = planning_it_es_foreign_assets_subparsers.add_parser(
        "demo",
        help="Run the synthetic IT-ES foreign assets check with bundled examples",
    )
    planning_it_es_foreign_assets_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_it_es_foreign_assets_demo_output(),
        help="Output synthetic IT-ES foreign assets snapshot JSON path",
    )
    planning_cross_border_it_es_parser = planning_subparsers.add_parser(
        "cross-border-it-es",
        help="Compose Italy-Spain pension, tax and foreign asset dossier",
    )
    planning_cross_border_it_es_subparsers = planning_cross_border_it_es_parser.add_subparsers(
        dest="planning_cross_border_it_es_command"
    )
    planning_cross_border_it_es_build_parser = planning_cross_border_it_es_subparsers.add_parser(
        "build",
        help="Build cross-border-it-es/v1 from deterministic source snapshots",
    )
    planning_cross_border_it_es_build_parser.add_argument(
        "--pension-scenario-snapshot",
        type=Path,
        default=default_pension_scenario_output(),
        help="Input pension-scenario/v1 snapshot JSON path",
    )
    planning_cross_border_it_es_build_parser.add_argument(
        "--pension-income-snapshot",
        type=Path,
        default=default_pension_income_output(),
        help="Input pension-income/v1 snapshot JSON path",
    )
    planning_cross_border_it_es_build_parser.add_argument(
        "--pension-tax-classification-snapshot",
        type=Path,
        default=default_it_es_pension_tax_classification_output(),
        help="Input IT-ES pension tax classification snapshot JSON path",
    )
    planning_cross_border_it_es_build_parser.add_argument(
        "--spanish-pension-net-snapshot",
        type=Path,
        default=default_spanish_pension_net_it_resident_output(),
        help="Input Spanish pension net snapshot JSON path",
    )
    planning_cross_border_it_es_build_parser.add_argument(
        "--eu-pension-pro-rata-snapshot",
        type=Path,
        default=default_it_es_eu_pension_pro_rata_output(),
        help="Input IT-ES EU pension pro-rata snapshot JSON path",
    )
    planning_cross_border_it_es_build_parser.add_argument(
        "--foreign-assets-snapshot",
        type=Path,
        default=default_it_es_foreign_assets_output(),
        help="Input IT-ES foreign assets snapshot JSON path",
    )
    planning_cross_border_it_es_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_cross_border_it_es_output(),
        help="Output IT-ES cross-border dossier snapshot JSON path",
    )
    planning_cross_border_it_es_demo_parser = planning_cross_border_it_es_subparsers.add_parser(
        "demo",
        help="Run the synthetic IT-ES cross-border dossier check with bundled examples",
    )
    planning_cross_border_it_es_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_cross_border_it_es_demo_output(),
        help="Output synthetic IT-ES cross-border dossier snapshot JSON path",
    )
    planning_pension_scenario_parser = planning_subparsers.add_parser(
        "pension-scenario",
        help="Build explicit multi-scenario retirement assumptions",
    )
    planning_pension_scenario_subparsers = planning_pension_scenario_parser.add_subparsers(
        dest="planning_pension_scenario_command"
    )
    planning_pension_scenario_build_parser = planning_pension_scenario_subparsers.add_parser(
        "build",
        help="Build pension-scenario/v1 from explicit assumptions",
    )
    planning_pension_scenario_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_pension_scenario_input(),
        help="Input pension scenario JSON path",
    )
    planning_pension_scenario_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_pension_scenario_output(),
        help="Output pension scenario snapshot JSON path",
    )
    planning_pension_scenario_demo_parser = planning_pension_scenario_subparsers.add_parser(
        "demo",
        help="Run the synthetic pension scenario check with bundled examples",
    )
    planning_pension_scenario_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_pension_scenario_demo_output(),
        help="Output synthetic pension scenario snapshot JSON path",
    )
    planning_real_estate_parser = planning_subparsers.add_parser(
        "real-estate",
        help="Compare explicit hold, rent and sell real-estate alternatives",
    )
    planning_real_estate_subparsers = planning_real_estate_parser.add_subparsers(
        dest="planning_real_estate_command"
    )
    planning_real_estate_build_parser = planning_real_estate_subparsers.add_parser(
        "build",
        help="Build real-estate-plan/v1 from explicit property assumptions",
    )
    planning_real_estate_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_real_estate_plan_input(),
        help="Input real estate plan JSON path",
    )
    planning_real_estate_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_real_estate_plan_output(),
        help="Output real estate plan snapshot JSON path",
    )
    planning_real_estate_demo_parser = planning_real_estate_subparsers.add_parser(
        "demo",
        help="Run the synthetic real estate planning check with bundled examples",
    )
    planning_real_estate_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_real_estate_plan_demo_output(),
        help="Output synthetic real estate plan snapshot JSON path",
    )
    planning_protection_parser = planning_subparsers.add_parser(
        "protection",
        help="Compare explicit insurance policies and family protection needs",
    )
    planning_protection_subparsers = planning_protection_parser.add_subparsers(
        dest="planning_protection_command"
    )
    planning_protection_build_parser = planning_protection_subparsers.add_parser(
        "build",
        help="Build protection-gap/v1 from explicit policies and family needs",
    )
    planning_protection_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_protection_gap_input(),
        help="Input protection gap JSON path",
    )
    planning_protection_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_protection_gap_output(),
        help="Output protection gap snapshot JSON path",
    )
    planning_protection_demo_parser = planning_protection_subparsers.add_parser(
        "demo",
        help="Run the synthetic insurance protection check with bundled examples",
    )
    planning_protection_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_protection_gap_demo_output(),
        help="Output synthetic protection gap snapshot JSON path",
    )
    planning_estate_parser = planning_subparsers.add_parser(
        "estate",
        help="Compare declared estate allocations, donations and beneficiary gaps",
    )
    planning_estate_subparsers = planning_estate_parser.add_subparsers(
        dest="planning_estate_command"
    )
    planning_estate_build_parser = planning_estate_subparsers.add_parser(
        "build",
        help="Build estate-plan/v2 from explicit succession planning inputs",
    )
    planning_estate_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_estate_plan_input(),
        help="Input estate plan JSON path",
    )
    planning_estate_build_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_estate_plan_rule_pack(),
        help="Input estate plan V2 rule pack JSON path",
    )
    planning_estate_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_estate_plan_output(),
        help="Output estate plan snapshot JSON path",
    )
    planning_estate_demo_parser = planning_estate_subparsers.add_parser(
        "demo",
        help="Run the synthetic estate planning check with bundled examples",
    )
    planning_estate_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_estate_plan_demo_output(),
        help="Output synthetic estate plan snapshot JSON path",
    )
    planning_wealth_strategy_parser = planning_subparsers.add_parser(
        "wealth-strategy",
        help="Compose V4 planning snapshots into comparable strategy packages",
    )
    planning_wealth_strategy_subparsers = planning_wealth_strategy_parser.add_subparsers(
        dest="planning_wealth_strategy_command"
    )
    planning_wealth_strategy_build_parser = planning_wealth_strategy_subparsers.add_parser(
        "build",
        help="Build wealth-strategy/v1 from explicit packages and source snapshots",
    )
    planning_wealth_strategy_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_wealth_strategy_input(),
        help="Input wealth strategy JSON path",
    )
    planning_wealth_strategy_build_parser.add_argument(
        "--liquidity-plan",
        type=Path,
        default=default_liquidity_plan_output(),
        help="Input liquidity-plan/v1 snapshot path",
    )
    planning_wealth_strategy_build_parser.add_argument(
        "--tax-aware-portfolio",
        type=Path,
        default=default_tax_aware_portfolio_output(),
        help="Input tax-aware-portfolio/v1 snapshot path",
    )
    planning_wealth_strategy_build_parser.add_argument(
        "--cross-border-it-es",
        type=Path,
        default=default_cross_border_it_es_output(),
        help="Input cross-border-it-es/v1 snapshot path",
    )
    planning_wealth_strategy_build_parser.add_argument(
        "--real-estate-plan",
        type=Path,
        default=default_real_estate_plan_output(),
        help="Input real-estate-plan/v1 snapshot path",
    )
    planning_wealth_strategy_build_parser.add_argument(
        "--protection-gap",
        type=Path,
        default=default_protection_gap_output(),
        help="Input protection-gap/v1 snapshot path",
    )
    planning_wealth_strategy_build_parser.add_argument(
        "--estate-plan",
        type=Path,
        default=default_estate_plan_output(),
        help="Input estate-plan/v2 snapshot path",
    )
    planning_wealth_strategy_build_parser.add_argument(
        "--work-exit",
        type=Path,
        default=default_work_exit_output(),
        help="Input work-exit-feasibility/v1 snapshot path",
    )
    planning_wealth_strategy_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_wealth_strategy_output(),
        help="Output wealth strategy snapshot JSON path",
    )
    planning_wealth_strategy_demo_parser = planning_wealth_strategy_subparsers.add_parser(
        "demo",
        help="Run the synthetic wealth strategy composer with bundled examples",
    )
    planning_wealth_strategy_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_wealth_strategy_demo_output(),
        help="Output synthetic wealth strategy snapshot JSON path",
    )
    orchestration = subparsers.add_parser("orchestration", help="Inspect deterministic orchestration contracts")
    orchestration_subparsers = orchestration.add_subparsers(dest="orchestration_command")
    orchestration_registry_parser = orchestration_subparsers.add_parser(
        "tool-registry",
        help="Build and inspect the deterministic tool registry",
    )
    orchestration_registry_subparsers = orchestration_registry_parser.add_subparsers(
        dest="orchestration_tool_registry_command"
    )
    orchestration_registry_build_parser = orchestration_registry_subparsers.add_parser(
        "build",
        help="Build tool-registry/v1 for local deterministic capabilities",
    )
    orchestration_registry_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_tool_registry_output(),
        help="Output tool-registry/v1 snapshot JSON path",
    )
    orchestration_registry_list_parser = orchestration_registry_subparsers.add_parser(
        "list",
        help="Print the registered deterministic tools",
    )
    orchestration_registry_list_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output tool-registry/v1 snapshot JSON path",
    )
    planning_it_es_eu_pension_parser = planning_subparsers.add_parser(
        "it-es-eu-pension",
        help="Estimate Spain EU entitlement and pro-rata pension share",
    )
    planning_it_es_eu_pension_subparsers = planning_it_es_eu_pension_parser.add_subparsers(
        dest="planning_it_es_eu_pension_command"
    )
    planning_it_es_eu_pension_prepare_parser = planning_it_es_eu_pension_subparsers.add_parser(
        "prepare",
        help="Create a guided synthetic draft input in the private workspace",
    )
    planning_it_es_eu_pension_prepare_parser.add_argument(
        "--template",
        type=Path,
        default=default_it_es_eu_pension_pro_rata_sample_input(),
        help="Template IT-ES EU pension pro-rata JSON path",
    )
    planning_it_es_eu_pension_prepare_parser.add_argument(
        "--draft",
        type=Path,
        default=default_it_es_eu_pension_pro_rata_draft(),
        help="Output draft IT-ES EU pension pro-rata JSON path",
    )
    planning_it_es_eu_pension_prepare_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing draft",
    )
    planning_it_es_eu_pension_wizard_parser = planning_it_es_eu_pension_subparsers.add_parser(
        "wizard",
        help="Interactively create a private mixed IT-ES pension pro-rata input",
    )
    planning_it_es_eu_pension_wizard_parser.add_argument(
        "--input",
        type=Path,
        default=default_it_es_eu_pension_pro_rata_input(),
        help="Output IT-ES EU pension pro-rata input JSON path",
    )
    planning_it_es_eu_pension_wizard_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing input",
    )
    planning_it_es_eu_pension_build_parser = planning_it_es_eu_pension_subparsers.add_parser(
        "build",
        help="Build it-es-eu-pension-pro-rata/v1 from dated periods and explicit theoretical amount",
    )
    planning_it_es_eu_pension_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_it_es_eu_pension_pro_rata_input(),
        help="Input IT-ES EU pension pro-rata JSON path",
    )
    planning_it_es_eu_pension_build_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_eu_pension_coordination_rule_pack(),
        help="Input EU pension coordination rule pack JSON path",
    )
    planning_it_es_eu_pension_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_it_es_eu_pension_pro_rata_output(),
        help="Output IT-ES EU pension pro-rata snapshot JSON path",
    )
    planning_it_es_eu_pension_build_parser.add_argument(
        "--spanish-theoretical-snapshot",
        type=Path,
        default=None,
        help="Optional spanish-eu-theoretical-pension/v1 snapshot used to fill the theoretical amount",
    )
    planning_it_es_eu_pension_demo_parser = planning_it_es_eu_pension_subparsers.add_parser(
        "demo",
        help="Run the synthetic IT-ES EU pension pro-rata check with bundled examples",
    )
    planning_it_es_eu_pension_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_it_es_eu_pension_pro_rata_demo_output(),
        help="Output synthetic IT-ES EU pension pro-rata snapshot JSON path",
    )
    planning_spanish_eu_theoretical_parser = planning_subparsers.add_parser(
        "spanish-eu-theoretical-pension",
        help="Estimate the Spanish EU theoretical gross pension amount",
    )
    planning_spanish_eu_theoretical_subparsers = planning_spanish_eu_theoretical_parser.add_subparsers(
        dest="planning_spanish_eu_theoretical_command"
    )
    planning_spanish_eu_theoretical_build_parser = planning_spanish_eu_theoretical_subparsers.add_parser(
        "build",
        help="Build spanish-eu-theoretical-pension/v1 from pro-rata periods and Spanish bases",
    )
    planning_spanish_eu_theoretical_build_parser.add_argument(
        "--pro-rata-input",
        type=Path,
        default=default_it_es_eu_pension_pro_rata_input(),
        help="Input IT-ES EU pension pro-rata JSON path with dated IT/ES periods",
    )
    planning_spanish_eu_theoretical_build_parser.add_argument(
        "--spanish-reconciliation-snapshot",
        type=Path,
        default=default_spanish_contribution_reconciliation_output(),
        help="Input Spanish contribution reconciliation snapshot JSON path",
    )
    planning_spanish_eu_theoretical_build_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_spanish_eu_theoretical_pension_rule_pack(),
        help="Input Spanish EU theoretical pension rule pack JSON path",
    )
    planning_spanish_eu_theoretical_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_spanish_eu_theoretical_pension_output(),
        help="Output Spanish EU theoretical pension snapshot JSON path",
    )
    planning_spanish_eu_theoretical_demo_parser = planning_spanish_eu_theoretical_subparsers.add_parser(
        "demo",
        help="Run the synthetic Spanish EU theoretical pension check",
    )
    planning_spanish_eu_theoretical_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_spanish_eu_theoretical_pension_demo_output(),
        help="Output synthetic Spanish EU theoretical pension snapshot JSON path",
    )
    planning_work_exit_parser = planning_subparsers.add_parser(
        "work-exit",
        help="Find the earliest sustainable household work-exit date",
    )
    planning_work_exit_subparsers = planning_work_exit_parser.add_subparsers(
        dest="planning_work_exit_command"
    )
    planning_work_exit_build_parser = planning_work_exit_subparsers.add_parser(
        "build",
        help="Build work-exit-feasibility/v1 from household constraints and pension snapshots",
    )
    planning_work_exit_build_parser.add_argument(
        "--input",
        type=Path,
        default=default_work_exit_input(),
        help="Input work-exit feasibility JSON path",
    )
    planning_work_exit_build_parser.add_argument(
        "--rule-pack",
        type=Path,
        default=default_work_exit_rule_pack(),
        help="Input INPS theoretical pension rule pack JSON path",
    )
    planning_work_exit_build_parser.add_argument(
        "--inps-snapshot",
        type=Path,
        default=default_inps_pension_output(),
        help="Optional INPS documentary projection snapshot JSON path",
    )
    planning_work_exit_build_parser.add_argument(
        "--pro-rata-snapshot",
        type=Path,
        default=default_it_es_eu_pension_pro_rata_output(),
        help="Optional IT-ES EU pro-rata snapshot JSON path",
    )
    planning_work_exit_build_parser.add_argument(
        "--pension-income-snapshot",
        type=Path,
        default=default_pension_income_output(),
        help="Optional pension income snapshot JSON path",
    )
    planning_work_exit_build_parser.add_argument(
        "--net-worth-snapshot",
        type=Path,
        default=default_net_worth_output(),
        help="Optional net worth snapshot JSON path",
    )
    planning_work_exit_build_parser.add_argument(
        "--liquidity-plan-snapshot",
        type=Path,
        default=default_liquidity_plan_output(),
        help="Optional liquidity plan snapshot JSON path",
    )
    planning_work_exit_build_parser.add_argument(
        "--lifecycle-expenses-snapshot",
        type=Path,
        default=default_lifecycle_expenses_output(),
        help="Optional lifecycle expenses snapshot JSON path",
    )
    planning_work_exit_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_work_exit_output(),
        help="Output work-exit feasibility snapshot JSON path",
    )
    planning_work_exit_demo_parser = planning_work_exit_subparsers.add_parser(
        "demo",
        help="Run the synthetic work-exit feasibility check",
    )
    planning_work_exit_demo_parser.add_argument(
        "--output",
        type=Path,
        default=default_work_exit_demo_output(),
        help="Output synthetic work-exit feasibility snapshot JSON path",
    )
    tax_documents = subparsers.add_parser("tax-documents", help="Import fiscal source documents")
    tax_documents_subparsers = tax_documents.add_subparsers(dest="tax_documents_command")
    tax_documents_import_parser = tax_documents_subparsers.add_parser(
        "import",
        help="Import classified CU and tax declaration PDFs",
    )
    tax_documents_import_parser.add_argument(
        "--cu-dir",
        type=Path,
        default=default_tax_documents_cu_input(),
        help="Input directory containing CU PDFs",
    )
    tax_documents_import_parser.add_argument(
        "--declarations-dir",
        type=Path,
        default=default_tax_documents_declarations_input(),
        help="Input directory containing tax declaration PDFs",
    )
    tax_documents_import_parser.add_argument(
        "--output",
        type=Path,
        default=default_tax_documents_output(),
        help="Output tax documents snapshot JSON path",
    )
    tax_documents_diagnose_parser = tax_documents_subparsers.add_parser(
        "diagnose",
        help="Diagnose CU and tax declaration PDFs without writing a snapshot",
    )
    tax_documents_diagnose_parser.add_argument(
        "--cu-dir",
        type=Path,
        default=default_tax_documents_cu_input(),
        help="Input directory containing CU PDFs",
    )
    tax_documents_diagnose_parser.add_argument(
        "--declarations-dir",
        type=Path,
        default=default_tax_documents_declarations_input(),
        help="Input directory containing tax declaration PDFs",
    )
    tax_documents_diagnose_parser.add_argument(
        "--json",
        action="store_true",
        help="Print full diagnostics as JSON",
    )
    retirement = subparsers.add_parser("retirement", help="Run retirement planning simulations")
    retirement_subparsers = retirement.add_subparsers(dest="retirement_command")
    simulate_parser = retirement_subparsers.add_parser(
        "simulate",
        help="Simulate retirement target ages 62, 64 and 67",
    )
    simulate_parser.add_argument(
        "--net-worth-snapshot",
        type=Path,
        default=default_net_worth_output(),
    )
    simulate_parser.add_argument(
        "--assumptions-snapshot",
        type=Path,
        default=default_assumptions_output(),
    )
    simulate_parser.add_argument(
        "--tax-events-snapshot",
        type=Path,
        default=default_tax_events_output(),
    )
    simulate_parser.add_argument(
        "--pension-income-snapshot",
        type=Path,
        default=None,
        help="Optional pension-income/v1 snapshot used as gross recurring pension offset",
    )
    simulate_parser.add_argument(
        "--output",
        type=Path,
        default=default_retirement_simulation_output(),
    )
    monte_carlo = subparsers.add_parser("monte-carlo", help="Run Monte Carlo planning simulations")
    monte_carlo_subparsers = monte_carlo.add_subparsers(dest="monte_carlo_command")
    monte_carlo_parser = monte_carlo_subparsers.add_parser(
        "simulate",
        help="Run a deterministic Monte Carlo planning simulation",
    )
    monte_carlo_parser.add_argument(
        "--net-worth-snapshot",
        type=Path,
        default=default_net_worth_output(),
    )
    monte_carlo_parser.add_argument(
        "--assumptions-snapshot",
        type=Path,
        default=default_assumptions_output(),
    )
    monte_carlo_parser.add_argument(
        "--simulations",
        type=int,
        default=DEFAULT_MONTE_CARLO_SIMULATIONS,
    )
    monte_carlo_parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_MONTE_CARLO_SEED,
    )
    monte_carlo_parser.add_argument(
        "--output",
        type=Path,
        default=default_monte_carlo_output(),
    )
    scenarios = subparsers.add_parser("scenarios", help="Compare decision scenarios")
    scenarios_subparsers = scenarios.add_subparsers(dest="scenarios_command")
    scenarios_compare_parser = scenarios_subparsers.add_parser(
        "compare-retirement",
        help="Compare retirement target ages with deterministic Monte Carlo",
    )
    scenarios_compare_parser.add_argument(
        "--net-worth-snapshot",
        type=Path,
        default=default_net_worth_output(),
    )
    scenarios_compare_parser.add_argument(
        "--assumptions-snapshot",
        type=Path,
        default=default_assumptions_output(),
    )
    scenarios_compare_parser.add_argument(
        "--target-age",
        type=int,
        action="append",
        dest="target_ages",
        help="Retirement target age to compare; repeat for multiple ages",
    )
    scenarios_compare_parser.add_argument(
        "--simulations",
        type=int,
        default=DEFAULT_MONTE_CARLO_SIMULATIONS,
    )
    scenarios_compare_parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_MONTE_CARLO_SEED,
    )
    scenarios_compare_parser.add_argument(
        "--output",
        type=Path,
        default=default_scenario_comparison_output(),
    )
    scenarios_compose_v2_parser = scenarios_subparsers.add_parser(
        "compose-v2",
        help="Compose a deterministic decision-scenario/v2 artifact",
    )
    scenarios_compose_v2_parser.add_argument(
        "--input",
        type=Path,
        default=default_decision_scenario_input(),
        help="Input decision scenario V2 JSON path",
    )
    scenarios_compose_v2_parser.add_argument(
        "--household-snapshot",
        type=Path,
        default=default_household_facts_output(),
        help="Input household facts snapshot JSON path",
    )
    scenarios_compose_v2_parser.add_argument(
        "--ownership-snapshot",
        type=Path,
        default=default_ownership_graph_output(),
        help="Input ownership graph snapshot JSON path",
    )
    scenarios_compose_v2_parser.add_argument(
        "--asset-availability-snapshot",
        type=Path,
        default=default_asset_availability_output(),
        help="Input asset availability snapshot JSON path",
    )
    scenarios_compose_v2_parser.add_argument(
        "--timeline-snapshot",
        type=Path,
        default=default_timeline_events_output(),
        help="Input timeline events snapshot JSON path",
    )
    scenarios_compose_v2_parser.add_argument(
        "--pension-income-snapshot",
        type=Path,
        default=default_pension_income_output(),
        help="Input pension income snapshot JSON path",
    )
    scenarios_compose_v2_parser.add_argument(
        "--lifecycle-expenses-snapshot",
        type=Path,
        default=default_lifecycle_expenses_output(),
        help="Input lifecycle expenses snapshot JSON path",
    )
    scenarios_compose_v2_parser.add_argument(
        "--output",
        type=Path,
        default=default_decision_scenario_output(),
        help="Output decision scenario V2 snapshot JSON path",
    )
    scenarios_evaluate_parser = scenarios_subparsers.add_parser(
        "evaluate",
        help="Run a registered deterministic evaluator and build decision-outcome/v1",
    )
    scenarios_evaluate_parser.add_argument(
        "--decision-scenario-snapshot",
        type=Path,
        default=default_decision_scenario_output(),
        help="Input decision scenario V2 snapshot JSON path",
    )
    scenarios_evaluate_parser.add_argument(
        "--input",
        type=Path,
        default=default_decision_outcome_input(),
        help="Input decision outcome configuration JSON path",
    )
    scenarios_evaluate_parser.add_argument(
        "--output",
        type=Path,
        default=default_decision_outcome_output(),
        help="Output decision outcome snapshot JSON path",
    )
    scenarios_sensitivity_parser = scenarios_subparsers.add_parser(
        "sensitivity",
        help="Build sensitivity-analysis/v1 and optionally rerun deterministic outcomes",
    )
    scenarios_sensitivity_parser.add_argument(
        "--decision-scenario-snapshot",
        type=Path,
        default=default_decision_scenario_output(),
        help="Input decision scenario V2 snapshot JSON path",
    )
    scenarios_sensitivity_parser.add_argument(
        "--input",
        type=Path,
        default=default_sensitivity_analysis_input(),
        help="Input sensitivity analysis JSON path",
    )
    scenarios_sensitivity_parser.add_argument(
        "--output",
        type=Path,
        default=default_sensitivity_analysis_output(),
        help="Output sensitivity analysis snapshot JSON path",
    )
    scenarios_score_parser = scenarios_subparsers.add_parser(
        "score",
        help="Build deterministic decision-score/v1 from explicit metrics and weights",
    )
    scenarios_score_parser.add_argument(
        "--decision-scenario-snapshot",
        type=Path,
        default=default_decision_scenario_output(),
        help="Input decision scenario V2 snapshot JSON path",
    )
    scenarios_score_parser.add_argument(
        "--sensitivity-analysis-snapshot",
        type=Path,
        default=default_sensitivity_analysis_output(),
        help="Input sensitivity analysis snapshot JSON path",
    )
    scenarios_score_parser.add_argument(
        "--input",
        type=Path,
        default=default_decision_score_input(),
        help="Input decision score JSON path",
    )
    scenarios_score_parser.add_argument(
        "--policy",
        type=Path,
        default=default_decision_score_policy(),
        help="Decision score policy JSON path",
    )
    scenarios_score_parser.add_argument(
        "--output",
        type=Path,
        default=default_decision_score_output(),
        help="Output decision score snapshot JSON path",
    )
    scenarios_dossier_parser = scenarios_subparsers.add_parser(
        "dossier",
        help="Build deterministic decision-dossier/v1 and Markdown report",
    )
    scenarios_dossier_parser.add_argument(
        "--decision-scenario-snapshot",
        type=Path,
        default=default_decision_scenario_output(),
        help="Input decision scenario V2 snapshot JSON path",
    )
    scenarios_dossier_parser.add_argument(
        "--sensitivity-analysis-snapshot",
        type=Path,
        default=default_sensitivity_analysis_output(),
        help="Input sensitivity analysis snapshot JSON path",
    )
    scenarios_dossier_parser.add_argument(
        "--decision-score-snapshot",
        type=Path,
        default=default_decision_score_output(),
        help="Input decision score snapshot JSON path",
    )
    scenarios_dossier_parser.add_argument(
        "--input",
        type=Path,
        default=default_decision_dossier_input(),
        help="Input decision dossier JSON path",
    )
    scenarios_dossier_parser.add_argument(
        "--output",
        type=Path,
        default=default_decision_dossier_output(),
        help="Output decision dossier snapshot JSON path",
    )
    scenarios_dossier_parser.add_argument(
        "--markdown-output",
        type=Path,
        default=default_decision_dossier_report_output(),
        help="Output decision dossier Markdown path",
    )
    dashboard = subparsers.add_parser("dashboard", help="Build decision dashboard snapshots")
    dashboard_subparsers = dashboard.add_subparsers(dest="dashboard_command")
    dashboard_build_parser = dashboard_subparsers.add_parser(
        "build",
        help="Build a deterministic decision dashboard snapshot",
    )
    dashboard_build_parser.add_argument(
        "--net-worth-snapshot",
        type=Path,
        default=default_net_worth_output(),
    )
    dashboard_build_parser.add_argument(
        "--assumptions-snapshot",
        type=Path,
        default=default_assumptions_output(),
    )
    dashboard_build_parser.add_argument(
        "--monte-carlo-snapshot",
        type=Path,
        default=default_monte_carlo_output(),
    )
    dashboard_build_parser.add_argument(
        "--scenario-comparison-snapshot",
        type=Path,
        default=default_scenario_comparison_output(),
    )
    dashboard_build_parser.add_argument(
        "--assumptions-readiness-snapshot",
        type=Path,
        default=default_assumptions_readiness_output(),
    )
    dashboard_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_decision_dashboard_output(),
    )
    report = subparsers.add_parser("report", help="Build deterministic reports")
    report_subparsers = report.add_subparsers(dest="report_command")
    report_build_parser = report_subparsers.add_parser(
        "build",
        help="Build the MVP retirement Markdown report",
    )
    report_build_parser.add_argument(
        "--simulation-snapshot",
        type=Path,
        default=default_retirement_simulation_output(),
    )
    report_build_parser.add_argument(
        "--net-worth-snapshot",
        type=Path,
        default=default_net_worth_output(),
    )
    report_build_parser.add_argument(
        "--assumptions-snapshot",
        type=Path,
        default=default_assumptions_output(),
    )
    report_build_parser.add_argument(
        "--assumptions-readiness-snapshot",
        type=Path,
        default=default_assumptions_readiness_output(),
    )
    report_build_parser.add_argument(
        "--output",
        type=Path,
        default=default_retirement_report_output(),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        status = validate()
        print_validate(status)
        return 0 if all(status.values()) else 1

    if args.command == "assumptions" and args.assumptions_command == "prepare":
        try:
            result = prepare_assumptions_input(
                args.template,
                args.draft,
                args.checklist,
                args.overwrite,
            )
        except AssumptionsImportError as exc:
            print(f"assumptions: ERROR ({exc})")
            return 1
        print(
            "assumptions: prepared "
            f"({result['draft_path']}, {result['checklist_path']})"
        )
        return 0

    if args.command == "assumptions" and args.assumptions_command == "import":
        try:
            import_assumptions(args.input, args.output)
        except AssumptionsImportError as exc:
            print(f"assumptions: ERROR ({exc})")
            return 1
        print(f"assumptions: OK ({args.output})")
        return 0

    if args.command == "assumptions" and args.assumptions_command == "check":
        try:
            snapshot = check_assumptions_readiness(
                args.input,
                args.template,
                args.snapshot,
                args.output,
            )
        except AssumptionsReadinessError as exc:
            print(f"assumptions: ERROR ({exc})")
            return 1
        print(f"assumptions: {snapshot['status']} ({args.output})")
        return 0

    if args.command == "documents" and args.documents_command == "inventory":
        try:
            snapshot = build_document_inventory(args.inbox, args.output)
        except DocumentInventoryError as exc:
            print(f"documents: ERROR ({exc})")
            return 1
        print(f"documents: OK {snapshot['summary']['document_count']} files ({args.output})")
        return 0

    if args.command == "documents" and args.documents_command == "organize":
        try:
            manifest = organize_documents(
                args.inbox,
                args.documents,
                args.manifest,
                args.apply,
            )
        except DocumentOrganizationError as exc:
            print(f"documents: ERROR ({exc})")
            return 1
        print(
            "documents: "
            f"{manifest['status']} {manifest['summary']['operation_count']} operations "
            f"({args.manifest})"
        )
        return 0

    if args.command == "pension" and args.pension_command == "import-inps":
        try:
            snapshot = import_inps_pension(args.input_dir, args.output)
        except InpsPensionImportError as exc:
            print(f"pension: ERROR ({exc})")
            return 1
        print(f"pension: {snapshot['extraction_status']} ({args.output})")
        return 0

    if args.command == "pension" and args.pension_command == "import-spain":
        try:
            snapshot = import_spanish_contribution_history(args.input_dir, args.output)
        except SpanishContributionHistoryImportError as exc:
            print(f"pension: ERROR ({exc})")
            return 1
        print(f"pension: {snapshot['extraction_status']} ({args.output})")
        return 0

    if args.command == "pension" and args.pension_command == "reconcile-spain":
        try:
            snapshot = reconcile_spanish_contributions(args.history_snapshot, args.output)
        except SpanishContributionReconciliationError as exc:
            print(f"pension: ERROR ({exc})")
            return 1
        print(
            "pension: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['usable_month_count']} usable months, "
            f"{snapshot['summary']['data_gap_count']} gaps, "
            f"{snapshot['summary']['anomaly_count']} anomalies "
            f"({args.output})"
        )
        return 0

    if args.command == "pension" and args.pension_command == "estimate-spain":
        try:
            snapshot = estimate_spanish_statutory_pension(
                args.reconciliation_snapshot,
                args.rule_pack,
                args.output,
                args.retirement_year,
                args.retirement_month,
                args.scenario,
            )
        except SpanishStatutoryPensionError as exc:
            print(f"pension: ERROR ({exc})")
            return 1
        if snapshot["status"] == "complete":
            print(
                "pension: "
                f"{snapshot['status']} "
                f"monthly={snapshot['gross_pension']['monthly_amount']} "
                f"annual={snapshot['gross_pension']['annual_amount']} "
                f"({args.output})"
            )
        else:
            print(
                "pension: "
                f"{snapshot['status']} "
                f"{len(snapshot['data_gaps'])} gaps "
                f"({args.output})"
            )
        return 0

    if args.command == "pension" and args.pension_command == "coordinate-it-es":
        try:
            snapshot = coordinate_it_es_pensions(
                args.inps_snapshot,
                args.spanish_pension_snapshot,
                args.rule_pack,
                args.output,
                args.italian_contribution_months,
            )
        except EuPensionCoordinationError as exc:
            print(f"pension: ERROR ({exc})")
            return 1
        print(
            "pension: "
            f"{snapshot['status']} "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if args.command == "pension" and args.pension_command == "compose-income":
        try:
            snapshot = compose_pension_income(
                args.inps_snapshot,
                args.spanish_pension_snapshot,
                args.output,
                rita_options_snapshot_path=args.rita_options_snapshot,
                eu_coordination_snapshot_path=args.eu_coordination_snapshot,
                include_rita=not args.no_rita,
            )
        except PensionIncomeError as exc:
            print(f"pension: ERROR ({exc})")
            return 1
        print(
            "pension: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['stream_count']} streams, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if args.command == "investments" and args.investments_command == "import":
        try:
            snapshot = import_investments(args.italy_dir, args.spain_dir, args.output, args.directa_dir)
        except InvestmentsImportError as exc:
            print(f"investments: ERROR ({exc})")
            return 1
        print(f"investments: {snapshot['extraction_status']} ({args.output})")
        return 0

    if args.command == "bank-insurance" and args.bank_insurance_command == "import":
        try:
            snapshot = import_bank_insurance(args.bank_dir, args.insurance_dir, args.output)
        except BankInsuranceImportError as exc:
            print(f"bank-insurance: ERROR ({exc})")
            return 1
        print(f"bank-insurance: {snapshot['extraction_status']} ({args.output})")
        return 0

    if args.command == "payroll" and args.payroll_command == "import":
        try:
            snapshot = import_payroll(args.input_dir, args.output)
        except PayrollImportError as exc:
            print(f"payroll: ERROR ({exc})")
            return 1
        print(
            "payroll: "
            f"{snapshot['extraction_status']} "
            f"{snapshot['summary']['record_count']} records, "
            f"{len(snapshot['documents'])} documents, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if args.command == "payroll" and args.payroll_command == "diagnose":
        try:
            diagnostics = diagnose_payroll_input(args.input_dir)
        except PayrollImportError as exc:
            print(f"payroll: ERROR ({exc})")
            return 1
        if args.json:
            print(json.dumps(diagnostics, indent=2, sort_keys=True))
        else:
            _print_payroll_diagnostics(diagnostics)
        return 0

    if args.command == "cashflow" and args.cashflow_command == "earned-income":
        try:
            snapshot = build_earned_income_cashflow(
                args.payroll_snapshot,
                args.output,
                args.assumptions_snapshot,
            )
        except EarnedIncomeCashflowError as exc:
            print(f"cashflow: ERROR ({exc})")
            return 1
        print(f"cashflow: {snapshot['status']} ({args.output})")
        return 0

    if args.command == "fonte" and args.fonte_command == "import":
        try:
            if args.input is not None:
                import_fonte(args.input, args.output)
            else:
                position_pdf, contributions_xlsx = resolve_fonte_source_paths(
                    args.position_pdf,
                    args.contributions_xlsx,
                )
                import_fonte_source_bundle(
                    position_pdf,
                    contributions_xlsx,
                    args.output,
                )
        except FonteImportError as exc:
            print(f"fonte: ERROR ({exc})")
            return 1
        print(f"fonte: OK ({args.output})")
        return 0

    if args.command == "net-worth" and args.net_worth_command == "consolidate":
        try:
            consolidate_net_worth(
                args.fonte_snapshot,
                args.output,
                args.assumptions_snapshot,
                args.investments_snapshot,
                args.bank_insurance_snapshot,
            )
        except NetWorthError as exc:
            print(f"net-worth: ERROR ({exc})")
            return 1
        print(f"net-worth: OK ({args.output})")
        return 0

    if args.command == "tax-events" and args.tax_events_command == "impatriati":
        try:
            generate_impatriati_events(
                args.start_year,
                args.end_year,
                args.taxable_income_share,
                args.regime,
                args.output,
            )
        except TaxEventsError as exc:
            print(f"tax-events: ERROR ({exc})")
            return 1
        print(f"tax-events: OK ({args.output})")
        return 0

    if args.command == "tax" and args.tax_command == "calculate":
        try:
            snapshot = calculate_tax(
                args.rule_pack,
                args.tax_year,
                args.jurisdiction,
                args.taxable_income,
                args.output,
            )
        except TaxCalculationError as exc:
            print(f"tax: ERROR ({exc})")
            return 1
        tax_due = snapshot["result"]["tax_due"] if snapshot["result"] else "n/a"
        print(f"tax: {snapshot['status']} due={tax_due} ({args.output})")
        return 0

    if args.command == "tax" and args.tax_command == "reconcile":
        try:
            snapshot = reconcile_tax_sources(
                args.payroll_snapshot,
                args.tax_documents_snapshot,
                args.output,
            )
        except TaxReconciliationError as exc:
            print(f"tax: ERROR ({exc})")
            return 1
        print(
            "tax: "
            f"{snapshot['status']} reconciliation "
            f"{len(snapshot['years'])} years, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if args.command == "rita" and args.rita_command == "optimize":
        try:
            snapshot = optimize_rita_options(
                args.rule_pack,
                args.output,
                age=args.age,
                years_to_public_pension=args.years_to_public_pension,
                employment_status=args.employment_status,
                unemployed_months=args.unemployed_months,
                mandatory_contribution_years=args.mandatory_contribution_years,
                complementary_pension_years=args.complementary_pension_years,
                complementary_balance=args.complementary_balance,
                duration_months=args.duration_months,
                monthly_need=args.monthly_need,
            )
        except RitaOptionsError as exc:
            print(f"rita: ERROR ({exc})")
            return 1
        print(
            "rita: "
            f"{snapshot['status']} "
            f"eligible={snapshot['eligibility']['eligible'] if snapshot['eligibility'] else 'n/a'} "
            f"options={len(snapshot['options'])} "
            f"({args.output})"
        )
        return 0

    if args.command == "estate" and args.estate_command == "baseline":
        try:
            snapshot = build_estate_baseline(
                args.net_worth_snapshot,
                args.rule_pack,
                args.output,
                has_spouse=args.has_spouse,
                children_count=args.children_count,
                prior_donations=args.prior_donations,
            )
        except EstateBaselineError as exc:
            print(f"estate: ERROR ({exc})")
            return 1
        print(
            "estate: "
            f"{snapshot['status']} "
            f"known_mass={snapshot['totals']['known_estate_mass']} "
            f"heirs={len(snapshot['theoretical_heirs'])} "
            f"gaps={len(snapshot['data_gaps'])} "
            f"({args.output})"
        )
        return 0

    if args.command == "household" and args.household_command == "validate":
        try:
            snapshot = import_household_facts(args.input, args.output)
        except HouseholdFactsError as exc:
            print(f"household: ERROR ({exc})")
            return 1
        print(
            "household: "
            f"{snapshot['status']} "
            f"{len(snapshot['persons'])} persons, "
            f"{len(snapshot['relationships'])} relationships, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "household"
        and args.household_command == "ownership"
        and args.household_ownership_command == "validate"
    ):
        try:
            snapshot = import_ownership_graph(args.input, args.output, args.household_snapshot)
        except OwnershipGraphError as exc:
            print(f"household ownership: ERROR ({exc})")
            return 1
        print(
            "household ownership: "
            f"{snapshot['status']} "
            f"{len(snapshot['assets'])} assets, "
            f"{len(snapshot['debts'])} debts, "
            f"{len(snapshot['beneficiaries'])} beneficiaries, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "household"
        and args.household_command == "availability"
        and args.household_availability_command == "validate"
    ):
        try:
            ownership_snapshot = None if args.skip_ownership_check else args.ownership_snapshot
            snapshot = import_asset_availability(args.input, args.output, ownership_snapshot)
        except AssetAvailabilityError as exc:
            print(f"household availability: ERROR ({format_asset_availability_error(exc)})")
            return 1
        print(
            "household availability: "
            f"{snapshot['status']} "
            f"{len(snapshot['classifications'])} classifications, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "household"
        and args.household_command == "availability"
        and args.household_availability_command == "wizard"
    ):
        try:
            result = run_asset_availability_wizard(args.input, args.net_worth_snapshot, args.overwrite)
        except (EOFError, KeyboardInterrupt):
            print("household availability wizard: interrupted; rerun with `--overwrite` to resume/revise.")
            return 1
        except AssetAvailabilityError as exc:
            print(f"household availability wizard: ERROR ({exc})")
            return 1
        if result["status"] == "existing":
            print(
                "household availability wizard: existing input found "
                f"({result['input_path']}; run `fo household availability validate`, or rerun with `--overwrite` to revise it)"
            )
            return 0
        print(
            "household availability wizard: prepared "
            f"{result['classification_count']} classifications, "
            f"{result['data_gap_count']} gaps "
            f"({result['input_path']}; run `fo household availability validate`)"
        )
        return 0

    if (
        args.command == "household"
        and args.household_command == "timeline"
        and args.household_timeline_command == "validate"
    ):
        try:
            snapshot = import_timeline_events(
                args.input,
                args.output,
                args.policy,
                args.household_snapshot,
                args.asset_availability_snapshot,
            )
        except TimelineEventsError as exc:
            print(f"household timeline: ERROR ({exc})")
            return 1
        print(
            "household timeline: "
            f"{snapshot['status']} "
            f"{len(snapshot['events'])} events, "
            f"{len(snapshot['occurrences'])} occurrences, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "goals"
        and args.planning_goals_command == "prepare"
    ):
        try:
            result = prepare_planning_goals_input(args.draft, args.input, args.overwrite)
        except PlanningGoalsError as exc:
            print(f"planning goals: ERROR ({exc})")
            return 1
        print(
            "planning goals: prepared "
            f"({result['input_path']}; edit it, then run `fo planning goals validate`)"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "goals"
        and args.planning_goals_command == "wizard"
    ):
        try:
            result = run_planning_goals_wizard(args.input, args.overwrite)
        except (EOFError, KeyboardInterrupt):
            print(
                "planning goals wizard: interrupted; progress saved. "
                "Run `fo planning goals wizard --overwrite` to resume."
            )
            return 1
        except PlanningGoalsError as exc:
            print(f"planning goals wizard: ERROR ({exc})")
            return 1
        if result["status"] == "existing":
            print(
                "planning goals wizard: existing input found "
                f"({result['input_path']}; run `fo planning goals validate`, or rerun with `--overwrite` to revise it)"
            )
            return 0
        print(
            "planning goals wizard: prepared "
            f"{result['data_gap_count']} gaps "
            f"({result['input_path']}; review it, then run `fo planning goals validate`)"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "goals"
        and args.planning_goals_command == "status"
    ):
        print_planning_goals_status(
            planning_goals_status(
                args.input,
                args.draft,
                args.output,
                args.timeline_snapshot,
            )
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "goals"
        and args.planning_goals_command == "validate"
    ):
        try:
            snapshot = import_planning_goals(args.input, args.output, args.timeline_snapshot)
        except PlanningGoalsError as exc:
            print(f"planning goals: ERROR ({format_planning_goals_error(exc, args.input)})")
            return 1
        print(
            "planning goals: "
            f"{snapshot['status']} "
            f"{len(snapshot['objectives'])} objectives, "
            f"{len(snapshot['constraints'])} constraints, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "goals"
        and args.planning_goals_command == "demo"
    ):
        try:
            timeline_snapshot = import_timeline_events(
                default_timeline_events_sample_input(),
                args.timeline_output,
                default_timeline_policy(),
                default_household_facts_sample_input(),
                default_asset_availability_sample_input(),
            )
            planning_snapshot = import_planning_goals(
                default_planning_goals_sample_input(),
                args.output,
                args.timeline_output,
            )
        except (TimelineEventsError, PlanningGoalsError) as exc:
            print(f"planning goals demo: ERROR ({exc})")
            return 1
        print(
            "planning goals demo: "
            f"timeline={timeline_snapshot['status']} "
            f"{len(timeline_snapshot['events'])} events, "
            f"goals={planning_snapshot['status']} "
            f"{len(planning_snapshot['objectives'])} objectives, "
            f"{len(planning_snapshot['constraints'])} constraints, "
            f"{len(planning_snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "liquidity"
        and args.planning_liquidity_command == "wizard"
    ):
        try:
            result = run_liquidity_plan_wizard(args.input, args.overwrite)
        except (EOFError, KeyboardInterrupt):
            print("planning liquidity wizard: interrupted; rerun with `--overwrite` to resume/revise.")
            return 1
        except LiquidityPlanError as exc:
            print(f"planning liquidity wizard: ERROR ({exc})")
            return 1
        if result["status"] == "existing":
            print(
                "planning liquidity wizard: existing input found "
                f"({result['input_path']}; run `fo planning liquidity build`, or rerun with `--overwrite` to revise it)"
            )
            return 0
        print(
            "planning liquidity wizard: prepared "
            f"{result['data_gap_count']} gaps "
            f"({result['input_path']}; review it, then run `fo planning liquidity build`)"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "liquidity"
        and args.planning_liquidity_command == "build"
    ):
        try:
            snapshot = build_liquidity_plan(
                args.input,
                args.output,
                net_worth_snapshot_path=args.net_worth_snapshot,
                asset_availability_snapshot_path=args.asset_availability_snapshot,
                planning_goals_snapshot_path=args.planning_goals_snapshot,
            )
        except LiquidityPlanError as exc:
            print(f"planning liquidity: ERROR ({exc})")
            return 1
        print_liquidity_plan_summary(snapshot, args.output)
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "liquidity"
        and args.planning_liquidity_command == "explain"
    ):
        try:
            snapshot = load_liquidity_plan_snapshot(args.snapshot)
        except LiquidityPlanError as exc:
            print(f"planning liquidity explain: ERROR ({exc})")
            return 1
        print_liquidity_plan_explain(snapshot, args.snapshot)
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "liquidity"
        and args.planning_liquidity_command == "demo"
    ):
        try:
            planning_snapshot = import_planning_goals(
                default_planning_goals_sample_input(),
                args.planning_goals_output,
                None,
            )
            snapshot = build_liquidity_plan(
                default_liquidity_plan_sample_input(),
                args.output,
                net_worth_snapshot_path=default_liquidity_plan_sample_net_worth(),
                asset_availability_snapshot_path=default_asset_availability_sample_input(),
                planning_goals_snapshot_path=args.planning_goals_output,
            )
        except (PlanningGoalsError, LiquidityPlanError) as exc:
            print(f"planning liquidity demo: ERROR ({exc})")
            return 1
        print(f"planning liquidity demo: goals={planning_snapshot['status']}")
        print_liquidity_plan_summary(snapshot, args.output, "planning liquidity demo")
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "decumulation"
        and args.planning_decumulation_command == "wizard"
    ):
        try:
            result = run_decumulation_policy_wizard(args.input, args.overwrite)
        except (EOFError, KeyboardInterrupt):
            print("planning decumulation wizard: interrupted; rerun with `--overwrite` to resume/revise.")
            return 1
        except DecumulationStrategyError as exc:
            print(f"planning decumulation wizard: ERROR ({exc})")
            return 1
        if result["status"] == "existing":
            print(
                "planning decumulation wizard: existing input found "
                f"({result['input_path']}; run `fo planning decumulation build`, or rerun with `--overwrite` to revise it)"
            )
            return 0
        print(
            "planning decumulation wizard: prepared "
            f"{result['data_gap_count']} gaps "
            f"({result['input_path']}; review it, then run `fo planning decumulation build`)"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "decumulation"
        and args.planning_decumulation_command == "build"
    ):
        try:
            snapshot = build_decumulation_strategy(
                args.input,
                args.output,
                net_worth_snapshot_path=args.net_worth_snapshot,
                liquidity_plan_snapshot_path=args.liquidity_plan_snapshot,
                pension_income_snapshot_path=args.pension_income_snapshot,
                rita_options_snapshot_path=args.rita_options_snapshot,
            )
        except DecumulationStrategyError as exc:
            print(f"planning decumulation: ERROR ({exc})")
            return 1
        print(
            "planning decumulation: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['policy_count']} policies, "
            f"best={snapshot['summary']['best_ranked_policy_id'] or 'n/a'}, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "decumulation"
        and args.planning_decumulation_command == "demo"
    ):
        try:
            snapshot = build_decumulation_strategy(
                default_decumulation_policy_set_sample_input(),
                args.output,
                net_worth_snapshot_path=default_decumulation_sample_net_worth(),
                liquidity_plan_snapshot_path=default_decumulation_sample_liquidity_plan(),
                pension_income_snapshot_path=default_decumulation_sample_pension_income(),
                rita_options_snapshot_path=default_decumulation_sample_rita_options(),
            )
        except DecumulationStrategyError as exc:
            print(f"planning decumulation demo: ERROR ({exc})")
            return 1
        print(
            "planning decumulation demo: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['policy_count']} policies, "
            f"best={snapshot['summary']['best_ranked_policy_id'] or 'n/a'}, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "pension-contributions"
        and args.planning_pension_contributions_command == "build"
    ):
        try:
            snapshot = build_pension_contribution_options(args.input, args.rule_pack, args.output)
        except PensionContributionOptionsError as exc:
            print(f"planning pension-contributions: ERROR ({format_pension_contribution_error(exc, args.input)})")
            return 1
        print(
            "planning pension-contributions: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['option_count']} options, "
            f"best={snapshot['summary']['best_option_id'] or 'n/a'}, "
            f"{snapshot['summary']['data_gap_count']} gaps, "
            f"{snapshot['summary']['constraint_count']} constraints "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "pension-contributions"
        and args.planning_pension_contributions_command == "wizard"
    ):
        try:
            result = run_pension_contribution_wizard(args.input, args.overwrite)
        except (EOFError, KeyboardInterrupt):
            print("planning pension-contributions wizard: interrupted; rerun with `--overwrite` to resume/revise.")
            return 1
        except PensionContributionOptionsError as exc:
            print(f"planning pension-contributions wizard: ERROR ({exc})")
            return 1
        if result["status"] == "existing":
            print(
                "planning pension-contributions wizard: existing input found "
                f"({result['input_path']}; run `fo planning pension-contributions build`, or rerun with `--overwrite` to revise it)"
            )
            return 0
        print(
            "planning pension-contributions wizard: prepared "
            f"{result['data_gap_count']} gaps "
            f"({result['input_path']}; review it, then run `fo planning pension-contributions build`)"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "pension-contributions"
        and args.planning_pension_contributions_command == "demo"
    ):
        try:
            snapshot = build_pension_contribution_options(
                default_pension_contribution_sample_input(),
                default_pension_contribution_rule_pack(),
                args.output,
            )
        except PensionContributionOptionsError as exc:
            print(f"planning pension-contributions demo: ERROR ({exc})")
            return 1
        print(
            "planning pension-contributions demo: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['option_count']} options, "
            f"best={snapshot['summary']['best_option_id'] or 'n/a'}, "
            f"{snapshot['summary']['data_gap_count']} gaps, "
            f"{snapshot['summary']['constraint_count']} constraints "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "tax-aware-portfolio"
        and args.planning_tax_aware_portfolio_command == "build"
    ):
        try:
            snapshot = build_tax_aware_portfolio(args.input, args.rule_pack, args.output)
        except TaxAwarePortfolioError as exc:
            print(f"planning tax-aware-portfolio: ERROR ({exc})")
            return 1
        print(
            "planning tax-aware-portfolio: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['option_count']} options, "
            f"best={snapshot['summary']['best_option_id'] or 'n/a'}, "
            f"{snapshot['summary']['data_gap_count']} gaps, "
            f"{snapshot['summary']['constraint_count']} constraints "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "tax-aware-portfolio"
        and args.planning_tax_aware_portfolio_command == "demo"
    ):
        try:
            snapshot = build_tax_aware_portfolio(
                default_tax_aware_portfolio_sample_input(),
                default_tax_aware_investment_rule_pack(),
                args.output,
            )
        except TaxAwarePortfolioError as exc:
            print(f"planning tax-aware-portfolio demo: ERROR ({exc})")
            return 1
        print(
            "planning tax-aware-portfolio demo: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['option_count']} options, "
            f"best={snapshot['summary']['best_option_id'] or 'n/a'}, "
            f"{snapshot['summary']['data_gap_count']} gaps, "
            f"{snapshot['summary']['constraint_count']} constraints "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "it-es-pension-tax"
        and args.planning_it_es_pension_tax_command == "classify"
    ):
        try:
            snapshot = classify_it_es_pension_tax(
                args.input,
                args.pension_income_snapshot,
                args.rule_pack,
                args.output,
            )
        except ItEsPensionTaxClassificationError as exc:
            print(f"planning it-es-pension-tax: ERROR ({exc})")
            return 1
        print(
            "planning it-es-pension-tax: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['classified_stream_count']}/{snapshot['summary']['stream_count']} classified, "
            f"{snapshot['summary']['data_gap_count']} gaps, "
            f"{snapshot['summary']['warning_count']} warnings "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "it-es-pension-tax"
        and args.planning_it_es_pension_tax_command == "demo"
    ):
        try:
            snapshot = classify_it_es_pension_tax(
                default_it_es_pension_tax_classification_sample_input(),
                default_it_es_pension_income_sample(),
                default_it_es_pension_tax_classification_rule_pack(),
                args.output,
            )
        except ItEsPensionTaxClassificationError as exc:
            print(f"planning it-es-pension-tax demo: ERROR ({exc})")
            return 1
        print(
            "planning it-es-pension-tax demo: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['classified_stream_count']}/{snapshot['summary']['stream_count']} classified, "
            f"{snapshot['summary']['data_gap_count']} gaps, "
            f"{snapshot['summary']['warning_count']} warnings "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "spanish-pension-net"
        and args.planning_spanish_pension_net_command == "build"
    ):
        try:
            snapshot = build_spanish_pension_net_it_resident(
                args.input,
                args.pension_income_snapshot,
                args.classification_snapshot,
                args.rule_pack,
                args.irpef_rule_pack,
                args.output,
            )
        except SpanishPensionNetItResidentError as exc:
            print(f"planning spanish-pension-net: ERROR ({exc})")
            return 1
        print(
            "planning spanish-pension-net: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['complete_stream_count']}/{snapshot['summary']['stream_count']} complete, "
            f"net={snapshot['summary']['net_annual_total'] or 'n/a'}, "
            f"{snapshot['summary']['data_gap_count']} gaps, "
            f"{snapshot['summary']['warning_count']} warnings "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "spanish-pension-net"
        and args.planning_spanish_pension_net_command == "demo"
    ):
        try:
            snapshot = build_spanish_pension_net_it_resident(
                default_spanish_pension_net_it_resident_sample_input(),
                default_it_es_pension_income_sample(),
                default_spanish_pension_net_it_resident_sample_classification(),
                default_spanish_pension_net_it_resident_rule_pack(),
                default_italy_tax_rule_pack(),
                args.output,
            )
        except SpanishPensionNetItResidentError as exc:
            print(f"planning spanish-pension-net demo: ERROR ({exc})")
            return 1
        print(
            "planning spanish-pension-net demo: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['complete_stream_count']}/{snapshot['summary']['stream_count']} complete, "
            f"net={snapshot['summary']['net_annual_total'] or 'n/a'}, "
            f"{snapshot['summary']['data_gap_count']} gaps, "
            f"{snapshot['summary']['warning_count']} warnings "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "it-es-foreign-assets"
        and args.planning_it_es_foreign_assets_command == "build"
    ):
        try:
            snapshot = build_it_es_foreign_assets(args.input, args.rule_pack, args.output)
        except ItEsForeignAssetsError as exc:
            print(f"planning it-es-foreign-assets: ERROR ({exc})")
            return 1
        print(
            "planning it-es-foreign-assets: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['asset_count']} assets, "
            f"{snapshot['summary']['rw_required_count']} RW-required, "
            f"IVAFE={snapshot['summary']['ivafe_due']}, "
            f"IVIE={snapshot['summary']['ivie_due']}, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "it-es-foreign-assets"
        and args.planning_it_es_foreign_assets_command == "demo"
    ):
        try:
            snapshot = build_it_es_foreign_assets(
                default_it_es_foreign_assets_sample_input(),
                default_it_es_foreign_assets_rule_pack(),
                args.output,
            )
        except ItEsForeignAssetsError as exc:
            print(f"planning it-es-foreign-assets demo: ERROR ({exc})")
            return 1
        print(
            "planning it-es-foreign-assets demo: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['asset_count']} assets, "
            f"{snapshot['summary']['rw_required_count']} RW-required, "
            f"IVAFE={snapshot['summary']['ivafe_due']}, "
            f"IVIE={snapshot['summary']['ivie_due']}, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "cross-border-it-es"
        and args.planning_cross_border_it_es_command == "build"
    ):
        try:
            snapshot = build_cross_border_it_es_dossier(
                args.output,
                pension_scenario_snapshot_path=args.pension_scenario_snapshot,
                pension_income_snapshot_path=args.pension_income_snapshot,
                pension_tax_classification_snapshot_path=args.pension_tax_classification_snapshot,
                spanish_pension_net_snapshot_path=args.spanish_pension_net_snapshot,
                eu_pension_pro_rata_snapshot_path=args.eu_pension_pro_rata_snapshot,
                foreign_assets_snapshot_path=args.foreign_assets_snapshot,
            )
        except CrossBorderItEsDossierError as exc:
            print(f"planning cross-border-it-es: ERROR ({exc})")
            return 1
        print(
            "planning cross-border-it-es: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['source_count']} sources, "
            f"{snapshot['summary']['data_gap_count']} gaps, "
            f"{snapshot['summary']['action_item_count']} actions "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "cross-border-it-es"
        and args.planning_cross_border_it_es_command == "demo"
    ):
        try:
            snapshot = build_cross_border_it_es_dossier(
                args.output,
                pension_scenario_snapshot_path=default_pension_scenario_sample_snapshot(),
                pension_income_snapshot_path=default_it_es_pension_income_sample(),
                pension_tax_classification_snapshot_path=default_spanish_pension_net_it_resident_sample_classification(),
                spanish_pension_net_snapshot_path=default_cross_border_it_es_sample_net(),
                eu_pension_pro_rata_snapshot_path=default_cross_border_it_es_sample_pro_rata(),
                foreign_assets_snapshot_path=default_cross_border_it_es_sample_foreign_assets(),
            )
        except CrossBorderItEsDossierError as exc:
            print(f"planning cross-border-it-es demo: ERROR ({exc})")
            return 1
        print(
            "planning cross-border-it-es demo: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['source_count']} sources, "
            f"{snapshot['summary']['data_gap_count']} gaps, "
            f"{snapshot['summary']['action_item_count']} actions "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "pension-scenario"
        and args.planning_pension_scenario_command == "build"
    ):
        try:
            snapshot = build_pension_scenario(args.input, args.output)
        except PensionScenarioError as exc:
            print(f"planning pension-scenario: ERROR ({exc})")
            return 1
        print(
            "planning pension-scenario: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['scenario_count']} scenarios, "
            f"selected={snapshot['selected_scenario_id']}, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "pension-scenario"
        and args.planning_pension_scenario_command == "demo"
    ):
        try:
            snapshot = build_pension_scenario(default_pension_scenario_sample_input(), args.output)
        except PensionScenarioError as exc:
            print(f"planning pension-scenario demo: ERROR ({exc})")
            return 1
        print(
            "planning pension-scenario demo: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['scenario_count']} scenarios, "
            f"selected={snapshot['selected_scenario_id']}, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "real-estate"
        and args.planning_real_estate_command == "build"
    ):
        try:
            snapshot = build_real_estate_plan(args.input, args.output)
        except RealEstatePlanError as exc:
            print(f"planning real-estate: ERROR ({exc})")
            return 1
        print(
            "planning real-estate: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['property_count']} properties, "
            f"{snapshot['summary']['alternative_count']} alternatives, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "real-estate"
        and args.planning_real_estate_command == "demo"
    ):
        try:
            snapshot = build_real_estate_plan(default_real_estate_plan_sample_input(), args.output)
        except RealEstatePlanError as exc:
            print(f"planning real-estate demo: ERROR ({exc})")
            return 1
        print(
            "planning real-estate demo: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['property_count']} properties, "
            f"{snapshot['summary']['alternative_count']} alternatives, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "protection"
        and args.planning_protection_command == "build"
    ):
        try:
            snapshot = build_protection_gap(args.input, args.output)
        except ProtectionGapError as exc:
            print(f"planning protection: ERROR ({exc})")
            return 1
        print(
            "planning protection: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['need_count']} needs, "
            f"{snapshot['summary']['policy_count']} policies, "
            f"shortfall={snapshot['summary']['total_shortfall']} "
            f"{snapshot['base_currency']}, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "protection"
        and args.planning_protection_command == "demo"
    ):
        try:
            snapshot = build_protection_gap(default_protection_gap_sample_input(), args.output)
        except ProtectionGapError as exc:
            print(f"planning protection demo: ERROR ({exc})")
            return 1
        print(
            "planning protection demo: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['need_count']} needs, "
            f"{snapshot['summary']['policy_count']} policies, "
            f"shortfall={snapshot['summary']['total_shortfall']} "
            f"{snapshot['base_currency']}, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "estate"
        and args.planning_estate_command == "build"
    ):
        try:
            snapshot = build_estate_plan(args.input, args.rule_pack, args.output)
        except EstatePlanError as exc:
            print(f"planning estate: ERROR ({exc})")
            return 1
        print(
            "planning estate: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['scenario_count']} scenarios, "
            f"{snapshot['summary']['conflict_count']} conflicts, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "estate"
        and args.planning_estate_command == "demo"
    ):
        try:
            snapshot = build_estate_plan(default_estate_plan_sample_input(), default_estate_plan_rule_pack(), args.output)
        except EstatePlanError as exc:
            print(f"planning estate demo: ERROR ({exc})")
            return 1
        print(
            "planning estate demo: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['scenario_count']} scenarios, "
            f"{snapshot['summary']['conflict_count']} conflicts, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "wealth-strategy"
        and args.planning_wealth_strategy_command == "build"
    ):
        try:
            snapshot = build_wealth_strategy(
                args.input,
                args.output,
                liquidity_plan_snapshot_path=args.liquidity_plan,
                tax_aware_portfolio_snapshot_path=args.tax_aware_portfolio,
                cross_border_it_es_snapshot_path=args.cross_border_it_es,
                real_estate_plan_snapshot_path=args.real_estate_plan,
                protection_gap_snapshot_path=args.protection_gap,
                estate_plan_snapshot_path=args.estate_plan,
                work_exit_snapshot_path=args.work_exit,
            )
        except WealthStrategyError as exc:
            print(f"planning wealth-strategy: ERROR ({exc})")
            return 1
        print(
            "planning wealth-strategy: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['package_count']} packages, "
            f"{snapshot['summary']['comparable_package_count']} comparable, "
            f"top={snapshot['ranking'][0]['package_id'] if snapshot['ranking'] else 'none'}, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "wealth-strategy"
        and args.planning_wealth_strategy_command == "demo"
    ):
        try:
            liquidity_output = default_liquidity_plan_demo_output()
            tax_output = default_tax_aware_portfolio_demo_output()
            real_estate_output = default_real_estate_plan_demo_output()
            protection_output = default_protection_gap_demo_output()
            estate_output = default_estate_plan_demo_output()
            work_exit_output = default_work_exit_demo_output()
            cross_border_output = default_cross_border_it_es_demo_output()
            asset_availability_output = resolve_repo("workspace") / "snapshots" / "cli-check-asset-availability.synthetic.snapshot.json"
            import_asset_availability(default_asset_availability_sample_input(), asset_availability_output)
            build_liquidity_plan(
                default_liquidity_plan_sample_input(),
                liquidity_output,
                net_worth_snapshot_path=default_liquidity_plan_sample_net_worth(),
                asset_availability_snapshot_path=asset_availability_output,
            )
            build_tax_aware_portfolio(default_tax_aware_portfolio_sample_input(), default_tax_aware_investment_rule_pack(), tax_output)
            build_real_estate_plan(default_real_estate_plan_sample_input(), real_estate_output)
            build_protection_gap(default_protection_gap_sample_input(), protection_output)
            build_estate_plan(default_estate_plan_sample_input(), default_estate_plan_rule_pack(), estate_output)
            build_work_exit_feasibility(
                default_work_exit_sample_input(),
                default_work_exit_rule_pack(),
                work_exit_output,
                inps_snapshot_path=default_work_exit_sample_inps_snapshot(),
                pro_rata_snapshot_path=default_work_exit_sample_pro_rata_snapshot(),
            )
            build_cross_border_it_es_dossier(
                cross_border_output,
                pension_scenario_snapshot_path=default_pension_scenario_sample_snapshot(),
                pension_income_snapshot_path=default_it_es_pension_income_sample(),
                pension_tax_classification_snapshot_path=default_spanish_pension_net_it_resident_sample_classification(),
                spanish_pension_net_snapshot_path=default_cross_border_it_es_sample_net(),
                eu_pension_pro_rata_snapshot_path=default_cross_border_it_es_sample_pro_rata(),
                foreign_assets_snapshot_path=default_cross_border_it_es_sample_foreign_assets(),
            )
            snapshot = build_wealth_strategy(
                default_wealth_strategy_sample_input(),
                args.output,
                liquidity_plan_snapshot_path=liquidity_output,
                tax_aware_portfolio_snapshot_path=tax_output,
                cross_border_it_es_snapshot_path=cross_border_output,
                real_estate_plan_snapshot_path=real_estate_output,
                protection_gap_snapshot_path=protection_output,
                estate_plan_snapshot_path=estate_output,
                work_exit_snapshot_path=work_exit_output,
            )
        except (
            LiquidityPlanError,
            AssetAvailabilityError,
            TaxAwarePortfolioError,
            RealEstatePlanError,
            ProtectionGapError,
            EstatePlanError,
            WorkExitFeasibilityError,
            CrossBorderItEsDossierError,
            WealthStrategyError,
        ) as exc:
            print(f"planning wealth-strategy demo: ERROR ({exc})")
            return 1
        print(
            "planning wealth-strategy demo: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['package_count']} packages, "
            f"{snapshot['summary']['comparable_package_count']} comparable, "
            f"top={snapshot['ranking'][0]['package_id'] if snapshot['ranking'] else 'none'}, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "orchestration"
        and args.orchestration_command == "tool-registry"
        and args.orchestration_tool_registry_command == "build"
    ):
        try:
            snapshot = build_tool_registry(args.output)
        except ToolRegistryError as exc:
            print(f"orchestration tool-registry: ERROR ({exc})")
            return 1
        print(
            "orchestration tool-registry: "
            f"{snapshot['status']} "
            f"{snapshot['tool_count']} tools "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "orchestration"
        and args.orchestration_command == "tool-registry"
        and args.orchestration_tool_registry_command == "list"
    ):
        try:
            snapshot = build_tool_registry(args.output)
        except ToolRegistryError as exc:
            print(f"orchestration tool-registry list: ERROR ({exc})")
            return 1
        print(
            "orchestration tool-registry list: "
            f"{snapshot['status']} "
            f"{snapshot['tool_count']} tools"
        )
        for tool in snapshot["tools"]:
            print(
                f"- {tool['tool_id']} -> {tool['output_schema_version']} "
                f"risk={tool['risk_level']} policy={','.join(tool['authorization_policy'])}"
            )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "it-es-eu-pension"
        and args.planning_it_es_eu_pension_command == "prepare"
    ):
        try:
            result = prepare_it_es_eu_pension_pro_rata_input(args.template, args.draft, args.overwrite)
        except ItEsEuPensionProRataError as exc:
            print(f"planning it-es-eu-pension prepare: ERROR ({exc})")
            return 1
        print(
            "planning it-es-eu-pension prepare: prepared "
            f"({result['draft_path']}; review it, then run `fo planning it-es-eu-pension build --input {result['draft_path']}`)"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "it-es-eu-pension"
        and args.planning_it_es_eu_pension_command == "wizard"
    ):
        try:
            result = run_it_es_eu_pension_wizard(args.input, args.overwrite)
        except (EOFError, KeyboardInterrupt):
            print("planning it-es-eu-pension wizard: interrupted")
            return 1
        except ItEsEuPensionProRataError as exc:
            print(f"planning it-es-eu-pension wizard: ERROR ({exc})")
            return 1
        if result["status"] == "existing":
            print(
                "planning it-es-eu-pension wizard: existing input "
                f"({result['input_path']}; run `fo planning it-es-eu-pension build`, or rerun with `--overwrite` to revise it)"
            )
            return 0
        print(
            "planning it-es-eu-pension wizard: prepared "
            f"{result['data_gap_count']} gaps "
            f"({result['input_path']}; run `fo planning it-es-eu-pension build`)"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "it-es-eu-pension"
        and args.planning_it_es_eu_pension_command == "build"
    ):
        try:
            snapshot = build_it_es_eu_pension_pro_rata(
                args.input,
                args.rule_pack,
                args.output,
                spanish_theoretical_snapshot_path=default_or_existing_spanish_theoretical_snapshot(
                    args.spanish_theoretical_snapshot
                ),
            )
        except ItEsEuPensionProRataError as exc:
            print(f"planning it-es-eu-pension: ERROR ({exc})")
            return 1
        print(
            "planning it-es-eu-pension: "
            f"{snapshot['status']} "
            f"entitlement={snapshot['spanish_entitlement']['status']}, "
            f"pro-rata={snapshot['spanish_pro_rata_pension']['status']}, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "spanish-eu-theoretical-pension"
        and args.planning_spanish_eu_theoretical_command == "build"
    ):
        try:
            snapshot = build_spanish_eu_theoretical_pension(
                args.pro_rata_input,
                args.spanish_reconciliation_snapshot,
                args.rule_pack,
                args.output,
            )
        except SpanishEuTheoreticalPensionError as exc:
            print(f"planning spanish-eu-theoretical-pension: ERROR ({exc})")
            return 1
        theoretical = snapshot.get("spanish_theoretical_pension") or {}
        print(
            "planning spanish-eu-theoretical-pension: "
            f"{snapshot['status']} "
            f"theoretical={theoretical.get('monthly_gross_amount', 'not_calculable')}, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "spanish-eu-theoretical-pension"
        and args.planning_spanish_eu_theoretical_command == "demo"
    ):
        try:
            snapshot = build_spanish_eu_theoretical_pension(
                default_spanish_eu_theoretical_pension_sample_input(),
                default_spanish_eu_theoretical_pension_sample_reconciliation(),
                default_spanish_eu_theoretical_pension_rule_pack(),
                args.output,
            )
        except SpanishEuTheoreticalPensionError as exc:
            print(f"planning spanish-eu-theoretical-pension demo: ERROR ({exc})")
            return 1
        theoretical = snapshot.get("spanish_theoretical_pension") or {}
        print(
            "planning spanish-eu-theoretical-pension demo: "
            f"{snapshot['status']} "
            f"theoretical={theoretical.get('monthly_gross_amount', 'not_calculable')}, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "it-es-eu-pension"
        and args.planning_it_es_eu_pension_command == "demo"
    ):
        try:
            snapshot = build_it_es_eu_pension_pro_rata(
                default_it_es_eu_pension_pro_rata_sample_input(),
                default_eu_pension_coordination_rule_pack(),
                args.output,
            )
        except ItEsEuPensionProRataError as exc:
            print(f"planning it-es-eu-pension demo: ERROR ({exc})")
            return 1
        print(
            "planning it-es-eu-pension demo: "
            f"{snapshot['status']} "
            f"entitlement={snapshot['spanish_entitlement']['status']}, "
            f"pro-rata={snapshot['spanish_pro_rata_pension']['status']}, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "work-exit"
        and args.planning_work_exit_command == "build"
    ):
        try:
            snapshot = build_work_exit_feasibility(
                args.input,
                args.rule_pack,
                args.output,
                inps_snapshot_path=args.inps_snapshot,
                pro_rata_snapshot_path=args.pro_rata_snapshot,
                pension_income_snapshot_path=args.pension_income_snapshot,
                net_worth_snapshot_path=args.net_worth_snapshot,
                liquidity_plan_snapshot_path=args.liquidity_plan_snapshot,
                lifecycle_expenses_snapshot_path=args.lifecycle_expenses_snapshot,
            )
        except WorkExitFeasibilityError as exc:
            print(f"planning work-exit: ERROR ({exc})")
            return 1
        print(
            "planning work-exit: "
            f"{snapshot['status']} "
            f"first={snapshot['first_sustainable_exit_date'] or 'not_found'}, "
            f"{snapshot['search']['candidate_count']} candidates, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "work-exit"
        and args.planning_work_exit_command == "demo"
    ):
        try:
            snapshot = build_work_exit_feasibility(
                default_work_exit_sample_input(),
                default_work_exit_rule_pack(),
                args.output,
                inps_snapshot_path=default_work_exit_sample_inps_snapshot(),
                pro_rata_snapshot_path=default_work_exit_sample_pro_rata_snapshot(),
            )
        except WorkExitFeasibilityError as exc:
            print(f"planning work-exit demo: ERROR ({exc})")
            return 1
        print(
            "planning work-exit demo: "
            f"{snapshot['status']} "
            f"first={snapshot['first_sustainable_exit_date'] or 'not_found'}, "
            f"{snapshot['search']['candidate_count']} candidates, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if args.command == "expenses" and args.expenses_command == "build-lifecycle":
        try:
            snapshot = build_lifecycle_expenses(
                args.input,
                args.output,
                household_snapshot_path=args.household_snapshot,
                timeline_snapshot_path=args.timeline_snapshot,
            )
        except LifecycleExpensesError as exc:
            print(f"expenses: ERROR ({exc})")
            return 1
        print(
            "expenses: "
            f"{snapshot['status']} "
            f"{snapshot['summary']['entry_count']} entries, "
            f"{snapshot['summary']['year_count']} years, "
            f"{snapshot['summary']['data_gap_count']} gaps "
            f"({args.output})"
        )
        return 0

    if args.command == "tax-documents" and args.tax_documents_command == "import":
        try:
            snapshot = import_tax_documents(
                args.cu_dir,
                args.declarations_dir,
                args.output,
            )
        except TaxDocumentsImportError as exc:
            print(f"tax-documents: ERROR ({exc})")
            return 1
        print(
            "tax-documents: "
            f"{snapshot['extraction_status']} "
            f"{snapshot['summary']['record_count']} records, "
            f"{len(snapshot['documents'])} documents, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if args.command == "tax-documents" and args.tax_documents_command == "diagnose":
        try:
            diagnostics = diagnose_tax_documents(args.cu_dir, args.declarations_dir)
        except TaxDocumentsImportError as exc:
            print(f"tax-documents: ERROR ({exc})")
            return 1
        if args.json:
            print(json.dumps(diagnostics, indent=2, sort_keys=True))
        else:
            _print_tax_documents_diagnostics(diagnostics)
        return 0

    if args.command == "retirement" and args.retirement_command == "simulate":
        try:
            simulate_retirement(
                args.net_worth_snapshot,
                args.assumptions_snapshot,
                args.tax_events_snapshot,
                args.output,
                pension_income_snapshot_path=args.pension_income_snapshot,
            )
        except RetirementSimulationError as exc:
            print(f"retirement: ERROR ({exc})")
            return 1
        print(f"retirement: OK ({args.output})")
        return 0

    if args.command == "monte-carlo" and args.monte_carlo_command == "simulate":
        try:
            snapshot = simulate_monte_carlo(
                args.net_worth_snapshot,
                args.assumptions_snapshot,
                args.output,
                args.simulations,
                args.seed,
            )
        except MonteCarloSimulationError as exc:
            print(f"monte-carlo: ERROR ({exc})")
            return 1
        print(f"monte-carlo: {snapshot['status']} ({args.output})")
        return 0

    if args.command == "scenarios" and args.scenarios_command == "compare-retirement":
        try:
            snapshot = compare_retirement_scenarios(
                args.net_worth_snapshot,
                args.assumptions_snapshot,
                args.output,
                args.target_ages or DEFAULT_SCENARIO_TARGET_AGES,
                args.simulations,
                args.seed,
            )
        except ScenarioComparisonError as exc:
            print(f"scenarios: ERROR ({exc})")
            return 1
        print(f"scenarios: {snapshot['status']} ({args.output})")
        return 0

    if args.command == "scenarios" and args.scenarios_command == "compose-v2":
        try:
            snapshot = compose_decision_scenario(
                args.input,
                args.output,
                household_snapshot_path=args.household_snapshot,
                ownership_snapshot_path=args.ownership_snapshot,
                asset_availability_snapshot_path=args.asset_availability_snapshot,
                timeline_snapshot_path=args.timeline_snapshot,
                pension_income_snapshot_path=args.pension_income_snapshot,
                lifecycle_expenses_snapshot_path=args.lifecycle_expenses_snapshot,
            )
        except DecisionScenarioError as exc:
            print(f"scenarios: ERROR ({exc})")
            return 1
        print(
            "scenarios: "
            f"{snapshot['status']} "
            f"{len(snapshot['sources'])} sources, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if args.command == "scenarios" and args.scenarios_command == "evaluate":
        try:
            snapshot = build_decision_outcome(
                args.decision_scenario_snapshot,
                args.input,
                args.output,
            )
        except DecisionOutcomeError as exc:
            print(f"scenarios: ERROR ({exc})")
            return 1
        print(
            "scenarios: "
            f"{snapshot['status']} "
            f"evaluator={snapshot['evaluator']['evaluator_id']}, "
            f"{len(snapshot['metrics'])} metrics, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if args.command == "scenarios" and args.scenarios_command == "sensitivity":
        try:
            snapshot = build_sensitivity_analysis(
                args.decision_scenario_snapshot,
                args.input,
                args.output,
            )
        except SensitivityAnalysisError as exc:
            print(f"scenarios: ERROR ({exc})")
            return 1
        print(
            "scenarios: "
            f"{snapshot['status']} "
            f"{len(snapshot['sensitivity_cases'])} sensitivities, "
            f"{len(snapshot['stress_matrix'])} stress scenarios, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if args.command == "scenarios" and args.scenarios_command == "score":
        try:
            snapshot = build_decision_score(
                args.decision_scenario_snapshot,
                args.sensitivity_analysis_snapshot,
                args.input,
                args.policy,
                args.output,
            )
        except DecisionScoreError as exc:
            print(f"scenarios: ERROR ({exc})")
            return 1
        print(
            "scenarios: "
            f"{snapshot['status']} "
            f"{len(snapshot['alternatives'])} alternatives, "
            f"{len(snapshot['ranking'])} ranked, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if args.command == "scenarios" and args.scenarios_command == "dossier":
        try:
            snapshot = build_decision_dossier(
                args.decision_scenario_snapshot,
                args.sensitivity_analysis_snapshot,
                args.decision_score_snapshot,
                args.input,
                args.output,
                args.markdown_output,
            )
        except DecisionDossierError as exc:
            print(f"scenarios: ERROR ({exc})")
            return 1
        recommendation = snapshot.get("recommendation") or {}
        recommendation_id = recommendation.get("alternative_id", "blocked")
        print(
            "scenarios: "
            f"{snapshot['status']} "
            f"recommendation={recommendation_id}, "
            f"{len(snapshot['blocking_gaps'])} blocking gaps "
            f"({args.output}; {args.markdown_output})"
        )
        return 0

    if args.command == "dashboard" and args.dashboard_command == "build":
        try:
            snapshot = build_decision_dashboard(
                args.net_worth_snapshot,
                args.assumptions_snapshot,
                args.monte_carlo_snapshot,
                args.scenario_comparison_snapshot,
                args.assumptions_readiness_snapshot,
                args.output,
            )
        except DashboardBuildError as exc:
            print(f"dashboard: ERROR ({exc})")
            return 1
        print(f"dashboard: {snapshot['status']} ({args.output})")
        return 0

    if args.command == "report" and args.report_command == "build":
        try:
            build_retirement_report(
                args.simulation_snapshot,
                args.net_worth_snapshot,
                args.output,
                args.assumptions_snapshot,
                args.assumptions_readiness_snapshot,
            )
        except ReportBuildError as exc:
            print(f"report: ERROR ({exc})")
            return 1
        print(f"report: OK ({args.output})")
        return 0

    parser.print_help()
    return 2


def _print_payroll_diagnostics(diagnostics: Mapping[str, object]) -> None:
    input_info = diagnostics["input"]
    summary = diagnostics["summary"]
    assert isinstance(input_info, dict)
    assert isinstance(summary, dict)
    print(f"payroll diagnostics: {diagnostics['status']}")
    print(f"input: {input_info['path']}")
    print(
        "summary: "
        f"{summary['document_count']} documents, "
        f"{summary['record_count']} records, "
        f"{summary['data_gap_count']} gaps"
    )
    documents = diagnostics["documents"]
    assert isinstance(documents, list)
    for document in documents:
        assert isinstance(document, dict)
        gap_codes = document.get("gap_codes") or []
        print(
            "document: "
            f"{document.get('filename')} "
            f"status={document.get('status')} "
            f"records={document.get('record_count')} "
            f"gaps={','.join(gap_codes) if gap_codes else '-'}"
        )
    next_actions = diagnostics["next_actions"]
    assert isinstance(next_actions, list)
    for action in next_actions:
        print(f"next: {action}")


def _print_tax_documents_diagnostics(diagnostics: Mapping[str, object]) -> None:
    input_info = diagnostics["input"]
    summary = diagnostics["summary"]
    assert isinstance(input_info, dict)
    assert isinstance(summary, dict)
    print(f"tax-documents diagnostics: {diagnostics['status']}")
    print(f"cu input: {input_info['cu_path']}")
    print(f"declarations input: {input_info['declarations_path']}")
    print(
        "summary: "
        f"{summary['document_count']} documents, "
        f"{summary['record_count']} records, "
        f"{summary['data_gap_count']} gaps"
    )
    documents = diagnostics["documents"]
    assert isinstance(documents, list)
    for document in documents:
        assert isinstance(document, dict)
        gap_codes = document.get("gap_codes") or []
        print(
            "document: "
            f"{document.get('filename')} "
            f"group={document.get('document_group')} "
            f"status={document.get('status')} "
            f"records={document.get('record_count')} "
            f"gaps={','.join(gap_codes) if gap_codes else '-'}"
        )
    next_actions = diagnostics["next_actions"]
    assert isinstance(next_actions, list)
    for action in next_actions:
        print(f"next: {action}")


if __name__ == "__main__":
    raise SystemExit(main())
