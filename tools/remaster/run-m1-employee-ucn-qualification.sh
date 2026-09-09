#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

python3 tools/remaster/test-m1-employee-ucn-qualification.py
tools/remaster/run-m1-second-pass-identity-qualification.sh

echo "M1 EmployeeId / CharacterUcn full static qualification: PASS"
echo "NOTE: employee publication and mutation owners remain pending; authority accounting is unchanged."
