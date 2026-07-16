import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "decision-dashboard/v1"


class DashboardBuildError(ValueError):
    pass


def build_decision_dashboard(
    net_worth_snapshot_path: Path,
    assumptions_snapshot_path: Path,
    monte_carlo_snapshot_path: Path,
    scenario_comparison_snapshot_path: Path,
    assumptions_readiness_snapshot_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    data_gaps: list[str] = []
    sources: dict[str, str] = {}

    net_worth = _read_optional_snapshot(net_worth_snapshot_path, "net worth", data_gaps, sources, "net_worth")
    assumptions = _read_optional_snapshot(
        assumptions_snapshot_path,
        "manual assumptions",
        data_gaps,
        sources,
        "manual_assumptions",
    )
    monte_carlo = _read_optional_snapshot(
        monte_carlo_snapshot_path,
        "monte carlo",
        data_gaps,
        sources,
        "monte_carlo",
    )
    scenario_comparison = _read_optional_snapshot(
        scenario_comparison_snapshot_path,
        "scenario comparison",
        data_gaps,
        sources,
        "scenario_comparison",
    )
    assumptions_readiness = _read_optional_snapshot(
        assumptions_readiness_snapshot_path,
        "assumptions readiness",
        data_gaps,
        sources,
        "assumptions_readiness",
    )

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "DecisionDashboardSnapshot",
        "status": "complete" if not data_gaps else "partial",
        "sources": sources,
        "summary": _summary(net_worth, assumptions, monte_carlo, scenario_comparison, assumptions_readiness),
        "metrics": _metrics(net_worth, assumptions, monte_carlo, scenario_comparison, assumptions_readiness),
        "decision_signals": _decision_signals(monte_carlo, scenario_comparison),
        "next_actions": _next_actions(net_worth, assumptions_readiness, monte_carlo, scenario_comparison, data_gaps),
        "data_gaps": data_gaps + _declared_gaps(net_worth, monte_carlo, scenario_comparison, assumptions_readiness),
        "notes": (
            "Deterministic dashboard assembled from snapshots. "
            "It does not calculate taxes, pension entitlements or financial advice."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise DashboardBuildError(f"Cannot write dashboard snapshot: {output_path}") from exc
    return snapshot


def _read_optional_snapshot(
    path: Path,
    label: str,
    data_gaps: list[str],
    sources: dict[str, str],
    source_key: str,
) -> dict[str, Any] | None:
    if not path.exists():
        data_gaps.append(f"Missing {label} snapshot: {path}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DashboardBuildError(f"Cannot read {label} snapshot: {path}") from exc
    if not isinstance(data, dict):
        raise DashboardBuildError(f"{label} snapshot must be a JSON object: {path}")
    sources[source_key] = str(path)
    return data


def _summary(
    net_worth: dict[str, Any] | None,
    assumptions: dict[str, Any] | None,
    monte_carlo: dict[str, Any] | None,
    scenario_comparison: dict[str, Any] | None,
    assumptions_readiness: dict[str, Any] | None,
) -> dict[str, Any]:
    totals = net_worth.get("totals", {}) if isinstance(net_worth, dict) else {}
    best = _best_ranked_scenario(scenario_comparison)
    return {
        "net_worth": totals.get("net_worth") if isinstance(totals, dict) else None,
        "currency": net_worth.get("currency", "EUR") if isinstance(net_worth, dict) else None,
        "assumptions_status": assumptions_readiness.get("status") if isinstance(assumptions_readiness, dict) else None,
        "manual_assumptions_present": assumptions is not None,
        "monte_carlo_status": monte_carlo.get("status") if isinstance(monte_carlo, dict) else None,
        "scenario_comparison_status": scenario_comparison.get("status") if isinstance(scenario_comparison, dict) else None,
        "best_ranked_scenario": best,
    }


def _metrics(
    net_worth: dict[str, Any] | None,
    assumptions: dict[str, Any] | None,
    monte_carlo: dict[str, Any] | None,
    scenario_comparison: dict[str, Any] | None,
    assumptions_readiness: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    cards = [
        {
            "id": "net_worth",
            "label": "Net worth",
            "value": _nested(net_worth, ("totals", "net_worth")),
            "unit": _nested(net_worth, ("currency",)) or "EUR",
            "status": "available" if net_worth is not None else "missing",
        },
        {
            "id": "manual_assumptions",
            "label": "Manual assumptions",
            "value": assumptions_readiness.get("status") if isinstance(assumptions_readiness, dict) else None,
            "status": "available" if assumptions is not None else "missing",
        },
        {
            "id": "monte_carlo_success_rate",
            "label": "Monte Carlo success rate",
            "value": _nested(monte_carlo, ("result", "success_rate")),
            "status": _snapshot_status(monte_carlo),
        },
        {
            "id": "net_retirement_drawdown_yearly",
            "label": "Net retirement drawdown yearly",
            "value": _nested(monte_carlo, ("result", "net_retirement_drawdown_yearly")),
            "unit": "EUR",
            "status": _snapshot_status(monte_carlo),
        },
        {
            "id": "pre_retirement_income_yearly",
            "label": "Pre-retirement income yearly",
            "value": _nested(monte_carlo, ("result", "pre_retirement_income_yearly")),
            "unit": "EUR",
            "status": _snapshot_status(monte_carlo),
        },
        {
            "id": "pre_retirement_net_cashflow_yearly",
            "label": "Pre-retirement net cashflow yearly",
            "value": _nested(monte_carlo, ("result", "pre_retirement_net_cashflow_yearly")),
            "unit": "EUR",
            "status": _snapshot_status(monte_carlo),
        },
        {
            "id": "rental_income_yearly",
            "label": "Rental income yearly",
            "value": _nested(monte_carlo, ("result", "rental_income_yearly")),
            "unit": "EUR",
            "status": _snapshot_status(monte_carlo),
        },
        {
            "id": "best_ranked_target_age",
            "label": "Best ranked target age",
            "value": _nested(_best_ranked_scenario(scenario_comparison), ("target_retirement_age",)),
            "status": _snapshot_status(scenario_comparison),
        },
    ]
    return cards


def _decision_signals(
    monte_carlo: dict[str, Any] | None,
    scenario_comparison: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    success_rate = _nested(monte_carlo, ("result", "success_rate"))
    if success_rate == "0.0000":
        signals.append(
            {
                "severity": "warning",
                "code": "zero_monte_carlo_success_rate",
                "message": "Monte Carlo success rate is zero under current explicit assumptions.",
            }
        )

    ranking = scenario_comparison.get("ranking", []) if isinstance(scenario_comparison, dict) else []
    if isinstance(ranking, list) and ranking:
        first = ranking[0]
        if isinstance(first, dict):
            signals.append(
                {
                    "severity": "info",
                    "code": "top_ranked_retirement_age",
                    "message": f"Top ranked target age by current ranking is {first.get('target_retirement_age')}.",
                }
            )
        if all(isinstance(item, dict) and item.get("success_rate") == "0.0000" for item in ranking):
            signals.append(
                {
                    "severity": "warning",
                    "code": "all_ranked_scenarios_zero_success",
                    "message": "All ranked scenarios have zero success rate under current explicit assumptions.",
                }
            )
    return signals


def _next_actions(
    net_worth: dict[str, Any] | None,
    assumptions_readiness: dict[str, Any] | None,
    monte_carlo: dict[str, Any] | None,
    scenario_comparison: dict[str, Any] | None,
    data_gaps: list[str],
) -> list[str]:
    actions: list[str] = []
    if data_gaps:
        actions.append("Resolve missing snapshots before interpreting dashboard metrics.")
    if isinstance(assumptions_readiness, dict) and assumptions_readiness.get("status") != "ready":
        actions.append("Complete and import manual assumptions.")
    if _nested(monte_carlo, ("result", "success_rate")) == "0.0000":
        actions.append(
            "Add explicit spouse salary, rental income, post-retirement income estimates or lower expense scenarios before interpreting zero success rate."
        )
    if _all_ranked_success_rates_zero(scenario_comparison):
        actions.append("Compare additional scenarios that change cashflow assumptions, not only retirement age.")
    if isinstance(net_worth, dict) and net_worth.get("data_gaps"):
        actions.append("Review net worth data gaps and unsupported documents.")
    if not actions:
        actions.append("Review scenario ranking and decide which alternative needs deeper analysis.")
    return actions


def _declared_gaps(*snapshots: dict[str, Any] | None) -> list[str]:
    gaps: list[str] = []
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            continue
        record_type = snapshot.get("record_type", "snapshot")
        for gap in snapshot.get("data_gaps", []) if isinstance(snapshot.get("data_gaps", []), list) else []:
            gaps.append(f"{record_type}: {_format_gap(gap)}")
    return gaps


def _best_ranked_scenario(scenario_comparison: dict[str, Any] | None) -> dict[str, Any] | None:
    ranking = scenario_comparison.get("ranking", []) if isinstance(scenario_comparison, dict) else []
    if not isinstance(ranking, list) or not ranking:
        return None
    first = ranking[0]
    return first if isinstance(first, dict) else None


def _all_ranked_success_rates_zero(scenario_comparison: dict[str, Any] | None) -> bool:
    ranking = scenario_comparison.get("ranking", []) if isinstance(scenario_comparison, dict) else []
    return bool(ranking) and all(isinstance(item, dict) and item.get("success_rate") == "0.0000" for item in ranking)


def _snapshot_status(snapshot: dict[str, Any] | None) -> str:
    if not isinstance(snapshot, dict):
        return "missing"
    return str(snapshot.get("status", "available"))


def _nested(data: dict[str, Any] | None, path: tuple[str, ...]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _format_gap(gap: Any) -> str:
    if isinstance(gap, dict):
        return ", ".join(f"{key}={gap[key]}" for key in sorted(gap))
    return str(gap)
