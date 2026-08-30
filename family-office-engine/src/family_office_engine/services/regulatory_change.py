"""Deterministic governance workflow for versioned regulatory changes.

This module records evidence and gates a change; it never interprets a rule or
downloads a source.  Knowledge and rule-pack changes remain a separate review.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse


class RegulatoryChangeError(ValueError):
    """Raised for invalid or unsafe regulatory change proposals."""


SCHEMA_VERSION = "regulatory-change/v1"
AUTHORITATIVE_AUTHORITIES = {"official", "institutional"}
ALLOWED_AUTHORITIES = AUTHORITATIVE_AUTHORITIES | {"professional", "user_declared", "unknown"}


def _iso(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise RegulatoryChangeError(f"{field} must be an ISO date")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise RegulatoryChangeError(f"{field} must be an ISO date") from exc
    return value


def _workspace_path(path: Path, workspace: Path) -> Path:
    resolved = path.resolve()
    root = workspace.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RegulatoryChangeError("output must remain inside the workspace") from exc
    return resolved


def _source_status(source: Mapping[str, Any]) -> tuple[str, list[dict[str, str]]]:
    authority = source.get("authority")
    url = source.get("url")
    gaps: list[dict[str, str]] = []
    parsed = urlparse(url) if isinstance(url, str) else None
    if authority not in ALLOWED_AUTHORITIES:
        raise RegulatoryChangeError("source authority is not supported")
    if not parsed or parsed.scheme != "https" or not parsed.netloc:
        gaps.append({"code": "source_not_verifiable", "message": "source must provide an HTTPS URL"})
    if authority not in AUTHORITATIVE_AUTHORITIES:
        gaps.append({"code": "source_not_authoritative", "message": "source requires authoritative verification"})
    return ("verified" if not gaps else "needs_review", gaps)


def build_regulatory_change(input_data: Mapping[str, Any], *, as_of_date: str | None = None) -> dict[str, Any]:
    required = ("change_id", "summary", "source", "jurisdiction", "valid_from", "affected_rule_packs", "required_tests", "rollback_strategy")
    missing = [field for field in required if field not in input_data]
    if missing:
        raise RegulatoryChangeError(f"missing fields: {', '.join(missing)}")
    change_id = input_data["change_id"]
    if not isinstance(change_id, str) or not change_id.strip():
        raise RegulatoryChangeError("change_id must be a non-empty string")
    valid_from = _iso(input_data["valid_from"], "valid_from")
    valid_to = _iso(input_data["valid_to"], "valid_to") if input_data.get("valid_to") else None
    if valid_to and valid_to < valid_from:
        raise RegulatoryChangeError("valid_to must not precede valid_from")
    if not isinstance(input_data["source"], Mapping):
        raise RegulatoryChangeError("source must be an object")
    source_status, gaps = _source_status(input_data["source"])
    observed = _iso(as_of_date or date.today().isoformat(), "as_of_date")
    retroactive = valid_from < observed
    affected = input_data["affected_rule_packs"]
    tests = input_data["required_tests"]
    if not isinstance(affected, list) or not all(isinstance(item, str) and item for item in affected):
        raise RegulatoryChangeError("affected_rule_packs must be a list of names")
    if not isinstance(tests, list) or not all(isinstance(item, str) and item for item in tests):
        raise RegulatoryChangeError("required_tests must be a list of names")
    findings = list(gaps)
    if retroactive:
        findings.append({"code": "retroactive_validity", "message": "valid_from precedes the observation date and requires explicit review"})
    if not affected:
        findings.append({"code": "missing_impact_scope", "message": "at least one affected rule pack must be named"})
    if not tests:
        findings.append({"code": "missing_regression_tests", "message": "at least one synthetic regression test is required"})
    return {
        "schema_version": SCHEMA_VERSION,
        "change_id": change_id,
        "status": "proposed",
        "observed_on": observed,
        "summary": input_data["summary"],
        "source": {**dict(input_data["source"]), "verification_status": source_status},
        "jurisdiction": input_data["jurisdiction"],
        "validity": {"from": valid_from, "to": valid_to, "retroactive": retroactive},
        "impact_assessment": {"affected_rule_packs": affected, "required_tests": tests, "findings": findings},
        "release_checklist": {"knowledge_updated": False, "rule_pack_versioned": False, "tests_passed": False, "human_approved": False},
        "approval": None,
        "rollback": {"strategy": input_data["rollback_strategy"], "status": "available"},
        "data_gaps": gaps,
    }


def write_regulatory_change(proposal: Mapping[str, Any], output: Path, workspace: Path) -> dict[str, Any]:
    destination = _workspace_path(output, workspace)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(proposal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return dict(proposal, path=str(destination))


def approve_regulatory_change(path: Path, workspace: Path, approver: str, *, tests_passed: bool, knowledge_updated: bool = False, rule_pack_versioned: bool = False, test_evidence: str = "") -> dict[str, Any]:
    destination = _workspace_path(path, workspace)
    proposal = json.loads(destination.read_text(encoding="utf-8"))
    if proposal.get("schema_version") != SCHEMA_VERSION:
        raise RegulatoryChangeError("unsupported regulatory change schema")
    if not approver.strip():
        raise RegulatoryChangeError("approver is required")
    if proposal.get("source", {}).get("verification_status") != "verified" or proposal.get("impact_assessment", {}).get("findings"):
        raise RegulatoryChangeError("proposal has unresolved source or impact findings")
    if not tests_passed:
        raise RegulatoryChangeError("approval requires passing required tests")
    if not knowledge_updated or not rule_pack_versioned:
        raise RegulatoryChangeError("approval requires completed knowledge and rule-pack checklist")
    if not isinstance(test_evidence, str) or not test_evidence.strip():
        raise RegulatoryChangeError("approval requires named test evidence")
    proposal["status"] = "approved"
    proposal["approval"] = {"approver": approver, "approved_on": date.today().isoformat()}
    proposal["approval"]["test_evidence"] = test_evidence.strip()
    proposal["release_checklist"].update({"knowledge_updated": True, "rule_pack_versioned": True, "tests_passed": True, "human_approved": True})
    return write_regulatory_change(proposal, destination, workspace)


def rollback_regulatory_change(path: Path, workspace: Path, reason: str) -> dict[str, Any]:
    destination = _workspace_path(path, workspace)
    proposal = json.loads(destination.read_text(encoding="utf-8"))
    if proposal.get("status") != "approved":
        raise RegulatoryChangeError("only an approved proposal can be rolled back")
    if not reason.strip():
        raise RegulatoryChangeError("rollback reason is required")
    proposal["status"] = "rolled_back"
    proposal["rollback"].update({"status": "executed", "reason": reason, "executed_on": date.today().isoformat()})
    return write_regulatory_change(proposal, destination, workspace)
