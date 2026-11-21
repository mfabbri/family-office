"""Constrained, scenario-only comparison of phased-work candidates."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from family_office_engine.services.work_transition_candidates import SCHEMA_VERSION as CANDIDATE_SCHEMA
from family_office_engine.services.work_transition_simulation import (
    WorkTransitionSimulationError,
    build_work_transition_simulation,
)

SCHEMA_VERSION = "work-transition-optimizer/v1"
MAX_EVALUATION_STEPS = 1_000_000
MAX_SENSITIVITY_VARIANTS = 20


class WorkTransitionOptimizerError(ValueError):
    pass


def build_work_transition_optimizer(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise WorkTransitionOptimizerError(f"schema_version must be {SCHEMA_VERSION}")
    question = data.get("decision_question")
    if not isinstance(question, str) or not question.strip():
        raise WorkTransitionOptimizerError("decision_question is required")
    start_month = _month(data.get("plan_start_month"))
    candidates = data.get("candidate_set")
    if not isinstance(candidates, dict) or candidates.get("schema_version") != CANDIDATE_SCHEMA:
        raise WorkTransitionOptimizerError("candidate_set must use work-transition-candidate-set/v1")
    candidate_rows = candidates.get("candidates")
    if not isinstance(candidate_rows, list) or not candidate_rows:
        raise WorkTransitionOptimizerError("candidate_set must contain candidates")
    if not _candidate_set_valid(candidates, candidate_rows):
        unknown_rows = [{"candidate_id": row.get("candidate_id") if isinstance(row, dict) and isinstance(row.get("candidate_id"), str)
                        else f"unidentified-row-{index}", "reason": "candidate_set_integrity_or_coverage_invalid"}
                        for index, row in enumerate(candidate_rows)]
        return _not_assessed_result(question, unknown_rows, "candidate_set_integrity_invalid",
                                    "Candidate IDs, statuses, row hashes, counts or set hash are inconsistent; no date is emitted.")
    policy = data.get("policy")
    if not isinstance(policy, dict):
        raise WorkTransitionOptimizerError("policy is required")
    stress = policy.get("stress")
    constraints = policy.get("constraints")
    if not isinstance(stress, dict) or not isinstance(constraints, dict):
        raise WorkTransitionOptimizerError("explicit common stress and family constraints are required")
    require_reversible = constraints.get("require_reversible", False)
    reversible_ids = constraints.get("reversible_candidate_ids", [])
    if not isinstance(require_reversible, bool) or not isinstance(reversible_ids, list) or any(not isinstance(x, str) for x in reversible_ids):
        raise WorkTransitionOptimizerError("reversibility constraints must be a boolean and candidate ID array")
    months = _month_count(candidate_rows)
    path = stress.get("monthly_return_path")
    trials, seed = stress.get("trials"), stress.get("seed")
    if not isinstance(path, list) or len(path) != months:
        raise WorkTransitionOptimizerError("common stress path must cover the full planning horizon")
    if not isinstance(trials, int) or isinstance(trials, bool) or not 1 <= trials <= 10000:
        raise WorkTransitionOptimizerError("stress trials must be an integer from 1 through 10000")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise WorkTransitionOptimizerError("stress seed must be an integer")
    variants = policy.get("sensitivity_variants", [])
    if not isinstance(variants, list) or len(variants) > MAX_SENSITIVITY_VARIANTS:
        raise WorkTransitionOptimizerError(f"sensitivity_variants must contain at most {MAX_SENSITIVITY_VARIANTS} entries")
    if any(not isinstance(item, dict) or not isinstance(item.get("variant_id"), str) or not item["variant_id"].strip()
           or not isinstance(item.get("constraints"), dict) for item in variants):
        raise WorkTransitionOptimizerError("each sensitivity variant requires variant_id and constraints")
    if len({item["variant_id"] for item in variants}) != len(variants):
        raise WorkTransitionOptimizerError("sensitivity variant IDs must be unique")
    _validate_constraints(constraints)
    for variant in variants:
        _validate_constraints({**constraints, **variant["constraints"]})

    eligible = [row for row in candidate_rows if isinstance(row, dict) and row.get("status") == "included"]
    steps = len(eligible) * months * trials * (1 + len(variants))
    if steps > MAX_EVALUATION_STEPS:
        return {"schema_version": SCHEMA_VERSION, "record_type": "WorkTransitionOptimizer",
                "status": "not_assessed", "decision_question": question,
                "earliest_full_time_exit_date": None, "recommended_full_time_exit_date": None,
                "full_work_exit_date": None, "recommended_candidate_id": None,
                "recommended_fte_plan": None, "evaluated_candidates": [],
                "unassessed_candidates": [{"candidate_id": row.get("candidate_id"),
                                            "reason": "evaluation_budget_exceeded"} for row in eligible],
                "sensitivity": [], "data_gaps": [
                    {"code": "evaluation_budget_exceeded", "message": "No candidate was evaluated because the aggregate work budget was exceeded; no date is emitted."},
                    {"code": "candidate_coverage_incomplete", "message": "All eligible candidates remain unassessed."},
                    {"code": "pension_entitlement_not_assessed", "message": "No pension entitlement is inferred."}],
                "pension_entitlement": {"status": "not_assessed", "verified_start_month": None,
                                        "verified_monthly_amount": None}}
    objective = policy.get("objective")
    _validate_objective(objective)
    evaluated: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for row in candidate_rows:
        if not isinstance(row, dict):
            raise WorkTransitionOptimizerError("candidate rows must be objects")
        if row.get("status") != "included":
            evaluated.append({"candidate_id": row.get("candidate_id"), "status": "excluded",
                              "reason": row.get("reason") or "excluded_by_candidate_set"})
            continue
        if not _candidate_hash_valid(row):
            unknown.append({"candidate_id": row.get("candidate_id"), "reason": "candidate_hash_mismatch"})
            continue
        scenario = row.get("scenario_input")
        if not isinstance(scenario, dict) or scenario.get("months") != months:
            unknown.append({"candidate_id": row.get("candidate_id"), "reason": "scenario_horizon_missing_or_inconsistent"})
            continue
        scenario = copy.deepcopy(scenario)
        scenario["assumptions"]["stress"] = {"monthly_return_path": path, "trials": trials, "seed": seed}
        try:
            result = build_work_transition_simulation(scenario)
        except (WorkTransitionSimulationError, KeyError, TypeError) as exc:
            unknown.append({"candidate_id": row.get("candidate_id"), "reason": f"scenario_not_assessed:{exc}"})
            continue
        metrics = _metrics(row, result)
        evaluated.append({"candidate_id": row["candidate_id"], "status": "pending_feasibility",
                          "reason": None, "metrics": metrics, "parameters": row.get("parameters")})

    if unknown:
        gaps.append({"code": "candidate_coverage_incomplete", "candidate_ids": [x["candidate_id"] for x in unknown],
                     "message": "Unassessed candidates may change the earliest date or recommendation."})
    base_eval = _apply_post_stop_coverage(_apply_constraints(evaluated, constraints), constraints, months)
    base_unknown = unknown + _post_stop_unknowns(base_eval)
    earliest, earliest_ambiguous = _earliest(base_eval, base_unknown, start_month, months, constraints)
    recommendation, recommendation_tie = _recommend(base_eval, base_unknown, objective, start_month, constraints, months)
    if earliest_ambiguous:
        gaps.append({"code": "earliest_date_materially_uncertain", "message": "An unassessed candidate could produce an earlier feasible transition."})
        earliest = None
    if recommendation_tie:
        gaps.append({"code": "recommendation_tie_unresolved", "candidate_ids": recommendation_tie,
                     "message": "The declared lexicographic objective leaves a tie; no recommendation is emitted."})
    elif objective is None:
        gaps.append({"code": "family_objective_not_declared", "message": "Earliest feasibility can be reported, but recommended and full-stop dates remain null."})

    sensitivity = []
    for variant in variants:
        variant_policy = {**constraints, **variant["constraints"]}
        variant_eval = _apply_post_stop_coverage(_apply_constraints(evaluated, variant_policy), variant_policy, months)
        variant_unknown = unknown + _post_stop_unknowns(variant_eval)
        variant_earliest, variant_uncertain = _earliest(variant_eval, variant_unknown, start_month, months, variant_policy)
        variant_rec, variant_tie = _recommend(variant_eval, variant_unknown, objective, start_month, variant_policy, months)
        sensitivity.append({"variant_id": variant["variant_id"],
                            "feasible_count": sum(x["status"] == "feasible" for x in variant_eval),
                            "earliest_full_time_exit_date": None if variant_uncertain else variant_earliest,
                            "recommended_candidate_id": None if variant_tie or not isinstance(variant_rec, dict) else variant_rec["candidate_id"],
                            "unassessed_candidate_ids": [x["candidate_id"] for x in variant_unknown]})
    if not variants:
        gaps.append({"code": "sensitivity_variants_not_provided", "message": "No threshold sensitivity was requested; results use only base constraints."})
    if not any(x.get("status") == "feasible" for x in base_eval):
        gaps.append({"code": "no_feasible_candidate", "message": "No evaluated candidate meets all declared hard constraints."})
    return {"schema_version": SCHEMA_VERSION, "record_type": "WorkTransitionOptimizer",
            "status": "scenario_projection", "decision_question": question,
            "earliest_full_time_exit_date": earliest,
            "recommended_full_time_exit_date": recommendation["transition_date"] if isinstance(recommendation, dict) else None,
            "full_work_exit_date": recommendation["full_stop_date"] if isinstance(recommendation, dict) else None,
            "recommended_candidate_id": recommendation["candidate_id"] if isinstance(recommendation, dict) else None,
            "recommended_fte_plan": recommendation["fte_plan"] if isinstance(recommendation, dict) else None,
            "evaluated_candidates": base_eval, "unassessed_candidates": base_unknown,
            "sensitivity": sensitivity,
            "policy": {"stress": {"monthly_return_path": path, "trials": trials, "seed": seed,
                                   "success_probability_precision": "compare at V4.16 published four-decimal precision"},
                       "constraints": constraints, "objective": objective,
                       "metric_definitions": {"minimum_liquid_buffer": "minimum month-end emergency_reserve plus short_term balance on deterministic baseline",
                                              "p05_terminal_wealth": "V4.16 total terminal wealth including restricted assets",
                                              "first_non_full_time_month": "month after the inclusive last full-time work month",
                                              "full_work_stop_month": "month after the inclusive last month with work income"}},
            "data_gaps": gaps + [{"code": "pension_entitlement_not_assessed",
                                  "message": "Projected transition dates do not establish pension eligibility, start date, amount or payment."}],
            "pension_entitlement": {"status": "not_assessed", "verified_start_month": None,
                                    "verified_monthly_amount": None}}


def _metrics(row: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    baseline = result["deterministic_baseline"]
    summary = baseline["summary"]
    stress = result.get("stress")
    liquid = [Decimal(item["closing_buckets"].get("emergency_reserve", "0")) +
              Decimal(item["closing_buckets"].get("short_term", "0")) for item in baseline["months"]]
    parameters = row["parameters"]
    exit_month = parameters["full_time_exit_month"]
    stop_month = parameters["work_stop_month"]
    transition = exit_month + 1
    full_stop = stop_month + 1
    return {"first_non_full_time_month": transition, "full_work_stop_month": full_stop,
            "total_shortfall": summary["total_shortfall"], "success_probability": stress["success_probability_conditional_on_model"] if stress else None,
            "p05_terminal_wealth": stress["terminal_wealth"]["p5"] if stress else None,
            "minimum_liquid_buffer": str(min(liquid, default=Decimal("0"))),
            "terminal_spendable_assets": summary["terminal_spendable_assets"]}


def _apply_constraints(items: list[dict[str, Any]], constraints: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for item in items:
        if item.get("status") != "pending_feasibility":
            output.append(item)
            continue
        metrics = item["metrics"]
        missing = [key for key in ("maximum_total_shortfall", "minimum_success_probability", "minimum_p05_terminal_wealth", "minimum_liquid_buffer")
                   if key not in constraints]
        if missing or metrics["success_probability"] is None or metrics["p05_terminal_wealth"] is None:
            output.append({**item, "status": "not_assessed", "reason": "required_comparable_metric_or_threshold_missing"})
            continue
        if constraints.get("require_reversible", False) and item.get("candidate_id") not in constraints.get("reversible_candidate_ids", []):
            output.append({**item, "status": "infeasible", "reason": "reversibility_not_attested_by_candidate_input"})
            continue
        # V4.16 publishes success probability to four decimals; compare on that basis.
        meets = (Decimal(metrics["total_shortfall"]) <= Decimal(str(constraints["maximum_total_shortfall"])) and
                 Decimal(metrics["success_probability"]) >= Decimal(str(constraints["minimum_success_probability"])) and
                 Decimal(metrics["p05_terminal_wealth"]) >= Decimal(str(constraints["minimum_p05_terminal_wealth"])) and
                 Decimal(metrics["minimum_liquid_buffer"]) >= Decimal(str(constraints["minimum_liquid_buffer"])))
        output.append({**item, "status": "feasible" if meets else "infeasible",
                       "reason": "meets_all_declared_hard_constraints" if meets else "one_or_more_hard_constraints_not_met"})
    return output


def _apply_post_stop_coverage(items: list[dict[str, Any]], constraints: dict[str, Any], horizon: int) -> list[dict[str, Any]]:
    required = constraints["minimum_post_stop_months"]
    output = []
    for item in items:
        if item.get("status") not in {"feasible", "infeasible"}:
            output.append(item)
            continue
        observed = horizon - item["metrics"]["full_work_stop_month"] + 1
        if observed < required:
            output.append({**item, "status": "not_assessed", "reason": "post_stop_horizon_coverage_incomplete",
                           "post_stop_coverage": {"required_months": required, "observed_months": observed}})
        else:
            output.append({**item, "post_stop_coverage": {"required_months": required, "observed_months": observed}})
    return output


def _post_stop_unknowns(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"candidate_id": item["candidate_id"], "reason": item["reason"],
             **item.get("post_stop_coverage", {})} for item in items
            if item.get("status") == "not_assessed" and item.get("reason") == "post_stop_horizon_coverage_incomplete"]


def _earliest(items: list[dict[str, Any]], unknown: list[dict[str, Any]], start: date, horizon: int,
              constraints: dict[str, Any]) -> tuple[str | None, bool]:
    minimum_post_stop = constraints.get("minimum_post_stop_months", 1)
    if not isinstance(minimum_post_stop, int) or isinstance(minimum_post_stop, bool) or minimum_post_stop < 0:
        raise WorkTransitionOptimizerError("minimum_post_stop_months must be a non-negative integer")
    feasible = [x for x in items if x.get("status") == "feasible"
                and Decimal(x["parameters"]["part_time_fraction"]) < 1
                and horizon - x["metrics"]["full_work_stop_month"] + 1 >= minimum_post_stop]
    if not feasible:
        return None, False
    earliest_month = min(x["metrics"]["first_non_full_time_month"] for x in feasible)
    if any(_unknown_could_precede(x, earliest_month) for x in unknown):
        return None, True
    return _month_date(start, earliest_month), False


def _recommend(items: list[dict[str, Any]], unknown: list[dict[str, Any]], objective: Any,
               start: date, constraints: dict[str, Any], horizon: int) -> tuple[dict[str, Any] | None, list[str]]:
    if objective is None:
        return None, []
    feasible = [x for x in items if x.get("status") == "feasible"
                and Decimal(x["parameters"]["part_time_fraction"]) < 1
                and horizon - x["metrics"]["full_work_stop_month"] + 1 >= constraints.get("minimum_post_stop_months", 1)]
    if not feasible or unknown:
        return None, []
    def key(item: dict[str, Any]) -> tuple[Decimal, ...]:
        metrics = item["metrics"]
        values = []
        for criterion in objective["criteria"]:
            name = criterion["metric"]
            if name == "earliest_transition_month":
                value = Decimal(metrics["first_non_full_time_month"])
            else:
                value = Decimal(str(metrics[name]))
            values.append(value if criterion["direction"] == "minimize" else -value)
        return tuple(values)
    ordered = sorted(feasible, key=key)
    best_key = key(ordered[0])
    ties = [x["candidate_id"] for x in ordered if key(x) == best_key]
    if len(ties) > 1:
        if objective.get("tie_breaker") == "earliest_transition":
            chosen = min((x for x in ordered if x["candidate_id"] in ties), key=lambda x: x["metrics"]["first_non_full_time_month"])
            ties = [chosen["candidate_id"]] if sum(x["metrics"]["first_non_full_time_month"] == chosen["metrics"]["first_non_full_time_month"] for x in ordered if x["candidate_id"] in ties) == 1 else ties
        if len(ties) > 1:
            return None, ties
    selected = next(x for x in ordered if x["candidate_id"] == ties[0])
    transition = selected["metrics"]["first_non_full_time_month"]
    stop = selected["metrics"]["full_work_stop_month"]
    return {"candidate_id": selected["candidate_id"], "transition_date": _month_date(start, transition),
            "full_stop_date": _month_date(start, stop), "fte_plan": selected["parameters"]}, []


def _unknown_could_precede(item: dict[str, Any], known_month: int) -> bool:
    return item.get("candidate_id") is not None


def _candidate_hash_valid(row: dict[str, Any]) -> bool:
    parameters, scenario = row.get("parameters"), row.get("scenario_input")
    if not isinstance(parameters, dict) or not isinstance(scenario, dict):
        return False
    canonical = json.dumps({"parameters": parameters, "scenario_input": scenario}, sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return row.get("content_hash") == digest and row.get("candidate_id") == f"candidate-{digest[:16]}"


def _candidate_set_valid(candidates: dict[str, Any], rows: list[Any]) -> bool:
    if candidates.get("candidate_count") != len(rows):
        return False
    if any(not isinstance(row, dict) or row.get("status") not in {"included", "excluded"}
           or not _candidate_hash_valid(row) for row in rows):
        return False
    ids = [row["candidate_id"] for row in rows]
    if len(set(ids)) != len(ids):
        return False
    included = sum(row["status"] == "included" for row in rows)
    excluded = sum(row["status"] == "excluded" for row in rows)
    if candidates.get("included_count") != included or candidates.get("excluded_count") != excluded:
        return False
    payload = {key: value for key, value in candidates.items() if key != "candidate_set_hash"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return candidates.get("candidate_set_hash") == hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _not_assessed_result(question: str, unknown: list[dict[str, Any]], code: str, message: str) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "record_type": "WorkTransitionOptimizer",
            "status": "not_assessed", "decision_question": question,
            "earliest_full_time_exit_date": None, "recommended_full_time_exit_date": None,
            "full_work_exit_date": None, "recommended_candidate_id": None,
            "recommended_fte_plan": None, "evaluated_candidates": [],
            "unassessed_candidates": unknown, "sensitivity": [],
            "data_gaps": [{"code": code, "message": message},
                           {"code": "pension_entitlement_not_assessed", "message": "No pension entitlement is inferred."}],
            "pension_entitlement": {"status": "not_assessed", "verified_start_month": None,
                                    "verified_monthly_amount": None}}


def _validate_constraints(constraints: dict[str, Any]) -> None:
    for key in ("maximum_total_shortfall", "minimum_p05_terminal_wealth", "minimum_liquid_buffer"):
        if key not in constraints:
            raise WorkTransitionOptimizerError(f"constraint {key} is required")
        value = _finite_decimal(constraints[key], key)
        if value < 0:
            raise WorkTransitionOptimizerError(f"constraint {key} must be non-negative")
    if "minimum_success_probability" not in constraints:
        raise WorkTransitionOptimizerError("constraint minimum_success_probability is required")
    probability = _finite_decimal(constraints["minimum_success_probability"], "minimum_success_probability")
    if not Decimal("0") <= probability <= Decimal("1"):
        raise WorkTransitionOptimizerError("minimum_success_probability must be from 0 through 1")
    minimum_post_stop = constraints.get("minimum_post_stop_months")
    if not isinstance(minimum_post_stop, int) or isinstance(minimum_post_stop, bool) or minimum_post_stop < 1:
        raise WorkTransitionOptimizerError("minimum_post_stop_months must be an integer of at least 1")
    require_reversible = constraints.get("require_reversible", False)
    reversible_ids = constraints.get("reversible_candidate_ids", [])
    if not isinstance(require_reversible, bool) or not isinstance(reversible_ids, list) or any(not isinstance(x, str) for x in reversible_ids):
        raise WorkTransitionOptimizerError("reversibility constraints must be a boolean and candidate ID array")


def _finite_decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise WorkTransitionOptimizerError(f"{field} must be a finite decimal") from exc
    if not result.is_finite():
        raise WorkTransitionOptimizerError(f"{field} must be a finite decimal")
    return result


def _month_count(rows: list[dict[str, Any]]) -> int:
    counts = {row.get("scenario_input", {}).get("months") for row in rows
              if isinstance(row, dict) and isinstance(row.get("scenario_input"), dict)}
    if len(counts) != 1 or not counts or not isinstance(next(iter(counts)), int):
        raise WorkTransitionOptimizerError("all candidates must share one valid planning horizon")
    return next(iter(counts))


def _validate_objective(objective: Any) -> None:
    if objective is None:
        return
    allowed = {"success_probability", "p05_terminal_wealth", "minimum_liquid_buffer", "terminal_spendable_assets", "earliest_transition_month"}
    if not isinstance(objective, dict) or objective.get("method") != "lexicographic" or not isinstance(objective.get("criteria"), list) or not objective["criteria"]:
        raise WorkTransitionOptimizerError("objective must declare a non-empty lexicographic criteria list")
    for item in objective["criteria"]:
        if not isinstance(item, dict) or item.get("metric") not in allowed or item.get("direction") not in {"minimize", "maximize"}:
            raise WorkTransitionOptimizerError("objective criteria must use supported metrics and directions")
    if objective.get("tie_breaker") not in {None, "earliest_transition"}:
        raise WorkTransitionOptimizerError("unsupported objective tie_breaker")


def _month(value: Any) -> date:
    if not isinstance(value, str) or len(value) != 7 or value[4] != "-":
        raise WorkTransitionOptimizerError("plan_start_month must use YYYY-MM")
    try:
        return date.fromisoformat(value + "-01")
    except ValueError as exc:
        raise WorkTransitionOptimizerError("plan_start_month must be a valid calendar month") from exc


def _month_date(start: date, month_index: int) -> str:
    offset = month_index - 1
    year = start.year + (start.month - 1 + offset) // 12
    month = (start.month - 1 + offset) % 12 + 1
    return date(year, month, 1).isoformat()
