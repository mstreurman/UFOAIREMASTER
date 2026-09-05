#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASELINE_REVISION = "f34679f8f5674a2a272595870b9ff55de7e13035"
M0_6_EVIDENCE_B3 = "9812843be2e738af10cc401d1d0ca5a46eb1e6d08c95abd8172f86fc4599d553"
M0_6_EVIDENCE_REL = Path("docs/reference/reference-m0-feature-selection.txt")
M0_6_SIDECAR_REL = Path("docs/reference/reference-m0-feature-selection.b3")

FIXTURE_DIR_REL = Path("tools/remaster/descriptor_heap_fixture")
FIXTURE_CMAKE_REL = FIXTURE_DIR_REL / "CMakeLists.txt"
FIXTURE_CPP_REL = FIXTURE_DIR_REL / "descriptor_heap_fixture.cpp"
FIXTURE_SHADER_REL = FIXTURE_DIR_REL / "descriptor_heap_fixture.slang"
RUNNER_REL = Path("tools/remaster/run-m0-descriptor-heap-fixture.py")
REFERENCE_DOC_REL = Path("docs/reference/reference-m0-descriptor-heap.md")
EVIDENCE_REL = Path("docs/reference/reference-m0-descriptor-heap.txt")
SIDECAR_REL = Path("docs/reference/reference-m0-descriptor-heap.b3")
BUILD_REL = Path("build-m0-descriptor-heap-f44")
SLANGC_REL = Path("tools/slang/v2026.17/bin/slangc")
ITERATIONS = 256

SYSTEM_ICD_DIRS = (
    Path("/usr/share/vulkan/icd.d"),
    Path("/etc/vulkan/icd.d"),
    Path("/usr/local/share/vulkan/icd.d"),
)

EXPECTED_FIXTURE = {
    "device.vendor_id": "0x8086",
    "device.device_id": "0xe20b",
    "extension.descriptor_heap_revision": "1",
    "feature.descriptor_heap": "true",
    "feature.descriptor_heap_capture_replay": "true",
    "feature.shader_untyped_pointers": "true",
    "feature.buffer_device_address": "true",
    "heap.sampler_alignment": "64",
    "heap.resource_alignment": "64",
    "heap.max_sampler_size": "2147483648",
    "heap.max_resource_size": "2147483648",
    "heap.sampler_descriptor_size": "32",
    "heap.image_descriptor_size": "64",
    "heap.buffer_descriptor_size": "64",
    "heap.sampler_descriptor_alignment": "32",
    "heap.image_descriptor_alignment": "64",
    "heap.buffer_descriptor_alignment": "64",
    "heap.sparse": "true",
    "heap.protected": "false",
    "heap.direct_mapped": "true",
    "heap.explicit_subrange_alignment": "PASS",
    "heap.reserved_tail_policy": "PASS",
    "execution.sampler_descriptor_write": "PASS",
    "execution.resource_descriptor_write": "PASS",
    "execution.sampler_heap_bind": "PASS",
    "execution.resource_heap_bind": "PASS",
    "execution.push_data_32_bytes": "PASS",
    "execution.sampled_image_read": "PASS",
    "execution.storage_image_write_readback": "PASS",
    "execution.storage_buffer_read_write": "PASS",
    "churn.iterations": str(ITERATIONS),
    "churn.retire_before_republish": "fence-complete",
    "validation.warning_count": "0",
    "validation.error_count": "0",
    "result": "PASS",
}

VULKAN_ENV_OVERRIDES = {
    "VK_ICD_FILENAMES",
    "VK_DRIVER_FILES",
    "VK_ADD_DRIVER_FILES",
    "VK_LAYER_PATH",
    "VK_ADD_LAYER_PATH",
    "VK_IMPLICIT_LAYER_PATH",
    "VK_ADD_IMPLICIT_LAYER_PATH",
    "VK_INSTANCE_LAYERS",
    "VK_LOADER_LAYERS_ENABLE",
    "VK_LOADER_LAYERS_DISABLE",
    "VK_LOADER_LAYERS_ALLOW",
    "VK_LOADER_DRIVERS_SELECT",
    "VK_LOADER_DRIVERS_DISABLE",
    "VK_LOADER_DEVICE_SELECT",
    "VK_LOADER_DISABLE_SELECT",
    "VK_LOADER_DEVICE_ID_FILTER",
    "VK_LOADER_VENDOR_ID_FILTER",
    "VK_LOADER_DRIVER_ID_FILTER",
    "VK_LOADER_DEBUG",
    "VK_VALIDATION_FEATURES",
    "VK_VALIDATION_CHECKS",
    "MESA_VK_DEVICE_SELECT",
    "MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE",
    "DRI_PRIME",
}


class GateError(RuntimeError):
    pass


def run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None,
        check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(args), flush=True)
    proc = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n", flush=True)
    if check and proc.returncode != 0:
        raise GateError(f"command failed ({proc.returncode}): {' '.join(args)}")
    return proc


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def b3_file(root: Path, path: Path) -> str:
    proc = subprocess.run(
        ["b3sum", str(path)], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise GateError(f"b3sum failed for {path}: {proc.stderr.strip()}")
    parts = proc.stdout.split()
    if not parts:
        raise GateError(f"b3sum produced no digest for {path}")
    return parts[0]


def b3_bytes(root: Path, data: bytes) -> str:
    proc = subprocess.run(
        ["b3sum"], cwd=root, input=data,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise GateError(f"b3sum failed: {proc.stderr.decode(errors='replace')}")
    return proc.stdout.decode().strip().split()[0]


def sidecar_digest(path: Path) -> str:
    parts = path.read_text(encoding="utf-8").strip().split()
    if not parts:
        raise GateError(f"empty sidecar: {path}")
    return parts[0]


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise GateError(
            f"required tool '{name}' is missing. On Fedora install SPIR-V/Vulkan build tools as needed; "
            "for spirv-val/spirv-dis use: sudo dnf install spirv-tools"
        )
    return path


def first_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else "unknown"


def require_baseline(root: Path) -> None:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_REVISION, "HEAD"],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    if proc.returncode != 0:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        raise GateError(f"HEAD {head} is not a descendant of M0.6 baseline {BASELINE_REVISION}")

    src_delta = subprocess.check_output(
        ["git", "diff", "--name-only", BASELINE_REVISION, "--", "src"],
        cwd=root, text=True,
    ).strip()
    if src_delta:
        raise GateError("M0.7 R2 must not change canonical/production src/:\n" + src_delta)
    src_status = subprocess.check_output(
        ["git", "status", "--porcelain", "--", "src"], cwd=root, text=True,
    ).strip()
    if src_status:
        raise GateError("M0.7 R2 requires src/ to be clean:\n" + src_status)


def verify_m0_6(root: Path) -> None:
    evidence = root / M0_6_EVIDENCE_REL
    sidecar = root / M0_6_SIDECAR_REL
    if not evidence.is_file() or not sidecar.is_file():
        raise GateError("M0.6 evidence/sidecar is missing")
    actual = b3_file(root, evidence)
    declared = sidecar_digest(sidecar)
    if actual != M0_6_EVIDENCE_B3 or declared != M0_6_EVIDENCE_B3:
        raise GateError(
            f"M0.6 evidence identity mismatch: expected={M0_6_EVIDENCE_B3}, "
            f"actual={actual}, sidecar={declared}"
        )


def discover_intel_anv_icd() -> tuple[Path, str]:
    candidates: list[tuple[Path, str]] = []
    parse_errors: list[str] = []
    for directory in SYSTEM_ICD_DIRS:
        if not directory.is_dir():
            continue
        for manifest in sorted(directory.glob("*.json")):
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as e:
                parse_errors.append(f"{manifest}: {e}")
                continue
            icd = data.get("ICD")
            if not isinstance(icd, dict):
                continue
            library_path = icd.get("library_path")
            if not isinstance(library_path, str) or not library_path:
                continue
            library_name = Path(library_path).name
            if library_name == "libvulkan_intel.so" or library_name.startswith("libvulkan_intel.so."):
                candidates.append((manifest.resolve(), library_path))

    if not candidates:
        detail = "" if not parse_errors else "\nmanifest parse errors:\n  " + "\n  ".join(parse_errors)
        raise GateError(
            "could not find a system Intel ANV Vulkan ICD manifest identifying libvulkan_intel.so" + detail
        )

    native = [item for item in candidates if "x86_64" in item[0].name.lower()]
    if len(native) == 1:
        return native[0]
    if len(candidates) == 1:
        return candidates[0]

    listing = "\n".join(f"  {path} -> {library}" for path, library in candidates)
    raise GateError(
        "multiple Intel ANV ICD manifests found and no unique native x86_64 manifest could be selected:\n" + listing
    )


def isolated_runtime_env(build: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key in VULKAN_ENV_OVERRIDES:
        env.pop(key, None)
    state = build / "runtime-state"
    home = state / "home"
    cache = state / "cache"
    config = state / "config"
    data = state / "data"
    for path in (home, cache, config, data):
        path.mkdir(parents=True, exist_ok=True)
    env.update({
        "HOME": str(home),
        "XDG_CACHE_HOME": str(cache),
        "XDG_CONFIG_HOME": str(config),
        "XDG_DATA_HOME": str(data),
        "LC_ALL": "C",
        "LANG": "C",
        "TZ": "UTC",
    })
    return env


def parse_fixture_output(text: str) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if "=" not in line:
            raise GateError(f"fixture stdout contains a non key=value line: {line!r}")
        key, value = line.split("=", 1)
        if key in values:
            raise GateError(f"fixture output contains duplicate key: {key}")
        values[key] = value
        lines.append(line)
    for key, expected in EXPECTED_FIXTURE.items():
        actual = values.get(key)
        if actual != expected:
            raise GateError(f"fixture output mismatch: {key} expected {expected!r}, got {actual!r}")
    if "trace.fnv1a64" not in values or not re.fullmatch(r"[0-9a-f]{16}", values["trace.fnv1a64"]):
        raise GateError("fixture trace.fnv1a64 is missing or malformed")
    max_push = values.get("heap.max_push_data_size")
    if max_push is None or int(max_push) < 32:
        raise GateError("fixture max push-data size is missing or <32")
    device_name = values.get("device.name", "")
    if not device_name or "llvmpipe" in device_name.lower():
        raise GateError("fixture selected an invalid device name")
    return values, lines


def validate_shader_interface(root: Path, spirv_dis: str, shader: Path) -> str:
    proc = run([spirv_dis, str(shader)], cwd=root)
    text = proc.stdout or ""
    if "DescriptorSet" not in text or "Binding" not in text:
        raise GateError("R2 shader no longer exposes legacy DescriptorSet/Binding decorations")
    if "PushConstant" not in text:
        raise GateError("R2 shader no longer exposes a push-constant interface for vkCmdPushDataEXT")
    if "SPV_EXT_descriptor_heap" in text or "DescriptorHeapEXT" in text:
        raise GateError(
            "R2 shader unexpectedly uses direct SPV_EXT_descriptor_heap; that belongs to the separate R3 gate"
        )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def evidence_bytes(
    root: Path,
    *,
    cmake_version: str,
    ninja_version: str,
    slang_version: str,
    spirv_val_version: str,
    spirv_dis_version: str,
    executable: Path,
    shader: Path,
    shader_disassembly_sha256: str,
    driver_manifest: Path,
    driver_library: str,
    fixture_lines: list[str],
) -> bytes:
    input_paths = [
        FIXTURE_CMAKE_REL,
        FIXTURE_CPP_REL,
        FIXTURE_SHADER_REL,
        RUNNER_REL,
        REFERENCE_DOC_REL,
    ]
    lines = [
        "ufoai-remaster-m0-descriptor-heap-v1",
        "schema.version=1",
        f"baseline.m0_6_revision={BASELINE_REVISION}",
        f"baseline.m0_6_evidence_blake3_256={M0_6_EVIDENCE_B3}",
        "scope.fixture=R2-native-vk-ext-descriptor-heap-sampler-resource",
        "scope.shader_interface=legacy-set-binding-mapped-to-native-heaps",
        "scope.direct_spv_ext_descriptor_heap=deferred-to-R3",
        "scope.acceleration_structure_heap=deferred-to-R4",
        "scope.production_integration=none",
        "source.src_delta_from_m0_6=none",
        f"tool.cmake={cmake_version}",
        f"tool.ninja={ninja_version}",
        f"tool.slang={slang_version}",
        f"tool.spirv_val={spirv_val_version}",
        f"tool.spirv_dis={spirv_dis_version}",
        "runtime.user_state=isolated",
        "runtime.locale=C",
        "runtime.timezone=UTC",
        "runtime.vulkan_environment=inherited-overrides-cleared-single-intel-anv-driver-forced",
        "runtime.vulkan_driver_override=VK_DRIVER_FILES",
        f"runtime.vulkan_driver_manifest={driver_manifest}",
        f"runtime.vulkan_driver_manifest.sha256={sha256_file(driver_manifest)}",
        f"runtime.vulkan_driver_library={driver_library}",
    ]
    for rel in input_paths:
        lines.append(f"input.{str(rel).replace('/', '_')}.sha256={sha256_file(root / rel)}")
    lines.extend([
        f"build.executable.sha256={sha256_file(executable)}",
        f"build.shader_spirv.sha256={sha256_file(shader)}",
        f"build.shader_disassembly.sha256={shader_disassembly_sha256}",
        "build.cmake=PASS",
        "build.shader_spirv_val_vulkan_1_4=PASS",
        "build.fixture=PASS",
        "validation.VK_LAYER_KHRONOS_validation=PASS",
        "fixture.output.begin",
    ])
    lines.extend("fixture." + line for line in fixture_lines)
    lines.extend([
        "fixture.output.end",
        "result=PASS",
    ])
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
    print("=== M0.7 R2 NATIVE VK_EXT_descriptor_heap EXECUTION FIXTURE ===")
    require_baseline(root)
    verify_m0_6(root)
    print(f"M0.6 evidence verification: PASS ({M0_6_EVIDENCE_B3})")

    for rel in (FIXTURE_CMAKE_REL, FIXTURE_CPP_REL, FIXTURE_SHADER_REL, RUNNER_REL, REFERENCE_DOC_REL):
        if not (root / rel).is_file():
            raise GateError(f"missing M0.7 fixture input: {rel}")

    cmake = require_tool("cmake")
    ninja = require_tool("ninja")
    b3sum = require_tool("b3sum")
    del b3sum
    spirv_val = require_tool("spirv-val")
    spirv_dis = require_tool("spirv-dis")
    slangc = root / SLANGC_REL
    if not slangc.is_file() or not os.access(slangc, os.X_OK):
        raise GateError(f"project-local Slang is missing or non-executable: {SLANGC_REL}")

    cmake_version = first_line(run([cmake, "--version"], cwd=root).stdout or "")
    ninja_version = first_line(run([ninja, "--version"], cwd=root).stdout or "")
    slang_text = run([str(slangc), "-version"], cwd=root).stdout or ""
    slang_match = re.search(r"2026\.17", slang_text)
    if not slang_match:
        raise GateError("project-local slangc is not pinned v2026.17")
    slang_version = "2026.17"
    spirv_val_version = first_line(run([spirv_val, "--version"], cwd=root).stdout or "")
    spirv_dis_version = first_line(run([spirv_dis, "--version"], cwd=root).stdout or "")

    build = root / BUILD_REL
    if build.exists():
        shutil.rmtree(build)

    print("\n=== CLEAN FIXTURE CONFIGURE ===")
    run([
        cmake,
        "-S", str(root / FIXTURE_DIR_REL),
        "-B", str(build),
        "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
        f"-DSLANGC={slangc}",
        f"-DSPIRV_VAL={spirv_val}",
    ], cwd=root)

    print("\n=== CLEAN FIXTURE BUILD + SPIR-V VALIDATION ===")
    run([cmake, "--build", str(build), "--parallel", "8"], cwd=root)
    executable = build / "m0_descriptor_heap_fixture"
    shader = build / "descriptor_heap_fixture.spv"
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise GateError("fixture executable missing after build")
    if not shader.is_file():
        raise GateError("fixture SPIR-V missing after build")
    run([spirv_val, "--target-env", "vulkan1.4", str(shader)], cwd=root)
    shader_disassembly_sha256 = validate_shader_interface(root, spirv_dis, shader)
    print("shader interface separation: PASS (legacy set/binding mapping; no direct SPV_EXT_descriptor_heap)")

    print("\n=== NATIVE B580 DESCRIPTOR-HEAP EXECUTION + CHURN ===")
    driver_manifest, driver_library = discover_intel_anv_icd()
    print(f"selected Vulkan driver manifest: {driver_manifest} -> {driver_library}")
    runtime_env = isolated_runtime_env(build)
    runtime_env["VK_DRIVER_FILES"] = str(driver_manifest)
    fixture_proc = run([
        str(executable),
        "--shader", str(shader),
        "--iterations", str(ITERATIONS),
    ], cwd=build, env=runtime_env)
    _, fixture_lines = parse_fixture_output(fixture_proc.stdout or "")
    print(f"native descriptor-heap execution: PASS ({ITERATIONS} publication/retirement iterations)")

    return evidence_bytes(
        root,
        cmake_version=cmake_version,
        ninja_version=ninja_version,
        slang_version=slang_version,
        spirv_val_version=spirv_val_version,
        spirv_dis_version=spirv_dis_version,
        executable=executable,
        shader=shader,
        shader_disassembly_sha256=shader_disassembly_sha256,
        driver_manifest=driver_manifest,
        driver_library=driver_library,
        fixture_lines=fixture_lines,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run/capture/verify the UFO:AI Remaster M0.7 R2 native VK_EXT_descriptor_heap fixture"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true", help="run and capture M0.7 R2 evidence")
    mode.add_argument("--verify", action="store_true", help="rerun and byte-compare with stored M0.7 R2 evidence")
    args = parser.parse_args()

    try:
        root = repo_root()
        os.chdir(root)
        new_evidence = execute(root)
        digest = b3_bytes(root, new_evidence)
        evidence_path = root / EVIDENCE_REL
        sidecar_path = root / SIDECAR_REL

        if args.verify:
            if not evidence_path.is_file() or not sidecar_path.is_file():
                raise GateError("M0.7 R2 evidence/sidecar missing; run --capture first")
            old = evidence_path.read_bytes()
            if old != new_evidence:
                diff = "".join(difflib.unified_diff(
                    old.decode("utf-8", errors="replace").splitlines(True),
                    new_evidence.decode("utf-8", errors="replace").splitlines(True),
                    fromfile=str(EVIDENCE_REL) + " (stored)",
                    tofile=str(EVIDENCE_REL) + " (rerun)",
                ))
                raise GateError("M0.7 R2 evidence changed on rerun:\n" + diff)
            declared = sidecar_digest(sidecar_path)
            stored = b3_file(root, evidence_path)
            if declared != digest or stored != digest:
                raise GateError(
                    f"M0.7 R2 digest mismatch: rerun={digest}, stored={stored}, sidecar={declared}"
                )
            print(f"\nM0.7 R2 native descriptor-heap verification: PASS ({digest})")
        else:
            atomic_write(evidence_path, new_evidence)
            sidecar = f"{digest}  {EVIDENCE_REL.name}\n".encode("utf-8")
            atomic_write(sidecar_path, sidecar)
            print(f"\nM0.7 R2 native descriptor-heap capture: PASS ({digest})")
        return 0
    except (GateError, OSError, ValueError) as e:
        print(f"M0.7 R2 descriptor-heap gate: FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
