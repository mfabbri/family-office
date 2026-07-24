import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "cross-border-it-es/v1"
SNAPSHOT_RECORD_TYPE = "CrossBorderItEsDossier"


class CrossBorderItEsDossierError(ValueError):
    pass


def build_cross_border_it_es_dossier(
    output_path: Path,
    *,
    pension_scenario_snapshot_path: Path | None = None,
    pension_income_snapshot_path: Path | None = None,
    pension_tax_classification_snapshot_path: Path | None = None,
    spanish_pension_net_snapshot_path: Path | None = None,
    eu_pension_pro_rata_snapshot_path: Path | None = None,
    foreign_assets_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    sources = {
        "pension_scenario": _optional_snapshot(pension_scenario_snapshot_path, "pension-scenario/v1"),
        "pension_income": _optional_snapshot(pension_income_snapshot_path, "pension-income/v1"),
        "pension_tax_classification": _optional_snapshot(
            pension_tax_classification_snapshot_path, "it-es-pension-tax-classification/v1"
        ),
        "spanish_pension_net": _optional_snapshot(spanish_pension_net_snapshot_path, "spanish-pension-net-it-resident/v1"),
        "eu_pension_pro_rata": _optional_snapshot(eu_pension_pro_rata_snapshot_path, "it-es-eu-pension-pro-rata/v1"),
        "foreign_assets": _optional_snapshot(foreign_assets_snapshot_path, "it-es-foreign-assets/v1"),
    }
    if not any(item["snapshot"] is not None or item["path"] is not None for item in sources.values()):
        raise CrossBorderItEsDossierError("At least one IT-ES source snapshot is required.")
    _assert_no_personal_synthetic_pension_scenario(sources["pension_scenario"]["snapshot"])

    data_gaps: list[dict[str, Any]] = []
    for key, item in sources.items():
        if item["path"] is not None and item["snapshot"] is None:
            data_gaps.append({"code": f"missing_{key}_snapshot", "message": "Configured source snapshot is missing.", "path": str(item["path"])})
    data_gaps.extend(_source_gaps(sources))
    data_gaps.extend(_context_consistency_gaps(sources))

    context = _context(sources)
    _assert_output_scope(output_path, context, sources)
    pension_scenario = _pension_scenario(sources["pension_scenario"]["snapshot"])
    pension_flows = _pension_flows(sources["pension_income"]["snapshot"])
    pension_rights = _pension_rights(sources["eu_pension_pro_rata"]["snapshot"])
    pension_taxation = _pension_taxation(
        sources["pension_tax_classification"]["snapshot"],
        sources["spanish_pension_net"]["snapshot"],
    )
    asset_monitoring = _asset_monitoring(sources["foreign_assets"]["snapshot"])
    tax_events = _tax_events(pension_taxation, asset_monitoring)
    required_documents = _required_documents(pension_taxation, asset_monitoring)
    risks = _risks(sources, data_gaps)
    action_items = _action_items(sources, pension_taxation, asset_monitoring, data_gaps)

    status = _status(sources, data_gaps)
    core = {
        "source": {
            key: {
                "path": None if item["path"] is None else str(item["path"]),
                "schema_version": None if item["snapshot"] is None else item["snapshot"].get("schema_version"),
                "status": None if item["snapshot"] is None else item["snapshot"].get("status"),
                "content_hash": _snapshot_hash(item["snapshot"]) if item["snapshot"] is not None else None,
                "rule_pack": _provenance_block(item["snapshot"], "rule_pack"),
                "irpef_rule_pack": _provenance_block(item["snapshot"], "irpef_rule_pack"),
                "source_refs": _source_refs(item["snapshot"]),
                "limitations": _limitations(item["snapshot"]),
                "assumptions": _assumptions(item["snapshot"]),
            }
            for key, item in sources.items()
        },
        "context": context,
        "pension_scenario": pension_scenario,
        "pension_flows": pension_flows,
        "pension_rights": pension_rights,
        "pension_taxation": pension_taxation,
        "foreign_asset_monitoring": asset_monitoring,
        "tax_events": tax_events,
        "required_documents": required_documents,
        "risks": risks,
        "action_items": action_items,
        "summary": {
            "source_count": sum(1 for item in sources.values() if item["snapshot"] is not None),
            "blocking_source_count": sum(1 for item in sources.values() if _is_blocking(item["snapshot"])),
            "data_gap_count": len(data_gaps),
            "action_item_count": len(action_items),
            "review_required": True,
        },
        "data_gaps": data_gaps,
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": status,
        **core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(_semantic_core(core)),
        },
        "notes": (
            "The IT-ES cross-border dossier composes deterministic source snapshots. It does not calculate new tax, "
            "pension entitlement, withholding, foreign tax credit, asset values, recommendations or filings."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise CrossBorderItEsDossierError(f"Cannot write IT-ES cross-border dossier: {output_path}") from exc
    return snapshot


def _optional_snapshot(path: Path | None, expected_schema: str) -> dict[str, Any]:
    if path is None:
        return {"path": None, "snapshot": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"path": path, "snapshot": None}
    except json.JSONDecodeError as exc:
        raise CrossBorderItEsDossierError(f"Invalid JSON in source snapshot {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CrossBorderItEsDossierError(f"Source snapshot must contain a JSON object: {path}")
    if data.get("schema_version") != expected_schema:
        raise CrossBorderItEsDossierError(f"Unsupported source schema in {path}: {data.get('schema_version')}; expected {expected_schema}")
    return {"path": path, "snapshot": data}


def _source_gaps(sources: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for key, item in sources.items():
        snapshot = item["snapshot"]
        if snapshot is None:
            continue
        status = snapshot.get("status")
        if isinstance(status, str) and status.startswith("blocked"):
            gaps.append({"code": f"{key}_blocked", "message": "Source snapshot is blocked and cannot support a complete dossier.", "status": status})
        elif status == "partial":
            gaps.append({"code": f"{key}_partial", "message": "Source snapshot is partial and must be reviewed.", "status": status})
        for gap in _collect_nested_gaps(snapshot):
            gaps.append({"code": f"{key}.{gap.get('code', 'data_gap')}", "message": gap.get("message", "Source data gap.")})
    return gaps


def _context(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for item in sources.values():
        context = _source_context(item["snapshot"])
        if any(value is not None for value in context.values()):
            return context
    return {"household_id": None, "as_of_date": None, "tax_year": None, "fiscal_residence": None}


def _source_context(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    input_block = snapshot.get("input", {}) if isinstance(snapshot, dict) else {}
    if not isinstance(input_block, dict) or not input_block:
        return {"household_id": None, "as_of_date": None, "tax_year": None, "fiscal_residence": None}
    fiscal_residence = _fiscal_residence(input_block)
    if fiscal_residence is None and snapshot.get("schema_version") == "pension-scenario/v1":
        summary = snapshot.get("summary") if isinstance(snapshot.get("summary"), dict) else {}
        fiscal_residence = summary.get("selected_fiscal_residence")
    return {
        "household_id": input_block.get("household_id"),
        "as_of_date": input_block.get("as_of_date"),
        "tax_year": input_block.get("tax_year"),
        "fiscal_residence": fiscal_residence,
    }


def _context_consistency_gaps(sources: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    observed: dict[str, dict[str, Any]] = {}
    for key, item in sources.items():
        context = _source_context(item["snapshot"])
        for field, value in context.items():
            if value is None:
                continue
            observed.setdefault(field, {}).setdefault(str(value), []).append(key)
    gaps = []
    for field, values in observed.items():
        if len(values) > 1:
            gaps.append(
                {
                    "code": "source_context_mismatch",
                    "message": "Source snapshots have inconsistent context fields.",
                    "field": field,
                    "values": values,
                }
            )
    if not observed and any(item["snapshot"] is not None for item in sources.values()):
        gaps.append(
            {
                "code": "source_context_missing",
                "message": "No source snapshot exposes enough context to verify household, tax year, as-of date or residence.",
            }
        )
    return gaps


def _fiscal_residence(input_block: dict[str, Any]) -> str | None:
    if isinstance(input_block.get("taxpayer"), dict):
        return input_block["taxpayer"].get("fiscal_residence")
    if isinstance(input_block.get("recipient"), dict):
        return input_block["recipient"].get("fiscal_residence")
    return input_block.get("resident_country")


def _pension_scenario(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if snapshot is None:
        return {"status": "missing", "selected_scenario_id": None, "selected_scenario": None}
    selected = snapshot.get("selected_scenario") if isinstance(snapshot.get("selected_scenario"), dict) else None
    return {
        "status": snapshot.get("status"),
        "selected_scenario_id": snapshot.get("selected_scenario_id"),
        "selected_scenario": selected,
        "summary": snapshot.get("summary"),
        "data_gaps": snapshot.get("data_gaps", []),
        "provenance": [] if selected is None else selected.get("provenance", []),
    }


def _pension_flows(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if snapshot is None:
        return {"status": "missing", "streams": [], "summary": None}
    streams = []
    for item in snapshot.get("income_streams", []):
        if isinstance(item, dict):
            streams.append(
                {
                    "stream_id": item.get("stream_id"),
                    "country": item.get("country"),
                    "status": item.get("status"),
                    "gross": item.get("gross") if isinstance(item.get("gross"), dict) else {
                        "annual_amount": item.get("gross_annual_amount"),
                        "currency": item.get("currency"),
                    },
                    "confidence": item.get("confidence"),
                    "data_gaps": item.get("data_gaps", []),
                }
            )
    return {"status": snapshot.get("status"), "streams": streams, "summary": snapshot.get("summary")}


def _pension_rights(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if snapshot is None:
        return {"status": "missing", "source_schema": None, "spanish_entitlement": None, "spanish_pro_rata_pension": None}
    return {
        "status": snapshot.get("status"),
        "source_schema": snapshot.get("schema_version"),
        "retirement_date": snapshot.get("retirement_date"),
        "spanish_entitlement": snapshot.get("spanish_entitlement"),
        "spanish_pro_rata_pension": snapshot.get("spanish_pro_rata_pension"),
        "warnings": snapshot.get("warnings", []),
    }


def _pension_taxation(classification: dict[str, Any] | None, net: dict[str, Any] | None) -> dict[str, Any]:
    classifications = []
    if classification is not None:
        for item in classification.get("classifications", []):
            if not isinstance(item, dict):
                continue
            classifications.append(
                {
                    "stream_id": item.get("stream_id"),
                    "status": item.get("classification_status"),
                    "taxing_power": item.get("taxing_power"),
                    "treaty_article": item.get("treaty_article"),
                    "rule_id": item.get("rule_id"),
                    "required_documents": item.get("required_documents", []),
                    "data_gaps": item.get("data_gaps", []),
                }
            )
    net_streams = []
    if net is not None:
        for item in net.get("streams", []):
            if isinstance(item, dict):
                net_streams.append(
                    {
                        "stream_id": item.get("stream_id"),
                        "status": item.get("status"),
                        "gross": item.get("gross"),
                        "spanish_tax": item.get("spanish_tax"),
                        "italian_tax": item.get("italian_tax"),
                        "foreign_tax_credit": item.get("foreign_tax_credit"),
                        "net": item.get("net"),
                        "data_gaps": item.get("data_gaps", []),
                    }
                )
    return {
        "classification_status": None if classification is None else classification.get("status"),
        "net_status": None if net is None else net.get("status"),
        "classifications": classifications,
        "net_streams": net_streams,
    }


def _asset_monitoring(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if snapshot is None:
        return {"status": "missing", "totals": None, "assets": []}
    assets = []
    for item in snapshot.get("assets", []):
        if isinstance(item, dict):
            assets.append(
                {
                    "asset_id": item.get("asset_id"),
                    "asset_type": item.get("asset_type"),
                    "jurisdiction": item.get("jurisdiction"),
                    "rw_monitoring": item.get("rw_monitoring"),
                    "wealth_tax": item.get("wealth_tax"),
                    "required_documents": item.get("required_documents", []),
                    "tax_events": item.get("tax_events", []),
                    "data_gaps": item.get("data_gaps", []),
                }
            )
    return {"status": snapshot.get("status"), "totals": snapshot.get("totals"), "assets": assets}


def _tax_events(pension_taxation: dict[str, Any], asset_monitoring: dict[str, Any]) -> list[dict[str, Any]]:
    events = []
    for stream in pension_taxation["net_streams"]:
        spanish_tax = stream.get("spanish_tax") or {}
        if spanish_tax.get("withheld") not in (None, "0.00"):
            events.append({"source": "spanish_pension_net", "stream_id": stream["stream_id"], "event_type": "spanish_tax_withheld", "amount": spanish_tax.get("withheld")})
    for asset in asset_monitoring["assets"]:
        for event in asset.get("tax_events", []):
            if isinstance(event, dict):
                events.append({"source": "it_es_foreign_assets", "asset_id": asset.get("asset_id"), **event})
    return events


def _required_documents(pension_taxation: dict[str, Any], asset_monitoring: dict[str, Any]) -> list[dict[str, Any]]:
    documents: dict[tuple[str, str], dict[str, Any]] = {}
    for item in pension_taxation["classifications"]:
        for doc in item.get("required_documents", []):
            documents.setdefault(("pension", doc), {"area": "pension", "document_type": doc, "source_ids": []})["source_ids"].append(item.get("stream_id"))
    for asset in asset_monitoring["assets"]:
        for doc in asset.get("required_documents", []):
            documents.setdefault(("foreign_assets", doc), {"area": "foreign_assets", "document_type": doc, "source_ids": []})["source_ids"].append(asset.get("asset_id"))
    return sorted(documents.values(), key=lambda item: (item["area"], item["document_type"]))


def _risks(sources: dict[str, dict[str, Any]], data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    risks = [{"code": "professional_review_required", "severity": "high", "message": "Cross-border tax, pension and asset monitoring conclusions require professional review before filing or decisions."}]
    if data_gaps:
        risks.append({"code": "open_data_gaps", "severity": "medium", "message": "One or more source snapshots contain gaps or blocked sections."})
    if sources["foreign_assets"]["snapshot"] is None:
        risks.append({"code": "foreign_asset_monitoring_missing", "severity": "medium", "message": "No IT-ES foreign asset monitoring snapshot was provided."})
    if sources["spanish_pension_net"]["snapshot"] is None and sources["eu_pension_pro_rata"]["snapshot"] is not None:
        risks.append({"code": "pension_tax_net_missing", "severity": "medium", "message": "Spanish pension entitlement exists but net tax treatment snapshot is missing."})
    return risks


def _action_items(
    sources: dict[str, dict[str, Any]],
    pension_taxation: dict[str, Any],
    asset_monitoring: dict[str, Any],
    data_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions = [{"action_id": "professional_cross_border_review", "area": "review", "priority": "high", "message": "Review dossier with a qualified tax/pension professional before filing or taking action."}]
    if data_gaps:
        actions.append({"action_id": "resolve_source_data_gaps", "area": "data_quality", "priority": "high", "message": "Resolve source data gaps before relying on the dossier."})
    if not pension_taxation["classifications"] and sources["pension_tax_classification"]["snapshot"] is None:
        actions.append({"action_id": "build_pension_tax_classification", "area": "pension_tax", "priority": "medium", "message": "Build it-es-pension-tax-classification/v1 for Spanish pension streams."})
    if not asset_monitoring["assets"] and sources["foreign_assets"]["snapshot"] is None:
        actions.append({"action_id": "build_foreign_asset_monitoring", "area": "foreign_assets", "priority": "medium", "message": "Build it-es-foreign-assets/v1 for Spanish assets."})
    return actions


def _status(sources: dict[str, dict[str, Any]], data_gaps: list[dict[str, Any]]) -> str:
    if any(_is_blocking(item["snapshot"]) for item in sources.values()):
        return "blocked_source"
    if any(gap.get("code") == "source_context_mismatch" for gap in data_gaps):
        return "blocked_source"
    if data_gaps:
        return "partial"
    return "complete"


def _is_blocking(snapshot: dict[str, Any] | None) -> bool:
    return isinstance(snapshot, dict) and isinstance(snapshot.get("status"), str) and snapshot["status"].startswith("blocked")


def _snapshot_hash(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _provenance_block(snapshot: dict[str, Any] | None, field: str) -> dict[str, Any] | None:
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get(field), dict):
        return None
    block = snapshot[field]
    return {
        key: block.get(key)
        for key in ("rule_pack_id", "schema_version", "content_hash", "sha256", "applied_rule_id", "status")
        if key in block
    }


def _source_refs(snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return []
    refs = []
    for block_name in ("rule_pack", "irpef_rule_pack"):
        block = snapshot.get(block_name)
        if isinstance(block, dict) and isinstance(block.get("source_refs"), list):
            refs.extend(ref for ref in block["source_refs"] if isinstance(ref, dict))
    if isinstance(snapshot.get("sources"), list):
        refs.extend(ref for ref in snapshot["sources"] if isinstance(ref, dict))
    return refs


def _limitations(snapshot: dict[str, Any] | None) -> list[Any]:
    if not isinstance(snapshot, dict):
        return []
    items = []
    for block_name in ("rule_pack", "irpef_rule_pack"):
        block = snapshot.get(block_name)
        if isinstance(block, dict) and isinstance(block.get("limitations"), list):
            items.extend(block["limitations"])
    return items


def _assumptions(snapshot: dict[str, Any] | None) -> list[Any]:
    if not isinstance(snapshot, dict):
        return []
    assumptions = snapshot.get("assumptions")
    return assumptions if isinstance(assumptions, list) else []


def _content_hash(data: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _semantic_core(core: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(core))
    for item in result["source"].values():
        item["path"] = "<source>"
    return result


def _collect_nested_gaps(value: Any) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    if isinstance(value, dict):
        raw = value.get("data_gaps")
        if isinstance(raw, list):
            gaps.extend(gap for gap in raw if isinstance(gap, dict))
        for child_key, child in value.items():
            if child_key != "data_gaps":
                gaps.extend(_collect_nested_gaps(child))
    elif isinstance(value, list):
        for item in value:
            gaps.extend(_collect_nested_gaps(item))
    return gaps


def _assert_output_scope(output_path: Path, context: dict[str, Any], sources: dict[str, dict[str, Any]]) -> None:
    workspace_root = Path(__file__).resolve().parents[4] / "family-office-workspace"
    try:
        output_path.resolve().relative_to(workspace_root.resolve())
        return
    except ValueError:
        pass
    if _all_loaded_sources_are_examples(sources):
        return
    household_id = context.get("household_id")
    if household_id is not None and str(household_id).lower().startswith("synthetic"):
        return
    raise CrossBorderItEsDossierError("Personal cross-border dossier output must stay inside family-office-workspace.")


def _assert_no_personal_synthetic_pension_scenario(snapshot: dict[str, Any] | None) -> None:
    if not isinstance(snapshot, dict):
        return
    input_block = snapshot.get("input") if isinstance(snapshot.get("input"), dict) else {}
    household_id = input_block.get("household_id")
    if isinstance(household_id, str) and household_id.lower().startswith("synthetic"):
        return
    selected = snapshot.get("selected_scenario") if isinstance(snapshot.get("selected_scenario"), dict) else {}
    sources = []
    if isinstance(snapshot.get("sources"), list):
        sources.extend(source for source in snapshot["sources"] if isinstance(source, dict))
    if isinstance(selected.get("provenance"), list):
        sources.extend(source for source in selected["provenance"] if isinstance(source, dict))
    if any(source.get("type") in {"synthetic", "synthetic_fixture", "demo_fixture"} for source in sources):
        raise CrossBorderItEsDossierError("Synthetic pension scenarios cannot be used in a personal cross-border dossier.")


def _all_loaded_sources_are_examples(sources: dict[str, dict[str, Any]]) -> bool:
    engine_examples = Path(__file__).resolve().parents[3] / "examples"
    loaded_paths = [item["path"] for item in sources.values() if item["snapshot"] is not None and item["path"] is not None]
    if not loaded_paths:
        return True
    for path in loaded_paths:
        try:
            path.resolve().relative_to(engine_examples.resolve())
        except ValueError:
            return False
    return True
