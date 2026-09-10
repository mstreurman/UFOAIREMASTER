#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

python3 tools/remaster/test-m1-item-production-subject-qualification.py
tools/remaster/run-m1-second-pass-identity-qualification.sh
python3 tools/remaster/test-m1-research-production-publication-map.py
python3 tools/remaster/test-m1-production-contract-normalization.py

echo "M1 ItemId + production subject full static qualification: PASS"
echo "NOTE: CreateProduction is canonical-applied; current authority accounting is strategic 31/27, tactical 13/2."
