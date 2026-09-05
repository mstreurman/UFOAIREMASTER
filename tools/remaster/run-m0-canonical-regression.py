#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

CANONICAL_REVISION = "763173ed036ebbee32c2a7bf6aefa19748df89ff"
M0_4_REVISION = "20e035758fa12ac8c7ee2fe71632eb3ed733dcc3"
M0_3_MANIFEST_B3 = "4b319f96f5674b3d39108fdd327b2e04143b1f4eaeaa88469eac364071f756b5"
M0_4_EVIDENCE_B3 = "0bcf17b95ab6cccffab75f059c9ff919fe098e424fb02a8f579af7b1b0617d8e"

SCOPE_REL = Path("tools/remaster/m0-canonical-reference-scope.json")
EVIDENCE_REL = Path("docs/reference/reference-m0-canonical-regression.txt")
SIDECAR_REL = Path("docs/reference/reference-m0-canonical-regression.b3")
M0_4_EVIDENCE_REL = Path("docs/reference/reference-m0-legacy-build-launch-smoke.txt")
M0_4_SIDECAR_REL = Path("docs/reference/reference-m0-legacy-build-launch-smoke.b3")
M0_3_CAPTURE_REL = Path("tools/remaster/capture-m0-manifest.py")
CMAKE_PRESETS_REL = Path("CMakePresets.json")
TEST_CMAKE_REL = Path("src/tests/CMakeLists.txt")
TEST_MAIN_REL = Path("src/tests/test_all.cpp")
LEGACY_TESTALL_MAKE_REL = Path("build/modules/testall.mk")
UFO2MAP_CMAKE_REL = Path("src/tools/ufo2map/CMakeLists.txt")
BUILD_REL = Path("build-m0-legacy-f44")
UFO2MAP_FLAGS = ["-v", "4", "-nice", "19", "-quant", "4", "-soft"]

class GateError(RuntimeError):
    pass


def run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None,
        check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )
    if check and proc.returncode != 0:
        out = proc.stdout or ""
        raise GateError(f"command failed ({proc.returncode}): {' '.join(args)}\n{out}")
    return proc


def run_logged(args: list[str], *, cwd: Path, log_path: Path,
               env: dict[str, str] | None = None) -> str:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    print("+ " + " ".join(args), flush=True)
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
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
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        rc = proc.wait()
    text = "".join(chunks)
    if rc != 0:
        raise GateError(f"command failed ({rc}): {' '.join(args)}; see {log_path}")
    return text


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise GateError("not inside a Git work tree")
    return Path(proc.stdout.strip()).resolve()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def b3_file(root: Path, path: Path) -> str:
    proc = run(["b3sum", str(path)], cwd=root)
    token = (proc.stdout or "").split()
    if not token:
        raise GateError(f"b3sum produced no digest for {path}")
    return token[0]


def b3_bytes(root: Path, data: bytes) -> str:
    proc = subprocess.run(
        ["b3sum"], cwd=root, input=data,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise GateError(f"b3sum failed: {proc.stderr.decode(errors='replace')}")
    return proc.stdout.decode().strip().split()[0]


def sidecar_digest(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    parts = text.split()
    if not parts:
        raise GateError(f"empty sidecar: {path}")
    return parts[0]


def require_ancestor(root: Path) -> None:
    proc = run(["git", "merge-base", "--is-ancestor", M0_4_REVISION, "HEAD"], cwd=root, check=False)
    if proc.returncode != 0:
        head = run(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()
        raise GateError(f"HEAD {head} is not a descendant of published M0.4 {M0_4_REVISION}")


def verify_m0_3(root: Path) -> None:
    path = root / M0_3_CAPTURE_REL
    if not path.is_file():
        raise GateError(f"missing M0.3 verifier: {M0_3_CAPTURE_REL}")
    proc = run([sys.executable, str(path), "--verify"], cwd=root, check=False)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.returncode != 0:
        raise GateError("M0.3 reference environment verification failed")
    if M0_3_MANIFEST_B3 not in (proc.stdout or ""):
        raise GateError("M0.3 verifier passed with an unexpected manifest identity")


def verify_m0_4(root: Path) -> None:
    evidence = root / M0_4_EVIDENCE_REL
    sidecar = root / M0_4_SIDECAR_REL
    if not evidence.is_file() or not sidecar.is_file():
        raise GateError("committed M0.4 evidence or sidecar is missing")
    actual = b3_file(root, evidence)
    declared = sidecar_digest(sidecar)
    if actual != M0_4_EVIDENCE_B3 or declared != M0_4_EVIDENCE_B3:
        raise GateError(
            f"M0.4 evidence identity mismatch: expected {M0_4_EVIDENCE_B3}, "
            f"actual={actual}, sidecar={declared}"
        )


def rpm_nevra(root: Path, package: str) -> str:
    fmt = "%{NAME}|%{EPOCH}|%{VERSION}|%{RELEASE}|%{ARCH}\\n"
    proc = run(["rpm", "-q", "--qf", fmt, package], cwd=root, check=False)
    if proc.returncode != 0:
        raise GateError(
            f"required M0.5 test-only package '{package}' is not installed. "
            f"Install it with: sudo dnf install {package}"
        )
    line = (proc.stdout or "").strip().splitlines()[0]
    fields = line.split("|")
    if len(fields) != 5:
        raise GateError(f"unexpected rpm query output for {package}: {line!r}")
    name, epoch, version, release, arch = fields
    if epoch in {"(none)", "", "None"}:
        epoch = "0"
    return f"{name}-{epoch}:{version}-{release}.{arch}"


def load_scope(root: Path) -> dict:
    path = root / SCOPE_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise GateError(f"cannot parse {SCOPE_REL}: {e}") from e
    if data.get("schema") != 1:
        raise GateError("unsupported M0.5 scope schema")
    selected = data.get("selected_test_sources")
    if not isinstance(selected, list) or not selected or not all(isinstance(x, str) for x in selected):
        raise GateError("selected_test_sources must be a non-empty string list")
    if len(selected) != len(set(selected)):
        raise GateError("selected_test_sources contains duplicates")
    support = data.get("support_test_sources", [])
    if not isinstance(support, list) or not all(isinstance(x, str) for x in support):
        raise GateError("support_test_sources must be a string list")
    if len(support) != len(set(support)):
        raise GateError("support_test_sources contains duplicates")
    overlap = sorted(set(selected) & set(support))
    if overlap:
        raise GateError(f"test/support source scope overlaps: {overlap}")
    fixture_roots = data.get("fixture_roots", [])
    if not isinstance(fixture_roots, list) or not fixture_roots or not all(isinstance(x, str) for x in fixture_roots):
        raise GateError("fixture_roots must be a non-empty string list")
    if len(fixture_roots) != len(set(fixture_roots)):
        raise GateError("fixture_roots contains duplicates")
    runtime_data_roots = data.get("runtime_data_roots", [])
    if not isinstance(runtime_data_roots, list) or not runtime_data_roots or not all(isinstance(x, str) for x in runtime_data_roots):
        raise GateError("runtime_data_roots must be a non-empty string list")
    if len(runtime_data_roots) != len(set(runtime_data_roots)):
        raise GateError("runtime_data_roots contains duplicates")
    if set(runtime_data_roots) & set(fixture_roots):
        raise GateError("runtime_data_roots must not overlap fixture_roots")
    deferred = data.get("deferred_asset_sweep_tests", [])
    if not isinstance(deferred, list) or not all(isinstance(x, dict) for x in deferred):
        raise GateError("deferred_asset_sweep_tests must be a list of objects")
    deferred_names: list[str] = []
    for entry in deferred:
        name = entry.get("name")
        reason = entry.get("reason")
        if not isinstance(name, str) or not name or not isinstance(reason, str) or not reason:
            raise GateError("each deferred asset sweep requires non-empty name and reason")
        deferred_names.append(name)
    if len(deferred_names) != len(set(deferred_names)):
        raise GateError("deferred_asset_sweep_tests contains duplicate names")
    compile_time_excluded = data.get("compile_time_excluded_tests", [])
    if not isinstance(compile_time_excluded, list) or not all(isinstance(x, dict) for x in compile_time_excluded):
        raise GateError("compile_time_excluded_tests must be a list of objects")
    compile_time_names: list[str] = []
    for entry in compile_time_excluded:
        name = entry.get("name")
        reason = entry.get("reason")
        if not isinstance(name, str) or not name or not isinstance(reason, str) or not reason:
            raise GateError("each compile-time excluded test requires non-empty name and reason")
        compile_time_names.append(name)
    if len(compile_time_names) != len(set(compile_time_names)):
        raise GateError("compile_time_excluded_tests contains duplicate names")
    unit_maps = data.get("unit_test_map_sources", [])
    if not isinstance(unit_maps, list) or not unit_maps or not all(isinstance(x, str) for x in unit_maps):
        raise GateError("unit_test_map_sources must be a non-empty string list")
    if len(unit_maps) != len(set(unit_maps)):
        raise GateError("unit_test_map_sources contains duplicates")
    for rel in unit_maps:
        if not rel.startswith("unittest/maps/") or not rel.endswith(".map"):
            raise GateError(f"invalid unit test map source path: {rel}")
    return data


def strip_cpp_comments(text: str) -> str:
    # Good enough for TEST/TEST_F macro discovery; strings/chars are preserved so
    # a literal containing TEST(...) would still be caught by the availability gate.
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return text


def source_tests(path: Path) -> list[str]:
    text = strip_cpp_comments(path.read_text(encoding="utf-8", errors="strict"))
    unsupported = re.findall(r"\b(?:TEST_P|TYPED_TEST|TYPED_TEST_P)\s*\(", text)
    if unsupported:
        raise GateError(f"unsupported parameterized/typed GoogleTest macro in canonical scope: {path}")
    rx = re.compile(
        r"\b(?:TEST|TEST_F)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*\)"
    )
    tests = [f"{m.group(1)}.{m.group(2)}" for m in rx.finditer(text)]
    if not tests:
        raise GateError(f"no TEST/TEST_F cases discovered in selected source: {path}")
    if len(tests) != len(set(tests)):
        raise GateError(f"duplicate test identity discovered in selected source: {path}")
    return tests


def parse_gtest_list(text: str) -> list[str]:
    result: list[str] = []
    suite: str | None = None
    for raw in text.splitlines():
        if not raw.strip():
            continue
        if raw[:1].isspace():
            if suite is None:
                continue
            name = raw.strip().split("#", 1)[0].strip()
            if name:
                result.append(f"{suite}.{name}")
        else:
            label = raw.strip().split("#", 1)[0].strip()
            if label.endswith("."):
                suite = label[:-1]
    return result


def parse_run_trace(text: str) -> list[str]:
    out: list[str] = []
    rx = re.compile(r"^\[\s*RUN\s*\]\s+(.+?)\s*$")
    for line in text.splitlines():
        m = rx.match(line.strip())
        if m:
            out.append(m.group(1))
    return out


def read_cache_value(cache: Path, key: str) -> str | None:
    prefix = key + ":"
    for line in cache.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix) and "=" in line:
            return line.split("=", 1)[1]
    return None


def make_isolated_env(build: Path, label: str) -> dict[str, str]:
    state = build / "m0-canonical-state" / label
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


def tracked_files(root: Path, relroot: str) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z", "--", relroot],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise GateError(
            f"cannot enumerate tracked fixture root {relroot!r}: "
            + proc.stderr.decode("utf-8", "replace").strip()
        )
    paths = [raw.decode("utf-8", "strict") for raw in proc.stdout.split(b"\0") if raw]
    if not paths:
        raise GateError(f"fixture root has no tracked files: {relroot}")
    return paths


def stage_tracked_fixtures(root: Path, build: Path, fixture_roots: list[str]) -> int:
    copied = 0
    for relroot in fixture_roots:
        destination = build / relroot
        if destination.exists():
            shutil.rmtree(destination)
        for rel in tracked_files(root, relroot):
            src = root / rel
            if not src.is_file():
                raise GateError(f"tracked fixture file is missing from worktree: {rel}")
            dst = build / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
    return copied


def compile_unit_test_maps(build: Path, map_sources: list[str], log_path: Path,
                           env: dict[str, str]) -> list[str]:
    ufo2map = build / "ufo2map"
    if not ufo2map.is_file() or not os.access(ufo2map, os.X_OK):
        raise GateError("ufo2map build artifact missing or non-executable")
    generated: list[str] = []
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
        for rel in map_sources:
            source = Path(rel)
            try:
                map_arg = source.relative_to("unittest")
            except ValueError as exc:
                raise GateError(f"unit test map is outside unittest/: {rel}") from exc
            args = [str(ufo2map), "-gamedir", "unittest", *UFO2MAP_FLAGS, str(map_arg)]
            print("+ " + " ".join(args), flush=True)
            proc = subprocess.Popen(
                args,
                cwd=build,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
            rc = proc.wait()
            if rc != 0:
                raise GateError(f"unit-test map compile failed ({rc}): {rel}; see {log_path}")
            bsp = (build / source).with_suffix(".bsp")
            if not bsp.is_file():
                raise GateError(f"compiled unit-test BSP missing: {bsp.relative_to(build)}")
            generated.append(str(bsp.relative_to(build)))
    return generated


def tracked_fixture_fingerprint(root: Path, relroot: str) -> tuple[int, str]:
    paths = tracked_files(root, relroot)
    lines: list[str] = []
    for rel in paths:
        path = root / rel
        if not path.is_file():
            raise GateError(f"tracked fixture file is missing from worktree: {rel}")
        lines.append(f"{rel}\t{sha256_file(path)}")
    blob = ("\n".join(lines) + "\n").encode("utf-8")
    return len(paths), b3_bytes(root, blob)


def evidence_bytes(root: Path, *, gtest_nevra: str, gtest_pkg_version: str,
                   test_sources: list[str], support_sources: list[str],
                   fixture_roots: list[str], runtime_data_roots: list[str], selected_tests: list[str],
                   discovered_enabled_tests: list[str], deferred_asset_tests: list[dict[str, str]],
                   compile_time_excluded_tests: list[dict[str, str]],
                   unit_test_map_sources: list[str], generated_fixture_bsps: list[str],
                   disabled_tests: list[str], trace: list[str]) -> bytes:
    script_rel = Path(__file__).resolve().relative_to(root)
    input_paths = [
        ("harness_script", script_rel),
        ("scope", SCOPE_REL),
        ("cmake_presets", CMAKE_PRESETS_REL),
        ("tests_cmake", TEST_CMAKE_REL),
        ("test_main", TEST_MAIN_REL),
        ("legacy_testall_make", LEGACY_TESTALL_MAKE_REL),
        ("ufo2map_cmake", UFO2MAP_CMAKE_REL),
    ]
    test_source_hashes = [(p, sha256_file(root / p)) for p in test_sources]
    support_source_hashes = [(p, sha256_file(root / p)) for p in support_sources]
    fixture_fingerprints = [(p, *tracked_fixture_fingerprint(root, p)) for p in fixture_roots]
    runtime_data_fingerprints = [(p, *tracked_fixture_fingerprint(root, p)) for p in runtime_data_roots]
    generated_fixture_bsp_hashes = [
        (name, sha256_file(root / BUILD_REL / name)) for name in generated_fixture_bsps
    ]

    corpus_lines = [
        "ufoai-remaster-m0-canonical-corpus-v1",
        "schema.version=1",
        f"source.canonical_revision={CANONICAL_REVISION}",
        f"baseline.m0_4_revision={M0_4_REVISION}",
    ]
    for idx, (path, digest) in enumerate(test_source_hashes):
        corpus_lines.append(f"test_source.{idx:02d}.path={path}")
        corpus_lines.append(f"test_source.{idx:02d}.sha256={digest}")
    for idx, (path, digest) in enumerate(support_source_hashes):
        corpus_lines.append(f"support_source.{idx:02d}.path={path}")
        corpus_lines.append(f"support_source.{idx:02d}.sha256={digest}")
    for idx, (path, file_count, digest) in enumerate(fixture_fingerprints):
        corpus_lines.append(f"fixture_root.{idx:02d}.path={path}")
        corpus_lines.append(f"fixture_root.{idx:02d}.tracked_file_count={file_count}")
        corpus_lines.append(f"fixture_root.{idx:02d}.blake3_256={digest}")
    for idx, (path, file_count, digest) in enumerate(runtime_data_fingerprints):
        corpus_lines.append(f"runtime_data_root.{idx:02d}.path={path}")
        corpus_lines.append(f"runtime_data_root.{idx:02d}.tracked_file_count={file_count}")
        corpus_lines.append(f"runtime_data_root.{idx:02d}.blake3_256={digest}")
    for idx, test in enumerate(selected_tests):
        corpus_lines.append(f"core_test.{idx:03d}={test}")
    for idx, entry in enumerate(deferred_asset_tests):
        corpus_lines.append(f"deferred_asset_test.{idx:02d}.name={entry['name']}")
        corpus_lines.append(f"deferred_asset_test.{idx:02d}.reason={entry['reason']}")
    for idx, entry in enumerate(compile_time_excluded_tests):
        corpus_lines.append(f"compile_time_excluded_test.{idx:02d}.name={entry['name']}")
        corpus_lines.append(f"compile_time_excluded_test.{idx:02d}.reason={entry['reason']}")
    for idx, rel in enumerate(unit_test_map_sources):
        corpus_lines.append(f"unit_test_map_source.{idx:02d}={rel}")
    corpus_blob = ("\n".join(corpus_lines) + "\n").encode("utf-8")
    corpus_b3 = b3_bytes(root, corpus_blob)

    trace_blob = ("\n".join(trace) + "\n").encode("utf-8")
    trace_b3 = b3_bytes(root, trace_blob)

    lines = [
        "ufoai-remaster-m0-canonical-regression-v1",
        "schema.version=1",
        f"source.canonical_revision={CANONICAL_REVISION}",
        f"baseline.m0_4_revision={M0_4_REVISION}",
        f"environment.m0_manifest_blake3_256={M0_3_MANIFEST_B3}",
        f"baseline.m0_4_evidence_blake3_256={M0_4_EVIDENCE_B3}",
    ]
    for label, path in input_paths:
        lines.append(f"input.{label}.sha256={sha256_file(root / path)}")
    lines.extend([
        f"test_dependency.gtest_devel_nevra={gtest_nevra}",
        f"test_dependency.gtest_pkg_config_version={gtest_pkg_version}",
        "build.configure_preset=legacy-m0-f44",
        "build.type=RelWithDebInfo",
        "build.ufoai_remaster=OFF",
        "build.clean_binary_dir=true",
        "build.test_tool_override.DISABLE_TOOLS=OFF",
        "build.test_tool_override.DISABLE_UFO2MAP=OFF",
        "build.test_tool_override.DISABLE_UFOMODEL=ON",
        "build.production_maps.DISABLE_MAPS_COMPILE=ON",
        "build.target.ufotestall=PASS",
        "build.target.ufo2map=PASS",
        "build.artifact.ufotestall=present-executable",
        "build.artifact.ufo2map=present-executable",
        "build.artifact.base_game_so=present",
        "build.runtime_data_stage=tracked-only",
        "build.fixture_stage=tracked-unittest-only",
        f"build.fixture_map_source_count={len(unit_test_map_sources)}",
        f"build.fixture_bsp_count={len(generated_fixture_bsps)}",
        "build.fixture_map_compile=PASS",
        "build.fixture_map_user_state=isolated",
        "corpus.authority_lane=canonical-state-and-protocol-assertions",
        "corpus.presentation_suites=excluded",
        f"corpus.selected_test_source_count={len(test_sources)}",
        f"corpus.support_source_count={len(support_sources)}",
        f"corpus.fixture_root_count={len(fixture_roots)}",
        f"corpus.runtime_data_root_count={len(runtime_data_roots)}",
        f"corpus.selected_source_count={len(test_sources) + len(support_sources)}",
        f"corpus.discovered_enabled_test_count={len(discovered_enabled_tests)}",
        f"corpus.core_enabled_test_count={len(selected_tests)}",
        f"corpus.deferred_asset_sweep_test_count={len(deferred_asset_tests)}",
        f"corpus.compile_time_excluded_test_count={len(compile_time_excluded_tests)}",
        f"corpus.selected_disabled_test_count={len(disabled_tests)}",
        f"corpus.blake3_256={corpus_b3}",
        "asset_sweep.status=DEFERRED-SEPARATE-LANE",
        "asset_sweep.production_bsp_corpus=not-built-by-m0-core-preset",
        "run.working_directory=clean-build-root",
        "run.fixture_directory=build-m0-legacy-f44/unittest",
        "run.user_state=isolated-per-invocation",
        "run.locale=C",
        "run.timezone=UTC",
        "run.pass_count=2",
        f"run.trace_test_count={len(trace)}",
        f"run.trace_blake3_256={trace_b3}",
        "run.trace_repeatability=PASS",
        "result=PASS",
        "corpus.begin",
    ])
    lines.extend(corpus_lines)
    lines.append("corpus.end")
    lines.append("generated_fixture_bsp.begin")
    for i, (name, digest) in enumerate(generated_fixture_bsp_hashes):
        lines.append(f"generated_fixture_bsp.{i:02d}.path={name}")
        lines.append(f"generated_fixture_bsp.{i:02d}.sha256={digest}")
    lines.append("generated_fixture_bsp.end")
    lines.append("deferred_asset_sweep.begin")
    for i, entry in enumerate(deferred_asset_tests):
        lines.append(f"deferred_asset_sweep.{i:02d}.name={entry['name']}")
        lines.append(f"deferred_asset_sweep.{i:02d}.reason={entry['reason']}")
    lines.append("deferred_asset_sweep.end")
    lines.append("compile_time_excluded.begin")
    for i, entry in enumerate(compile_time_excluded_tests):
        lines.append(f"compile_time_excluded.{i:02d}.name={entry['name']}")
        lines.append(f"compile_time_excluded.{i:02d}.reason={entry['reason']}")
    lines.append("compile_time_excluded.end")
    if disabled_tests:
        lines.append("disabled.begin")
        lines.extend(f"disabled.{i:03d}={name}" for i, name in enumerate(disabled_tests))
        lines.append("disabled.end")
    lines.append("trace.begin")
    lines.extend(f"trace.{i:03d}={name}" for i, name in enumerate(trace))
    lines.append("trace.end")
    return ("\n".join(lines) + "\n").encode("utf-8")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def execute(root: Path) -> bytes:
    require_ancestor(root)

    print("=== M0.5 PRECONDITION: M0.3 ENVIRONMENT ===")
    verify_m0_3(root)

    print("\n=== M0.5 PRECONDITION: M0.4 LEGACY BASELINE ===")
    verify_m0_4(root)
    print(f"M0.4 evidence verification: PASS ({M0_4_EVIDENCE_B3})")

    scope = load_scope(root)
    test_sources = list(scope["selected_test_sources"])
    support_sources = list(scope.get("support_test_sources", []))
    fixture_roots = list(scope.get("fixture_roots", []))
    runtime_data_roots = list(scope.get("runtime_data_roots", []))
    deferred_asset_tests = list(scope.get("deferred_asset_sweep_tests", []))
    compile_time_excluded_tests = list(scope.get("compile_time_excluded_tests", []))
    unit_test_map_sources = list(scope.get("unit_test_map_sources", []))
    for rel in test_sources + support_sources + unit_test_map_sources:
        if not (root / rel).is_file():
            raise GateError(f"selected canonical test/support source missing: {rel}")
    for rel in fixture_roots:
        if not (root / rel).is_dir():
            raise GateError(f"canonical fixture root missing: {rel}")
    for rel in runtime_data_roots:
        if not (root / rel).is_dir():
            raise GateError(f"canonical runtime data root missing: {rel}")

    gtest_nevra = rpm_nevra(root, "gtest-devel")
    pkg = run(["pkg-config", "--modversion", "gtest"], cwd=root, check=False)
    gtest_pkg_version = (pkg.stdout or "").strip() if pkg.returncode == 0 else "not-reported"
    print(f"M0.5 test-only GoogleTest: {gtest_nevra}")

    selected_all: list[str] = []
    for rel in test_sources:
        selected_all.extend(source_tests(root / rel))
    if len(selected_all) != len(set(selected_all)):
        seen: set[str] = set()
        dup = sorted({x for x in selected_all if x in seen or seen.add(x)})
        raise GateError(f"duplicate canonical test identities across selected sources: {dup}")
    disabled = sorted(
        name for name in selected_all
        if name.split(".", 1)[0].startswith("DISABLED_") or name.split(".", 1)[1].startswith("DISABLED_")
    )
    compile_time_names = [entry["name"] for entry in compile_time_excluded_tests]
    unknown_compile_time = sorted(set(compile_time_names) - set(selected_all))
    if unknown_compile_time:
        raise GateError(
            "compile-time excluded tests are not present in selected source text: "
            + ", ".join(unknown_compile_time)
        )
    discovered_enabled = sorted(set(selected_all) - set(disabled) - set(compile_time_names))
    deferred_names = [entry["name"] for entry in deferred_asset_tests]
    unknown_deferred = sorted(set(deferred_names) - set(discovered_enabled))
    if unknown_deferred:
        raise GateError("deferred asset sweep tests are not selected/enabled: " + ", ".join(unknown_deferred))
    selected_enabled = sorted(set(discovered_enabled) - set(deferred_names))
    if not selected_enabled:
        raise GateError("canonical core test corpus is empty after exclusions")

    build = root / BUILD_REL
    if build.exists():
        shutil.rmtree(build)

    configure_log = build / "m0-canonical-configure.log"
    build_log = build / "m0-canonical-build.log"
    fixture_map_log = build / "m0-canonical-fixture-maps.log"
    list_log = build / "m0-canonical-list.log"
    run1_log = build / "m0-canonical-run-1.log"
    run2_log = build / "m0-canonical-run-2.log"

    print("\n=== CLEAN CANONICAL LEGACY CONFIGURE ===")
    configure_args = [
        "cmake", "--preset", "legacy-m0-f44",
        "-DDISABLE_TOOLS=OFF",
        "-DDISABLE_UFO2MAP=OFF",
        "-DDISABLE_UFOMODEL=ON",
    ]
    run_logged(configure_args, cwd=root, log_path=configure_log)
    cache = build / "CMakeCache.txt"
    if not cache.is_file():
        raise GateError("CMakeCache.txt missing after configure")
    expected_cache = {
        "UFOAI_REMASTER": "OFF",
        "CMAKE_BUILD_TYPE": "RelWithDebInfo",
        "DISABLE_TOOLS": "OFF",
        "DISABLE_UFO2MAP": "OFF",
        "DISABLE_UFOMODEL": "ON",
        "DISABLE_MAPS_COMPILE": "ON",
    }
    for key, expected in expected_cache.items():
        actual = read_cache_value(cache, key)
        if actual != expected:
            raise GateError(f"legacy M0.5 cache gate failed: {key} expected {expected}, got {actual}")
    print("legacy M0.5 cache gate: PASS (canonical legacy + ufo2map test tool, production maps disabled)")

    print("\n=== TRACKED CANONICAL RUNTIME DATA STAGE ===")
    staged_runtime_count = stage_tracked_fixtures(root, build, runtime_data_roots)
    print(f"canonical runtime data: PASS ({staged_runtime_count} tracked files staged)")

    print("\n=== CLEAN CANONICAL UFOTESTALL + UFO2MAP BUILD ===")
    run_logged(
        ["cmake", "--build", str(build), "--target", "ufotestall", "ufo2map", "--parallel", "8"],
        cwd=root, log_path=build_log,
    )
    ufotestall = build / "ufotestall"
    ufo2map = build / "ufo2map"
    game_so = build / "base/game.so"
    if not ufotestall.is_file() or not os.access(ufotestall, os.X_OK):
        raise GateError("ufotestall build artifact missing or non-executable")
    if not ufo2map.is_file() or not os.access(ufo2map, os.X_OK):
        raise GateError("ufo2map build artifact missing or non-executable")
    if not game_so.is_file():
        raise GateError("base/game.so dependency artifact missing")
    print("canonical test build artifacts: PASS (ufotestall, ufo2map, base/game.so)")

    print("\n=== TRACKED TEST FIXTURE STAGE + MAP COMPILE ===")
    copied_fixture_count = stage_tracked_fixtures(root, build, fixture_roots)
    generated_fixture_bsps = compile_unit_test_maps(
        build, unit_test_map_sources, fixture_map_log,
        env=make_isolated_env(build, "fixture-map-compile"),
    )
    print(
        f"canonical test fixtures: PASS ({copied_fixture_count} tracked files staged, "
        f"{len(generated_fixture_bsps)} BSPs compiled)"
    )

    print("\n=== CANONICAL TEST DISCOVERY ===")
    listed = run_logged(
        [str(ufotestall), "--gtest_list_tests", "--gtest_color=no"],
        cwd=build, log_path=list_log, env=make_isolated_env(build, "discovery"),
    )
    available = set(parse_gtest_list(listed))
    missing = [name for name in discovered_enabled if name not in available]
    if missing:
        raise GateError("selected canonical tests not exposed by ufotestall: " + ", ".join(missing))
    unexpectedly_exposed = [name for name in compile_time_names if name in available]
    if unexpectedly_exposed:
        raise GateError(
            "compile-time exclusion scope is stale; tests are now exposed: "
            + ", ".join(unexpectedly_exposed)
        )
    print(
        f"canonical test discovery: PASS ({len(discovered_enabled)} enabled exposed; "
        f"{len(selected_enabled)} core; {len(deferred_asset_tests)} deferred asset sweeps; "
        f"{len(compile_time_excluded_tests)} compile-time excluded; {len(disabled)} disabled excluded)"
    )

    filter_value = ":".join(selected_enabled)
    args = [
        str(ufotestall),
        f"--gtest_filter={filter_value}",
        "--gtest_color=no",
        "--gtest_print_time=0",
    ]

    print("\n=== CANONICAL REGRESSION PASS 1/2 ===")
    out1 = run_logged(
        args, cwd=build, log_path=run1_log, env=make_isolated_env(build, "run-1")
    )
    trace1 = parse_run_trace(out1)
    if trace1 != selected_enabled:
        if set(trace1) != set(selected_enabled) or len(trace1) != len(selected_enabled):
            raise GateError(
                f"run 1 executed an unexpected test set: expected {len(selected_enabled)}, got {len(trace1)}"
            )
        # Registration order need not match the lexicographic filter order; normalize to actual order.
    print(f"canonical regression pass 1: PASS ({len(trace1)} tests)")

    print("\n=== CANONICAL REGRESSION PASS 2/2 ===")
    out2 = run_logged(
        args, cwd=build, log_path=run2_log, env=make_isolated_env(build, "run-2")
    )
    trace2 = parse_run_trace(out2)
    if trace1 != trace2:
        raise GateError("canonical two-run execution trace mismatch")
    if set(trace2) != set(selected_enabled) or len(trace2) != len(selected_enabled):
        raise GateError("run 2 executed an unexpected test set")
    print(f"canonical regression pass 2: PASS ({len(trace2)} tests)")
    print("canonical two-run trace repeatability: PASS")

    return evidence_bytes(
        root,
        gtest_nevra=gtest_nevra,
        gtest_pkg_version=gtest_pkg_version,
        test_sources=test_sources,
        support_sources=support_sources,
        fixture_roots=fixture_roots,
        runtime_data_roots=runtime_data_roots,
        selected_tests=selected_enabled,
        discovered_enabled_tests=discovered_enabled,
        deferred_asset_tests=deferred_asset_tests,
        compile_time_excluded_tests=compile_time_excluded_tests,
        unit_test_map_sources=unit_test_map_sources,
        generated_fixture_bsps=generated_fixture_bsps,
        disabled_tests=disabled,
        trace=trace1,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run/verify the UFO:AI Remaster M0.5 canonical regression corpus")
    parser.add_argument("--verify", action="store_true", help="rerun the corpus and byte-compare with committed/generated evidence")
    args = parser.parse_args()

    try:
        root = repo_root()
        os.chdir(root)
        new_evidence = execute(root)
        new_digest = b3_bytes(root, new_evidence)

        evidence_path = root / EVIDENCE_REL
        sidecar_path = root / SIDECAR_REL

        if args.verify:
            if not evidence_path.is_file() or not sidecar_path.is_file():
                raise GateError("M0.5 evidence/sidecar missing; run without --verify first")
            old = evidence_path.read_bytes()
            if old != new_evidence:
                import difflib
                diff = "".join(difflib.unified_diff(
                    old.decode("utf-8", errors="replace").splitlines(True),
                    new_evidence.decode("utf-8", errors="replace").splitlines(True),
                    fromfile=str(EVIDENCE_REL) + " (stored)",
                    tofile=str(EVIDENCE_REL) + " (current)",
                ))
                raise GateError("M0.5 evidence drift detected:\n" + diff)
            declared = sidecar_digest(sidecar_path)
            actual = b3_file(root, evidence_path)
            if declared != new_digest or actual != new_digest:
                raise GateError(
                    f"M0.5 sidecar mismatch: regenerated={new_digest}, stored={actual}, sidecar={declared}"
                )
            print(f"\nM0.5 canonical regression verification: PASS ({new_digest})")
            return 0

        atomic_write(evidence_path, new_evidence)
        sidecar = f"{new_digest}  {EVIDENCE_REL.name}\n".encode("utf-8")
        atomic_write(sidecar_path, sidecar)
        print("\nM0.5 canonical regression/replay/reference harness: PASS")
        print(f"evidence: {EVIDENCE_REL}")
        print(f"BLAKE3-256: {new_digest}")
        print(f"sidecar:  {SIDECAR_REL}")
        print(f"configure log: {BUILD_REL / 'm0-canonical-configure.log'}")
        print(f"build log:     {BUILD_REL / 'm0-canonical-build.log'}")
        print(f"fixture maps:  {BUILD_REL / 'm0-canonical-fixture-maps.log'}")
        print(f"list log:      {BUILD_REL / 'm0-canonical-list.log'}")
        print(f"run 1 log:     {BUILD_REL / 'm0-canonical-run-1.log'}")
        print(f"run 2 log:     {BUILD_REL / 'm0-canonical-run-2.log'}")
        return 0
    except GateError as e:
        print(f"M0.5 canonical regression: FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
