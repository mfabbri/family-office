import json
import os
import stat
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.services.security import (
    SecurityError,
    build_security_check,
    decrypt_file,
    encrypt_file,
    redact_sensitive_text,
)


class SecurityTest(unittest.TestCase):
    def test_authenticated_encryption_round_trip_and_wrong_key(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            source = workspace / "documents" / "synthetic.txt"
            source.parent.mkdir()
            source.write_text("synthetic content", encoding="utf-8")
            encrypted = encrypt_file(workspace, source, workspace / "snapshots" / "synthetic.txt.enc")
            self.assertNotEqual(encrypted.read_bytes(), source.read_bytes())
            restored = decrypt_file(workspace, encrypted, workspace / "restored.txt")
            self.assertEqual(restored.read_text(encoding="utf-8"), "synthetic content")
            workspace.joinpath(".security", "workspace.key").write_bytes(b"invalid")
            with self.assertRaisesRegex(SecurityError, "invalid key"):
                decrypt_file(workspace, encrypted, workspace / "restored-again.txt")

    def test_paths_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            source = workspace / "input.txt"
            source.write_text("safe", encoding="utf-8")
            with self.assertRaisesRegex(SecurityError, "inside the workspace"):
                encrypt_file(workspace, source, workspace.parent / "escape.enc")

    def test_check_reports_secret_sensitive_file_and_permissions_without_content(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder) / "workspace"
            repository = Path(folder) / "repository"
            workspace.mkdir()
            repository.mkdir()
            fixture_value = "live-" + "credential-value"
            (repository / "bad.py").write_text(f'API_KEY = "{fixture_value}"\n', encoding="utf-8")
            (workspace / "identity.pem").write_text("synthetic", encoding="utf-8")
            report = build_security_check(workspace, repository)
            self.assertEqual(report["schema_version"], "security-check/v1")
            self.assertEqual(report["status"], "attention")
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("secret_detected", codes)
            self.assertIn("unencrypted_sensitive_file", codes)
            rendered = json.dumps(report)
            self.assertNotIn(fixture_value, rendered)

    def test_redaction_and_cli_are_safe(self):
        fixture_value = "live-" + "credential-value"
        self.assertNotIn(fixture_value, redact_sensitive_text(f'token="{fixture_value}"'))
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder) / "workspace"
            repository = Path(folder) / "repository"
            workspace.mkdir()
            repository.mkdir()
            with patch("sys.stdout", new_callable=StringIO) as output:
                self.assertEqual(main(["security", "check", "--workspace", str(workspace), "--repository", str(repository)]), 0)
            self.assertNotIn(fixture_value, output.getvalue())
            self.assertIn("security check: ready", output.getvalue())

    def test_excessive_secret_store_permissions_are_finding(self):
        if os.name == "nt":
            self.skipTest("Windows ACLs are not represented by POSIX mode bits")
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            report = build_security_check(workspace)
            key = workspace / ".security" / "workspace.key"
            try:
                key.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
                report = build_security_check(workspace)
                self.assertIn("secret_store_permissions", {item["code"] for item in report["findings"]})
            except PermissionError:
                self.skipTest("filesystem does not permit synthetic permission change")


if __name__ == "__main__":
    unittest.main()
