#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

python3 tools/remaster/test-m1-market-owner-extraction.py
python3 tools/remaster/test-m1-authoritative-intent-surface.py
python3 tools/remaster/test-m1-legacy-save-compatibility-contract.py
python3 tools/remaster/test-m1-legacy-wire-compatibility-contract.py
python3 tools/remaster/test-m1-canonical-identity-completeness.py

echo "M1 Market owner qualification: PASS"
echo "authority accounting: strategic 38/20; tactical 13/2"
echo "save v4 / protocol 18: unchanged"
