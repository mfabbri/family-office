"""Evidence-only adapter from public pension services to timeline v2.

The adapter records service/source-version gaps; it never promotes screening,
estimates, candidate dates, coordination metadata, or Annex matching into an
individual event. The v2 schema aggregates jurisdiction branches by event.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from family_office_engine.services.pension_entitlement_timeline import (
    validate_pension_entitlement_timeline,
)
from family_office_engine.services.italian_old_age_eligibility import (
    ItalianOldAgeEligibilityError,
    assess_italian_old_age_eligibility,
    search_first_post_1996_alternative_eligibility_month,
    search_first_post_1996_ordinary_threshold_eligibility_month,
    search_first_pre_1996_ordinary_eligibility_month,
)
from family_office_engine.services.pension_timeline_source_gate import (
    EVENTS,
    JURISDICTIONS,
    PACK_REGISTRY,
    TRANSITION_CLASSES,
    evaluate_pension_timeline_source_branch,
    select_eu_pension_rule_pack,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
FAMILY_RULES_ROOT = REPOSITORY_ROOT / "family-office-rules"
EU_SERVICE_KEYS = ("EU_COORDINATION", "EU_PRO_RATA")

# Separate from candidate source bindings below: approval covers screening only.
# Exact bytes recorded by the w-z-k v0.2 six-file technical review.
ITALIAN_SCREENING_PACK = {
    "path": "italy/2026/inps-old-age-eligibility.json",
    "rule_pack_id": "it.inps-old-age-eligibility.2026-2028.v2",
    "schema_version": "inps-old-age-eligibility-rule-pack/v2",
    "sha256": "2b824d7ca46b4faaa38a83a7cd2d53769bcda6713251e17146a6244a1b0edee9",
    "valid_from": "2026-01-01",
    "valid_to_inclusive": "2028-12-31",
}


def assess_italian_timeline_screening(
    *, facts: dict[str, Any], as_of_date: str,
    search_path: str | None = None,
    monthly_history: list[dict[str, Any]] | None = None,
    rules_root: Path = FAMILY_RULES_ROOT,
) -> dict[str, Any]:
    """Invoke approved v2 screening; never populate an individual event date.

    Candidate assessment and first observed month retain their existing service
    contracts. This adapter does not accept caller-constructed service results or
    activate candidate v3-v6. Facts and history stay in the caller's workspace.
    """
    as_of = _parse_iso_date(as_of_date, "as_of_date")
    if not isinstance(facts, dict):
        raise TypeError("facts must be a mapping")
    searches = {
        "pre_1996_ordinary": search_first_pre_1996_ordinary_eligibility_month,
        "post_1996_ordinary_threshold": search_first_post_1996_ordinary_threshold_eligibility_month,
        "post_1996_alternative": search_first_post_1996_alternative_eligibility_month,
    }
    if search_path is not None and search_path not in searches:
        raise ValueError("Unsupported approved Italian screening path")
    if search_path is None and monthly_history is not None:
        raise ValueError("monthly_history requires an explicit search_path")
    root = rules_root.resolve()
    pack_path = _resolve_under_rules_root(root / ITALIAN_SCREENING_PACK["path"], root)
    try:
        if pack_path is None:
            payload = None
            binding = _missing_binding("Approved screening pack path escapes the Rules root.")
        else:
            payload = _read_rule_pack_bytes(pack_path)
            binding = _verify_pack_file(pack_path, ITALIAN_SCREENING_PACK, root, payload=payload)
    except OSError:
        payload = None
        binding = _missing_binding("Approved screening pack is unavailable.")
    result = None
    gaps = []
    if not binding["verified"]:
        gaps.append({"code": "source_version_missing", "message": binding["reason"], "severity": "blocking"})
    elif search_path is None and (
        not isinstance(facts.get("candidate_date"), str)
        or _screening_candidate_after_as_of(facts["candidate_date"], as_of)
    ):
        gaps.append({"code": "candidate_date_missing_or_invalid", "message": "An observed candidate date no later than as_of_date is required.", "severity": "blocking"})
    else:
        try:
            evidence_gaps = _candidate_screening_evidence_gaps(facts, as_of) if search_path is None else []
            if evidence_gaps:
                gaps.extend(evidence_gaps)
            elif search_path is None:
                result = assess_italian_old_age_eligibility(facts, pack_path, as_of_date, rule_pack_bytes=payload)
            else:
                result = searches[search_path](facts, monthly_history, pack_path, as_of_date, rule_pack_bytes=payload)
            # Detect bytes changing during execution; never expose an unbound result.
            after = _verify_pack_file(pack_path, ITALIAN_SCREENING_PACK, root)
            if not after["verified"]:
                binding = after
                result = None
                gaps.append({"code": "source_version_missing", "message": "Screening pack changed during execution.", "severity": "blocking"})
            else:
                gaps.extend(result.get("data_gaps", []) if result is not None else [])
        except ItalianOldAgeEligibilityError as exc:
            gaps.append({"code": "rule_pack_unavailable_or_stale", "message": str(exc), "severity": "blocking"})
    return {
        "schema_version": "italian-timeline-screening/v1",
        "status": "assessed" if result is not None and result.get("status") == "assessed" else "not_assessed",
        "as_of_date": as_of_date,
        "evidence_role": "path_specific_screening_only",
        "precision": "observed_month" if search_path else "candidate_day_check",
        "rule_pack": binding,
        "screening": result,
        "pension_entitlement": {"status": "not_assessed", **{event: None for event in EVENTS}},
        "data_gaps": gaps,
        "limitations": [
            "A candidate-day check is not a first eligibility date; an observed month is not an exact legal day.",
            "Screening never establishes overall entitlement, recognition, economic effect, amount or payment.",
            "Candidate source bindings and the integrated IT/ES/EU parent gate remain separate.",
        ],
    }


def _screening_candidate_after_as_of(candidate: str, as_of: date) -> bool:
    try:
        return _parse_iso_date(candidate, "candidate_date") > as_of
    except (TypeError, ValueError):
        return True


def _candidate_screening_evidence_gaps(facts: dict[str, Any], as_of: date) -> list[dict[str, str]]:
    """Bind observed evidence to the candidate and report dates, without inference."""
    gaps = []
    candidate = _parse_iso_date(facts["candidate_date"], "candidate_date")
    for key in ("scope_evidence", "cessation_evidence"):
        evidence = facts.get(key)
        try:
            if not isinstance(evidence, dict):
                raise ValueError("missing evidence")
            attested = _parse_iso_date(evidence.get("as_of_date"), "as_of_date")
            if attested > as_of:
                raise ValueError("future evidence")
            if key == "scope_evidence":
                start = _parse_iso_date(evidence.get("coverage_from"), "coverage_from")
                end = _parse_iso_date(evidence.get("coverage_to"), "coverage_to")
                if not start <= candidate <= end <= attested:
                    raise ValueError("profile does not cover candidate")
            elif _parse_iso_date(evidence.get("cessation_date"), "cessation_date") > attested:
                raise ValueError("cessation not yet observed")
        except (TypeError, ValueError):
            gaps.append({"code": "scope_evidence_coverage_missing_or_invalid" if key == "scope_evidence" else "employee_cessation_evidence_missing",
                         "message": f"{key} must be dated, observed by as_of_date and cover the relevant candidate/event.", "severity": "blocking"})
    return gaps

# These are source/version bindings, not entitlement rules. Inclusive valid_to
# values are retained in the source packs and normalized only by this adapter.
DOMESTIC_PACK_REGISTRY: dict[str, dict[str, str]] = {
    "IT": {
        "path": "italy/2026/inps-old-age-eligibility-v3.json",
        "rule_pack_id": "it.inps-old-age-eligibility.2026-2028.v3",
        "schema_version": "inps-old-age-eligibility-rule-pack/v2",
        "sha256": "2f1e5d07d43f6c5af2ac6e6a645a5ae46c13bfbfe691de5eec1c85e6e06e7e32",
        "valid_from": "2026-01-01",
        "valid_to_inclusive": "2028-12-31",
    },
    "ES": {
        "path": "spain/statutory-retirement-general-v3.json",
        "rule_pack_id": "es.seguridad-social.statutory-retirement.general.2026-baseline.v3",
        "schema_version": "spanish-statutory-pension-rule-pack/v2",
        "sha256": "9b5d0acbadb2b49d7f314c3739f447fb7d6397cf3cbeb390e4e8dd89c2b2b99c",
        "valid_from": "2026-01-01",
        "valid_to_inclusive": "2036-12-31",
    },
}


@dataclass(frozen=True)
class EUPensionRuleSelectionInputs:
    """Externally established temporal facts consumed by the reviewed selector.

    These inputs are not a selector result and do not establish eligibility.
    The producer executes the selector itself and never accepts a caller-built
    ``candidate_selected`` mapping.
    """

    member_state: str | None
    applicable_date: str | None
    right_acquisition_date: str | None
    contingency_date: str | None
    transition_classification: str | None
    pre_application_periods: str | None


@dataclass(frozen=True)
class PublicPensionEvidenceBundle:
    """In-memory outputs and source paths supplied by deterministic services.

    ``service_snapshots`` keys are IT, ES, EU_COORDINATION, and EU_PRO_RATA.
    Rule-pack paths identify the exact files passed to those services. EU
    temporal selector inputs are explicit; the selector output is always
    recomputed internally. No snapshot or personal fact is written here.
    """

    service_snapshots: Mapping[str, Mapping[str, Any] | None] = field(default_factory=dict)
    rule_pack_paths: Mapping[str, Path | str] = field(default_factory=dict)
    eu_selector_inputs: EUPensionRuleSelectionInputs | None = None


@dataclass(frozen=True)
class BranchAssessment:
    """Internal jurisdiction/event assessment; never persisted by timeline v2."""

    event: str
    jurisdiction: str
    status: str
    date: None
    payer: None
    amount: None
    evidence_role: str
    rule_pack_id: str | None
    digest_sha256: str | None
    valid_from: str | None
    valid_to_exclusive: str | None
    data_gaps: tuple[dict[str, str], ...]


def normalize_inclusive_validity(valid_from: str, valid_to_inclusive: str | None) -> tuple[str, str | None]:
    """Normalize a source pack's inclusive end date to a half-open interval."""
    start = _parse_iso_date(valid_from, "valid_from")
    if valid_to_inclusive is None:
        return start.isoformat(), None
    end = _parse_iso_date(valid_to_inclusive, "valid_to")
    if end < start:
        raise ValueError("valid_to must not precede valid_from")
    try:
        end_exclusive = end + timedelta(days=1)
    except OverflowError as exc:
        raise ValueError("valid_to cannot be normalized beyond the maximum date") from exc
    return start.isoformat(), end_exclusive.isoformat()


def map_public_service_branches(
    evidence_bundle: PublicPensionEvidenceBundle,
    *,
    rules_root: Path = FAMILY_RULES_ROOT,
) -> tuple[BranchAssessment, ...]:
    """Map service metadata to 15 fail-closed branches without inferring dates."""
    if not isinstance(evidence_bundle, PublicPensionEvidenceBundle):
        raise TypeError("evidence_bundle must be PublicPensionEvidenceBundle")
    root = rules_root.resolve()
    eu_selection = _run_eu_selector(evidence_bundle, root)
    bindings = {
        "IT": _domestic_binding("IT", evidence_bundle, root),
        "ES": _domestic_binding("ES", evidence_bundle, root),
        "EU": _eu_binding(evidence_bundle, root, eu_selection),
    }
    assessments: list[BranchAssessment] = []
    for event in EVENTS:
        for jurisdiction in JURISDICTIONS:
            binding = bindings[jurisdiction]
            selection = eu_selection if jurisdiction == "EU" else None
            source_result = evaluate_pension_timeline_source_branch(
                event=event,
                jurisdiction=jurisdiction,
                rule_selection=selection,
            )
            selector_gap = _selector_gap(selection) if jurisdiction == "EU" else None
            if selector_gap is not None:
                code = selector_gap["code"]
                message = selector_gap["message"]
            elif not binding["verified"]:
                code = "source_version_missing"
                message = binding["reason"]
            elif source_result["data_gaps"][0]["code"] != "event_evidence_missing":
                code = source_result["data_gaps"][0]["code"]
                message = source_result["data_gaps"][0]["message"]
            else:
                # A verified pack is not event evidence. Individual evidence is
                # still absent, so every event remains not_assessed.
                code = "event_evidence_missing"
                message = (
                    f"{event} for {jurisdiction} remains not_assessed: "
                    "event-specific primary evidence is absent."
                )
            assessments.append(
                BranchAssessment(
                    event=event,
                    jurisdiction=jurisdiction,
                    status="not_assessed",
                    date=None,
                    payer=None,
                    amount=None,
                    evidence_role="diagnostic_only",
                    rule_pack_id=binding["rule_pack_id"],
                    digest_sha256=binding["digest_sha256"],
                    valid_from=binding["valid_from"],
                    valid_to_exclusive=binding["valid_to_exclusive"],
                    data_gaps=({"code": code, "message": message, "severity": "blocking"},),
                )
            )
    return tuple(assessments)


def _selector_gap(selection: Mapping[str, Any]) -> dict[str, str] | None:
    """Keep temporal/legal selection gaps distinct from source binding gaps."""
    if selection.get("status") == "candidate_selected":
        return None
    gaps = selection.get("data_gaps")
    if not isinstance(gaps, list) or not gaps or not isinstance(gaps[0], Mapping):
        return None
    code = gaps[0].get("code")
    message = gaps[0].get("message")
    if not isinstance(code, str) or not isinstance(message, str):
        return None
    return {"code": code, "message": message, "severity": "blocking"}


def produce_source_bound_pension_timeline(
    *,
    member_id: str,
    as_of_date: str,
    evidence_bundle: PublicPensionEvidenceBundle,
    rules_root: Path = FAMILY_RULES_ROOT,
) -> dict[str, Any]:
    """Build and validate a v2 snapshot; all five dates remain null by design."""
    if not isinstance(member_id, str) or not member_id.strip():
        raise ValueError("member_id is required")
    _parse_iso_date(as_of_date, "as_of_date")
    assessments = map_public_service_branches(evidence_bundle, rules_root=rules_root)
    event_values: dict[str, dict[str, Any]] = {}
    all_gaps: list[dict[str, str]] = []
    for event in EVENTS:
        event_gaps = [gap for branch in assessments if branch.event == event for gap in branch.data_gaps]
        event_values[event] = {
            "event_kind": event,
            "status": "not_assessed",
            "date": None,
            "evidence": [],
            "data_gaps": event_gaps,
        }
        if event == "economic_effective_date":
            event_values[event]["retroactivity_status"] = "not_assessed"
        all_gaps.extend(event_gaps)
    all_gaps.append({
        "code": "amount_basis_unknown",
        "message": "No source-bound individual pension amount basis is supplied to this evidence-only producer.",
        "severity": "blocking",
    })
    snapshot = {
        "schema_version": "pension-entitlement-timeline/v2",
        "record_type": "PensionEntitlementTimeline",
        "status": "not_assessed",
        "member_id": member_id,
        "as_of_date": as_of_date,
        "human_review_required": True,
        "events": event_values,
        "pension_amount_basis": {
            "basis_state": "unknown",
            "tax_jurisdiction": None,
            "tax_period": None,
            "source_evidence": [],
            "data_gaps": [{
                "code": "amount_basis_unknown",
                "message": "No source-bound individual pension amount basis is supplied to this evidence-only producer.",
                "severity": "blocking",
            }],
        },
        "data_gaps": all_gaps,
        "limitations": [
            "Service screening, candidate dates, estimates, and pack metadata are diagnostic only.",
            "No individual event date, entitlement, recognition, effective date, payer, payment, or amount is inferred.",
            "Timeline v2 aggregates jurisdiction branches into five events; the 15 branch assessments remain internal.",
        ],
    }
    return validate_pension_entitlement_timeline(snapshot)


def _domestic_binding(
    jurisdiction: str,
    bundle: PublicPensionEvidenceBundle,
    rules_root: Path,
) -> dict[str, Any]:
    spec = DOMESTIC_PACK_REGISTRY[jurisdiction]
    snapshot = bundle.service_snapshots.get(jurisdiction)
    metadata = _service_pack_metadata(snapshot, jurisdiction)
    expected_path = (rules_root / spec["path"]).resolve()
    supplied_path = bundle.rule_pack_paths.get(jurisdiction)
    snapshot_path = metadata.get("path")
    path_value = supplied_path if supplied_path is not None else snapshot_path
    if not isinstance(path_value, (str, Path)):
        return _missing_binding("domestic service did not provide its canonical rule-pack path")
    resolved_path = _resolve_under_rules_root(path_value, rules_root)
    if resolved_path is None or resolved_path != expected_path:
        return _missing_binding("domestic service path does not match the exact candidate pack")
    if snapshot_path is not None:
        snapshot_resolved = _resolve_under_rules_root(snapshot_path, rules_root)
        if snapshot_resolved != expected_path:
            return _missing_binding("service snapshot path does not match the supplied candidate pack")
    if metadata.get("rule_pack_id") != spec["rule_pack_id"]:
        return _missing_binding("service snapshot rule-pack ID is not the exact current candidate")
    if metadata.get("schema_version") != spec["schema_version"]:
        return _missing_binding("service snapshot does not attest the exact candidate schema version")
    return _verify_pack_file(expected_path, spec, rules_root)


def _run_eu_selector(
    bundle: PublicPensionEvidenceBundle, rules_root: Path
) -> dict[str, Any]:
    inputs = bundle.eu_selector_inputs
    if not isinstance(inputs, EUPensionRuleSelectionInputs):
        return {
            "status": "not_assessed",
            "rule_pack_id": None,
            "digest_sha256": None,
            "transition_classification": None,
            "activation_allowed": False,
            "human_review_required": True,
            "data_gaps": [{
                "code": "legal_applicability_unknown",
                "message": "Explicit EU temporal selector inputs are missing.",
                "severity": "blocking",
            }],
        }
    return select_eu_pension_rule_pack(
        member_state=inputs.member_state,
        applicable_date=inputs.applicable_date,
        right_acquisition_date=inputs.right_acquisition_date,
        contingency_date=inputs.contingency_date,
        transition_classification=inputs.transition_classification,
        pre_application_periods=inputs.pre_application_periods,
        rules_root=rules_root / "cross-border",
    )


def _eu_binding(
    bundle: PublicPensionEvidenceBundle,
    rules_root: Path,
    selection: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(selection, Mapping) or selection.get("status") != "candidate_selected":
        return _missing_binding("the EU source selector did not select an exact candidate")
    pack_id = selection.get("rule_pack_id")
    spec = PACK_REGISTRY.get(pack_id) if isinstance(pack_id, str) else None
    if (
        spec is None
        or selection.get("digest_sha256") != spec["sha256"]
        or selection.get("activation_allowed") is not False
        or selection.get("human_review_required") is not True
        or selection.get("transition_classification") not in TRANSITION_CLASSES
        or not isinstance(selection.get("data_gaps"), list)
        or selection.get("data_gaps")
    ):
        return _missing_binding("EU selector identity or activation guard does not match the reviewed registry")
    if (
        (pack_id.endswith("v11.1.1") and selection["transition_classification"] != "acquired_before_application_date")
        or (pack_id.endswith("v12.1.1") and selection["transition_classification"] == "acquired_before_application_date")
    ):
        return _missing_binding("EU selector transition classification conflicts with the selected pack period")
    expected_path = (rules_root / "cross-border" / spec["path"]).resolve()
    supplied_path = bundle.rule_pack_paths.get("EU")
    if supplied_path is None or _resolve_under_rules_root(supplied_path, rules_root) != expected_path:
        return _missing_binding("EU candidate path is missing or non-canonical")
    for service_key in EU_SERVICE_KEYS:
        snapshot = bundle.service_snapshots.get(service_key)
        metadata = _service_pack_metadata(snapshot, service_key)
        if (
            metadata.get("rule_pack_id") != pack_id
            or metadata.get("sha256") != spec["sha256"]
            or metadata.get("valid_from") != spec["valid_from"].isoformat()
            or metadata.get("valid_to") != spec["valid_to"].isoformat()
        ):
            return _missing_binding(f"{service_key} does not expose the same exact EU candidate binding")
        if _resolve_under_rules_root(metadata.get("path"), rules_root) != expected_path:
            return _missing_binding(f"{service_key} path does not match the exact EU candidate")
    domestic_spec = {
        "path": str(expected_path.relative_to(rules_root)),
        "rule_pack_id": pack_id,
        "schema_version": "eu-pension-coordination-rule-pack/v2",
        "sha256": spec["sha256"],
        "valid_from": spec["valid_from"].isoformat(),
        "valid_to_inclusive": spec["valid_to"].isoformat(),
    }
    return _verify_pack_file(expected_path, domestic_spec, rules_root)


def _verify_pack_file(path: Path, spec: Mapping[str, str], rules_root: Path,
                      *, payload: bytes | None = None) -> dict[str, Any]:
    raw_path = _resolve_under_rules_root(path, rules_root)
    if raw_path is None:
        return _missing_binding("rule-pack path escapes the approved Rules root")
    try:
        payload = _read_rule_pack_bytes(raw_path) if payload is None else payload
        actual_digest = hashlib.sha256(payload).hexdigest()
        pack = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _missing_binding("exact rule-pack bytes are unavailable or invalid")
    if actual_digest != spec["sha256"] or pack.get("rule_pack_id") != spec["rule_pack_id"]:
        return _missing_binding("rule-pack content digest or identity differs from the reviewed candidate")
    if pack.get("schema_version") != spec["schema_version"]:
        return _missing_binding("rule-pack schema version differs from the reviewed candidate")
    if pack.get("valid_from") != spec["valid_from"] or pack.get("valid_to") != spec["valid_to_inclusive"]:
        return _missing_binding("rule-pack validity period differs from the reviewed candidate")
    try:
        valid_from, valid_to_exclusive = normalize_inclusive_validity(
            spec["valid_from"], spec["valid_to_inclusive"]
        )
    except ValueError:
        return _missing_binding("rule-pack validity period cannot be normalized safely")
    return {
        "verified": True,
        "reason": "event-specific primary evidence is absent.",
        "rule_pack_id": spec["rule_pack_id"],
        "digest_sha256": actual_digest,
        "valid_from": valid_from,
        "valid_to_exclusive": valid_to_exclusive,
    }


def _service_pack_metadata(snapshot: Mapping[str, Any] | None, service_key: str) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        return {}
    nested = snapshot.get("rule_pack")
    metadata = dict(nested) if isinstance(nested, Mapping) else {}
    if service_key == "IT" and "rule_pack_id" not in metadata:
        metadata["rule_pack_id"] = snapshot.get("rule_pack_id")
    return metadata


def _resolve_under_rules_root(value: Any, rules_root: Path) -> Path | None:
    if not isinstance(value, (str, Path)) or not str(value):
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = rules_root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(rules_root)
    except ValueError:
        return None
    return resolved


def _read_rule_pack_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _missing_binding(reason: str) -> dict[str, Any]:
    return {
        "verified": False,
        "reason": reason + " Event outputs remain not_assessed.",
        "rule_pack_id": None,
        "digest_sha256": None,
        "valid_from": None,
        "valid_to_exclusive": None,
    }


def _parse_iso_date(value: str, label: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{label} must use canonical ISO YYYY-MM-DD form")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must use canonical ISO YYYY-MM-DD form") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{label} must use canonical ISO YYYY-MM-DD form")
    return parsed
