import argparse
import hashlib
import json
import os
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
from family_office_engine.services.household_facts import HouseholdFactsError, import_household_facts
from family_office_engine.services.ownership_graph import OwnershipGraphError, import_ownership_graph
from family_office_engine.services.asset_availability import AssetAvailabilityError, import_asset_availability
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


def default_pension_income_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "pension-income.snapshot.json"


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


def default_estate_baseline_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "estate-baseline.snapshot.json"


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


def run_planning_goals_wizard(input_path: Path, overwrite: bool = False) -> dict[str, Any]:
    print("planning goals wizard: leave uncertain answers blank; they will be marked as data gaps.")
    household_id = _prompt_text("Household id", "household_private")
    as_of_date = _prompt_text("As-of date (YYYY-MM-DD)", "2026-01-01")
    start_year = _prompt_int("Planning start year", 2026)
    end_year = _prompt_int("Planning end year", start_year + 30)
    risk_capacity = _prompt_choice("Risk capacity (low/medium/high/unknown)", "unknown", {"low", "medium", "high", "unknown"})
    risk_tolerance = _prompt_choice(
        "Risk tolerance (low/medium/high/unknown)",
        "unknown",
        {"low", "medium", "high", "unknown"},
    )
    max_loss_ratio = _prompt_decimal_text("Maximum acceptable loss ratio", "0.20")
    reserve_months = _prompt_int("Minimum emergency reserve months", 12)
    annual_need = _prompt_decimal_text("Target annual net retirement need", "0.00")
    target_year = _prompt_int("Target retirement income year", max(start_year, 2035))

    gaps = _wizard_gaps(
        [
            (risk_capacity == "unknown", "unknown_risk_capacity", "Risk capacity was left unknown in the wizard."),
            (risk_tolerance == "unknown", "unknown_risk_tolerance", "Risk tolerance was left unknown in the wizard."),
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
    _write_wizard_json(input_path, data, overwrite, PlanningGoalsError, "planning goals")
    return {"status": "prepared", "input_path": str(input_path), "data_gap_count": len(gaps)}


def run_liquidity_plan_wizard(input_path: Path, overwrite: bool = False) -> dict[str, Any]:
    print("planning liquidity wizard: enter declared values only; uncertain fields become data gaps.")
    household_id = _prompt_text("Household id", "household_private")
    as_of_date = _prompt_text("As-of date (YYYY-MM-DD)", "2026-01-01")
    base_currency = _prompt_text("Base currency", "EUR").upper()
    monthly_expenses = _prompt_decimal_text("Monthly expenses", "0.00")
    reserve_months = _prompt_int("Minimum emergency reserve months", 12)
    concentration_threshold = _prompt_decimal_text("Concentration threshold ratio", "0.60")
    gaps = _wizard_gaps(
        [(monthly_expenses == "0.00", "unknown_monthly_expenses", "Monthly expenses must be reviewed.")]
    )
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


def run_decumulation_policy_wizard(input_path: Path, overwrite: bool = False) -> dict[str, Any]:
    print("planning decumulation wizard: rates and returns must be explicit reviewed assumptions.")
    household_id = _prompt_text("Household id", "household_private")
    as_of_date = _prompt_text("As-of date (YYYY-MM-DD)", "2026-01-01")
    base_currency = _prompt_text("Base currency", "EUR").upper()
    current_age = _prompt_int("Current age", 60)
    retirement_age = _prompt_int("Retirement age", max(current_age, 67))
    end_age = _prompt_int("End age", max(retirement_age, 95))
    annual_spending_need = _prompt_decimal_text("Annual spending need", "0.00")
    cash_buffer_target = _prompt_decimal_text("Cash buffer target", "0.00")
    withdrawal_order = _prompt_list("Withdrawal asset ids, comma-separated", ["asset_cash"])
    include_rita = _prompt_bool("Include RITA bridge? (yes/no)", False)
    annual_returns = _prompt_list("Annual return sequence, comma-separated decimals", ["0.00"])
    withdrawal_tax_rate = _prompt_decimal_text("Withdrawal tax rate", "0.00")
    pension_tax_rate = _prompt_decimal_text("Pension tax rate", "0.00")
    rita_tax_rate = _prompt_decimal_text("RITA tax rate", "0.00")
    gaps = _wizard_gaps(
        [
            (annual_spending_need == "0.00", "unknown_annual_spending_need", "Annual spending need must be reviewed."),
            (cash_buffer_target == "0.00", "unknown_cash_buffer_target", "Cash buffer target must be reviewed."),
            (annual_returns == ["0.00"], "unknown_return_assumption", "Return sequence must be reviewed."),
        ]
    )
    data = {
        "schema_version": "decumulation-policy-set/v1",
        "record_type": "DecumulationPolicySet",
        "household_id": household_id,
        "as_of_date": as_of_date,
        "base_currency": base_currency,
        "current_age": current_age,
        "policies": [
            {
                "policy_id": "wizard_policy",
                "label": "Wizard policy",
                "retirement_age": retirement_age,
                "end_age": end_age,
                "annual_spending_need": annual_spending_need,
                "cash_buffer_target": cash_buffer_target,
                "withdrawal_order": withdrawal_order,
                "include_rita": include_rita,
                "annual_return_sequence": annual_returns,
                "withdrawal_tax_rate": withdrawal_tax_rate,
                "pension_tax_rate": pension_tax_rate,
                "rita_tax_rate": rita_tax_rate,
            }
        ],
        "data_gaps": gaps,
    }
    validate_decumulation_policy_set(data)
    _write_wizard_json(input_path, data, overwrite, DecumulationStrategyError, "decumulation policy set")
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


def _prompt_text(label: str, default: str) -> str:
    value = input(f"{label} [{default}]: ").strip()
    return value or default


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
            "next_action": "fill planning-goals.json, then run `fo planning goals validate`",
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


def format_planning_goals_error(exc: PlanningGoalsError, input_path: Path) -> str:
    message = str(exc)
    if "Planning goals file not found:" in message:
        return (
            f"{message}. Run `fo planning goals prepare` to create the editable private input, "
            "or `fo planning goals demo` for a synthetic smoke check."
        )
    if _is_unedited_planning_goals_draft(input_path):
        return (
            f"Planning goals input is still an unedited draft: {input_path}. "
            "Fill household_id, as_of_date, planning_horizon, risk_profile, liquidity_policy, "
            "objectives and constraints, then run `fo planning goals validate` again."
        )
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
        "--output",
        type=Path,
        default=default_asset_availability_output(),
        help="Output asset availability snapshot JSON path",
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
            snapshot = import_asset_availability(args.input, args.output, args.ownership_snapshot)
        except AssetAvailabilityError as exc:
            print(f"household availability: ERROR ({exc})")
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
        except PlanningGoalsError as exc:
            print(f"planning goals wizard: ERROR ({exc})")
            return 1
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
        except LiquidityPlanError as exc:
            print(f"planning liquidity wizard: ERROR ({exc})")
            return 1
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
        print(
            "planning liquidity: "
            f"{snapshot['status']} "
            f"reserve={snapshot['emergency_reserve']['funded_amount']}/"
            f"{snapshot['emergency_reserve']['target_amount']} "
            f"{len(snapshot['asset_assignments'])} assets, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
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
        print(
            "planning liquidity demo: "
            f"goals={planning_snapshot['status']} "
            f"liquidity={snapshot['status']} "
            f"reserve={snapshot['emergency_reserve']['funded_amount']}/"
            f"{snapshot['emergency_reserve']['target_amount']} "
            f"{len(snapshot['asset_assignments'])} assets, "
            f"{len(snapshot['data_gaps'])} gaps "
            f"({args.output})"
        )
        return 0

    if (
        args.command == "planning"
        and args.planning_command == "decumulation"
        and args.planning_decumulation_command == "wizard"
    ):
        try:
            result = run_decumulation_policy_wizard(args.input, args.overwrite)
        except DecumulationStrategyError as exc:
            print(f"planning decumulation wizard: ERROR ({exc})")
            return 1
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
            print(f"planning pension-contributions: ERROR ({exc})")
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
        and args.planning_it_es_eu_pension_command == "build"
    ):
        try:
            snapshot = build_it_es_eu_pension_pro_rata(args.input, args.rule_pack, args.output)
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
