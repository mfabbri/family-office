import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "decision-dossier/v1"
INPUT_RECORD_TYPE = "DecisionDossierInput"
SNAPSHOT_RECORD_TYPE = "DecisionDossierSnapshot"
DECISION_SCENARIO_SCHEMA_VERSION = "decision-scenario/v2"
SENSITIVITY_SCHEMA_VERSION = "sensitivity-analysis/v1"
DECISION_SCORE_SCHEMA_VERSION = "decision-score/v1"


class DecisionDossierError(ValueError):
    pass


def build_decision_dossier(
    decision_scenario_snapshot_path: Path,
    sensitivity_analysis_snapshot_path: Path,
    decision_score_snapshot_path: Path,
    dossier_input_path: Path,
    output_path: Path,
    markdown_output_path: Path,
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
    decision_score = _read_schema_snapshot(
        decision_score_snapshot_path,
        "decision score snapshot",
        DECISION_SCORE_SCHEMA_VERSION,
    )
    dossier_input = _read_dossier_input(dossier_input_path)

    data_gaps = []
    data_gaps.extend(_source_gaps("decision_scenario", decision_scenario))
    data_gaps.extend(_source_gaps("sensitivity_analysis", sensitivity_analysis))
    data_gaps.extend(_source_gaps("decision_score", decision_score))
    data_gaps.extend(_score_lineage_gaps(decision_score))
    human_review = dossier_input.get("human_review", {"required": True})
    if not isinstance(human_review, dict) or human_review.get("required") is not True:
        data_gaps.append(
            {
                "source": "dossier_input",
                "code": "human_review_required",
                "blocking": True,
                "message": "Human review must be explicitly required for a decision recommendation.",
            }
        )

    blocking_gap_codes = set(str(code) for code in dossier_input.get("blocking_gap_codes", []))
    blocking_gaps = _blocking_gaps(data_gaps, blocking_gap_codes)
    if decision_score.get("status") != "complete":
        blocking_gaps.append(
            {
                "source": "decision_score",
                "code": "decision_score_not_complete",
                "message": "Decision score snapshot is not complete.",
            }
        )
    ranking = decision_score.get("ranking", [])
    if not isinstance(ranking, list) or not ranking:
        blocking_gaps.append(
            {
                "source": "decision_score",
                "code": "missing_decision_ranking",
                "message": "Decision score ranking is missing.",
            }
        )

    recommendation = None if blocking_gaps else _recommendation(decision_score)
    dossier_core = {
        "dossier_id": dossier_input["dossier_id"],
        "label": dossier_input["label"],
        "as_of_date": dossier_input["as_of_date"],
        "status_reason": "blocked_missing_inputs" if blocking_gaps else "recommendation_available",
        "sources": {
            "decision_scenario": _source_descriptor(decision_scenario_snapshot_path, decision_scenario),
            "sensitivity_analysis": _source_descriptor(sensitivity_analysis_snapshot_path, sensitivity_analysis),
            "decision_score": _source_descriptor(decision_score_snapshot_path, decision_score),
            "dossier_input": {"path": str(dossier_input_path), "schema_version": dossier_input.get("schema_version")},
        },
        "facts_summary": _facts_summary(decision_scenario),
        "assumptions_summary": _assumptions_summary(decision_scenario),
        "alternatives": decision_score.get("alternatives", []),
        "ranking": ranking if isinstance(ranking, list) else [],
        "recommendation": recommendation,
        "ranking_rationale": _ranking_rationale(decision_score),
        "lineage_summary": _lineage_summary(decision_score),
        "risk_summary": _risk_summary(sensitivity_analysis, data_gaps),
        "next_actions": _next_actions(dossier_input, blocking_gaps),
        "human_review": human_review,
        "blocking_gaps": blocking_gaps,
        "data_gaps": data_gaps,
        "limitations": [
            "Dossier is deterministic and based only on supplied snapshots.",
            "No tax, pension, investment return, legal or financial advice is calculated.",
            "Human review is required before acting on any recommendation.",
        ],
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": SNAPSHOT_RECORD_TYPE,
        "status": "blocked_missing_inputs" if blocking_gaps else "complete",
        **dossier_core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(_semantic_dossier_core(dossier_core)),
        },
        "notes": (
            "Decision dossier V1 explains deterministic ranking and recommendation evidence. "
            "It does not run simulations, calculate taxes, returns, pension entitlements or new metrics."
        ),
    }
    markdown = _markdown(snapshot)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_output_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        raise DecisionDossierError(f"Cannot write decision dossier outputs: {output_path}") from exc
    return snapshot


def _read_schema_snapshot(path: Path, label: str, expected_schema: str) -> dict[str, Any]:
    data = _read_json(path, label)
    if data.get("schema_version") != expected_schema:
        raise DecisionDossierError(f"Unsupported {label} schema: {data.get('schema_version')}; expected {expected_schema}")
    return data


def _read_dossier_input(path: Path) -> dict[str, Any]:
    data = _read_json(path, "decision dossier input")
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported decision dossier input schema: {data.get('schema_version')}")
    if data.get("record_type") != INPUT_RECORD_TYPE:
        errors.append(f"Unsupported decision dossier input record type: {data.get('record_type')}")
    for field in ("dossier_id", "label", "as_of_date"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            errors.append(f"{field} is required")
    if not isinstance(data.get("next_actions", []), list):
        errors.append("next_actions must be a list")
    if not isinstance(data.get("blocking_gap_codes", []), list):
        errors.append("blocking_gap_codes must be a list")
    if errors:
        raise DecisionDossierError("; ".join(errors))
    return data


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DecisionDossierError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DecisionDossierError(f"Invalid JSON in {label}: {path}") from exc
    if not isinstance(data, dict):
        raise DecisionDossierError(f"{label} must contain a JSON object: {path}")
    return data


def _recommendation(decision_score: dict[str, Any]) -> dict[str, Any]:
    top = decision_score["ranking"][0]
    alternative = _alternative_by_id(decision_score, top["alternative_id"])
    return {
        "status": "recommended_for_human_review",
        "alternative_id": top["alternative_id"],
        "label": top.get("label", top["alternative_id"]),
        "total_score": top.get("total_score"),
        "summary": (
            f"Highest ranked alternative under explicit weights: "
            f"{top.get('label', top['alternative_id'])}."
        ),
        "evidence": _metric_evidence(alternative),
    }


def _ranking_rationale(decision_score: dict[str, Any]) -> list[dict[str, Any]]:
    rationale = []
    for row in decision_score.get("ranking", []):
        alternative = _alternative_by_id(decision_score, row.get("alternative_id"))
        rationale.append(
            {
                "alternative_id": row.get("alternative_id"),
                "rank": row.get("rank"),
                "total_score": row.get("total_score"),
                "top_metric_contributions": _metric_evidence(alternative)[:3],
            }
        )
    return rationale


def _metric_evidence(alternative: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not alternative:
        return []
    metrics = alternative.get("metrics", [])
    if not isinstance(metrics, list):
        return []
    return sorted(
        [
            {
                "metric_id": metric.get("metric_id"),
                "label": metric.get("label"),
                "raw_value": metric.get("raw_value"),
                "normalized_score": metric.get("normalized_score"),
                "weight": metric.get("weight"),
                "weighted_score": metric.get("weighted_score"),
                "provenance": metric.get("provenance"),
            }
            for metric in metrics
            if isinstance(metric, dict)
        ],
        key=lambda metric: (_numeric_score(metric.get("weighted_score")), str(metric.get("metric_id", ""))),
        reverse=True,
    )


def _risk_summary(sensitivity_analysis: dict[str, Any], data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    tornado = sensitivity_analysis.get("tornado_data", [])
    stress = sensitivity_analysis.get("stress_matrix", [])
    return {
        "top_sensitivities": tornado[:3] if isinstance(tornado, list) else [],
        "stress_scenario_count": len(stress) if isinstance(stress, list) else 0,
        "gap_count": len(data_gaps),
    }


def _score_lineage_gaps(decision_score: dict[str, Any]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    if decision_score.get("lineage_status") != "complete":
        gaps.append(
            {
                "source": "decision_score",
                "code": "decision_score_lineage_incomplete",
                "blocking": True,
                "message": "Decision score does not declare complete deterministic outcome lineage.",
            }
        )
    alternatives = {
        alternative.get("alternative_id"): alternative
        for alternative in decision_score.get("alternatives", [])
        if isinstance(alternative, dict)
    }
    for row in decision_score.get("ranking", []):
        if not isinstance(row, dict):
            continue
        alternative_id = row.get("alternative_id")
        alternative = alternatives.get(alternative_id)
        metrics = alternative.get("metrics", []) if isinstance(alternative, dict) else []
        if not isinstance(metrics, list) or not metrics:
            gaps.append(
                {
                    "source": "decision_score",
                    "code": "ranked_alternative_metrics_missing",
                    "blocking": True,
                    "alternative_id": alternative_id,
                    "message": "Ranked alternative has no traceable metric evidence.",
                }
            )
            continue
        for metric in metrics:
            provenance = metric.get("provenance") if isinstance(metric, dict) else None
            required = ("scenario_content_hash", "evaluator_id", "outcome_hash", "outcome_metric_id")
            if not isinstance(provenance, dict) or any(not provenance.get(field) for field in required):
                gaps.append(
                    {
                        "source": "decision_score",
                        "code": "metric_lineage_missing",
                        "blocking": True,
                        "alternative_id": alternative_id,
                        "metric_id": metric.get("metric_id") if isinstance(metric, dict) else None,
                        "message": "Ranked metric is missing scenario, evaluator or outcome lineage.",
                    }
                )
    return gaps


def _lineage_summary(decision_score: dict[str, Any]) -> dict[str, Any]:
    ranked_ids = {
        row.get("alternative_id")
        for row in decision_score.get("ranking", [])
        if isinstance(row, dict)
    }
    metrics = [
        metric
        for alternative in decision_score.get("alternatives", [])
        if isinstance(alternative, dict) and alternative.get("alternative_id") in ranked_ids
        for metric in alternative.get("metrics", [])
        if isinstance(metric, dict)
    ]
    return {
        "status": decision_score.get("lineage_status", "incomplete"),
        "ranked_alternative_count": len(ranked_ids),
        "traceable_metric_count": sum(1 for metric in metrics if isinstance(metric.get("provenance"), dict)),
        "outcome_hashes": sorted(
            {
                metric["provenance"].get("outcome_hash")
                for metric in metrics
                if isinstance(metric.get("provenance"), dict) and metric["provenance"].get("outcome_hash")
            }
        ),
    }


def _facts_summary(decision_scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario_id": decision_scenario.get("scenario_id"),
        "label": decision_scenario.get("label"),
        "status": decision_scenario.get("status"),
        "source_summaries": decision_scenario.get("source_summaries", {}),
    }


def _assumptions_summary(decision_scenario: dict[str, Any]) -> dict[str, Any]:
    assumptions = decision_scenario.get("assumptions", {})
    if not isinstance(assumptions, dict):
        return {}
    return {
        "sections": sorted(str(key) for key in assumptions),
        "market": assumptions.get("market") if isinstance(assumptions.get("market"), dict) else None,
        "withdrawal_policy": (
            assumptions.get("withdrawal_policy") if isinstance(assumptions.get("withdrawal_policy"), dict) else None
        ),
    }


def _next_actions(dossier_input: dict[str, Any], blocking_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions = [action for action in dossier_input.get("next_actions", []) if isinstance(action, dict)]
    if blocking_gaps:
        actions.insert(
            0,
            {
                "action_id": "resolve_blocking_gaps",
                "label": "Resolve blocking gaps before interpreting the recommendation.",
                "owner": "human_reviewer",
            },
        )
    return actions


def _blocking_gaps(data_gaps: list[dict[str, Any]], blocking_gap_codes: set[str]) -> list[dict[str, Any]]:
    return [
        gap
        for gap in data_gaps
        if gap.get("blocking") is True or (gap.get("code") is not None and str(gap.get("code")) in blocking_gap_codes)
    ]


def _source_gaps(source: str, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    raw_gaps = snapshot.get("data_gaps", [])
    if not isinstance(raw_gaps, list):
        return []
    gaps = []
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
        "content_hash": _nested_or_none(snapshot, ("reproducibility", "content_hash")),
    }


def _alternative_by_id(decision_score: dict[str, Any], alternative_id: str | None) -> dict[str, Any] | None:
    for alternative in decision_score.get("alternatives", []):
        if isinstance(alternative, dict) and alternative.get("alternative_id") == alternative_id:
            return alternative
    return None


def _markdown(snapshot: dict[str, Any]) -> str:
    recommendation = snapshot.get("recommendation") or {}
    lines = [
        f"# {snapshot['label']}",
        "",
        f"- Status: {snapshot['status']}",
        f"- As of date: {snapshot['as_of_date']}",
        f"- Scenario: {snapshot['facts_summary'].get('label', snapshot['facts_summary'].get('scenario_id'))}",
        "",
        "## Recommendation",
        "",
    ]
    if recommendation:
        lines.append(f"- Recommended alternative: {recommendation.get('label')} ({recommendation.get('alternative_id')})")
        lines.append(f"- Total score: {recommendation.get('total_score')}")
    else:
        lines.append("- No active recommendation because blocking inputs or ranking gaps are present.")
    lines.extend(["", "## Ranking", "", "| Rank | Alternative | Score |", "|---:|---|---:|"])
    for row in snapshot.get("ranking", []):
        lines.append(f"| {row.get('rank')} | {row.get('label')} | {row.get('total_score')} |")
    lines.extend(["", "## Blocking Gaps", ""])
    blocking_gaps = snapshot.get("blocking_gaps", [])
    if blocking_gaps:
        for gap in blocking_gaps:
            lines.append(f"- {gap.get('source', 'source')}: {gap.get('code')} - {gap.get('message', '')}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Next Actions", ""])
    for action in snapshot.get("next_actions", []):
        lines.append(f"- {action.get('label', action.get('action_id'))}")
    lines.extend(["", "## Limitations", ""])
    for limitation in snapshot.get("limitations", []):
        lines.append(f"- {limitation}")
    return "\n".join(lines) + "\n"


def _nested_or_none(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _numeric_score(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _semantic_dossier_core(dossier_core: dict[str, Any]) -> dict[str, Any]:
    semantic = json.loads(json.dumps(dossier_core))
    for descriptor in semantic.get("sources", {}).values():
        if isinstance(descriptor, dict):
            descriptor.pop("path", None)
    return semantic
