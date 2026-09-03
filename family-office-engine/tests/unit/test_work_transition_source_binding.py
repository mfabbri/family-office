import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.services.work_transition_readiness import build_work_transition_readiness
from family_office_engine.services.work_transition_source_binding import (
    WorkTransitionSourceBindingError,
    bind_work_transition_source,
    discover_work_transition_sources,
    validate_work_transition_readiness_manifest,
)


def _manifest() -> dict:
    return {
        "schema_version": "work-transition-readiness-input/v1",
        "record_type": "WorkTransitionReadinessInput",
        "household_id": "synthetic_household",
        "as_of_date": "2026-08-24",
        "household_members": ["primary"],
        "required_inputs": [
            {"input_id": "employment", "category": "employment_income", "member_id": "primary", "accepted_value_basis": ["net"]},
            {"input_id": "bridge", "category": "liquidity", "accepted_value_basis": ["not_applicable"], "requires_liquid_asset": True},
        ],
        "sources": [],
    }


class WorkTransitionSourceBindingTests(unittest.TestCase):
    def _prepare(self, root: Path) -> Path:
        snapshots = root / "snapshots"
        snapshots.mkdir()
        (snapshots / "payroll.json").write_text(json.dumps({"schema_version": "payroll/v1", "as_of_date": "2026-08-20", "record_type": "PayrollSnapshot"}), encoding="utf-8")
        manifest_path = root / "planning" / "readiness.json"
        manifest_path.parent.mkdir()
        manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
        return manifest_path

    def test_discovers_workspace_local_snapshots_and_records_explicit_provenance(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest_path = self._prepare(root)
            discovery = discover_work_transition_sources(root, _manifest()["required_inputs"])
            candidate = discovery["candidates_by_input"]["employment"][0]
            self.assertEqual("snapshots/payroll.json", candidate["workspace_path"])
            self.assertEqual("net", candidate["value_basis"])
            entry = bind_work_transition_source(manifest_path, root, input_id="employment", candidate=candidate)
            self.assertEqual("/bindings/employment_", entry["binding_pointer"][:21])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual("workspace-local explicit source binding", manifest["sources"][0]["provenance"]["origin"])
            self.assertEqual("snapshots/payroll.json", manifest["sources"][0]["provenance"]["source_snapshot_path"])
            readiness = build_work_transition_readiness(
                manifest_path, root / "snapshots" / "readiness.json", workspace_root=root
            )
            self.assertEqual("selected", readiness["input_selections"][0]["status"])
            self.assertEqual("missing", readiness["input_selections"][1]["status"])

    def test_multiple_candidates_are_an_explicit_conflict_and_overwrite_is_required(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest_path = self._prepare(root)
            (root / "snapshots" / "payroll-second.json").write_text(json.dumps({"schema_version": "payroll/v1", "as_of_date": "2026-08-21"}), encoding="utf-8")
            discovery = discover_work_transition_sources(root, _manifest()["required_inputs"])
            gaps = {gap["code"] for gap in discovery["data_gaps"]}
            self.assertIn("multiple_compatible_workspace_snapshots", gaps)
            candidates = discovery["candidates_by_input"]["employment"]
            bind_work_transition_source(manifest_path, root, input_id="employment", candidate=candidates[0])
            with self.assertRaisesRegex(WorkTransitionSourceBindingError, "use --overwrite"):
                bind_work_transition_source(manifest_path, root, input_id="employment", candidate=candidates[1])
            entry = bind_work_transition_source(manifest_path, root, input_id="employment", candidate=candidates[1], overwrite=True)
            self.assertEqual(candidates[1]["workspace_path"], entry["provenance"]["source_snapshot_path"])

    def test_preserves_bounds_liquidity_and_coverage_metadata_for_readiness(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest()
            manifest["required_inputs"][0]["requires_stream_bounds"] = True
            manifest["required_inputs"][1]["required"] = False
            manifest["sources"] = []
            snapshots = root / "snapshots"
            snapshots.mkdir()
            (snapshots / "payroll.json").write_text(json.dumps({"schema_version": "payroll/v1", "as_of_date": "2026-08-20", "stream_start_date": "2026-01-01", "stream_end_date": "2026-12-31", "coverage_keys": ["income:primary"]}), encoding="utf-8")
            manifest_path = root / "planning" / "readiness.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            candidate = discover_work_transition_sources(root, manifest["required_inputs"])["candidates_by_input"]["employment"][0]
            entry = bind_work_transition_source(manifest_path, root, input_id="employment", candidate=candidate)
            self.assertEqual("2026-01-01", entry["stream_start_date"])
            self.assertEqual(["income:primary"], entry["coverage_keys"])
            readiness = build_work_transition_readiness(
                manifest_path, root / "snapshots" / "readiness.json", workspace_root=root
            )
            self.assertEqual("selected", readiness["input_selections"][0]["status"])

            liquidity_manifest = _manifest()
            liquidity_manifest["required_inputs"] = [liquidity_manifest["required_inputs"][1]]
            liquidity_manifest_path = root / "planning" / "liquidity.json"
            liquidity_manifest_path.write_text(json.dumps(liquidity_manifest), encoding="utf-8")
            (snapshots / "liquidity.json").write_text(json.dumps({"schema_version": "liquidity-plan/v1", "as_of_date": "2026-08-20", "liquidity_tier": "immediate"}), encoding="utf-8")
            candidate = discover_work_transition_sources(root, liquidity_manifest["required_inputs"])["candidates_by_input"]["bridge"][0]
            entry = bind_work_transition_source(liquidity_manifest_path, root, input_id="bridge", candidate=candidate)
            self.assertEqual("immediate", entry["liquidity_tier"])

    def test_reports_actionable_gap_when_required_snapshot_metadata_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest_path = self._prepare(root)
            manifest = _manifest()
            manifest["required_inputs"][0]["requires_stream_bounds"] = True
            discovery = discover_work_transition_sources(root, manifest["required_inputs"])
            gaps = {gap["code"] for gap in discovery["data_gaps"]}
            self.assertIn("missing_stream_bounds_from_selected_snapshot", gaps)

    def test_post_binding_hash_mutation_or_deletion_blocks_readiness(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest_path = self._prepare(root)
            candidate = discover_work_transition_sources(root, _manifest()["required_inputs"])["candidates_by_input"]["employment"][0]
            bind_work_transition_source(manifest_path, root, input_id="employment", candidate=candidate)
            payroll = root / "snapshots" / "payroll.json"
            payroll.write_text(json.dumps({"schema_version": "payroll/v1", "as_of_date": "2026-08-21"}), encoding="utf-8")
            mutated = build_work_transition_readiness(
                manifest_path, root / "snapshots" / "mutated-readiness.json", workspace_root=root
            )
            self.assertEqual("missing", mutated["input_selections"][0]["status"])
            self.assertIn("source_snapshot_hash_mismatch", mutated["sources"][0]["exclusion_reasons"])
            payroll.unlink()
            deleted = build_work_transition_readiness(
                manifest_path, root / "snapshots" / "deleted-readiness.json", workspace_root=root
            )
            self.assertEqual("missing", deleted["input_selections"][0]["status"])
            self.assertIn("missing_source_snapshot", deleted["sources"][0]["exclusion_reasons"])

    def test_rejects_malformed_manifest_and_keeps_schema_valid_input_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest_path = self._prepare(root)
            malformed = _manifest()
            malformed["unexpected"] = True
            manifest_path.write_text(json.dumps(malformed), encoding="utf-8")
            stdout = io.StringIO()
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(root)}), redirect_stdout(stdout):
                code = main(["planning", "work-transition", "sources", "setup", "--input", str(manifest_path)])
            self.assertEqual(1, code)
            self.assertIn("does not match work-transition-readiness-input schema", stdout.getvalue())

            unsafe = _manifest()
            unsafe["required_inputs"][0]["input_id"] = "income / primary"
            manifest_path.write_text(json.dumps(unsafe), encoding="utf-8")
            manual = _manifest()
            manual["sources"] = [{"source_id": "manual source entry", "input_id": "income / primary", "category": "employment_income", "source_kind": "manual", "path": "manual.json", "expected_schema_versions": ["manual/v1"], "value_basis": "net", "binding_pointer": "/binding", "provenance": {"origin": "manual advanced fallback"}}]
            manual["required_inputs"][0]["input_id"] = "income / primary"
            validate_work_transition_readiness_manifest(manual)
            candidate = discover_work_transition_sources(root, unsafe["required_inputs"])["candidates_by_input"]["income / primary"][0]
            entry = bind_work_transition_source(manifest_path, root, input_id="income / primary", candidate=candidate)
            self.assertEqual("income / primary", entry["input_id"])
            self.assertNotIn("/", entry["source_id"])
            self.assertTrue((root / "planning" / "work-transition-source-bindings" / f"{entry['source_id']}.json").is_file())

    def test_cli_requires_explicit_choice_and_rebuilds_readiness(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest_path = self._prepare(root)
            output_path = root / "snapshots" / "readiness.json"
            stdout = io.StringIO()
            with patch.dict(os.environ, {"FO_WORKSPACE_PATH": str(root)}), patch("builtins.input", side_effect=["1", "0"]), redirect_stdout(stdout):
                code = main(["planning", "work-transition", "sources", "setup", "--input", str(manifest_path), "--output", str(output_path)])
            self.assertEqual(0, code, stdout.getvalue())
            self.assertIn("scegli esplicitamente", stdout.getvalue())
            self.assertIn("planning work-transition sources setup: blocked", stdout.getvalue())
            self.assertEqual(1, len(json.loads(manifest_path.read_text(encoding="utf-8"))["sources"]))


if __name__ == "__main__":
    unittest.main()
