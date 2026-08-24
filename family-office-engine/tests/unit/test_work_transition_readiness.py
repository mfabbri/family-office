import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.services.work_transition_readiness import (
    WorkTransitionReadinessError,
    build_work_transition_readiness,
)


class WorkTransitionReadinessTest(unittest.TestCase):
    def test_selects_freshest_source_and_preserves_conflict_lineage(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            _add_source(manifest, root, "employment_old", "employment", "documentary", "2026-03-01", value_basis="net")
            _add_source(manifest, root, "employment_new", "employment", "documentary", "2026-07-01", value_basis="net")

            result = _build(root, manifest)

            selection = next(item for item in result["input_selections"] if item["input_id"] == "employment")
            self.assertEqual(selection["selected_source_id"], "employment_new")
            old = next(item for item in result["sources"] if item["source_id"] == "employment_old")
            self.assertEqual(old["exclusion_reasons"], ["older_or_tie_break"])
            self.assertEqual(result["status"], "partial")
            self.assertIn("conflicting_candidate_sources", {gap["code"] for gap in result["data_gaps"]})

    def test_documentary_payroll_wins_over_manual_assumption(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            _add_source(manifest, root, "manual_salary", "employment", "manual", "2026-08-01", value_basis="net")
            _add_source(manifest, root, "payroll", "employment", "documentary", "2026-07-01", value_basis="net")

            result = _build(root, manifest)

            selection = next(item for item in result["input_selections"] if item["input_id"] == "employment")
            self.assertEqual(selection["selected_source_id"], "payroll")
            manual = next(item for item in result["sources"] if item["source_id"] == "manual_salary")
            self.assertEqual(manual["exclusion_reasons"], ["lower_precedence"])

    def test_gross_net_mismatch_blocks_optimization(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            _add_source(manifest, root, "gross_salary", "employment", "documentary", "2026-07-01", value_basis="gross")

            result = _build(root, manifest)

            self.assertEqual(result["status"], "blocked")
            self.assertFalse(result["optimization_allowed"])
            source = next(item for item in result["sources"] if item["source_id"] == "gross_salary")
            self.assertIn("incompatible_value_basis", source["exclusion_reasons"])

    def test_duplicate_asset_coverage_blocks_double_counting(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            manifest["required_inputs"].append({"input_id": "liquidity", "category": "liquidity", "requires_liquid_asset": True})
            manifest["required_inputs"].append({"input_id": "reserve", "category": "liquidity", "requires_liquid_asset": True})
            _add_source(manifest, root, "employment", "employment", "documentary", "2026-07-01", value_basis="net")
            _add_source(manifest, root, "cash", "liquidity", "normalized", "2026-08-01", liquidity_tier="immediate", coverage_keys=["asset:cash"])
            _add_source(manifest, root, "cash_again", "reserve", "derived", "2026-08-01", liquidity_tier="short_term", coverage_keys=["asset:cash"])

            result = _build(root, manifest)

            self.assertEqual(result["status"], "blocked")
            duplicate = next(gap for gap in result["data_gaps"] if gap["code"] == "duplicate_selected_coverage")
            self.assertTrue(duplicate["blocking"])

    def test_non_liquid_asset_and_missing_pension_bounds_are_excluded(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            manifest["required_inputs"].extend(
                [
                    {"input_id": "liquidity", "category": "liquidity", "requires_liquid_asset": True},
                    {
                        "input_id": "inps",
                        "category": "inps_pension",
                        "member_id": "primary",
                        "accepted_value_basis": ["gross"],
                        "requires_stream_bounds": True,
                    },
                ]
            )
            _add_source(manifest, root, "employment", "employment", "documentary", "2026-07-01", value_basis="net")
            _add_source(manifest, root, "house", "liquidity", "normalized", "2026-08-01", liquidity_tier="illiquid")
            _add_source(manifest, root, "inps", "inps", "documentary", "2026-08-01", value_basis="gross")

            result = _build(root, manifest)

            reasons = {reason for source in result["sources"] for reason in source["exclusion_reasons"]}
            self.assertIn("asset_not_liquid_for_bridge", reasons)
            self.assertIn("missing_stream_bounds", reasons)
            self.assertEqual(result["summary"]["blocking_gap_count"], 2)

    def test_stale_source_and_missing_period_block_required_inputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            manifest["required_inputs"][0]["required_period"] = {"start_date": "2026-01-01", "end_date": "2026-07-31"}
            _add_source(
                manifest,
                root,
                "employment",
                "employment",
                "documentary",
                "2025-01-01",
                value_basis="net",
                period={"start_date": "2026-06-01", "end_date": "2026-07-31"},
            )

            result = _build(root, manifest)

            source = result["sources"][0]
            self.assertEqual(set(source["exclusion_reasons"]), {"missing_required_period", "stale_source"})
            self.assertEqual(result["status"], "blocked")

    def test_manifest_cannot_override_embedded_source_as_of_date(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            _add_source(manifest, root, "employment", "employment", "documentary", "2025-01-01", value_basis="net")
            manifest["sources"][0]["as_of_date"] = "2026-08-01"

            result = _build(root, manifest)

            source = result["sources"][0]
            self.assertEqual(source["as_of_date"], "2025-01-01")
            self.assertEqual(set(source["exclusion_reasons"]), {"as_of_date_mismatch", "stale_source"})
            self.assertEqual(result["status"], "blocked")

    def test_missing_spouse_source_is_a_blocking_household_gap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            manifest["required_inputs"].append(
                {"input_id": "spouse_income", "category": "spouse_income", "member_id": "spouse", "accepted_value_basis": ["net"]}
            )
            _add_source(manifest, root, "employment", "employment", "documentary", "2026-07-01", value_basis="net")

            result = _build(root, manifest)

            spouse = next(item for item in result["input_selections"] if item["input_id"] == "spouse_income")
            self.assertEqual(spouse["status"], "missing")
            self.assertEqual(result["status"], "blocked")

    def test_relative_paths_accept_windows_and_posix_separators(self):
        for separator in ("/", "\\"):
            with self.subTest(separator=separator), tempfile.TemporaryDirectory() as tmp_dir:
                root = Path(tmp_dir)
                manifest = _manifest(root)
                source_dir = root / "sources"
                source_dir.mkdir()
                source_path = source_dir / "employment.json"
                source_path.write_text(
                    json.dumps(
                        _source(
                            "2026-07-01",
                            bindings={
                                "employment": {
                                    "category": "employment_income",
                                    "member_id": "primary",
                                    "value_basis": "net",
                                }
                            },
                        )
                    ),
                    encoding="utf-8",
                )
                manifest["sources"].append(
                    {
                        "source_id": "employment",
                        "input_id": "employment",
                        "category": "employment_income",
                        "member_id": "primary",
                        "source_kind": "documentary",
                        "path": f"sources{separator}employment.json",
                        "expected_schema_versions": ["synthetic-source/v1"],
                        "value_basis": "net",
                        "binding_pointer": "/bindings/employment",
                        "provenance": {"origin": "synthetic payroll"},
                    }
                )

                result = _build(root, manifest)

                self.assertEqual(result["status"], "ready")

    def test_rejects_unknown_household_member(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            manifest["required_inputs"][0]["member_id"] = "unknown"

            with self.assertRaisesRegex(WorkTransitionReadinessError, "Unknown household member"):
                _build(root, manifest)

    def test_source_binding_must_match_required_member(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            _add_source(manifest, root, "employment", "employment", "documentary", "2026-07-01", value_basis="net")
            source_path = root / "employment.json"
            source = json.loads(source_path.read_text(encoding="utf-8"))
            source["bindings"]["employment"]["member_id"] = "spouse"
            source_path.write_text(json.dumps(source), encoding="utf-8")

            result = _build(root, manifest)

            self.assertEqual(result["status"], "blocked")
            self.assertIn("source_binding_member_mismatch", result["sources"][0]["exclusion_reasons"])

    def test_rejects_manifest_that_violates_published_contract(self):
        cases = (
            ("record_type", "WrongInput", "record type"),
            ("category", "unsupported", "Unsupported category"),
            ("required", "yes", "must be boolean"),
        )
        for field, value, message in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp_dir:
                root = Path(tmp_dir)
                manifest = _manifest(root)
                if field == "record_type":
                    manifest[field] = value
                else:
                    manifest["required_inputs"][0][field] = value
                with self.assertRaisesRegex(WorkTransitionReadinessError, message):
                    _build(root, manifest)

    def test_personal_output_outside_workspace_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            manifest["household_id"] = "personal_household"
            _add_source(manifest, root, "employment", "employment", "documentary", "2026-07-01", value_basis="net")
            input_path = root / "readiness-input.json"
            input_path.write_text(json.dumps(manifest), encoding="utf-8")

            with patch(
                "family_office_engine.services.work_transition_readiness._workspace_root",
                return_value=root / "workspace",
            ), self.assertRaisesRegex(WorkTransitionReadinessError, "inside family-office-workspace"):
                build_work_transition_readiness(input_path, root / "readiness.snapshot.json")

    def test_synthetic_id_does_not_bypass_output_scope(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            _add_source(manifest, root, "employment", "employment", "documentary", "2026-07-01", value_basis="net")
            input_path = root / "readiness-input.json"
            input_path.write_text(json.dumps(manifest), encoding="utf-8")

            with patch(
                "family_office_engine.services.work_transition_readiness._workspace_root",
                return_value=root / "workspace",
            ), self.assertRaisesRegex(WorkTransitionReadinessError, "inside family-office-workspace"):
                build_work_transition_readiness(input_path, root / "readiness.snapshot.json")

    def test_rejects_boolean_freshness_and_non_string_provenance(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            manifest["freshness_policy"]["default_max_age_days"] = True
            with self.assertRaisesRegex(WorkTransitionReadinessError, "non-negative integer"):
                _build(root, manifest)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            _add_source(manifest, root, "employment", "employment", "documentary", "2026-07-01", value_basis="net")
            manifest["sources"][0]["provenance"]["origin"] = 1
            with self.assertRaisesRegex(WorkTransitionReadinessError, "non-empty string"):
                _build(root, manifest)

    def test_rejects_non_object_freshness_policy(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest = _manifest(root)
            manifest["freshness_policy"] = None
            with self.assertRaisesRegex(WorkTransitionReadinessError, "must be an object"):
                _build(root, manifest)


def _manifest(root: Path) -> dict:
    return {
        "schema_version": "work-transition-readiness-input/v1",
        "record_type": "WorkTransitionReadinessInput",
        "household_id": "synthetic_household",
        "as_of_date": "2026-08-24",
        "household_members": ["primary", "spouse"],
        "freshness_policy": {"default_max_age_days": 365, "max_age_days_by_category": {"employment_income": 180}},
        "required_inputs": [
            {"input_id": "employment", "category": "employment_income", "member_id": "primary", "accepted_value_basis": ["net"]}
        ],
        "sources": [],
    }


def _add_source(manifest: dict, root: Path, source_id: str, input_id: str, source_kind: str, as_of_date: str, **fields) -> None:
    requirement = next(item for item in manifest["required_inputs"] if item["input_id"] == input_id)
    value_basis = fields.pop("value_basis", "not_applicable")
    binding = {
        "category": requirement["category"],
        "member_id": requirement.get("member_id"),
        "value_basis": value_basis,
    }
    path = root / f"{source_id}.json"
    path.write_text(json.dumps(_source(as_of_date, marker=source_id, bindings={source_id: binding})), encoding="utf-8")
    manifest["sources"].append(
        {
            "source_id": source_id,
            "input_id": input_id,
            "category": requirement["category"],
            "member_id": requirement.get("member_id"),
            "source_kind": source_kind,
            "path": path.name,
            "expected_schema_versions": ["synthetic-source/v1"],
            "value_basis": value_basis,
            "binding_pointer": f"/bindings/{source_id}",
            "provenance": {"origin": f"synthetic {source_kind} fixture"},
            **fields,
        }
    )


def _source(as_of_date: str, **fields) -> dict:
    return {"schema_version": "synthetic-source/v1", "as_of_date": as_of_date, **fields}


def _build(root: Path, manifest: dict) -> dict:
    input_path = root / "readiness-input.json"
    input_path.write_text(json.dumps(manifest), encoding="utf-8")
    with patch(
        "family_office_engine.services.work_transition_readiness._workspace_root",
        return_value=root,
    ):
        return build_work_transition_readiness(input_path, root / "readiness.snapshot.json")


if __name__ == "__main__":
    unittest.main()
