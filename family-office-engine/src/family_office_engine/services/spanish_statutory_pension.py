import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from family_office_engine.services.spanish_pension_rules import (
    SpanishPensionRulesError,
    accrued_pension_percentage,
    base_reguladora_parameters,
    load_rule_pack,
    ordinary_retirement_age,
)

SCHEMA_VERSION = "spanish-statutory-pension/v1"
RECORD_TYPE = "SpanishStatutoryPensionEstimate"


class SpanishStatutoryPensionError(ValueError):
    pass


def estimate_spanish_statutory_pension(
    reconciliation_snapshot_path: Path,
    rule_pack_path: Path,
    output_path: Path,
    retirement_year: int,
    retirement_month: int = 12,
    scenario: str = "ordinary",
) -> dict[str, Any]:
    if scenario != "ordinary":
        snapshot = _blocked_snapshot(
            reconciliation_snapshot_path,
            rule_pack_path,
            retirement_year,
            retirement_month,
            scenario,
            [{"code": "unsupported_scenario", "message": f"Spanish pension scenario is not supported: {scenario}."}],
            None,
            None,
        )
        return _write_snapshot(snapshot, output_path)

    reconciliation = _read_reconciliation(reconciliation_snapshot_path)
    try:
        rule_pack = load_rule_pack(rule_pack_path)
        base_params = base_reguladora_parameters(rule_pack, retirement_year)
        contribution_months = _contribution_months(reconciliation)
        age = ordinary_retirement_age(rule_pack, retirement_year, contribution_months)
        percentage = accrued_pension_percentage(rule_pack, retirement_year, contribution_months)
    except SpanishPensionRulesError as exc:
        snapshot = _blocked_snapshot(
            reconciliation_snapshot_path,
            rule_pack_path,
            retirement_year,
            retirement_month,
            scenario,
            [{"code": "missing_or_invalid_rule", "message": str(exc)}],
            None,
            None,
        )
        return _write_snapshot(snapshot, output_path)

    gaps = _eligibility_gaps(rule_pack, reconciliation, retirement_year, retirement_month, contribution_months)
    base_inputs = _base_reguladora_inputs(reconciliation, retirement_year, retirement_month, base_params)
    gaps.extend(base_inputs["data_gaps"])

    if gaps:
        snapshot = _blocked_snapshot(
            reconciliation_snapshot_path,
            rule_pack_path,
            retirement_year,
            retirement_month,
            scenario,
            gaps,
            rule_pack,
            {
                "ordinary_retirement_age": age,
                "base_reguladora_parameters": base_params,
                "accrued_percentage": percentage,
                "base_reguladora_input_summary": base_inputs["summary"],
            },
        )
        return _write_snapshot(snapshot, output_path)

    selected_bases = base_inputs["selected_bases"]
    bases_total = sum((_decimal(base["base_amount"], "base_amount") for base in selected_bases), Decimal("0.00"))
    divisor = _decimal(base_params["divisor"], "divisor")
    base_reguladora = _round_money(bases_total / divisor)
    percentage_rate = _decimal(percentage["percentage"], "percentage")
    monthly_gross = _round_money(base_reguladora * percentage_rate)
    payments_per_year = int(rule_pack["payment_schedule"]["ordinary_payments_per_year"])
    annual_gross = _round_money(monthly_gross * Decimal(payments_per_year))

    snapshot = _base_snapshot(
        reconciliation_snapshot_path,
        rule_pack_path,
        retirement_year,
        retirement_month,
        scenario,
        "complete",
        rule_pack,
    )
    snapshot.update(
        {
            "result_type": "internal_estimate",
            "ordinary_retirement_age": age,
            "eligibility": {
                "contribution_months": contribution_months,
                "minimum_total_contribution_months": int(rule_pack["eligibility"]["minimum_total_contribution_months"]),
                "specific_contribution_months_in_lookback": _specific_contribution_months(
                    reconciliation,
                    retirement_year,
                    retirement_month,
                    int(rule_pack["eligibility"]["specific_contribution_lookback_months"]),
                ),
                "specific_contribution_months_required": int(
                    rule_pack["eligibility"]["specific_contribution_months_within_lookback"]
                ),
                "status": "eligible_by_encoded_rules",
            },
            "base_reguladora": {
                "amount": _money(base_reguladora),
                "currency": "EUR",
                "selected_base_total": _money(bases_total),
                "selected_base_count": len(selected_bases),
                "parameters": base_params,
                "selected_bases": selected_bases,
                "limitations": [
                    "Uses documented nominal official bases only.",
                    "Does not revalue bases or integrate contribution gaps.",
                    "Does not apply minimum or maximum pension caps.",
                ],
            },
            "accrued_percentage": percentage,
            "gross_pension": {
                "monthly_amount": _money(monthly_gross),
                "annual_amount": _money(annual_gross),
                "currency": "EUR",
                "payments_per_year": payments_per_year,
                "annualization_source": rule_pack["payment_schedule"]["source_provision"],
            },
            "confidence": "medium",
            "data_gaps": [],
        }
    )
    return _write_snapshot(snapshot, output_path)


def _read_reconciliation(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpanishStatutoryPensionError(f"Missing Spanish contribution reconciliation snapshot: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SpanishStatutoryPensionError(f"Invalid Spanish contribution reconciliation JSON: {path}") from exc
    if data.get("schema_version") != "spanish-contribution-reconciliation/v1":
        raise SpanishStatutoryPensionError(
            f"Unsupported Spanish contribution reconciliation schema: {data.get('schema_version')}"
        )
    if not isinstance(data.get("months"), list):
        raise SpanishStatutoryPensionError("Spanish contribution reconciliation months must be a list.")
    return data


def _eligibility_gaps(
    rule_pack: dict[str, Any],
    reconciliation: dict[str, Any],
    retirement_year: int,
    retirement_month: int,
    contribution_months: int,
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    minimum_total = int(rule_pack["eligibility"]["minimum_total_contribution_months"])
    if contribution_months < minimum_total:
        gaps.append(
            {
                "code": "insufficient_total_contribution_months",
                "message": "Contribution months do not satisfy the encoded ordinary retirement minimum.",
                "available_months": contribution_months,
                "required_months": minimum_total,
            }
        )

    lookback = int(rule_pack["eligibility"]["specific_contribution_lookback_months"])
    specific_required = int(rule_pack["eligibility"]["specific_contribution_months_within_lookback"])
    specific_available = _specific_contribution_months(reconciliation, retirement_year, retirement_month, lookback)
    if specific_available < specific_required:
        gaps.append(
            {
                "code": "insufficient_specific_contribution_months",
                "message": "Contribution months in the encoded lookback period are insufficient.",
                "available_months": specific_available,
                "required_months": specific_required,
                "lookback_months": lookback,
            }
        )
    return gaps


def _base_reguladora_inputs(
    reconciliation: dict[str, Any],
    retirement_year: int,
    retirement_month: int,
    base_params: dict[str, Any],
) -> dict[str, Any]:
    window = _lookback_window(retirement_year, retirement_month, int(base_params["lookback_months"]))
    by_month = {month["month"]: month for month in reconciliation["months"] if isinstance(month, dict) and "month" in month}
    usable: list[dict[str, Any]] = []
    missing_months: list[str] = []

    for month_key in window:
        month = by_month.get(month_key)
        selected = month.get("selected_base") if month else None
        if month and month.get("usable_for_estimator") and selected and selected.get("source_type") == "official_bases":
            usable.append(
                {
                    "month": month_key,
                    "base_amount": _money(_decimal(selected["base_amount"], "selected_base.base_amount")),
                    "currency": selected.get("currency", "EUR"),
                    "source_documents": selected.get("source_documents", []),
                }
            )
        else:
            missing_months.append(month_key)

    required = int(base_params["selected_highest_bases"])
    data_gaps: list[dict[str, Any]] = []
    if len(usable) < required:
        data_gaps.append(
            {
                "code": "insufficient_base_reguladora_months",
                "message": "Not enough official usable monthly bases in the base reguladora lookback window.",
                "available_months": len(usable),
                "required_months": required,
                "lookback_months": int(base_params["lookback_months"]),
                "missing_months": missing_months,
            }
        )

    selected_bases = sorted(usable, key=lambda item: _decimal(item["base_amount"], "base_amount"), reverse=True)[:required]
    selected_bases = sorted(selected_bases, key=lambda item: item["month"])
    return {
        "selected_bases": selected_bases,
        "data_gaps": data_gaps,
        "summary": {
            "lookback_months": int(base_params["lookback_months"]),
            "available_usable_months": len(usable),
            "required_selected_months": required,
            "missing_month_count": len(missing_months),
        },
    }


def _contribution_months(reconciliation: dict[str, Any]) -> int:
    return sum(1 for month in reconciliation["months"] if isinstance(month, dict) and month.get("covered_by_vida_laboral"))


def _specific_contribution_months(
    reconciliation: dict[str, Any],
    retirement_year: int,
    retirement_month: int,
    lookback_months: int,
) -> int:
    window = set(_lookback_window(retirement_year, retirement_month, lookback_months))
    return sum(
        1
        for month in reconciliation["months"]
        if isinstance(month, dict) and month.get("month") in window and month.get("covered_by_vida_laboral")
    )


def _blocked_snapshot(
    reconciliation_snapshot_path: Path,
    rule_pack_path: Path,
    retirement_year: int,
    retirement_month: int,
    scenario: str,
    data_gaps: list[dict[str, Any]],
    rule_pack: dict[str, Any] | None,
    rule_results: dict[str, Any] | None,
) -> dict[str, Any]:
    snapshot = _base_snapshot(
        reconciliation_snapshot_path,
        rule_pack_path,
        retirement_year,
        retirement_month,
        scenario,
        "blocked_missing_inputs",
        rule_pack,
    )
    snapshot.update(
        {
            "result_type": "not_calculated",
            "rule_results": rule_results or {},
            "gross_pension": None,
            "confidence": "none",
            "data_gaps": data_gaps,
        }
    )
    return snapshot


def _base_snapshot(
    reconciliation_snapshot_path: Path,
    rule_pack_path: Path,
    retirement_year: int,
    retirement_month: int,
    scenario: str,
    status: str,
    rule_pack: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "status": status,
        "scenario": scenario,
        "retirement_date": f"{retirement_year:04d}-{retirement_month:02d}",
        "source": {
            "type": "spanish-contribution-reconciliation-snapshot",
            "path": str(reconciliation_snapshot_path),
        },
        "rule_pack": {
            "path": str(rule_pack_path),
            "rule_pack_id": rule_pack.get("rule_pack_id") if rule_pack else None,
            "schema_version": rule_pack.get("schema_version") if rule_pack else None,
            "source_refs": rule_pack.get("source_refs", []) if rule_pack else [],
            "limitations": rule_pack.get("limitations", []) if rule_pack else [],
        },
        "notes": (
            "Internal ordinary Spanish statutory pension estimate from documented official bases and versioned rules. "
            "Not an official Seguridad Social calculation; excludes caps, minimums, tax, EU coordination, early/deferred "
            "retirement, base revaluation and gap integration."
        ),
    }


def _write_snapshot(snapshot: dict[str, Any], output_path: Path) -> dict[str, Any]:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise SpanishStatutoryPensionError(f"Cannot write Spanish statutory pension snapshot: {output_path}") from exc
    return snapshot


def _lookback_window(retirement_year: int, retirement_month: int, months: int) -> list[str]:
    if retirement_month < 1 or retirement_month > 12:
        raise SpanishStatutoryPensionError(f"Invalid retirement month: {retirement_month}")
    end_index = retirement_year * 12 + retirement_month - 2
    start_index = end_index - months + 1
    return [_month_from_index(index) for index in range(start_index, end_index + 1)]


def _month_from_index(index: int) -> str:
    year = index // 12
    month = index % 12 + 1
    return f"{year:04d}-{month:02d}"


def _decimal(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise SpanishStatutoryPensionError(f"Invalid decimal value for {field}: {value}") from exc


def _money(value: Decimal) -> Decimal:
    return f"{_round_money(value)}"


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
