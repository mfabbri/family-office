import json
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "asset-availability/v1"
SNAPSHOT_RECORD_TYPE = "AssetAvailabilitySnapshot"
INPUT_RECORD_TYPE = "AssetAvailability"

ASSET_CLASSES = {
    "cash",
    "deposit",
    "brokerage",
    "pension_fund",
    "insurance_policy",
    "real_estate",
    "company_share",
    "other",
}
RISK_LEVELS = {"low", "medium", "high", "illiquid", "unknown"}
LIQUIDITY_TIERS = {
    "immediate",
    "short_term",
    "notice_required",
    "locked_until_date",
    "illiquid",
    "unknown",
}
CONSTRAINT_TYPES = {
    "none",
    "pension_lock",
    "policy_terms",
    "mortgage_or_lien",
    "co_ownership",
    "foreign_reporting",
    "sale_process",
    "other",
    "unknown",
}
TAX_TREATMENTS = {
    "ordinary_taxable",
    "tax_deferred",
    "pension_taxation",
    "insurance_wrapper",
    "real_estate_taxation",
    "foreign_asset_reporting",
    "unknown",
}


class AssetAvailabilityError(ValueError):
    pass


def validate_asset_availability(
    data: dict[str, Any],
    ownership_snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    errors: list[str] = []
    gaps: list[dict[str, Any]] = []

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported asset availability schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported asset availability record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_date(data, "as_of_date", errors)

    classifications = _required_list(data, "classifications", errors)
    ownership_asset_ids = _asset_ids_from_ownership(ownership_snapshot, errors)
    seen_asset_ids = _validate_classifications(classifications, ownership_asset_ids, errors, gaps)
    _validate_declared_gaps(data.get("data_gaps", []), errors, gaps)

    if ownership_asset_ids is not None:
        for asset_id in sorted(ownership_asset_ids - seen_asset_ids):
            gaps.append(_gap("missing_asset_availability", asset_id, "Asset has no availability classification."))

    if errors:
        raise AssetAvailabilityError("; ".join(errors))
    return gaps


def import_asset_availability(
    input_path: Path,
    output_path: Path,
    ownership_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    data = load_asset_availability(input_path)
    ownership_snapshot = _load_optional_ownership_snapshot(ownership_snapshot_path)
    gaps = validate_asset_availability(data, ownership_snapshot)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "complete" if not gaps else "partial",
        "source": {
            "type": "asset-availability-json",
            "path": str(input_path),
        },
        "household": {
            "household_id": data["household_id"],
            "as_of_date": data["as_of_date"],
            "ownership_snapshot_path": str(ownership_snapshot_path) if ownership_snapshot_path else None,
        },
        "taxonomy": _taxonomy(),
        "classifications": data["classifications"],
        "data_gaps": gaps,
        "notes": (
            "Asset availability is user-provided classification; liquidity, risk, tax treatment "
            "and constraints are not inferred."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise AssetAvailabilityError(f"Cannot write asset availability snapshot: {output_path}") from exc
    return snapshot


def load_asset_availability(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssetAvailabilityError(f"Asset availability file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AssetAvailabilityError(f"Invalid JSON in asset availability file: {exc}") from exc
    if not isinstance(data, dict):
        raise AssetAvailabilityError("Asset availability file must contain a JSON object")
    return data


def _load_optional_ownership_snapshot(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssetAvailabilityError(f"Invalid JSON in ownership snapshot: {exc}") from exc
    if not isinstance(data, dict):
        raise AssetAvailabilityError("Ownership snapshot must contain a JSON object")
    return data


def _asset_ids_from_ownership(ownership_snapshot: dict[str, Any] | None, errors: list[str]) -> set[str] | None:
    if ownership_snapshot is None:
        return None
    assets = ownership_snapshot.get("assets")
    if not isinstance(assets, list):
        errors.append("Ownership snapshot assets must be a list")
        return set()
    asset_ids: set[str] = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            errors.append(f"ownership.assets[{index}] must be an object")
            continue
        asset_id = asset.get("asset_id")
        if isinstance(asset_id, str) and asset_id:
            asset_ids.add(asset_id)
    return asset_ids


def _validate_classifications(
    classifications: list[Any],
    ownership_asset_ids: set[str] | None,
    errors: list[str],
    gaps: list[dict[str, Any]],
) -> set[str]:
    seen_asset_ids: set[str] = set()
    classification_ids: set[str] = set()
    for index, classification in enumerate(classifications):
        if not isinstance(classification, dict):
            errors.append(f"classifications[{index}] must be an object")
            continue
        classification_id = _required_string(classification, "classification_id", errors, f"classifications[{index}]")
        if classification_id:
            if classification_id in classification_ids:
                errors.append(f"Duplicate classification_id: {classification_id}")
            classification_ids.add(classification_id)
        asset_id = _required_string(classification, "asset_id", errors, f"classifications[{index}]")
        if asset_id:
            if asset_id in seen_asset_ids:
                errors.append(f"Duplicate asset_id classification: {asset_id}")
            seen_asset_ids.add(asset_id)
            if ownership_asset_ids is not None and asset_id not in ownership_asset_ids:
                errors.append(f"classifications[{index}].asset_id references unknown asset: {asset_id}")
        _validate_enum(classification, "asset_class", ASSET_CLASSES, errors, gaps, asset_id, f"classifications[{index}]")
        _validate_enum(classification, "risk_level", RISK_LEVELS, errors, gaps, asset_id, f"classifications[{index}]")
        _validate_currency(classification.get("currency"), errors, gaps, asset_id, f"classifications[{index}].currency")
        _validate_jurisdiction(
            classification.get("jurisdiction"),
            errors,
            gaps,
            asset_id,
            f"classifications[{index}].jurisdiction",
        )
        _validate_enum(
            classification,
            "liquidity_tier",
            LIQUIDITY_TIERS,
            errors,
            gaps,
            asset_id,
            f"classifications[{index}]",
        )
        _validate_constraints(classification.get("constraints"), errors, gaps, asset_id, f"classifications[{index}]")
        _validate_enum(
            classification,
            "tax_treatment",
            TAX_TREATMENTS,
            errors,
            gaps,
            asset_id,
            f"classifications[{index}]",
        )
        _validate_availability_date(classification, errors, gaps, asset_id, f"classifications[{index}]")
        _required_string(classification, "provenance", errors, f"classifications[{index}]")
    return seen_asset_ids


def _validate_enum(
    item: dict[str, Any],
    field: str,
    allowed: set[str],
    errors: list[str],
    gaps: list[dict[str, Any]],
    asset_id: str | None,
    label: str,
) -> None:
    value = item.get(field)
    if value in (None, ""):
        gaps.append(_gap(f"missing_{field}", asset_id, f"{field} is missing."))
        return
    if value not in allowed:
        errors.append(f"Invalid {field} for {label}")
    elif value == "unknown":
        gaps.append(_gap(f"unknown_{field}", asset_id, f"{field} is explicitly unknown."))


def _validate_currency(
    value: Any,
    errors: list[str],
    gaps: list[dict[str, Any]],
    asset_id: str | None,
    label: str,
) -> None:
    if value in (None, ""):
        gaps.append(_gap("missing_currency", asset_id, "currency is missing."))
        return
    if not isinstance(value, str) or len(value) != 3 or value.upper() != value:
        errors.append(f"{label} must be an ISO-4217 uppercase code")


def _validate_jurisdiction(
    value: Any,
    errors: list[str],
    gaps: list[dict[str, Any]],
    asset_id: str | None,
    label: str,
) -> None:
    if value in (None, ""):
        gaps.append(_gap("missing_jurisdiction", asset_id, "jurisdiction is missing."))
        return
    if not isinstance(value, str) or len(value) != 2 or value.upper() != value:
        errors.append(f"{label} must be an ISO-3166 alpha-2 uppercase code")


def _validate_constraints(
    constraints: Any,
    errors: list[str],
    gaps: list[dict[str, Any]],
    asset_id: str | None,
    label: str,
) -> None:
    if constraints in (None, ""):
        gaps.append(_gap("missing_constraints", asset_id, "constraints are missing."))
        return
    if not isinstance(constraints, list):
        errors.append(f"{label}.constraints must be a list")
        return
    if not constraints:
        gaps.append(_gap("missing_constraints", asset_id, "constraints are empty."))
        return
    for constraint in constraints:
        if constraint not in CONSTRAINT_TYPES:
            errors.append(f"Invalid constraint for {label}: {constraint}")
        elif constraint == "unknown":
            gaps.append(_gap("unknown_constraints", asset_id, "constraints are explicitly unknown."))


def _validate_availability_date(
    item: dict[str, Any],
    errors: list[str],
    gaps: list[dict[str, Any]],
    asset_id: str | None,
    label: str,
) -> None:
    liquidity_tier = item.get("liquidity_tier")
    first_available_date = item.get("first_available_date")
    if first_available_date in (None, ""):
        gaps.append(_gap("missing_first_available_date", asset_id, "first_available_date is missing."))
        return
    parsed = _parse_date(first_available_date, f"{label}.first_available_date", errors)
    as_of_date = _parse_date(item.get("availability_as_of_date"), f"{label}.availability_as_of_date", errors)
    if liquidity_tier == "immediate" and parsed is not None and as_of_date is not None and parsed > as_of_date:
        errors.append(f"{label}.first_available_date cannot be after availability_as_of_date for immediate liquidity")


def _validate_declared_gaps(raw_gaps: Any, errors: list[str], gaps: list[dict[str, Any]]) -> None:
    if raw_gaps in (None, ""):
        return
    if not isinstance(raw_gaps, list):
        errors.append("data_gaps must be a list")
        return
    for index, gap in enumerate(raw_gaps):
        if not isinstance(gap, dict):
            errors.append(f"data_gaps[{index}] must be an object")
            continue
        if not gap.get("code"):
            errors.append(f"data_gaps[{index}].code is required")
            continue
        gaps.append(gap)


def _required_list(data: dict[str, Any], field: str, errors: list[str]) -> list[Any]:
    value = data.get(field)
    if not isinstance(value, list):
        errors.append(f"{field} must be a list")
        return []
    return value


def _required_string(
    data: dict[str, Any],
    field: str,
    errors: list[str],
    prefix: str | None = None,
) -> str | None:
    label = field if prefix is None else f"{prefix}.{field}"
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} is required")
        return None
    return value


def _required_date(
    data: dict[str, Any],
    field: str,
    errors: list[str],
    prefix: str | None = None,
) -> date | None:
    label = field if prefix is None else f"{prefix}.{field}"
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} is required")
        return None
    return _parse_date(value, label, errors)


def _parse_date(value: Any, label: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{label} must be an ISO date string")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label} must be a valid ISO date")
        return None


def _taxonomy() -> dict[str, list[str]]:
    return {
        "asset_classes": sorted(ASSET_CLASSES),
        "risk_levels": sorted(RISK_LEVELS),
        "liquidity_tiers": sorted(LIQUIDITY_TIERS),
        "constraint_types": sorted(CONSTRAINT_TYPES),
        "tax_treatments": sorted(TAX_TREATMENTS),
    }


def _gap(code: str, asset_id: str | None, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "asset_id": asset_id,
        "message": message,
    }
