import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "retirement-report/v1"


class ReportBuildError(ValueError):
    pass


def build_retirement_report(
    simulation_snapshot_path: Path,
    net_worth_snapshot_path: Path,
    output_path: Path,
    assumptions_snapshot_path: Path | None = None,
    assumptions_readiness_snapshot_path: Path | None = None,
) -> str:
    simulation = _read_json(simulation_snapshot_path, "retirement simulation")
    net_worth = _read_json(net_worth_snapshot_path, "net worth")
    assumptions = (
        _read_optional_json(assumptions_snapshot_path, "manual assumptions")
        if assumptions_snapshot_path is not None
        else None
    )
    readiness = (
        _read_optional_json(assumptions_readiness_snapshot_path, "assumptions readiness")
        if assumptions_readiness_snapshot_path is not None
        else None
    )

    markdown = _render_report(
        simulation,
        net_worth,
        assumptions,
        readiness,
        {
            "simulation": simulation_snapshot_path,
            "net_worth": net_worth_snapshot_path,
            "manual_assumptions": assumptions_snapshot_path,
            "assumptions_readiness": assumptions_readiness_snapshot_path,
        },
    )
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        raise ReportBuildError(f"Cannot write report: {output_path}") from exc
    return markdown


def _render_report(
    simulation: dict[str, Any],
    net_worth: dict[str, Any],
    assumptions: dict[str, Any] | None,
    readiness: dict[str, Any] | None,
    paths: dict[str, Path | None],
) -> str:
    _require_record_type(simulation, "RetirementSimulationSnapshot", "retirement simulation")
    _require_record_type(net_worth, "NetWorthSnapshot", "net worth")
    if assumptions is not None:
        _require_record_type(assumptions, "ManualAssumptions", "manual assumptions")
    if readiness is not None:
        _require_record_type(readiness, "AssumptionsReadinessSnapshot", "assumptions readiness")

    lines = [
        "# Retirement planning report",
        "",
        "## Summary",
        "",
        f"- Report schema: `{SCHEMA_VERSION}`",
        f"- Simulation status: `{simulation.get('status', 'unknown')}`",
        f"- Net worth: {_money_total(net_worth)}",
        f"- Target ages: {_target_ages(simulation)}",
        "",
    ]
    lines.extend(_scenario_section(simulation))
    lines.extend(_net_worth_section(net_worth))
    lines.extend(_assumptions_section(assumptions, readiness))
    lines.extend(_sources_section(simulation, net_worth, paths))
    lines.extend(_gaps_section(simulation, net_worth, readiness))
    lines.extend(
        [
            "## Limits",
            "",
            "- This report is generated from deterministic snapshots only.",
            "- It does not calculate taxes, pension entitlements, investment advice or legal advice.",
            "- Missing inputs remain gaps; no placeholder personal data is created.",
            "",
        ]
    )
    return "\n".join(lines)


def _scenario_section(simulation: dict[str, Any]) -> list[str]:
    lines = ["## Retirement scenarios", ""]
    scenarios = simulation.get("scenarios", [])
    if not scenarios:
        lines.extend(
            [
                "- No complete retirement scenario is available.",
                f"- Current simulation status: `{simulation.get('status', 'unknown')}`",
                "",
            ]
        )
        return lines

    lines.append("| Target age | Status | Final balance |")
    lines.append("| --- | --- | ---: |")
    for scenario in scenarios:
        lines.append(
            "| "
            f"{scenario.get('target_retirement_age', '')} | "
            f"{scenario.get('status', '')} | "
            f"{scenario.get('final_balance', 'n/a')} |"
        )
    lines.append("")
    return lines


def _net_worth_section(net_worth: dict[str, Any]) -> list[str]:
    lines = ["## Net worth", ""]
    totals = net_worth.get("totals", {})
    lines.extend(
        [
            f"- Assets: {totals.get('assets', 'n/a')} {net_worth.get('currency', 'EUR')}",
            f"- Liabilities: {totals.get('liabilities', 'n/a')} {net_worth.get('currency', 'EUR')}",
            f"- Net worth: {totals.get('net_worth', 'n/a')} {net_worth.get('currency', 'EUR')}",
            "",
        ]
    )
    components = net_worth.get("components", [])
    if components:
        lines.append("| Component | Class | Value | Valuation date |")
        lines.append("| --- | --- | ---: | --- |")
        for component in components:
            lines.append(
                "| "
                f"{_escape_table(component.get('label', ''))} | "
                f"{component.get('asset_class', '')} | "
                f"{component.get('value', '')} {component.get('currency', 'EUR')} | "
                f"{component.get('valuation_date') or 'n/a'} |"
            )
        lines.append("")
    return lines


def _assumptions_section(
    assumptions: dict[str, Any] | None,
    readiness: dict[str, Any] | None,
) -> list[str]:
    lines = ["## Assumptions", ""]
    if readiness is not None:
        lines.append(f"- Readiness status: `{readiness.get('status', 'unknown')}`")
    else:
        lines.append("- Readiness status: `not_available`")

    if assumptions is None:
        lines.extend(["- Manual assumptions snapshot: `missing`", ""])
        return lines

    data = assumptions.get("assumptions", {})
    personal = data.get("personal", {}) if isinstance(data, dict) else {}
    cashflow = data.get("cashflow", {}) if isinstance(data, dict) else {}
    returns = data.get("returns", {}) if isinstance(data, dict) else {}
    lines.extend(
        [
            f"- Current age: {personal.get('current_age', 'n/a')}",
            f"- Target retirement age: {personal.get('target_retirement_age', 'n/a')}",
            f"- Family expenses yearly: {cashflow.get('family_expenses_yearly', 'n/a')}",
            f"- Net salary monthly: {cashflow.get('net_salary_monthly', 'n/a')}",
            f"- Salary months: {cashflow.get('salary_months', 'n/a')}",
            f"- Return scenario: {returns.get('scenario', 'n/a')}",
            f"- Nominal return: {returns.get('nominal_return', 'n/a')}",
            "",
        ]
    )
    return lines


def _sources_section(
    simulation: dict[str, Any],
    net_worth: dict[str, Any],
    paths: dict[str, Path | None],
) -> list[str]:
    lines = ["## Sources", ""]
    for label, path in paths.items():
        if path is not None:
            lines.append(f"- {label}: `{path}`")

    for source_group, sources in (
        ("simulation", simulation.get("sources", {})),
        ("net_worth", net_worth.get("sources", {})),
    ):
        if isinstance(sources, dict):
            for name, source_path in sorted(sources.items()):
                lines.append(f"- {source_group}.{name}: `{source_path}`")
    lines.append("")
    return lines


def _gaps_section(
    simulation: dict[str, Any],
    net_worth: dict[str, Any],
    readiness: dict[str, Any] | None,
) -> list[str]:
    lines = ["## Data gaps", ""]
    gaps: list[str] = []
    gaps.extend(_string_gaps("simulation", simulation.get("data_gaps", [])))
    gaps.extend(_string_gaps("net_worth", net_worth.get("data_gaps", [])))
    if readiness is not None:
        gaps.extend(_string_gaps("assumptions_readiness", readiness.get("data_gaps", [])))
        actions = readiness.get("next_actions", [])
        gaps.extend(_string_gaps("next_action", actions))

    if not gaps:
        lines.append("- No data gaps declared by the input snapshots.")
    else:
        for gap in gaps:
            lines.append(f"- {gap}")
    lines.append("")
    return lines


def _string_gaps(prefix: str, gaps: Any) -> list[str]:
    if not isinstance(gaps, list):
        return [f"{prefix}: invalid gap list"]
    return [f"{prefix}: {_format_value(gap)}" for gap in gaps]


def _format_value(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{key}={value[key]}" for key in sorted(value))
    return str(value)


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise ReportBuildError(f"Missing {label} snapshot: {path}")
    return _load_json(path, label)


def _read_optional_json(path: Path, label: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _load_json(path, label)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportBuildError(f"Cannot read {label} snapshot: {path}") from exc
    if not isinstance(data, dict):
        raise ReportBuildError(f"{label} snapshot must be a JSON object: {path}")
    return data


def _require_record_type(data: dict[str, Any], expected: str, label: str) -> None:
    if data.get("record_type") != expected:
        raise ReportBuildError(f"Unsupported {label} record type")


def _money_total(net_worth: dict[str, Any]) -> str:
    totals = net_worth.get("totals", {})
    if not isinstance(totals, dict):
        return "n/a"
    return f"{totals.get('net_worth', 'n/a')} {net_worth.get('currency', 'EUR')}"


def _target_ages(simulation: dict[str, Any]) -> str:
    target_ages = simulation.get("target_ages", [])
    if not isinstance(target_ages, list):
        return "n/a"
    return ", ".join(str(age) for age in target_ages)


def _escape_table(value: Any) -> str:
    return str(value).replace("|", "\\|")
