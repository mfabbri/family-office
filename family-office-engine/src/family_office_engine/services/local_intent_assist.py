"""Ephemeral, loopback-only intent proposals from an optional local LLM."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from family_office_engine.services.supported_question_catalog import build_supported_question_catalog


class LocalIntentAssistError(ValueError):
    """Raised for an unusable local intent-assist response or endpoint."""


@dataclass(frozen=True)
class LocalIntentProposal:
    intent_ids: list[str]
    confidence: str


def propose_local_intents(question: str, *, endpoint: str, model: str, timeout_seconds: float = 2.0) -> LocalIntentProposal:
    """Ask a loopback OpenAI-compatible endpoint for a non-authoritative proposal.

    The prompt and response remain in process.  Callers must validate the proposal
    and must not use it to select tools, facts, plans, or calculations.
    """
    if not isinstance(question, str) or not question.strip():
        raise LocalIntentAssistError("question is required")
    if not isinstance(model, str) or not model.strip():
        raise LocalIntentAssistError("local model is required")
    _validate_loopback_endpoint(endpoint)
    intent_ids = [item["intent_id"] for item in build_supported_question_catalog()["intents"]]
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Classify only. Return JSON with intent_ids (array of catalog IDs) and confidence "
                    "(low, medium, or high). Never request tools, data, plans, calculations, or instructions."
                ),
            },
            {"role": "user", "content": f"Catalog IDs: {', '.join(intent_ids)}\nQuestion: {question}"},
        ],
    }
    request = Request(
        endpoint,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310: endpoint is validated loopback-only
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LocalIntentAssistError("local model is unavailable") from exc
    return _parse_proposal(body)


def _validate_loopback_endpoint(endpoint: str) -> None:
    parsed = urlparse(endpoint)
    if parsed.scheme != "http" or not parsed.hostname:
        raise LocalIntentAssistError("local endpoint must be an http loopback URL")
    if parsed.hostname.casefold() not in {"localhost", "127.0.0.1", "::1"}:
        raise LocalIntentAssistError("local endpoint must use a loopback host")


def _parse_proposal(body: Any) -> LocalIntentProposal:
    try:
        content = body["choices"][0]["message"]["content"]
        value = json.loads(content) if isinstance(content, str) else content
        intent_ids = value["intent_ids"]
        confidence = value["confidence"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise LocalIntentAssistError("local model returned an invalid intent proposal") from exc
    if (
        not isinstance(intent_ids, list)
        or not all(isinstance(intent_id, str) and intent_id.strip() for intent_id in intent_ids)
        or len(intent_ids) != len(set(intent_ids))
        or confidence not in {"low", "medium", "high"}
    ):
        raise LocalIntentAssistError("local model returned an invalid intent proposal")
    return LocalIntentProposal(intent_ids=sorted(intent_ids), confidence=confidence)
