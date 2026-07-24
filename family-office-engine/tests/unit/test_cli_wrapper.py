import sys
import unittest
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    tomllib = None

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class CliWrapperTest(unittest.TestCase):
    def test_pyproject_exposes_fo_console_script(self):
        self.assertIsNotNone(tomllib)
        pyproject = REPOSITORY_ROOT / "family-office-engine" / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

        scripts = data["project"]["scripts"]

        self.assertEqual(scripts["fo"], "family_office_engine.cli.main:main")

    def test_root_shims_exist_for_local_usage(self):
        self.assertTrue((REPOSITORY_ROOT / "fo.ps1").is_file())
        self.assertTrue((REPOSITORY_ROOT / "fo.cmd").is_file())
        self.assertTrue((REPOSITORY_ROOT / "use-family-office.ps1").is_file())


if __name__ == "__main__":
    unittest.main()
