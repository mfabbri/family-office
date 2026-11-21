"""End-to-end, scenario-only work-transition plan composition."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

from family_office_engine.services.retirement_bridge_projection import (
    RetirementBridgeProjectionError,
    build_retirement_bridge_projection,
)
from family_office_engine.services.work_transition_candidates import (
    WorkTransitionCandidateError,
    build_work_transition_candidates,
)
from family_office_engine.services.work_transition_optimizer import (
    WorkTransitionOptimizerError,
    build_work_transition_optimizer,
)
from family_office_engine.services.work_transition_simulation import (
    WorkTransitionSimulationError,
    build_work_transition_simulation,
)

SCHEMA_VERSION = "work-transition-plan/v1"
INPUT_SCHEMA_VERSION = "work-transition-plan-input/v1"


class WorkTransitionPlanError(ValueError):
    """Raised when a composed work-transition plan is invalid."""


def build_work_transition_plan(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise WorkTransitionPlanError(f"schema_version must be {INPUT_SCHEMA_VERSION}")
    if not isinstance(data.get("household_id"), str) or not data["household_id"].strip():
        raise WorkTransitionPlanError("household_id is required")
    if not isinstance(data.get("decision_question"), str) or not data["decision_question"].strip():
        raise WorkTransitionPlanError("decision_question is required")
    as_of_date = data.get("as_of_date")
    if not isinstance(as_of_date, str):
        raise WorkTransitionPlanError("as_of_date must use YYYY-MM-DD")
    try:
        parsed_as_of_date = date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise WorkTransitionPlanError("as_of_date must use YYYY-MM-DD") from exc
    if parsed_as_of_date.isoformat() != as_of_date:
        raise WorkTransitionPlanError("as_of_date must use YYYY-MM-DD")
    provenance = data.get("provenance")
    if not isinstance(provenance, dict) or not isinstance(provenance.get("origin"), str) or not provenance["origin"].strip():
        raise WorkTransitionPlanError("provenance.origin is required")
    readiness = data.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("status") not in {"ready", "blocked", "partial"}:
        raise WorkTransitionPlanError("readiness must declare ready, partial or blocked status")
    if not isinstance(readiness.get("data_gaps", []), list):
        raise WorkTransitionPlanError("readiness.data_gaps must be an array")
    phase_plan = data.get("phase_plan")
    if not isinstance(phase_plan, list) or len(phase_plan) != 3:
        raise WorkTransitionPlanError("phase_plan must declare full_time, part_time and stop phases")
    expected_phases = [("full_time", {"1", "1.0", "1.00"}), ("part_time", {"0.6", "0.60"}), ("stop", {"0", "0.0", "0.00"})]
    for index, phase in enumerate(phase_plan):
        if not isinstance(phase, dict) or not isinstance(phase.get("stage"), str) or not phase["stage"].strip():
            raise WorkTransitionPlanError(f"phase_plan[{index}].stage is required")
        fraction = phase.get("work_fraction")
        stage, accepted_fractions = expected_phases[index]
        if phase["stage"] != stage or not isinstance(fraction, (int, float, str)) or str(fraction) not in accepted_fractions:
            raise WorkTransitionPlanError(f"phase_plan[{index}] must match the {stage} phase and work fraction")
        start_month, end_month = phase.get("start_month"), phase.get("end_month")
        if (not isinstance(start_month, int) or isinstance(start_month, bool) or start_month < 1
                or not isinstance(end_month, int) or isinstance(end_month, bool) or end_month < start_month):
            raise WorkTransitionPlanError(f"phase_plan[{index}] requires valid inclusive start_month/end_month")
        if index and start_month != phase_plan[index - 1]["end_month"] + 1:
            raise WorkTransitionPlanError("phase_plan months must be contiguous and non-overlapping")
        if not isinstance(phase.get("provenance"), str) or not phase["provenance"].strip():
            raise WorkTransitionPlanError(f"phase_plan[{index}].provenance is required")

    bridge_input = data.get("bridge_input")
    simulation_input = data.get("simulation_input")
    candidate_input = data.get("candidate_input")
    optimizer_policy = data.get("optimizer_policy")
    plan_start_month = data.get("plan_start_month")
    if not isinstance(optimizer_policy, dict) or not isinstance(plan_start_month, str):
        raise WorkTransitionPlanError("optimizer_policy and plan_start_month are required")
    try:
        bridge = build_retirement_bridge_projection(bridge_input)
        simulation = build_work_transition_simulation(simulation_input)
        candidates = build_work_transition_candidates(candidate_input)
        optimizer = build_work_transition_optimizer({
            "schema_version": "work-transition-optimizer/v1",
            "decision_question": data["decision_question"],
            "plan_start_month": plan_start_month,
            "candidate_set": candidates,
            "policy": optimizer_policy,
        })
    except (RetirementBridgeProjectionError, WorkTransitionSimulationError,
            WorkTransitionCandidateError, WorkTransitionOptimizerError, KeyError, TypeError) as exc:
        raise WorkTransitionPlanError(str(exc)) from exc

    if any(item.get("status") != "scenario_projection" for item in (bridge, simulation, candidates, optimizer)):
        raise WorkTransitionPlanError("all composed projections must retain scenario_projection status")
    if any(not _entitlement_unverified(component.get("pension_entitlement"))
           for component in (bridge, candidates, optimizer)):
        raise WorkTransitionPlanError("scenario projections cannot populate verified pension entitlement")

    excluded = [
        {"candidate_id": item.get("candidate_id"), "reason": item.get("reason")}
        for item in candidates.get("candidates", []) if item.get("status") == "excluded"
    ]
    rejected = [
        {"candidate_id": item.get("candidate_id"), "reason": item.get("reason")}
        for item in optimizer.get("evaluated_candidates", [])
        if item.get("status") in {"infeasible", "excluded", "not_assessed"}
    ]
    gaps = _merge_gaps(
        readiness.get("data_gaps", []), bridge.get("data_gaps", []),
        simulation.get("data_gaps", []), candidates.get("data_gaps", []),
        optimizer.get("data_gaps", []),
    )
    blockers = []
    if readiness["status"] != "ready":
        blockers.append(f"readiness_{readiness['status']}")
    if optimizer.get("status") == "not_assessed":
        blockers.append("optimization_not_assessed")
    if not optimizer.get("earliest_full_time_exit_date"):
        blockers.append("no_assessed_earliest_transition_date")
    if not any(item.get("status") == "feasible" for item in optimizer.get("evaluated_candidates", [])):
        blockers.append("no_feasible_candidate_under_declared_constraints")

    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "WorkTransitionPlan",
        "status": "scenario_projection",
        "decision_question": data["decision_question"],
        "household_id": data["household_id"],
        "as_of_date": data.get("as_of_date"),
        "readiness_report": deepcopy(readiness),
        "phase_plan": deepcopy(phase_plan),
        "provenance": deepcopy(provenance),
        "assumptions": {
            "origin": provenance["origin"],
            "bridge": bridge["assumptions"],
            "simulation": simulation.get("assumptions"),
            "optimizer_policy": optimizer.get("policy"),
        },
        "bridge_projection": bridge,
        "risk_metrics": {
            "simulation_baseline": simulation.get("deterministic_baseline", {}).get("summary"),
            "simulation_stress": simulation.get("stress"),
            "optimizer_earliest_full_time_exit_date": optimizer.get("earliest_full_time_exit_date"),
            "optimizer_recommended_full_time_exit_date": optimizer.get("recommended_full_time_exit_date"),
            "optimizer_full_work_exit_date": optimizer.get("full_work_exit_date"),
            "optimizer_sensitivity": optimizer.get("sensitivity", []),
        },
        "candidate_set": candidates,
        "optimization": optimizer,
        "rejected_candidates": excluded + rejected,
        "blockers": blockers,
        "data_gaps": gaps,
        "pension_entitlement": {
            "status": "not_assessed",
            "verified_start_date": None,
            "verified_monthly_amount": None,
        },
        "next_action": (
            "Completa i data_gaps con fatti documentati nel workspace e riesegui il piano; fai rivedere le ipotesi a un professionista prima di agire."
            if gaps or blockers else
            "Rivedi con la famiglia e con un professionista le ipotesi dichiarate e la provenienza prima di agire."
        ),
        "notes": "All bridge, simulation and transition dates are scenario projections. No pension entitlement, tax result or administrative determination is established.",
    }


def synthetic_work_transition_plan_input() -> dict[str, Any]:
    """Return a deterministic, non-personal golden plan for the CLI demo."""
    months = 6
    base_assumptions = {
        "provenance": "synthetic V4.20 golden scenario; not household facts",
        "annual_inflation_rate": "0.02",
        "annual_return_rate": "0.03",
        "monthly_net_income": "6000",
        "monthly_household_spending": "5200",
        "monthly_declared_tax": "0",
        "monthly_declared_costs": "0",
        "emergency_floor_months": "3",
        "draw_order": ["emergency_reserve", "short_term", "medium_term"],
        "buckets": [
            {"bucket": "emergency_reserve", "opening_balance": "18000"},
            {"bucket": "short_term", "opening_balance": "42000"},
            {"bucket": "medium_term", "opening_balance": "90000"},
            {"bucket": "restricted", "opening_balance": "25000"},
        ],
        "income_streams": [{
            "stream_id": "synthetic_spouse_income",
            "monthly_net_amount": "1800",
            "start_month": 1,
            "end_month": months,
            "assumption_status": "scenario_assumption",
            "provenance": "synthetic spouse-income assumption",
        }],
        "stress": {
            "monthly_return_path": ["-0.12", "-0.06", "0.01", "0.02", "0.01", "0.02"],
            "trials": 16,
            "seed": 42020,
        },
    }
    simulation = {
        "schema_version": "work-transition-simulation/v1",
        "decision_question": "How do declared phases affect the synthetic household cash-flow and asset path?",
        "months": months,
        "assumptions": deepcopy(base_assumptions),
    }
    candidate_scenario = {key: deepcopy(value) for key, value in simulation.items() if key != "assumptions"}
    candidate_scenario["assumptions"] = deepcopy(base_assumptions)
    candidate = {
        "schema_version": "work-transition-candidate-set/v1",
        "decision_question": "Which synthetic transition candidate meets the declared constraints?",
        "scenario_input": candidate_scenario,
        "grid": {
            "full_time_exit_months": [1, 2],
            "part_time_fractions": ["0.6", "0"],
            "part_time_durations_months": [2, 0],
            "work_stop_months": [3, 5],
            "bridge_policies": [{
                "policy_id": "es_then_inps_scenario_assumptions",
                "income_streams": [
                    {"monthly_net_amount": "500", "start_month": 3, "end_month": 4,
                     "assumption_status": "scenario_assumption", "provenance": "synthetic RITA fund scenario assumption"},
                    {"monthly_net_amount": "700", "start_month": 4, "end_month": 5,
                     "assumption_status": "scenario_assumption", "provenance": "synthetic ES pension scenario assumption"},
                    {"monthly_net_amount": "900", "start_month": 6, "end_month": 6,
                     "assumption_status": "scenario_assumption", "provenance": "synthetic INPS pension scenario assumption"},
                ],
            }],
        },
        "constraints": {"minimum_terminal_spendable_assets": "0", "maximum_total_shortfall": "25000"},
    }
    bridge = {
        "schema_version": "retirement-bridge-projection/v1",
        "household_id": "synthetic_v420_household",
        "as_of_month": "2026-11",
        "months": months,
        "assumptions": {
            "opening_available_assets": "175000",
            "monthly_household_spending": "5200",
            "monthly_full_time_net_income": "6000",
            "annual_inflation_rate": "0.02",
            "annual_return_rate": "0.03",
            "provenance": "synthetic V4.20 golden assumptions; no real-family data",
            "hypothetical_pension": {
                "monthly_net_amount": "800", "start_month": 4,
                "assumption_status": "scenario_assumption",
                "provenance": "synthetic ES/INPS transition placeholder; not an entitlement estimate",
            },
        },
    }
    return {
        "schema_version": INPUT_SCHEMA_VERSION,
        "household_id": "synthetic_v420_household",
        "as_of_date": "2026-11-01",
        "decision_question": "When can a synthetic household move from full-time to part-time and stop work under declared assumptions?",
        "readiness": {"status": "partial", "data_gaps": [{
            "code": "source_bound_pension_entitlement_missing",
            "message": "No source-bound Spanish or INPS entitlement facts are present in this synthetic scenario.",
        }, {
            "code": "spouse_income_excluded_from_linear_bridge",
            "message": "Synthetic spouse income is included in the cash-flow simulation; the 100/60/0 retirement bridge scales only the primary declared net-income assumption.",
        }]},
        "phase_plan": [
            {"stage": "full_time", "work_fraction": "1.00", "start_month": 1, "end_month": 2,
             "provenance": "synthetic golden scenario assumption"},
            {"stage": "part_time", "work_fraction": "0.60", "start_month": 3, "end_month": 4,
             "provenance": "synthetic golden scenario assumption"},
            {"stage": "stop", "work_fraction": "0.00", "start_month": 5, "end_month": 6,
             "provenance": "synthetic golden scenario assumption"},
        ],
        "provenance": {"origin": "synthetic golden fixture", "source_ids": [], "personal_data": False},
        "plan_start_month": "2026-11",
        "bridge_input": bridge,
        "simulation_input": simulation,
        "candidate_input": candidate,
        "optimizer_policy": {
            "stress": {"monthly_return_path": ["-0.12", "-0.06", "0.01", "0.02", "0.01", "0.02"],
                       "trials": 16, "seed": 42020},
            "constraints": {"maximum_total_shortfall": "25000", "minimum_success_probability": "0.75",
                            "minimum_p05_terminal_wealth": "80000", "minimum_liquid_buffer": "0",
                            "minimum_post_stop_months": 1},
            "objective": {"method": "lexicographic",
                          "criteria": [{"metric": "p05_terminal_wealth", "direction": "maximize"}],
                          "tie_breaker": "earliest_transition"},
            "sensitivity_variants": [{"variant_id": "stricter_terminal_wealth",
                                       "constraints": {"minimum_p05_terminal_wealth": "120000"}}],
        },
    }


def _merge_gaps(*groups: list[Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        for item in group:
            if not isinstance(item, dict):
                continue
            normalized = deepcopy(item)
            key = (str(normalized.get("code", "unknown_gap")), str(normalized.get("message", "")))
            if key not in seen:
                seen.add(key)
                output.append(normalized)
    return output


def _entitlement_unverified(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("status") == "not_assessed"
        and value.get("verified_start_month") is None
        and value.get("verified_monthly_amount") is None
    )
