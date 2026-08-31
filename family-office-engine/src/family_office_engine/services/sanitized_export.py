"""Deterministic, allowlisted exports suitable for technical sharing."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "sanitized-export/v1"
MANIFEST_PATH = "manifest.json"
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_ALLOWLIST = (
    (Path("family-office-engine") / "src", frozenset({".py"})),
    (Path("family-office-engine") / "docs" / "roadmap", frozenset({".md"})),
    (Path("family-office-engine") / "docs" / "reports", frozenset({".md"})),
)
_EXCLUDED_PARTS = frozenset({".venv", ".history", "snapshot", "snapshots", "workspace", "family-office-workspace"})
_REDACTIONS = (
    (re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", re.IGNORECASE), "[REDACTED_IBAN]"),
    (re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b(?:\+?\d[\d .()/-]{7,}\d)\b"), "[REDACTED_PHONE]"),
    (re.compile(r"(?i)(authorization\s*[:=]\s*[\"']bearer\s+)([^\"']+)([\"'])"), r"\1[REDACTED]\3"),
    (re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)([\"']?(?:api[_-]?key|token|password|secret|authorization)[\"']?\s*[:=]\s*[\"'])([^\"']*)([\"'])"), r"\1[REDACTED]\3"),
    (re.compile(r"(?i)([\"']?(?:api[_-]?key|token|password|secret|authorization)[\"']?\s*[:=]\s*)([^\s,#}\]]+)"), r"\1[REDACTED]"),
)


class SanitizedExportError(ValueError):
    """Raised when a sanitized export would violate its fixed boundary."""


def build_sanitized_export(source_root: Path, workspace_root: Path, output_path: Path, *, overwrite: bool = False) -> dict[str, Any]:
    """Write a reproducible ZIP from the fixed public-source allowlist.

    This deliberately has no option for arbitrary include patterns.  The manifest contains
    hashes and relative paths, but never source absolute paths or file contents.
    """
    source = source_root.resolve()
    workspace = workspace_root.resolve()
    if not source.is_dir():
        raise SanitizedExportError("source repository root is not a directory")
    if not workspace.is_dir():
        raise SanitizedExportError("workspace root is not a directory")
    output = _resolve_output(workspace, output_path)
    if output == source or source == workspace or (source in output.parents and workspace not in output.parents):
        raise SanitizedExportError("export target must not be inside the source repository outside the workspace")
    if output.exists() and not overwrite:
        raise SanitizedExportError("export target already exists; use --overwrite to replace it")

    included, exclusions, missing_roots = _collect_allowlisted_files(source)
    manifest = _manifest(included, exclusions, missing_roots)
    _write_zip_atomic(output, included, manifest)
    return manifest | {"output_path": output.relative_to(workspace).as_posix()}


def _resolve_output(workspace: Path, candidate: Path) -> Path:
    output = (workspace / candidate if not candidate.is_absolute() else candidate).resolve()
    if output == workspace or workspace not in output.parents:
        raise SanitizedExportError("export target must remain inside the workspace")
    return output


def _collect_allowlisted_files(source: Path) -> tuple[list[tuple[str, bytes]], Counter[str], list[str]]:
    included: list[tuple[str, bytes]] = []
    exclusions: Counter[str] = Counter()
    missing_roots: list[str] = []
    for relative_root, suffixes in _ALLOWLIST:
        root = source / relative_root
        if not root.is_dir():
            missing_roots.append(relative_root.as_posix())
            continue
        if root.is_symlink():
            exclusions["symlink"] += 1
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.is_symlink():
                exclusions["symlink"] += 1
                continue
            relative = path.relative_to(source)
            reason = _exclusion_reason(relative, path, source, suffixes)
            if reason:
                exclusions[reason] += 1
                continue
            try:
                content = _sanitize_content(path.read_bytes())
            except (OSError, UnicodeDecodeError):
                exclusions["binary_or_invalid_text"] += 1
                continue
            included.append((relative.as_posix(), content))
    return sorted(included), exclusions, sorted(missing_roots)


def _exclusion_reason(relative: Path, path: Path, source: Path, suffixes: frozenset[str]) -> str | None:
    parts = tuple(part.lower() for part in relative.parts)
    if any(part in _EXCLUDED_PARTS for part in parts):
        return "private_workspace_or_snapshot"
    if any("backup" in part for part in parts):
        return "backup"
    if path.suffix.lower() == ".pdf":
        return "pdf"
    if path.suffix.lower() not in suffixes:
        return "not_allowlisted"
    try:
        path.resolve().relative_to(source)
    except ValueError:
        return "outside_source"
    return None


def _manifest(included: list[tuple[str, bytes]], exclusions: Counter[str], missing_roots: list[str]) -> dict[str, Any]:
    files = [
        {"path": relative, "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)}
        for relative, content in included
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "SanitizedExportManifest",
        "hash_algorithm": "sha256",
        "allowlist": ["family-office-engine/src/**/*.py", "family-office-engine/docs/roadmap/**/*.md", "family-office-engine/docs/reports/**/*.md"],
        "missing_allowlist_roots": missing_roots,
        "files": files,
        "counts": {"included": len(files), "excluded": sum(exclusions.values()), "excluded_by_reason": dict(sorted(exclusions.items()))},
        "redaction": {"status": "deterministic", "markers": ["[REDACTED_IBAN]", "[REDACTED_EMAIL]", "[REDACTED_PHONE]", "[REDACTED]"]},
        "limitations": [
            "Only fixed public-source paths are considered; no arbitrary discovery or include patterns are supported.",
            "Private workspace data, snapshots, backups, history, virtual environments and PDFs are excluded.",
            "This archive is a technical sharing package, not a backup or restore mechanism.",
        ],
    }


def _sanitize_content(content: bytes) -> bytes:
    text = content.decode("utf-8")
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text.encode("utf-8")


def _write_zip_atomic(output: Path, included: list[tuple[str, bytes]], manifest: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative, content in included:
                _write_zip_member(archive, relative, content)
            _write_zip_member(archive, MANIFEST_PATH, _canonical_json(manifest))
        os.replace(temporary, output)
    except (OSError, zipfile.BadZipFile) as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise SanitizedExportError("sanitized export could not be written atomically") from exc


def _write_zip_member(archive: zipfile.ZipFile, name: str, content: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def _canonical_json(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
