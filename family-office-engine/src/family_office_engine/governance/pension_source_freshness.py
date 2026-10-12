"""Deterministic freshness gates for the active V4.14 pension rule packs.

This module checks only declared provenance/review metadata. It does not fetch
sources, infer legal validity, or certify that a human review was substantive.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


MAX_REVIEW_INTERVAL_DAYS = 90
ACTIVE_PENSION_RULE_PACKS = (
    Path("italy/2026/inps-theoretical-pension.json"),
    Path("italy/2026/inps-old-age-eligibility.json"),
    Path("spain/statutory-retirement-general.json"),
    Path("cross-border/eu-pension-coordination-it-es.json"),
    Path("cross-border/spanish-eu-theoretical-pension.json"),
)
OFFICIAL_SOURCE_HOSTS = {
    "boe.es",
    "eur-lex.europa.eu",
    "inps.it",
    "lavoro.gov.it",
    "seg-social.es",
}


class PensionSourceFreshnessError(ValueError):
    """Raised when a pension rule pack cannot pass its freshness gate."""


def audit_active_pension_rule_packs(
    rules_root: Path,
    as_of_date: str | date,
    rule_pack_paths: Iterable[Path] = ACTIVE_PENSION_RULE_PACKS,
) -> dict[str, Any]:
    as_of = _parse_date(as_of_date, "as_of_date")
    packs = [audit_pension_rule_pack(rules_root / relative, as_of) for relative in rule_pack_paths]
    gaps = [gap for pack in packs for gap in pack["data_gaps"]]
    return {
        "schema_version": "pension-source-freshness-report/v1",
        "record_type": "PensionSourceFreshnessReport",
        "status": "fresh" if not gaps else "blocked",
        "as_of_date": as_of.isoformat(),
        "max_review_interval_days": MAX_REVIEW_INTERVAL_DAYS,
        "network_checked": False,
        "rule_packs": packs,
        "data_gaps": gaps,
        "limitations": [
            "The audit validates declared provenance and review dates only; it does not fetch official sources.",
            "A fresh review date is not proof that a human review was correctly performed.",
            "Rule-pack/legal valid_from and valid_to are reported separately from review freshness.",
        ],
    }


def audit_pension_rule_pack(rule_pack_path: Path, as_of_date: str | date) -> dict[str, Any]:
    as_of = _parse_date(as_of_date, "as_of_date")
    gaps: list[dict[str, Any]] = []
    try:
        pack = json.loads(rule_pack_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _blocked_pack(rule_pack_path, as_of, [
            _gap("normative_source_provenance_missing", "Rule pack is missing or is not valid JSON.")
        ])
    if not isinstance(pack, dict):
        return _blocked_pack(rule_pack_path, as_of, [
            _gap("normative_source_provenance_missing", "Rule pack root must be an object.")
        ])

    source_refs = pack.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs:
        gaps.append(_gap("normative_source_provenance_missing", "Active rule pack must declare source_refs."))
        source_refs = []

    source_results = []
    for index, source in enumerate(source_refs):
        source_gaps = _audit_source(source, index, as_of)
        gaps.extend(source_gaps)
        source_results.append({
            "source_id": source.get("source_id") if isinstance(source, dict) else None,
            "reviewed_on": source.get("reviewed_on") if isinstance(source, dict) else None,
            "next_review_due": source.get("next_review_due") if isinstance(source, dict) else None,
            "status": "fresh" if not source_gaps else "blocked",
            "data_gaps": source_gaps,
        })

    return {
        "path": rule_pack_path.as_posix(),
        "rule_pack_id": pack.get("rule_pack_id"),
        "schema_version": pack.get("schema_version"),
        "jurisdiction": pack.get("jurisdiction", pack.get("jurisdictions")),
        "legal_validity": {"valid_from": pack.get("valid_from"), "valid_to": pack.get("valid_to")},
        "status": "fresh" if not gaps else "blocked",
        "source_count": len(source_results),
        "sources": source_results,
        "data_gaps": gaps,
        "as_of_date": as_of.isoformat(),
    }


def require_fresh_pension_rule_pack(rule_pack_path: Path, as_of_date: str | date | None = None) -> dict[str, Any]:
    report = audit_pension_rule_pack(
        rule_pack_path,
        date.today() if as_of_date is None else as_of_date,
    )
    if report["status"] != "fresh":
        codes = sorted({gap["code"] for gap in report["data_gaps"]})
        raise PensionSourceFreshnessError(
            f"Pension rule pack is blocked by source freshness/provenance: {', '.join(codes)}"
        )
    return report


def record_pension_source_review(
    rule_pack_path: Path,
    source_id: str,
    reviewed_on: str | date,
) -> dict[str, str]:
    """Record an operator-confirmed review; this function never fetches sources."""
    reviewed = _parse_date(reviewed_on, "reviewed_on")
    if reviewed > date.today():
        raise PensionSourceFreshnessError("reviewed_on cannot be in the future")
    try:
        pack = json.loads(rule_pack_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PensionSourceFreshnessError(f"Cannot read pension rule pack: {rule_pack_path}") from exc
    refs = pack.get("source_refs") if isinstance(pack, dict) else None
    if not isinstance(refs, list):
        raise PensionSourceFreshnessError("Pension rule pack has no source_refs array")
    matches = [ref for ref in refs if isinstance(ref, dict) and ref.get("source_id") == source_id]
    if len(matches) != 1:
        raise PensionSourceFreshnessError(f"Expected exactly one source_id {source_id!r} in the rule pack")
    source = matches[0]
    if not all(_non_empty_string(source.get(field)) for field in ("title", "authority", "jurisdiction", "url")):
        raise PensionSourceFreshnessError("Cannot record review while source provenance is incomplete")
    if not isinstance(source.get("provisions"), list) or not source["provisions"]:
        raise PensionSourceFreshnessError("Cannot record review without declared provisions/source subject")
    parsed_url = urlparse(source["url"])
    source_host = parsed_url.hostname.lower() if parsed_url.hostname else ""
    if parsed_url.scheme != "https" or not _is_official_host(source_host):
        raise PensionSourceFreshnessError("Cannot record review for a non-official HTTPS source")
    retrieved = _parse_date(source.get("retrieved_on"), "retrieved_on")
    if retrieved > reviewed:
        raise PensionSourceFreshnessError("reviewed_on cannot precede retrieved_on")
    due = reviewed + timedelta(days=MAX_REVIEW_INTERVAL_DAYS)
    source["reviewed_on"] = reviewed.isoformat()
    source["next_review_due"] = due.isoformat()
    temporary = rule_pack_path.with_name(f"{rule_pack_path.name}.review.tmp")
    try:
        temporary.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(rule_pack_path)
    except OSError as exc:
        raise PensionSourceFreshnessError(f"Cannot write reviewed pension rule pack: {rule_pack_path}") from exc
    return {"source_id": source_id, "reviewed_on": reviewed.isoformat(), "next_review_due": due.isoformat()}


def _audit_source(source: Any, index: int, as_of: date) -> list[dict[str, Any]]:
    if not isinstance(source, dict):
        return [_gap("normative_source_provenance_missing", f"source_refs[{index}] must be an object.")]
    label = str(source.get("source_id") or f"source_refs[{index}]")
    required_text = ("source_id", "title", "authority", "jurisdiction")
    missing = [field for field in required_text if not _non_empty_string(source.get(field))]
    if missing:
        return [_gap(
            "normative_source_provenance_missing",
            f"{label} is missing required provenance: {', '.join(missing)}.",
            source_id=label,
        )]

    gaps: list[dict[str, Any]] = []
    url = source.get("url")
    parsed = urlparse(url) if isinstance(url, str) else None
    host = parsed.hostname.lower() if parsed and parsed.hostname else ""
    if not parsed or parsed.scheme != "https" or not _is_official_host(host):
        gaps.append(_gap(
            "normative_source_provenance_missing",
            f"{label} must link to an official HTTPS source.",
            source_id=label,
        ))
    provisions = source.get("provisions")
    if not isinstance(provisions, list) or not provisions or any(not _non_empty_string(item) for item in provisions):
        gaps.append(_gap(
            "normative_source_provenance_missing",
            f"{label} must identify at least one legal provision or source subject.",
            source_id=label,
        ))

    parsed_dates: dict[str, date] = {}
    for field in ("retrieved_on", "reviewed_on", "next_review_due"):
        try:
            parsed_dates[field] = _parse_date(source.get(field), field)
        except ValueError:
            gaps.append(_gap(
                "normative_source_provenance_missing" if field == "retrieved_on" else "normative_source_review_metadata_invalid",
                f"{label} has missing or invalid {field} (expected ISO date).",
                source_id=label,
                field=field,
            ))
    if len(parsed_dates) != 3:
        return gaps

    retrieved = parsed_dates["retrieved_on"]
    reviewed = parsed_dates["reviewed_on"]
    due = parsed_dates["next_review_due"]
    if reviewed > as_of or due <= reviewed or retrieved > reviewed:
        gaps.append(_gap(
            "normative_source_review_metadata_invalid",
            f"{label} has inconsistent retrieval/review dates or a review date in the future.",
            source_id=label,
        ))
    if due - reviewed > timedelta(days=MAX_REVIEW_INTERVAL_DAYS):
        gaps.append(_gap(
            "normative_source_review_metadata_invalid",
            f"{label} next_review_due exceeds the {MAX_REVIEW_INTERVAL_DAYS}-day review interval.",
            source_id=label,
        ))
    if as_of > due:
        gaps.append(_gap(
            "normative_source_review_overdue",
            f"{label} requires human review; next_review_due was {due.isoformat()}.",
            source_id=label,
            next_review_due=due.isoformat(),
        ))
    return gaps


def _is_official_host(host: str) -> bool:
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in OFFICIAL_SOURCE_HOSTS)


def _parse_date(value: Any, field: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must use canonical ISO date format")
    return parsed


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _gap(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def _blocked_pack(rule_pack_path: Path, as_of: date, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "path": rule_pack_path.as_posix(),
        "rule_pack_id": None,
        "schema_version": None,
        "jurisdiction": None,
        "legal_validity": {"valid_from": None, "valid_to": None},
        "status": "blocked",
        "source_count": 0,
        "sources": [],
        "data_gaps": gaps,
        "as_of_date": as_of.isoformat(),
    }
