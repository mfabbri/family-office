import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "document-inventory/v1"
ORGANIZATION_SCHEMA_VERSION = "document-organization/v1"

IGNORED_FILENAMES = {".gitkeep"}

IMPORT_PRIORITY = {
    "pensione": 1,
    "pensione_inps": 1,
    "pensione_spagna": 2,
    "fonte": 3,
    "directa": 4,
    "investimenti_directa": 4,
    "investimenti_italia": 5,
    "investimenti_spagna": 6,
    "banca": 7,
    "polizze": 8,
    "bustepaga": 9,
    "buste_paga": 9,
    "payroll": 9,
    "cu": 10,
    "isee": 11,
}


class DocumentInventoryError(ValueError):
    pass


class DocumentOrganizationError(ValueError):
    pass


def build_document_inventory(inbox_path: Path, output_path: Path) -> dict[str, Any]:
    if not inbox_path.exists():
        raise DocumentInventoryError(f"Inbox path not found: {inbox_path}")
    if not inbox_path.is_dir():
        raise DocumentInventoryError(f"Inbox path is not a directory: {inbox_path}")

    documents = [
        _document_record(path, inbox_path)
        for path in sorted(inbox_path.rglob("*"))
        if path.is_file() and path.name not in IGNORED_FILENAMES
    ]

    category_counts = Counter(document["category"] for document in documents)
    extension_counts = Counter(document["extension"] for document in documents)

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "DocumentInventorySnapshot",
        "source": {
            "type": "workspace-inbox",
            "path": str(inbox_path),
        },
        "summary": {
            "document_count": len(documents),
            "categories": dict(sorted(category_counts.items())),
            "extensions": dict(sorted(extension_counts.items())),
        },
        "documents": documents,
        "next_import_candidates": _next_import_candidates(category_counts),
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise DocumentInventoryError(f"Cannot write document inventory: {output_path}") from exc

    return snapshot


def organize_documents(
    inbox_path: Path,
    documents_path: Path,
    manifest_path: Path,
    apply: bool = False,
) -> dict[str, Any]:
    if not inbox_path.exists():
        raise DocumentOrganizationError(f"Inbox path not found: {inbox_path}")
    if not inbox_path.is_dir():
        raise DocumentOrganizationError(f"Inbox path is not a directory: {inbox_path}")

    workspace_root = inbox_path.resolve().parent
    resolved_inbox = inbox_path.resolve()
    resolved_documents = documents_path.resolve()
    resolved_manifest = manifest_path.resolve()
    _require_within(workspace_root, resolved_inbox, "inbox")
    _require_within(workspace_root, resolved_documents, "documents")
    _require_within(workspace_root, resolved_manifest, "manifest")

    operations: list[dict[str, Any]] = []
    planned_destinations: set[Path] = set()
    for path in sorted(inbox_path.rglob("*")):
        if not path.is_file() or path.name in IGNORED_FILENAMES:
            continue
        operation = _organization_operation(path, inbox_path, documents_path, planned_destinations)
        planned_destinations.add(Path(operation["destination_path"]))
        operations.append(operation)

    if apply:
        _apply_operations(operations, workspace_root)
        status = "applied"
    else:
        status = "planned"

    manifest = {
        "schema_version": ORGANIZATION_SCHEMA_VERSION,
        "record_type": "DocumentOrganizationManifest",
        "status": status,
        "source": {
            "type": "workspace-inbox",
            "path": str(inbox_path),
        },
        "destination_root": str(documents_path),
        "summary": {
            "operation_count": len(operations),
            "apply": apply,
            "destinations": dict(
                sorted(Counter(operation["destination_category"] for operation in operations).items())
            ),
        },
        "operations": operations,
    }

    try:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise DocumentOrganizationError(f"Cannot write document organization manifest: {manifest_path}") from exc

    return manifest


def _document_record(path: Path, inbox_path: Path) -> dict[str, Any]:
    relative_path = path.relative_to(inbox_path)
    category = _category_from_relative_path(relative_path)

    return {
        "category": category,
        "extension": path.suffix.lower() or "none",
        "filename": path.name,
        "relative_path": str(relative_path),
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _category_from_relative_path(relative_path: Path) -> str:
    if len(relative_path.parts) <= 1:
        return "uncategorized"
    first_part = relative_path.parts[0].lower()
    second_part = relative_path.parts[1].lower() if len(relative_path.parts) > 2 else ""
    if first_part == "pensione" and second_part in {"spagna", "es"}:
        return "pensione_spagna"
    if first_part == "pensione" and second_part == "inps":
        return "pensione_inps"
    return relative_path.parts[0].lower()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _organization_operation(
    path: Path,
    inbox_path: Path,
    documents_path: Path,
    planned_destinations: set[Path],
) -> dict[str, Any]:
    relative_path = path.relative_to(inbox_path)
    destination_category = _destination_category(relative_path)
    destination_path = _unique_destination_path(
        documents_path / destination_category / path.name,
        _category_from_relative_path(relative_path),
        planned_destinations,
    )
    digest = _sha256(path)

    return {
        "source_path": str(path),
        "source_relative_path": str(relative_path),
        "source_category": _category_from_relative_path(relative_path),
        "destination_path": str(destination_path),
        "destination_relative_path": str(destination_path.relative_to(documents_path)),
        "destination_category": destination_category,
        "filename": path.name,
        "extension": path.suffix.lower() or "none",
        "size_bytes": path.stat().st_size,
        "sha256": digest,
        "action": "planned_move",
    }


def _unique_destination_path(destination_path: Path, source_category: str, planned_destinations: set[Path]) -> Path:
    if destination_path not in planned_destinations:
        return destination_path

    suffix = f"__from_{source_category}"
    candidate = destination_path.with_name(f"{destination_path.stem}{suffix}{destination_path.suffix}")
    counter = 2
    while candidate in planned_destinations:
        candidate = destination_path.with_name(
            f"{destination_path.stem}{suffix}_{counter}{destination_path.suffix}"
        )
        counter += 1
    return candidate


def _destination_category(relative_path: Path) -> str:
    filename = relative_path.name.lower()
    source_category = _category_from_relative_path(relative_path)
    if source_category == "fonte" or filename.startswith("sintesi_posizione_aderente") or filename.startswith("importi_versati"):
        return "fonte"
    if _is_directa_document(source_category, filename):
        return "investimenti/directa"
    if _is_spanish_pension_document(source_category, filename):
        return "pensione/spagna"
    if _is_payroll_document(source_category, filename):
        return "redditi/buste-paga"
    if _is_cu_document(source_category, filename):
        return "redditi/cu"
    if source_category in {"pensione", "pensione_inps", "inps"}:
        return "pensione/inps"
    if source_category == "investimenti_italia":
        return "investimenti/italia"
    if source_category == "investimenti_spagna":
        return "investimenti/spagna"
    if source_category == "isee":
        return "isee"
    return source_category


def _apply_operations(operations: list[dict[str, Any]], workspace_root: Path) -> None:
    for operation in operations:
        source = Path(operation["source_path"]).resolve()
        destination = Path(operation["destination_path"]).resolve()
        _require_within(workspace_root, source, "source")
        _require_within(workspace_root, destination, "destination")
        if not source.exists():
            raise DocumentOrganizationError(f"Source file not found: {source}")
        if destination.exists():
            if _sha256(destination) == operation["sha256"]:
                operation["action"] = "already_present"
                continue
            raise DocumentOrganizationError(f"Destination already exists with different content: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)
        operation["action"] = "moved"


def _require_within(root: Path, path: Path, label: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise DocumentOrganizationError(f"{label} path is outside workspace: {path}") from exc


def _next_import_candidates(category_counts: Counter[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for category, count in category_counts.items():
        candidates.append(
            {
                "category": category,
                "document_count": count,
                "priority": IMPORT_PRIORITY.get(category, 99),
                "suggested_increment": _suggested_increment(category),
            }
        )
    return sorted(candidates, key=lambda item: (item["priority"], item["category"]))


def _suggested_increment(category: str) -> str:
    suggestions = {
        "pensione": "Import INPS pension simulation PDFs, or split Spanish pension documents into pensione_spagna.",
        "pensione_inps": "Import INPS pension simulation PDFs.",
        "pensione_spagna": "Import Spanish pension documents.",
        "directa": "Import Directa investment statements.",
        "investimenti_directa": "Import Directa investment statements.",
        "fonte": "Refresh Fon.Te PDF/XLSX import.",
        "investimenti_italia": "Import Italian investment statements.",
        "investimenti_spagna": "Import Spanish investment statements.",
        "banca": "Import bank balances and account statements.",
        "polizze": "Import insurance policy values.",
        "bustepaga": "Import payroll payslips.",
        "buste_paga": "Import payroll payslips.",
        "payroll": "Import payroll payslips.",
        "cu": "Import Certificazione Unica documents.",
        "isee": "Use ISEE balances as supporting evidence, not as primary net-worth source.",
    }
    return suggestions.get(category, "Classify documents before building a parser.")


def _is_directa_document(source_category: str, filename: str) -> bool:
    return source_category in {"directa", "investimenti_directa"} or "directa" in filename


def _is_spanish_pension_document(source_category: str, filename: str) -> bool:
    if source_category in {"pensione_spagna", "pension_spagna", "pensione_es", "pension_es"}:
        return True
    normalized_filename = filename.replace(" ", "_").replace("-", "_")
    spanish_markers = (
        "pension_es",
        "pensione_spagna",
        "pension_spagna",
        "seguridad_social",
        "vida_laboral",
        "jubilacion",
        "plan_universal",
    )
    return source_category == "pensione" and any(marker in normalized_filename for marker in spanish_markers)


def _is_payroll_document(source_category: str, filename: str) -> bool:
    normalized_filename = filename.replace(" ", "_").replace("-", "_")
    payroll_categories = {"bustepaga", "buste_paga", "buste-paga", "payroll", "redditi"}
    payroll_markers = ("busta_paga", "bustapaga", "cedolino", "payslip")
    return source_category in payroll_categories or any(marker in normalized_filename for marker in payroll_markers)


def _is_cu_document(source_category: str, filename: str) -> bool:
    normalized_filename = filename.replace(" ", "_").replace("-", "_")
    return source_category in {"cu", "certificazione_unica"} or "certificazione_unica" in normalized_filename
