"""Local encrypted workspace backups with deterministic manifests."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from cryptography.fernet import Fernet, InvalidToken

from family_office_engine.services.security import SecurityError, ensure_secret_store

SCHEMA_VERSION = "workspace-backup/v1"
DEFAULT_BACKUP_RELATIVE = Path("backups") / "workspace.fobak"
_EXCLUDED_DIRS = {".security", "backups", ".history", ".venv", "__pycache__"}


class BackupError(ValueError):
    """Raised when a backup operation cannot be completed safely."""


def create_backup(
    workspace: Path,
    output_path: Path | None = None,
    key_path: Path | None = None,
    *,
    retention: int = 3,
    overwrite: bool = False,
) -> dict[str, Any]:
    root = workspace.resolve()
    if not root.is_dir():
        raise BackupError("workspace root is not a directory")
    if retention < 1:
        raise BackupError("retention must be at least 1")
    output = _inside(root, output_path or DEFAULT_BACKUP_RELATIVE)
    if output.exists() and not overwrite:
        raise BackupError("backup already exists; use --overwrite to replace it")
    files = list(_collect_files(root))
    plain = _zip_bytes(files)
    key = _load_key(root, key_path)
    encrypted = Fernet(key).encrypt(plain)
    _atomic_write(output, encrypted)
    manifest = _manifest(root, output, files, plain, encrypted, retention)
    _atomic_write(_manifest_path(output), _canonical_json(manifest))
    _apply_retention(output, retention)
    return manifest | {"output_path": output.relative_to(root).as_posix()}


def verify_backup(workspace: Path, input_path: Path, key_path: Path | None = None) -> dict[str, Any]:
    root = workspace.resolve()
    backup = _inside(root, input_path)
    manifest_path = _manifest_path(backup)
    if not backup.is_file() or not manifest_path.is_file():
        raise BackupError("backup and manifest must both exist")
    manifest = _read_manifest(manifest_path)
    encrypted = backup.read_bytes()
    if hashlib.sha256(encrypted).hexdigest() != manifest.get("encrypted_sha256"):
        raise BackupError("backup integrity hash does not match its manifest")
    plain = _decrypt(encrypted, _load_key(root, key_path))
    actual = _inspect_zip(plain)
    if actual != manifest.get("files"):
        raise BackupError("backup contents do not match its manifest")
    return {"schema_version": SCHEMA_VERSION, "status": "verified", "file_count": len(actual), "manifest": manifest_path.relative_to(root).as_posix()}


def restore_backup(
    workspace: Path,
    input_path: Path,
    target: Path,
    key_path: Path | None = None,
    selections: Iterable[str] = (),
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    root = workspace.resolve()
    backup = _inside(root, input_path)
    destination = _inside(root, target)
    if not destination.exists():
        destination.mkdir(parents=True)
    if not destination.is_dir():
        raise BackupError("restore target is not a directory")
    plain = _decrypt(backup.read_bytes(), _load_key(root, key_path))
    wanted = {_normalise_selection(item) for item in selections if item.strip()}
    restored = 0
    with _open_zip(plain) as archive:
        for info in archive.infolist():
            relative = _safe_member(info.filename)
            if wanted and not any(relative == item or relative.startswith(item + "/") for item in wanted):
                continue
            target_file = destination / Path(*PurePosixPath(relative).parts)
            if target_file.exists() and not overwrite:
                raise BackupError(f"restore target already contains {relative}; use --overwrite")
            target_file.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(target_file, archive.read(info))
            restored += 1
    return {"schema_version": SCHEMA_VERSION, "status": "restored", "file_count": restored, "target": str(destination)}


def recovery_drill(workspace: Path, input_path: Path, target: Path, key_path: Path | None = None) -> dict[str, Any]:
    root = workspace.resolve()
    destination = _inside(root, target)
    if destination.exists() and any(destination.iterdir()):
        raise BackupError("recovery drill target must be an empty directory")
    result = restore_backup(workspace, input_path, destination, key_path)
    result["status"] = "drill_passed"
    result["recovery_note"] = "Backup authenticated and restored into an empty directory."
    return result


def _collect_files(root: Path) -> Iterable[tuple[str, bytes]]:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in _EXCLUDED_DIRS for part in relative.parts) or path.name.endswith(".tmp"):
            continue
        yield relative.as_posix(), path.read_bytes()


def _zip_bytes(files: list[tuple[str, bytes]]) -> bytes:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "payload.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, content in files:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        return path.read_bytes()


def _inspect_zip(payload: bytes) -> list[dict[str, Any]]:
    with _open_zip(payload) as archive:
        entries = []
        for info in archive.infolist():
            name = _safe_member(info.filename)
            content = archive.read(info)
            entries.append({"path": name, "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)})
        return entries


def _open_zip(payload: bytes) -> zipfile.ZipFile:
    import io
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
        if archive.testzip() is not None:
            raise BackupError("backup ZIP is corrupted")
        return archive
    except (zipfile.BadZipFile, OSError) as exc:
        raise BackupError("backup payload is not a valid ZIP") from exc


def _manifest(root: Path, output: Path, files: list[tuple[str, bytes]], plain: bytes, encrypted: bytes, retention: int) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "record_type": "WorkspaceBackupManifest", "hash_algorithm": "sha256", "files": [{"path": name, "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)} for name, content in files], "payload_sha256": hashlib.sha256(plain).hexdigest(), "encrypted_sha256": hashlib.sha256(encrypted).hexdigest(), "retention": retention, "excluded": sorted(_EXCLUDED_DIRS), "limitations": ["The secret store is never included; restoring requires the separate workspace key.", "Backups, temporary files, virtual environments, history, caches and symlinks are excluded.", "This local workflow does not upload or manage keys remotely."]}


def _apply_retention(current: Path, retention: int) -> None:
    candidates = sorted(current.parent.glob("*.fobak"), key=lambda item: (item.stat().st_mtime_ns, item.name), reverse=True)
    for old in candidates[retention:]:
        old.unlink(missing_ok=True)
        _manifest_path(old).unlink(missing_ok=True)


def _load_key(root: Path, key_path: Path | None) -> bytes:
    try:
        return ensure_secret_store(root, key_path).read_bytes()
    except SecurityError as exc:
        raise BackupError(str(exc)) from exc


def _decrypt(payload: bytes, key: bytes) -> bytes:
    try:
        return Fernet(key).decrypt(payload)
    except (InvalidToken, ValueError, TypeError) as exc:
        raise BackupError("backup cannot be authenticated with the secret store") from exc


def _inside(root: Path, candidate: Path) -> Path:
    path = (root / candidate if not candidate.is_absolute() else candidate).resolve()
    if path == root or root not in path.parents:
        raise BackupError("path must remain inside the workspace")
    return path


def _manifest_path(backup: Path) -> Path:
    return backup.with_name(backup.name + ".manifest.json")


def _normalise_selection(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise BackupError("restore selection must be a relative workspace path")
    return path.as_posix()


def _safe_member(value: str) -> str:
    return _normalise_selection(value)


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError("backup manifest is invalid") from exc
    if value.get("schema_version") != SCHEMA_VERSION:
        raise BackupError("unsupported backup manifest schema")
    return value


def _canonical_json(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
