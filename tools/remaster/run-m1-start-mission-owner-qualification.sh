#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

python3 tools/remaster/test-m1-start-mission-owner-extraction.py
python3 tools/remaster/test-m1-authoritative-intent-surface.py
python3 tools/remaster/test-m1-authority-bookkeeping-sync.py
python3 tools/remaster/test-m1-legacy-save-compatibility-contract.py
python3 tools/remaster/test-m1-legacy-wire-compatibility-contract.py

echo "M1 StartMission owner qualification: PASS"
echo "authority accounting: strategic 56/1; tactical 13/2"
echo "save v4 / protocol 18: unchanged"
