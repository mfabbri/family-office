"""Local, deterministic security checks and explicit file encryption."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class SecurityError(ValueError):
    """Raised when a security operation cannot be completed safely."""


SCHEMA_VERSION = "security-check/v1"
DEFAULT_KEY_RELATIVE = Path(".security") / "workspace.key"
_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
)
_SENSITIVE_SUFFIXES = {".pem", ".p12", ".pfx", ".key", ".env", ".secret", ".token"}
_SKIP_DIRS = {".git", ".venv", "__pycache__", ".security"}


def _resolve_inside(root: Path, candidate: Path) -> Path:
    root = root.resolve()
    path = (root / candidate if not candidate.is_absolute() else candidate).resolve()
    if path != root and root not in path.parents:
        raise SecurityError("path must remain inside the workspace")
    return path


def _set_private_mode(path: Path) -> None:
    # POSIX bits are still useful on Windows and are harmless where ACLs apply.
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError as exc:
        raise SecurityError(f"cannot restrict permissions for {path.name}") from exc


def ensure_secret_store(workspace: Path, key_path: Path | None = None) -> Path:
    workspace = workspace.resolve()
    path = _resolve_inside(workspace, key_path or DEFAULT_KEY_RELATIVE)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not path.is_file():
            raise SecurityError("secret store path is not a file")
        _set_private_mode(path)
        try:
            Fernet(path.read_bytes())
        except (ValueError, TypeError) as exc:
            raise SecurityError("secret store contains an invalid key") from exc
        return path
    path.write_bytes(Fernet.generate_key())
    _set_private_mode(path)
    return path


def _load_fernet(workspace: Path, key_path: Path | None = None) -> tuple[Path, Fernet]:
    path = ensure_secret_store(workspace, key_path)
    return path, Fernet(path.read_bytes())


def encrypt_file(workspace: Path, input_path: Path, output_path: Path | None = None, key_path: Path | None = None) -> Path:
    source = _resolve_inside(workspace, input_path)
    if not source.is_file():
        raise SecurityError("input file does not exist")
    destination = _resolve_inside(workspace, output_path or Path(str(input_path) + ".enc"))
    if destination == source:
        raise SecurityError("encrypted output must differ from input")
    _, cipher = _load_fernet(workspace, key_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_bytes(cipher.encrypt(source.read_bytes()))
    _set_private_mode(temporary)
    os.replace(temporary, destination)
    _set_private_mode(destination)
    return destination


def decrypt_file(workspace: Path, input_path: Path, output_path: Path, key_path: Path | None = None) -> Path:
    source = _resolve_inside(workspace, input_path)
    destination = _resolve_inside(workspace, output_path)
    if not source.is_file() or source == destination:
        raise SecurityError("invalid encrypted input or output")
    _, cipher = _load_fernet(workspace, key_path)
    try:
        plaintext = cipher.decrypt(source.read_bytes())
    except InvalidToken as exc:
        raise SecurityError("encrypted file cannot be authenticated with the secret store") from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_bytes(plaintext)
    _set_private_mode(temporary)
    os.replace(temporary, destination)
    _set_private_mode(destination)
    return destination


def redact_sensitive_text(message: str) -> str:
    """Redact likely credentials while keeping stable diagnostic text."""
    result = message
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub(lambda match: f"{match.group(0)[:match.group(0).find('=') + 1] if '=' in match.group(0) else '[REDACTED]'}[REDACTED]", result)
    return result


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _scan_for_secrets(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not root.exists():
        return findings
    for path in root.rglob("*"):
        if not path.is_file() or any(part in _SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            lowered = line.lower()
            if any(marker in lowered for marker in ("synthetic", "fixture", "example")):
                continue
            if any(pattern.search(line) for pattern in _SECRET_PATTERNS):
                findings.append({"code": "secret_detected", "path": _relative(root, path), "line": str(line_number)})
    return findings


def build_security_check(workspace: Path, repository: Path | None = None, key_path: Path | None = None) -> dict[str, Any]:
    workspace = workspace.resolve()
    key = ensure_secret_store(workspace, key_path)
    findings = _scan_for_secrets(repository.resolve() if repository else workspace)
    mode = stat.S_IMODE(key.stat().st_mode)
    if os.name != "nt" and mode & (stat.S_IRWXG | stat.S_IRWXO):
        findings.append({"code": "secret_store_permissions", "path": _relative(workspace, key), "line": "-"})
    for path in workspace.rglob("*"):
        if path.is_file() and path.suffix.lower() in _SENSITIVE_SUFFIXES and ".security" not in path.parts:
            findings.append({"code": "unencrypted_sensitive_file", "path": _relative(workspace, path), "line": "-"})
    status = "ready" if not findings else "attention"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "workspace": _relative(workspace.parent, workspace),
        "secret_store": {"path": _relative(workspace, key), "permissions": "acl-managed" if os.name == "nt" else oct(mode)},
        "findings": findings,
        "data_gaps": [] if not findings else [{"code": item["code"], "path": item["path"]} for item in findings],
        "log_policy": "diagnostics contain relative paths and finding codes only; secrets and file contents are never emitted",
    }
