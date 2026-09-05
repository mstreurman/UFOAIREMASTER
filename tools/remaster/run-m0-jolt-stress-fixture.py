#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASELINE = "d9702cc772c136124d98e7cbe384c9c6225b9c2b"
R4_B3 = "a8aa4a83dc5c3e444159bff55b94c76ea18d4c7907043a53cf3101ce7a53c07a"
JOLT_COMMIT = "e77f175595e64cb44218cc9d9d56fc365ad0e36a"
JOLT_TREE_B3 = "ffe175b315e20631eea26419b65ef225b73e37e3788dd93b66407fb3f37a9df2"
JOLT_TAG = "v5.6.0"

R4_TXT = Path("docs/reference/reference-m0-rt-descriptor-heap.txt")
R4_SIDECAR = Path("docs/reference/reference-m0-rt-descriptor-heap.b3")
JOLT_MANIFEST = Path("third_party/JoltPhysics/UFOAI_VENDOR_MANIFEST.txt")
FIXTURE = Path("tools/remaster/jolt_stress_fixture")
CMAKE_FILE = FIXTURE / "CMakeLists.txt"
CPP_FILE = FIXTURE / "jolt_stress.cpp"
RUNNER = Path("tools/remaster/run-m0-jolt-stress-fixture.py")
REFERENCE_MD = Path("docs/reference/reference-m0-jolt-stress.md")
EVIDENCE = Path("docs/reference/reference-m0-jolt-stress.txt")
SIDECAR = Path("docs/reference/reference-m0-jolt-stress.b3")
SAN_EVIDENCE = Path("docs/reference/reference-m0-jolt-stress-sanitizer.txt")
SAN_SIDECAR = Path("docs/reference/reference-m0-jolt-stress-sanitizer.b3")
BUILD = Path("build-m0-jolt-stress-f44")
SAN_BUILD = Path("build-m0-jolt-stress-sanitize-f44")

TICKS = 36000
WORKER_THREADS = 7
DYNAMIC_BODIES = 256
RAGDOLL_CONSTRAINTS = 56
FINITE_CHECKS = TICKS * DYNAMIC_BODIES
FORCED_BATCHES = 60
SANITIZER_FLAGS = "-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer"


class GateError(RuntimeError):
    pass


def run(args: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(args), flush=True)
    proc = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=False)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n", flush=True)
    if check and proc.returncode != 0:
        raise GateError(f"command failed ({proc.returncode}): {' '.join(args)}")
    return proc


def repo_root() -> Path:
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise GateError("not inside a git work tree")
    return Path(proc.stdout.strip()).resolve()


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise GateError(f"required tool missing: {name}")
    return path


def require_sanitizer_runtimes(cxx: str, root: Path) -> dict[str, str]:
    runtimes: dict[str, str] = {}
    for library in ("libasan.so", "libubsan.so"):
        proc = run([cxx, f"-print-file-name={library}"], cwd=root)
        resolved = proc.stdout.strip()
        path = Path(resolved)
        if not resolved or resolved == library or not path.is_absolute() or not path.is_file():
            raise GateError(
                f"sanitizer runtime unavailable: {library}; compiler resolved {resolved!r}"
            )
        runtimes[library] = str(path)
    print(
        "Sanitizer runtimes: PASS "
        f"(ASan={runtimes['libasan.so']} UBSan={runtimes['libubsan.so']})",
        flush=True,
    )
    return runtimes


def require_cmake_cache(build: Path) -> None:
    cache = build / "CMakeCache.txt"
    if not cache.is_file():
        raise GateError(f"missing CMake cache after configure: {cache}")
    values: dict[str, str] = {}
    for line in cache.read_text().splitlines():
        if not line or line.startswith("//") or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    expected = {
        "PROFILER_IN_DEBUG_AND_RELEASE:BOOL": "OFF",
        "PROFILER_IN_DISTRIBUTION:BOOL": "OFF",
        "USE_ASSERTS:BOOL": "ON",
    }
    for key, value in expected.items():
        if values.get(key) != value:
            raise GateError(f"CMake cache mismatch {key}: {values.get(key)!r} != {value!r}")
    print("Jolt qualification CMake policy: PASS (profiler=OFF asserts=ON)", flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def b3_file(path: Path, root: Path) -> str:
    proc = subprocess.run(["b3sum", str(path)], cwd=root, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise GateError(f"b3sum failed for {path}: {proc.stderr.strip()}")
    return proc.stdout.split()[0]


def sidecar_digest(path: Path) -> str:
    parts = path.read_text().strip().split()
    if not parts:
        raise GateError(f"empty sidecar: {path}")
    return parts[0]


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def parse_kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            out[key] = value
    return out


def require_baseline(root: Path) -> None:
    proc = subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"], cwd=root)
    if proc.returncode != 0:
        raise GateError(f"required R4 baseline {BASELINE} is not an ancestor of HEAD")
    proc = subprocess.run(["git", "diff", "--quiet", BASELINE, "--", "src"], cwd=root)
    if proc.returncode != 0:
        raise GateError("src/ differs from the sealed R4 baseline")
    proc = subprocess.run(["git", "diff", "--quiet", BASELINE, "--", "third_party/JoltPhysics"], cwd=root)
    if proc.returncode != 0:
        raise GateError("vendored Jolt differs from the sealed R4 baseline")
    proc = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "--", "third_party/JoltPhysics"],
                          cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise GateError("failed to inspect vendored Jolt untracked state")
    if proc.stdout.strip():
        raise GateError("untracked files exist inside third_party/JoltPhysics")


def verify_r4(root: Path) -> None:
    txt = root / R4_TXT
    side = root / R4_SIDECAR
    if not txt.is_file() or not side.is_file():
        raise GateError("R4 accepted evidence is missing")
    if sidecar_digest(side) != R4_B3 or b3_file(txt, root) != R4_B3:
        raise GateError("R4 evidence identity mismatch")
    print(f"M0.7 R4 evidence verification: PASS ({R4_B3})", flush=True)


def parse_vendor_manifest(root: Path) -> dict[str, str]:
    path = root / JOLT_MANIFEST
    if not path.is_file():
        raise GateError(f"missing Jolt vendor manifest: {JOLT_MANIFEST}")
    values = parse_kv(path.read_text())
    expected = {
        "release_tag": JOLT_TAG,
        "commit_sha": JOLT_COMMIT,
        "sorted_file_manifest_blake3_256": JOLT_TREE_B3,
        "local_patch_list": "none",
    }
    for key, value in expected.items():
        if values.get(key) != value:
            raise GateError(f"Jolt vendor manifest mismatch for {key}: {values.get(key)!r} != {value!r}")
    print(f"Jolt vendor manifest: PASS ({JOLT_TAG} {JOLT_COMMIT})", flush=True)
    return values


def validate_stress_output(kv: dict[str, str]) -> None:
    exact = {
        "jolt.version": "5.6.0",
        "simulation.hz": "60",
        "simulation.ticks": str(TICKS),
        "simulation.seconds": "600.000",
        "simulation.worker_threads": str(WORKER_THREADS),
        "dynamic_bodies": str(DYNAMIC_BODIES),
        "debris_bodies": "192",
        "ragdoll_bodies": "64",
        "ragdoll_constraints": str(RAGDOLL_CONSTRAINTS),
        "finite_checks": str(FINITE_CHECKS),
        "sleep_wake.forced_sleep_batches": str(FORCED_BATCHES),
        "sleep_wake.forced_wake_batches": str(FORCED_BATCHES),
        "canonical.sentinel_before": "0x5aa53cc396690f17",
        "canonical.sentinel_after": "0x5aa53cc396690f17",
        "canonical.authority": "none",
        "result": "PASS",
    }
    for key, value in exact.items():
        if kv.get(key) != value:
            raise GateError(f"stress output mismatch {key}: {kv.get(key)!r} != {value!r}")
    for key in ("sleep_wake.activation_events", "sleep_wake.deactivation_events",
                "contacts.added", "contacts.persisted"):
        try:
            number = int(kv[key])
        except (KeyError, ValueError) as exc:
            raise GateError(f"stress output missing/non-integer {key}") from exc
        if number <= 0:
            raise GateError(f"stress output {key} must be > 0, got {number}")
    if int(kv["sleep_wake.activation_events"]) <= DYNAMIC_BODIES:
        raise GateError("activation listener did not observe wake transitions after initial activation")


def common_evidence_lines(root: Path, tool_versions: dict[str, str], vendor: dict[str, str]) -> list[str]:
    return [
        f"baseline.r4_revision={BASELINE}",
        f"baseline.r4_evidence_blake3_256={R4_B3}",
        f"jolt.release_tag={vendor['release_tag']}",
        f"jolt.commit_sha={vendor['commit_sha']}",
        f"jolt.sorted_file_manifest_blake3_256={vendor['sorted_file_manifest_blake3_256']}",
        f"jolt.local_patch_list={vendor['local_patch_list']}",
        f"tool.cmake={tool_versions['cmake']}",
        f"tool.ninja={tool_versions['ninja']}",
        f"tool.cxx={tool_versions['cxx']}",
        f"input.fixture_cmake.sha256={sha256(root / CMAKE_FILE)}",
        f"input.fixture_cpp.sha256={sha256(root / CPP_FILE)}",
        f"input.runner.sha256={sha256(root / RUNNER)}",
        f"input.reference_doc.sha256={sha256(root / REFERENCE_MD)}",
        f"input.vendor_manifest.sha256={sha256(root / JOLT_MANIFEST)}",
        "build.linkage=static",
        "build.asserts=enabled",
        "build.profiler_debug_release=off",
        "build.profiler_distribution=off",
        "build.double_precision=off",
        "build.cross_platform_deterministic=off",
        "build.exceptions=off",
        "build.rtti=off",
        "build.avx2=on",
        "build.fmadd=on",
        "build.jolt_graphics_compute=off",
        "stress.simulation_hz=60",
        f"stress.ticks={TICKS}",
        "stress.simulation_seconds=600.000",
        f"stress.worker_threads={WORKER_THREADS}",
        f"stress.dynamic_bodies={DYNAMIC_BODIES}",
        "stress.debris_bodies=192",
        "stress.ragdoll_bodies=64",
        f"stress.ragdoll_constraints={RAGDOLL_CONSTRAINTS}",
        "stress.contact_heavy=PASS",
        "stress.repeated_sleep_wake=PASS",
        f"stress.finite_state_checks={FINITE_CHECKS}",
        "stress.finite_position_every_tick=PASS",
        "stress.finite_orientation_every_tick=PASS",
        "stress.finite_linear_velocity_every_tick=PASS",
        "stress.finite_angular_velocity_every_tick=PASS",
        "stress.physics_update_errors=none",
        "stress.body_ownership=PASS",
        "canonical.authority=none",
        "canonical.sentinel_unchanged=PASS",
        "source.src_delta_from_r4=none",
        "production.behavior_replacement=none",
    ]


def sanitizer_evidence_bytes(root: Path, tool_versions: dict[str, str], vendor: dict[str, str]) -> bytes:
    lines = [
        "ufoai-remaster-m0-jolt-stress-sanitizer-v2",
        "schema.version=2",
        *common_evidence_lines(root, tool_versions, vendor),
        "sanitizer.compiler_family=gcc-or-clang",
        "sanitizer.address=PASS",
        "sanitizer.undefined=PASS",
        "sanitizer.recover=disabled",
        f"sanitizer.flags={SANITIZER_FLAGS}",
        "result=PASS",
    ]
    return ("\n".join(lines) + "\n").encode()


def verify_sanitizer_evidence(root: Path, tool_versions: dict[str, str], vendor: dict[str, str]) -> str:
    evidence = root / SAN_EVIDENCE
    sidecar = root / SAN_SIDECAR
    if not evidence.is_file() or not sidecar.is_file():
        raise GateError("R5 sanitizer evidence is missing; run --sanitize-capture and --sanitize-verify first")
    expected = sanitizer_evidence_bytes(root, tool_versions, vendor)
    if evidence.read_bytes() != expected:
        raise GateError("R5 sanitizer evidence does not match the current fixture/toolchain contract")
    digest = b3_file(evidence, root)
    if sidecar_digest(sidecar) != digest:
        raise GateError("R5 sanitizer sidecar digest does not match sanitizer evidence")
    return digest


def evidence_bytes(root: Path, tool_versions: dict[str, str], vendor: dict[str, str], sanitizer_digest: str) -> bytes:
    lines = [
        "ufoai-remaster-m0-jolt-stress-v3",
        "schema.version=3",
        *common_evidence_lines(root, tool_versions, vendor),
        "sanitizer.status=PASS",
        "sanitizer.address=PASS",
        "sanitizer.undefined=PASS",
        "sanitizer.recover=disabled",
        f"sanitizer.evidence_blake3_256={sanitizer_digest}",
        "result=PASS",
    ]
    return ("\n".join(lines) + "\n").encode()


def clean_build(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def configure_and_run(root: Path, cmake: str, build: Path, *, sanitizers: bool) -> dict[str, str]:
    clean_build(build)
    label = "SANITIZED" if sanitizers else "RELEASE"
    print(f"\n=== CLEAN R5 {label} CONFIGURE ===", flush=True)
    run([
        cmake,
        "-S", str(root / FIXTURE),
        "-B", str(build),
        "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DUFOAI_JOLT_ROOT={root / 'third_party/JoltPhysics'}",
        f"-DUFOAI_JOLT_SANITIZERS={'ON' if sanitizers else 'OFF'}",
    ], cwd=root)
    require_cmake_cache(build)

    print(f"\n=== CLEAN R5 {label} BUILD ===", flush=True)
    run([cmake, "--build", str(build), "--target", "m0_jolt_stress", "--parallel", "8"], cwd=root)

    heading = "ASAN+UBSAN " if sanitizers else ""
    print(f"\n=== JOLT V5.6.0 {heading}600-SECOND PRESENTATION-PHYSICS STRESS ===", flush=True)
    proc = run([
        str(build / "m0_jolt_stress"),
        "--ticks", str(TICKS),
        "--worker-threads", str(WORKER_THREADS),
    ], cwd=root)
    kv = parse_kv(proc.stdout)
    validate_stress_output(kv)
    if sanitizers:
        print("M0.7 R5 ASAN+UBSAN full-stress semantic gate: PASS", flush=True)
    else:
        print("M0.7 R5 finite-transform stress semantic gate: PASS", flush=True)
    return kv


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--sanitize-capture", action="store_true")
    mode.add_argument("--sanitize-verify", action="store_true")
    args = parser.parse_args()

    root = repo_root()
    try:
        require_baseline(root)
        require_tool("b3sum")
        verify_r4(root)
        vendor = parse_vendor_manifest(root)

        cmake = require_tool("cmake")
        ninja = require_tool("ninja")
        cxx = require_tool("c++")
        versions = {
            "cmake": first_line(run([cmake, "--version"], cwd=root).stdout),
            "ninja": first_line(run([ninja, "--version"], cwd=root).stdout),
            "cxx": first_line(run([cxx, "--version"], cwd=root).stdout),
        }

        if args.sanitize_capture or args.sanitize_verify:
            require_sanitizer_runtimes(cxx, root)
            build = root / SAN_BUILD
            configure_and_run(root, cmake, build, sanitizers=True)
            data = sanitizer_evidence_bytes(root, versions, vendor)
            evidence = root / SAN_EVIDENCE
            sidecar = root / SAN_SIDECAR
            if args.sanitize_capture:
                evidence.write_bytes(data)
                digest = b3_file(evidence, root)
                sidecar.write_text(f"{digest}  {SAN_EVIDENCE.name}\n")
                print(f"M0.7 R5 sanitizer capture: PASS ({digest})", flush=True)
            else:
                if not evidence.is_file() or not sidecar.is_file():
                    raise GateError("accepted R5 sanitizer evidence is missing; run --sanitize-capture first")
                if evidence.read_bytes() != data:
                    raise GateError("R5 regenerated sanitizer evidence differs from captured evidence")
                digest = b3_file(evidence, root)
                if sidecar_digest(sidecar) != digest:
                    raise GateError("R5 sanitizer sidecar digest does not match evidence")
                print(f"M0.7 R5 sanitizer verification: PASS ({digest})", flush=True)
            return 0

        sanitizer_digest = verify_sanitizer_evidence(root, versions, vendor)
        print(f"M0.7 R5 sanitizer evidence verification: PASS ({sanitizer_digest})", flush=True)
        build = root / BUILD
        configure_and_run(root, cmake, build, sanitizers=False)
        data = evidence_bytes(root, versions, vendor, sanitizer_digest)
        evidence = root / EVIDENCE
        sidecar = root / SIDECAR

        if args.capture:
            evidence.write_bytes(data)
            digest = b3_file(evidence, root)
            sidecar.write_text(f"{digest}  {EVIDENCE.name}\n")
            print(f"M0.7 R5 Jolt stress capture: PASS ({digest})", flush=True)
        else:
            if not evidence.is_file() or not sidecar.is_file():
                raise GateError("accepted R5 evidence is missing; run --capture first")
            if evidence.read_bytes() != data:
                raise GateError("R5 regenerated evidence differs from captured evidence")
            digest = b3_file(evidence, root)
            if sidecar_digest(sidecar) != digest:
                raise GateError("R5 sidecar digest does not match evidence")
            print(f"M0.7 R5 Jolt stress verification: PASS ({digest})", flush=True)
        return 0
    except GateError as exc:
        print(f"M0.7 R5 Jolt stress gate: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
