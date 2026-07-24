from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from family_office_engine.governance.roadmap_audit import (
    RoadmapAuditCadenceError,
    active_roadmap_path,
    default_paths,
    validate_audit_cadence,
)


class RoadmapAuditCadenceTest(unittest.TestCase):
    def test_repository_roadmap_and_current_increment_are_consistent(self) -> None:
        roadmap_path, current_path = default_paths()

        report = validate_audit_cadence(roadmap_path, current_path)

        self.assertTrue(report.current_increment_id.startswith("V"))
        if report.audit_due:
            self.assertEqual(report.current_increment_kind, "audit")
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
