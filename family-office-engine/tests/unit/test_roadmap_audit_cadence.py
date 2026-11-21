from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from family_office_engine.governance.roadmap_audit import (
    RoadmapAuditCadenceError,
    active_roadmap_path,
    default_paths,
    parse_roadmap,
    validate_audit_cadence,
    validate_predecessor_order,
)


class RoadmapAuditCadenceTest(unittest.TestCase):
    def test_bridge_cli_requires_both_completed_predecessors(self) -> None:
        roadmap_path, _ = default_paths()
        increments = parse_roadmap(roadmap_path.parent / "roadmap-v4b-work-transition.md")
        current = replace(
            next(item for item in increments if item.increment_id == "V4.15e"),
            status="in_progress",
        )
        roadmap_path = roadmap_path.parent / "roadmap-v4b-work-transition.md"
        validate_predecessor_order(increments, current, roadmap_path=roadmap_path)
        for prerequisite in ("V4.15", "V4.15d"):
            for status in ("blocked", "deferred"):
                with self.subTest(prerequisite=prerequisite, status=status):
                    items = [
                        replace(item, status=status) if item.increment_id == prerequisite else item
                        for item in increments
                    ]
                    with self.assertRaisesRegex(RoadmapAuditCadenceError, "must be done"):
                        validate_predecessor_order(items, current, roadmap_path=roadmap_path)
        current_416 = replace(
            next(item for item in increments if item.increment_id == "V4.16"),
            status="in_progress",
        )
        validate_predecessor_order(increments, current_416, roadmap_path=roadmap_path)
        for prerequisite in ("V4.15", "V4.15e"):
            items = [replace(item, status="blocked") if item.increment_id == prerequisite else item for item in increments]
            with self.subTest(v416_prerequisite=prerequisite):
                with self.assertRaisesRegex(RoadmapAuditCadenceError, "declared financial prerequisite"):
                    validate_predecessor_order(items, current_416, roadmap_path=roadmap_path)
        current_417 = replace(
            next(item for item in increments if item.increment_id == "V4.17"),
            status="in_progress",
        )
        validate_predecessor_order(increments, current_417, roadmap_path=roadmap_path)
        incomplete_416 = [
            replace(item, status="blocked") if item.increment_id == "V4.16" else item
            for item in increments
        ]
        with self.assertRaisesRegex(RoadmapAuditCadenceError, "declared financial prerequisite"):
            validate_predecessor_order(incomplete_416, current_417, roadmap_path=roadmap_path)
        current_418 = replace(
            next(item for item in increments if item.increment_id == "V4.18"),
            status="in_progress",
        )
        validate_predecessor_order(increments, current_418, roadmap_path=roadmap_path)
        incomplete_417 = [
            replace(item, status="blocked") if item.increment_id == "V4.17" else item
            for item in increments
        ]
        with self.assertRaisesRegex(RoadmapAuditCadenceError, "declared financial prerequisite"):
            validate_predecessor_order(incomplete_417, current_418, roadmap_path=roadmap_path)
        current_418a = replace(
            next(item for item in increments if item.increment_id == "V4.18a"),
            status="in_progress",
        )
        validate_predecessor_order(increments, current_418a, roadmap_path=roadmap_path)
        incomplete_418 = [
            replace(item, status="blocked") if item.increment_id == "V4.18" else item
            for item in increments
        ]
        with self.assertRaisesRegex(RoadmapAuditCadenceError, "declared financial prerequisite"):
            validate_predecessor_order(incomplete_418, current_418a, roadmap_path=roadmap_path)
        current_419 = replace(
            next(item for item in increments if item.increment_id == "V4.19"),
            status="in_progress",
        )
        validate_predecessor_order(increments, current_419, roadmap_path=roadmap_path)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "docs"
            roadmap_dir = docs / "roadmap"
            roadmap_dir.mkdir(parents=True)
            (docs / "adr").mkdir()
            active_path = roadmap_dir / "roadmap-v4b-work-transition.md"
            v5_path = roadmap_dir / "roadmap-v5-ai-orchestration.md"
            index_path = roadmap_dir / "roadmap-index.md"
            active_path.write_text(
                "# V4B\n\n### V4.14 - Legal parent\n\n**Stato:** `blocked`\n**Tipo:** `functional`\n\n"
                "### V4.18a - Scenario audit\n\n**Stato:** `done`\n**Tipo:** `audit`\n\n"
                "### V4.19 - Registry migration\n\n**Stato:** `in_progress`\n**Tipo:** `functional`\n"
                "**Dipende da:** V4.18a, V5.1, V5.3, V5.4.\n"
                "**Percorso finanziario indipendente:** `../adr/ADR-2026-11-21-separate-pension-entitlement-from-scenario-projection.md`\n",
                encoding="utf-8",
            )
            v5_path.write_text(
                "# V5\n\n### V5.1 - Tool registry\n\n**Stato:** `done`\n**Tipo:** `functional`\n\n"
                "### V5.3 - Supported-question catalog\n\n**Stato:** `done`\n**Tipo:** `functional`\n\n"
                "### V5.4 - Intent router\n\n**Stato:** `done`\n**Tipo:** `functional`\n",
                encoding="utf-8",
            )
            index_path.write_text(
                "| Ordine | Roadmap | Obiettivo | Stato |\n|---:|---|---|---|\n"
                "| 5 | `roadmap-v4b-work-transition.md` | V4B | `in_progress` |\n"
                "| 6 | `roadmap-v5-ai-orchestration.md` | V5 | `done` |\n",
                encoding="utf-8",
            )
            (docs / "adr" / "ADR-2026-11-21-separate-pension-entitlement-from-scenario-projection.md").write_text(
                "Accepted projection ADR\n", encoding="utf-8"
            )
            temp_increments = parse_roadmap(active_path)
            temp_current = next(item for item in temp_increments if item.increment_id == "V4.19")
            validate_predecessor_order(temp_increments, temp_current, roadmap_path=active_path)
            v5_original = v5_path.read_text(encoding="utf-8")
            for prerequisite, title in (("V5.1", "Tool registry"), ("V5.3", "Supported-question catalog"),
                                        ("V5.4", "Intent router")):
                with self.subTest(prerequisite=prerequisite):
                    marker = f"### {prerequisite} - {title}\n\n**Stato:** `done`"
                    v5_path.write_text(v5_original.replace(marker, marker.replace("`done`", "`blocked`")), encoding="utf-8")
                    with self.assertRaisesRegex(RoadmapAuditCadenceError, f"financial prerequisite {prerequisite} is 'blocked'"):
                        validate_predecessor_order(temp_increments, temp_current, roadmap_path=active_path)
            v5_path.write_text(v5_original, encoding="utf-8")

    def test_repository_roadmap_and_current_increment_are_consistent(self) -> None:
        roadmap_path, current_path = default_paths()

        report = validate_audit_cadence(roadmap_path, current_path)

        self.assertTrue(report.current_increment_id.startswith("V"))
        if report.audit_due:
            self.assertIn(report.current_increment_kind, {"audit", "functional"})
        else:
            self.assertLess(report.functional_since_last_audit, 4)

    def test_active_roadmap_is_selected_from_index(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            active = root / "active.md"
            active.write_text("# Active\n", encoding="utf-8")
            index = root / "roadmap-index.md"
            index.write_text(
                "| Ordine | Roadmap | Obiettivo | Stato |\n"
                "|---:|---|---|---|\n"
                "| 0 | `done.md` | Done | `done` |\n"
                "| 1 | `active.md` | Active | `in_progress` |\n",
                encoding="utf-8",
            )

            self.assertEqual(active_roadmap_path(index), active)

    def test_zero_to_three_completed_functional_increments_allow_functional_work(self) -> None:
        for count in range(4):
            with self.subTest(count=count):
                entries = [("V4.1", "audit", "done")]
                entries.extend(
                    (f"V4.{index + 2}", "functional", "done")
                    for index in range(count)
                )
                entries.append(("V4.9", "functional", "planned"))

                report = self._validate(entries, "V4.9", "planned")

                self.assertFalse(report.audit_due)
                self.assertEqual(report.functional_since_last_audit, count)

    def test_four_completed_functional_increments_require_audit(self) -> None:
        entries = [
            ("V4.1", "audit", "done"),
            ("V4.2", "functional", "done"),
            ("V4.3", "functional", "done"),
            ("V4.4", "functional", "done"),
            ("V4.5", "functional", "done"),
            ("V4.6", "functional", "planned"),
        ]

        with self.assertRaisesRegex(RoadmapAuditCadenceError, "Audit due after 4"):
            self._validate(entries, "V4.6", "planned")

    def test_fourth_completed_functional_increment_can_wait_for_its_required_audit(self) -> None:
        entries = [
            ("V4.1", "audit", "done"),
            ("V4.2", "functional", "done"),
            ("V4.3", "functional", "done"),
            ("V4.4", "functional", "done"),
            ("V4.5", "functional", "done"),
        ]

        report = self._validate(entries, "V4.5", "done")

        self.assertTrue(report.audit_due)
        self.assertEqual("functional", report.current_increment_kind)

    def test_fourth_completed_functional_increment_can_wait_when_later_work_is_planned(self) -> None:
        entries = [
            ("V4.1", "audit", "done"),
            ("V4.2", "functional", "done"),
            ("V4.3", "functional", "done"),
            ("V4.4", "functional", "done"),
            ("V4.5", "functional", "done"),
            ("V4.6", "functional", "planned"),
        ]

        report = self._validate(entries, "V4.5", "done")

        self.assertTrue(report.audit_due)
        self.assertEqual("functional", report.current_increment_kind)

    def test_due_audit_is_allowed_as_current_increment(self) -> None:
        entries = [
            ("V4.1", "audit", "done"),
            ("V4.2", "functional", "done"),
            ("V4.3", "functional", "done"),
            ("V4.4", "functional", "done"),
            ("V4.5", "functional", "done"),
            ("V4.5a", "audit", "in_progress"),
        ]

        report = self._validate(entries, "V4.5a", "in_progress")

        self.assertTrue(report.audit_due)
        self.assertEqual(report.current_increment_kind, "audit")

    def test_suffixed_increment_header_is_parsed_as_a_separate_section(self) -> None:
        entries = [
            ("V4.3", "functional", "done"),
            ("V4.3a", "functional", "in_progress"),
        ]

        report = self._validate(entries, "V4.3a", "in_progress")

        self.assertEqual("V4.3a", report.current_increment_id)
        self.assertEqual("functional", report.current_increment_kind)

    def test_due_audit_does_not_block_a_docs_increment(self) -> None:
        entries = [
            ("V4.1", "audit", "done"),
            ("V4.2", "functional", "done"),
            ("V4.3", "functional", "done"),
            ("V4.4", "functional", "done"),
            ("V4.5", "functional", "done"),
            ("V4.5a", "docs", "planned"),
        ]

        report = self._validate(entries, "V4.5a", "planned")

        self.assertTrue(report.audit_due)
        self.assertEqual("docs", report.current_increment_kind)

    def test_completed_audit_resets_the_counter(self) -> None:
        entries = [
            ("V4.1", "functional", "done"),
            ("V4.2", "functional", "done"),
            ("V4.3", "functional", "done"),
            ("V4.4", "functional", "done"),
            ("V4.4a", "audit", "done"),
            ("V4.5", "functional", "planned"),
        ]

        report = self._validate(entries, "V4.5", "planned")

        self.assertFalse(report.audit_due)
        self.assertEqual(report.functional_since_last_audit, 0)
        self.assertEqual(report.last_completed_audit_id, "V4.4a")

    def test_missing_increment_type_is_rejected(self) -> None:
        roadmap = (
            "# Roadmap\n\n## Incrementi\n\n"
            "### V4.1 - Missing type\n\n"
            "**Stato:** `planned`\n"
        )

        with self.assertRaisesRegex(RoadmapAuditCadenceError, "exactly one Tipo"):
            self._validate_text(roadmap, self._current("V4.1", "planned"))

    def test_current_status_must_match_roadmap(self) -> None:
        entries = [("V4.1", "functional", "planned")]

        with self.assertRaisesRegex(RoadmapAuditCadenceError, "has status 'in_progress'"):
            self._validate(entries, "V4.1", "in_progress")

    def test_current_increment_must_exist_in_roadmap(self) -> None:
        entries = [("V4.1", "functional", "done")]

        with self.assertRaisesRegex(RoadmapAuditCadenceError, "V4.2 is absent"):
            self._validate(entries, "V4.2", "planned")

    def test_downstream_functional_increment_cannot_skip_blocked_predecessor(self) -> None:
        entries = [
            ("V4.1", "functional", "done"),
            ("V4.2", "functional", "blocked"),
            ("V4.3", "functional", "planned"),
        ]

        with self.assertRaisesRegex(
            RoadmapAuditCadenceError,
            "predecessor V4.2 is 'blocked'; resolve the earliest unfinished predecessor first",
        ):
            self._validate(entries, "V4.3", "planned")

    def test_later_release_cannot_skip_blocked_predecessor_even_if_listed_first(self) -> None:
        entries = [
            ("V4.15c", "audit", "planned"),
            ("V4.14", "functional", "blocked"),
        ]

        with self.assertRaisesRegex(
            RoadmapAuditCadenceError,
            "Cannot select V4.15c: predecessor V4.14 is 'blocked'",
        ):
            self._validate(entries, "V4.15c", "planned")

    def test_adr_scoped_financial_path_can_bypass_unrelated_blocker_but_checks_dependencies(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            roadmap_path = root / "docs" / "roadmap" / "roadmap.md"
            roadmap_path.parent.mkdir(parents=True)
            adr = root / "docs" / "adr" / "scenario.md"
            adr.parent.mkdir(parents=True)
            adr.write_text("Accepted ADR\n", encoding="utf-8")
            roadmap_path.write_text(
                "# Roadmap\n\n"
                "### V4.14 - Legal parent\n\n**Stato:** `blocked`\n**Tipo:** `functional`\n\n"
                "### V4.2 - Wealth model\n\n**Stato:** `done`\n**Tipo:** `functional`\n\n"
                "### V4.3 - Household cashflow\n\n**Stato:** `done`\n**Tipo:** `functional`\n\n"
                "### V4.5 - Lifecycle model\n\n**Stato:** `done`\n**Tipo:** `functional`\n\n"
                "### V4.15 - Financial projection\n\n**Stato:** `in_progress`\n**Tipo:** `functional`\n"
                "**Dipende da:** V4.2, V4.3, V4.5.\n"
                "**Percorso finanziario indipendente:** `../adr/scenario.md`\n",
                encoding="utf-8",
            )
            current_path = root / "current.md"
            current_path.write_text(self._current("V4.15", "in_progress"), encoding="utf-8")

            report = validate_audit_cadence(roadmap_path, current_path)

            self.assertEqual("V4.15", report.current_increment_id)

            roadmap_path.write_text(roadmap_path.read_text(encoding="utf-8").replace(
                "### V4.5 - Lifecycle model\n\n**Stato:** `done`",
                "### V4.5 - Lifecycle model\n\n**Stato:** `blocked`",
            ), encoding="utf-8")
            with self.assertRaisesRegex(RoadmapAuditCadenceError, "financial prerequisite V4.5 is 'blocked'"):
                validate_audit_cadence(roadmap_path, current_path)

    def test_downstream_audit_cannot_skip_in_progress_predecessor(self) -> None:
        entries = [
            ("V4.1", "functional", "done"),
            ("V4.2", "functional", "in_progress"),
            ("V4.2a", "audit", "planned"),
        ]

        with self.assertRaisesRegex(
            RoadmapAuditCadenceError,
            "predecessor V4.2 is 'in_progress'",
        ):
            self._validate(entries, "V4.2a", "planned")

    def test_minimum_functional_slice_can_unblock_its_parent_without_skipping_older_siblings(
        self,
    ) -> None:
        entries = [
            ("V4.14w-a", "functional", "planned"),
            ("V4.14", "functional", "blocked"),
            ("V4.14w", "functional", "blocked"),
            ("V4.14x", "audit", "blocked"),
        ]

        report = self._validate(entries, "V4.14w-a", "planned")

        self.assertEqual("V4.14w-a", report.current_increment_id)

    def test_audit_remediation_slice_can_address_its_own_blocked_parent(self) -> None:
        entries = [
            ("V4.14", "functional", "blocked"),
            ("V4.14w", "functional", "blocked"),
            ("V4.14w-m", "audit", "planned"),
        ]

        report = self._validate(entries, "V4.14w-m", "planned")

        self.assertEqual("V4.14w-m", report.current_increment_id)

    def test_functional_slice_cannot_skip_earlier_sibling_in_its_release(self) -> None:
        entries = [
            ("V4.14w-b", "functional", "planned"),
            ("V4.14w-a", "functional", "blocked"),
        ]

        with self.assertRaisesRegex(
            RoadmapAuditCadenceError,
            "predecessor V4.14w-a is 'blocked'",
        ):
            self._validate(entries, "V4.14w-b", "planned")

    def test_governance_work_can_reconcile_roadmap_without_skipping(self) -> None:
        entries = [
            ("V4.1", "functional", "blocked"),
            ("V4.1a", "governance", "in_progress"),
        ]

        report = self._validate(entries, "V4.1a", "in_progress")

        self.assertEqual("V4.1a", report.current_increment_id)

    def _validate(
        self,
        entries: list[tuple[str, str, str]],
        current_id: str,
        current_status: str,
    ):
        sections = []
        for increment_id, kind, status in entries:
            sections.append(
                f"### {increment_id} - Synthetic increment\n\n"
                f"**Stato:** `{status}`\n"
                f"**Tipo:** `{kind}`\n"
            )
        roadmap = "# Roadmap\n\n## Incrementi\n\n" + "\n".join(sections)
        return self._validate_text(
            roadmap, self._current(current_id, current_status)
        )

    def _validate_text(self, roadmap: str, current: str):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            roadmap_path = root / "roadmap.md"
            current_path = root / "current.md"
            roadmap_path.write_text(roadmap, encoding="utf-8")
            current_path.write_text(current, encoding="utf-8")
            return validate_audit_cadence(roadmap_path, current_path)

    @staticmethod
    def _current(increment_id: str, status: str) -> str:
        return (
            "# Current Next Increment\n\n"
            "## ID e titolo\n\n"
            f"{increment_id} - Synthetic increment.\n\n"
            "## Stato\n\n"
            f"`{status}`\n"
        )


if __name__ == "__main__":
    unittest.main()
