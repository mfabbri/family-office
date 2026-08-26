"""Deterministic V5.6 scenario drafting; it never composes or executes a scenario."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from family_office_engine.services.question_intent import route_question_intent

SCHEMA_VERSION = "scenario-draft/v1"
RECORD_TYPE = "ScenarioDraft"
_INJECTION_PROBLEM = "prompt_injection_or_tool_instruction"
_AGE_PATTERN = re.compile(r"\b(\d{1,3})\s*anni\b")
_DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_AMOUNT_PATTERN = re.compile(r"(?:budget\s+(?:di\s+)?)?(?:€\s*|euro\s*)(-?\d+(?:[.,]\d{1,2})?)", re.IGNORECASE)


class ScenarioDraftError(ValueError):
    pass


def build_scenario_draft(question: str, output_path: Path) -> dict[str, Any]:
    snapshot = draft_scenario(question)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ScenarioDraftError(f"Cannot write scenario draft: {output_path}") from exc
    return snapshot


def draft_scenario(question: str) -> dict[str, Any]:
    """Extract only explicit, reviewable scenario proposals from a question."""
    if not isinstance(question, str) or not question.strip():
        raise ScenarioDraftError("question is required")
    normalized = " ".join(question.casefold().split())
    question_intent = route_question_intent(question)
    facts: list[dict[str, Any]] = []
    assumptions: list[dict[str, Any]] = []
    objectives: list[dict[str, Any]] = []
    confirmation_requests: list[dict[str, Any]] = []
    rejected_values: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    data_gaps: list[dict[str, Any]] = []

    if any(problem.get("code") == _INJECTION_PROBLEM for problem in question_intent["problems"]):
        rejected_values.append({"code": "tool_instruction_not_scenario_input", "message": "Tool instructions are not accepted in a scenario draft."})
    else:
        _extract_retirement_age(normalized, facts, confirmation_requests, rejected_values, conflicts)
        _extract_retirement_date(normalized, facts, rejected_values)
        _extract_budget(normalized, assumptions, rejected_values)
        _extract_children_education(normalized, objectives, confirmation_requests)
        _add_omission_requests(normalized, confirmation_requests, data_gaps)

    status = "ready_for_confirmation"
    if rejected_values or conflicts or not question_intent["selected_intent_ids"]:
        status = "needs_clarification"
    if any(item["code"] == "tool_instruction_not_scenario_input" for item in rejected_values):
        status = "rejected"
    core = {
        "question": {"fingerprint": question_intent["question_fingerprint"], "persisted_verbatim": False},
        "question_intent": {
            "schema_version": question_intent["schema_version"],
            "status": question_intent["status"],
            "content_hash": question_intent["reproducibility"]["content_hash"],
            "selected_intent_ids": question_intent["selected_intent_ids"],
        },
        "proposed_scenario": {
            "scenario_id": f"draft-{question_intent['question_fingerprint'][:12]}",
            "scenario_type": "planning",
            "facts": facts,
            "assumptions": assumptions,
            "objectives": objectives,
            "executable": False,
        },
        "confirmation_requests": _unique_requests(confirmation_requests),
        "rejected_values": rejected_values,
        "conflicts": conflicts,
        "data_gaps": data_gaps,
        "policy": {
            "draft_requires_confirmation": True,
            "draft_is_not_decision_scenario_v2": True,
            "scenario_execution_allowed": False,
            "tax_pension_financial_calculations_performed": False,
            "unsupported_values_are_not_promoted": True,
        },
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "status": status,
        **core,
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": _content_hash(core)},
    }


def _extract_retirement_age(
    normalized: str,
    facts: list[dict[str, Any]],
    requests: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
) -> None:
    ages = [int(value) for value in _AGE_PATTERN.findall(normalized)]
    valid = sorted(set(age for age in ages if 18 <= age <= 100))
    for age in sorted(set(ages) - set(valid)):
        rejected.append({"code": "unsupported_retirement_age", "field": "target_retirement_age", "value": age, "message": "Retirement age must be between 18 and 100."})
    if len(valid) > 1:
        conflicts.append({"code": "conflicting_retirement_ages", "field": "target_retirement_age", "values": valid, "message": "Choose one retirement age before creating a scenario."})
        return
    if len(valid) == 1:
        facts.append(_proposal("assumptions.personal.target_retirement_age", valid[0], "integer"))
        requests.append(_request("confirm_target_retirement_age", "Confirm the proposed retirement age."))


def _extract_retirement_date(normalized: str, facts: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> None:
    for value in _DATE_PATTERN.findall(normalized):
        try:
            date.fromisoformat(value)
        except ValueError:
            rejected.append({"code": "unsupported_date", "field": "target_retirement_date", "value": value, "message": "Use a valid ISO date."})
            continue
        if any(keyword in normalized for keyword in ("pensione", "pension", "ritiro", "retire")):
            facts.append(_proposal("assumptions.personal.target_retirement_date", value, "date"))


def _extract_budget(normalized: str, assumptions: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> None:
    for raw_value in _AMOUNT_PATTERN.findall(normalized):
        canonical = raw_value.replace(",", ".")
        try:
            positive = Decimal(canonical) > 0
        except InvalidOperation:
            positive = False
        if not positive:
            rejected.append({"code": "unsupported_amount", "field": "declared_budget", "value": raw_value, "message": "A declared budget must be positive."})
            continue
        assumptions.append({**_proposal("constraints.declared_budget", canonical, "decimal"), "currency": "EUR"})


def _extract_children_education(normalized: str, objectives: list[dict[str, Any]], requests: list[dict[str, Any]]) -> None:
    if any(phrase in normalized for phrase in ("universita dei figli", "università dei figli", "universita figl", "università figl")):
        objectives.append({"objective_id": "children_university", "status": "proposed", "source": "explicit_user_text", "confirmation_required": True})
        requests.append(_request("confirm_children_university_objective", "Confirm affected children, timing and declared budget."))


def _add_omission_requests(normalized: str, requests: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> None:
    retirement_requested = any(keyword in normalized for keyword in ("pensione", "pension", "ritiro", "retire"))
    has_age = bool(_AGE_PATTERN.search(normalized))
    has_date = bool(_DATE_PATTERN.search(normalized))
    if retirement_requested and not has_age and not has_date:
        requests.append(_request("target_retirement_age_or_date_required", "Provide a target retirement age or ISO date."))
        gaps.append({"code": "missing_target_retirement_timing", "message": "Retirement timing is not explicit in the question."})


def _proposal(path: str, value: Any, value_type: str) -> dict[str, Any]:
    return {"path": path, "value": value, "value_type": value_type, "source": "explicit_user_text", "confirmation_required": True}


def _request(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _unique_requests(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for request in requests:
        if request["code"] not in seen:
            result.append(request)
            seen.add(request["code"])
    return result


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
