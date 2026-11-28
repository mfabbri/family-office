"""Compose pension scenarios and source-bound, per-benefit observed event timelines."""

import hashlib
import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from family_office_engine.services.it_es_eu_pension_pro_rata import calculate_it_es_eu_pension_pro_rata
from family_office_engine.services.pension_entitlement_timeline import (
    EVENT_NAMES,
    PensionEntitlementTimelineError,
    _within_workspace,
    _workspace_path,
    validate_pension_entitlement_timeline,
)
from family_office_engine.services.spanish_eu_theoretical_pension import calculate_spanish_eu_theoretical_pension
from family_office_engine.services.work_exit_feasibility import (
    INPUT_SCHEMA_VERSION as WORK_EXIT_INPUT_VERSION,
    inps_documentary_projection,
    load_inps_projection_rule_pack,
    project_inps_for_adult,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_ROOT = Path(__file__).resolve().parents[3] / "schemas"
INPUT_SCHEMA_VERSION = "pension-timeline-integration-input/v1"
SCHEMA_VERSION = "pension-timeline-integration/v1"
_REQUEST_VALIDATOR = Draft202012Validator(
    json.loads((SCHEMA_ROOT / "pension-timeline-integration-input.schema.json").read_text(encoding="utf-8")),
    format_checker=FormatChecker(),
)
_REPORT_VALIDATOR = Draft202012Validator(
    json.loads((SCHEMA_ROOT / "pension-timeline-integration.schema.json").read_text(encoding="utf-8")),
    format_checker=FormatChecker(),
)
_IDENTITY_FIELDS = ("household_id", "member_id", "jurisdiction", "stream_id")
_OBSERVED_ROLES = {
    "eligibility_date": ("individual_decision", "individual_institutional_decision"),
    "requirements_met_date": ("individual_decision", "individual_institutional_decision"),
    "official_recognition_date": ("individual_decision", "individual_institutional_decision"),
    "economic_effective_date": ("economic_effective_basis", "individual_institutional_decision"),
    "first_cash_payment_date": ("cash_availability_confirmation", "individual_payment_evidence"),
}
_MISSING_EVENT_CODES = {
    "official_recognition_date": "decision_evidence_missing",
    "economic_effective_date": "economic_effective_evidence_missing",
    "first_cash_payment_date": "cash_availability_evidence_missing",
}
_LIMITATIONS = [
    "Observed dates are supported only within externally confirmed source bindings and remain subject to human review.",
    "Institutional authenticity is outside the scope of integration. Estimates and cessation do not establish any entitlement event.",
]
_SOURCE_ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, ArithmeticError)


class PensionTimelineIntegrationError(ValueError):
    """Invalid transport, workspace path or integration request."""


class _UnresolvedTransitionScope(PensionTimelineIntegrationError):
    """An externally established transition classification is missing."""


class _CapturedSources:
    def __init__(self, workspace: Path, rules: Path):
        self.workspace = workspace
        self.rules = rules
        self.payloads: dict[Path, bytes] = {}

    def _read(self, path: Path) -> bytes:
        if path not in self.payloads:
            self.payloads[path] = path.read_bytes()
        return self.payloads[path]

    def local(self, ref: str) -> tuple[Path, bytes]:
        path = _workspace_path(self.workspace, ref)
        return path, self._read(path)

    def rule(self, directory: str, name: str) -> tuple[Path, bytes, dict[str, str]]:
        relative = Path(directory, name)
        path = (self.rules / relative).resolve()
        path.relative_to(self.rules)
        payload = self._read(path)
        return path, payload, _reference(relative.as_posix(), payload)


def build_pension_timeline_integration(
    input_path: Path,
    output_path: Path,
    *,
    workspace_root: Path | None = None,
    rules_root: Path | None = None,
    request_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Read an integration request and publish its report within the workspace."""
    captures = _captures(workspace_root, rules_root)
    try:
        source = input_path.resolve()
        destination = output_path.resolve()
        _within_workspace(captures.workspace, source, "integration input")
        _within_workspace(captures.workspace, destination, "integration output")
        if request_bytes is not None:
            captures.payloads[source] = request_bytes
        request = _json_object(captures._read(source))
        _guard_output_sources(destination, source, request, captures)
        report = _integrate(request, captures)
        if destination in captures.payloads:
            raise PensionTimelineIntegrationError("Timeline integration output must differ from all captured source paths.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, PensionEntitlementTimelineError, UnicodeError, json.JSONDecodeError) as exc:
        raise PensionTimelineIntegrationError("Cannot read or write the workspace timeline integration report.") from exc
    return report


def _guard_output_sources(destination: Path, request_path: Path, request: dict[str, Any], captures: _CapturedSources) -> None:
    """Protect declared sources even when an assessment never reads them."""
    def references(value):
        if isinstance(value, str) and value.startswith("workspace-ref:"):
            yield value
        elif isinstance(value, dict):
            for item in value.values():
                yield from references(item)
        elif isinstance(value, list):
            for item in value:
                yield from references(item)
    declared_paths = set()
    for ref in references(request):
        try:
            declared_paths.add(_workspace_path(captures.workspace, ref))
        except (ValueError, OSError):
            # Assessment isolates the invalid source to its stream. It cannot
            # collide with an output already confined inside this workspace.
            continue
    if destination == request_path or destination in declared_paths:
        raise PensionTimelineIntegrationError("Timeline output must differ from every declared source, including unused sources.")
    if destination.exists():
        prior = _json_object(destination.read_bytes())
        if not _REPORT_VALIDATOR.is_valid(prior) or prior.get("household_id") != request.get("household_id"):
            raise PensionTimelineIntegrationError("An existing non-report source cannot be overwritten by the timeline report.")


def integrate_pension_timeline(
    request: dict[str, Any],
    *,
    workspace_root: Path | None = None,
    rules_root: Path | None = None,
) -> dict[str, Any]:
    """Build the timeline report from a prepared request and captured source files."""
    return _integrate(request, _captures(workspace_root, rules_root))


def _captures(workspace_root: Path | None, rules_root: Path | None) -> _CapturedSources:
    workspace = (workspace_root or REPOSITORY_ROOT / "family-office-workspace").resolve()
    if not workspace.is_dir():
        raise PensionTimelineIntegrationError("Timeline integration requires an existing workspace.")
    configured_rules = os.environ.get("FO_RULES_PATH")
    default_rules = Path(configured_rules).expanduser() if configured_rules else REPOSITORY_ROOT / "family-office-rules"
    return _CapturedSources(workspace, (rules_root or default_rules).resolve())


def _integrate(request: dict[str, Any], captures: _CapturedSources) -> dict[str, Any]:
    if not _REQUEST_VALIDATOR.is_valid(request):
        raise PensionTimelineIntegrationError("Invalid pension timeline integration request.")
    household_id = request["household_id"]
    as_of = date.fromisoformat(request["as_of_date"])
    keys = [(stream["member_id"], stream["jurisdiction"], stream["stream_id"]) for stream in request["streams"]]
    if len(set(keys)) != len(keys):
        raise PensionTimelineIntegrationError("Pension benefit streams must have unique member, jurisdiction and stream identity.")
    stream_members = {member for member, _, _ in keys}
    members = request.get("household_members", sorted(stream_members))
    if stream_members.difference(members):
        raise PensionTimelineIntegrationError("Each stream member must appear in household_members.")
    gaps = [
        _gap("member_pension_evidence_missing", "No benefit stream was supplied for this household member.", member_id=member)
        for member in members if member not in stream_members
    ]
    if not members:
        gaps.append(_gap("household_members_missing", "No household members or pension benefit streams were declared."))

    streams = [_stream(household_id, stream, as_of, captures) for stream in request["streams"]]
    gaps.extend(
        {**{field: stream[field] for field in _IDENTITY_FIELDS}, **gap}
        for stream in streams for gap in stream["data_gaps"]
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "PensionTimelineIntegration",
        "status": "partial" if any(item["timeline_v2"]["status"] == "partial" for item in streams) else "not_assessed",
        "household_id": household_id,
        "household_members": members,
        "as_of_date": as_of.isoformat(),
        "human_review_required": True,
        "streams": streams,
        "data_gaps": gaps,
        "limitations": _LIMITATIONS.copy(),
    }
    if not _REPORT_VALIDATOR.is_valid(report):
        raise PensionTimelineIntegrationError("The integrated report violates its output contract.")
    return report


def _stream(household_id: str, stream: dict[str, Any], as_of: date, captures: _CapturedSources) -> dict[str, Any]:
    identity = {"household_id": household_id, **{key: stream[key] for key in _IDENTITY_FIELDS[1:]}}
    timeline, bindings, gaps = _observed_timeline(identity, stream.get("observed_event_refs", []), as_of, captures)
    inps = theoretical = pro_rata = benchmark = None
    if stream["jurisdiction"] == "IT":
        declarations = stream.get("inps", {})
        inps, scenario_gaps = _inps_projection(identity, declarations, as_of, captures)
        benchmark, documentary_gaps = _documentary_benchmark(identity, declarations, captures)
        gaps.extend(scenario_gaps + documentary_gaps)
    else:
        theoretical, pro_rata, scenario_gaps = _spanish_projections(identity, stream.get("spanish", {}), as_of, captures)
        gaps.extend(scenario_gaps)
    gaps.extend(
        {**gap, "event_kind": event_kind}
        for event_kind, event in timeline["events"].items() for gap in event["data_gaps"]
    )
    cessation = stream.get("cessation_date")
    return {
        **identity,
        "timeline_v2": timeline,
        "compatibility_v1": _compatibility_view(timeline),
        "observed_event_bindings": bindings,
        "scenario_projection": {
            "status": "scenario_projection",
            "cessation_date": cessation,
            "inps": inps,
            "spanish_theoretical": theoretical,
            "spanish_pro_rata": pro_rata,
        },
        "documentary_benchmark": benchmark,
        "data_gaps": gaps,
    }


def _observed_timeline(
    identity: dict[str, str], refs: list[str], as_of: date, captures: _CapturedSources,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    timeline = _blank_timeline(identity["member_id"], as_of)
    gaps: list[dict[str, Any]] = []
    supported: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {event: [] for event in EVENT_NAMES}
    failed: dict[str, str] = {}
    evidence_bytes: dict[str, bytes] = {}
    for ref in refs:
        event_kind = None
        try:
            path, payload = captures.local(ref)
            binding = _json_object(payload)
            kind = binding.get("event_kind")
            event_kind = kind if kind in EVENT_NAMES else None
            if event_kind is None:
                raise PensionTimelineIntegrationError("Unrecognized observed event kind.")
            event, metadata = _bound_event(identity, event_kind, binding, as_of, path, captures, evidence_bytes)
            candidate = {**timeline, "events": {**timeline["events"], event_kind: event}}
            validate_pension_entitlement_timeline(candidate, workspace_root=captures.workspace, source_bytes=evidence_bytes)
            supported[event_kind].append((event, {"binding": _reference(ref, payload), **metadata}))
        except _SOURCE_ERRORS as exc:
            gap_code = "transitional_branch_unknown" if isinstance(exc, _UnresolvedTransitionScope) else "observed_event_binding_invalid"
            if event_kind is not None:
                failed[event_kind] = gap_code
            gaps.append(_gap(
                gap_code,
                "An observed event binding failed identity, source content, event, coverage or review checks.",
                binding_ref=ref,
                event_kind=event_kind,
            ))

    published_bindings = {}
    for event_kind, claims in supported.items():
        if event_kind in failed:
            timeline["events"][event_kind] = _unknown_event(event_kind, "A supplied observed event binding could not be verified.")
            if failed[event_kind] == "transitional_branch_unknown":
                timeline["events"][event_kind]["data_gaps"] = [_gap("transitional_branch_unknown", "The transition scope was not externally established for this event.")]
        elif claims:
            dates = {event["date"] for event, _ in claims}
            retroactivity = {event.get("retroactivity_status") for event, _ in claims}
            transition_scopes = {
                tuple(sorted({proof["transition_scope"]["status"] for proof in event["evidence"]}))
                for event, _ in claims
            }
            canonical_scopes = {}
            scope_conflict = False
            for claim, _ in claims:
                for proof in claim["evidence"]:
                    for scope in proof["transition_scope"]["scope_evidence"]:
                        provenance = scope["source_provenance"]
                        identity = (_workspace_path(captures.workspace, provenance["source_ref"]),
                                    provenance["digest_sha256"].lower(), provenance["act_identifier"],
                                    provenance["article_identifier"], provenance["source_version"], event_kind)
                        status = scope["scope"]["transition_status"]
                        if identity in canonical_scopes and canonical_scopes[identity] != status:
                            scope_conflict = True
                        canonical_scopes[identity] = status
            if len(dates) != 1 or len(retroactivity) != 1 or len(transition_scopes) != 1 or scope_conflict:
                timeline["events"][event_kind] = _unknown_event(event_kind, "Conflicting observed event bindings require resolution.")
                timeline["events"][event_kind]["data_gaps"] = [_gap("transitional_branch_unknown", "Confirmed sources disagree on the event or transition scope.")]
                gaps.append(_gap("observed_event_conflict", "Confirmed bindings disagree on the event date or scope.", event_kind=event_kind))
                continue
            event = dict(claims[0][0])
            event["evidence"] = [proof for item, _ in claims for proof in item["evidence"]]
            timeline["events"][event_kind] = event
            published_bindings[event_kind] = [metadata for _, metadata in claims]

    timeline["status"] = "partial" if published_bindings else "not_assessed"
    timeline["data_gaps"] = [gap for event in timeline["events"].values() for gap in event["data_gaps"]]
    validate_pension_entitlement_timeline(timeline, workspace_root=captures.workspace, source_bytes=evidence_bytes)
    return timeline, published_bindings, gaps


def _bound_event(
    identity: dict[str, str],
    event_kind: str,
    binding: dict[str, Any],
    as_of: date,
    binding_path: Path,
    captures: _CapturedSources,
    evidence_bytes: dict[str, bytes],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if any(binding.get(key) != identity[key] for key in _IDENTITY_FIELDS):
        raise PensionTimelineIntegrationError("Observed event subject or benefit stream differs.")
    observed_at = _date(binding["date"])
    verification = binding["verification"]
    proof_date = _date(verification["verified_on"])
    verifier = verification["verifier_ref"]
    if (
        verification.get("status") != "externally_verified"
        or not isinstance(verifier, str) or not verifier.strip()
        or not (observed_at <= proof_date <= as_of)
    ):
        raise PensionTimelineIntegrationError("An external individual source verification is required.")
    source_ref = verification["source_ref"]
    source_path, source_payload = captures.local(source_ref)
    expected_digest = verification["digest_sha256"].lower()
    if source_path == binding_path or _digest(source_payload) != expected_digest:
        raise PensionTimelineIntegrationError("Observed event verification does not match the individual source bytes.")
    _verify_structured_source(source_payload, identity, event_kind, observed_at)

    role, authority = _OBSERVED_ROLES[event_kind]
    matching_proof = False
    scope_statuses = {}
    evidence = binding["evidence"]
    for proof in evidence:
        if proof["transition_scope"]["status"] == "unknown":
            raise _UnresolvedTransitionScope("The transition status must be established externally before this event can be supported.")
        provenance = proof["source_provenance"]
        main_ref = provenance["source_ref"]
        main_path, main_payload = captures.local(main_ref)
        if main_path == binding_path or provenance["jurisdiction"] not in {identity["jurisdiction"], "EU"}:
            raise PensionTimelineIntegrationError("Evidence does not match the observed benefit jurisdiction or source.")
        if provenance["source_authority"] in {"individual_institutional_decision", "individual_payment_evidence"}:
            if (
                main_ref != source_ref or provenance["digest_sha256"].lower() != expected_digest
                or provenance["jurisdiction"] != identity["jurisdiction"]
            ):
                raise PensionTimelineIntegrationError("Individual evidence is outside the verified source binding.")
            matching_proof |= proof["evidence_role"] == role and provenance["source_authority"] == authority
            if not (_date(provenance["retrieved_on"]) <= _date(provenance["reviewed_on"]) <= proof_date):
                raise PensionTimelineIntegrationError("Individual evidence review dates are inconsistent.")
        evidence_bytes[main_ref] = main_payload
        for scope in proof["transition_scope"]["scope_evidence"]:
            scope_provenance = scope["source_provenance"]
            scope_ref = scope_provenance["source_ref"]
            scope_path, scope_payload = captures.local(scope_ref)
            if scope_path in {source_path, binding_path} or scope_provenance["jurisdiction"] not in {identity["jurisdiction"], "EU"}:
                raise PensionTimelineIntegrationError("Transition scope requires distinct, relevant source evidence.")
            scope_identity = (scope_path, scope_provenance["act_identifier"], scope_provenance["article_identifier"], scope_provenance["source_version"])
            status = scope["scope"]["transition_status"]
            if scope_identity in scope_statuses and scope_statuses[scope_identity] != status:
                raise PensionTimelineIntegrationError("The same transition source has contradictory scope within this event binding.")
            scope_statuses[scope_identity] = status
            evidence_bytes[scope_ref] = scope_payload
    if not matching_proof:
        raise PensionTimelineIntegrationError("The verified source does not carry the required individual event evidence role.")
    result = {"event_kind": event_kind, "date": observed_at.isoformat(), "status": "supported", "evidence": evidence, "data_gaps": []}
    if event_kind == "economic_effective_date":
        result["retroactivity_status"] = binding.get("retroactivity_status", "not_assessed")
    return result, {
        "source": _reference(source_ref, source_payload),
        "verification_scope": "externally_confirmed_subject_stream_event_and_date",
        "verified_on": proof_date.isoformat(),
    }


def _verify_structured_source(payload: bytes, identity: dict[str, str], event_kind: str, observed_at: date) -> None:
    # An externally reviewed document can be binary. A structured individual source
    # that declares event fields must also reconcile those fields independently.
    if not payload.lstrip().startswith(b"{"):
        return
    source = _json_object(payload)
    if source.get("schema_version") != "pension-observed-event-source/v1":
        return
    expected = {**identity, "event_kind": event_kind, "date": observed_at.isoformat()}
    if any(source.get(field) != value for field, value in expected.items()):
        raise PensionTimelineIntegrationError("Structured individual source contradicts its observed event binding.")


def _blank_timeline(member: str, as_of: date) -> dict[str, Any]:
    return {
        "schema_version": "pension-entitlement-timeline/v2",
        "record_type": "PensionEntitlementTimeline",
        "status": "not_assessed",
        "member_id": member,
        "as_of_date": as_of.isoformat(),
        "human_review_required": True,
        "events": {event: _unknown_event(event) for event in EVENT_NAMES},
        "pension_amount_basis": {
            "basis_state": "unknown", "tax_jurisdiction": None, "tax_period": None, "source_evidence": [],
            "data_gaps": [_gap("amount_basis_unknown", "An individual, documented pension amount basis was not assessed.")],
        },
        "data_gaps": [_gap("event_evidence_missing", "Individual event evidence is missing.")],
        "limitations": _LIMITATIONS.copy(),
    }


def _unknown_event(event_kind: str, message: str = "Individual evidence for this benefit event is missing.") -> dict[str, Any]:
    unknown = {
        "event_kind": event_kind, "date": None, "status": "not_assessed", "evidence": [],
        "data_gaps": [_gap(_MISSING_EVENT_CODES.get(event_kind, "event_evidence_missing"), message)],
    }
    if event_kind == "economic_effective_date":
        unknown["retroactivity_status"] = "not_assessed"
    return unknown


def _compatibility_view(timeline: dict[str, Any]) -> dict[str, Any]:
    result = {key: timeline[key] for key in ("record_type", "status", "member_id", "as_of_date", "limitations")}
    result["schema_version"] = "pension-entitlement-timeline/v1"
    result["data_gaps"] = _legacy_gaps(timeline["data_gaps"])
    result["events"] = {
        key: {
            "status": event["status"],
            "date": event["date"],
            "source_refs": list(dict.fromkeys(
                provenance["source_ref"]
                for proof in event["evidence"]
                for provenance in [
                    proof["source_provenance"],
                    *(scope["source_provenance"] for scope in proof["transition_scope"]["scope_evidence"]),
                ]
            )),
            "data_gaps": _legacy_gaps(event["data_gaps"]),
        }
        for key, event in timeline["events"].items()
    }
    return result


def _legacy_gaps(gaps: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [{"code": gap["code"], "message": gap["message"]} for gap in gaps]


def _inps_projection(
    identity: dict[str, str], declarations: dict[str, Any], as_of: date, captures: _CapturedSources,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not {"work_exit_input_ref", "rule_pack", "candidate_date"} <= declarations.keys():
        return None, [_gap("inps_scenario_inputs_missing", "An INPS scenario requires a member input, rule pack and candidate date.")]
    ref = declarations["work_exit_input_ref"]
    try:
        _, payload = captures.local(ref)
        data = _json_object(payload)
        if data.get("schema_version") != WORK_EXIT_INPUT_VERSION or data.get("household_id") != identity["household_id"]:
            raise PensionTimelineIntegrationError("INPS scenario source schema or household mismatch.")
        adults = [adult for adult in data["adults"] if adult["person_id"] == identity["member_id"]]
        if len(adults) != 1:
            return None, [_gap("inps_member_input_missing_or_ambiguous", "Exactly one INPS scenario input is required for this member.")]
        candidate = _date(declarations["candidate_date"])
        method = adults[0].get("inps_contributory_estimate") or {}
        if future := method.get("future_contributions"):
            supported_fields = {"annual_taxable_income", "annual_taxable_income_by_year", "through_year", "computation_rate"}
            if not isinstance(future, dict) or future.keys() - supported_fields:
                return None, [_gap("unsupported_annual_contribution_schedule", "Supply declared annual taxable bases for the existing contribution kernel.")]
        if (candidate.month, candidate.day) != (12, 31) and "annual_taxable_income_by_year" not in method.get("future_contributions", {}):
            return None, [_gap("partial_final_year_contribution_total_missing", "A partial final scenario year requires explicit declared yearly totals; a full annual flat income is not prorated or inferred.")]
        if candidate < as_of or _date(data["as_of_date"]) > as_of or method.get("as_of_year", as_of.year) > as_of.year:
            return None, [_gap("inps_scenario_date_scope_invalid", "The candidate or input dates are outside the scenario snapshot scope.")]
        rule_path, rule_payload, rule_reference = captures.rule("italy/2026", declarations["rule_pack"])
        pack = load_inps_projection_rule_pack(rule_path, rule_pack_bytes=rule_payload, as_of_date=as_of)
        estimate = project_inps_for_adult(adults[0], candidate, pack)
        return {
            "classification": "scenario_projection",
            "service_schema_version": estimate["schema_version"],
            "status": estimate["status"],
            "candidate_date": estimate["candidate_date"],
            "inputs": estimate["inputs"] if estimate["status"] == "complete" else None,
            "amount": estimate["pension"] if estimate["status"] == "complete" else None,
            "method": estimate["method"],
            "source_inputs": [_reference(ref, payload)],
            "rule_pack": _rule_metadata(rule_reference, pack),
        }, _service_gaps(estimate["data_gaps"], "inps")
    except _SOURCE_ERRORS:
        return None, [_gap("inps_scenario_input_or_rule_invalid", "INPS scenario sources, freshness or rule scope could not be validated.")]


def _documentary_benchmark(
    identity: dict[str, str], declarations: dict[str, Any], captures: _CapturedSources,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    ref = declarations.get("documentary_ref")
    if ref is None:
        return None, [_gap("inps_documentary_benchmark_missing", "A separate INPS documentary projection was not supplied.")]
    try:
        _, payload = captures.local(ref)
        data = _json_object(payload)
        _check_declared_identity(data, identity)
        if data.get("schema_version") != "inps-pension/v1" or data.get("extraction_status") != "extracted":
            raise PensionTimelineIntegrationError("A successfully extracted INPS documentary snapshot is required.")
        projection = inps_documentary_projection(data)
        monthly = projection["monthly_gross_pension"]
        if not isinstance(monthly, str) or not Decimal(monthly).is_finite() or Decimal(monthly) < 0:
            raise PensionTimelineIntegrationError("Documentary monthly gross pension is missing.")
        declared_subject = all(data.get(key) == identity[key] for key in _IDENTITY_FIELDS)
        return {
            "classification": "documentary_projection_benchmark",
            "source": _reference(ref, payload),
            "source_schema_version": data["schema_version"],
            "subject_binding": "declared_identity_matched" if declared_subject else "source_selection_only",
            "projection": {
                "retirement_date": projection.get("retirement_date"),
                "monthly_gross_pension": monthly,
                "prices_year": projection.get("prices_year"),
            },
        }, ([] if declared_subject else [_gap(
            "inps_documentary_subject_not_attested",
            "The selected documentary benchmark lacks explicit member/benefit identity; it is not verified subject evidence.",
        )])
    except _SOURCE_ERRORS:
        return None, [_gap("inps_documentary_benchmark_invalid", "The separate INPS documentary projection could not be used.")]


def _spanish_projections(
    identity: dict[str, str], declarations: dict[str, Any], as_of: date, captures: _CapturedSources,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[dict[str, Any]]]:
    if not {"pro_rata_input_ref", "reconciliation_ref", "theoretical_rule_pack"} <= declarations.keys():
        return None, None, [_gap("spanish_scenario_inputs_missing", "Spanish scenario input, reconciliation or theoretical rule pack is missing.")]
    try:
        input_ref = declarations["pro_rata_input_ref"]
        reconciliation_ref = declarations["reconciliation_ref"]
        input_path, input_bytes = captures.local(input_ref)
        reconciliation_path, reconciliation_bytes = captures.local(reconciliation_ref)
        for payload in (input_bytes, reconciliation_bytes):
            data = _json_object(payload)
            _check_declared_identity(data, identity)
            if any(data.get(field) != identity[field] for field in _IDENTITY_FIELDS):
                return None, None, [_gap("spanish_source_subject_not_attested", "Spanish scenario sources require explicit matching household/member/country/benefit identity before any amount is published.")]
        source_inputs = [_reference(input_ref, input_bytes), _reference(reconciliation_ref, reconciliation_bytes)]
        rule_path, rule_payload, reference = captures.rule("cross-border", declarations["theoretical_rule_pack"])
        theory = calculate_spanish_eu_theoretical_pension(
            input_path, reconciliation_path, rule_path, pro_rata_input_bytes=input_bytes, reconciliation_bytes=reconciliation_bytes,
            rule_pack_bytes=rule_payload, as_of_date=as_of,
        )
        theoretical = {
            "classification": "scenario_projection",
            "service_schema_version": theory["schema_version"],
            "status": theory["status"],
            "candidate_month": theory["retirement_date"],
            "amount": theory["spanish_theoretical_pension"],
            "source_inputs": source_inputs,
            "rule_pack": _rule_metadata(reference, theory["rule_pack"]),
        }
        gaps = _service_gaps(theory["data_gaps"], "spanish_theoretical")
    except _SOURCE_ERRORS:
        return None, None, [_gap("spanish_theoretical_input_or_rule_invalid", "Spanish theoretical sources, freshness or rule scope could not be validated.")]
    if "pro_rata_rule_pack" not in declarations:
        return theoretical, None, gaps + [_gap("eu_pro_rata_rule_pack_missing", "No EU pro-rata rule pack was supplied.")]
    try:
        rule_path, rule_payload, reference = captures.rule("cross-border", declarations["pro_rata_rule_pack"])
        snapshot = calculate_it_es_eu_pension_pro_rata(
            input_path, rule_path, input_bytes=input_bytes, rule_pack_bytes=rule_payload, as_of_date=as_of,
            spanish_theoretical_snapshot=theory,
        )
        pro_rata = snapshot["spanish_pro_rata_pension"]
        return theoretical, {
            "classification": "scenario_projection",
            "service_schema_version": snapshot["schema_version"],
            "status": snapshot["status"],
            "candidate_month": theory["retirement_date"],
            "amount": pro_rata.get("amounts") if snapshot["status"] == "complete" else None,
            "ratio": pro_rata.get("ratio") if snapshot["status"] == "complete" else None,
            "source_inputs": source_inputs,
            "rule_pack": _rule_metadata(reference, snapshot["rule_pack"]),
        }, gaps + _service_gaps(snapshot["data_gaps"], "spanish_pro_rata")
    except _SOURCE_ERRORS:
        return theoretical, None, gaps + [_gap("eu_pro_rata_input_or_rule_invalid", "EU pro-rata scope, provenance or freshness could not be validated.")]


def _service_gaps(gaps: list[dict[str, Any]], service: str) -> list[dict[str, Any]]:
    return [
        _gap(gap["code"], gap.get("message") or "The scenario service reported a data gap.",
             severity="blocking" if gap.get("blocking", True) else "warning", service=service)
        for gap in gaps
    ]


def _rule_metadata(ref: dict[str, str], pack: dict[str, Any]) -> dict[str, Any]:
    fields = ("rule_pack_id", "valid_from", "valid_to", "calculation_mode", "source_refs", "limitations")
    return {**ref, **{key: pack[key] for key in fields if key in pack}}


def _check_declared_identity(data: dict[str, Any], identity: dict[str, str]) -> None:
    if any(key in data and data[key] != identity[key] for key in _IDENTITY_FIELDS):
        raise PensionTimelineIntegrationError("The source's declared identity conflicts with the requested benefit stream.")


def _date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Expected a calendar date in YYYY-MM-DD format.")
    return parsed


def _json_object(payload: bytes) -> dict[str, Any]:
    def without_duplicate_keys(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise PensionTimelineIntegrationError("A source JSON object contains duplicate keys.")
            result[key] = value
        return result

    data = json.loads(payload.decode("utf-8"), object_pairs_hook=without_duplicate_keys)
    if not isinstance(data, dict):
        raise PensionTimelineIntegrationError("A source JSON object is required.")
    return data


def _reference(ref: str, payload: bytes) -> dict[str, str]:
    return {"source_ref": ref, "digest_sha256": _digest(payload)}


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _gap(code: str, message: str, *, severity: str = "blocking", **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, "severity": severity, **details}
