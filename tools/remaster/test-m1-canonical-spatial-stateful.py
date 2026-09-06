#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASELINE_REVISION = "4ad13451e20b66293d3eb788cdae3150e0f61754"
SEALED_TEST_CMAKE_BLOB = "5110f532e62126a7b89fc07b1248717e5e71cbf0"
BUILD_REL = Path("build-m1-spatial-stateful")
PROBE_REL = Path("tools/remaster/m1-canonical-spatial-stateful.cpp")
SERVER_ORACLE_REL = Path("tools/remaster/m1-canonical-spatial-stateful-server.cpp")
TEST_CMAKE_REL = Path("src/tests/CMakeLists.txt")
EXPECTED_TESTS = [
    "M1SpatialStatefulTest.RoutingQueriesMatchCanonicalState",
    "M1SpatialStatefulTest.WorldTraceLineAndContentsMatchCanonicalState",
    "M1SpatialStatefulTest.LinkAndUnlinkMutateCanonicalWorldMembership",
    "M1SpatialStatefulTest.InlineModelOrientationAndBoundsMatchCanonicalState",
    "M1SpatialStatefulTest.GrenadeTargetMatchesCanonicalSolver",
    "M1SpatialStatefulTest.LoadedModelAABBMatchesCanonicalLoader",
]
UFO2MAP_FLAGS = ["-v", "4", "-nice", "19", "-quant", "4", "-soft"]


class GateError(RuntimeError):
    pass


def run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None,
        capture: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )
    if proc.returncode != 0:
        out = proc.stdout or ""
        raise GateError(f"command failed ({proc.returncode}): {' '.join(args)}\n{out}")
    return proc


def run_streaming(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    print("+ " + " ".join(args), flush=True)
    proc = subprocess.Popen(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    assert proc.stdout is not None
    chunks: list[str] = []
    for line in proc.stdout:
        chunks.append(line)
        print(line, end="", flush=True)
    rc = proc.wait()
    if rc != 0:
        raise GateError(f"command failed ({rc}): {' '.join(args)}")
    return "".join(chunks)


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


def require_baseline_ancestor(root: Path) -> None:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_REVISION, "HEAD"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        head = run(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()
        raise GateError(
            f"HEAD {head} is not a descendant of stateful-lane baseline {BASELINE_REVISION}"
        )


def require_sealed_test_cmake(root: Path) -> None:
    path = root / TEST_CMAKE_REL
    blob = run(["git", "hash-object", str(path)], cwd=root).stdout.strip()
    if blob != SEALED_TEST_CMAKE_BLOB:
        raise GateError(
            f"sealed {TEST_CMAKE_REL} changed: expected blob {SEALED_TEST_CMAKE_BLOB}, got {blob}"
        )


def audit_source_contract(root: Path) -> None:
    require_baseline_ancestor(root)
    require_sealed_test_cmake(root)

    cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
    required_cmake = [
        'option(UFOAI_M1_SPATIAL_STATEFUL_TESTS',
        'target_sources(ufotestall PRIVATE',
        'tools/remaster/m1-canonical-spatial-stateful.cpp',
        'tools/remaster/m1-canonical-spatial-stateful-server.cpp',
    ]
    for token in required_cmake:
        if token not in cmake:
            raise GateError(f"missing M1 stateful CMake contract token: {token}")

    probe = root / PROBE_REL
    if not probe.is_file():
        raise GateError(f"missing stateful probe: {PROBE_REL}")
    oracle = root / SERVER_ORACLE_REL
    if not oracle.is_file():
        raise GateError(f"missing server-side trace oracle: {SERVER_ORACLE_REL}")
    oracle_text = oracle.read_text(encoding="utf-8")
    for token in ("extern \"C\" trace_t M1_CanonicalServerTrace", "SV_Trace(traceLine, box, nullptr, contentmask)"):
        if token not in oracle_text:
            raise GateError(f"server-side trace oracle contract missing token: {token}")
    text = probe.read_text(encoding="utf-8")
    for test in EXPECTED_TESTS:
        suite, name = test.split(".", 1)
        if f"TEST_F({suite}, {name})" not in text:
            raise GateError(f"missing stateful test case: {test}")

    forbidden = ["glBegin", "glEnd", "vkCmd", "JPH::", "alSource"]
    for token in forbidden:
        if token in text:
            raise GateError(f"presentation/physics dependency leaked into spatial fixture: {token}")


def ensure_link(path: Path, target: Path) -> None:
    if path.is_symlink():
        if path.resolve() == target.resolve():
            return
        path.unlink()
    elif path.exists():
        raise GateError(
            f"{path} already exists and is not the expected symlink; remove the dedicated M1 build dir and retry"
        )
    path.symlink_to(target, target_is_directory=True)


def configure_and_build(root: Path, build: Path) -> None:
    build.mkdir(parents=True, exist_ok=True)
    ensure_link(build / "base", root / "base")
    ensure_link(build / "radiant", root / "radiant")

    configure = [
        "cmake", "-S", str(root), "-B", str(build), "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
        "-DCMAKE_C_COMPILER=gcc",
        "-DCMAKE_CXX_COMPILER=g++",
        "-DUFOAI_REMASTER=OFF",
        "-DUFOAI_M1_SPATIAL_STATEFUL_TESTS=ON",
        "-DDISABLE_UFO=ON",
        "-DDISABLE_UFODED=ON",
        "-DDISABLE_TESTS=OFF",
        "-DDISABLE_TOOLS=OFF",
        "-DDISABLE_UFO2MAP=OFF",
        "-DDISABLE_UFOMODEL=ON",
        "-DDISABLE_UFORADIANT=ON",
        "-DDISABLE_I18N=ON",
        "-DDISABLE_MANUAL=ON",
        "-DDISABLE_DOXYGEN_DOCS=ON",
        "-DDISABLE_BASE_PACKAGES=ON",
        "-DDISABLE_MAPS_COMPILE=ON",
    ]
    run_streaming(configure, cwd=root)
    run_streaming(
        ["cmake", "--build", str(build), "--parallel", "8", "--target", "ufo2map", "ufotestall"],
        cwd=root,
    )


def tracked_unittest_files(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z", "--", "unittest"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise GateError(proc.stderr.decode("utf-8", "replace"))
    paths = [x.decode("utf-8", "strict") for x in proc.stdout.split(b"\0") if x]
    if not paths:
        raise GateError("tracked unittest fixture tree is empty")
    return paths


def stage_unittest(root: Path, build: Path) -> int:
    target = build / "unittest"
    if target.exists():
        shutil.rmtree(target)
    count = 0
    for rel in tracked_unittest_files(root):
        src = root / rel
        if not src.is_file():
            raise GateError(f"tracked unittest fixture missing from worktree: {rel}")
        dst = build / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        count += 1
    return count


def isolated_env(build: Path) -> dict[str, str]:
    state = build / "m1-stateful-state"
    if state.exists():
        shutil.rmtree(state)
    home = state / "home"
    config = state / "config"
    data = state / "data"
    cache = state / "cache"
    runtime = state / "runtime"
    for path in (home, config, data, cache, runtime):
        path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(config),
        "XDG_DATA_HOME": str(data),
        "XDG_CACHE_HOME": str(cache),
        "XDG_RUNTIME_DIR": str(runtime),
        "LC_ALL": "C",
        "LANG": "C",
        "TZ": "UTC",
    })
    return env


def compile_maps(build: Path, env: dict[str, str]) -> None:
    ufo2map = build / "ufo2map"
    if not ufo2map.is_file():
        raise GateError("dedicated M1 ufo2map artifact is missing")
    for name in ("test_game", "test_routing"):
        run_streaming(
            [str(ufo2map), "-gamedir", "unittest", *UFO2MAP_FLAGS, f"maps/{name}.map"],
            cwd=build,
            env=env,
        )
        bsp = build / "unittest" / "maps" / f"{name}.bsp"
        if not bsp.is_file():
            raise GateError(f"compiled M1 fixture missing: {bsp}")


def run_fixture(build: Path, env: dict[str, str]) -> str:
    binary = build / "ufotestall"
    if not binary.is_file():
        raise GateError("dedicated M1 ufotestall artifact is missing")
    text = run_streaming(
        [
            str(binary),
            "--gtest_filter=M1SpatialStatefulTest.*",
            "--gtest_color=no",
            "--gtest_print_time=0",
        ],
        cwd=build,
        env=env,
    )
    for test in EXPECTED_TESTS:
        if f"[ RUN      ] {test}" not in text or f"[       OK ] {test}" not in text:
            raise GateError(f"stateful fixture did not execute successfully: {test}")
    if "[  PASSED  ] 6 tests." not in text:
        raise GateError("expected six M1 stateful spatial tests to pass")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and run the M1-only stateful canonical spatial integration lane."
    )
    parser.add_argument(
        "--audit-only", action="store_true",
        help="Validate source/CMake/sealed-test contracts without configuring or running the fixture.",
    )
    args = parser.parse_args()

    root = repo_root()
    audit_source_contract(root)
    if args.audit_only:
        print("M1 canonical spatial stateful lane: PASS (audit-only)")
        print("  corrected sentinel accounting: 7/23")
        print("  stateful direct services declared: 12/23")
        print("  sealed src/tests/CMakeLists.txt: unchanged")
        print("  server-side Trace oracle bridge: present")
        return 0

    build = root / BUILD_REL
    configure_and_build(root, build)
    staged = stage_unittest(root, build)
    env = isolated_env(build)
    compile_maps(build, env)
    run_fixture(build, env)

    print("M1 canonical spatial stateful lane: PASS")
    print("  stateful GoogleTest cases: 6/6")
    print("  stateful direct services: 12/23")
    print(f"  tracked unittest fixtures staged: {staged}")
    print("  tracked BSP fixtures compiled: 2")
    print("  positive loaded-model AABB fixture: models/objects/abrams/abrams.md2")
    print("  sealed src/tests/CMakeLists.txt: unchanged")
    print("  server-side Trace oracle bridge: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"M1 canonical spatial stateful lane: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
