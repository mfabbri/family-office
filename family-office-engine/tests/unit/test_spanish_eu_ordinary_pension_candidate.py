import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.pension_timeline_wizard import PensionTimelineWizardError, prepare_pension_timeline_request
from family_office_engine.cli.main import _it_es_eu_pension_input_data
from family_office_engine.services.pension_entitlement_timeline import EVENT_NAMES
from family_office_engine.services.pension_timeline_integration import integrate_pension_timeline
from family_office_engine.services.spanish_eu_ordinary_pension import RULE_PACK_NAME, RULE_PACK_SHA256, attested_claims_digest
from test_spanish_eu_theoretical_pension import _months, _period, _pro_rata_input, _reconciliation


RULES = Path(__file__).resolve().parents[3] / "family-office-rules"
IDENTITY = {"household_id": "synthetic_house", "member_id": "synthetic_member", "jurisdiction": "ES", "stream_id": "ordinary"}
AS_OF = "2026-12-10"
BRIDGE = {f"2001-{month:02d}": "1.70" for month in range(7, 13)}


class SpanishEuOrdinaryCandidateTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="fo-ordinary-2026-")
        self.addCleanup(directory.cleanup)
        self.workspace = Path(directory.name)
        self.pack_file = RULES / "cross-border" / RULE_PACK_NAME

    def _write(self, name, payload):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        (self.workspace / name).write_bytes(raw)
        return {"source_ref": "workspace-ref:" + name, "digest_sha256": hashlib.sha256(raw).hexdigest()}

    def _scenario(self, *, initial_base="2400.00"):
        scenario = _pro_rata_input()
        scenario["date_of_birth"] = "1959-12-01"  # Synthetic age67 at the common contingency.
        scenario.pop("article_57_assessment")
        scenario["insurance_periods"] = [
            _period("IT", "1999-07-01", "2001-06-30"),
            _period("ES", "2001-07-01", "2026-10-31"),
        ]
        rows = _months("2001-07", 304, "2400.00")
        for month in rows[:4]:
            month["selected_base"]["base_amount"] = initial_base
            month["official_bases"][0]["base_amount"] = initial_base
        return scenario, _reconciliation(rows)

    def _prepared(self, scenario, reconciliation):
        scenario_ref = self._write("scenario.json", scenario)
        reconciliation_ref = self._write("reconciliation.json", reconciliation)
        documents = {role: self._write(role + ".txt", f"Synthetic {role} document for testing only.".encode())
                     for role in ("coordination", "italian_periods", "historical_ipc")}
        authorities = {"coordination": "ES-INSS", "italian_periods": "IT-INPS", "historical_ipc": "ES-INE"}
        evidence = {
            "schema_version": "spanish-eu-ordinary-pension-evidence/v2",
            "subject": IDENTITY,
            "input_sha256": {"scenario": scenario_ref["digest_sha256"], "reconciliation": reconciliation_ref["digest_sha256"]},
            "risk": "ordinary_old_age",
            "contingency_date": "2026-12-01",
            "last_spanish_payment_date": "2026-11-30",
            "last_spanish_contribution_month": "2026-10",
            "base_window": {"first_month": "2001-07", "last_month": "2026-10"},
            "schemes": {"ES": "ES-regimen-general", "IT": "IT-AGO-FPLD"},
            "durations": {"unit": "institution_certified_comparable_months", "ES": 304, "IT": 24, "coordinated_total": 328},
            "coordination_findings": {
                "considered_institutions": "ES-INSS_and_IT-INPS_only",
                "formula": "article_52_1_b", "annex_viii_part_1": "waiver_not_applied",
                "annex_viii_part_2": "not_matched", "article_57": "not_applied",
                "article_56_duration_cap": "not_applied", "overlap": "none", "anti_cumulation": "not_applied",
                "ordinary_gross_scope": "confirmed_without_early_or_deferred_adjustment",
                "transition": "no_prior_award_or_preserved_regime", "revaluation": "no_intermediate_revaluation_year",
                "annex_xi_window": "confirmed_common_ES_window",
                "base_admissibility": "all_bases_computable_under_lgss_209_2_to_5",
                "article_50_2": "no_exclusion_required_under_article_50_2",
                "article_50_2_basis": "all_involved_state_conditions_met_as_of_contingency",
                "eu_2026_applicability": "2026_2359_application_and_transition_confirmed",
            },
            "historical_ipc": {"reference_month": "2024-10", "factors": dict(BRIDGE),
                               "method": "ine_national_general_official_cross_base_factors_to_reference_month"},
            "attestations": {
                role: {"document": document, "authority": authorities[role], "status": "externally_verified",
                       "verifier_ref": "synthetic_verifier", "document_locator": "page 1",
                       "issued_on": "2026-12-02", "verified_on": "2026-12-03"}
                for role, document in documents.items()
            },
        }
        stream = {
            "member_id": IDENTITY["member_id"], "jurisdiction": "ES", "stream_id": IDENTITY["stream_id"],
            "spanish": {
                "pro_rata_input_ref": scenario_ref["source_ref"], "reconciliation_ref": reconciliation_ref["source_ref"],
                "ordinary_2026": {"documents": documents},
            },
        }
        request = {"schema_version": "pension-timeline-integration-input/v1",
                   "household_id": IDENTITY["household_id"], "household_members": [IDENTITY["member_id"]],
                   "as_of_date": AS_OF, "streams": [stream]}
        self._repin(request, evidence)
        return request, evidence

    def _repin(self, request, evidence, *, reattest=True):
        if reattest:
            for role, attestation in evidence["attestations"].items():
                attestation["verified_original_sha256"] = attestation["document"]["digest_sha256"]
                attestation["claims_sha256"] = attested_claims_digest(evidence, role)
        request["streams"][0]["spanish"]["ordinary_2026"]["evidence"] = self._write("normalized.json", evidence)

    def _public(self, request, *, rules=RULES):
        stream = integrate_pension_timeline(request, workspace_root=self.workspace, rules_root=rules)["streams"][0]
        for name in EVENT_NAMES:
            self.assertIsNone(stream["timeline_v2"]["events"][name]["date"])
            self.assertIsNone(stream["compatibility_v1"]["events"][name]["date"])
        return stream

    def _projections(self, request):
        stream = self._public(request)
        return stream["scenario_projection"]["spanish_theoretical"], stream["scenario_projection"]["spanish_pro_rata"]

    def test_public_candidate_computes_indexed_theory_and_distinct_eu_share(self):
        request, _ = self._prepared(*self._scenario())
        theory, pro_rata = self._projections(request)
        self.assertIsNotNone(theory, self._public(request)["data_gaps"])
        self.assertEqual(theory["status"], "candidate_pending_independent_review")
        self.assertEqual(theory["classification"], "scenario_projection")
        self.assertEqual(theory["rule_pack"]["digest_sha256"], RULE_PACK_SHA256)
        self.assertEqual(theory["calculation"]["winning_branch"], "lgss_2026")
        self.assertEqual(theory["calculation"]["base_reguladora_by_branch"], {"lgss_2023": "2608.64", "lgss_2026": "2624.11"})
        self.assertEqual(pro_rata["ratio"], {"spain_months": 304, "total_eu_non_overlapping_months": 328, "value": "0.926829"})
        self.assertEqual(theory["amount"], {"monthly_gross_amount": "2075.67", "annual_gross_amount": "29059.38", "currency": "EUR", "payments_per_year": 14})
        self.assertEqual(pro_rata["amount"], {"monthly_gross_amount": "1923.79", "annual_gross_amount": "26933.06", "currency": "EUR", "payments_per_year": 14})
        self.assertEqual(len(pro_rata["source_inputs"]), 6)

    def test_favorable_comparison_can_select_2023_branch_and_ipc_changes_amount(self):
        request, _ = self._prepared(*self._scenario(initial_base="800.00"))
        old, old_share = self._projections(request)
        self.assertEqual(old["calculation"]["winning_branch"], "lgss_2023")
        self.assertEqual(old["calculation"]["base_reguladora_by_branch"], {"lgss_2023": "2608.64", "lgss_2026": "2599.10"})
        self.assertEqual(old["amount"]["monthly_gross_amount"], "2063.43")
        self.assertEqual(old_share["amount"]["monthly_gross_amount"], "1912.45")
        request, evidence = self._prepared(*self._scenario())
        evidence["historical_ipc"]["factors"]["2001-11"] = "2.20"
        self._repin(request, evidence)
        changed, changed_share = self._projections(request)
        self.assertEqual(changed["amount"]["monthly_gross_amount"], "2078.37")
        self.assertEqual(changed_share["amount"]["monthly_gross_amount"], "1926.29")

    def test_public_candidate_requires_scope_dates_schemes_ipc_and_duration(self):
        mutations = (
            ("ordinary_2026_date_or_scenario_outside_scope", lambda evidence: evidence.update(contingency_date="2027-01-01")),
            ("ordinary_2026_coordination_scope_unproved", lambda evidence: evidence["schemes"].update(ES="special")),
            ("ordinary_2026_coordination_scope_unproved", lambda evidence: evidence["coordination_findings"].update(annex_viii_part_2="not_assessed")),
            ("ordinary_2026_coordination_scope_unproved", lambda evidence: evidence["coordination_findings"].update(article_57="applies")),
            ("ordinary_2026_annex_xi_anchor_unproved", lambda evidence: evidence.update(last_spanish_contribution_month="2026-11")),
            ("ordinary_2026_annex_xi_anchor_unproved", lambda evidence: evidence.update(last_spanish_payment_date="2026-10-31")),
            ("ordinary_2026_annex_xi_anchor_unproved", lambda evidence: evidence["base_window"].update(last_month="2026-11")),
            ("ordinary_2026_ipc_unproved", lambda evidence: evidence["historical_ipc"]["factors"].pop("2001-07")),
            ("ordinary_2026_duration_unproved", lambda evidence: evidence["durations"].update(IT=23)),
            ("ordinary_2026_duration_unproved", lambda evidence: evidence["durations"].update(unit="weeks")),
            ("ordinary_2026_source_attestation_unproved", lambda evidence: evidence["attestations"]["coordination"].update(authority="private")),
            ("ordinary_2026_source_attestation_unproved", lambda evidence: evidence["attestations"]["historical_ipc"].update(verified_on="2026-12-11")),
            ("ordinary_2026_evidence_subject_or_input_mismatch", lambda evidence: evidence["subject"].update(member_id="other")),
        )
        for index, (gap, mutate) in enumerate(mutations):
            with self.subTest(index=index, gap=gap):
                request, evidence = self._prepared(*self._scenario())
                self.assertIsNotNone(self._projections(request)[1])
                # Keep the immutable test identity separate from the mutable envelope.
                evidence["subject"] = dict(evidence["subject"])
                mutate(evidence)
                self._repin(request, evidence)
                stream = self._public(request)
                self.assertIsNone(stream["scenario_projection"]["spanish_theoretical"])
                self.assertIsNone(stream["scenario_projection"]["spanish_pro_rata"])
                self.assertIn(gap, {item["code"] for item in stream["data_gaps"]})

    def test_public_candidate_rejects_source_or_rule_byte_drift(self):
        request, _ = self._prepared(*self._scenario())
        self.assertIsNotNone(self._projections(request)[1])
        self._write("historical_ipc.txt", b"Different original bytes")
        blocked = self._public(request)
        self.assertIn("ordinary_2026_evidence_hash_mismatch", {item["code"] for item in blocked["data_gaps"]})
        self.assertIsNone(blocked["scenario_projection"]["spanish_pro_rata"])
        request, _ = self._prepared(*self._scenario())
        self._write("reconciliation.json", b"{}")
        blocked = self._public(request)
        self.assertIn("ordinary_2026_evidence_subject_or_input_mismatch", {item["code"] for item in blocked["data_gaps"]})
        request, _ = self._prepared(*self._scenario())
        rules = self.workspace / "rules"
        (rules / "cross-border").mkdir(parents=True)
        (rules / "cross-border" / RULE_PACK_NAME).write_bytes(self.pack_file.read_bytes() + b" ")
        blocked = self._public(request, rules=rules)
        self.assertIn("ordinary_2026_rule_hash_mismatch", {item["code"] for item in blocked["data_gaps"]})
        request, evidence = self._prepared(*self._scenario())
        evidence["historical_ipc"]["factors"]["2001-11"] = "2.00"
        self._repin(request, evidence, reattest=False)
        blocked = self._public(request)
        self.assertIn("ordinary_2026_source_attestation_unproved", {item["code"] for item in blocked["data_gaps"]})

    def test_prepare_imports_pinned_institutional_evidence_and_uses_public_candidate(self):
        self._prepared(*self._scenario())
        answers = [
            IDENTITY["household_id"], AS_OF, IDENTITY["member_id"], "s", IDENTITY["member_id"], "ES",
            IDENTITY["stream_id"], "scenario.json", "reconciliation.json", "CANDIDATO", "normalized.json", "n", "n",
        ]
        with patch("builtins.input", side_effect=answers):
            request = prepare_pension_timeline_request(self.workspace / "request.json", workspace_root=self.workspace)
        theory, pro_rata = self._projections(request)
        self.assertIsNotNone(theory, self._public(request)["data_gaps"])
        self.assertIsNotNone(pro_rata)

    def test_real_wizard_input_calculates_its_own_theory_without_dummy_amount(self):
        sample, reconciliation = self._scenario()
        scenario = _it_es_eu_pension_input_data({
            "italy_months": 24, "italy_end_month": "2001-06",
            "spain_months": 304, "spain_end_month": "2026-10",
            "retirement_date": sample["retirement_date"], "date_of_birth": sample["date_of_birth"],
            "recent_contribution_anchor_date": sample["recent_contribution_anchor_date"],
            "no_future_spanish_contributions": True, "spanish_theoretical_monthly": "0.00", "payments_per_year": 14,
        })
        self.assertNotIn("spanish_theoretical_pension", scenario)
        self.assertEqual([gap["code"] for gap in scenario["data_gaps"]], ["missing_spanish_theoretical_amount"])
        request, _ = self._prepared(scenario, reconciliation)
        theory, share = self._projections(request)
        self.assertEqual(theory["amount"]["monthly_gross_amount"], "2075.67")
        self.assertEqual(share["amount"]["monthly_gross_amount"], "1923.79")
        scenario["data_gaps"].append({"code": "unresolved_input_evidence", "message": "Synthetic unknown input."})
        request, _ = self._prepared(scenario, reconciliation)
        self.assertIsNone(self._projections(request)[0])

    def test_fully_reattested_noncomputable_bases_and_article50_adverse_scope_stay_null(self):
        for field, adverse in (("base_admissibility", "contains_noncomputable_increase"),
                               ("article_50_2", "italian_conditions_unmet_and_inclusion_reduces_benefit"),
                               ("article_50_2_basis", "not_assessed"),
                               ("eu_2026_applicability", "not_assessed")):
            with self.subTest(field=field):
                scenario, reconciliation = self._scenario()
                if field == "base_admissibility":
                    # A contributed increase is not itself proof of admissibility.
                    reconciliation["months"][-1]["selected_base"]["base_amount"] = "2700.00"
                    reconciliation["months"][-1]["official_bases"][0]["base_amount"] = "2700.00"
                request, evidence = self._prepared(scenario, reconciliation)
                self.assertIsNotNone(self._projections(request)[1])
                evidence["coordination_findings"][field] = adverse
                self._repin(request, evidence)
                stream = self._public(request)
                self.assertIsNone(stream["scenario_projection"]["spanish_pro_rata"])
                self.assertIn("ordinary_2026_coordination_scope_unproved", {g["code"] for g in stream["data_gaps"]})

    def test_repinning_original_bytes_and_both_pointers_does_not_reissue_receipt(self):
        request, evidence = self._prepared(*self._scenario())
        self.assertIsNotNone(self._projections(request)[1])
        replacement = self._write("historical_ipc.txt", b"Unrelated replacement source bytes")
        request["streams"][0]["spanish"]["ordinary_2026"]["documents"]["historical_ipc"] = replacement
        evidence["attestations"]["historical_ipc"]["document"] = replacement
        for replace_verified_digest in (False, True):
            with self.subTest(replace_verified_digest=replace_verified_digest):
                if replace_verified_digest:
                    evidence["attestations"]["historical_ipc"]["verified_original_sha256"] = replacement["digest_sha256"]
                self._repin(request, evidence, reattest=False)
                stream = self._public(request)
                self.assertIsNone(stream["scenario_projection"]["spanish_pro_rata"])
                self.assertIn("ordinary_2026_source_attestation_unproved", {g["code"] for g in stream["data_gaps"]})

    def test_malformed_period_and_base_provenance_is_rejected_after_full_reattestation(self):
        mutations = (
            ("ordinary_2026_periods_unproved", lambda s, r: s["insurance_periods"][0].update(source_document={"unrelated": True})),
            ("ordinary_2026_spanish_bases_unproved", lambda s, r: r["months"][0].update(periods=[])),
            ("ordinary_2026_spanish_bases_unproved", lambda s, r: r["months"][0]["periods"][0].update(source_document=None)),
            ("ordinary_2026_spanish_bases_unproved", lambda s, r: r["months"][0]["selected_base"].update(component_count=True)),
            ("ordinary_2026_spanish_bases_unproved", lambda s, r: (
                r["months"][0]["official_bases"][0].update(source_document=None),
                r["months"][0]["selected_base"].update(source_documents=[None]))),
        )
        for code, mutate in mutations:
            with self.subTest(code=code, mutate=mutate):
                scenario, reconciliation = self._scenario()
                request, _ = self._prepared(scenario, reconciliation)
                self.assertIsNotNone(self._projections(request)[1])
                mutate(scenario, reconciliation)
                request, _ = self._prepared(scenario, reconciliation)
                stream = self._public(request)
                self.assertIsNone(stream["scenario_projection"]["spanish_pro_rata"])
                self.assertIn(code, {g["code"] for g in stream["data_gaps"]})

    def test_inps_document_cannot_predate_its_attested_actual_periods(self):
        request, evidence = self._prepared(*self._scenario())
        self.assertIsNotNone(self._projections(request)[1])
        evidence["attestations"]["italian_periods"].update(issued_on="1990-01-01", verified_on="1990-01-02")
        self._repin(request, evidence)
        stream = self._public(request)
        self.assertIsNone(stream["scenario_projection"]["spanish_pro_rata"])
        self.assertIn("ordinary_2026_source_attestation_unproved", {g["code"] for g in stream["data_gaps"]})

    def test_prepare_only_rejects_invalid_authority_or_legal_status_before_ready_save(self):
        for index, mutate in enumerate((
            lambda e: e["attestations"]["coordination"].update(authority="private"),
            lambda e: e["coordination_findings"].update(base_admissibility="not_assessed"),
        )):
            with self.subTest(index=index):
                request, evidence = self._prepared(*self._scenario())
                self.assertIsNotNone(self._projections(request)[1])
                mutate(evidence)
                self._repin(request, evidence)
                answers = [IDENTITY["household_id"], AS_OF, IDENTITY["member_id"], "s", IDENTITY["member_id"], "ES",
                           IDENTITY["stream_id"], "scenario.json", "reconciliation.json", "CANDIDATO", "normalized.json"]
                target = self.workspace / f"invalid-request-{index}.json"
                with patch("builtins.input", side_effect=answers), self.assertRaises(PensionTimelineWizardError):
                    prepare_pension_timeline_request(target, workspace_root=self.workspace)
                if target.exists():
                    self.assertEqual(json.loads(target.read_bytes())["streams"], [])
