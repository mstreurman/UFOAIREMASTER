#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

python3 tools/remaster/test-m1-canonical-identity-lifetime-audit.py
python3 tools/remaster/test-m1-canonical-identity-completeness.py
tools/remaster/run-m1-legacy-compatibility-qualification.sh

echo "M1 second-pass canonical identity static qualification: PASS"
echo "NOTE: tactical publication, canonical regression, and fresh legacy/remaster builds remain separate gates."
