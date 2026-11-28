import hashlib
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.pension_timeline_wizard import (
    PensionTimelineWizardError, prepare_pension_timeline_request,
)


class PensionTimelineWizardTest(unittest.TestCase):
    def test_unknown_inputs_are_saved_progressively_without_manual_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_path = root / "planning/request.json"
            with patch("builtins.input", side_effect=["synthetic-household", "2026-11-22", "primary,spouse", "n"]), redirect_stdout(io.StringIO()):
                result = prepare_pension_timeline_request(request_path, workspace_root=root)
            self.assertEqual(["primary", "spouse"], result["household_members"])
            self.assertEqual([], result["streams"])
            self.assertEqual(result, json.loads(request_path.read_text(encoding="utf-8")))
            with patch("builtins.input") as prompt, redirect_stdout(io.StringIO()):
                self.assertEqual(result, prepare_pension_timeline_request(request_path, workspace_root=root))
            prompt.assert_not_called()

    def test_individual_fact_needs_distinct_transition_evidence_and_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "decision.txt").write_text("Synthetic decision for primary/IT/pension_it, recognition 2026-10-20.", encoding="utf-8")
            (root / "basis.txt").write_text("Synthetic primary-law transition evidence only.", encoding="utf-8")
            request_path = root / "planning/request.json"
            refs = iter(["decision.txt", "basis.txt"])
            add = iter(["s", "n"])
            transition_state = "applicable"
            def answer(prompt):
                if prompt.startswith("Stato transitorio accertato"): return transition_state
                if prompt.startswith("Etichetta locale"): return "synthetic-household"
                if prompt.startswith("Data del rapporto"): return "2026-11-22"
                if prompt.startswith("Etichette dei membri"): return "primary,spouse"
                if prompt.startswith("Aggiungere una prestazione"): return next(add)
                if prompt.startswith("Membro cui"): return "primary"
                if prompt.startswith("Paese della"): return "IT"
                if prompt.startswith("Identificativo locale"): return "pension_it"
                if prompt.startswith("Input di scenario"): return ""
                if prompt.startswith("Importare eventi"): return "s"
                if prompt.startswith("Data del riconoscimento"): return "2026-10-20"
                if prompt.startswith(("Data del solo", "Data di soddisfacimento", "Data di decorrenza", "Data del primo")): return ""
                if prompt.startswith("Percorso relativo"): return next(refs)
                if prompt.startswith("Identificativo dell'atto"): return "synthetic-verified-document"
                if prompt.startswith("Articolo o riferimento"): return "synthetic-event-paragraph"
                if prompt.startswith("Versione esatta"): return "synthetic-v1"
                if prompt.startswith(("Data di acquisizione", "Data di verifica esterna")): return "2026-11-22"
                if prompt.startswith("Inizio applicabilita"): return "2026-01-01"
                if prompt.startswith("Fine ESCLUSA"): return "APERTA"
                if "CONFERMO" in prompt: return "CONFERMO"
                if prompt.startswith("Riferimento alla verifica"): return "synthetic-review-reference"
                raise AssertionError(prompt)
            with patch("builtins.input", side_effect=answer), redirect_stdout(io.StringIO()):
                result = prepare_pension_timeline_request(request_path, workspace_root=root)
            stream = result["streams"][0]
            self.assertEqual(1, len(stream["observed_event_refs"]))
            binding_path = root / stream["observed_event_refs"][0].removeprefix("workspace-ref:")
            binding = json.loads(binding_path.read_text(encoding="utf-8"))
            self.assertEqual("official_recognition_date", binding["event_kind"])
            self.assertEqual("2026-10-20", binding["date"])
            self.assertEqual("primary", binding["member_id"])
            self.assertEqual(hashlib.sha256((root / "decision.txt").read_bytes()).hexdigest(), binding["verification"]["digest_sha256"])
            self.assertEqual("primary_legislation", binding["evidence"][0]["transition_scope"]["scope_evidence"][0]["source_provenance"]["source_authority"])
            # Run the public command on the wizard's saved request, with real
            # source-byte and timeline validation rather than mocked provenance.
            from family_office_engine.cli.main import main
            report_path = root / "snapshots/report.json"
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(root)}), redirect_stdout(io.StringIO()):
                code = main(["planning", "work-transition", "pension-timeline", "--input", str(request_path), "--output", str(report_path)])
            self.assertEqual(0, code)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            stream_report = report["streams"][0]
            self.assertEqual("2026-10-20", stream_report["timeline_v2"]["events"]["official_recognition_date"]["date"])
            self.assertEqual("2026-10-20", stream_report["compatibility_v1"]["events"]["official_recognition_date"]["date"])
            self.assertTrue(any(gap.get("member_id") == "spouse" for gap in report["data_gaps"]))
            (root / "decision.txt").write_text("Synthetic altered decision bytes.", encoding="utf-8")
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(root)}), redirect_stdout(io.StringIO()):
                code = main(["planning", "work-transition", "pension-timeline", "--input", str(request_path), "--output", str(report_path)])
            self.assertEqual(0, code)
            changed = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertIsNone(changed["streams"][0]["timeline_v2"]["events"]["official_recognition_date"]["date"])
            from family_office_engine.cli.pension_timeline_wizard import _observed_binding
            for transition_state in ("not_applicable", "unknown"):
                refs = iter(["decision.txt", "basis.txt"])
                with patch("builtins.input", side_effect=answer), redirect_stdout(io.StringIO()):
                    ref = _observed_binding(root, result, result["streams"][0], "official_recognition_date")
                result["streams"][0]["observed_event_refs"] = [ref]
                request_path.write_text(json.dumps(result), encoding="utf-8")
                with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(root)}), redirect_stdout(io.StringIO()):
                    code = main(["planning", "work-transition", "pension-timeline", "--input", str(request_path), "--output", str(report_path)])
                self.assertEqual(0, code)
                report = json.loads(report_path.read_bytes())
                for view in ("timeline_v2", "compatibility_v1"):
                    event = report["streams"][0][view]["events"]["official_recognition_date"]
                    self.assertEqual(None if transition_state == "unknown" else "2026-10-20", event["date"])
                    if transition_state == "unknown":
                        self.assertIn("transitional_branch_unknown", {gap["code"] for gap in event["data_gaps"]})

    def test_wrong_target_is_not_overwritten_by_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "source.json"
            target.write_text('{"record_type":"SyntheticSource"}', encoding="utf-8")
            before = target.read_bytes()
            with self.assertRaises(PensionTimelineWizardError):
                prepare_pension_timeline_request(target, workspace_root=root, revise=True)
            self.assertEqual(before, target.read_bytes())

    def test_yearly_phase_bases_are_declared_in_a_new_scenario_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "planning/base.json"
            base.parent.mkdir()
            sample = Path(__file__).resolve().parents[2] / "examples/work-exit-feasibility-sample.json"
            base.write_bytes(sample.read_bytes())
            original = base.read_bytes()
            responses = [
                "synthetic_it_es_household", "2026-11-22", "primary,spouse", "s", "primary", "IT", "inps",
                "planning/base.json", "2028-01-01", "s", "2027", "40000", "2028", "24000", "", "", "n", "n",
            ]
            with patch("builtins.input", side_effect=responses), redirect_stdout(io.StringIO()):
                request = prepare_pension_timeline_request(root / "planning/request.json", workspace_root=root)
            self.assertEqual(original, base.read_bytes())
            ref = request["streams"][0]["inps"]["work_exit_input_ref"]
            copied = json.loads((root / ref.removeprefix("workspace-ref:")).read_text(encoding="utf-8"))
            future = copied["adults"][0]["inps_contributory_estimate"]["future_contributions"]
            self.assertEqual({"2027": "40000", "2028": "24000"}, future["annual_taxable_income_by_year"])
            self.assertNotIn("annual_taxable_income", future)
            self.assertNotIn("through_year", future)
            self.assertEqual(json.loads(original)["adults"][1], copied["adults"][1])

    def test_target_outside_workspace_is_rejected_before_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("builtins.input") as prompt, self.assertRaises(PensionTimelineWizardError):
                prepare_pension_timeline_request(root.parent / "outside.json", workspace_root=root)
            prompt.assert_not_called()

    def test_revision_interruption_preserves_all_existing_streams(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "request.json"
            saved = {"schema_version": "pension-timeline-integration-input/v1", "household_id": "synthetic-household",
                     "as_of_date": "2026-11-22", "household_members": ["primary", "spouse"],
                     "streams": [{"member_id": "primary", "jurisdiction": "IT", "stream_id": "existing"}]}
            target.write_text(json.dumps(saved), encoding="utf-8")
            before = target.read_bytes()
            with patch("builtins.input", side_effect=EOFError), redirect_stdout(io.StringIO()), self.assertRaises(EOFError):
                prepare_pension_timeline_request(target, workspace_root=root, revise=True)
            self.assertEqual(before, target.read_bytes())
            with patch("builtins.input", return_value="n"), redirect_stdout(io.StringIO()):
                result = prepare_pension_timeline_request(target, workspace_root=root, revise=True)
            self.assertEqual(saved, result)
            self.assertEqual(before, target.read_bytes())

    def test_spanish_scenario_sources_are_bound_only_after_explicit_confirmation(self):
        from family_office_engine.services.pension_timeline_integration import integrate_pension_timeline
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            examples = Path(__file__).resolve().parents[2] / "examples"
            names = ["spanish-eu-theoretical-pension-pro-rata-input-sample.json", "spanish-eu-theoretical-pension-reconciliation-sample.json"]
            for name in names: (root / name).write_bytes((examples / name).read_bytes())
            before = [(root / name).read_bytes() for name in names]
            answers = ["synthetic-household", "2026-11-22", "primary,spouse", "s", "primary", "ES", "spanish-pension",
                       names[0], names[1], "CONFERMO", "n", "n"]
            with patch("builtins.input", side_effect=answers), redirect_stdout(io.StringIO()):
                request = prepare_pension_timeline_request(root / "request.json", workspace_root=root)
            for field in ("pro_rata_input_ref", "reconciliation_ref"):
                prepared = root / request["streams"][0]["spanish"][field].removeprefix("workspace-ref:")
                bound = json.loads(prepared.read_bytes())
                self.assertEqual("primary", bound["member_id"])
                self.assertEqual("spanish-pension", bound["stream_id"])
                self.assertEqual("operator_confirmed_scenario_subject", bound["source_binding"]["status"])
            report = integrate_pension_timeline(request, workspace_root=root)
            self.assertEqual("complete", report["streams"][0]["scenario_projection"]["spanish_theoretical"]["status"])
            self.assertIsNone(report["streams"][0]["scenario_projection"]["spanish_pro_rata"]["amount"])
            self.assertEqual(before, [(root / name).read_bytes() for name in names])

    def test_plan_roster_and_captured_request_are_bound_before_publication(self):
        from family_office_engine.cli.main import run_work_transition_plan_wizard, _work_exit_readiness_requirements
        from family_office_engine.services.work_transition_readiness import WorkTransitionReadinessError
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "planning/manifest.json"; manifest.parent.mkdir()
            manifest.write_text(json.dumps({"schema_version": "work-transition-readiness-input/v1", "record_type": "WorkTransitionReadinessInput",
                "household_id": "synthetic-household", "as_of_date": "2026-11-22", "household_members": ["primary", "spouse"],
                "required_inputs": _work_exit_readiness_requirements(), "sources": []}), encoding="utf-8")
            request_path = root / "planning/request.json"
            request = {"schema_version": "pension-timeline-integration-input/v1", "household_id": "synthetic-household",
                       "as_of_date": "2026-11-22", "household_members": ["primary", "spouse"], "streams": []}
            def invoke():
                with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(root)}), patch(
                    "family_office_engine.cli.main.run_work_transition_source_setup", return_value={"readiness": {}, "bound_count": 0}), patch(
                    "family_office_engine.cli.main._run_work_transition_scenario_wizard", return_value={"blockers": []}), redirect_stdout(io.StringIO()):
                    return run_work_transition_plan_wizard(manifest, root / "snapshots/readiness.json", pension_timeline_input=request_path)
            outsider = {**request, "household_members": ["outsider"]}
            request_path.write_text(json.dumps(outsider), encoding="utf-8")
            with self.assertRaises(WorkTransitionReadinessError): invoke()
            self.assertFalse((root / "snapshots/pension-timeline-integration.snapshot.json").exists())
            original = json.dumps(request).encode()
            request_path.write_bytes(original)
            reads = 0
            native = Path.read_bytes
            def substituted(path):
                nonlocal reads
                if path == request_path:
                    reads += 1
                    return original if reads == 1 else json.dumps({**request, "household_id": "swapped-household"}).encode()
                return native(path)
            with patch.object(Path, "read_bytes", substituted): result = invoke()
            self.assertEqual(1, reads)
            self.assertEqual("synthetic-household", result["pension_timeline_integration"]["household_id"])

    def test_revised_inps_scenario_preserves_omitted_existing_benchmark(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "new-scenario.json").write_text('{}', encoding="utf-8")
            request = {"schema_version": "pension-timeline-integration-input/v1", "household_id": "synthetic-household",
                       "as_of_date": "2026-11-22", "household_members": ["primary"], "streams": [
                           {"member_id": "primary", "jurisdiction": "IT", "stream_id": "it-a", "observed_event_refs": [],
                            "inps": {"rule_pack": "inps-theoretical-pension.json", "work_exit_input_ref": "workspace-ref:old.json",
                                     "candidate_date": "2028-01-01", "documentary_ref": "workspace-ref:saved-benchmark.json"}}]}
            target = root / "request.json"; target.write_text(json.dumps(request), encoding="utf-8")
            responses = ["s", "primary", "IT", "it-a", "new-scenario.json", "2028-01-01", "n", "", "n", "n"]
            with patch("builtins.input", side_effect=responses), redirect_stdout(io.StringIO()):
                result = prepare_pension_timeline_request(target, workspace_root=root, revise=True)
            self.assertEqual("workspace-ref:saved-benchmark.json", result["streams"][0]["inps"]["documentary_ref"])
            self.assertEqual("workspace-ref:new-scenario.json", result["streams"][0]["inps"]["work_exit_input_ref"])
