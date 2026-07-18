import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "decision-score/v1"
INPUT_RECORD_TYPE = "DecisionScoreInput"
SNAPSHOT_RECORD_TYPE = "DecisionScoreSnapshot"
POLICY_SCHEMA_VERSION = "decision-score-policy/v1"
DECISION_SCENARIO_SCHEMA_VERSION = "decision-scenario/v2"
SENSITIVITY_SCHEMA_VERSION = "sensitivity-analysis/v1"


class DecisionScoreError(ValueError):
    pass


def build_decision_score(
    decision_scenario_snapshot_path: Path,
    sensitivity_analysis_snapshot_path: Path,
    scoring_input_path: Path,
    policy_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    decision_scenario = _read_schema_snapshot(
        decision_scenario_snapshot_path,
        "decision scenario snapshot",
        DECISION_SCENARIO_SCHEMA_VERSION,
    )
    sensitivity_analysis = _read_schema_snapshot(
        sensitivity_analysis_snapshot_path,
        "sensitivity analysis snapshot",
        SENSITIVITY_SCHEMA_VERSION,
    )
    scoring_input = _read_scoring_input(scoring_input_path)
    policy = _read_policy(policy_path)
    metric_definitions = {metric["metric_id"]: metric for metric in policy["metrics"]}

    data_gaps: list[dict[str, Any]] = []
    data_gaps.extend(_source_gaps("decision_scenario", decision_scenario))
    data_gaps.extend(_source_gaps("sensitivity_analysis", sensitivity_analysis))
    weights = _weights(scoring_input, metric_definitions, data_gaps)
    alternatives = [
        _score_alternative(alternative, sensitivity_analysis, metric_definitions, weights, data_gaps)
        for alternative in _sorted_alternatives(scoring_input["alternatives"])
    ]
    ranking = _ranking(alternatives)
    lineage_status = "complete" if alternatives and all(a["lineage_status"] == "complete" for a in alternatives) else "incomplete"

    score_core = {
        "score_id": scoring_input["score_id"],
        "label": scoring_input["label"],
        "as_of_date": scoring_input["as_of_date"],
        "sources": {
            "decision_scenario": _source_descriptor(decision_scenario_snapshot_path, decision_scenario),
            "sensitivity_analysis": _source_descriptor(sensitivity_analysis_snapshot_path, sensitivity_analysis),
            "score_policy": _source_descriptor(policy_path, policy),
            "scoring_input": {"path": str(scoring_input_path), "schema_version": scoring_input.get("schema_version")},
        },
        "base_scenario": {
            "scenario_id": decision_scenario.get("scenario_id"),
            "label": decision_scenario.get("label"),
            "status": decision_scenario.get("status"),
        },
        "weights": {metric_id: str(weight) for metric_id, weight in weights.items()},
        "metric_policy": _metric_policy_summary(metric_definitions, weights),
        "lineage_status": lineage_status,
        "alternatives": alternatives,
        "ranking": ranking,
        "data_gaps": data_gaps,
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "complete" if not data_gaps and all(a["status"] == "complete" for a in alternatives) else "partial",
        **score_core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(_semantic_score_core(score_core)),
        },
        "notes": (
            "Decision score V1 resolves explicitly mapped deterministic outcome metrics and applies explicit "
            "weights. Metrics without outcome lineage are blocking. It does not calculate taxes, pension "
            "entitlements, underlying metrics or recommendations."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise DecisionScoreError(f"Cannot write decision score snapshot: {output_path}") from exc
    return snapshot


def _read_schema_snapshot(path: Path, label: str, expected_schema: str) -> dict[str, Any]:
    data = _read_json(path, label)
    if data.get("schema_version") != expected_schema:
        raise DecisionScoreError(f"Unsupported {label} schema: {data.get('schema_version')}; expected {expected_schema}")
    return data


def _read_scoring_input(path: Path) -> dict[str, Any]:
    data = _read_json(path, "decision score input")
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported decision score input schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported decision score input record type: {data.get('record_type')}")
    for field in ("score_id", "label", "as_of_date"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            errors.append(f"{field} is required")
    if not isinstance(data.get("weights"), dict) or not data["weights"]:
        errors.append("weights must be a non-empty object")
    if not isinstance(data.get("alternatives"), list) or not data["alternatives"]:
        errors.append("alternatives must be a non-empty list")
    if errors:
        raise DecisionScoreError("; ".join(errors))
    return data


def _read_policy(path: Path) -> dict[str, Any]:
    policy = _read_schema_snapshot(path, "decision score policy", POLICY_SCHEMA_VERSION)
    metrics = policy.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise DecisionScoreError("decision score policy requires non-empty metrics")
    seen: set[str] = set()
    for metric in metrics:
        if not isinstance(metric, dict):
            raise DecisionScoreError("decision score policy metrics must be objects")
        metric_id = metric.get("metric_id")
        if not isinstance(metric_id, str) or not metric_id:
            raise DecisionScoreError("decision score policy metric_id is required")
        if metric_id in seen:
            raise DecisionScoreError(f"duplicate decision score policy metric: {metric_id}")
        seen.add(metric_id)
        if metric.get("orientation") not in {"higher_is_better", "lower_is_better"}:
            raise DecisionScoreError(f"unsupported orientation for metric {metric_id}: {metric.get('orientation')}")
        min_value = _decimal(metric.get("min_value"), f"{metric_id}.min_value")
        max_value = _decimal(metric.get("max_value"), f"{metric_id}.max_value")
        if max_value <= min_value:
            raise DecisionScoreError(f"invalid normalization range for metric {metric_id}")
    return policy


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DecisionScoreError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DecisionScoreError(f"Invalid JSON in {label}: {path}") from exc
    if not isinstance(data, dict):
        raise DecisionScoreError(f"{label} must contain a JSON object: {path}")
    return data


def _weights(
    scoring_input: dict[str, Any],
    metric_definitions: dict[str, dict[str, Any]],
    data_gaps: list[dict[str, Any]],
) -> dict[str, Decimal]:
    weights: dict[str, Decimal] = {}
    for metric_id in sorted(str(metric_id) for metric_id in scoring_input["weights"]):
        if metric_id not in metric_definitions:
            data_gaps.append(
                {
                    "code": "unsupported_weight_metric",
                    "metric_id": metric_id,
                    "message": "Weight references a metric not allowed by the decision score policy.",
                }
            )
            continue
        weight = _decimal(scoring_input["weights"][metric_id], f"weights.{metric_id}")
        if weight < 0:
            raise DecisionScoreError(f"weight cannot be negative: {metric_id}")
        if weight == 0:
            continue
        weights[metric_id] = weight
    if not weights:
        raise DecisionScoreError("at least one positive supported weight is required")
    return weights


def _score_alternative(
    alternative: dict[str, Any],
    sensitivity_analysis: dict[str, Any],
    metric_definitions: dict[str, dict[str, Any]],
    weights: dict[str, Decimal],
    data_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    alternative_id = _required_text(alternative, "alternative_id", "alternative")
    metrics = alternative.get("metrics")
    if not isinstance(metrics, dict):
        raise DecisionScoreError(f"alternative {alternative_id} metrics must be an object")

    outcome, outcome_reference = _resolve_outcome(alternative, sensitivity_analysis, alternative_id, data_gaps)

    metric_scores: list[dict[str, Any]] = []
    weighted_sum = Decimal("0")
    applied_weight = Decimal("0")
    missing_metrics: list[str] = []
    for metric_id, weight in weights.items():
        definition = metric_definitions[metric_id]
        if metric_id not in metrics:
            missing_metrics.append(metric_id)
            data_gaps.append(
                {
                    "code": "missing_alternative_metric",
                    "alternative_id": alternative_id,
                    "metric_id": metric_id,
                    "message": "Alternative does not provide a weighted metric.",
                }
            )
            continue
        metric_spec = metrics[metric_id]
        if not isinstance(metric_spec, dict) or not isinstance(metric_spec.get("outcome_metric_id"), str):
            missing_metrics.append(metric_id)
            data_gaps.append(
                {
                    "code": "metric_provenance_missing",
                    "blocking": True,
                    "alternative_id": alternative_id,
                    "metric_id": metric_id,
                    "message": "Weighted metric must map explicitly to a deterministic outcome metric.",
                }
            )
            continue
        if outcome is None:
            missing_metrics.append(metric_id)
            continue
        outcome_metric_id = metric_spec["outcome_metric_id"]
        outcome_metric = _outcome_metric(outcome, outcome_metric_id)
        if outcome_metric is None:
            missing_metrics.append(metric_id)
            data_gaps.append(
                {
                    "code": "outcome_metric_missing",
                    "blocking": True,
                    "alternative_id": alternative_id,
                    "metric_id": metric_id,
                    "outcome_metric_id": outcome_metric_id,
                    "message": "Mapped metric is not available in the referenced deterministic outcome.",
                }
            )
            continue
        expected_unit = definition.get("unit")
        if expected_unit and outcome_metric.get("unit") != expected_unit:
            missing_metrics.append(metric_id)
            data_gaps.append(
                {
                    "code": "outcome_metric_unit_mismatch",
                    "blocking": True,
                    "alternative_id": alternative_id,
                    "metric_id": metric_id,
                    "expected_unit": expected_unit,
                    "actual_unit": outcome_metric.get("unit"),
                    "message": "Outcome metric unit does not match the score policy metric unit.",
                }
            )
            continue
        raw_value = _decimal(outcome_metric["value"], f"{alternative_id}.{metric_id}")
        normalized = _normalize(raw_value, definition)
        weighted = normalized * weight
        weighted_sum += weighted
        applied_weight += weight
        metric_scores.append(
            {
                "metric_id": metric_id,
                "label": definition.get("label", metric_id),
                "raw_value": str(raw_value),
                "normalized_score": _ratio(normalized),
                "weight": str(weight),
                "weighted_score": _ratio(weighted),
                "orientation": definition["orientation"],
                "unit": definition.get("unit"),
                "provenance": {
                    **dict(outcome_metric.get("provenance", {})),
                    "outcome_metric_id": outcome_metric_id,
                    "outcome_id": outcome.get("outcome_id"),
                    "outcome_hash": _nested_or_none(outcome, ("reproducibility", "content_hash")),
                    "sensitivity_analysis_hash": _nested_or_none(
                        sensitivity_analysis, ("reproducibility", "content_hash")
                    ),
                    "outcome_reference": outcome_reference,
                },
            }
        )

    status = "complete" if not missing_metrics else "partial"
    total_score = None if applied_weight == 0 else _ratio(weighted_sum / applied_weight)
    return {
        "alternative_id": alternative_id,
        "label": alternative.get("label", alternative_id),
        "status": status,
        "lineage_status": "complete" if status == "complete" else "incomplete",
        "outcome_reference": outcome_reference,
        "metrics": metric_scores,
        "missing_metrics": missing_metrics,
        "total_score": total_score,
    }


def _resolve_outcome(
    alternative: dict[str, Any],
    sensitivity_analysis: dict[str, Any],
    alternative_id: str,
    data_gaps: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    reference = alternative.get("outcome_ref")
    if not isinstance(reference, dict) or reference.get("kind") not in {"baseline", "sensitivity", "stress"}:
        data_gaps.append(
            {
                "code": "missing_outcome_reference",
                "blocking": True,
                "alternative_id": alternative_id,
                "message": "Alternative must reference baseline, sensitivity or stress deterministic outcome.",
            }
        )
        return None, None
    kind = reference["kind"]
    reference_id = reference.get("id")
    outcome: Any = None
    if kind == "baseline":
        outcome = sensitivity_analysis.get("baseline_outcome")
    else:
        collection_name = "sensitivity_cases" if kind == "sensitivity" else "stress_matrix"
        collection = sensitivity_analysis.get(collection_name, [])
        if isinstance(collection, list):
            row = next(
                (item for item in collection if isinstance(item, dict) and item.get("id") == reference_id),
                None,
            )
            outcome = row.get("outcome") if isinstance(row, dict) else None
    normalized_reference = {"kind": kind, "id": reference_id if kind != "baseline" else None}
    if not isinstance(outcome, dict) or outcome.get("status") != "complete":
        data_gaps.append(
            {
                "code": "outcome_reference_unavailable",
                "blocking": True,
                "alternative_id": alternative_id,
                "outcome_reference": normalized_reference,
                "message": "Referenced deterministic outcome is missing or not complete.",
            }
        )
        return None, normalized_reference
    return outcome, normalized_reference


def _outcome_metric(outcome: dict[str, Any], metric_id: str) -> dict[str, Any] | None:
    metrics = outcome.get("metrics", [])
    if not isinstance(metrics, list):
        return None
    return next(
        (metric for metric in metrics if isinstance(metric, dict) and metric.get("metric_id") == metric_id),
        None,
    )


def _normalize(raw_value: Decimal, definition: dict[str, Any]) -> Decimal:
    min_value = _decimal(definition["min_value"], f"{definition['metric_id']}.min_value")
    max_value = _decimal(definition["max_value"], f"{definition['metric_id']}.max_value")
    if definition["orientation"] == "higher_is_better":
        normalized = (raw_value - min_value) / (max_value - min_value)
    else:
        normalized = (max_value - raw_value) / (max_value - min_value)
    return max(Decimal("0"), min(Decimal("1"), normalized))


def _ranking(alternatives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    complete = [alternative for alternative in alternatives if alternative["status"] == "complete"]
    ranked = sorted(
        complete,
        key=lambda alternative: (-_decimal(alternative["total_score"], "total_score"), alternative["alternative_id"]),
    )
    rows: list[dict[str, Any]] = []
    previous_score: str | None = None
    previous_rank = 0
    for index, alternative in enumerate(ranked, start=1):
        score = alternative["total_score"]
        rank = previous_rank if score == previous_score else index
        rows.append(
            {
                "rank": rank,
                "alternative_id": alternative["alternative_id"],
                "label": alternative["label"],
                "total_score": score,
            }
        )
        previous_score = score
        previous_rank = rank
    return rows


def _source_gaps(source: str, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    raw_gaps = snapshot.get("data_gaps", [])
    if not isinstance(raw_gaps, list):
        return []
    gaps: list[dict[str, Any]] = []
    for gap in raw_gaps:
        if isinstance(gap, dict):
            copied = dict(gap)
            copied["source"] = source
            gaps.append(copied)
        else:
            gaps.append({"source": source, "code": "source_gap", "message": str(gap)})
    return gaps


def _source_descriptor(path: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": str(path),
        "schema_version": snapshot.get("schema_version"),
        "record_type": snapshot.get("record_type"),
        "status": snapshot.get("status"),
    }


def _metric_policy_summary(
    metric_definitions: dict[str, dict[str, Any]],
    weights: dict[str, Decimal],
) -> list[dict[str, Any]]:
    return [
        {
            "metric_id": metric_id,
            "label": metric_definitions[metric_id].get("label", metric_id),
            "orientation": metric_definitions[metric_id]["orientation"],
            "min_value": metric_definitions[metric_id]["min_value"],
            "max_value": metric_definitions[metric_id]["max_value"],
            "unit": metric_definitions[metric_id].get("unit"),
        }
        for metric_id in sorted(weights)
    ]


def _sorted_alternatives(alternatives: list[Any]) -> list[dict[str, Any]]:
    normalized = [alternative for alternative in alternatives if isinstance(alternative, dict)]
    return sorted(normalized, key=lambda alternative: str(alternative.get("alternative_id", "")))


def _required_text(data: dict[str, Any], field: str, label: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise DecisionScoreError(f"{label} {field} is required")
    return value


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DecisionScoreError(f"Invalid decimal for {field_name}: {value}") from exc


def _ratio(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001")))


def _nested_or_none(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _semantic_score_core(score_core: dict[str, Any]) -> dict[str, Any]:
    semantic = json.loads(json.dumps(score_core))
    for descriptor in semantic.get("sources", {}).values():
        if isinstance(descriptor, dict):
            descriptor.pop("path", None)
    return semantic


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
