from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

CATALOG_SCHEMA_VERSION = "knowledge-citation-catalog/v1"
INDEX_SCHEMA_VERSION = "citation-index/v1"
SEARCH_SCHEMA_VERSION = "citation-search/v1"

SUPPORTED_AUTHORITY_LEVELS = {"primary_law", "official_guidance", "institutional_guidance"}
SUPPORTED_SOURCE_STATUSES = {"active", "abrogated", "superseded", "withdrawn"}


class CitationIndexError(ValueError):
    pass


def build_citation_index(
    catalog_path: Path,
    knowledge_root: Path,
    contract_records: list[dict[str, Any]] | None = None,
    output_path: Path | None = None,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    catalog = _read_json(catalog_path, "citation catalog")
    if catalog.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise CitationIndexError(
            f"Citation catalog has schema {catalog.get('schema_version')}; expected {CATALOG_SCHEMA_VERSION}"
        )
    catalog_id = _required_text(catalog, "catalog_id", "citation catalog")
    effective_date = _iso_date(as_of_date or date.today().isoformat(), "as_of_date")
    data_gaps: list[dict[str, Any]] = []

    citations, citation_aliases = _normalize_citations(catalog.get("citations"), data_gaps)
    documents = _normalize_documents(
        catalog.get("documents"),
        knowledge_root,
        citation_aliases,
        data_gaps,
    )
    _link_documents_to_citations(citations, documents, data_gaps)
    _find_unindexed_documents(catalog, knowledge_root, documents, data_gaps)
    contracts = _normalize_contracts(contract_records or [])

    citations.sort(key=lambda item: item["citation_id"])
    documents.sort(key=lambda item: item["document_id"])
    contracts.sort(key=lambda item: item["schema_version"])
    data_gaps.sort(key=lambda item: (item["code"], str(item.get("path", "")), str(item.get("citation_id", ""))))

    core = {
        "index_id": f"{catalog_id}-index",
        "catalog": {
            "catalog_id": catalog_id,
            "schema_version": CATALOG_SCHEMA_VERSION,
            "content_hash": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        },
        "as_of_date": effective_date,
        "summary": {
            "citation_count": len(citations),
            "knowledge_document_count": len(documents),
            "contract_count": len(contracts),
            "data_gap_count": len(data_gaps),
        },
        "citations": citations,
        "knowledge_documents": documents,
        "contracts": contracts,
        "data_gaps": data_gaps,
    }
    snapshot = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "record_type": "CitationIndexSnapshot",
        "status": "complete" if not data_gaps else "complete_with_gaps",
        **core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(core),
        },
        "notes": (
            "The index records public knowledge sources and versioned contracts. "
            "Missing citations remain explicit data gaps and are not inferred."
        ),
    }
    if output_path is not None:
        _write_json(output_path, snapshot, "citation index")
    return snapshot


def search_citation_index(
    index_path: Path,
    query: str | None = None,
    jurisdiction: str | None = None,
    topic: str | None = None,
    as_of_date: str | None = None,
    include_inactive: bool = False,
) -> dict[str, Any]:
    index = _read_json(index_path, "citation index")
    if index.get("schema_version") != INDEX_SCHEMA_VERSION:
        raise CitationIndexError(
            f"Citation index has schema {index.get('schema_version')}; expected {INDEX_SCHEMA_VERSION}"
        )
    effective_date = _iso_date(as_of_date or index.get("as_of_date"), "as_of_date")
    normalized_query = (query or "").strip().casefold()
    normalized_jurisdiction = (jurisdiction or "").strip().upper()
    normalized_topic = (topic or "").strip().casefold()

    matches: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for citation in index.get("citations", []):
        if not isinstance(citation, dict):
            raise CitationIndexError("Citation index contains a non-object citation")
        if normalized_jurisdiction and normalized_jurisdiction not in citation.get("jurisdictions", []):
            continue
        if normalized_topic and normalized_topic not in {str(value).casefold() for value in citation.get("topics", [])}:
            continue
        if normalized_query and not _matches_query(citation, normalized_query):
            continue
        temporal_status = _temporal_status(citation, effective_date)
        result = {**citation, "temporal_status": temporal_status}
        if temporal_status == "active" or include_inactive:
            matches.append(result)
        else:
            excluded.append({"citation_id": citation["citation_id"], "reason": temporal_status})

    matches.sort(key=lambda item: (-_authority_rank(item["authority_level"]), item["citation_id"]))
    excluded.sort(key=lambda item: item["citation_id"])
    core = {
        "query": {
            "text": query or "",
            "jurisdiction": normalized_jurisdiction or None,
            "topic": topic or None,
            "as_of_date": effective_date,
            "include_inactive": bool(include_inactive),
        },
        "citation_count": len(matches),
        "citations": matches,
        "excluded_citations": excluded,
        "source_index": {
            "path": str(index_path),
            "content_hash": index.get("reproducibility", {}).get("content_hash"),
        },
        "data_gaps": list(index.get("data_gaps", [])),
    }
    return {
        "schema_version": SEARCH_SCHEMA_VERSION,
        "record_type": "CitationSearchResult",
        "status": "complete" if matches else "complete_no_matches",
        **core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(core),
        },
    }


def _normalize_citations(
    raw_citations: Any,
    data_gaps: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if not isinstance(raw_citations, list):
        raise CitationIndexError("citation catalog citations must be a list")
    by_locator: dict[str, dict[str, Any]] = {}
    aliases: dict[str, str] = {}
    seen_ids: set[str] = set()

    for position, raw in enumerate(raw_citations):
        context = f"citation[{position}]"
        if not isinstance(raw, dict):
            raise CitationIndexError(f"{context} must be an object")
        citation_id = _required_text(raw, "citation_id", context)
        if citation_id in seen_ids:
            raise CitationIndexError(f"Duplicate citation id: {citation_id}")
        seen_ids.add(citation_id)
        authority = _required_text(raw, "authority_level", context)
        if authority not in SUPPORTED_AUTHORITY_LEVELS:
            raise CitationIndexError(f"Unsupported authority level for {citation_id}: {authority}")
        source_status = _required_text(raw, "source_status", context)
        if source_status not in SUPPORTED_SOURCE_STATUSES:
            raise CitationIndexError(f"Unsupported source status for {citation_id}: {source_status}")
        url = _optional_text(raw.get("url"))
        official_reference = _optional_text(raw.get("official_reference"))
        if not url and not official_reference:
            raise CitationIndexError(f"Citation {citation_id} requires url or official_reference")
        locator_key = _canonical_url(url) if url else f"ref:{official_reference.casefold()}"
        valid_from = _optional_iso_date(raw.get("valid_from"), f"{citation_id}.valid_from")
        valid_to = _optional_iso_date(raw.get("valid_to"), f"{citation_id}.valid_to")
        if valid_from and valid_to and valid_to < valid_from:
            raise CitationIndexError(f"Citation {citation_id} valid_to precedes valid_from")
        if source_status in {"abrogated", "superseded"} and not valid_to:
            raise CitationIndexError(f"Citation {citation_id} with status {source_status} requires valid_to")
        record = {
            "citation_id": citation_id,
            "alias_citation_ids": [],
            "title": _required_text(raw, "title", context),
            "issuer": _required_text(raw, "issuer", context),
            "source_type": _required_text(raw, "source_type", context),
            "authority_level": authority,
            "url": url,
            "official_reference": official_reference,
            "jurisdictions": _text_list(raw.get("jurisdictions"), f"{citation_id}.jurisdictions", upper=True),
            "topics": _text_list(raw.get("topics"), f"{citation_id}.topics"),
            "valid_from": valid_from,
            "valid_to": valid_to,
            "verified_at": _optional_iso_date(raw.get("verified_at"), f"{citation_id}.verified_at"),
            "source_status": source_status,
            "knowledge_document_ids": [],
        }
        if not valid_from:
            data_gaps.append({
                "code": "citation_validity_start_missing",
                "citation_id": citation_id,
                "message": "Citation has no verified validity start.",
            })
        if record["verified_at"] is None:
            data_gaps.append({
                "code": "citation_verification_date_missing",
                "citation_id": citation_id,
                "message": "Citation has no recorded verification date.",
            })
        existing = by_locator.get(locator_key)
        if existing is None:
            by_locator[locator_key] = record
            aliases[citation_id] = citation_id
            continue
        _validate_duplicate_compatibility(existing, record)
        aliases[citation_id] = existing["citation_id"]
        existing["alias_citation_ids"].append(citation_id)
        existing["jurisdictions"] = sorted(set(existing["jurisdictions"]) | set(record["jurisdictions"]))
        existing["topics"] = sorted(set(existing["topics"]) | set(record["topics"]))

    return list(by_locator.values()), aliases


def _normalize_documents(
    raw_documents: Any,
    knowledge_root: Path,
    citation_aliases: dict[str, str],
    data_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(raw_documents, list):
        raise CitationIndexError("citation catalog documents must be a list")
    documents: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for position, raw in enumerate(raw_documents):
        context = f"document[{position}]"
        if not isinstance(raw, dict):
            raise CitationIndexError(f"{context} must be an object")
        document_id = _required_text(raw, "document_id", context)
        relative_path = _required_text(raw, "path", context).replace("\\", "/")
        if document_id in seen_ids:
            raise CitationIndexError(f"Duplicate document id: {document_id}")
        if relative_path in seen_paths:
            raise CitationIndexError(f"Duplicate knowledge document path: {relative_path}")
        seen_ids.add(document_id)
        seen_paths.add(relative_path)
        document_path = _safe_knowledge_path(knowledge_root, relative_path)
        if not document_path.is_file():
            raise CitationIndexError(f"Knowledge document not found: {relative_path}")
        raw_citation_ids = _text_list(raw.get("citation_ids"), f"{document_id}.citation_ids", allow_empty=True)
        unknown = sorted(citation_id for citation_id in raw_citation_ids if citation_id not in citation_aliases)
        if unknown:
            raise CitationIndexError(f"Document {document_id} references unknown citations: {', '.join(unknown)}")
        citation_ids = sorted({citation_aliases[citation_id] for citation_id in raw_citation_ids})
        if not citation_ids:
            data_gaps.append({
                "code": "knowledge_document_citation_missing",
                "path": relative_path,
                "document_id": document_id,
                "message": "Knowledge document has no structured citation.",
            })
        documents.append({
            "document_id": document_id,
            "path": relative_path,
            "title": _markdown_title(document_path),
            "topics": _text_list(raw.get("topics"), f"{document_id}.topics"),
            "jurisdictions": _text_list(raw.get("jurisdictions"), f"{document_id}.jurisdictions", upper=True),
            "citation_ids": citation_ids,
            "content_hash": hashlib.sha256(document_path.read_bytes()).hexdigest(),
        })
    return documents


def _link_documents_to_citations(
    citations: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
) -> None:
    by_id = {citation["citation_id"]: citation for citation in citations}
    for document in documents:
        for citation_id in document["citation_ids"]:
            by_id[citation_id]["knowledge_document_ids"].append(document["document_id"])
    for citation in citations:
        citation["knowledge_document_ids"].sort()
        citation["alias_citation_ids"].sort()
        if not citation["knowledge_document_ids"]:
            data_gaps.append({
                "code": "orphan_citation",
                "citation_id": citation["citation_id"],
                "message": "Citation is not linked to a knowledge document.",
            })


def _find_unindexed_documents(
    catalog: dict[str, Any],
    knowledge_root: Path,
    documents: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
) -> None:
    roots = _text_list(catalog.get("corpus_roots"), "citation catalog corpus_roots")
    excluded = {path.replace("\\", "/") for path in _text_list(
        catalog.get("excluded_paths", []), "citation catalog excluded_paths", allow_empty=True
    )}
    indexed = {document["path"] for document in documents}
    for root_name in roots:
        root_path = _safe_knowledge_path(knowledge_root, root_name)
        if not root_path.is_dir():
            raise CitationIndexError(f"Knowledge corpus root not found: {root_name}")
        for path in sorted(root_path.rglob("*.md")):
            relative_path = path.relative_to(knowledge_root.resolve()).as_posix()
            if relative_path in excluded or relative_path in indexed:
                continue
            data_gaps.append({
                "code": "unindexed_knowledge_document",
                "path": relative_path,
                "message": "Markdown document is inside the declared corpus but absent from the catalog.",
            })


def _normalize_contracts(contract_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for position, tool in enumerate(contract_records):
        if not isinstance(tool, dict):
            raise CitationIndexError(f"contract record[{position}] must be an object")
        tool_id = _required_text(tool, "tool_id", f"contract record[{position}]")
        for role in ("input", "output"):
            schema_version = _required_text(tool, f"{role}_schema_version", tool_id)
            record = contracts.setdefault(
                schema_version,
                {"schema_version": schema_version, "roles": [], "tool_ids": []},
            )
            record["roles"].append(role)
            record["tool_ids"].append(tool_id)
    for contract in contracts.values():
        contract["roles"] = sorted(set(contract["roles"]))
        contract["tool_ids"] = sorted(set(contract["tool_ids"]))
    return list(contracts.values())


def _matches_query(citation: dict[str, Any], query: str) -> bool:
    haystack = " ".join(
        [
            citation.get("citation_id", ""),
            citation.get("title", ""),
            citation.get("issuer", ""),
            " ".join(citation.get("topics", [])),
            " ".join(citation.get("jurisdictions", [])),
        ]
    ).casefold()
    return all(term in haystack for term in query.split())


def _temporal_status(citation: dict[str, Any], as_of_date: str) -> str:
    valid_from = citation.get("valid_from")
    valid_to = citation.get("valid_to")
    source_status = citation.get("source_status")
    if not valid_from:
        return "unknown_validity"
    if valid_from and as_of_date < valid_from:
        return "not_yet_valid"
    if valid_to and as_of_date > valid_to:
        return "abrogated" if source_status in {"abrogated", "superseded"} else "expired"
    if source_status == "withdrawn":
        return "withdrawn"
    return "active"


def _authority_rank(authority_level: str) -> int:
    return {"primary_law": 3, "official_guidance": 2, "institutional_guidance": 1}.get(authority_level, 0)


def _validate_duplicate_compatibility(existing: dict[str, Any], duplicate: dict[str, Any]) -> None:
    keys = ("issuer", "source_type", "authority_level", "valid_from", "valid_to", "verified_at", "source_status")
    conflicts = [key for key in keys if existing.get(key) != duplicate.get(key)]
    if conflicts:
        raise CitationIndexError(
            f"Duplicate locator has conflicting metadata for {duplicate['citation_id']}: {', '.join(conflicts)}"
        )


def _canonical_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise CitationIndexError(f"Citation URL must be absolute HTTP(S): {value}")
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def _safe_knowledge_path(knowledge_root: Path, relative_path: str) -> Path:
    root = knowledge_root.resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        raise CitationIndexError(f"Knowledge path escapes repository root: {relative_path}")
    return candidate


def _markdown_title(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8") as handle:
            first_line = handle.readline().strip()
    except OSError as exc:
        raise CitationIndexError(f"Cannot read knowledge document: {path}") from exc
    return first_line[2:].strip() if first_line.startswith("# ") else path.stem


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CitationIndexError(f"Cannot read {label}: {path}") from exc
    if not isinstance(data, dict):
        raise CitationIndexError(f"{label} must contain a JSON object")
    return data


def _write_json(path: Path, data: dict[str, Any], label: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise CitationIndexError(f"Cannot write {label}: {path}") from exc


def _required_text(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CitationIndexError(f"{context} requires non-empty {key}")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CitationIndexError("Optional text values must be non-empty strings or null")
    return value.strip()


def _text_list(value: Any, context: str, upper: bool = False, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise CitationIndexError(f"{context} must be {'a' if allow_empty else 'a non-empty'} list")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise CitationIndexError(f"{context} entries must be non-empty strings")
        text = item.strip().upper() if upper else item.strip()
        normalized.append(text)
    return sorted(set(normalized))


def _iso_date(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise CitationIndexError(f"{context} must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise CitationIndexError(f"{context} must be an ISO date") from exc


def _optional_iso_date(value: Any, context: str) -> str | None:
    return None if value is None else _iso_date(value, context)


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
