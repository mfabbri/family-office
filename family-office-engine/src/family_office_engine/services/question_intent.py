"""Deterministic V5.4 question routing; it never invokes planning tools."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from family_office_engine.services.supported_question_catalog import assess_question_capability, build_supported_question_catalog

SCHEMA_VERSION = "question-intent/v1"
RECORD_TYPE = "QuestionIntent"

KEYWORDS = {
    "knowledge_and_sources": ("fonte", "fonti", "norma", "normative", "citazione", "citation"),
    "compliance_and_guardrails": ("aml", "crs", "antiriciclaggio", "compliance", "anonimato"),
    "liquidity_and_cashflow": ("liquidita", "liquidità", "cash flow", "riserva", "emergenza"),
    "retirement_and_work_exit": ("pensione", "pension", "ritiro", "smettere di lavorare", "part-time"),
    "cross_border_tax_and_reporting": ("spagna", "spain", "rw", "ivafe", "ivie", "residenza fiscale"),
    "portfolio_and_contributions": ("portafoglio", "etf", "investimenti", "contributo", "previdenza complementare"),
    "wealth_protection_and_estate": ("successione", "testamento", "polizza", "protezione", "patrimonio"),
    "real_estate_hold_rent_sell": ("vendere casa", "affitto", "tenere immobile", "hold", "rent", "sell"),
    "investment_opportunity": ("camper", "immobile a reddito", "appartamento a reddito", "noleggio", "opportunita di investimento", "opportunità di investimento"),
}
INJECTION_MARKERS = ("ignore previous", "ignore le istruzioni", "system prompt", "prompt injection", "bypass", "invoca il tool", "execute tool")


class QuestionIntentError(ValueError):
    pass


def build_question_intent(question: str, output_path: Path, *, provided_data: list[str] | None = None) -> dict[str, Any]:
    result = route_question_intent(question, provided_data=provided_data)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise QuestionIntentError(f"Cannot write question intent: {output_path}") from exc
    return result


def route_question_intent(question: str, *, provided_data: list[str] | None = None) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise QuestionIntentError("question is required")
    if provided_data is not None and (not isinstance(provided_data, list) or not all(isinstance(item, str) and item.strip() for item in provided_data)):
        raise QuestionIntentError("provided_data must be a list of non-empty strings")
    normalized = _normalize(question)
    catalog = build_supported_question_catalog()
    problems: list[dict[str, Any]] = []
    if any(marker in normalized for marker in INJECTION_MARKERS):
        problems.append({"code": "prompt_injection_or_tool_instruction", "severity": "blocking", "message": "Tool instructions in user text are not executable."})
        selected: list[str] = []
        candidates: list[dict[str, Any]] = []
    else:
        matches = {intent_id: sum(1 for keyword in keywords if keyword in normalized) for intent_id, keywords in KEYWORDS.items()}
        matches = {intent_id: count for intent_id, count in matches.items() if count}
        candidates = _candidates(matches)
        selected = [item["intent_id"] for item in candidates if item["confidence"] != "low"]
        if not selected:
            problems.append({"code": "question_unsupported", "severity": "blocking", "message": "No supported deterministic intent matched the question."})
    assessment = assess_question_capability(selected, provided_data) if selected else None
    if assessment is not None:
        problems.extend(assessment["problems"])
    entities = _entities(normalized)
    status = "routed" if selected and not any(item["severity"] == "blocking" for item in problems) else "needs_clarification"
    core = {
        "question_fingerprint": _fingerprint(normalized),
        "intent_candidates": candidates,
        "selected_intent_ids": selected,
        "proposed_entities": entities,
        "provided_data": sorted(set(provided_data or [])),
        "missing_data": [] if assessment is None else sorted({item for result in assessment["intent_results"] for item in result["missing_data"]}),
        "problems": problems,
        "tool_invocations": [],
        "data_gaps": [item for item in problems if item["code"] == "minimum_data_missing"],
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "status": status,
        **core,
        "policy": {"tool_invocation_allowed": False, "facts_written_to_workspace": False, "entities_are_proposals": True},
        "catalog": {"schema_version": catalog["schema_version"], "content_hash": catalog["reproducibility"]["content_hash"]},
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": _fingerprint(json.dumps(core, sort_keys=True, separators=(",", ":")))},
    }


def _candidates(matches: dict[str, int]) -> list[dict[str, Any]]:
    maximum = max(matches.values(), default=0)
    return [
        {"intent_id": intent_id, "match_count": count, "confidence": "high" if count == maximum and count >= 2 else "medium"}
        for intent_id, count in sorted(matches.items(), key=lambda item: (-item[1], item[0]))
    ]


def _entities(normalized: str) -> list[dict[str, Any]]:
    entities = []
    for country, aliases in {"IT": ("italia", "italy"), "ES": ("spagna", "spain")}.items():
        if any(alias in normalized for alias in aliases):
            entities.append({"type": "country", "value": country, "confidence": "high"})
    for asset, aliases in {"income_property": ("immobile a reddito", "appartamento a reddito"), "camper": ("camper",)}.items():
        if any(alias in normalized for alias in aliases):
            entities.append({"type": "asset_type", "value": asset, "confidence": "high"})
    for age in re.findall(r"\b(\d{2})\s*anni\b", normalized):
        entities.append({"type": "age_years", "value": age, "confidence": "medium"})
    return entities


def _normalize(question: str) -> str:
    return " ".join(question.casefold().split())


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
