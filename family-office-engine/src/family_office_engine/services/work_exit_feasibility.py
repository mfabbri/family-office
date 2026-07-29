import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "work-exit-feasibility/v1"
INPUT_SCHEMA_VERSION = "work-exit-feasibility-input/v1"
INPS_SCHEMA_VERSION = "inps-theoretical-pension/v1"
RULE_PACK_SCHEMA_VERSION = "inps-theoretical-pension-rule-pack/v1"
CENT = Decimal("0.01")
RATIO = Decimal("0.0001")


class WorkExitFeasibilityError(ValueError):
    pass


def build_work_exit_feasibility(
    input_path: Path,
    rule_pack_path: Path,
    output_path: Path,
    *,
    inps_snapshot_path: Path | None = None,
    pro_rata_snapshot_path: Path | None = None,
    pension_income_snapshot_path: Path | None = None,
    net_worth_snapshot_path: Path | None = None,
    liquidity_plan_snapshot_path: Path | None = None,
    lifecycle_expenses_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    data = _read_json(input_path, "work-exit feasibility input")
    rule_pack = _load_rule_pack(rule_pack_path)
    if data.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise WorkExitFeasibilityError(f"Unsupported work-exit feasibility input schema: {data.get('schema_version')}")

    sources: dict[str, str] = {"input": str(input_path), "inps_rule_pack": str(rule_pack_path)}
    optional = {
        "inps_documentary_projection": _load_optional_snapshot(inps_snapshot_path, "inps-pension/v1", sources, "inps_documentary_projection"),
        "spanish_pro_rata": _load_optional_snapshot(pro_rata_snapshot_path, "it-es-eu-pension-pro-rata/v1", sources, "spanish_pro_rata"),
        "pension_income": _load_optional_snapshot(pension_income_snapshot_path, "pension-income/v1", sources, "pension_income"),
        "net_worth": _load_optional_snapshot(net_worth_snapshot_path, "net-worth/v1", sources, "net_worth"),
        "liquidity_plan": _load_optional_snapshot(liquidity_plan_snapshot_path, "liquidity-plan/v1", sources, "liquidity_plan"),
        "lifecycle_expenses": _load_optional_snapshot(lifecycle_expenses_snapshot_path, "lifecycle-expenses/v1", sources, "lifecycle_expenses"),
    }

    data_gaps: list[dict[str, Any]] = []
    as_of_date = _required_date(data.get("as_of_date"), "as_of_date")
    candidates = _candidate_dates(data)
    adults = data.get("adults")
    if not isinstance(adults, list) or not adults:
        raise WorkExitFeasibilityError("adults must contain at least one household adult")
    constraints = data.get("sustainability_constraints") if isinstance(data.get("sustainability_constraints"), dict) else {}
    annual_spending = _annual_spending(data, optional["lifecycle_expenses"], data_gaps)
    horizon_years = _positive_int(constraints.get("horizon_years", data.get("horizon_years", 35)), "horizon_years")
    min_terminal_assets = _decimal(constraints.get("minimum_terminal_assets", "0"), "minimum_terminal_assets")
    bridge_assets = _bridge_assets(data, optional["net_worth"], optional["liquidity_plan"], data_gaps)

    evaluated = []
    for candidate in candidates:
        evaluated.append(
            _evaluate_candidate(
                candidate,
                as_of_date,
                adults,
                rule_pack,
                optional,
                annual_spending,
                horizon_years,
                min_terminal_assets,
                bridge_assets,
            )
        )

    first = next((item for item in evaluated if item["status"] == "sustainable"), None)
    data_gaps.extend(_household_level_gaps(adults, optional))
    data_gaps.extend(gap for item in evaluated for gap in item["data_gaps"] if gap.get("blocking"))
    status = "complete" if first and not data_gaps else "partial" if first else "blocked_no_sustainable_date"
    core = {
        "household_id": data.get("household_id"),
        "as_of_date": as_of_date.isoformat(),
        "search": {
            "candidate_granularity": data.get("candidate_granularity", "explicit_dates"),
            "candidate_count": len(evaluated),
            "horizon_years": horizon_years,
        },
        "sources": sources,
        "rule_pack": _public_rule_pack(rule_pack, rule_pack_path),
        "adult_count": len(adults),
        "first_sustainable_exit_date": first["candidate_date"] if first else None,
        "candidate_dates": evaluated,
        "discarded_dates": [
            {
                "candidate_date": item["candidate_date"],
                "failure_reasons": item["failure_reasons"],
                "terminal_assets": item["sustainability"]["terminal_assets"],
            }
            for item in evaluated
            if item["status"] != "sustainable"
        ],
        "data_gaps": data_gaps,
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "WorkExitFeasibilitySnapshot",
        "status": status,
        **core,
        "reproducibility": {
            "hash_algorithm": "sha256",
            "content_hash": _content_hash(core),
        },
        "notes": (
            "Work-exit feasibility searches explicit candidate dates and composes separated gross pension streams. "
            "Internal INPS estimates are contributory planning estimates, not official INPS decisions. No tax, net "
            "pension, administrative eligibility, investment recommendation or LLM calculation is performed."
        ),
    }
    return _write_snapshot(snapshot, output_path)


def _evaluate_candidate(
    candidate: date,
    as_of_date: date,
    adults: list[Any],
    rule_pack: dict[str, Any],
    optional: dict[str, Any],
    annual_spending: Decimal,
    horizon_years: int,
    min_terminal_assets: Decimal,
    bridge_assets: Decimal,
) -> dict[str, Any]:
    streams: list[dict[str, Any]] = []
    estimates: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for index, adult in enumerate(adults):
        if not isinstance(adult, dict):
            raise WorkExitFeasibilityError(f"adults[{index}] must be an object")
        estimate = _inps_estimate_for_adult(adult, candidate, rule_pack)
        estimates.append(estimate)
        gaps.extend(estimate["data_gaps"])
        pension = estimate.get("pension")
        if isinstance(pension, dict) and pension.get("annual_gross_amount"):
            streams.append(_stream(adult, "IT", "INPS", "internal_inps_contributory_estimate", candidate, pension["annual_gross_amount"]))
        streams.extend(_declared_streams(adult, candidate, gaps))

    streams.extend(_spanish_pro_rata_streams(optional.get("spanish_pro_rata"), candidate))
    streams.extend(_pension_income_streams(optional.get("pension_income"), candidate))
    streams.extend(_inps_documentary_benchmark(optional.get("inps_documentary_projection"), candidate, rule_pack, estimates))
    sustainability = _simulate_sustainability(as_of_date, candidate, horizon_years, annual_spending, bridge_assets, streams)
    failure_reasons = []
    if any(gap.get("blocking") for gap in gaps):
        failure_reasons.append("blocking_data_gaps")
    if sustainability["terminal_assets_decimal"] < min_terminal_assets:
        failure_reasons.append("terminal_assets_below_minimum")
    if sustainability["depleted_before_horizon"]:
        failure_reasons.append("assets_depleted_before_horizon")
    return {
        "candidate_date": candidate.isoformat(),
        "status": "sustainable" if not failure_reasons else "not_sustainable",
        "inps_theoretical_pensions": estimates,
        "gross_pension_streams": streams,
        "household_gross_annual_pension_by_source": _gross_by_source(streams),
        "sustainability": {
            key: value for key, value in sustainability.items() if key != "terminal_assets_decimal"
        },
        "failure_reasons": failure_reasons,
        "data_gaps": gaps,
    }


def _inps_estimate_for_adult(adult: dict[str, Any], candidate: date, rule_pack: dict[str, Any]) -> dict[str, Any]:
    gaps: list[dict[str, Any]] = []
    person_id = _required_string(adult, "person_id")
    dob = _required_date(adult.get("date_of_birth"), f"{person_id}.date_of_birth")
    inps = adult.get("inps_contributory_estimate") if isinstance(adult.get("inps_contributory_estimate"), dict) else None
    if inps is None:
        return _blocked_inps(person_id, candidate, [{"code": "missing_inps_contributory_estimate", "blocking": True}])
    if inps.get("calculation_scope") not in {"contributory_only", "post_1995_contributory_quota"}:
        gaps.append({"code": "unsupported_inps_calculation_scope", "person_id": person_id, "blocking": True})

    montante = _historical_montante(inps, gaps, person_id)
    projected = _projected_contributions(inps, candidate, rule_pack, gaps, person_id)
    revaluation = _revaluation_rate(inps, rule_pack)
    years = max(candidate.year - _as_of_year(inps, candidate), 0)
    montante_at_exit = (montante * ((Decimal("1") + revaluation) ** years)) + projected
    age = _age_at(dob, candidate)
    coefficient = _coefficient(rule_pack, age, candidate, gaps, person_id)
    annual = montante_at_exit * coefficient if coefficient is not None else None
    status = "complete" if annual is not None and not any(gap.get("blocking") for gap in gaps) else "blocked_missing_inputs"
    return {
        "schema_version": INPS_SCHEMA_VERSION,
        "record_type": "InpsTheoreticalPensionEstimate",
        "status": status,
        "person_id": person_id,
        "candidate_date": candidate.isoformat(),
        "method": {
            "scope": inps.get("calculation_scope"),
            "projection_status": _projection_status(rule_pack, candidate),
            "official_decision": False,
        },
        "inputs": {
            "historical_montante": _money(montante),
            "projected_contributions": _money(projected),
            "annual_revaluation_rate": _ratio(revaluation),
            "age_at_candidate": age,
            "transformation_coefficient": _ratio(coefficient) if coefficient is not None else None,
        },
        "pension": {
            "annual_gross_amount": _money(annual) if annual is not None else None,
            "monthly_gross_amount": _money(annual / Decimal(str(rule_pack["contributory_method"]["annual_gross_payments_for_planning"]))) if annual is not None else None,
            "payments_per_year": rule_pack["contributory_method"]["annual_gross_payments_for_planning"],
            "currency": rule_pack.get("currency", "EUR"),
        },
        "data_gaps": gaps,
    }


def _blocked_inps(person_id: str, candidate: date, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": INPS_SCHEMA_VERSION,
        "record_type": "InpsTheoreticalPensionEstimate",
        "status": "blocked_missing_inputs",
        "person_id": person_id,
        "candidate_date": candidate.isoformat(),
        "method": {"official_decision": False},
        "inputs": {},
        "pension": None,
        "data_gaps": gaps,
    }


def _historical_montante(inps: dict[str, Any], gaps: list[dict[str, Any]], person_id: str) -> Decimal:
    if inps.get("historical_montante") not in (None, ""):
        return _decimal(inps["historical_montante"], f"{person_id}.historical_montante")
    annual_bases = inps.get("annual_bases")
    if not isinstance(annual_bases, list) or not annual_bases:
        gaps.append({"code": "missing_historical_montante_or_annual_bases", "person_id": person_id, "blocking": True})
        return Decimal("0")
    total = Decimal("0")
    for index, item in enumerate(annual_bases):
        if not isinstance(item, dict):
            raise WorkExitFeasibilityError(f"{person_id}.annual_bases[{index}] must be an object")
        rate = _decimal(item.get("computation_rate", "0.33"), f"{person_id}.annual_bases[{index}].computation_rate")
        total += _decimal(item.get("taxable_income"), f"{person_id}.annual_bases[{index}].taxable_income") * rate
    return total


def _projected_contributions(
    inps: dict[str, Any],
    candidate: date,
    rule_pack: dict[str, Any],
    gaps: list[dict[str, Any]],
    person_id: str,
) -> Decimal:
    future = inps.get("future_contributions") if isinstance(inps.get("future_contributions"), dict) else {}
    if future.get("annual_taxable_income") in (None, ""):
        gaps.append({"code": "missing_future_annual_taxable_income", "person_id": person_id, "blocking": True})
        return Decimal("0")
    from_year = _as_of_year(inps, candidate) + 1
    to_year = min(int(future.get("through_year", candidate.year)), candidate.year)
    if to_year < from_year:
        return Decimal("0")
    income = _decimal(future["annual_taxable_income"], f"{person_id}.future_contributions.annual_taxable_income")
    rate = _decimal(future.get("computation_rate", rule_pack["contributory_method"]["default_employee_computation_rate"]), "future computation_rate")
    revaluation = _revaluation_rate(inps, rule_pack)
    total = Decimal("0")
    for year in range(from_year, to_year + 1):
        contribution = income * rate
        years_to_exit = max(candidate.year - year, 0)
        total += contribution * ((Decimal("1") + revaluation) ** years_to_exit)
    return total


def _simulate_sustainability(
    as_of_date: date,
    candidate: date,
    horizon_years: int,
    annual_spending: Decimal,
    bridge_assets: Decimal,
    streams: list[dict[str, Any]],
) -> dict[str, Any]:
    balance = bridge_assets
    depleted_year = None
    start_year = as_of_date.year
    end_year = candidate.year + horizon_years - 1
    cashflows = []
    for year in range(start_year, end_year + 1):
        if year < candidate.year:
            income = Decimal("0")
            shortfall = Decimal("0")
        else:
            income = sum(
                (
                    _decimal(stream["annual_gross_amount"], "stream annual_gross_amount")
                    for stream in streams
                    if int(str(stream["start_date"])[:4]) <= year
                ),
                Decimal("0"),
            )
            shortfall = max(annual_spending - income, Decimal("0"))
        balance -= shortfall
        if balance < 0 and depleted_year is None:
            depleted_year = year
        cashflows.append(
            {
                "year": year,
                "gross_pension_income": _money(income),
                "spending_need": _money(annual_spending),
                "asset_withdrawal": _money(shortfall),
                "ending_assets": _money(balance),
            }
        )
    return {
        "initial_bridge_assets": _money(bridge_assets),
        "annual_spending_need": _money(annual_spending),
        "terminal_assets": _money(balance),
        "terminal_assets_decimal": balance,
        "depleted_before_horizon": depleted_year is not None,
        "depletion_year": depleted_year,
        "annual_cashflows": cashflows,
    }


def _declared_streams(adult: dict[str, Any], candidate: date, gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    streams = []
    declared = adult.get("declared_pension_streams")
    if declared is None:
        if adult.get("role") == "spouse":
            gaps.append({"code": "missing_spouse_pension_stream", "person_id": adult.get("person_id"), "blocking": True})
        return streams
    if not isinstance(declared, list):
        raise WorkExitFeasibilityError("declared_pension_streams must be a list")
    for stream in declared:
        if not isinstance(stream, dict):
            continue
        start = _required_date(stream.get("start_date", candidate.isoformat()), "declared_pension_stream.start_date")
        streams.append(
            _stream(
                adult,
                stream.get("country", "IT"),
                stream.get("payer", "declared"),
                stream.get("source_type", "declared_household_pension"),
                start,
                stream.get("annual_gross_amount"),
            )
        )
    return streams


def _spanish_pro_rata_streams(snapshot: dict[str, Any] | None, candidate: date) -> list[dict[str, Any]]:
    if not snapshot:
        return []
    result = snapshot.get("spanish_pro_rata_pension") if isinstance(snapshot.get("spanish_pro_rata_pension"), dict) else {}
    annual = result.get("annual_gross_amount")
    if annual in (None, ""):
        monthly = result.get("monthly_gross_amount")
        payments = result.get("payments_per_year")
        if monthly not in (None, "") and payments not in (None, ""):
            annual = _decimal(monthly, "spanish monthly") * _decimal(payments, "spanish payments")
    if annual in (None, ""):
        return []
    return [
        {
            "person_id": snapshot.get("person_id", "primary"),
            "country": "ES",
            "payer": "Seguridad Social",
            "source_type": "spanish_eu_pro_rata",
            "start_date": snapshot.get("retirement_date", candidate.isoformat()),
            "annual_gross_amount": _money(_decimal(annual, "spanish annual")),
            "currency": "EUR",
        }
    ]


def _pension_income_streams(snapshot: dict[str, Any] | None, candidate: date) -> list[dict[str, Any]]:
    if not snapshot:
        return []
    streams = []
    for stream in snapshot.get("income_streams", []):
        if not isinstance(stream, dict):
            continue
        gross = stream.get("gross") if isinstance(stream.get("gross"), dict) else {}
        annual = gross.get("annual_amount")
        if annual in (None, "") or gross.get("currency", "EUR") != "EUR":
            continue
        streams.append(
            {
                "person_id": stream.get("person_id", "household"),
                "country": stream.get("country"),
                "payer": stream.get("payer"),
                "source_type": stream.get("source_type", "pension_income_snapshot"),
                "start_date": stream.get("start_date") or candidate.isoformat(),
                "annual_gross_amount": _money(_decimal(annual, "pension income annual")),
                "currency": "EUR",
            }
        )
    return streams


def _inps_documentary_benchmark(
    snapshot: dict[str, Any] | None,
    candidate: date,
    rule_pack: dict[str, Any],
    estimates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not snapshot:
        return []
    projection = snapshot.get("projection") if isinstance(snapshot.get("projection"), dict) else {}
    monthly = projection.get("monthly_gross_pension")
    if monthly in (None, ""):
        return []
    payments = Decimal(str(rule_pack["contributory_method"]["annual_gross_payments_for_planning"]))
    annual = _decimal(monthly, "documentary INPS monthly") * payments
    estimate = next((item for item in estimates if item.get("status") == "complete"), None)
    difference = None
    if estimate:
        difference = annual - _decimal(estimate["pension"]["annual_gross_amount"], "estimated annual")
    return [
        {
            "person_id": "primary",
            "country": "IT",
            "payer": "INPS",
            "source_type": "documentary_inps_projection_benchmark",
            "start_date": projection.get("retirement_date") or candidate.isoformat(),
            "annual_gross_amount": _money(annual),
            "currency": "EUR",
            "benchmark_difference_vs_internal_estimate": _money(difference) if difference is not None else None,
        }
    ]


def _stream(adult: dict[str, Any], country: str, payer: str, source_type: str, start_date: date | str, annual: Any) -> dict[str, Any]:
    return {
        "person_id": adult.get("person_id", "unknown"),
        "country": country,
        "payer": payer,
        "source_type": source_type,
        "start_date": start_date.isoformat() if isinstance(start_date, date) else start_date,
        "annual_gross_amount": _money(_decimal(annual, "annual_gross_amount")),
        "currency": "EUR",
    }


def _gross_by_source(streams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str], Decimal] = {}
    for stream in streams:
        key = (str(stream.get("person_id")), str(stream.get("source_type")))
        totals[key] = totals.get(key, Decimal("0")) + _decimal(stream["annual_gross_amount"], "stream annual")
    return [
        {"person_id": person_id, "source_type": source_type, "annual_gross_amount": _money(total), "currency": "EUR"}
        for (person_id, source_type), total in sorted(totals.items())
    ]


def _household_level_gaps(adults: list[Any], optional: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = []
    if optional.get("spanish_pro_rata") is None:
        gaps.append({"code": "missing_spanish_pro_rata_snapshot", "blocking": False})
    if not any(isinstance(adult, dict) and adult.get("role") == "spouse" for adult in adults):
        gaps.append({"code": "missing_spouse_adult", "blocking": True})
    return gaps


def _annual_spending(data: dict[str, Any], lifecycle: dict[str, Any] | None, gaps: list[dict[str, Any]]) -> Decimal:
    constraints = data.get("sustainability_constraints") if isinstance(data.get("sustainability_constraints"), dict) else {}
    if constraints.get("annual_spending_need") not in (None, ""):
        return _decimal(constraints["annual_spending_need"], "annual_spending_need")
    if lifecycle:
        summary = lifecycle.get("summary") if isinstance(lifecycle.get("summary"), dict) else {}
        annual = summary.get("annual_total") or summary.get("gross_annual_total")
        if annual not in (None, ""):
            return _decimal(annual, "lifecycle annual spending")
    gaps.append({"code": "missing_annual_spending_need", "blocking": True})
    return Decimal("0")


def _bridge_assets(
    data: dict[str, Any],
    net_worth: dict[str, Any] | None,
    liquidity: dict[str, Any] | None,
    gaps: list[dict[str, Any]],
) -> Decimal:
    constraints = data.get("sustainability_constraints") if isinstance(data.get("sustainability_constraints"), dict) else {}
    if constraints.get("available_bridge_assets") not in (None, ""):
        return _decimal(constraints["available_bridge_assets"], "available_bridge_assets")
    if not net_worth:
        gaps.append({"code": "missing_available_bridge_assets", "blocking": True})
        return Decimal("0")
    allowed = _allowed_assets(liquidity)
    total = Decimal("0")
    for component in net_worth.get("components", []):
        if not isinstance(component, dict) or component.get("type") != "asset":
            continue
        asset_id = component.get("id")
        if allowed is not None and asset_id not in allowed:
            continue
        if component.get("currency", "EUR") == "EUR":
            total += _decimal(component.get("value"), "net worth asset value")
    return total


def _allowed_assets(liquidity: dict[str, Any] | None) -> set[str] | None:
    if not liquidity:
        return None
    allowed_buckets = {"emergency_reserve", "short_term", "medium_term", "long_term"}
    return {
        item["asset_id"]
        for item in liquidity.get("asset_assignments", [])
        if isinstance(item, dict) and item.get("bucket") in allowed_buckets and isinstance(item.get("asset_id"), str)
    }


def _candidate_dates(data: dict[str, Any]) -> list[date]:
    raw = data.get("candidate_dates")
    if isinstance(raw, list) and raw:
        return sorted(_required_date(value, "candidate_dates[]") for value in raw)
    grid = data.get("candidate_grid") if isinstance(data.get("candidate_grid"), dict) else {}
    start_year = _positive_int(grid.get("start_year"), "candidate_grid.start_year")
    end_year = _positive_int(grid.get("end_year"), "candidate_grid.end_year")
    month = int(grid.get("month", 1))
    day = int(grid.get("day", 1))
    step = int(grid.get("step_years", 1))
    return [date(year, month, day) for year in range(start_year, end_year + 1, step)]


def _load_rule_pack(path: Path) -> dict[str, Any]:
    data = _read_json(path, "INPS theoretical pension rule pack")
    if data.get("schema_version") != RULE_PACK_SCHEMA_VERSION:
        raise WorkExitFeasibilityError(f"Unsupported INPS rule pack schema: {data.get('schema_version')}")
    for field in ("rule_pack_id", "contributory_method", "transformation_coefficients", "planning_projection", "source_refs"):
        if field not in data:
            raise WorkExitFeasibilityError(f"INPS rule pack missing field: {field}")
    return data


def _coefficient(rule_pack: dict[str, Any], age: int, candidate: date, gaps: list[dict[str, Any]], person_id: str) -> Decimal | None:
    values = rule_pack["transformation_coefficients"]["official_period"]["values_by_age"]
    key = str(max(min(age, max(int(item) for item in values)), min(int(item) for item in values)))
    if str(age) not in values:
        gaps.append({"code": "transformation_age_clamped_to_rule_table", "person_id": person_id, "age": age, "used_age": int(key)})
    if candidate.isoformat() > rule_pack["valid_to"]:
        projection = rule_pack["planning_projection"]
        if not (projection["valid_from"] <= candidate.isoformat() <= projection["valid_to"]):
            gaps.append({"code": "candidate_date_not_covered_by_inps_rule_pack", "person_id": person_id, "blocking": True})
            return None
        gaps.append({"code": "future_inps_rules_are_planning_projection", "person_id": person_id, "blocking": False})
    return _decimal(values[key], "transformation coefficient")


def _projection_status(rule_pack: dict[str, Any], candidate: date) -> str:
    return "official_encoded_period" if candidate.isoformat() <= rule_pack["valid_to"] else rule_pack["planning_projection"]["status"]


def _revaluation_rate(inps: dict[str, Any], rule_pack: dict[str, Any]) -> Decimal:
    value = inps.get("annual_revaluation_rate") or rule_pack["planning_projection"]["default_annual_revaluation_rate"]
    return _decimal(value, "annual_revaluation_rate")


def _as_of_year(inps: dict[str, Any], candidate: date) -> int:
    return int(inps.get("as_of_year", candidate.year))


def _public_rule_pack(rule_pack: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "rule_pack_id": rule_pack["rule_pack_id"],
        "schema_version": rule_pack["schema_version"],
        "sha256": _file_sha256(path),
        "valid_from": rule_pack["valid_from"],
        "valid_to": rule_pack["valid_to"],
        "projection_status": rule_pack["planning_projection"]["status"],
        "source_refs": rule_pack["source_refs"],
        "limitations": rule_pack["limitations"],
    }


def _load_optional_snapshot(path: Path | None, expected_schema: str, sources: dict[str, str], key: str) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    data = _read_json(path, key)
    if data.get("schema_version") != expected_schema:
        raise WorkExitFeasibilityError(f"Unsupported {key} schema: {data.get('schema_version')}; expected {expected_schema}")
    sources[key] = str(path)
    return data


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkExitFeasibilityError(f"Cannot read {label}: {path}") from exc
    if not isinstance(data, dict):
        raise WorkExitFeasibilityError(f"{label} must be a JSON object: {path}")
    return data


def _write_snapshot(snapshot: dict[str, Any], output_path: Path) -> dict[str, Any]:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise WorkExitFeasibilityError(f"Cannot write work-exit feasibility snapshot: {output_path}") from exc
    return snapshot


def _required_string(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise WorkExitFeasibilityError(f"{field} is required")
    return value


def _required_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise WorkExitFeasibilityError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise WorkExitFeasibilityError(f"{field} must be an ISO date: {value}") from exc


def _positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise WorkExitFeasibilityError(f"{field} must be a positive integer")
    return value


def _age_at(dob: date, at_date: date) -> int:
    return at_date.year - dob.year - ((at_date.month, at_date.day) < (dob.month, dob.day))


def _decimal(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise WorkExitFeasibilityError(f"Invalid decimal for {field}: {value}") from exc


def _money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _ratio(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value.quantize(RATIO, rounding=ROUND_HALF_UP))


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _content_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
