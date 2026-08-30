"""Deterministic data-quality checks for workspace-local document inventories."""

import json
import os
import re
from collections import Counter
from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Any

INPUT_SCHEMA_VERSION = "data-quality-input/v1"
POLICY_SCHEMA_VERSION = "data-quality-policy/v1"
REPORT_SCHEMA_VERSION = "data-quality-report/v1"
_MONTH_PATTERN = re.compile(r"(?<!\d)(\d{4})[-_]?([01]\d)(?!\d)")


class DocumentDataQualityError(ValueError):
    pass


def build_workspace_document_data_quality(
    workspace_root: Path,
    output_path: Path | None = None,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Build a report from workspace defaults, without requiring an input JSON file."""
    workspace = _workspace(workspace_root)
    inventory_path = workspace / "snapshots" / "document-inventory.snapshot.json"
    output = (output_path or workspace / "snapshots" / "data-quality.report.json").resolve()
    _require_within(workspace, inventory_path.resolve(), "inventory")
    _require_within(workspace, output, "output")
    if not inventory_path.is_file():
        raise DocumentDataQualityError("document inventory is missing; run 'fo documents inventory' first")
    inventory = _read_json(inventory_path, "document inventory")
    if inventory.get("schema_version") != "document-inventory/v1" or not isinstance(inventory.get("documents"), list):
        raise DocumentDataQualityError("document inventory must be document-inventory/v1 with documents")
    report_date = date.today() if as_of_date is None else _date(as_of_date, "as_of_date")
    policy = _read_policy(_policy_path(workspace))
    return _build_report(
        workspace, inventory_path, output, report_date, inventory["documents"],
        policy["expected_periods"], policy["declared_totals"],
    )


def setup_workspace_document_data_quality(
    workspace_root: Path,
    as_of_date: str,
    ask: Any,
) -> dict[str, Any]:
    """Ask only for monthly coverage that cannot be inferred from the inventory."""
    workspace = _workspace(workspace_root)
    inventory_path = workspace / "snapshots" / "document-inventory.snapshot.json"
    if not inventory_path.is_file():
        raise DocumentDataQualityError("document inventory is missing; run 'fo documents inventory' first")
    inventory = _read_json(inventory_path, "document inventory")
    if inventory.get("schema_version") != "document-inventory/v1" or not isinstance(inventory.get("documents"), list):
        raise DocumentDataQualityError("document inventory must be document-inventory/v1 with documents")
    report_date = _date(as_of_date, "as_of_date")
    documents = [_document(document) for document in inventory["documents"]]
    existing = _read_policy(_policy_path(workspace))
    policies = {item["category"]: item for item in existing["expected_periods"]}
    excluded = set(existing["excluded_categories"])
    for category, months in _observed_months(documents).items():
        if category in policies or category in excluded:
            continue
        first, last = min(months), max(months)
        answer = ask(f"Monitor monthly coverage for {category} ({first} to {last})? [y/N]: ").strip().lower()
        if answer not in {"y", "yes", "s", "si", "sì"}:
            excluded.add(category)
            _write_policy(workspace, policies, excluded, existing["declared_totals"])
            continue
        start = ask(f"First expected month for {category} [{first}]: ").strip() or first
        default_end = report_date.strftime("%Y-%m")
        end = ask(f"Last expected month for {category} [{default_end}]: ").strip() or default_end
        _month(start, "start_month"); _month(end, "end_month")
        if start > end:
            raise DocumentDataQualityError("expected period start_month must not follow end_month")
        policies[category] = {"category": category, "start_month": start, "end_month": end}
        excluded.discard(category)
        _write_policy(workspace, policies, excluded, existing["declared_totals"])
    return _write_policy(workspace, policies, excluded, existing["declared_totals"])


def build_document_data_quality(
    input_path: Path, output_path: Path, workspace_root: Path
) -> dict[str, Any]:
    workspace = _workspace(workspace_root)
    _require_within(workspace, input_path.resolve(), "input")
    _require_within(workspace, output_path.resolve(), "output")
    declaration = _read_json(input_path, "quality input")
    if declaration.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise DocumentDataQualityError(f"quality input schema_version must be {INPUT_SCHEMA_VERSION}")

    inventory_path = _workspace_path(workspace, declaration.get("inventory_path"), "inventory_path")
    inventory = _read_json(inventory_path, "document inventory")
    if inventory.get("schema_version") != "document-inventory/v1" or not isinstance(inventory.get("documents"), list):
        raise DocumentDataQualityError("document inventory must be document-inventory/v1 with documents")
    as_of_date = _date(declaration.get("as_of_date"), "as_of_date")
    return _build_report(
        workspace, inventory_path, output_path, as_of_date, inventory["documents"],
        declaration.get("expected_periods", []), declaration.get("declared_totals", []),
    )


def _build_report(
    workspace: Path, inventory_path: Path, output_path: Path, report_date: date,
    raw_documents: list[Any], expected_periods: Any, declared_totals: Any,
) -> dict[str, Any]:
    documents = [_document(document) for document in raw_documents]
    findings = _duplicate_findings(documents)
    findings.extend(_uncategorized_findings(documents))
    findings.extend(_missing_month_findings(documents, expected_periods))
    findings.extend(_declared_total_findings(documents, declared_totals))
    findings.sort(key=lambda item: (item["code"], item.get("category", ""), item.get("month", "")))
    configured = {policy["category"] for policy in expected_periods if isinstance(policy, dict) and isinstance(policy.get("category"), str)}
    configured.update(_read_policy(_policy_path(workspace))["excluded_categories"])
    data_gaps = [
        {"code": "monthly_expectation_not_configured", "category": category, "observed_from": min(months), "observed_to": max(months), "action": "Run 'fo pipeline quality setup' to choose whether this category requires monthly coverage."}
        for category, months in sorted(_observed_months(documents).items()) if category not in configured
    ]
    status = "needs_remediation" if findings else ("needs_configuration" if data_gaps else "ready")
    report = {
        "schema_version": REPORT_SCHEMA_VERSION, "record_type": "DocumentDataQualityReport", "status": status,
        "as_of_date": report_date.isoformat(), "inventory_path": _relative(workspace, inventory_path),
        "summary": {"document_count": len(documents), "finding_count": len(findings), "data_gap_count": len(data_gaps), "findings_by_code": dict(sorted(Counter(item["code"] for item in findings).items()))},
        "findings": findings, "data_gaps": data_gaps, "remediation_queue": [_remediation(finding) for finding in findings],
    }
    _write_atomic(output_path, report)
    return report


def _observed_months(documents: list[dict[str, Any]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for document in documents:
        month = _document_month(document)
        if month is not None:
            result.setdefault(document["category"], set()).add(month)
    return result


def _policy_path(workspace: Path) -> Path:
    return workspace / "snapshots" / "data-quality.policy.json"


def _read_policy(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"expected_periods": [], "excluded_categories": [], "declared_totals": []}
    policy = _read_json(path, "data quality policy")
    if policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise DocumentDataQualityError(f"data quality policy schema_version must be {POLICY_SCHEMA_VERSION}")
    expected, excluded, totals = policy.get("expected_periods", []), policy.get("excluded_categories", []), policy.get("declared_totals", [])
    if not isinstance(expected, list) or not isinstance(excluded, list) or not isinstance(totals, list) or not all(isinstance(category, str) for category in excluded):
        raise DocumentDataQualityError("data quality policy requires expected_periods, excluded_categories and declared_totals lists")
    return {"expected_periods": expected, "excluded_categories": excluded, "declared_totals": totals}


def _write_policy(workspace: Path, policies: dict[str, dict[str, Any]], excluded: set[str], totals: list[Any]) -> dict[str, Any]:
    policy = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "record_type": "DocumentDataQualityPolicy",
        "expected_periods": [policies[key] for key in sorted(policies)],
        "excluded_categories": sorted(excluded),
        "declared_totals": totals,
    }
    _write_atomic(_policy_path(workspace), policy)
    return policy


def _document(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DocumentDataQualityError("inventory document must be an object")
    category, relative_path, digest, size = raw.get("category"), raw.get("relative_path"), raw.get("sha256"), raw.get("size_bytes")
    if not isinstance(category, str) or not category:
        raise DocumentDataQualityError("inventory document category is required")
    if not isinstance(relative_path, str) or not relative_path or Path(relative_path).is_absolute() or PureWindowsPath(relative_path).is_absolute():
        raise DocumentDataQualityError("inventory document relative_path must be relative")
    if not isinstance(digest, str) or len(digest) != 64:
        raise DocumentDataQualityError("inventory document sha256 is required")
    if not isinstance(size, int) or size < 0:
        raise DocumentDataQualityError("inventory document size_bytes must be a non-negative integer")
    return {"category": category, "relative_path": relative_path.replace("\\", "/"), "sha256": digest, "size_bytes": size}


def _duplicate_findings(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = {}
    for document in documents:
        grouped.setdefault(document["sha256"], []).append(document["relative_path"])
    return [
        {"code": "duplicate_document", "severity": "warning", "document_paths": sorted(paths), "message": "Duplicate document content requires review."}
        for paths in grouped.values() if len(paths) > 1
    ]


def _uncategorized_findings(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paths = sorted(document["relative_path"] for document in documents if document["category"] == "uncategorized")
    return [] if not paths else [{"code": "unclassified_document", "severity": "warning", "document_paths": paths, "message": "Classify documents before relying on them."}]


def _missing_month_findings(documents: list[dict[str, Any]], policies: Any) -> list[dict[str, Any]]:
    if not isinstance(policies, list):
        raise DocumentDataQualityError("expected_periods must be a list")
    findings = []
    for policy in policies:
        if not isinstance(policy, dict) or not isinstance(policy.get("category"), str):
            raise DocumentDataQualityError("expected period requires category, start_month and end_month")
        start, end = _month(policy.get("start_month"), "start_month"), _month(policy.get("end_month"), "end_month")
        if start > end:
            raise DocumentDataQualityError("expected period start_month must not follow end_month")
        observed = {_document_month(document) for document in documents if document["category"] == policy["category"]}
        for value in _months_between(start, end):
            if value not in observed:
                findings.append({"code": "missing_month", "severity": "warning", "category": policy["category"], "month": value, "message": "Expected monthly document is missing."})
    return findings


def _declared_total_findings(documents: list[dict[str, Any]], totals: Any) -> list[dict[str, Any]]:
    if not isinstance(totals, list):
        raise DocumentDataQualityError("declared_totals must be a list")
    findings = []
    for total in totals:
        if not isinstance(total, dict) or not isinstance(total.get("total_id"), str) or not total["total_id"]:
            raise DocumentDataQualityError("declared total requires total_id")
        category = total.get("category")
        if category is not None and not isinstance(category, str):
            raise DocumentDataQualityError("declared total category must be a string")
        scoped = [document for document in documents if category is None or document["category"] == category]
        for field, actual in (("document_count", len(scoped)), ("size_bytes", sum(document["size_bytes"] for document in scoped))):
            expected = total.get(field)
            if expected is not None and (not isinstance(expected, int) or expected < 0):
                raise DocumentDataQualityError(f"declared total {field} must be a non-negative integer")
            if expected is not None and expected != actual:
                findings.append({"code": "declared_total_mismatch", "severity": "warning", "total_id": total["total_id"], "category": category, "field": field, "expected": expected, "actual": actual, "message": "Declared inventory total is inconsistent."})
    return findings


def _document_month(document: dict[str, Any]) -> str | None:
    match = _MONTH_PATTERN.search(document["relative_path"])
    if match is None or not 1 <= int(match.group(2)) <= 12:
        return None
    return f"{match.group(1)}-{match.group(2)}"


def _month(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise DocumentDataQualityError(f"{label} must be YYYY-MM")
    return value


def _months_between(start: str, end: str) -> list[str]:
    year, month = map(int, start.split("-")); final_year, final_month = map(int, end.split("-")); values = []
    while (year, month) <= (final_year, final_month):
        values.append(f"{year:04d}-{month:02d}"); year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return values


def _remediation(finding: dict[str, Any]) -> dict[str, Any]:
    action = {"duplicate_document": "Review duplicates and retain one authoritative copy.", "unclassified_document": "Move or classify the document in a known category.", "missing_month": "Acquire or explicitly waive the missing monthly document.", "declared_total_mismatch": "Reconcile the declared total with the inventory."}[finding["code"]]
    return {"finding_code": finding["code"], "action": action, "status": "open"}


def _workspace(root: Path) -> Path:
    workspace = root.resolve()
    if not workspace.is_dir(): raise DocumentDataQualityError(f"workspace path is not a directory: {root}")
    return workspace


def _workspace_path(workspace: Path, raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute() or PureWindowsPath(raw).is_absolute(): raise DocumentDataQualityError(f"{label} must be a relative path")
    path = (workspace / Path(raw.replace("\\", "/"))).resolve(); _require_within(workspace, path, label); return path


def _require_within(root: Path, path: Path, label: str) -> None:
    try: path.relative_to(root)
    except ValueError as exc: raise DocumentDataQualityError(f"{label} path is outside workspace: {path}") from exc


def _relative(workspace: Path, path: Path) -> str: return path.resolve().relative_to(workspace).as_posix()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise DocumentDataQualityError(f"cannot read {label}: {path}") from exc
    if not isinstance(value, dict): raise DocumentDataQualityError(f"{label} must be an object")
    return value


def _date(value: Any, label: str) -> date:
    if not isinstance(value, str): raise DocumentDataQualityError(f"{label} must be an ISO date")
    try: return date.fromisoformat(value)
    except ValueError as exc: raise DocumentDataQualityError(f"{label} must be an ISO date") from exc


def _write_atomic(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); os.replace(temporary, path)
    except OSError as exc: raise DocumentDataQualityError(f"cannot write data quality report: {path}") from exc
