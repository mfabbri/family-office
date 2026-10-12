"""Bounded V4.13 employment-income projection.

This is a machine contract, deliberately not a payroll calculator.  It carries
only declared/observed amounts and applies the two rule-pack operations whose
scope is explicit: annual national gross IRPEF and pension-capital computation.
"""

import hashlib
import json
import tempfile
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from family_office_engine.governance.pension_source_freshness import (
    PensionSourceFreshnessError,
    require_fresh_pension_rule_pack,
)
from family_office_engine.services.tax_calculation import calculate_tax


SCHEMA_VERSION = "employment-income-projection/v1"
INPUT_SCHEMA_VERSION = "employment-income-projection-input/v1"
SCENARIO_SCHEMA_VERSION = "work-transition-scenario/v1"
INPS_RULE_SCHEMA_VERSION = "inps-theoretical-pension-rule-pack/v1"
IRPEF_RULE_PACK_ID = "it.irpef-national.2026.v2"
CENT = Decimal("0.01")


class EmploymentIncomeProjectionError(ValueError):
    pass


def build_employment_income_projection(
    scenario_path: Path,
    input_path: Path,
    irpef_rule_pack_path: Path,
    inps_rule_pack_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Build a periodized projection without inferring payroll facts or policy."""
    _assert_input_scope(scenario_path)
    _assert_input_scope(input_path)
    scenario = _read_json(scenario_path, "work-transition scenario")
    data = _read_json(input_path, "employment-income projection input")
    try:
        require_fresh_pension_rule_pack(inps_rule_pack_path)
    except PensionSourceFreshnessError as exc:
        raise EmploymentIncomeProjectionError(str(exc)) from exc
    inps_rule = _read_json(inps_rule_pack_path, "INPS theoretical pension rule pack")
    _validate_scenario(scenario)
    _validate_input(data, scenario)
    _validate_inps_rule(inps_rule)
    _assert_output_scope(output_path)

    periods_by_key = _periods(data["periods"])
    scenario_months = _scenario_months(scenario)
    records: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    annual_bases: dict[tuple[str, int], Decimal] = defaultdict(lambda: Decimal("0"))
    annual_complete: dict[tuple[str, int], bool] = defaultdict(lambda: True)
    annual_months: dict[tuple[str, int], set[int]] = defaultdict(set)
    annual_has_worked_month: dict[tuple[str, int], bool] = defaultdict(bool)
    scenario_month_keys = {(item["member_id"], item["month"]) for item in scenario_months}
    if len(scenario_month_keys) != len(scenario_months):
        raise EmploymentIncomeProjectionError("scenario contains duplicate member/month periods")
    extra_periods = sorted(set(periods_by_key) - scenario_month_keys)
    if extra_periods:
        raise EmploymentIncomeProjectionError("input contains periods outside the work-transition scenario")

    for scenario_month in scenario_months:
        key = (scenario_month["member_id"], scenario_month["month"])
        period = periods_by_key.get(key)
        record, record_gaps = _project_period(scenario_month, period, inps_rule)
        records.append(record)
        gaps.extend(record_gaps)
        month_date = date.fromisoformat(scenario_month["month"])
        annual_key = (scenario_month["member_id"], month_date.year)
        annual_months[annual_key].add(month_date.month)
        annual_complete.setdefault(annual_key, True)
        if scenario_month["status"] != "not_working":
            annual_has_worked_month[annual_key] = True
            if period is None or period.get("taxable_income") is None:
                annual_complete[annual_key] = False
            else:
                annual_bases[annual_key] += _money_decimal(period["taxable_income"], "taxable_income")

    annual_irpef, tax_gaps = _annual_irpef(
        annual_bases, annual_complete, annual_months, annual_has_worked_month, irpef_rule_pack_path, output_path
    )
    gaps.extend(tax_gaps)
    blocking_count = sum(1 for gap in gaps if gap["blocking"])
    core = {
        "household_id": scenario["household_id"],
        "as_of_date": scenario["as_of_date"],
        "status": "blocked" if blocking_count else "complete",
        "sources": {
            "work_transition_scenario": _source(scenario_path, scenario),
            "input": _source_file(input_path),
            "irpef_rule_pack": _rule_source(irpef_rule_pack_path),
            "inps_rule_pack": _rule_source(inps_rule_pack_path),
        },
        "policy": {
            "period_granularity": "monthly",
            "irpef": "illustrative_national_gross_on_employment_base_only_not_total_tax_liability",
            "irpef_scope": "other_taxable_income_not_included_and_reported_as_blocking_gap",
            "inps": "no_pension_capital_computation_without_rule_pack_supported_management_and_rounding_policy",
            "full_payroll_net": "not_calculated",
            "retirement_dates": "not_emitted",
        },
        "periods": records,
        "illustrative_annual_national_gross_irpef_on_employment_income": annual_irpef,
        "data_gaps": sorted(gaps, key=lambda item: (not item["blocking"], item.get("member_id", ""), item["code"])),
        "summary": {
            "period_count": len(records),
            "blocking_gap_count": blocking_count,
            "warning_count": len(gaps) - blocking_count,
        },
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "EmploymentIncomeProjectionSnapshot",
        **core,
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": _content_hash(core)},
        "notes": (
            "This machine-only contract does not calculate payroll net, employee INPS withholding, deductions, "
            "regional or municipal additional taxes, TFR accrual, or complementary-pension matching. "
            "Observed/declared TFR and complementary contributions are carried separately."
        ),
    }
    return _write_snapshot(snapshot, output_path)


def _validate_scenario(scenario: dict[str, Any]) -> None:
    if scenario.get("schema_version") != SCENARIO_SCHEMA_VERSION or scenario.get("record_type") != "WorkTransitionScenarioSnapshot":
        raise EmploymentIncomeProjectionError("input scenario must be work-transition-scenario/v1")
    for key in ("household_id", "as_of_date", "monthly_timeline", "reproducibility"):
        if key not in scenario:
            raise EmploymentIncomeProjectionError(f"scenario is missing {key}")
    if not isinstance(scenario["monthly_timeline"], list):
        raise EmploymentIncomeProjectionError("scenario monthly_timeline must be an array")
    reproducibility = scenario["reproducibility"]
    if not isinstance(reproducibility, dict) or reproducibility.get("hash_algorithm") != "sha256":
        raise EmploymentIncomeProjectionError("scenario sha256 reproducibility metadata is required")
    declared_hash = reproducibility.get("content_hash")
    core = {key: value for key, value in scenario.items() if key not in {"schema_version", "record_type", "reproducibility", "notes"}}
    if not isinstance(declared_hash, str) or _content_hash(core) != declared_hash:
        raise EmploymentIncomeProjectionError("scenario content hash does not match snapshot content")


def _validate_input(data: dict[str, Any], scenario: dict[str, Any]) -> None:
    if data.get("schema_version") != INPUT_SCHEMA_VERSION or data.get("record_type") != "EmploymentIncomeProjectionInput":
        raise EmploymentIncomeProjectionError("unsupported employment-income projection input")
    if data.get("household_id") != scenario["household_id"] or data.get("as_of_date") != scenario["as_of_date"]:
        raise EmploymentIncomeProjectionError("input household_id and as_of_date must match scenario")
    unknown = sorted(set(data) - {"schema_version", "record_type", "household_id", "as_of_date", "periods"})
    if unknown:
        raise EmploymentIncomeProjectionError(f"input contains unsupported fields: {', '.join(unknown)}")
    if not isinstance(data.get("periods"), list):
        raise EmploymentIncomeProjectionError("periods must be an array")


def _validate_inps_rule(rule: dict[str, Any]) -> None:
    if (
        rule.get("schema_version") != INPS_RULE_SCHEMA_VERSION
        or rule.get("rule_pack_id") != "it.inps-theoretical-pension.2026.v1"
        or rule.get("jurisdiction") != "IT"
        or rule.get("valid_from") != "2026-01-01"
        or rule.get("valid_to") != "2026-12-31"
    ):
        raise EmploymentIncomeProjectionError("unsupported or out-of-scope INPS rule pack")
    rate = rule.get("contributory_method", {}).get("default_employee_computation_rate")
    parsed_rate = _money_decimal(rate, "INPS pension-capital computation rate")
    if parsed_rate > Decimal("1"):
        raise EmploymentIncomeProjectionError("INPS pension-capital computation rate must not exceed 1")


def _periods(value: list[Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result = {}
    allowed = {
        "member_id", "month", "taxable_income", "taxable_income_basis", "pensionable_base",
        "pensionable_base_basis", "inps_management", "provenance", "tfr", "complementary_contributions",
    }
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise EmploymentIncomeProjectionError(f"periods[{index}] must be an object")
        unknown = sorted(set(item) - allowed)
        if unknown:
            raise EmploymentIncomeProjectionError(f"periods[{index}] contains unsupported fields: {', '.join(unknown)}")
        member_id = _required_text(item.get("member_id"), f"periods[{index}].member_id")
        month = _month(item.get("month"), f"periods[{index}].month")
        _provenance(item.get("provenance"), f"periods[{index}].provenance")
        for field in ("taxable_income", "pensionable_base"):
            if item.get(field) is not None:
                _money_decimal(item[field], f"periods[{index}].{field}")
                basis = item.get(f"{field}_basis")
                if basis not in {"observed", "declared"}:
                    raise EmploymentIncomeProjectionError(f"periods[{index}].{field}_basis must be observed or declared")
        if item.get("inps_management") is not None:
            _required_text(item["inps_management"], f"periods[{index}].inps_management")
        _passthrough(item.get("tfr"), f"periods[{index}].tfr")
        contributions = item.get("complementary_contributions", [])
        if not isinstance(contributions, list):
            raise EmploymentIncomeProjectionError(f"periods[{index}].complementary_contributions must be an array")
        for contribution in contributions:
            _passthrough(contribution, f"periods[{index}].complementary_contributions")
        key = (member_id, month)
        if key in result:
            raise EmploymentIncomeProjectionError(f"duplicate period for {member_id} {month}")
        result[key] = item
    return result


def _project_period(scenario_month: dict[str, Any], period: dict[str, Any] | None, inps_rule: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    member_id, month = scenario_month["member_id"], scenario_month["month"]
    if scenario_month["status"] == "not_working":
        if period and any(
            period.get(field) not in (None, "0", "0.0", "0.00", 0, 0.0)
            for field in ("taxable_income", "pensionable_base")
        ):
            raise EmploymentIncomeProjectionError(
                f"not_working scenario month {month} cannot contain positive employment or pensionable bases"
            )
        return _record(scenario_month, period, None, None), []
    gaps = [_gap("full_payroll_net_unsupported", member_id, month, "Full payroll net is outside the approved rule-pack scope."),
            _gap("employee_inps_withholding_unsupported", member_id, month, "The 33% pension-capital rate is not employee withholding."),
            _gap("deductions_and_additional_taxes_unsupported", member_id, month, "Deductions and regional/municipal additional taxes are unsupported.")]
    for field, code, description in (
        ("compensation_policy_ref", "compensation_policy_not_resolved", "No compensation-policy resolver is implemented; supplied period amounts are not generated from this reference."),
        ("contribution_benefit_policy_ref", "contribution_benefit_policy_not_resolved", "No contribution/benefit policy resolver is implemented; no employer matching or contractual benefit is inferred."),
    ):
        reference = scenario_month.get(field)
        gaps.append(_gap(code, member_id, month, description if reference else f"Missing {field}; no policy is inferred."))
    if period is None:
        gaps.append(_gap("missing_periodized_income_input", member_id, month, "No documented periodized income input was supplied."))
        return _record(scenario_month, None, None, None), gaps
    if "complementary_contributions" not in period:
        gaps.append(_gap("complementary_contributions_not_reported", member_id, month, "Declare the observed contribution stream or an explicit empty list; no fund rate/matching is inferred."))
    pension_capital = None
    if period.get("pensionable_base") is None or period.get("inps_management") is None:
        gaps.append(_gap("missing_declared_inps_management_or_pensionable_base", member_id, month, "Pension capital requires an explicitly declared management and base."))
    elif not inps_rule["valid_from"] <= month <= inps_rule["valid_to"]:
        gaps.append(_gap("inps_computation_rule_outside_validity", member_id, month, "The INPS computation rule is only valid in 2026; later years require an explicit planning assumption or updated rule pack."))
    elif period["inps_management"] not in inps_rule["contributory_method"].get("supported_managements", []):
        gaps.append(_gap("inps_management_not_covered_by_rule_pack", member_id, month, "The rule pack does not declare an applicable INPS management; no computation rate is inferred."))
    elif inps_rule["contributory_method"].get("pension_capital_precision") != "exact_decimal_no_rounding":
        gaps.append(_gap("inps_pension_capital_precision_not_defined", member_id, month, "The rule pack does not define a pension-capital precision/rounding method."))
    else:
        rate = _money_decimal(inps_rule["contributory_method"]["default_employee_computation_rate"], "INPS rate")
        pension_capital = _format_exact_decimal(_money_decimal(period["pensionable_base"], "pensionable_base") * rate)
    if period.get("tfr") is None:
        gaps.append(_gap("tfr_accrual_unsupported", member_id, month, "TFR is only passed through when observed or declared; no accrual is derived."))
    return _record(scenario_month, period, pension_capital, period.get("inps_management")), gaps


def _record(scenario_month: dict[str, Any], period: dict[str, Any] | None, pension_capital: str | None, management: str | None) -> dict[str, Any]:
    is_working = scenario_month["status"] != "not_working"
    return {
        "member_id": scenario_month["member_id"], "month": scenario_month["month"], "phase_id": scenario_month["phase_id"],
        "status": scenario_month["status"], "fte": scenario_month["fte"],
        "compensation_policy_ref": scenario_month.get("compensation_policy_ref"),
        "contribution_benefit_policy_ref": scenario_month.get("contribution_benefit_policy_ref"),
        "taxable_income": period.get("taxable_income") if period and is_working else "0.00" if not is_working else None,
        "taxable_income_basis": period.get("taxable_income_basis") if period and is_working else "scenario_not_working" if not is_working else None,
        "pensionable_base": period.get("pensionable_base") if period and is_working else "0.00" if not is_working else None,
        "pensionable_base_basis": period.get("pensionable_base_basis") if period and is_working else "scenario_not_working" if not is_working else None,
        "inps_management": management if is_working else None,
        "pension_capital_contribution": pension_capital,
        "employee_inps_withholding": None, "national_gross_irpef": None, "deductions": None,
        "additional_taxes": None, "payroll_net": None,
        "tfr": period.get("tfr") if period else None,
        "complementary_contributions": period.get("complementary_contributions", []) if period else [],
        "provenance": period.get("provenance") if period else None,
    }


def _annual_irpef(
    bases: dict[tuple[str, int], Decimal],
    complete: dict[tuple[str, int], bool],
    coverage: dict[tuple[str, int], set[int]],
    has_worked_month: dict[tuple[str, int], bool],
    rule_path: Path,
    output_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result, gaps = [], []
    for (member_id, year) in sorted(complete):
        if not has_worked_month[(member_id, year)]:
            continue
        if year != 2026:
            result.append({"member_id": member_id, "tax_year": year, "explicit_employment_taxable_income": None, "illustrative_national_gross_irpef": None})
            gaps.append(_gap("irpef_rule_year_unsupported", member_id, f"{year}-01-01", "Only the supplied 2026 IRPEF rule pack may be used."))
        elif coverage[(member_id, year)] != set(range(1, 13)):
            result.append({"member_id": member_id, "tax_year": year, "explicit_employment_taxable_income": None, "illustrative_national_gross_irpef": None})
            gaps.append(_gap("incomplete_calendar_year_coverage_for_irpef", member_id, f"{year}-01-01", "Annual IRPEF requires a complete January-December scenario horizon; partial years are not annualized."))
        elif not complete[(member_id, year)]:
            result.append({"member_id": member_id, "tax_year": year, "explicit_employment_taxable_income": None, "illustrative_national_gross_irpef": None})
            gaps.append(_gap("missing_periodized_taxable_income_for_annual_irpef", member_id, "2026-01-01", "Annual gross IRPEF requires every worked month to have explicit taxable income."))
        else:
            gaps.append(_gap(
                "other_taxable_income_not_included_in_irpef_base",
                member_id,
                f"{year}-01-01",
                "Only employment taxable income is supplied; the progressive IRPEF result is illustrative, not the person's total tax liability.",
            ))
            # Keep the transient TaxCalculationSnapshot inside the approved
            # workspace output tree; do not spill personal inputs to a system
            # temporary directory outside the family-office workspace.
            output_parent = output_path.parent
            output_parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=output_parent) as directory:
                calculated = calculate_tax(rule_path, 2026, "IT", _format_money(bases[(member_id, year)]), Path(directory) / "irpef.json")
            if calculated["status"] != "complete" or calculated["rule_pack"]["rule_pack_id"] != IRPEF_RULE_PACK_ID:
                raise EmploymentIncomeProjectionError("IRPEF rule pack must be it.irpef-national.2026.v2 and cover 2026")
            result.append({"member_id": member_id, "tax_year": year, "explicit_employment_taxable_income": _format_money(bases[(member_id, year)]), "illustrative_national_gross_irpef": calculated["result"]["tax_due"]})
            if any("retrieved_on" not in source for source in calculated["rule_pack"].get("source_refs", [])):
                gaps.append({
                    "code": "irpef_source_verification_date_not_recorded",
                    "member_id": member_id,
                    "tax_year": year,
                    "blocking": True,
                    "message": "The rule pack has no explicit source retrieval date; independent current-period validity confirmation is required before production use.",
                })
    return result, gaps


def _scenario_months(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    months = []
    for timeline in scenario["monthly_timeline"]:
        if not isinstance(timeline, dict) or not isinstance(timeline.get("months"), list):
            raise EmploymentIncomeProjectionError("scenario monthly_timeline is malformed")
        for item in timeline["months"]:
            if not isinstance(item, dict):
                raise EmploymentIncomeProjectionError("scenario month must be an object")
            for key in ("member_id", "month", "phase_id", "status", "fte"):
                if key not in item and key != "member_id":
                    raise EmploymentIncomeProjectionError(f"scenario month is missing {key}")
            months.append({**item, "member_id": timeline.get("member_id")})
    return sorted(months, key=lambda item: (item["member_id"], item["month"]))


def _passthrough(value: Any, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise EmploymentIncomeProjectionError(f"{label} must be an object")
    allowed = {"amount", "basis", "provenance", "contributor"}
    unknown = sorted(set(value) - allowed)
    if unknown or value.get("basis") not in {"observed", "declared"}:
        raise EmploymentIncomeProjectionError(f"{label} must be observed or declared with no unsupported fields")
    if "complementary_contributions" in label and value.get("contributor") not in {"employee", "employer"}:
        raise EmploymentIncomeProjectionError(f"{label}.contributor must be employee or employer")
    _money_decimal(value.get("amount"), f"{label}.amount")
    _provenance(value.get("provenance"), f"{label}.provenance")


def _provenance(value: Any, label: str) -> None:
    if not isinstance(value, dict) or not isinstance(value.get("origin"), str) or not value["origin"].strip():
        raise EmploymentIncomeProjectionError(f"{label}.origin is required")


def _gap(code: str, member_id: str, month: str, message: str) -> dict[str, Any]:
    return {"code": code, "member_id": member_id, "month": month, "blocking": True, "message": message}


def _source(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    return {"path": str(path).replace("\\", "/"), "schema_version": data["schema_version"], "content_hash": data["reproducibility"].get("content_hash")}


def _source_file(path: Path) -> dict[str, str]:
    return {"path": str(path).replace("\\", "/"), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _rule_source(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        pack = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EmploymentIncomeProjectionError(f"invalid rule pack: {path}") from exc
    validity = [
        {"valid_from": rule.get("valid_from"), "valid_to": rule.get("valid_to")}
        for rule in pack.get("rules", [])
    ] or [{"valid_from": pack.get("valid_from"), "valid_to": pack.get("valid_to")}]
    return {
        "path": str(path).replace("\\", "/"),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "rule_pack_id": pack.get("rule_pack_id"),
        "schema_version": pack.get("schema_version"),
        "validity": validity,
        "source_refs": pack.get("source_refs", []),
        "limitations": pack.get("limitations", []),
    }


def _month(value: Any, label: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise EmploymentIncomeProjectionError(f"{label} must be an ISO month date") from exc
    if parsed.day != 1:
        raise EmploymentIncomeProjectionError(f"{label} must be the first day of a month")
    return parsed.isoformat()


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EmploymentIncomeProjectionError(f"{label} must be a non-empty string")
    return value.strip()


def _money_decimal(value: Any, label: str) -> Decimal:
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise EmploymentIncomeProjectionError(f"{label} must be a decimal") from exc
    if not decimal.is_finite() or decimal < 0:
        raise EmploymentIncomeProjectionError(f"{label} must be a non-negative decimal")
    return decimal


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _format_exact_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text and len(text.rsplit(".", 1)[1]) < 2:
        text += "0" * (2 - len(text.rsplit(".", 1)[1]))
    return text


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EmploymentIncomeProjectionError(f"cannot read {label}: {path}") from exc
    if not isinstance(data, dict):
        raise EmploymentIncomeProjectionError(f"{label} must be a JSON object")
    return data


def _assert_output_scope(output_path: Path) -> None:
    try:
        output_path.resolve().relative_to(_workspace_root().resolve())
    except ValueError as exc:
        raise EmploymentIncomeProjectionError("employment-income projection output must stay inside family-office-workspace") from exc


def _assert_input_scope(input_path: Path) -> None:
    try:
        input_path.resolve().relative_to(_workspace_root().resolve())
    except ValueError as exc:
        raise EmploymentIncomeProjectionError("personal employment-income inputs must stay inside family-office-workspace") from exc


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[4] / "family-office-workspace"


def _write_snapshot(snapshot: dict[str, Any], output_path: Path) -> dict[str, Any]:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise EmploymentIncomeProjectionError(f"cannot write employment-income projection: {output_path}") from exc
    return snapshot


def _content_hash(data: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
