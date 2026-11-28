import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker

from family_office_engine.services.pension_entitlement_timeline import EVENT_NAMES
from family_office_engine.services.pension_timeline_integration import (
    PensionTimelineIntegrationError,
    build_pension_timeline_integration,
    integrate_pension_timeline,
)
from test_it_es_eu_pension_pro_rata import _synthetic_annex_not_matched
from test_pension_entitlement_timeline_contract import V1_SCHEMA_PATH, evidence


REPOSITORY = Path(__file__).resolve().parents[3]
EXAMPLES = REPOSITORY / "family-office-engine" / "examples"
RULES = REPOSITORY / "family-office-rules"
AS_OF = "2026-11-22"
HOUSEHOLD = "synthetic_it_es_household"
RECOGNITION = "official_recognition_date"
EFFECT = "economic_effective_date"
CASH = "first_cash_payment_date"
ELIGIBILITY = "eligibility_date"
INDIVIDUAL_PROOF = {
    ELIGIBILITY: ("individual_decision", "individual_institutional_decision"),
    "requirements_met_date": ("individual_decision", "individual_institutional_decision"),
    RECOGNITION: ("individual_decision", "individual_institutional_decision"),
    EFFECT: ("economic_effective_basis", "individual_institutional_decision"),
    CASH: ("cash_availability_confirmation", "individual_payment_evidence"),
}


class PensionTimelineIntegrationTest(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory(prefix="fo-pension-integration-")
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()

    def test_shipped_services_project_inps_and_spanish_theory_with_eu_annex_gap(self):
        request = self.sample()
        report = self.run_request(request)
        italian, spanish = report["streams"]
        self.assertEqual("complete", italian["scenario_projection"]["inps"]["status"])
        self.assertEqual("4300.00", italian["documentary_benchmark"]["projection"]["monthly_gross_pension"])
        theory = spanish["scenario_projection"]["spanish_theoretical"]
        pro_rata = spanish["scenario_projection"]["spanish_pro_rata"]
        self.assertEqual("complete", theory["status"])
        self.assertGreater(float(theory["amount"]["annual_gross_amount"]), 0)
        self.assertIsNone(pro_rata["amount"])
        self.assertEqual("blocked_missing_inputs", pro_rata["status"])
        self.assertEqual("eu.it-es.pension-coordination.2026.v4", pro_rata["rule_pack"]["rule_pack_id"])
        self.assertIn("missing_article_57_annex_viii_part_2_catalogue", {item["code"] for item in spanish["data_gaps"]})
        self.assertIn("spouse", {item["member_id"] for item in report["data_gaps"] if item["code"] == "member_pension_evidence_missing"})
        for stream in report["streams"]:
            self.assert_unknown(stream)

    def test_hypothetical_annex_catalogue_exercises_existing_eu_formula(self):
        request = self.sample()
        request["streams"] = request["streams"][1:]
        isolated_rules = self.root / "synthetic-rules"
        cross_border = isolated_rules / "cross-border"
        cross_border.mkdir(parents=True)
        spanish = request["streams"][0]["spanish"]
        for key in ("theoretical_rule_pack", "pro_rata_rule_pack"):
            name = spanish[key]
            (cross_border / name).write_bytes((RULES / "cross-border" / name).read_bytes())

        pro_rata_pack_path = cross_border / spanish["pro_rata_rule_pack"]
        pack = json.loads(pro_rata_pack_path.read_bytes())
        pack["limitations"].append("Synthetic test catalogue only. No applicability for production.")
        pack["pro_rata_method"]["article_57_source_bound"]["annex_viii_part_2"].update({
            "machine_readable_validity_catalogue_status": "available",
            "catalogue_entry_ids": ["synthetic-catalogue-entry"],
            "catalogue_id": "synthetic-annex", "catalogue_schema_version": "v1", "catalogue_digest": "sha256:synthetic",
            "catalogue_valid_from": "2010-05-01", "catalogue_valid_to": None,
        })
        pro_rata_pack_path.write_text(json.dumps(pack), encoding="utf-8")
        input_name = spanish["pro_rata_input_ref"].removeprefix("workspace-ref:")
        payload = json.loads((self.workspace / input_name).read_bytes())
        payload["article_57_assessment"]["annex_viii_part_2_applicability"] = _synthetic_annex_not_matched()
        self.write_json(input_name, payload)

        stream = self.run_request(request, rules_root=isolated_rules)["streams"][0]
        projections = stream["scenario_projection"]
        theory = projections["spanish_theoretical"]
        pro_rata = projections["spanish_pro_rata"]
        self.assertEqual("complete", pro_rata["status"], stream["data_gaps"])
        self.assertEqual("scenario_projection", pro_rata["classification"])
        self.assertLess(float(pro_rata["amount"]["annual_gross_amount"]), float(theory["amount"]["annual_gross_amount"]))
        # The existing pro-rata service publishes its ratio to six decimals.
        self.assertEqual("0.039474", pro_rata["ratio"]["value"])
        self.assertIn("Synthetic test catalogue only. No applicability for production.", pro_rata["rule_pack"]["limitations"])
        self.assert_unknown(stream)

    def test_explicit_annual_bases_change_inps_montante_and_preserve_benchmark(self):
        request = self.sample()
        italian = request["streams"][0]
        request["streams"] = [italian]
        italian["inps"]["candidate_date"] = "2028-01-01"
        work_exit_ref = italian["inps"]["work_exit_input_ref"]
        work_exit_name = work_exit_ref.removeprefix("workspace-ref:")
        work_exit = json.loads((self.workspace / work_exit_name).read_bytes())
        method = work_exit["adults"][0]["inps_contributory_estimate"]

        def project(annual_taxable_base):
            method["future_contributions"] = {"annual_taxable_income_by_year": {"2027": annual_taxable_base, "2028": "0.00"}}
            self.write_json(work_exit_name, work_exit)
            return self.run_request(request)["streams"][0]

        full_time = project("95000.00")
        part_time = project("47000.00")
        full_inputs = full_time["scenario_projection"]["inps"]["inputs"]
        part_inputs = part_time["scenario_projection"]["inps"]["inputs"]
        self.assertGreater(float(full_inputs["montante_at_candidate"]), float(part_inputs["montante_at_candidate"]))
        self.assertEqual(full_time["documentary_benchmark"], part_time["documentary_benchmark"])
        benchmark_name = italian["inps"]["documentary_ref"].removeprefix("workspace-ref:")
        self.assertEqual(self.digest((self.workspace / benchmark_name).read_bytes()), full_time["documentary_benchmark"]["source"]["digest_sha256"])
        self.assert_unknown(part_time)

        del method["future_contributions"]["annual_taxable_income_by_year"]["2028"]
        self.write_json(work_exit_name, work_exit)
        partial = self.run_request(request)["streams"][0]
        self.assertIsNone(partial["scenario_projection"]["inps"]["amount"])
        self.assertIn("unsupported_annual_contribution_schedule", {gap["code"] for gap in partial["data_gaps"]})

        method["future_contributions"] = {"annual_taxable_income": "95000.00", "phase_fte": "0.6"}
        self.write_json(work_exit_name, work_exit)
        unsupported = self.run_request(request)["streams"][0]
        self.assertIsNone(unsupported["scenario_projection"]["inps"])
        self.assertIn("unsupported_annual_contribution_schedule", {gap["code"] for gap in unsupported["data_gaps"]})

    def test_benefit_identity_and_five_events_are_preserved_in_both_views(self):
        request = self.request()
        identities = [("primary", "IT", "inps-a"), ("primary", "IT", "inps-b"), ("primary", "ES", "es-a"), ("spouse", "ES", "es-b")]
        expected = {}
        for index, (member, country, benefit) in enumerate(identities, 1):
            stream = {"member_id": member, "jurisdiction": country, "stream_id": benefit, "observed_event_refs": []}
            request["streams"].append(stream)
            values = {}
            for day, event in enumerate(EVENT_NAMES, 1):
                observed = f"2026-0{index}-{day:02d}"
                ref, _ = self.binding(stream, event, observed, f"{benefit}-{day}")
                stream["observed_event_refs"].append(ref)
                values[event] = observed
            expected[(member, country, benefit)] = values
        report = self.run_request(request)
        validator = Draft202012Validator(json.loads(V1_SCHEMA_PATH.read_bytes()), format_checker=FormatChecker())
        self.assertNotIn("earliest_date", report)
        for stream in report["streams"]:
            identity = (stream["member_id"], stream["jurisdiction"], stream["stream_id"])
            v2, v1 = stream["timeline_v2"], stream["compatibility_v1"]
            self.assertEqual(expected[identity], {event: value["date"] for event, value in v2["events"].items()})
            self.assertEqual(expected[identity], {event: value["date"] for event, value in v1["events"].items()})
            validator.validate(v1)
            for event, value in v1["events"].items():
                bound = stream["observed_event_bindings"][event][0]
                self.assertIn(bound["source"]["source_ref"], value["source_refs"])
                self.assertEqual("externally_confirmed_subject_stream_event_and_date", bound["verification_scope"])

    def test_wrong_identity_event_source_drift_and_half_open_boundary_fail_closed(self):
        stream = {"member_id": "primary", "jurisdiction": "IT", "stream_id": "pension"}
        request = self.request(streams=[stream])
        mutations = (
            ("household", lambda item: item.update(household_id="other-household")),
            ("member", lambda item: item.update(member_id="spouse")),
            ("jurisdiction", lambda item: item.update(jurisdiction="ES")),
            ("benefit", lambda item: item.update(stream_id="other-pension")),
            ("event", lambda item: item.update(event_kind=CASH)),
            ("date", lambda item: item.update(date="2026-01-02")),
            ("authority", lambda item: item["evidence"][0]["source_provenance"].update(source_authority="official_administrative_guidance")),
            ("half-open", lambda item: item["evidence"][0]["source_provenance"]["legal_applicability"].update(valid_to=item["date"])),
            ("review", lambda item: item["verification"].update(status="unverified")),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                ref, value = self.binding(stream, RECOGNITION, "2026-01-01", label)
                mutate(value)
                self.write_json(ref.removeprefix("workspace-ref:"), value)
                stream["observed_event_refs"] = [ref]
                self.assert_unknown(self.run_request(request)["streams"][0])
        ref, value = self.binding(stream, RECOGNITION, "2026-01-01", "drift")
        source_name = value["verification"]["source_ref"].removeprefix("workspace-ref:")
        self.write_json(source_name, {"changed": True})
        stream["observed_event_refs"] = [ref]
        self.assert_unknown(self.run_request(request)["streams"][0])

    def test_individual_evidence_does_not_migrate_from_other_events_or_streams(self):
        italian = {"member_id": "primary", "jurisdiction": "IT", "stream_id": "it-a"}
        spanish = {"member_id": "spouse", "jurisdiction": "ES", "stream_id": "es-a"}
        first, _ = self.binding(italian, RECOGNITION, "2026-02-01", "first")
        second, _ = self.binding(italian, RECOGNITION, "2026-03-01", "second")
        effect, _ = self.binding(italian, EFFECT, "2026-02-02", "effect")
        italian["observed_event_refs"] = [first, second, effect]
        spanish["observed_event_refs"] = [effect]
        report = self.run_request(self.request(streams=[italian, spanish]))
        it_result, es_result = report["streams"]
        self.assertIsNone(it_result["timeline_v2"]["events"][RECOGNITION]["date"])
        self.assertEqual("2026-02-02", it_result["timeline_v2"]["events"][EFFECT]["date"])
        self.assertIsNone(it_result["timeline_v2"]["events"][CASH]["date"])
        self.assert_unknown(es_result)
        conflicts = [gap for gap in report["data_gaps"] if gap["code"] == "observed_event_conflict"]
        self.assertEqual(["it-a"], [gap["stream_id"] for gap in conflicts])

    def test_cessation_and_missing_members_remain_explicitly_unknown(self):
        request = self.request(streams=[{"member_id": "primary", "jurisdiction": "IT", "stream_id": "it-a", "cessation_date": "2026-03-02"}])
        report = self.run_request(request)
        self.assertEqual("2026-03-02", report["streams"][0]["scenario_projection"]["cessation_date"])
        self.assert_unknown(report["streams"][0])
        self.assertTrue(any(gap["member_id"] == "spouse" for gap in report["data_gaps"]))
        request["streams"] = []
        self.assertEqual({"primary", "spouse"}, {gap["member_id"] for gap in self.run_request(request)["data_gaps"]})

    def test_observed_source_bytes_are_read_once_per_report(self):
        stream = {"member_id": "primary", "jurisdiction": "IT", "stream_id": "it-a"}
        ref, item = self.binding(stream, RECOGNITION, "2026-01-01", "immutable")
        stream["observed_event_refs"] = [ref]
        source = self.workspace / item["verification"]["source_ref"].removeprefix("workspace-ref:")
        reads = 0
        original = Path.read_bytes

        def drift(path):
            nonlocal reads
            payload = original(path)
            if path == source:
                reads += 1
                source.write_bytes(b"replaced after capture")
            return payload

        with patch.object(Path, "read_bytes", drift):
            result = self.run_request(self.request(streams=[stream]))["streams"][0]
        self.assertEqual(1, reads)
        self.assertEqual("2026-01-01", result["timeline_v2"]["events"][RECOGNITION]["date"])
        self.assert_unknown(self.run_request(self.request(streams=[stream]))["streams"][0])

    def test_file_builder_contains_paths_and_preserves_input(self):
        self.write_json("request.json", self.request())
        source = self.workspace / "request.json"
        output = self.workspace / "planning" / "report.json"
        result = build_pension_timeline_integration(source, output, workspace_root=self.workspace)
        self.assertEqual(result, json.loads(output.read_bytes()))
        for destination in (source, self.root / "outside.json"):
            with self.assertRaises(PensionTimelineIntegrationError):
                build_pension_timeline_integration(source, destination, workspace_root=self.workspace)
        self.assertEqual(self.request(), json.loads(source.read_bytes()))

    def test_unused_declared_source_cannot_be_overwritten(self):
        request = self.request(streams=[{"member_id": "primary", "jurisdiction": "ES", "stream_id": "es-a",
            "spanish": {"reconciliation_ref": "workspace-ref:unread.json"}}])
        self.write_json("request.json", request)
        self.write_json("unread.json", {"synthetic_original_source": True})
        before = (self.workspace / "unread.json").read_bytes()
        with self.assertRaises(PensionTimelineIntegrationError):
            build_pension_timeline_integration(self.workspace / "request.json", self.workspace / "unread.json", workspace_root=self.workspace)
        self.assertEqual(before, (self.workspace / "unread.json").read_bytes())

    def test_missing_spanish_subject_cannot_be_reused_for_two_members(self):
        request = self.sample()
        spanish = request["streams"][1]
        for field in ("pro_rata_input_ref", "reconciliation_ref"):
            name = spanish["spanish"][field].removeprefix("workspace-ref:")
            data = json.loads((self.workspace / name).read_bytes())
            for key in ("household_id", "member_id", "jurisdiction", "stream_id"):
                data.pop(key, None)
            self.write_json(name, data)
        other = {**deepcopy(spanish), "member_id": "spouse"}
        request["streams"] = [spanish, other]
        for stream in self.run_request(request)["streams"]:
            self.assertIsNone(stream["scenario_projection"]["spanish_theoretical"])
            self.assertIn("spanish_source_subject_not_attested", {g["code"] for g in stream["data_gaps"]})

    def test_same_date_opposite_transition_scopes_conflict_only_on_affected_event(self):
        stream = {"member_id": "primary", "jurisdiction": "IT", "stream_id": "it-a"}
        first, _ = self.binding(stream, RECOGNITION, "2026-02-01", "scope-first")
        second, binding = self.binding(stream, RECOGNITION, "2026-02-01", "scope-second")
        for proof in binding["evidence"]:
            proof["transition_scope"]["status"] = "not_applicable"
            for scope in proof["transition_scope"]["scope_evidence"]:
                scope["scope"]["transition_status"] = "not_applicable"
        self.write_json(second.removeprefix("workspace-ref:"), binding)
        cash, _ = self.binding(stream, CASH, "2026-03-01", "scope-cash")
        stream["observed_event_refs"] = [first, second, cash]
        result = self.run_request(self.request(streams=[stream]))["streams"][0]
        self.assertIsNone(result["timeline_v2"]["events"][RECOGNITION]["date"])
        self.assertEqual("2026-03-01", result["timeline_v2"]["events"][CASH]["date"])

    def test_projection_frame_rates_and_historical_year_overlap_fail_closed(self):
        request = self.sample()
        request["streams"] = request["streams"][:1]
        declarations = request["streams"][0]["inps"]
        declarations["candidate_date"] = "2028-01-01"
        name = declarations["work_exit_input_ref"].removeprefix("workspace-ref:")
        baseline = json.loads((self.workspace / name).read_bytes())
        method = baseline["adults"][0]["inps_contributory_estimate"]
        method["future_contributions"] = {"annual_taxable_income_by_year": {"2027": "95000.00", "2028": "0.00"}, "computation_rate": "0.33"}
        self.write_json(name, baseline)
        positive = self.run_request(request)["streams"][0]["scenario_projection"]["inps"]
        self.assertEqual("31820.25", positive["inputs"]["projected_contributions"])
        self.assertEqual("567537.25", positive["inputs"]["montante_at_candidate"])
        mutations = []
        missing = deepcopy(baseline); missing["adults"][0]["inps_contributory_estimate"].pop("as_of_year"); mutations.append(missing)
        overlap = deepcopy(baseline); history = overlap["adults"][0]["inps_contributory_estimate"]
        history.pop("historical_montante"); history["annual_bases"] = [{"year": 2027, "taxable_income": "95000", "computation_rate": "0.33"}]; mutations.append(overlap)
        for rate in ("-0.33", "NaN", "Infinity"):
            invalid = deepcopy(baseline); invalid["adults"][0]["inps_contributory_estimate"]["future_contributions"]["computation_rate"] = rate; mutations.append(invalid)
        for invalid in mutations:
            self.write_json(name, invalid)
            stream = self.run_request(request)["streams"][0]
            result = stream["scenario_projection"]["inps"]
            self.assertTrue(result is None or result["amount"] is None)
            self.assertTrue(stream["data_gaps"])

    def test_flat_income_cannot_fill_partial_final_year_implicitly(self):
        request = self.sample()
        request["streams"] = request["streams"][:1]
        declarations = request["streams"][0]["inps"]
        name = declarations["work_exit_input_ref"].removeprefix("workspace-ref:")
        data = json.loads((self.workspace / name).read_bytes())
        data["adults"][0]["inps_contributory_estimate"]["future_contributions"] = {"annual_taxable_income": "95000", "through_year": 2039}
        self.write_json(name, data)
        result = self.run_request(request)["streams"][0]
        self.assertIsNone(result["scenario_projection"]["inps"])
        self.assertIn("partial_final_year_contribution_total_missing", {g["code"] for g in result["data_gaps"]})

    def test_malformed_prior_report_is_not_overwritten(self):
        self.write_json("request.json", self.request())
        output = self.workspace / "report.json"
        output.write_text(json.dumps({"schema_version": "pension-timeline-integration/v1", "household_id": HOUSEHOLD, "private_source": True}), encoding="utf-8")
        before = output.read_bytes()
        with self.assertRaises(PensionTimelineIntegrationError):
            build_pension_timeline_integration(self.workspace / "request.json", output, workspace_root=self.workspace)
        self.assertEqual(before, output.read_bytes())

    def test_one_escaped_source_does_not_abort_other_streams_on_file_report(self):
        stream = {"member_id": "primary", "jurisdiction": "IT", "stream_id": "good"}
        ref, _ = self.binding(stream, RECOGNITION, "2026-02-01", "isolated-good")
        stream["observed_event_refs"] = [ref]
        bad = {"member_id": "spouse", "jurisdiction": "ES", "stream_id": "bad", "observed_event_refs": ["workspace-ref:../outside.json"]}
        self.write_json("request.json", self.request(streams=[stream, bad]))
        report = build_pension_timeline_integration(self.workspace / "request.json", self.workspace / "report.json", workspace_root=self.workspace)
        self.assertEqual("2026-02-01", report["streams"][0]["timeline_v2"]["events"][RECOGNITION]["date"])
        self.assert_unknown(report["streams"][1])

    def test_opposite_scopes_inside_one_binding_cannot_support_an_event(self):
        stream = {"member_id": "primary", "jurisdiction": "IT", "stream_id": "it-a"}
        ref, binding = self.binding(stream, RECOGNITION, "2026-02-01", "inside-conflict")
        opposed = deepcopy(binding["evidence"][0])
        opposed["transition_scope"]["status"] = "not_applicable"
        opposed["transition_scope"]["scope_evidence"][0]["scope"]["transition_status"] = "not_applicable"
        binding["evidence"].append(opposed)
        self.write_json(ref.removeprefix("workspace-ref:"), binding)
        cash, _ = self.binding(stream, CASH, "2026-03-01", "inside-cash")
        stream["observed_event_refs"] = [ref, cash]
        report = self.run_request(self.request(streams=[stream]))
        self.assertIsNone(report["streams"][0]["timeline_v2"]["events"][RECOGNITION]["date"])
        self.assertEqual("2026-03-01", report["streams"][0]["timeline_v2"]["events"][CASH]["date"])

    def test_cross_binding_scope_identity_swap_clears_only_conflicting_event(self):
        stream = {"member_id": "primary", "jurisdiction": "IT", "stream_id": "it-a"}
        first_ref, first = self.binding(stream, RECOGNITION, "2026-02-01", "swap-a")
        second_ref, second = self.binding(stream, RECOGNITION, "2026-02-01", "swap-b")
        scopes = [deepcopy(first["evidence"][0]["transition_scope"]["scope_evidence"][0]),
                  deepcopy(second["evidence"][0]["transition_scope"]["scope_evidence"][0])]
        def set_scopes(binding, statuses):
            template = deepcopy(binding["evidence"][0]); binding["evidence"] = []
            for index, (scope, status) in enumerate(zip(scopes, statuses)):
                proof = deepcopy(template); proof["evidence_ref"] += f"-{index}"
                scope = deepcopy(scope); scope["scope"]["transition_status"] = status
                proof["transition_scope"] = {"status": status, "scope_evidence": [scope]}
                binding["evidence"].append(proof)
        set_scopes(first, ("applicable", "not_applicable"))
        set_scopes(second, ("applicable", "not_applicable"))
        self.write_json(first_ref.removeprefix("workspace-ref:"), first)
        self.write_json(second_ref.removeprefix("workspace-ref:"), second)
        cash, _ = self.binding(stream, CASH, "2026-03-01", "swap-cash")
        stream["observed_event_refs"] = [first_ref, second_ref, cash]
        positive = self.run_request(self.request(streams=[stream]))
        self.assertEqual("2026-02-01", positive["streams"][0]["timeline_v2"]["events"][RECOGNITION]["date"])
        set_scopes(second, ("not_applicable", "applicable"))
        self.write_json(second_ref.removeprefix("workspace-ref:"), second)
        changed = self.run_request(self.request(streams=[stream]))
        for view in ("timeline_v2", "compatibility_v1"):
            events = changed["streams"][0][view]["events"]
            self.assertIsNone(events[RECOGNITION]["date"])
            self.assertTrue(events[RECOGNITION]["data_gaps"])
            self.assertEqual("2026-03-01", events[CASH]["date"])

    def request(self, *, streams=None):
        return {
            "schema_version": "pension-timeline-integration-input/v1", "household_id": HOUSEHOLD, "as_of_date": AS_OF,
            "household_members": ["primary", "spouse"], "streams": [] if streams is None else streams,
        }

    def run_request(self, request, *, rules_root=RULES):
        report = integrate_pension_timeline(request, workspace_root=self.workspace, rules_root=rules_root)
        schema = json.loads((EXAMPLES.parent / "schemas/pension-timeline-integration.schema.json").read_bytes())
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(report)
        return report

    def sample(self):
        for path in EXAMPLES.glob("*"):
            if path.name in {
                "work-exit-feasibility-sample.json", "work-exit-inps-snapshot-sample.json",
                "spanish-eu-theoretical-pension-pro-rata-input-sample.json",
                "spanish-eu-theoretical-pension-reconciliation-sample.json",
                "pension-timeline-inps-input-sample.json",
            }:
                (self.workspace / path.name).write_bytes(path.read_bytes())
        request = json.loads((EXAMPLES / "pension-timeline-integration-sample.json").read_bytes())
        stream = request["streams"][1]
        identity = {"household_id": HOUSEHOLD, **{key: stream[key] for key in ("member_id", "jurisdiction", "stream_id")}}
        for field in ("pro_rata_input_ref", "reconciliation_ref"):
            name = stream["spanish"][field].removeprefix("workspace-ref:")
            data = json.loads((self.workspace / name).read_bytes()); data.update(identity); self.write_json(name, data)
        return request

    def write_json(self, name, value):
        payload = json.dumps(value).encode("utf-8")
        (self.workspace / name).write_bytes(payload)
        return "workspace-ref:" + name, self.digest(payload)

    @staticmethod
    def digest(payload):
        return hashlib.sha256(payload).hexdigest()

    def binding(self, stream, event, observed, label):
        identity = {"household_id": HOUSEHOLD, **{key: stream[key] for key in ("member_id", "jurisdiction", "stream_id")}}
        event_fields = {**identity, "event_kind": event, "date": observed}
        source_ref, digest = self.write_json(
            label + "-source.json", {"schema_version": "pension-observed-event-source/v1", **event_fields},
        )
        scope_path = self.workspace / (label + "-scope.txt")
        scope_path.write_bytes(b"synthetic primary scope and applicability fixture")
        scope_ref = "workspace-ref:" + scope_path.name
        scope_digest = self.digest(scope_path.read_bytes())
        role, authority = INDIVIDUAL_PROOF[event]
        proof = evidence(event, role, authority)
        self.set_source(proof["source_provenance"], source_ref, digest, identity["jurisdiction"], observed)
        scope_provenance = proof["transition_scope"]["scope_evidence"][0]["source_provenance"]
        self.set_source(scope_provenance, scope_ref, scope_digest, identity["jurisdiction"], observed)
        proofs = [proof]
        if event in (ELIGIBILITY, "requirements_met_date"):
            legal = deepcopy(proof)
            legal["evidence_ref"] += "-legal"
            legal["evidence_role"] = "eligibility_legal_basis" if event == ELIGIBILITY else "requirements_evidence"
            legal["source_provenance"] = deepcopy(scope_provenance)
            proofs.insert(0, legal)
        value = {
            **event_fields,
            "verification": {
                "status": "externally_verified", "verified_on": AS_OF, "verifier_ref": "synthetic-reviewer",
                "source_ref": source_ref, "digest_sha256": digest,
            },
            "evidence": proofs,
        }
        if event == EFFECT:
            value["retroactivity_status"] = "not_retroactive"
        ref, _ = self.write_json(label + "-binding.json", value)
        return ref, value

    @staticmethod
    def set_source(provenance, ref, digest, country, event_date):
        provenance.update({
            "source_ref": ref, "digest_sha256": digest, "jurisdiction": country,
            "retrieved_on": AS_OF, "reviewed_on": AS_OF,
        })
        provenance["coverage_assessment"].update({"event_date": event_date, "as_of_date": AS_OF, "assessed_on": AS_OF})

    def assert_unknown(self, stream):
        for view in ("timeline_v2", "compatibility_v1"):
            self.assertEqual(set(EVENT_NAMES), set(stream[view]["events"]))
            for value in stream[view]["events"].values():
                self.assertIsNone(value["date"])
                self.assertEqual("not_assessed", value["status"])
                self.assertTrue(value["data_gaps"])
