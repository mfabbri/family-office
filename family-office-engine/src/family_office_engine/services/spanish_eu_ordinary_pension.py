"""Bounded ES ordinary pension scenario candidate for coordination with Italy."""

import calendar
import hashlib
import json
import re
from datetime import date
from fractions import Fraction
from typing import Any

RULE_PACK_NAME = "spanish-eu-ordinary-pension-2026-amounts-v0.3.json"
RULE_PACK_SHA256 = "61bfa3b6f9d67471c1b59d474076ab9cc83cc91e757762a1d454acff0f3080ad"
SCHEMA_VERSION = "spanish-eu-ordinary-pension-scenario/v1"


class OrdinaryPensionEvidenceError(ValueError):
    """The scenario falls outside the exact candidate or its evidence."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def load_candidate_rules(payload: bytes) -> dict[str, Any]:
    if hashlib.sha256(payload).hexdigest() != RULE_PACK_SHA256:
        raise OrdinaryPensionEvidenceError(
            "ordinary_2026_rule_hash_mismatch", "The ordinary pension candidate requires the exact versioned rule bytes."
        )
    return json.loads(payload)


def attested_claims_digest(evidence: dict[str, Any], role: str) -> str:
    """Bind an external verification receipt to its original, scope and verifier metadata.

    Authenticity of the external verifier is an input premise, not a digital
    signature supplied by this checksum. Re-pinning a source is not re-verification.
    """
    if role == "historical_ipc":
        claims = evidence["historical_ipc"]
    elif role == "italian_periods":
        claims = {
            "subject": evidence["subject"],
            "contingency_date": evidence["contingency_date"],
            "scenario_sha256": evidence["input_sha256"]["scenario"],
            "scheme": evidence["schemes"]["IT"],
            "duration": evidence["durations"]["IT"],
            "duration_unit": evidence["durations"]["unit"],
        }
    else:
        claims = {field: evidence[field] for field in (
            "subject", "input_sha256", "risk", "contingency_date", "last_spanish_payment_date",
            "last_spanish_contribution_month", "base_window", "schemes", "durations", "coordination_findings",
        )}
    receipt = evidence["attestations"][role]
    verified = {key: receipt[key] for key in (
        "verified_original_sha256", "authority", "status", "verifier_ref",
        "document_locator", "issued_on", "verified_on",
    )}
    canonical = json.dumps({"role": role, "verification": verified, "claims": claims},
                           ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def calculate_ordinary_pension(
    scenario: dict[str, Any],
    reconciliation: dict[str, Any],
    evidence: dict[str, Any],
    rules: dict[str, Any],
    as_of: date,
) -> dict[str, Any]:
    """Calculate scenario amounts after the integration has verified source bytes and subject."""
    scope = rules["scope"]
    contingency = _exact_date(evidence.get("contingency_date"))
    if (
        contingency is None
        or not rules["valid_from"] <= contingency.isoformat() < rules["valid_to"]
        or as_of.isoformat() < rules["sources_verified_on"]
        or scenario.get("retirement_date") != contingency.isoformat()[:7]
        or scenario.get("schema_version") != "it-es-eu-pension-pro-rata-input/v1"
        or scenario.get("scenario") != "ordinary"
        or _unresolved_input_gaps(scenario.get("data_gaps", []))
    ):
        raise OrdinaryPensionEvidenceError("ordinary_2026_date_or_scenario_outside_scope", "The candidate covers December 2026 ordinary old age scenarios.")
    if (
        evidence.get("schema_version") != rules["evidence"]["schema_version"]
        or evidence.get("risk") != scope["risk"]
        or evidence.get("schemes") != {"ES": scope["spanish_scheme"], "IT": scope["italian_scheme"]}
        or evidence.get("coordination_findings") != rules["evidence"]["required_coordination_findings"]
    ):
        raise OrdinaryPensionEvidenceError(
            "ordinary_2026_coordination_scope_unproved",
            "The institution must confirm the schemes, Article 52/56/57, Annex VIII, transition and Annex XI scope.",
        )

    risk_month = _month_number(contingency)
    last_payment_month = risk_month - scope["last_payment_months_before_contingency"]
    end = risk_month - scope["window_end_months_before_contingency"]
    last_payment = _exact_date(evidence.get("last_spanish_payment_date"))
    if (
        last_payment is None
        or _month_number(last_payment) != last_payment_month
        or last_payment > as_of
        or evidence.get("last_spanish_contribution_month") != _month_label(end)
    ):
        raise OrdinaryPensionEvidenceError(
            "ordinary_2026_annex_xi_anchor_unproved", "The last Spanish credited month and its payment in the following month must be proven."
        )
    branches = rules["base_reguladora"]["branches"]
    start = end - max(branch["window_months"] for branch in branches) + 1
    if evidence.get("base_window") != {"first_month": _month_label(start), "last_month": _month_label(end)}:
        raise OrdinaryPensionEvidenceError(
            "ordinary_2026_annex_xi_anchor_unproved", "The institutional record must identify the common Spanish calculation window."
        )
    periods = _insurance_months(scenario.get("insurance_periods"), scope, end)
    if not set(range(start, end + 1)) <= periods["ES"] or max(periods["IT"], default=start) >= start:
        raise OrdinaryPensionEvidenceError(
            "ordinary_2026_base_window_outside_scope", "Complete Spanish coverage and strictly earlier Italian coverage are required."
        )
    durations = _durations(evidence.get("durations"), periods, scope)
    subtotal = sum(durations.values())
    raw_bases = _spanish_bases(reconciliation, start, end, scope["currency"])
    adjusted = _indexed_bases(raw_bases, start, end, evidence.get("historical_ipc"), rules)
    values = _branch_values(adjusted, branches)
    winner = max(values, key=values.__getitem__)
    rate = _accrual(subtotal, rules["percentage"])
    theoretical = values[winner] * rate
    if theoretical > Fraction(scope["maximum_monthly_gross"]):
        raise OrdinaryPensionEvidenceError("ordinary_2026_cap_outside_scope", "The calculated gross amount exceeds the candidate's ceiling.")
    ratio = Fraction(durations["ES"], subtotal)
    return {
        "candidate_month": contingency.isoformat()[:7],
        "theoretical": _amount(theoretical, scope),
        "pro_rata": _amount(theoretical * ratio, scope),
        "ratio": {"spain_months": durations["ES"], "total_eu_non_overlapping_months": subtotal, "value": _rounded(ratio, 6)},
        "calculation": {
            "winning_branch": winner,
            "base_reguladora_by_branch": {branch: _rounded(value, 2) for branch, value in values.items()},
            "accrual_rate": _rounded(rate, 4),
            "last_spanish_payment_date": last_payment.isoformat(),
            "ipc_source_id": rules["cpi"]["source_id"],
            "ipc_reference_month": rules["cpi"]["index_reference_month"],
            "duration_basis": "institution_certified_comparable_months",
            "legal_baseline_verified_on": rules["sources_verified_on"],
        },
    }


def _unresolved_input_gaps(value: Any) -> bool:
    # The legacy wizard asks for a theoretical amount. This path calculates it;
    # only that one derived gap is resolved here. Unknown gaps stay blocking.
    return not isinstance(value, list) or any(
        not isinstance(gap, dict) or gap.get("code") != "missing_spanish_theoretical_amount"
        for gap in value
    )


def _source_name(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _exact_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _month_number(value: date) -> int:
    return value.year * 12 + value.month - 1


def _month_label(value: int) -> str:
    year, month = divmod(value, 12)
    return f"{year:04d}-{month + 1:02d}"


def _month_end(value: int) -> date:
    year, month = divmod(value, 12)
    return date(year, month + 1, calendar.monthrange(year, month + 1)[1])


def _insurance_months(value: Any, scope: dict[str, Any], last_month: int) -> dict[str, set[int]]:
    countries: dict[str, set[int]] = {"ES": set(), "IT": set()}
    if not isinstance(value, list) or not value:
        raise OrdinaryPensionEvidenceError("ordinary_2026_periods_unproved", "Dated compulsory insurance periods are required.")
    for record in value:
        if not isinstance(record, dict):
            raise OrdinaryPensionEvidenceError("ordinary_2026_periods_unproved", "Insurance period objects are required.")
        start = _exact_date(record.get("start_date"))
        end = _exact_date(record.get("end_date"))
        country = record.get("country")
        if (
            country not in countries
            or record.get("period_type") != scope["period_type"]
            or not _source_name(record.get("source_document"))
            or not start or not end or start > end or start.day != 1
            or end != _month_end(_month_number(end))
            or _month_number(end) > last_month
        ):
            raise OrdinaryPensionEvidenceError("ordinary_2026_periods_unproved", "Only full pre-contingency IT/ES compulsory periods are covered.")
        months = set(range(_month_number(start), _month_number(end) + 1))
        if months & (countries["ES"] | countries["IT"]):
            raise OrdinaryPensionEvidenceError("ordinary_2026_period_overlap", "Overlapping or duplicate insurance periods fall outside the candidate.")
        countries[country].update(months)
    return countries


def _durations(value: Any, periods: dict[str, set[int]], scope: dict[str, Any]) -> dict[str, int]:
    if not isinstance(value, dict) or value.keys() != {"unit", "ES", "IT", "coordinated_total"}:
        raise OrdinaryPensionEvidenceError("ordinary_2026_duration_unproved", "An institutional ES, IT and coordinated native duration breakdown is required.")
    es, it, total = value["ES"], value["IT"], value["coordinated_total"]
    if (
        value["unit"] != "institution_certified_comparable_months"
        or any(type(item) is not int for item in (es, it, total))
        or min(es, it) < scope["minimum_country_duration_months"]
        or es != len(periods["ES"]) or it != len(periods["IT"]) or total != es + it
        or total >= scope["exclusive_maximum_total_months"]
    ):
        raise OrdinaryPensionEvidenceError(
            "ordinary_2026_duration_unproved", "Institutional durations must agree with the dated periods and fit the Article 56/57 scope."
        )
    return {"ES": es, "IT": it}


def _positive_fraction(value: Any) -> Fraction:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,8}(?:\.[0-9]{1,15})?", value):
        raise ValueError("Invalid positive decimal.")
    number = Fraction(value)
    if number <= 0:
        raise ValueError("Invalid positive decimal.")
    return number


def _spanish_bases(reconciliation: dict[str, Any], start: int, end: int, currency: str) -> list[Fraction]:
    required = {_month_label(month) for month in range(start, end + 1)}
    bases: dict[str, Fraction] = {}
    try:
        if reconciliation.get("schema_version") != "spanish-contribution-reconciliation/v1":
            raise ValueError("Unrecognized reconciliation.")
        for item in reconciliation["months"]:
            label = item["month"]
            if label not in required:
                continue
            selected = item["selected_base"]
            official = item["official_bases"]
            periods = item.get("periods")
            if (
                label in bases
                or item.get("usable_for_estimator") is not True
                or item.get("covered_by_vida_laboral") is not True
                or item.get("data_gap_codes") or item.get("anomaly_codes")
                or selected.get("source_type") != "official_bases"
                or selected.get("month") != label
                or selected.get("currency") != currency
                or not isinstance(selected.get("source_documents"), list)
                or len(selected["source_documents"]) != 1
                or not _source_name(selected["source_documents"][0])
                or type(selected.get("component_count")) is not int
                or selected["component_count"] != 1
                or not isinstance(official, list) or len(official) != 1
                or not isinstance(official[0], dict)
                or not _source_name(official[0].get("source_document"))
                or not isinstance(periods, list) or not periods
                or any(not isinstance(period, dict) or not _source_name(period.get("source_document")) for period in periods)
                or selected["source_documents"] != [official[0]["source_document"]]
                or _positive_fraction(selected["base_amount"]) != _positive_fraction(official[0]["base_amount"])
            ):
                raise ValueError("Unproven monthly Spanish base.")
            bases[label] = _positive_fraction(selected["base_amount"])
        if bases.keys() != required:
            raise ValueError("Incomplete Spanish base window.")
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        raise OrdinaryPensionEvidenceError("ordinary_2026_spanish_bases_unproved", "Unambiguous official Spanish bases must cover each calculation month.") from exc
    return [bases[_month_label(month)] for month in range(start, end + 1)]


def _indexed_bases(raw: list[Fraction], start: int, end: int, historical: Any, rules: dict[str, Any]) -> list[Fraction]:
    cpi = rules["cpi"]
    reference = _month_label(end - rules["base_reguladora"]["nominal_months"])
    bridge_months = cpi["historical_bridge_months"]
    try:
        if (
            reference != cpi["index_reference_month"]
            or historical["reference_month"] != reference
            or historical["method"] != cpi["historical_bridge_method"]
            or historical["factors"].keys() != set(bridge_months)
        ):
            raise ValueError("Unproven historical CPI coverage.")
        bridge = {month: _positive_fraction(historical["factors"][month]) for month in bridge_months}
        indices = cpi["monthly_index"]
        reference_index = _positive_fraction(indices[reference])
        adjusted = []
        for month, base in enumerate(raw, start):
            label = _month_label(month)
            if label > reference:
                adjusted.append(base)
            elif label in bridge:
                adjusted.append(base * bridge[label])
            else:
                adjusted.append(base * reference_index / _positive_fraction(indices[label]))
        return adjusted
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        raise OrdinaryPensionEvidenceError(
            "ordinary_2026_ipc_unproved", "The official national CPI and exact historical factors must cover the full calculation window."
        ) from exc


def _branch_values(bases: list[Fraction], branches: list[dict[str, Any]]) -> dict[str, Fraction]:
    values = {}
    for branch in branches:
        window = bases[-branch["window_months"]:]
        selected = sorted(window, reverse=True)[:branch["selected_months"]]
        values[branch["id"]] = sum(selected) / Fraction(branch["divisor"])
    return values


def _accrual(months: int, rule: dict[str, Any]) -> Fraction:
    remaining = months - rule["initial_months"]
    rate = Fraction(rule["initial_rate"])
    for segment in rule["segments"]:
        used = min(remaining, segment["months"])
        rate += used * Fraction(segment["rate_per_month"])
        remaining -= used
    return rate


def _rounded(number: Fraction, digits: int) -> str:
    scale = 10 ** digits
    quotient, remainder = divmod(number.numerator * scale, number.denominator)
    quotient += 2 * remainder >= number.denominator
    return f"{quotient // scale}.{quotient % scale:0{digits}d}"


def _amount(monthly: Fraction, scope: dict[str, Any]) -> dict[str, Any]:
    monthly_gross = _rounded(monthly, 2)
    payments = scope["annual_payments"]
    return {
        "monthly_gross_amount": monthly_gross,
        "annual_gross_amount": _rounded(Fraction(monthly_gross) * payments, 2),
        "currency": scope["currency"],
        "payments_per_year": payments,
    }
