#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python3 tools/remaster/test-m1-create-production-owner-extraction.py
python3 tools/remaster/test-m1-production-contract-normalization.py
python3 tools/remaster/test-m1-production-owner-extraction.py
python3 tools/remaster/test-m1-item-production-subject-qualification.py
python3 tools/remaster/test-m1-research-production-publication-map.py
python3 tools/remaster/test-m1-authoritative-intent-surface.py
