#!/usr/bin/env bash
set -euo pipefail
python3 - <<PY
from pathlib import Path
for r in ["engine","rules","knowledge","workspace"]:
    p=Path("../family-office-"+r)
    print(r, "OK" if p.exists() else "MISSING")
PY
