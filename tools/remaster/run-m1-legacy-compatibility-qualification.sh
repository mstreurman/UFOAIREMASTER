#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

python3 tools/remaster/test-m1-legacy-save-compatibility-contract.py
python3 tools/remaster/test-m1-legacy-wire-compatibility-contract.py

# Re-run the established identity/publication guards that protect the same
# canonical/presentation boundary. These files are already part of M1.
python3 tools/remaster/test-m1-stored-ufo-identity.py
python3 tools/remaster/test-m1-canonical-identity-completeness.py
python3 tools/remaster/test-m1-strategic-publication.py

echo "M1 legacy compatibility static qualification: PASS"
echo "NOTE: classic<->remaster cross-binary save/network qualification remains a separate dynamic gate."
