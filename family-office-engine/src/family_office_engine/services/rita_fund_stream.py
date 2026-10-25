"""Documentary RITA intake. Values are transcribed, never calculated."""

import hashlib
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


FIELDS = (
    "fund", "benefit_type", "eligibility_status", "request_date", "acceptance_date",
    "requested_capital", "scheduled_start", "scheduled_end", "gross_amount",
    "frequency", "currency", "tax_status", "actual_payments",
)
DATE_FIELDS = {"request_date", "acceptance_date", "scheduled_start", "scheduled_end"}
AMOUNT_FIELDS = {"requested_capital", "gross_amount"}


def _date(value):
    try:
        if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
            return None
        return date.fromisoformat(value)
    except ValueError:
        return None


def _amount(value):
    try:
        if not isinstance(value, str):
            return False
        number = Decimal(value)
        return number.is_finite() and number >= 0
    except InvalidOperation:
        return False


def _valid_value(field, value, as_of):
    if field in DATE_FIELDS:
        return _date(value) is not None
    if field in AMOUNT_FIELDS:
        return _amount(value)
    if field == "actual_payments":
        return (isinstance(value, list) and bool(value) and all(
            isinstance(item, dict) and set(item) == {"date", "gross_amount"}
            and _date(item["date"]) is not None and _date(item["date"]) <= as_of
            and _amount(item["gross_amount"]) for item in value)
            and len({item["date"] for item in value}) == len(value))
    if field == "frequency":
        return value in ("monthly", "quarterly", "semiannual", "annual", "other")
    if field == "currency":
        return isinstance(value, str) and len(value) == 3 and value.isascii() and value.isalpha() and value.isupper()
    if field == "benefit_type":
        return value in ("rita", "other")
    return isinstance(value, str) and bool(value.strip())


def build_rita_fund_stream(data, workspace_root):
    """Validate individually sourced transcriptions and produce a fail-closed snapshot.

    Evidence is a workspace-relative file, identified by SHA-256. This validates
    the binding and metadata; a human remains responsible for transcription.
    """
    if not isinstance(data, dict):
        raise ValueError("input must be an object")
    as_of = _date(data.get("as_of"))
    if as_of is None:
        raise ValueError("as_of must be an ISO date")
    observations = data.get("observations", [])
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")
    root = Path(workspace_root).resolve()
    result = {"schema_version": "rita-fund-stream/v1", "as_of": as_of.isoformat(),
              "facts": {field: None for field in FIELDS}, "net_amount": None,
              "provenance": {}, "data_gaps": [], "status": "incomplete"}
    gaps = result["data_gaps"]
    candidates = {field: [] for field in FIELDS}
    for index, item in enumerate(observations):
        if not isinstance(item, dict) or item.get("field") not in candidates:
            gaps.append({"code": "invalid_observation", "observation": index})
            continue
        field = item["field"]
        value = item.get("value")
        start, end = _date(item.get("coverage_start")), _date(item.get("coverage_end"))
        issuer, ref = item.get("issuer"), item.get("source_ref")
        valid = (_valid_value(field, value, as_of) and isinstance(issuer, str) and bool(issuer.strip())
                 and isinstance(ref, str) and bool(ref.strip()) and start is not None and end is not None
                 and start <= as_of <= end and item.get("basis") == "attested")
        if valid and field in DATE_FIELDS:
            valid = start <= _date(value) <= end
        if valid and field == "actual_payments":
            valid = all(start <= _date(payment["date"]) <= end for payment in value)
        source = None
        if valid:
            try:
                source = (root / ref).resolve()
                valid = not Path(ref).is_absolute() and source.is_relative_to(root) and source.is_file()
            except (OSError, ValueError):
                valid = False
        if not valid:
            gaps.append({"code": "unusable_evidence", "field": field, "observation": index})
            candidates[field].append((None, None))
            continue
        try:
            source_snapshot = source.read_bytes()
            digest = hashlib.sha256(source_snapshot).hexdigest()
        except OSError:
            gaps.append({"code": "unreadable_evidence", "field": field, "observation": index})
            candidates[field].append((None, None))
            continue
        if item.get("sha256") != digest:
            gaps.append({"code": "source_digest_mismatch", "field": field, "observation": index})
            candidates[field].append((None, None))
            continue
        try:
            if source.read_bytes() != source_snapshot:
                gaps.append({"code": "source_changed_during_validation", "field": field, "observation": index})
                candidates[field].append((None, None))
                continue
        except OSError:
            gaps.append({"code": "unreadable_evidence", "field": field, "observation": index})
            candidates[field].append((None, None))
            continue
        candidates[field].append((value, {"source_ref": ref, "sha256": digest, "issuer": issuer,
                                          "coverage_start": start.isoformat(), "coverage_end": end.isoformat(),
                                          "basis": "attested"}))
    for field, items in candidates.items():
        sources = [source for _, source in items if source is not None]
        if sources:
            result["provenance"][field] = sources
        if not items:
            gaps.append({"code": "missing_fact", "field": field})
        elif any(value is None for value, _ in items) or any(value != items[0][0] for value, _ in items):
            gaps.append({"code": "conflicting_or_unusable_fact", "field": field})
        else:
            result["facts"][field] = items[0][0]
    facts = result["facts"]
    original = facts.copy()
    invalidated = set()
    chronology = ("request_date", "acceptance_date", "scheduled_start", "scheduled_end")
    for earlier_index, earlier in enumerate(chronology):
        for later in chronology[earlier_index + 1:]:
            if original[earlier] and original[later] and original[earlier] > original[later]:
                invalidated.update((earlier, later))
                gaps.append({"code": "conflicting_dates", "fields": [earlier, later]})
    if original["acceptance_date"] and original["acceptance_date"] > as_of.isoformat():
        invalidated.add("acceptance_date")
        gaps.append({"code": "future_acceptance", "field": "acceptance_date"})
    if original["request_date"] and original["request_date"] > as_of.isoformat():
        invalidated.add("request_date")
        gaps.append({"code": "future_request", "field": "request_date"})
    if original["actual_payments"] and original["acceptance_date"] and any(
        p["date"] < original["acceptance_date"] for p in original["actual_payments"]
    ):
        invalidated.add("actual_payments")
        gaps.append({"code": "payment_before_acceptance", "field": "actual_payments"})
    if original["actual_payments"] and any(
        (original["scheduled_start"] and p["date"] < original["scheduled_start"])
        or (original["scheduled_end"] and p["date"] > original["scheduled_end"])
        for p in original["actual_payments"]
    ):
        invalidated.add("actual_payments")
        gaps.append({"code": "payment_outside_schedule", "field": "actual_payments"})
    for field in invalidated:
        facts[field] = None
    gaps.append({"code": "net_not_calculated", "field": "net_amount"})
    if facts["benefit_type"] != "rita":
        gaps.append({"code": "non_rita_benefit_excluded" if facts["benefit_type"] == "other"
                     else "rita_benefit_not_attested", "field": "benefit_type"})
        for field in FIELDS:
            facts[field] = None
    result["stream_availability"] = "not_assessed"
    if any(facts[field] is None for field in ("benefit_type", "request_date", "acceptance_date", "requested_capital",
                                              "scheduled_start", "scheduled_end", "gross_amount", "frequency", "currency")) or facts["benefit_type"] != "rita":
        result["stream_availability"] = "unavailable_or_not_assessable"
    result["status"] = "documented_partial" if any(v is not None for v in facts.values()) else "unavailable"
    result["limits"] = ["Transcription requires human verification; no eligibility, acceptance or payment is inferred.",
                        "No tax or financial calculation; not a retirement bridge input."]
    return result
