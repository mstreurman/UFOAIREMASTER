#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

python3 tools/remaster/test-m1-authority-bookkeeping-sync.py
python3 tools/remaster/capture-m1-presentation-authority-inventory.py --strict
python3 tools/remaster/test-m1-authoritative-intent-surface.py
python3 tools/remaster/test-m1-intent-catalog-expansion.py
python3 tools/remaster/test-m1-canonical-identity-completeness.py
python3 tools/remaster/test-m1-canonical-identity-lifetime-audit.py
python3 tools/remaster/test-m1-base-installation-owner-extraction.py
python3 tools/remaster/test-m1-research-owner-extraction.py
python3 tools/remaster/test-m1-production-owner-extraction.py
python3 tools/remaster/test-m1-production-contract-normalization.py
python3 tools/remaster/test-m1-create-production-owner-extraction.py
python3 tools/remaster/test-m1-production-runtime-identity.py
python3 tools/remaster/test-m1-stored-ufo-identity.py
python3 tools/remaster/test-m1-ufo-recovery-owner-extraction.py
python3 tools/remaster/test-m1-alien-containment-owner-extraction.py
python3 tools/remaster/test-m1-aircraft-configuration-owner-extraction.py
python3 tools/remaster/test-m1-defence-owner-extraction.py
python3 tools/remaster/test-m1-transfer-owner-extraction.py
python3 tools/remaster/test-m1-save-owner-extraction.py
python3 tools/remaster/test-m1-load-owner-extraction.py
python3 tools/remaster/test-m1-load-last-save-owner-extraction.py
python3 tools/remaster/test-m1-item-production-subject-qualification.py
python3 tools/remaster/test-m1-employee-team-owner-extraction.py
python3 tools/remaster/test-m1-market-owner-extraction.py
python3 tools/remaster/test-m1-authority-runtime-hardening.py
python3 tools/remaster/test-m1-legacy-save-compatibility-contract.py
python3 tools/remaster/test-m1-legacy-wire-compatibility-contract.py

echo "M1 authority bookkeeping qualification: PASS"
echo "  strategic: 57 total / 55 canonical-applied / 2 fail-closed"
echo "  tactical:  15 total / 13 forwarded / 2 fail-closed"
echo "  save/wire: save v4 / protocol 18"
