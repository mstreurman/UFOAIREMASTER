#!/usr/bin/env bash
set -euo pipefail

BASELINE="8c8daf73150acff077b63fbf127a1cd1679f4b79"
ROOT="${UFOAI_ROOT:-$HOME/Projects/ufoai-remaster/upstream-ufoai}"
LOG="${HOME}/Downloads/UFOAIREMASTER-M1-STRATEGIC-PUBLICATION-QUALIFICATION-R6.log"
EVIDENCE_REL="docs/reference/reference-m1-strategic-publication-2026-09-07.txt"

mkdir -p "$(dirname "$LOG")"
: > "$LOG"
exec > >(tee -a "$LOG") 2>&1
fail() { echo "FAIL: $*"; exit 1; }

cd "$ROOT"
echo "=== UFOAIREMASTER M1 strategic publication qualification r6 ==="
date --iso-8601=seconds
[[ "$(git branch --show-current)" == "main" ]] || fail "expected branch main"
[[ "$(git rev-parse HEAD)" == "$BASELINE" ]] || fail "expected base $BASELINE"
[[ ! -e "$EVIDENCE_REL" ]] || fail "PASS evidence must not exist before qualification"
grep -F -- "- [ ] Publish immutable strategic snapshots/view data without raw canonical pointers." README.md >/dev/null || fail "README strategic item must be open before qualification"

echo
echo "--- G0 hygiene ---"
git diff --check

echo
echo "--- G1 focused strategic contract/audit ---"
python3 tools/remaster/test-m1-strategic-publication.py

echo
echo "--- G2 sealed canonical regression ---"
python3 tools/remaster/run-m0-canonical-regression.py --verify

echo
echo "--- G3 production legacy client ---"
[[ -f build-m0-legacy-f44/CMakeCache.txt ]] || fail "legacy build tree missing after canonical regression"
cmake --build build-m0-legacy-f44 --target ufo --parallel 8

echo
echo "--- G4 production remaster client ---"
python3 tools/remaster/provision-m0-slang.py
cmake --preset remaster-m0-f44
cmake --build --preset remaster-m0-f44

echo
echo "--- final pre-closure hygiene ---"
git diff --check
[[ ! -e "$EVIDENCE_REL" ]] || fail "qualification unexpectedly created PASS evidence"

echo
echo "=== M1 STRATEGIC PUBLICATION QUALIFICATION R6: PASS ==="
echo "log: $LOG"
