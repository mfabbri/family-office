import hashlib
import json
import tempfile
import unittest
import zipfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.services.sanitized_export import SanitizedExportError, build_sanitized_export


class SanitizedExportTest(unittest.TestCase):
    def test_allowlist_exclusions_and_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root, workspace = _layout(Path(folder))
            _write(root / "family-office-engine/src/family_office_engine/allowed.py", "answer = 42\n")
            _write(root / "family-office-engine/docs/roadmap/v6.md", "# V6\n")
            _write(root / "family-office-engine/docs/reports/check.md", "# Check\n")
            _write(root / "family-office-engine/src/.venv/private.py", "no\n")
            _write(root / "family-office-engine/src/.history/old.py", "no\n")
            _write(root / "family-office-engine/src/snapshots/secret.py", "no\n")
            _write(root / "family-office-engine/src/family-office-workspace/private.py", "no\n")
            _write(root / "family-office-engine/docs/roadmap/backup-plan.md", "no\n")
            _write(root / "family-office-engine/docs/roadmap/source.pdf", "no\n")
            _write(root / "unlisted.txt", "no\n")

            result = build_sanitized_export(root, workspace, workspace / "exports/package.zip")

            self.assertEqual(result["counts"]["included"], 3)
            self.assertEqual(result["counts"]["excluded"], 6)
            self.assertEqual(result["counts"]["excluded_by_reason"], {"backup": 1, "pdf": 1, "private_workspace_or_snapshot": 4})
            with zipfile.ZipFile(workspace / "exports/package.zip") as archive:
                self.assertEqual(archive.namelist(), ["family-office-engine/docs/reports/check.md", "family-office-engine/docs/roadmap/v6.md", "family-office-engine/src/family_office_engine/allowed.py", "manifest.json"])
                manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["schema_version"], "sanitized-export/v1")
            self.assertTrue(all("\\" not in item["path"] for item in manifest["files"]))
            entry = next(item for item in manifest["files"] if item["path"].endswith("allowed.py"))
            self.assertEqual(
                entry["sha256"],
                hashlib.sha256((root / "family-office-engine/src/family_office_engine/allowed.py").read_bytes()).hexdigest(),
            )

    def test_redacts_sensitive_text_and_hashes_exported_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root, workspace = _layout(Path(folder))
            source = root / "family-office-engine/src/family_office_engine/allowed.py"
            _write(source, 'email = "person@example.com"\niban = "IT60X0542811101000000123456"\n')
            build_sanitized_export(root, workspace, workspace / "exports/package.zip")
            with zipfile.ZipFile(workspace / "exports/package.zip") as archive:
                content = archive.read("family-office-engine/src/family_office_engine/allowed.py")
                manifest = json.loads(archive.read("manifest.json"))
            self.assertNotIn(b"person@example.com", content)
            self.assertNotIn(b"IT60X0542811101000000123456", content)
            item = next(item for item in manifest["files"] if item["path"].endswith("allowed.py"))
            self.assertEqual(item["sha256"], hashlib.sha256(content).hexdigest())

    def test_redacts_structured_credentials_and_bearer_headers(self):
        with tempfile.TemporaryDirectory() as folder:
            root, workspace = _layout(Path(folder))
            source = root / "family-office-engine/src/family_office_engine/allowed.py"
            _write(source, 'config = {"api_key": "structured-secret"}\napi_key: yaml-secret\nAuthorization: Bearer bearer-secret\n"Authorization": "Bearer quoted-secret"\n')
            build_sanitized_export(root, workspace, workspace / "exports/package.zip")
            with zipfile.ZipFile(workspace / "exports/package.zip") as archive:
                content = archive.read("family-office-engine/src/family_office_engine/allowed.py")
            self.assertNotIn(b"structured-secret", content)
            self.assertNotIn(b"yaml-secret", content)
            self.assertNotIn(b"bearer-secret", content)
            self.assertNotIn(b"quoted-secret", content)

    def test_cli_names_missing_allowlist_roots(self):
        with tempfile.TemporaryDirectory() as folder:
            root, workspace = _layout(Path(folder))
            with patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(["export", "sanitized", "--source", str(root), "--workspace", str(workspace)]), 0)
            self.assertIn("family-office-engine/docs/reports", stdout.getvalue())

    def test_reproducible_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            root, workspace = _layout(Path(folder))
            _write(root / "family-office-engine/src/family_office_engine/allowed.py", "answer = 42\n")
            first, second = workspace / "exports/first.zip", workspace / "exports/second.zip"
            build_sanitized_export(root, workspace, first)
            build_sanitized_export(root, workspace, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_rejects_target_outside_workspace_or_inside_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root, workspace = _layout(Path(folder))
            with self.assertRaisesRegex(SanitizedExportError, "inside the workspace"):
                build_sanitized_export(root, workspace, root.parent / "escape.zip")
            source_with_workspace = workspace
            with self.assertRaisesRegex(SanitizedExportError, "inside the source"):
                build_sanitized_export(source_with_workspace, workspace, workspace / "package.zip")

    def test_default_project_layout_allows_workspace_child_and_existing_target_needs_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / "project"
            workspace = project / "family-office-workspace"
            project.mkdir(parents=True)
            workspace.mkdir()
            _write(project / "family-office-engine/src/family_office_engine/allowed.py", "answer = 42\n")
            # The real layout has the workspace below the project root; it is excluded by path policy.
            build_sanitized_export(project, workspace, workspace / "exports/package.zip")
            with self.assertRaisesRegex(SanitizedExportError, "already exists"):
                build_sanitized_export(project, workspace, workspace / "exports/package.zip")
            build_sanitized_export(project, workspace, workspace / "exports/package.zip", overwrite=True)

    def test_symlink_to_workspace_is_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            root, workspace = _layout(Path(folder))
            private = workspace / "private.py"
            _write(private, "private = True\n")
            link = root / "family-office-engine/src/family_office_engine/private-link.py"
            try:
                link.symlink_to(private)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            result = build_sanitized_export(root, workspace, workspace / "exports/package.zip")
            self.assertEqual(1, result["counts"]["excluded_by_reason"]["symlink"])

    def test_cli_reports_safe_operator_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            root, workspace = _layout(Path(folder))
            _write(root / "family-office-engine/src/family_office_engine/allowed.py", "answer = 42\n")
            with patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(["export", "sanitized", "--source", str(root), "--workspace", str(workspace)]), 0)
            rendered = stdout.getvalue()
            self.assertIn("Facts:", rendered)
            self.assertIn("Assumptions:", rendered)
            self.assertIn("Limits:", rendered)
            self.assertIn("Next action:", rendered)
            self.assertNotIn("answer = 42", rendered)


def _layout(base: Path) -> tuple[Path, Path]:
    root, workspace = base / "repository", base / "workspace"
    root.mkdir()
    workspace.mkdir()
    return root, workspace


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
