import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.services.work_transition_scenario import (
    WorkTransitionScenarioError,
    build_work_transition_scenario,
)


class WorkTransitionScenarioTest(unittest.TestCase):
    def test_builds_monthly_timeline_and_distinct_exit_dates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            result = _build(root, _scenario())

            self.assertEqual(result["schema_version"], "work-transition-scenario/v1")
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["derived_dates"]["full_time_exit_date_by_member"]["primary"], "2030-01-01")
            self.assertEqual(result["derived_dates"]["work_cessation_date_by_member"]["primary"], "2032-01-01")
            self.assertIsNone(result["derived_dates"]["pension_entitlement_date_by_member"]["primary"])
            self.assertIsNone(result["derived_dates"]["pension_payment_start_date_by_member"]["primary"])
            primary = next(item for item in result["monthly_timeline"] if item["member_id"] == "primary")
            self.assertEqual(len(primary["months"]), 76)
            self.assertEqual(primary["months"][0]["status"], "full_time")
            self.assertEqual(primary["months"][40]["status"], "part_time")
            self.assertEqual(primary["months"][64]["status"], "not_working")

    def test_allows_multiple_part_time_levels_and_two_adults(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario = _scenario()
            scenario["work_phases"][1]["end_date"] = "2030-12-01"
            scenario["work_phases"].insert(2, _phase("primary_part_time_40", "primary", "2031-01-01", "2031-12-01", "part_time", 0.4))
            scenario["work_phases"][3]["start_date"] = "2032-01-01"

            result = _build(root, scenario)

            self.assertEqual(result["status"], "ready")
            primary = next(item for item in result["member_summaries"] if item["member_id"] == "primary")
            self.assertEqual([item["fte"] for item in primary["status_sequence"]], [1.0, 0.6, 0.4, 0.0])
            spouse = next(item for item in result["member_summaries"] if item["member_id"] == "spouse")
            self.assertIsNone(spouse["full_time_exit_date"])
            self.assertIsNone(spouse["work_cessation_date"])

    def test_blocked_readiness_prevents_apparently_usable_scenario(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            readiness = _readiness(status="blocked", optimization_allowed=False)

            with self.assertRaisesRegex(WorkTransitionScenarioError, "readiness snapshot is blocked"):
                _build(root, _scenario(), readiness=readiness)

    def test_rejects_unknown_member_from_readiness_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario = _scenario()
            scenario["work_phases"][0]["member_id"] = "unknown"

            with self.assertRaisesRegex(WorkTransitionScenarioError, "Unknown household member"):
                _build(root, scenario)

    def test_overlapping_phases_block_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario = _scenario()
            scenario["work_phases"][1]["start_date"] = "2029-12-01"

            result = _build(root, scenario)

            self.assertEqual(result["status"], "blocked")
            self.assertIn("overlapping_phases", {gap["code"] for gap in result["data_gaps"]})
            self.assertIsNone(result["derived_dates"]["full_time_exit_date_by_member"]["primary"])
            self.assertIsNone(result["derived_dates"]["work_cessation_date_by_member"]["primary"])

    def test_undeclared_gap_blocks_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario = _scenario()
            scenario["work_phases"][1]["start_date"] = "2030-03-01"

            result = _build(root, scenario)

            self.assertEqual(result["status"], "blocked")
            gap = next(item for item in result["data_gaps"] if item["code"] == "undeclared_timeline_gap")
            self.assertEqual(gap["start_date"], "2030-01-01")
            self.assertEqual(gap["end_date"], "2030-02-01")

    def test_declared_gap_blocks_dates_until_a_monthly_phase_exists(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario = _scenario()
            scenario["work_phases"][1]["start_date"] = "2030-03-01"
            scenario["declared_timeline_gaps"].append(
                {
                    "member_id": "primary",
                    "start_date": "2030-01-01",
                    "end_date": "2030-02-01",
                    "reason": "Synthetic sabbatical declared before part-time starts.",
                }
            )

            result = _build(root, scenario)

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(len(result["declared_timeline_gaps"]), 1)
            self.assertIn("declared_timeline_gap", {gap["code"] for gap in result["data_gaps"]})
            self.assertIsNone(result["derived_dates"]["full_time_exit_date_by_member"]["primary"])
            self.assertIsNone(result["derived_dates"]["work_cessation_date_by_member"]["primary"])

    def test_rejects_zero_duration_and_non_monthly_dates(self):
        cases = (
            ("end_date", "2025-12-01", "zero or negative duration"),
            ("start_date", "2026-09-15", "first day of a month"),
        )
        for field, value, message in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp_dir:
                root = Path(tmp_dir)
                scenario = _scenario()
                scenario["work_phases"][0][field] = value

                with self.assertRaisesRegex(WorkTransitionScenarioError, message):
                    _build(root, scenario)

    def test_rejects_status_fte_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scenario = _scenario()
            scenario["work_phases"][1]["fte"] = 1.0

            with self.assertRaisesRegex(WorkTransitionScenarioError, "between 0 and 1"):
                _build(root, scenario)

    def test_rejects_unknown_financial_fields_before_projection_increment(self):
        cases = (
            lambda scenario: scenario["work_phases"][0].update({"projected_net_monthly_income": 2500}),
            lambda scenario: scenario["work_phases"][0]["provenance"].update({"projected_net_monthly_income": 2500}),
        )
        for mutate in cases:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as tmp_dir:
                root = Path(tmp_dir)
                scenario = _scenario()
                mutate(scenario)

                with self.assertRaisesRegex(WorkTransitionScenarioError, "unsupported fields"):
                    _build(root, scenario)

    def test_readiness_blocking_gaps_and_hash_mismatch_are_rejected(self):
        cases = (
            (
                _readiness(extra={"data_gaps": [{"code": "missing_input", "blocking": True}], "summary": {"blocking_gap_count": 1}}),
                "blocking data gaps",
            ),
            (_readiness(tamper_hash=True), "content_hash does not match"),
            (_readiness(as_of_date="2026-08-01"), "as_of_date must match"),
            (
                _readiness(
                    extra={
                        "data_gaps": [{"code": "warning", "blocking": False}],
                        "summary": {
                            "required_input_count": 0,
                            "selected_input_count": 0,
                            "source_count": 0,
                            "blocking_gap_count": 0,
                            "warning_count": 1,
                        },
                    }
                ),
                "ready must not include warning",
            ),
            (_readiness(status="partial"), "partial must include warning"),
        )
        for readiness, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as tmp_dir:
                root = Path(tmp_dir)
                with self.assertRaisesRegex(WorkTransitionScenarioError, message):
                    _build(root, _scenario(), readiness=readiness)

    def test_rejects_readiness_missing_required_hashed_core_field(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            readiness = _readiness()
            del readiness["policy"]
            readiness["reproducibility"]["content_hash"] = _content_hash(
                {
                    key: value
                    for key, value in readiness.items()
                    if key not in {"schema_version", "record_type", "reproducibility", "notes"}
                }
            )

            with self.assertRaisesRegex(WorkTransitionScenarioError, "missing required fields"):
                _build(root, _scenario(), readiness=readiness)

    def test_personal_output_outside_workspace_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "scenario.json"
            readiness_path = root / "readiness.json"
            input_path.write_text(json.dumps(_scenario()), encoding="utf-8")
            readiness_path.write_text(json.dumps(_readiness()), encoding="utf-8")

            with patch(
                "family_office_engine.services.work_transition_scenario._workspace_root",
                return_value=root / "workspace",
            ), self.assertRaisesRegex(WorkTransitionScenarioError, "inside family-office-workspace"):
                build_work_transition_scenario(input_path, readiness_path, root / "scenario.snapshot.json")


def _scenario() -> dict:
    return {
        "schema_version": "work-transition-scenario-input/v1",
        "record_type": "WorkTransitionScenarioInput",
        "household_id": "synthetic_household",
        "as_of_date": "2026-08-24",
        "plan_start_date": "2026-09-01",
        "plan_end_date": "2032-12-01",
        "work_phases": [
            _phase("primary_full_time", "primary", "2026-09-01", "2029-12-01", "full_time", 1.0),
            _phase("primary_part_time_60", "primary", "2030-01-01", "2031-12-01", "part_time", 0.6),
            _phase("primary_not_working", "primary", "2032-01-01", "2032-12-01", "not_working", 0.0),
            _phase("spouse_full_time", "spouse", "2026-09-01", "2032-12-01", "full_time", 1.0),
        ],
        "declared_timeline_gaps": [],
    }


def _phase(phase_id: str, member_id: str, start: str, end: str, status: str, fte: float) -> dict:
    return {
        "phase_id": phase_id,
        "member_id": member_id,
        "start_date": start,
        "end_date": end,
        "status": status,
        "fte": fte,
        "compensation_policy_ref": f"employment-compensation-policy/{member_id}-synthetic-v1",
        "contribution_benefit_policy_ref": f"employment-contribution-benefit-policy/{member_id}-synthetic-v1",
        "contractual_constraints": [
            {
                "constraint_id": f"{phase_id}_declared_constraint",
                "constraint_type": "synthetic_contract",
                "description": "Synthetic declared constraint.",
                "binding": "declared",
            }
        ],
        "provenance": {"origin": "synthetic unit test fixture"},
    }


def _readiness(
    status: str = "ready",
    optimization_allowed: bool = True,
    as_of_date: str = "2026-08-24",
    extra: dict | None = None,
    tamper_hash: bool = False,
) -> dict:
    core = {
        "household_id": "synthetic_household",
        "as_of_date": as_of_date,
        "status": status,
        "optimization_allowed": optimization_allowed,
        "policy": {
            "policy_version": "work-transition-source-selection/v1",
            "precedence": ["documentary", "normalized", "derived", "manual"],
            "default_max_age_days": 365,
            "max_age_days_by_category": {},
            "conflicts_are_preserved": True,
        },
        "household_members": ["primary", "spouse"],
        "input_selections": [],
        "sources": [],
        "data_gaps": [],
        "summary": {
            "required_input_count": 0,
            "selected_input_count": 0,
            "source_count": 0,
            "blocking_gap_count": 0,
            "warning_count": 0,
        },
    }
    if extra:
        core.update(extra)
    content_hash = _content_hash(core)
    if tamper_hash:
        content_hash = "tampered-" + content_hash[:55]
    return {
        "schema_version": "work-transition-readiness/v1",
        "record_type": "WorkTransitionReadinessSnapshot",
        **core,
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": content_hash},
    }


def _content_hash(data: dict) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _build(root: Path, scenario: dict, readiness: dict | None = None) -> dict:
    input_path = root / "scenario.json"
    readiness_path = root / "readiness.json"
    input_path.write_text(json.dumps(scenario), encoding="utf-8")
    readiness_path.write_text(json.dumps(readiness or _readiness()), encoding="utf-8")
    with patch(
        "family_office_engine.services.work_transition_scenario._workspace_root",
        return_value=root,
    ):
        return build_work_transition_scenario(input_path, readiness_path, root / "scenario.snapshot.json")


if __name__ == "__main__":
    unittest.main()
