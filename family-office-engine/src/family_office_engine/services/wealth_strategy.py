import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "wealth-strategy/v1"
INPUT_SCHEMA_VERSION = "wealth-strategy-input/v1"
INPUT_RECORD_TYPE = "WealthStrategyInput"
SNAPSHOT_RECORD_TYPE = "WealthStrategySnapshot"
CENT = Decimal("0.01")
SCORE_QUANT = Decimal("0.01")

SOURCE_SCHEMAS = {
    "planning_goals": "planning-goals/v1",
    "liquidity_plan": "liquidity-plan/v1",
    "decumulation_strategy": "decumulation-strategy/v1",
    "pension_contribution_options": "pension-contribution-options/v1",
    "tax_aware_portfolio": "tax-aware-portfolio/v1",
    "cross_border_it_es": "cross-border-it-es/v1",
    "real_estate_plan": "real-estate-plan/v1",
    "protection_gap": "protection-gap/v1",
    "estate_plan": "estate-plan/v2",
    "work_exit": "work-exit-feasibility/v1",
    "investment_opportunity_comparison": "investment-opportunity-comparison/v1",
}
SCORE_KEYS = ("liquidity", "retirement", "tax_efficiency", "protection", "succession", "cross_border", "reversibility")
REVERSIBILITY_SCORE = {"low": 1, "medium": 3, "high": 5}


class WealthStrategyError(ValueError):
    pass


def build_wealth_strategy(
    input_path: Path,
    output_path: Path,
    *,
    planning_goals_snapshot_path: Path | None = None,
    liquidity_plan_snapshot_path: Path | None = None,
    decumulation_strategy_snapshot_path: Path | None = None,
    pension_contribution_options_snapshot_path: Path | None = None,
    tax_aware_portfolio_snapshot_path: Path | None = None,
    cross_border_it_es_snapshot_path: Path | None = None,
    real_estate_plan_snapshot_path: Path | None = None,
    protection_gap_snapshot_path: Path | None = None,
    estate_plan_snapshot_path: Path | None = None,
    work_exit_snapshot_path: Path | None = None,
    investment_opportunity_comparison_snapshot_paths: list[Path] | None = None,
) -> dict[str, Any]:
    data = _read_json(input_path, "wealth strategy input")
    sources = {
        "planning_goals": _optional_snapshot(planning_goals_snapshot_path, SOURCE_SCHEMAS["planning_goals"]),
        "liquidity_plan": _optional_snapshot(liquidity_plan_snapshot_path, SOURCE_SCHEMAS["liquidity_plan"]),
        "decumulation_strategy": _optional_snapshot(decumulation_strategy_snapshot_path, SOURCE_SCHEMAS["decumulation_strategy"]),
        "pension_contribution_options": _optional_snapshot(
            pension_contribution_options_snapshot_path, SOURCE_SCHEMAS["pension_contribution_options"]
        ),
        "tax_aware_portfolio": _optional_snapshot(tax_aware_portfolio_snapshot_path, SOURCE_SCHEMAS["tax_aware_portfolio"]),
        "cross_border_it_es": _optional_snapshot(cross_border_it_es_snapshot_path, SOURCE_SCHEMAS["cross_border_it_es"]),
        "real_estate_plan": _optional_snapshot(real_estate_plan_snapshot_path, SOURCE_SCHEMAS["real_estate_plan"]),
        "protection_gap": _optional_snapshot(protection_gap_snapshot_path, SOURCE_SCHEMAS["protection_gap"]),
        "estate_plan": _optional_snapshot(estate_plan_snapshot_path, SOURCE_SCHEMAS["estate_plan"]),
        "work_exit": _optional_snapshot(work_exit_snapshot_path, SOURCE_SCHEMAS["work_exit"]),
        "investment_opportunity_comparison": _optional_investment_comparison_snapshots(
            investment_opportunity_comparison_snapshot_paths or []
        ),
    }
    errors: list[str] = []
    data_gaps: list[dict[str, Any]] = []
    _validate_input(data, errors, data_gaps)
    if errors:
        raise WealthStrategyError("; ".join(errors))

    weights = _weights(data["comparison_weights"])
    packages = [
        _package(item, index, weights, sources, data.get("incompatibilities", []), data_gaps)
        for index, item in enumerate(data["packages"])
    ]
    ranking = _ranking(packages)
    automatic_ranking_produced = _automatic_ranking_allowed(packages, ranking)
    status = _status(packages, sources, data_gaps)
    core = {
        "source": {"type": "wealth-strategy-input-json", "path": str(input_path), "snapshots": _source_summary(sources)},
        "household": {"household_id": data["household_id"], "as_of_date": data["as_of_date"]},
        "base_currency": data["base_currency"],
        "comparison_weights": {key: _format_score(value) for key, value in weights.items()},
        "packages": packages,
        "ranking": ranking,
        "summary": {
            "package_count": len(packages),
            "comparable_package_count": sum(1 for item in packages if item["status"] in {"complete", "partial"}),
            "blocked_package_count": sum(1 for item in packages if item["status"].startswith("blocked")),
            "data_gap_count": len(data_gaps),
            "automatic_ranking_produced": automatic_ranking_produced,
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
            "Wealth strategy V1 composes deterministic V4 snapshots into comparable declared packages. "
            "It does not calculate new tax, pension, investment returns, legal effects or recommendations. "
            "Investment personal utility is an explicit non-taxable annotation, never a cash-flow input."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise WealthStrategyError(f"Cannot write wealth strategy snapshot: {output_path}") from exc
    return snapshot


def _validate_input(data: dict[str, Any], errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if data.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append(f"Unsupported wealth strategy schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported wealth strategy record type: {data.get('record_type')}")
    _required_string(data, "household_id", errors)
    _required_string(data, "as_of_date", errors)
    base_currency = _required_string(data, "base_currency", errors)
    if base_currency and (len(base_currency) != 3 or base_currency.upper() != base_currency):
        errors.append("base_currency must be an ISO-4217 uppercase code")
    weights = data.get("comparison_weights")
    if not isinstance(weights, dict):
        errors.append("comparison_weights is required")
    else:
        for key in SCORE_KEYS:
            if key not in weights:
                errors.append(f"comparison_weights.{key} is required")
            else:
                value = _decimal(weights[key], f"comparison_weights.{key}")
                if value < 0:
                    errors.append(f"comparison_weights.{key} must be greater than or equal to 0")
    packages = data.get("packages")
    if not isinstance(packages, list) or not 2 <= len(packages) <= 4:
        errors.append("packages must contain 2 to 4 strategy packages")
    elif not all(isinstance(item, dict) for item in packages):
        errors.append("packages must contain objects")
    _validate_declared_gaps(data.get("data_gaps", []), errors, data_gaps)


def _package(
    item: dict[str, Any],
    index: int,
    weights: dict[str, Decimal],
    sources: dict[str, dict[str, Any]],
    incompatibilities: list[dict[str, Any]],
    global_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    prefix = f"packages[{index}]"
    package_id = _required_item_text(item, "package_id", prefix)
    components = _components(item.get("components", []), package_id, sources)
    package_gaps = [gap for component in components for gap in component["data_gaps"]]
    package_gaps.extend(_incompatibility_gaps(package_id, components, incompatibilities))
    personal_utility, personal_utility_gaps = _personal_utility(
        item.get("personal_utility"), any(component["source_key"] == "investment_opportunity_comparison" for component in components)
    )
    package_gaps.extend(personal_utility_gaps)
    global_gaps.extend({"package_id": package_id, **gap} for gap in package_gaps)
    declared_scores = _declared_scores(item.get("declared_scores", {}), prefix, item.get("reversibility"))
    weighted_score = _weighted_score(declared_scores, weights, package_gaps)
    return {
        "package_id": package_id,
        "label": item.get("label") or package_id,
        "status": _package_status(components, package_gaps),
        "components": components,
        "declared_scores": declared_scores,
        "weighted_score": _format_score(weighted_score),
        "implementation_plan": {
            "actions_90_days": _non_empty_string_list(item.get("implementation", {}).get("actions_90_days"), f"{prefix}.implementation.actions_90_days"),
            "actions_180_days": _non_empty_string_list(item.get("implementation", {}).get("actions_180_days"), f"{prefix}.implementation.actions_180_days"),
        },
        "costs": _costs(item.get("costs", []), package_id),
        "dependencies": _string_list(item.get("dependencies", []), f"{prefix}.dependencies"),
        "reversibility": item.get("reversibility") or "unknown",
        "personal_utility": personal_utility,
        "controls": _non_empty_string_list(item.get("controls"), f"{prefix}.controls"),
        "risks": _non_empty_string_list(item.get("risks"), f"{prefix}.risks"),
        "adverse_scenarios": _non_empty_string_list(item.get("adverse_scenarios"), f"{prefix}.adverse_scenarios"),
        "data_gaps": package_gaps,
    }


def _components(raw_components: Any, package_id: str, sources: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(raw_components, list) or not raw_components:
        raise WealthStrategyError(f"{package_id}.components must contain at least one component")
    result = []
    for index, item in enumerate(raw_components):
        if not isinstance(item, dict):
            raise WealthStrategyError(f"{package_id}.components[{index}] must be an object")
        component_id = _required_item_text(item, "component_id", f"{package_id}.components[{index}]")
        source_key = _required_item_text(item, "source_key", f"{package_id}.components[{index}]")
        if source_key not in SOURCE_SCHEMAS:
            raise WealthStrategyError(f"{component_id}.source_key must be one of {sorted(SOURCE_SCHEMAS)}")
        selector = item.get("selector", {})
        if source_key == "investment_opportunity_comparison":
            source, selector = _investment_comparison_source(sources[source_key], selector)
        else:
            source = sources[source_key]
        evidence, gaps = _component_evidence(component_id, source_key, selector, source)
        result.append(
            {
                "component_id": component_id,
                "source_key": source_key,
                "source_status": None if source["snapshot"] is None else source["snapshot"].get("status"),
                "source_hash": _snapshot_hash(source["snapshot"]) if source["snapshot"] is not None else None,
                "evidence": evidence,
                "data_gaps": gaps,
            }
        )
    return result


def _component_evidence(component_id: str, source_key: str, selector: Any, source: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    gaps = []
    snapshot = source["snapshot"]
    if snapshot is None:
        return None, [{"code": "missing_source_snapshot", "component_id": component_id, "source_key": source_key, "message": "Required source snapshot is missing."}]
    if str(snapshot.get("status", "")).startswith("blocked"):
        gaps.append({"code": "blocked_source_snapshot", "component_id": component_id, "source_key": source_key, "message": "Required source snapshot is blocked."})
    elif snapshot.get("status") == "partial":
        gaps.append({"code": "partial_source_snapshot", "component_id": component_id, "source_key": source_key, "message": "Required source snapshot is partial and needs review."})
    gaps.extend({"code": f"source.{gap.get('code', 'data_gap')}", "component_id": component_id, "source_key": source_key, "message": gap.get("message", "Source data gap.")} for gap in _collect_nested_gaps(snapshot))
    if not isinstance(selector, dict) or not selector:
        return _evidence_summary(snapshot), gaps
    if "collection" in selector:
        evidence = _select_collection_item(snapshot, selector)
        if evidence is None:
            gaps.append({"code": "missing_selected_option", "component_id": component_id, "source_key": source_key, "selector": selector, "message": "Selected source option was not found."})
            return None, gaps
        return _evidence_summary(evidence), gaps
    if "path" in selector:
        value = _path_value(snapshot, str(selector["path"]))
        if selector.get("exists") is True:
            if value is None:
                gaps.append({"code": "missing_selected_value", "component_id": component_id, "source_key": source_key, "selector": selector, "message": "Selected source value was not found."})
            return {"path": selector["path"], "value": value}, gaps
        if "equals" in selector and value != selector["equals"]:
            gaps.append({"code": "selected_value_mismatch", "component_id": component_id, "source_key": source_key, "selector": selector, "actual": value, "message": "Selected source value does not match the package expectation."})
        return {"path": selector["path"], "value": value}, gaps
    raise WealthStrategyError(f"{component_id}.selector must use collection or path")


def _investment_comparison_source(source: dict[str, Any], selector: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(selector, dict):
        raise WealthStrategyError("investment opportunity comparison selector must be an object")
    comparison_id = selector.get("comparison_id")
    if not isinstance(comparison_id, str) or not comparison_id.strip():
        raise WealthStrategyError("investment opportunity comparison selector.comparison_id is required")
    snapshot = source.get("snapshots", {}).get(comparison_id)
    if snapshot is None:
        return {"path": None, "snapshot": None}, {}
    scenario_type = selector.get("scenario_type")
    if scenario_type is None:
        return {"path": source["paths"].get(comparison_id), "snapshot": snapshot}, {}
    if scenario_type not in {"base", "upside", "adverse"}:
        raise WealthStrategyError("investment opportunity comparison selector.scenario_type must be base, upside or adverse")
    view = dict(snapshot)
    primary = snapshot.get("primary")
    view["scenarios"] = primary.get("scenarios", []) if isinstance(primary, dict) else []
    return (
        {"path": source["paths"].get(comparison_id), "snapshot": view},
        {"collection": "scenarios", "id_field": "scenario_type", "id": scenario_type},
    )


def _select_collection_item(snapshot: dict[str, Any], selector: dict[str, Any]) -> dict[str, Any] | None:
    collection = snapshot.get(selector.get("collection"))
    if not isinstance(collection, list):
        return None
    id_field = selector.get("id_field")
    expected = selector.get("id")
    for item in collection:
        if isinstance(item, dict) and item.get(id_field) == expected:
            return item
    return None


def _evidence_summary(value: dict[str, Any]) -> dict[str, Any]:
    summary_keys = (
        "option_id",
        "alternative_id",
        "scenario_id",
        "strategy",
        "status",
        "label",
        "weighted_score",
        "rank",
        "totals",
        "summary",
        "failure_reasons",
        "reserve_conflicts",
        "operational_flags",
        "return",
        "risk",
        "liquidity",
        "management_burden",
    )
    return {key: value.get(key) for key in summary_keys if key in value}


def _declared_scores(value: Any, prefix: str, reversibility: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise WealthStrategyError(f"{prefix}.declared_scores is required")
    scores = {}
    for key in SCORE_KEYS:
        raw_score = value.get(key)
        if key == "reversibility" and raw_score is None:
            raw_score = REVERSIBILITY_SCORE.get(reversibility)
        score = _decimal(raw_score, f"{prefix}.declared_scores.{key}")
        if score < 0 or score > 5:
            raise WealthStrategyError(f"{prefix}.declared_scores.{key} must be between 0 and 5")
        scores[key] = _format_score(score)
    return scores


def _weighted_score(scores: dict[str, str], weights: dict[str, Decimal], gaps: list[dict[str, Any]]) -> Decimal:
    raw = sum((_decimal(scores[key], key) * weights[key] for key in SCORE_KEYS), Decimal("0.00"))
    penalty = Decimal("0.50") * sum(1 for gap in gaps if gap["code"] in {"partial_source_snapshot", "source.data_gap"})
    penalty += Decimal("1.00") * sum(1 for gap in gaps if gap["code"] in {"missing_source_snapshot", "blocked_source_snapshot", "missing_selected_option", "selected_value_mismatch", "incompatible_components"})
    score = raw - penalty
    return max(score, Decimal("0.00"))


def _weights(value: dict[str, Any]) -> dict[str, Decimal]:
    weights = {key: _decimal(value[key], f"comparison_weights.{key}") for key in SCORE_KEYS}
    total = sum(weights.values(), Decimal("0.00"))
    if total <= 0:
        raise WealthStrategyError("comparison_weights total must be greater than 0")
    return {key: weights[key] / total for key in SCORE_KEYS}


def _incompatibility_gaps(package_id: str, components: list[dict[str, Any]], incompatibilities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    component_ids = {item["component_id"] for item in components}
    gaps = []
    for item in incompatibilities:
        ids = set(item.get("component_ids", [])) if isinstance(item, dict) else set()
        if len(ids) >= 2 and ids.issubset(component_ids):
            gaps.append(
                {
                    "code": "incompatible_components",
                    "package_id": package_id,
                    "rule_code": item.get("code"),
                    "component_ids": sorted(ids),
                    "message": item.get("message", "Package contains incompatible components."),
                }
            )
    return gaps


def _package_status(components: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> str:
    gap_codes = {gap["code"] for gap in gaps}
    if gap_codes & {"missing_source_snapshot", "blocked_source_snapshot", "missing_selected_option", "selected_value_mismatch", "incompatible_components"}:
        return "blocked_source"
    if gaps or any(component["source_status"] == "partial" for component in components):
        return "partial"
    return "complete"


def _status(packages: list[dict[str, Any]], sources: dict[str, dict[str, Any]], data_gaps: list[dict[str, Any]]) -> str:
    if not any(_source_available(item) for item in sources.values()):
        return "blocked_missing_sources"
    if sum(1 for package in packages if package["status"] in {"complete", "partial"}) < 2:
        return "blocked_insufficient_comparable_packages"
    if any(package["status"].startswith("blocked") for package in packages):
        return "partial"
    if data_gaps:
        return "partial"
    return "complete"


def _source_available(source: dict[str, Any]) -> bool:
    if "snapshots" in source:
        return bool(source["snapshots"])
    return source["snapshot"] is not None


def _ranking(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(packages, key=lambda item: (-_decimal(item["weighted_score"], "weighted_score"), item["package_id"]))
    result = []
    previous_score: Decimal | None = None
    rank = 0
    for index, item in enumerate(ranked):
        score = _decimal(item["weighted_score"], "weighted_score")
        if score != previous_score:
            rank = index + 1
            previous_score = score
        tied_with = [candidate["package_id"] for candidate in ranked if candidate["package_id"] != item["package_id"] and candidate["weighted_score"] == item["weighted_score"]]
        result.append(
            {
            "rank": rank,
            "package_id": item["package_id"],
            "status": item["status"],
            "weighted_score": item["weighted_score"],
            "tied_with_package_ids": tied_with,
            "review_required": True,
            }
        )
    return result


def _automatic_ranking_allowed(packages: list[dict[str, Any]], ranking: list[dict[str, Any]]) -> bool:
    critical_codes = {
        "source.missing_tax_classification",
        "source.missing_activity_classification",
        "source.missing_benchmark",
        "source.missing_household_constraints",
        "source.incomplete_household_constraints",
        "missing_personal_utility",
    }
    return not any(
        set(gap.get("code", "") for gap in package["data_gaps"]) & critical_codes
        for package in packages
    ) and not any(item["tied_with_package_ids"] for item in ranking)


def _personal_utility(value: Any, required: bool) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if value is None:
        if required:
            return None, [{"code": "missing_personal_utility", "message": "Investment packages must declare personal utility or an explicit zero value."}]
        return None, []
    if not isinstance(value, dict):
        raise WealthStrategyError("personal_utility must be an object")
    allowed = {"annual_economic_benefit", "source"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise WealthStrategyError(f"personal_utility has unknown fields: {', '.join(unknown)}")
    benefit = _decimal(value.get("annual_economic_benefit"), "personal_utility.annual_economic_benefit")
    if benefit < 0:
        raise WealthStrategyError("personal_utility.annual_economic_benefit must be greater than or equal to 0")
    source = _required_item_text(value, "source", "personal_utility")
    return {
        "annual_economic_benefit": _format_money(benefit),
        "source": source,
        "tax_treatment": "not_taxable_cash_flow",
    }, []


def _costs(value: Any, package_id: str) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise WealthStrategyError(f"{package_id}.costs must be a list")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise WealthStrategyError(f"{package_id}.costs[{index}] must be an object")
        amount = _decimal(item.get("amount"), f"{package_id}.costs[{index}].amount")
        if amount < 0:
            raise WealthStrategyError(f"{package_id}.costs[{index}].amount must be greater than or equal to 0")
        result.append(
            {
                "code": item.get("code") or f"cost_{index + 1}",
                "timing": item.get("timing") or "unspecified",
                "amount": _format_money(amount),
                "currency": item.get("currency"),
            }
        )
    return result


def _source_summary(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, item in sources.items():
        if "snapshots" in item:
            result[key] = [
                {
                    "comparison_id": comparison_id,
                    "path": str(item["paths"][comparison_id]),
                    "schema_version": snapshot.get("schema_version"),
                    "status": snapshot.get("status"),
                    "content_hash": _snapshot_hash(snapshot),
                }
                for comparison_id, snapshot in item["snapshots"].items()
            ]
            continue
        result[key] = {
            "path": None if item["path"] is None else str(item["path"]),
            "schema_version": None if item["snapshot"] is None else item["snapshot"].get("schema_version"),
            "status": None if item["snapshot"] is None else item["snapshot"].get("status"),
            "content_hash": _snapshot_hash(item["snapshot"]) if item["snapshot"] is not None else None,
        }
    return result


def _optional_snapshot(path: Path | None, expected_schema: str) -> dict[str, Any]:
    if path is None:
        return {"path": None, "snapshot": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"path": path, "snapshot": None}
    except json.JSONDecodeError as exc:
        raise WealthStrategyError(f"Invalid JSON in source snapshot {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise WealthStrategyError(f"Source snapshot must contain a JSON object: {path}")
    if data.get("schema_version") != expected_schema:
        raise WealthStrategyError(f"Unsupported source schema in {path}: {data.get('schema_version')}; expected {expected_schema}")
    return {"path": path, "snapshot": data}


def _optional_investment_comparison_snapshots(paths: list[Path]) -> dict[str, Any]:
    snapshots: dict[str, dict[str, Any]] = {}
    source_paths: dict[str, Path] = {}
    for path in paths:
        source = _optional_snapshot(path, SOURCE_SCHEMAS["investment_opportunity_comparison"])
        snapshot = source["snapshot"]
        if snapshot is None:
            continue
        comparison_id = snapshot.get("comparison_id")
        if not isinstance(comparison_id, str) or not comparison_id.strip():
            raise WealthStrategyError(f"Investment comparison snapshot needs comparison_id: {path}")
        if comparison_id in snapshots:
            raise WealthStrategyError(f"Duplicate investment comparison_id: {comparison_id}")
        snapshots[comparison_id] = snapshot
        source_paths[comparison_id] = path
    return {"paths": source_paths, "snapshots": snapshots}


def _collect_nested_gaps(value: Any) -> list[dict[str, Any]]:
    gaps = []
    if isinstance(value, dict):
        raw_gaps = value.get("data_gaps")
        if isinstance(raw_gaps, list):
            gaps.extend(gap for gap in raw_gaps if isinstance(gap, dict))
        for child in value.values():
            gaps.extend(_collect_nested_gaps(child))
    elif isinstance(value, list):
        for child in value:
            gaps.extend(_collect_nested_gaps(child))
    return gaps


def _path_value(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WealthStrategyError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WealthStrategyError(f"Invalid JSON in {label} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise WealthStrategyError(f"{label} must contain a JSON object.")
    return data


def _required_string(data: dict[str, Any], field: str, errors: list[str]) -> str | None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required")
        return None
    return value


def _required_item_text(data: dict[str, Any], field: str, prefix: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise WealthStrategyError(f"{prefix}.{field} is required")
    return value


def _validate_declared_gaps(raw_gaps: Any, errors: list[str], data_gaps: list[dict[str, Any]]) -> None:
    if raw_gaps in (None, ""):
        return
    if not isinstance(raw_gaps, list):
        errors.append("data_gaps must be a list")
        return
    for index, gap in enumerate(raw_gaps):
        if not isinstance(gap, dict):
            errors.append(f"data_gaps[{index}] must be an object")
        elif not gap.get("code"):
            errors.append(f"data_gaps[{index}].code is required")
        else:
            data_gaps.append(gap)


def _non_empty_string_list(value: Any, label: str) -> list[str]:
    result = _string_list(value, label)
    if not result:
        raise WealthStrategyError(f"{label} must contain at least one item")
    return result


def _string_list(value: Any, label: str) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise WealthStrategyError(f"{label} must contain strings")
    return value


def _decimal(value: Any, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise WealthStrategyError(f"{label} must be a decimal") from exc


def _semantic_core(core: dict[str, Any]) -> dict[str, Any]:
    semantic = json.loads(json.dumps(core))
    source = semantic.get("source")
    if isinstance(source, dict):
        source.pop("path", None)
        snapshots = source.get("snapshots")
        if isinstance(snapshots, dict):
            for item in snapshots.values():
                if isinstance(item, dict):
                    item.pop("path", None)
        elif isinstance(snapshots, list):
            for item in snapshots:
                if isinstance(item, dict):
                    item.pop("path", None)
    return semantic


def _snapshot_hash(snapshot: dict[str, Any] | None) -> str | None:
    if snapshot is None:
        return None
    reproducibility = snapshot.get("reproducibility")
    if isinstance(reproducibility, dict) and isinstance(reproducibility.get("content_hash"), str):
        return reproducibility["content_hash"]
    return _content_hash(snapshot)


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _format_score(value: Decimal) -> str:
    return str(value.quantize(SCORE_QUANT, rounding=ROUND_HALF_UP))
