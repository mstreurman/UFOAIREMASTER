#!/usr/bin/env python3
"""Capture/verify the M0.6 fail-closed presentation-selection scaffold."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

M0_5_REVISION = "9616ae01839a93e3938121841c1484c0f4be25b8"
M0_5_EVIDENCE_BLAKE3 = "b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e"
SELECTORS = (
    "PLATFORM",
    "RENDERER",
    "UI",
    "AUDIO",
    "VFX",
    "CINEMATICS",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(cmd: list[str], *, cwd: Path, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def git_output(repo: Path, *args: str) -> str:
    result = run(["git", *args], cwd=repo, capture=True)
    require(result.returncode == 0, result.stdout or f"git {' '.join(args)} failed")
    return (result.stdout or "").strip()


def check_m0_5_identity(repo: Path) -> None:
    sidecar = repo / "docs/reference/reference-m0-canonical-regression.b3"
    require(sidecar.is_file(), f"missing M0.5 sidecar: {sidecar}")
    first = sidecar.read_text(encoding="utf-8").strip().split()
    require(first, "M0.5 sidecar is empty")
    require(
        first[0] == M0_5_EVIDENCE_BLAKE3,
        f"M0.5 evidence identity changed: expected {M0_5_EVIDENCE_BLAKE3}, got {first[0]}",
    )

    ancestry = run(
        ["git", "merge-base", "--is-ancestor", M0_5_REVISION, "HEAD"],
        cwd=repo,
        capture=True,
    )
    require(ancestry.returncode == 0, "current HEAD does not descend from the landed M0.5 revision")


def check_no_src_delta(repo: Path) -> None:
    committed = git_output(repo, "diff", "--name-only", M0_5_REVISION, "--", "src")
    working = git_output(repo, "status", "--porcelain", "--", "src")
    require(not committed, f"M0.6 must not change committed src/ files:\n{committed}")
    require(not working, f"M0.6 must not change working-tree src/ files:\n{working}")


def check_root_integration(repo: Path) -> None:
    root_cmake = (repo / "CMakeLists.txt").read_text(encoding="utf-8")
    include_line = 'include("${CMAKE_SOURCE_DIR}/cmake/remaster/PresentationSelection.cmake")'
    call_line = "ufoai_remaster_configure_presentation_selection()"
    require(root_cmake.count(include_line) == 1, "root CMake must include PresentationSelection.cmake exactly once")
    require(root_cmake.count(call_line) == 1, "root CMake must configure presentation selection exactly once")
    require(
        root_cmake.index(call_line) < root_cmake.index("if (UFOAI_REMASTER)"),
        "presentation selection must fail closed before remaster dependency probing",
    )

    presets = json.loads((repo / "CMakePresets.json").read_text(encoding="utf-8"))
    for preset in presets.get("configurePresets", []):
        cache = preset.get("cacheVariables", {})
        for selector in SELECTORS:
            name = f"UFOAI_PRESENTATION_{selector}"
            value = cache.get(name)
            require(
                value in (None, "LEGACY"),
                f"preset {preset.get('name')} overrides {name}={value}; M0.6 defaults must remain legacy",
            )


def write_probe_project(repo: Path, source_dir: Path) -> None:
    module = (repo / "cmake/remaster/PresentationSelection.cmake").as_posix()
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.15)",
                "project(ufoai_m0_selection_probe LANGUAGES NONE)",
                'option(UFOAI_REMASTER "probe remaster bootstrap" OFF)',
                f'include("{module}")',
                "ufoai_remaster_configure_presentation_selection()",
                "",
            ]
        ),
        encoding="utf-8",
    )


def configure_case(
    repo: Path,
    probe_source: Path,
    case_dir: Path,
    definitions: dict[str, str],
    *,
    expect_success: bool,
    expected_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    if case_dir.exists():
        shutil.rmtree(case_dir)
    cmd = ["cmake", "-S", str(probe_source), "-B", str(case_dir), "-G", "Ninja"]
    cmd.extend(f"-D{name}={value}" for name, value in definitions.items())
    result = run(cmd, cwd=repo, capture=True)

    if expect_success:
        require(result.returncode == 0, result.stdout or f"configure failed for {case_dir.name}")
    else:
        require(result.returncode != 0, f"configure unexpectedly succeeded for {case_dir.name}")
        if expected_text:
            require(expected_text in (result.stdout or ""), f"expected failure text not found: {expected_text}")
    return result


def parse_manifest(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("ufoai-") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def run_selection_probes(repo: Path) -> dict[str, str]:
    build_root = repo / "build-m0-feature-selection-check"
    if build_root.exists():
        shutil.rmtree(build_root)
    probe_source = build_root / "probe-src"
    write_probe_project(repo, probe_source)

    default_off = build_root / "default-off"
    configure_case(repo, probe_source, default_off, {"UFOAI_REMASTER": "OFF"}, expect_success=True)
    build_result = run(
        ["cmake", "--build", str(default_off), "--target", "remaster-presentation-selection"],
        cwd=repo,
        capture=True,
    )
    require(build_result.returncode == 0, build_result.stdout or "selection manifest target failed")

    manifest_off = default_off / "remaster/presentation-selection.txt"
    header_off = default_off / "generated/ufoai/remaster/presentation_selection.h"
    require(manifest_off.is_file(), "default-off manifest was not generated")
    require(header_off.is_file(), "default-off generated header was not generated")
    values_off = parse_manifest(manifest_off)
    require(values_off.get("bootstrap.ufoai_remaster") == "0", "default-off bootstrap marker must be 0")
    for selector in SELECTORS:
        require(values_off.get(f"selection.{selector.lower()}") == "LEGACY", f"{selector} default is not LEGACY")
    require(values_off.get("production.behavior") == "legacy", "default production behavior must be legacy")

    default_on = build_root / "default-on"
    configure_case(repo, probe_source, default_on, {"UFOAI_REMASTER": "ON"}, expect_success=True)
    manifest_on = default_on / "remaster/presentation-selection.txt"
    require(manifest_on.is_file(), "default-on manifest was not generated")
    values_on = parse_manifest(manifest_on)
    require(values_on.get("bootstrap.ufoai_remaster") == "1", "default-on bootstrap marker must be 1")
    for selector in SELECTORS:
        require(values_on.get(f"selection.{selector.lower()}") == "LEGACY", f"{selector} changed under bootstrap ON")
    require(values_on.get("production.behavior") == "legacy", "bootstrap ON must not switch production behavior")

    configure_case(
        repo,
        probe_source,
        build_root / "invalid-value",
        {"UFOAI_PRESENTATION_RENDERER": "BANANA"},
        expect_success=False,
        expected_text="Invalid UFOAI_PRESENTATION_RENDERER='BANANA'",
    )
    configure_case(
        repo,
        probe_source,
        build_root / "remaster-without-bootstrap",
        {"UFOAI_REMASTER": "OFF", "UFOAI_PRESENTATION_RENDERER": "REMASTER"},
        expect_success=False,
        expected_text="UFOAI_PRESENTATION_RENDERER=REMASTER requires UFOAI_REMASTER=ON",
    )
    configure_case(
        repo,
        probe_source,
        build_root / "unimplemented-remaster",
        {"UFOAI_REMASTER": "ON", "UFOAI_PRESENTATION_RENDERER": "REMASTER"},
        expect_success=False,
        expected_text="UFOAI_PRESENTATION_RENDERER=REMASTER is not implemented yet",
    )

    return {
        "manifest_off_sha256": sha256_file(manifest_off),
        "manifest_on_sha256": sha256_file(manifest_on),
        "header_off_sha256": sha256_file(header_off),
    }


def verify_canonical_m0_5(repo: Path) -> None:
    harness = repo / "tools/remaster/run-m0-canonical-regression.py"
    require(harness.is_file(), f"missing M0.5 harness: {harness}")
    print("\n=== M0.5 CANONICAL PRESERVATION VERIFY ===", flush=True)
    result = run([sys.executable, str(harness), "--verify"], cwd=repo, capture=False)
    require(result.returncode == 0, "M0.5 canonical regression verification failed under M0.6 scaffold")
    check_m0_5_identity(repo)


def evidence_text(repo: Path, probe_hashes: dict[str, str]) -> str:
    paths = {
        "root_cmake": repo / "CMakeLists.txt",
        "cmake_presets": repo / "CMakePresets.json",
        "selection_module": repo / "cmake/remaster/PresentationSelection.cmake",
        "selection_header_template": repo / "cmake/remaster/PresentationSelection.h.in",
        "selection_manifest_template": repo / "cmake/remaster/presentation-selection.txt.in",
        "verifier": repo / "tools/remaster/verify-m0-feature-selection.py",
        "reference_doc": repo / "docs/reference/reference-m0-feature-selection.md",
    }
    lines = [
        "ufoai-remaster-m0-feature-selection-v1",
        "schema.version=1",
        f"baseline.m0_5_revision={M0_5_REVISION}",
        f"baseline.m0_5_evidence_blake3_256={M0_5_EVIDENCE_BLAKE3}",
    ]
    for key, path in paths.items():
        require(path.is_file(), f"missing M0.6 input: {path}")
        lines.append(f"input.{key}.sha256={sha256_file(path)}")
    lines.extend(
        [
            "selection.component_count=6",
            "selection.default.platform=LEGACY",
            "selection.default.renderer=LEGACY",
            "selection.default.ui=LEGACY",
            "selection.default.audio=LEGACY",
            "selection.default.vfx=LEGACY",
            "selection.default.cinematics=LEGACY",
            "selection.bootstrap_off_default=PASS",
            "selection.bootstrap_on_default=PASS-LEGACY-BEHAVIOR",
            "selection.invalid_value_policy=FAIL-CLOSED",
            "selection.remaster_without_bootstrap_policy=FAIL-CLOSED",
            "selection.unimplemented_remaster_policy=FAIL-CLOSED",
            "selection.interface_target=ufoai_remaster_presentation_selection",
            "selection.inspect_target=remaster-presentation-selection",
            "source.src_delta_from_m0_5=none",
            f"generated.default_off_manifest.sha256={probe_hashes['manifest_off_sha256']}",
            f"generated.default_on_manifest.sha256={probe_hashes['manifest_on_sha256']}",
            f"generated.default_off_header.sha256={probe_hashes['header_off_sha256']}",
            "canonical.m0_5_verify=PASS",
            "production.behavior_replacement=none",
            "result=PASS",
            "",
        ]
    )
    return "\n".join(lines)


def write_b3(repo: Path, evidence_path: Path, sidecar_path: Path) -> str:
    result = run(["b3sum", evidence_path.name], cwd=evidence_path.parent, capture=True)
    require(result.returncode == 0, result.stdout or "b3sum failed")
    line = (result.stdout or "").strip()
    require(line, "b3sum returned no output")
    sidecar_path.write_text(line + "\n", encoding="utf-8")
    return line.split()[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--capture", action="store_true", help="capture M0.6 reference evidence (default)")
    mode.add_argument("--verify", action="store_true", help="recompute and verify committed M0.6 evidence")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    evidence_path = repo / "docs/reference/reference-m0-feature-selection.txt"
    sidecar_path = repo / "docs/reference/reference-m0-feature-selection.b3"

    try:
        print("=== M0.6 FEATURE-SELECTION / COMPATIBILITY SCAFFOLD ===", flush=True)
        check_m0_5_identity(repo)
        check_no_src_delta(repo)
        check_root_integration(repo)
        probe_hashes = run_selection_probes(repo)
        print("selection configure probes: PASS", flush=True)

        verify_canonical_m0_5(repo)
        rendered = evidence_text(repo, probe_hashes)

        if args.verify:
            require(evidence_path.is_file(), f"missing M0.6 evidence: {evidence_path}")
            require(sidecar_path.is_file(), f"missing M0.6 sidecar: {sidecar_path}")
            require(evidence_path.read_text(encoding="utf-8") == rendered, "M0.6 evidence content mismatch")
            check = run(["b3sum", "-c", sidecar_path.name], cwd=sidecar_path.parent, capture=True)
            require(check.returncode == 0, check.stdout or "M0.6 sidecar verification failed")
            identity = sidecar_path.read_text(encoding="utf-8").split()[0]
            print(f"M0.6 feature-selection verification: PASS ({identity})", flush=True)
        else:
            evidence_path.write_text(rendered, encoding="utf-8")
            identity = write_b3(repo, evidence_path, sidecar_path)
            print(f"M0.6 feature-selection capture: PASS ({identity})", flush=True)

        return 0
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
