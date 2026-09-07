#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
BASELINE="ccdf66f0da7723f0689ab253ac1a127982669d52"
LOG="${HOME}/Downloads/UFOAIREMASTER-M1.2-QUALIFICATION.log"

EXPECTED_TRACKED=$'CMakeLists.txt\ndocs/architecture/001-legacy-system-boundaries.md\ndocs/architecture/076-legacy-renderer-and-sound-migration-map.md\nsrc/client/CMakeLists.txt\nsrc/client/battlescape/events/e_parse.cpp'
EXPECTED_UNTRACKED=$'src/client/presentation/canonical_identity.h\nsrc/client/presentation/tactical_presentation_event.h\nsrc/client/presentation/tactical_publication.cpp\nsrc/client/presentation/tactical_publication.h\nsrc/client/presentation/tactical_snapshot.h\nsrc/client/presentation/tactical_snapshot_legacy_adapter.cpp\nsrc/client/presentation/tactical_snapshot_legacy_adapter.h\ntools/remaster/m1-tactical-publication-integration.cpp\ntools/remaster/run-m1-tactical-publication-qualification.sh\ntools/remaster/test-m1-tactical-publication.py'

fail() {
	echo "FAIL: $*" >&2
	exit 1
}

check_exact_source_delta() {
	local actual_tracked actual_untracked
	if ! git diff --cached --quiet; then
		fail "staged changes are present; qualification requires the unapplied-to-index M1.2 source delta only"
	fi
	actual_tracked="$(git diff --name-only | LC_ALL=C sort)"
	actual_untracked="$(git ls-files --others --exclude-standard | LC_ALL=C sort)"
	if [[ "$actual_tracked" != "$EXPECTED_TRACKED" ]]; then
		echo "Expected tracked delta:" >&2
		printf '%s\n' "$EXPECTED_TRACKED" >&2
		echo "Actual tracked delta:" >&2
		printf '%s\n' "$actual_tracked" >&2
		fail "tracked worktree does not match the M1.2 patch scope"
	fi
	if [[ "$actual_untracked" != "$EXPECTED_UNTRACKED" ]]; then
		echo "Expected untracked source delta:" >&2
		printf '%s\n' "$EXPECTED_UNTRACKED" >&2
		echo "Actual untracked source delta:" >&2
		printf '%s\n' "$actual_untracked" >&2
		fail "untracked source worktree does not match the M1.2 patch scope"
	fi
}

mkdir -p "$(dirname "$LOG")"
exec > >(tee "$LOG") 2>&1

cd "$ROOT"

echo "=== UFOAIREMASTER M1.2 tactical publication qualification ==="
date -Is
HEAD="$(git rev-parse HEAD)"
BRANCH="$(git branch --show-current)"
echo "HEAD: $HEAD"
echo "branch: $BRANCH"
git status --short --branch
[[ "$HEAD" == "$BASELINE" ]] || fail "expected uncommitted M1.2 qualification to start at baseline $BASELINE"

echo
echo "--- source-state gate: exact M1.2 delta only ---"
check_exact_source_delta

echo
echo "--- G0 hygiene: git diff --check ---"
git diff --check

echo
echo "--- G0/G1: tactical publication source audit + injected component integration ---"
python3 tools/remaster/test-m1-tactical-publication.py

echo
echo "--- restore/verify pinned Slang cache removed by clean reset ---"
python3 tools/remaster/provision-m0-slang.py

echo
echo "--- G2: sealed canonical regression/repeatability ---"
python3 tools/remaster/run-m0-canonical-regression.py --verify

echo
echo "--- G0: production legacy client build using canonical build tree ---"
cmake --build build-m0-legacy-f44 --target ufo --parallel 8

echo
echo "--- G0: remaster production configure/build ---"
cmake --preset remaster-m0-f44
cmake --build --preset remaster-m0-f44

echo
echo "--- final source-state/hygiene gate ---"
check_exact_source_delta
git diff --check

echo
echo "=== M1.2 QUALIFICATION: PASS ==="
echo "log: $LOG"
