"""Non-activating source/version gate for synthetic pension-timeline branches.

This seam selects an exact candidate EU rule pack from externally established
legal timing. It does not assess entitlement or register/activate a consumer.
"""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
RULES_ROOT = REPOSITORY_ROOT / "family-office-rules" / "cross-border"
APPLICATION_DATE = date(2026, 11, 1)

EVENTS = (
    "eligibility_date",
    "requirements_met_date",
    "official_recognition_date",
    "economic_effective_date",
    "first_cash_payment_date",
)
JURISDICTIONS = ("IT", "ES", "EU")

PACK_REGISTRY = {
    "eu.it-es.pension-coordination.2026.v11.1.1": {
        "path": "eu-pension-coordination-it-es-v11.1.1.json",
        "sha256": "1d002510a168ce11c2f508cb9102498b9624ddf9a7a221e24b05843da5a82d66",
        "valid_from": date(2026, 1, 1),
        "valid_to": date(2026, 10, 31),
    },
    "eu.it-es.pension-coordination.2026.v12.1.1": {
        "path": "eu-pension-coordination-it-es-v12.1.1.json",
        "sha256": "05f888e8dd59dc548198ebfd3ccaf84c0d1c79f5c4be85f2b32586150fd7fb0a",
        "valid_from": date(2026, 11, 1),
        "valid_to": date(2026, 12, 31),
    },
}

TRANSITION_CLASSES = {
    "acquired_before_application_date",
    "post_application_contingency",
    "pre_application_contingency_right_acquired_after_date",
}
PRE_APPLICATION_PERIODS = {
    "none",
    "considered_under_article_87b_2",
}


def select_eu_pension_rule_pack(
    *,
    member_state: str | None,
    applicable_date: str | None,
    right_acquisition_date: str | None,
    contingency_date: str | None,
    transition_classification: str | None,
    pre_application_periods: str | None,
    rules_root: Path | None = None,
) -> dict[str, Any]:
    """Select an exact candidate pack or return ``not_assessed`` with gaps.

    Dates/classification must come from independently established evidence.
    No latest-version fallback, rule activation, or benefit inference occurs.
    """
    required = {
        "member_state": member_state,
        "applicable_date": applicable_date,
        "right_acquisition_date": right_acquisition_date,
        "contingency_date": contingency_date,
        "transition_classification": transition_classification,
        "pre_application_periods": pre_application_periods,
    }
    missing = [name for name, value in required.items() if value is None or value == ""]
    if missing:
        return _selection_gap(
            "legal_applicability_unknown",
            "Required legal timing/classification is missing: " + ", ".join(missing),
        )

    if member_state not in {"IT", "ES"}:
        return _selection_gap("legal_applicability_unknown", "Member State is outside the supported IT/ES scope.")
    if transition_classification not in TRANSITION_CLASSES:
        return _selection_gap("transitional_branch_unknown", "Transition classification is unsupported or ambiguous.")
    if pre_application_periods not in PRE_APPLICATION_PERIODS:
        return _selection_gap("transitional_branch_unknown", "Pre-application period treatment is unsupported or ambiguous.")

    try:
        application = _parse_date(applicable_date)
        acquired = _parse_date(right_acquisition_date)
        contingency = _parse_date(contingency_date)
    except (TypeError, ValueError):
        return _selection_gap("legal_applicability_unknown", "A required legal date is invalid.")

    if application != APPLICATION_DATE:
        return _selection_gap("legal_applicability_unknown", "No reviewed candidate covers the supplied application date.")

    if acquired < application:
        expected_class = "acquired_before_application_date"
        pack_id = "eu.it-es.pension-coordination.2026.v11.1.1"
        if contingency >= application:
            return _selection_gap("transitional_branch_unknown", "A pre-application right classification conflicts with a post-application contingency.")
    elif contingency < application:
        expected_class = "pre_application_contingency_right_acquired_after_date"
        pack_id = "eu.it-es.pension-coordination.2026.v12.1.1"
        if pre_application_periods != "considered_under_article_87b_2":
            return _selection_gap("transitional_branch_unknown", "Article 87b(2) period treatment is not confirmed.")
    else:
        expected_class = "post_application_contingency"
        pack_id = "eu.it-es.pension-coordination.2026.v12.1.1"

    if transition_classification != expected_class:
        return _selection_gap("transitional_branch_unknown", "Transition classification conflicts with the supplied dates.")

    spec = PACK_REGISTRY[pack_id]
    if acquired < spec["valid_from"] or acquired > spec["valid_to"]:
        return _selection_gap("source_version_missing", "No candidate pack covers the supplied right-acquisition date.")
    pack_path = (rules_root or RULES_ROOT) / spec["path"]
    try:
        payload = pack_path.read_bytes()
        actual_digest = hashlib.sha256(payload).hexdigest()
        pack = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _selection_gap("source_version_missing", "The exact candidate pack is unavailable or unreadable.")
    if actual_digest != spec["sha256"] or pack.get("rule_pack_id") != pack_id:
        return _selection_gap("source_version_missing", "Candidate pack identity or digest does not match the pinned registry.")
    if pack.get("valid_from") != spec["valid_from"].isoformat() or pack.get("valid_to") != spec["valid_to"].isoformat():
        return _selection_gap("legal_applicability_unknown", "Candidate pack period does not match the pinned interval.")

    return {
        "status": "candidate_selected",
        "rule_pack_id": pack_id,
        "digest_sha256": actual_digest,
        "transition_classification": expected_class,
        "activation_allowed": False,
        "human_review_required": True,
        "data_gaps": [],
    }


def evaluate_pension_timeline_source_branch(
    *, event: str, jurisdiction: str, rule_selection: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Expose one fail-closed event/jurisdiction branch for synthetic checks."""
    if event not in EVENTS:
        raise ValueError(f"Unsupported timeline event: {event}")
    if jurisdiction not in JURISDICTIONS:
        raise ValueError(f"Unsupported jurisdiction: {jurisdiction}")

    code = "event_evidence_missing"
    if jurisdiction == "EU":
        selection_id = None if rule_selection is None else rule_selection.get("rule_pack_id")
        valid_selection = (
            rule_selection is not None
            and rule_selection.get("status") == "candidate_selected"
            and isinstance(selection_id, str)
            and selection_id in PACK_REGISTRY
            and rule_selection.get("digest_sha256") == PACK_REGISTRY[selection_id]["sha256"]
        )
        if not valid_selection:
            code = "source_version_missing"
    return {
        "event": event,
        "jurisdiction": jurisdiction,
        "status": "not_assessed",
        "date": None,
        "payer": None,
        "amount": None,
        "human_review_required": True,
        "data_gaps": [{
            "code": code,
            "message": f"{event} for {jurisdiction} lacks approved event-specific evidence.",
            "severity": "blocking",
        }],
    }


def _parse_date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Date must use ISO YYYY-MM-DD form")
    return parsed


def _selection_gap(code: str, message: str) -> dict[str, Any]:
    return {
        "status": "not_assessed",
        "rule_pack_id": None,
        "digest_sha256": None,
        "transition_classification": None,
        "activation_allowed": False,
        "human_review_required": True,
        "data_gaps": [{"code": code, "message": message, "severity": "blocking"}],
    }
