#!/usr/bin/env bash
set -euo pipefail
echo "Validate sibling repositories..."
for d in family-office-engine family-office-rules family-office-knowledge family-office-workspace; do [ -d "../$d" ] || echo "Missing ../$d"; done
