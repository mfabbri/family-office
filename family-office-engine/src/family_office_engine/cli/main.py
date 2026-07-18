import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Mapping

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
from family_office_engine.services.planning_goals import PlanningGoalsError, import_planning_goals
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


def default_eu_pension_coordination_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "eu-pension-coordination-it-es.snapshot.json"


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


def default_household_facts_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "household-facts.snapshot.json"


def default_ownership_graph_input() -> Path:
    return resolve_repo("workspace") / "household" / "ownership-beneficiaries.json"


def default_ownership_graph_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "ownership-beneficiary-graph.snapshot.json"


def default_asset_availability_input() -> Path:
    return resolve_repo("workspace") / "household" / "asset-availability.json"


def default_asset_availability_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "asset-availability.snapshot.json"


def default_timeline_events_input() -> Path:
    return resolve_repo("workspace") / "household" / "timeline-events.json"


def default_timeline_events_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "timeline-events.snapshot.json"


def default_timeline_policy() -> Path:
    return resolve_repo("rules") / "timeline" / "default-overlap-policy.json"


def default_planning_goals_input() -> Path:
    return resolve_repo("workspace") / "household" / "planning-goals.json"


def default_planning_goals_output() -> Path:
    return resolve_repo("workspace") / "snapshots" / "planning-goals.snapshot.json"


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
        and args.planning_goals_command == "validate"
    ):
        try:
            snapshot = import_planning_goals(args.input, args.output, args.timeline_snapshot)
        except PlanningGoalsError as exc:
            print(f"planning goals: ERROR ({exc})")
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
