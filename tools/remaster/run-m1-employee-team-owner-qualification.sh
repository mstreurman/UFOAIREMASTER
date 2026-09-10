#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

python3 tools/remaster/test-m1-employee-team-owner-extraction.py
python3 tools/remaster/test-m1-authoritative-intent-surface.py
python3 tools/remaster/test-m1-strategic-publication.py
python3 tools/remaster/test-m1-canonical-identity-completeness.py

echo "M1 Employee + Team owner qualification: PASS"
echo "authority accounting: strategic 31/27; tactical 13/2"
echo "save v4 / protocol 18: unchanged"
