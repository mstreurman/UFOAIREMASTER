#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

BASE_COMMIT="f36eef93da1be052d46ae0f7dbe8dce6b99a206a"
README_BASE_BLOB="af4e171b9942c1351c00271e5c02934c375864f7"
BUILD_DIR="$ROOT/.build/m1-canonical-identity"
LOG="${HOME}/Downloads/UFOAIREMASTER-M1-TYPED-IDENTITY-QUALIFICATION.log"
REFERENCE_REL="docs/reference/reference-m1-typed-identity-2026-09-07.txt"
REFERENCE="$ROOT/$REFERENCE_REL"

mkdir -p "$(dirname "$LOG")" "$BUILD_DIR"
exec > >(tee "$LOG") 2>&1

echo "=== UFOAIREMASTER M1 typed canonical identity qualification ==="
date --iso-8601=seconds
printf 'HEAD:   %s\n' "$(git rev-parse HEAD)"
printf 'branch: %s\n' "$(git branch --show-current)"

fail() {
	echo "M1 typed canonical identity qualification: FAIL: $*" >&2
	exit 1
}

require_exact_paths() {
	python3 - "$@" <<'PY'
import subprocess
import sys
expected = sorted(sys.argv[1:])
lines = subprocess.check_output(
    ["git", "status", "--porcelain=v1", "--untracked-files=all"],
    text=True,
).splitlines()
actual = sorted(line[3:] for line in lines if line.strip())
if actual != expected:
    print("unexpected worktree state", file=sys.stderr)
    print("expected:", file=sys.stderr)
    for path in expected:
        print(f"  {path}", file=sys.stderr)
    print("actual:", file=sys.stderr)
    for path in actual:
        print(f"  {path}", file=sys.stderr)
    raise SystemExit(1)
PY
}

check_text_hygiene() {
	python3 - "$@" <<'PY'
from pathlib import Path
import sys
bad = []
for raw in sys.argv[1:]:
    path = Path(raw)
    if not path.is_file():
        bad.append(f"missing file: {path}")
        continue
    text = path.read_text(encoding="utf-8")
    if "\r" in text:
        bad.append(f"CR line ending: {path}")
    for number, line in enumerate(text.splitlines(), 1):
        if line.rstrip(" \t") != line:
            bad.append(f"trailing whitespace: {path}:{number}")
    if text and not text.endswith("\n"):
        bad.append(f"missing final newline: {path}")
if bad:
    print("\n".join(bad), file=sys.stderr)
    raise SystemExit(1)
PY
}

[[ "$(git branch --show-current)" == "main" ]] || fail "expected branch main"
[[ "$(git rev-parse HEAD)" == "$BASE_COMMIT" ]] || fail "expected HEAD $BASE_COMMIT"

PRE_PATHS=(
	"src/client/presentation/canonical_identity.h"
	"tools/remaster/m1-canonical-identity-contract.cpp"
	"tools/remaster/run-m1-canonical-identity-qualification.sh"
)

FINAL_PATHS=(
	"README.md"
	"$REFERENCE_REL"
	"${PRE_PATHS[@]}"
)

echo
echo "--- source-state gate: exact identity delta only ---"
require_exact_paths "${PRE_PATHS[@]}" || fail "worktree contains files outside the identity slice"

echo
echo "--- G0 hygiene ---"
git diff --check -- src/client/presentation/canonical_identity.h
check_text_hygiene \
	src/client/presentation/canonical_identity.h \
	tools/remaster/m1-canonical-identity-contract.cpp \
	tools/remaster/run-m1-canonical-identity-qualification.sh

echo
echo "--- G1: strict C++11 identity contract ---"
g++ \
	-std=c++11 \
	-Wall -Wextra -Werror -pedantic \
	-I"$ROOT" \
	tools/remaster/m1-canonical-identity-contract.cpp \
	-o "$BUILD_DIR/m1-canonical-identity-contract"
"$BUILD_DIR/m1-canonical-identity-contract"

echo
echo "--- G0: production legacy client incremental build ---"
[[ -f "$ROOT/build-m0-legacy-f44/CMakeCache.txt" ]] || fail "qualified build-m0-legacy-f44 tree is missing; do not silently reconfigure"
cmake --build "$ROOT/build-m0-legacy-f44" --target ufo --parallel 8

echo
echo "--- G0: production remaster client incremental build ---"
[[ -f "$ROOT/build-m0-remaster-f44/CMakeCache.txt" ]] || fail "qualified build-m0-remaster-f44 tree is missing; do not silently reconfigure"
cmake --build "$ROOT/build-m0-remaster-f44" --target ufo --parallel 8

echo
echo "--- documentation/evidence closure ---"
[[ "$(git hash-object README.md)" == "$README_BASE_BLOB" ]] || fail "README is not the exact f36eef93da identity baseline"
[[ ! -e "$REFERENCE" ]] || fail "$REFERENCE_REL already exists unexpectedly"

README_TMP="$(mktemp)"
README_BACKUP="$(mktemp)"
cp README.md "$README_BACKUP"
cleanup_docs() {
	rc=$?
	if (( rc != 0 )); then
		cp "$README_BACKUP" README.md
		rm -f "$REFERENCE"
	fi
	rm -f "$README_TMP" "$README_BACKUP"
	exit "$rc"
}
trap cleanup_docs EXIT

python3 - README.md "$README_TMP" <<'PY'
from pathlib import Path
import sys
src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text(encoding="utf-8")
replacements = [
(
"3. introduce typed presentation IDs and intent dispatch — **tactical canonical entity identity introduced; remaining strategic/intent typing active**;",
"3. introduce typed presentation IDs and intent dispatch — **typed presentation identity complete; typed intent dispatch remaining**;"
),
(
"- [ ] Introduce typed presentation IDs where required.\n"
"  - [x] Introduce the strong canonical entity identity used by tactical publication.\n"
"  - [ ] Extend typed identity coverage to the remaining strategic/view/intent seams as those seams are introduced.",
"- [x] Introduce typed presentation IDs where required.\n"
"  - [x] Introduce the strong canonical entity identity used by tactical publication.\n"
"  - [x] Define strong 32-bit canonical bridge identities for Mission, Aircraft, Base, Installation, Nation, Employee, Technology, Production, Message and Item domains required by strategic view/intent contracts.\n"
"  - [x] Keep canonical identity domains mutually distinct, value-only and free of implicit integer or cross-domain conversions."
),
(
"- [`docs/reference/reference-m1-tactical-publication-2026-09-06.txt`](docs/reference/reference-m1-tactical-publication-2026-09-06.txt) — M1.2 tactical publication qualification evidence.",
"- [`docs/reference/reference-m1-tactical-publication-2026-09-06.txt`](docs/reference/reference-m1-tactical-publication-2026-09-06.txt) — M1.2 tactical publication qualification evidence.\n"
"- [`docs/reference/reference-m1-typed-identity-2026-09-07.txt`](docs/reference/reference-m1-typed-identity-2026-09-07.txt) — M1 typed canonical presentation identity qualification evidence."
),
(
"M1.2 tactical publication is qualified. The tactical client now exposes a strong canonical entity identity and immutable, value-only snapshot/event publication after canonical mirror mutation, with legacy local-entity access confined to an adapter. The dedicated M1 lane passes 3/3 tests; the sealed canonical regression remains 104/104 in both repeatability passes with the same evidence identity; and both legacy and remaster production client builds pass. The qualification transcript is summarized in `docs/reference/reference-m1-tactical-publication-2026-09-06.txt`.",
"M1.2 tactical publication is qualified. The tactical client now exposes a strong canonical entity identity and immutable, value-only snapshot/event publication after canonical mirror mutation, with legacy local-entity access confined to an adapter. The dedicated M1 lane passes 3/3 tests; the sealed canonical regression remains 104/104 in both repeatability passes with the same evidence identity; and both legacy and remaster production client builds pass. The qualification transcript is summarized in `docs/reference/reference-m1-tactical-publication-2026-09-06.txt`.\n\n"
"The M1 typed presentation identity contract is also qualified. Tactical `EntityId` remains unchanged, while the strategic/view/intent bridge now defines distinct 32-bit `MissionId`, `AircraftId`, `BaseId`, `InstallationId`, `NationId`, `EmployeeId`, `TechnologyId`, `ProductionId`, `MessageId` and `ItemId` domains. The strict C++11 contract proves domain separation and value semantics, and both qualified production client configurations rebuild successfully."
),
(
"M0 is complete; the M1 canonical spatial-service workstream and M1.2 tactical publication slice are qualified. Active M1 work now moves to immutable strategic publication/view data and typed intent dispatch, extending typed identity coverage as those seams are introduced.",
"M0 is complete; the M1 canonical spatial-service workstream, M1.2 tactical publication slice and typed presentation identity contract are qualified. Active M1 work now moves to immutable strategic publication/view data and typed intent dispatch; those remaining seams consume the completed typed identity contract."
),
]
for old, new in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"README transform source block count for {old[:48]!r}: expected 1, got {count}")
    text = text.replace(old, new, 1)
dst.write_text(text, encoding="utf-8")
PY

cat > "$REFERENCE" <<EOF_REF
UFOAIREMASTER_M1_TYPED_IDENTITY_REFERENCE_V1
schema.version=1
qualification.slice=M1-typed-identity
qualification.result=PASS
qualification.completed_local=$(date --iso-8601=seconds)
base.branch=main
base.commit=$BASE_COMMIT

identity.domain.count=11
identity.domain.01=EntityId
identity.domain.02=MissionId
identity.domain.03=AircraftId
identity.domain.04=BaseId
identity.domain.05=InstallationId
identity.domain.06=NationId
identity.domain.07=EmployeeId
identity.domain.08=TechnologyId
identity.domain.09=ProductionId
identity.domain.10=MessageId
identity.domain.11=ItemId
identity.strategic_authority=architecture-078
identity.storage=uint32_t
identity.invalid_value=UINT32_MAX
identity.implicit_integer_conversion=FORBIDDEN
identity.cross_domain_conversion=FORBIDDEN
identity.raw_pointer_boundary=FORBIDDEN

gate.strict_cpp11_contract=PASS
gate.strict_cpp11_warnings_as_errors=PASS
gate.production_legacy_ufo_incremental_build=PASS
gate.production_remaster_ufo_incremental_build=PASS
gate.diff_hygiene=PASS
canonical.regression.rerun=NOT_REQUIRED
canonical.regression.rationale=Identity-only declarations preserve existing EntityId behavior and do not modify gameplay, protocol, mutation or publication logic.
prior.canonical.evidence_blake3_256=b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e
EOF_REF

check_text_hygiene "$README_TMP" "$REFERENCE"
cp "$README_TMP" README.md

echo
echo "--- final exact worktree + hygiene gate ---"
require_exact_paths "${FINAL_PATHS[@]}" || fail "final worktree contains files outside the completed identity slice"
git diff --check -- README.md src/client/presentation/canonical_identity.h
check_text_hygiene \
	README.md \
	"$REFERENCE_REL" \
	src/client/presentation/canonical_identity.h \
	tools/remaster/m1-canonical-identity-contract.cpp \
	tools/remaster/run-m1-canonical-identity-qualification.sh

trap - EXIT
rm -f "$README_TMP" "$README_BACKUP"

echo
git status --short --branch
echo
echo "=== M1 TYPED CANONICAL IDENTITY QUALIFICATION: PASS ==="
echo "log: $LOG"
