#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

python3 tools/remaster/test-m1-authority-runtime-hardening.py
python3 tools/remaster/test-m1-legacy-save-compatibility-contract.py
python3 tools/remaster/test-m1-legacy-wire-compatibility-contract.py

mkdir -p .build/m1-authority-runtime-hardening
g++ -std=c++11 -Wall -Wextra -Werror -pedantic -I. \
    tools/remaster/m1-strategic-intent-header-contract.cpp \
    -o .build/m1-authority-runtime-hardening/strategic-intent-header-contract
.build/m1-authority-runtime-hardening/strategic-intent-header-contract

g++ -std=c++11 -Wall -Wextra -Werror -pedantic -I. \
    tools/remaster/m1-strategic-publication-contract.cpp \
    -o .build/m1-authority-runtime-hardening/strategic-publication-contract
.build/m1-authority-runtime-hardening/strategic-publication-contract

echo "M1 runtime authority hardening qualification: PASS"
