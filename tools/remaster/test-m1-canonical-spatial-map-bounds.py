#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HEADER_REL = Path("src/server/sv_spatial.h")
SERVER_REL = Path("src/server/sv_game.cpp")
PROBE_REL = Path("tools/remaster/m1-canonical-spatial-map-bounds.cpp")
PASS_MARKER = "M1.1b.2a map-bounds direct fixture: PASS"
FORBIDDEN_PRESENTATION_TOKENS = ("OpenGL", "Vulkan", "Vk", "Jolt", "OpenAL", "renderer")


class GateError(RuntimeError):
    pass


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise GateError("not inside a Git work tree")
    return Path(proc.stdout.strip()).resolve()


def function_body(text: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^)]*\)\s*\{{", text)
    if not match:
        raise GateError(f"function not found: {name}")
    brace = text.find("{", match.start())
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1:index]
    raise GateError(f"unterminated function body: {name}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateError(message)


def audit(root: Path) -> None:
    header = root / HEADER_REL
    server = root / SERVER_REL
    probe = root / PROBE_REL
    for path in (header, server, probe):
        require(path.is_file(), f"missing required file: {path.relative_to(root)}")

    header_text = header.read_text(encoding="utf-8")
    server_text = server.read_text(encoding="utf-8")
    helper_body = function_body(header_text, "SV_CanonicalPointWithinMapBounds")
    wrapper_body = function_body(server_text, "SV_GridIsOnMap")

    require('#include "sv_spatial.h"' in server_text, "sv_game.cpp does not include sv_spatial.h")
    delegation = re.search(
        r"return\s+SV_CanonicalPointWithinMapBounds\s*\(\s*"
        r"sv->mapData\.mapBox\.mins\s*,\s*sv->mapData\.mapBox\.maxs\s*,\s*vec\s*\)\s*;",
        wrapper_body,
    )
    require(delegation is not None, "SV_GridIsOnMap does not delegate to the canonical map-bounds helper")
    require(".contains(" not in wrapper_body, "SV_GridIsOnMap still bypasses the direct-test helper")

    for axis in range(3):
        require(f"point[{axis}] >= mins[{axis}]" in helper_body, f"missing inclusive minimum check for axis {axis}")
        require(f"point[{axis}] <= maxs[{axis}]" in helper_body, f"missing inclusive maximum check for axis {axis}")

    for token in FORBIDDEN_PRESENTATION_TOKENS:
        require(token not in helper_body, f"presentation token leaked into canonical helper: {token}")


def run_probe(root: Path) -> None:
    cxx = os.environ.get("CXX", "c++")
    with tempfile.TemporaryDirectory(prefix="ufoai-m1-map-bounds-") as tmp:
        exe = Path(tmp) / "m1-map-bounds"
        compile_cmd = [
            cxx,
            "-std=c++11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            str(root / PROBE_REL),
            "-o",
            str(exe),
        ]
        compile_proc = subprocess.run(
            compile_cmd,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if compile_proc.returncode != 0:
            raise GateError("direct map-bounds probe failed to compile:\n" + (compile_proc.stdout or ""))

        run_proc = subprocess.run(
            [str(exe)],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if run_proc.stdout:
            print(run_proc.stdout, end="" if run_proc.stdout.endswith("\n") else "\n")
        if run_proc.returncode != 0:
            raise GateError(f"direct map-bounds probe failed with exit code {run_proc.returncode}")
        require(PASS_MARKER in (run_proc.stdout or ""), "direct probe passed without the expected PASS marker")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit/run the M1.1b.2a direct canonical isOnMap fixture.")
    parser.add_argument("--audit-only", action="store_true", help="Validate source wiring only; do not compile/run the C++ probe.")
    args = parser.parse_args()

    root = repo_root()
    audit(root)
    if not args.audit_only:
        run_probe(root)

    print("M1.1b.2a canonical map-bounds gate: PASS")
    print("  service: isOnMap")
    print("  canonical wrapper: SV_GridIsOnMap")
    print("  boundary semantics: inclusive min/max")
    if args.audit_only:
        print("  runtime probe: skipped (--audit-only)")
    else:
        print("  runtime probe: PASS (16 cases)")
    print("  presentation dependencies in helper: none")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"M1.1b.2a canonical map-bounds gate: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
