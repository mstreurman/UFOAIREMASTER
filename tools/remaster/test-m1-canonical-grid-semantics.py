#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


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


def main() -> int:
    root = repo_root()
    probe = root / "tools/remaster/m1-canonical-grid-semantics.cpp"
    helper = root / "src/common/grid_semantics.h"
    grid_cpp = root / "src/common/grid.cpp"

    for path in (probe, helper, grid_cpp):
        if not path.is_file():
            raise GateError(f"missing required file: {path.relative_to(root)}")

    grid_text = grid_cpp.read_text(encoding="utf-8")
    required_calls = (
        "Grid_MoveNextSemantic(moveLen, RT_AREA_FROM_POS(path, toPos, crouchingState))",
        "Grid_ShouldUseAutostandSemantic(tusCrouched, tusUpright)",
        "Grid_PosToVecSemantic(actorSize, pos, gridFloor, vec)",
    )
    for token in required_calls:
        if token not in grid_text:
            raise GateError(f"production grid.cpp is not routed through helper: {token}")

    compiler = os.environ.get("CXX") or shutil.which("c++") or shutil.which("g++")
    if not compiler:
        raise GateError("no C++ compiler found (set CXX or install c++)")

    with tempfile.TemporaryDirectory(prefix="ufoai-m1-grid-") as tmp:
        exe = Path(tmp) / "m1-grid-semantics"
        cmd = [
            compiler,
            "-std=c++11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            str(probe),
            "-I",
            str(root),
            "-o",
            str(exe),
        ]
        print("+ " + " ".join(cmd), flush=True)
        proc = subprocess.run(cmd, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        if proc.stdout:
            print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
        if proc.returncode != 0:
            raise GateError(f"grid semantic probe compile failed with exit code {proc.returncode}")

        proc = subprocess.run([str(exe)], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        if proc.stdout:
            print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
        if proc.returncode != 0:
            raise GateError(f"grid semantic probe failed with exit code {proc.returncode}")
        if "M1 canonical grid semantics: PASS" not in (proc.stdout or ""):
            raise GateError("grid semantic probe exited successfully without PASS marker")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"M1 canonical grid semantics: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
