"""Bounded phased-work scenario candidate generation."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from family_office_engine.services.work_transition_simulation import (
    WorkTransitionSimulationError,
    build_work_transition_simulation,
)

SCHEMA_VERSION = "work-transition-candidate-set/v1"
MAX_CANDIDATES = 500


class WorkTransitionCandidateError(ValueError):
    pass


def build_work_transition_candidates(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise WorkTransitionCandidateError(f"schema_version must be {SCHEMA_VERSION}")
    question = data.get("decision_question")
    if not isinstance(question, str) or not question.strip():
        raise WorkTransitionCandidateError("decision_question is required")
    base = data.get("scenario_input")
    if not isinstance(base, dict) or base.get("schema_version") != "work-transition-simulation/v1":
        raise WorkTransitionCandidateError("scenario_input must use work-transition-simulation/v1")
    months = base.get("months")
    if not isinstance(months, int) or isinstance(months, bool) or not 1 <= months <= 600:
        raise WorkTransitionCandidateError("scenario_input months must be an integer from 1 through 600")
    assumptions = base.get("assumptions")
    if not isinstance(assumptions, dict):
        raise WorkTransitionCandidateError("scenario_input assumptions are required")
    full_income = _nonnegative_decimal(assumptions.get("monthly_net_income"), "monthly_net_income")
    provenance = assumptions.get("provenance")
    if not isinstance(provenance, str) or not provenance.strip():
        raise WorkTransitionCandidateError("scenario assumption provenance is required")

    grid = data.get("grid")
    if not isinstance(grid, dict):
        raise WorkTransitionCandidateError("grid is required")
    exits = _unique_values(grid, "full_time_exit_months", 1, months, integer=True)
    fractions = _unique_values(grid, "part_time_fractions", 0, 1, integer=False)
    durations = _unique_values(grid, "part_time_durations_months", 0, months, integer=True)
    stops = _unique_values(grid, "work_stop_months", 1, months, integer=True)
    policies = grid.get("bridge_policies")
    if not isinstance(policies, list) or not policies:
        raise WorkTransitionCandidateError("bridge_policies must be a non-empty array")
    policy_ids: set[str] = set()
    normalized_policies = []
    for policy in policies:
        if not isinstance(policy, dict) or not isinstance(policy.get("policy_id"), str) or not policy["policy_id"].strip():
            raise WorkTransitionCandidateError("each bridge policy requires a non-empty policy_id")
        if policy["policy_id"] in policy_ids:
            raise WorkTransitionCandidateError("bridge policy IDs must be unique")
        policy_ids.add(policy["policy_id"])
        streams = policy.get("income_streams", [])
        if not isinstance(streams, list):
            raise WorkTransitionCandidateError("bridge policy income_streams must be an array")
        normalized_policies.append({"policy_id": policy["policy_id"], "income_streams": streams})

    dimensions = (exits, fractions, durations, stops, normalized_policies)
    candidate_count = 1
    for values in dimensions:
        candidate_count *= len(values)
        if candidate_count > MAX_CANDIDATES:
            raise WorkTransitionCandidateError(f"grid exceeds the {MAX_CANDIDATES} candidate limit")

    constraints = data.get("constraints", {})
    if not isinstance(constraints, dict):
        raise WorkTransitionCandidateError("constraints must be an object")
    min_terminal = _optional_nonnegative(constraints, "minimum_terminal_spendable_assets")
    max_shortfall = _optional_nonnegative(constraints, "maximum_total_shortfall")
    candidates = []
    for exit_month, fraction, duration, stop_month, policy in itertools.product(*dimensions):
        fraction_decimal = Decimal(str(fraction))
        parameters = {"full_time_exit_month": exit_month, "part_time_fraction": str(fraction_decimal),
                      "part_time_duration_months": duration, "work_stop_month": stop_month,
                      "bridge_policy_id": policy["policy_id"]}
        derived = _derive_scenario(base, full_income, provenance, parameters, policy)
        identity_payload = {"parameters": parameters, "scenario_input": derived}
        canonical = json.dumps(identity_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        candidate = {"candidate_id": f"candidate-{digest[:16]}", "content_hash": digest,
                     "parameters": parameters, "scenario_input": derived,
                     "status": "excluded", "reason": None, "scenario_summary": None}
        if stop_month != exit_month + duration:
            candidate["reason"] = "work_stop_must_match_exit_plus_part_time_duration"
        elif (duration == 0) != (fraction_decimal == 0):
            candidate["reason"] = "part_time_fraction_and_duration_are_incompatible"
        else:
            try:
                projection = build_work_transition_simulation(derived)
            except WorkTransitionSimulationError as exc:
                candidate["reason"] = f"derived_scenario_invalid:{exc}"
            else:
                summary = projection["deterministic_baseline"]["summary"]
                candidate["scenario_summary"] = summary
                if max_shortfall is not None and Decimal(summary["total_shortfall"]) > max_shortfall:
                    candidate["reason"] = "maximum_total_shortfall_constraint_not_met"
                elif min_terminal is not None and Decimal(summary["terminal_spendable_assets"]) < min_terminal:
                    candidate["reason"] = "minimum_terminal_spendable_assets_constraint_not_met"
                else:
                    candidate["status"] = "included"
                    candidate["reason"] = "within_declared_constraints"
        candidates.append(candidate)
    result = {"schema_version": SCHEMA_VERSION, "record_type": "WorkTransitionCandidateSet",
            "status": "scenario_projection", "decision_question": question,
            "candidate_count": len(candidates),
            "included_count": sum(item["status"] == "included" for item in candidates),
            "excluded_count": sum(item["status"] == "excluded" for item in candidates),
            "candidates": candidates,
            "data_gaps": [{"code": "candidate_grid_is_not_an_optimizer",
                           "message": "Inclusion reflects declared constraints only; candidates are not ranked or recommended."},
                          {"code": "pension_entitlement_not_assessed",
                           "message": "Scenario assumptions do not establish pension eligibility, timing, amount or payment."}],
            "pension_entitlement": {"status": "not_assessed", "verified_monthly_amount": None,
                                   "verified_start_month": None}}
    canonical_result = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    result["candidate_set_hash"] = hashlib.sha256(canonical_result.encode("utf-8")).hexdigest()
    return result


def _derive_scenario(base: dict[str, Any], full_income: Decimal, provenance: str,
                     parameters: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    assumptions = result["assumptions"]
    assumptions["monthly_net_income"] = "0.00"
    streams = list(assumptions.get("income_streams", []))
    exit_month = parameters["full_time_exit_month"]
    duration = parameters["part_time_duration_months"]
    fraction = Decimal(parameters["part_time_fraction"])
    stop_month = parameters["work_stop_month"]
    if exit_month >= 1:
        streams.append(_income_stream(full_income, 1, exit_month, "full_time_income", provenance))
    if duration:
        parttime_income = (full_income * fraction).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        streams.append(_income_stream(parttime_income, exit_month + 1, stop_month, "part_time_income", provenance))
    streams.extend(policy["income_streams"])
    assumptions["income_streams"] = streams
    assumptions.pop("stress", None)
    return result


def _income_stream(amount: Decimal, start: int, end: int, label: str, provenance: str) -> dict[str, Any]:
    return {"monthly_net_amount": str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "start_month": start, "end_month": end, "assumption_status": "scenario_assumption",
            "provenance": f"{provenance}; derived {label} assumption"}


def _unique_values(source: dict[str, Any], key: str, low: Any, high: Any, *, integer: bool) -> list[Any]:
    raw = source.get(key)
    if not isinstance(raw, list) or not raw:
        raise WorkTransitionCandidateError(f"{key} must be a non-empty array")
    result = []
    for value in raw:
        if integer:
            if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
                raise WorkTransitionCandidateError(f"{key} values must be unique integers from {low} through {high}")
            normalized = value
        else:
            try:
                normalized = Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise WorkTransitionCandidateError(f"{key} values must be finite decimals") from exc
            if not normalized.is_finite() or not Decimal(str(low)) <= normalized <= Decimal(str(high)):
                raise WorkTransitionCandidateError(f"{key} values must be from {low} through {high}")
            normalized = str(normalized.normalize())
        if normalized in result:
            raise WorkTransitionCandidateError(f"{key} values must be unique")
        result.append(normalized)
    return result


def _nonnegative_decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise WorkTransitionCandidateError(f"{field} must be a finite non-negative decimal") from exc
    if not result.is_finite() or result < 0:
        raise WorkTransitionCandidateError(f"{field} must be a finite non-negative decimal")
    return result


def _optional_nonnegative(source: dict[str, Any], key: str) -> Decimal | None:
    return None if source.get(key) is None else _nonnegative_decimal(source[key], key)
