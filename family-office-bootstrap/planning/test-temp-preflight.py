"""Non-invasive preflight for a Python test temporary directory.

No application tests or business rules are modified. Verifies creation, use,
cleanup, and nested temporary directories in the process environment.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-parent", required=True)
    args = parser.parse_args()
    expected = Path(args.expected_parent).resolve()
    result: dict[str, object] = {
        "status": "fail",
        "python": sys.executable,
        "expected_temp_parent": str(expected),
        "TEMP": os.environ.get("TEMP"),
        "TMP": os.environ.get("TMP"),
        "TMPDIR": os.environ.get("TMPDIR"),
    }
    try:
        if not expected.is_dir():
            raise RuntimeError("expected temporary parent does not exist")
        # Force the OS temp lookup in this interpreter and assert location.
        actual = Path(tempfile.gettempdir()).resolve()
        result["actual_temp_parent"] = str(actual)
        if os.path.normcase(str(actual)) != os.path.normcase(str(expected)):
            raise RuntimeError("Python ignored the requested temp parent")
        with tempfile.TemporaryDirectory(prefix="fo-smoke-") as outer:
            outer_path = Path(outer)
            payload = outer_path / "write-read.txt"
            payload.write_text("test-temp-ok", encoding="utf-8")
            if payload.read_text(encoding="utf-8") != "test-temp-ok":
                raise RuntimeError("temp read/write mismatch")
            with tempfile.TemporaryDirectory(prefix="nested-", dir=outer) as nested:
                (Path(nested) / "probe.txt").write_text("ok", encoding="utf-8")
            if (outer_path / Path(nested).name).exists():
                raise RuntimeError("nested temp cleanup failed")
        if outer_path.exists():
            raise RuntimeError("temp cleanup failed")
        result["status"] = "pass"
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        result["failure"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
