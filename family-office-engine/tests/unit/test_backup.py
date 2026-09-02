import hashlib
import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.services.backup import BackupError, create_backup, recovery_drill, restore_backup, verify_backup


class BackupTest(unittest.TestCase):
    def test_encrypted_round_trip_manifest_and_private_exclusions(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder) / "workspace"
            workspace.mkdir()
            (workspace / "planning").mkdir()
            (workspace / "planning/input.json").write_text('{"synthetic": true}', encoding="utf-8")
            (workspace / ".security").mkdir()
            (workspace / "backups").mkdir()
            result = create_backup(workspace)
            backup = workspace / result["output_path"]
            self.assertNotIn(b'{"synthetic": true}', backup.read_bytes())
            self.assertNotIn((workspace / ".security/workspace.key").read_bytes(), backup.read_bytes())
            self.assertEqual(verify_backup(workspace, backup)["status"], "verified")
            self.assertEqual(result["files"][0]["sha256"], hashlib.sha256(b'{"synthetic": true}').hexdigest())

    def test_corruption_and_wrong_key_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder) / "workspace"
            workspace.mkdir()
            (workspace / "data.txt").write_text("safe", encoding="utf-8")
            result = create_backup(workspace)
            backup = workspace / result["output_path"]
            backup.write_bytes(backup.read_bytes()[:-1] + b"x")
            with self.assertRaisesRegex(BackupError, "integrity hash"):
                verify_backup(workspace, backup)

    def test_missing_key_and_traversal_selection_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            workspace = base / "workspace"
            workspace.mkdir()
            (workspace / "data.txt").write_text("safe", encoding="utf-8")
            result = create_backup(workspace)
            backup = workspace / result["output_path"]
            with self.assertRaisesRegex(BackupError, "relative workspace path"):
                restore_backup(workspace, backup, workspace / "out", selections=["../outside"])
            (workspace / ".security/workspace.key").unlink()
            with self.assertRaisesRegex(BackupError, "cannot be authenticated"):
                verify_backup(workspace, backup)

    def test_selective_restore_and_empty_target_drill(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            workspace = base / "workspace"
            workspace.mkdir()
            (workspace / "a.txt").write_text("a", encoding="utf-8")
            (workspace / "nested").mkdir()
            (workspace / "nested/b.txt").write_text("b", encoding="utf-8")
            result = create_backup(workspace)
            backup = workspace / result["output_path"]
            selected = workspace / "selected"
            restore_backup(workspace, backup, selected, selections=["nested/b.txt"])
            self.assertFalse((selected / "a.txt").exists())
            self.assertEqual((selected / "nested/b.txt").read_text(encoding="utf-8"), "b")
            drill = workspace / "drill"
            self.assertEqual(recovery_drill(workspace, backup, drill)["status"], "drill_passed")
            with self.assertRaisesRegex(BackupError, "empty"):
                recovery_drill(workspace, backup, drill)

    def test_retention_and_cli_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder) / "workspace"
            workspace.mkdir()
            (workspace / "data.txt").write_text("safe", encoding="utf-8")
            for index in range(3):
                create_backup(workspace, workspace / "backups" / f"backup-{index}.fobak", retention=2)
            self.assertEqual(len(list((workspace / "backups").glob("*.fobak"))), 2)
            with patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(["backup", "create", "--workspace", str(workspace)]), 0)
            self.assertIn("backup create: ready", stdout.getvalue())
            self.assertIn("Next action:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
