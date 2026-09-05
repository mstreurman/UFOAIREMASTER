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

BASELINE = "5e2aa2ba6ac620f3cc202f56c8f3205b9b56c2bc"
R2_B3 = "a31f501b96a5cc3467a67c8025a4f7ca585c47fa94c1887c4469c7595c59e594"
R3_B3 = "1793f2d3d23b8ed8455d4f01379578773b48cbe878a46affc0785e95565a7b63"
R2_TXT = Path("docs/reference/reference-m0-descriptor-heap.txt")
R2_SIDECAR = Path("docs/reference/reference-m0-descriptor-heap.b3")
R3_TXT = Path("docs/reference/reference-m0-slang-descriptor-heap.txt")
R3_SIDECAR = Path("docs/reference/reference-m0-slang-descriptor-heap.b3")
FIXTURE = Path("tools/remaster/rt_descriptor_heap_fixture")
CMAKE = FIXTURE / "CMakeLists.txt"
CPP_COMPILE = FIXTURE / "rt_descriptor_heap_compile.cpp"
CPP_NATIVE = FIXTURE / "rt_descriptor_heap_native.cpp"
SHADER = FIXTURE / "rt_descriptor_heap_fixture.slang"
RUNNER = Path("tools/remaster/run-m0-rt-descriptor-heap-fixture.py")
REFERENCE_MD = Path("docs/reference/reference-m0-rt-descriptor-heap.md")
EVIDENCE = Path("docs/reference/reference-m0-rt-descriptor-heap.txt")
SIDECAR = Path("docs/reference/reference-m0-rt-descriptor-heap.b3")
BUILD = Path("build-m0-rt-descriptor-heap-f44")
SLANG_ROOT = Path("tools/slang/v2026.17")

class GateError(RuntimeError):
    pass

def run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(args), flush=True)
    proc = subprocess.run(args, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n", flush=True)
    if check and proc.returncode != 0:
        raise GateError(f"command failed ({proc.returncode}): {' '.join(args)}")
    return proc

def repo_root() -> Path:
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise GateError("not inside a git work tree")
    return Path(p.stdout.strip()).resolve()

def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise GateError(f"required tool missing: {name}")
    return path

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def b3_bytes(data: bytes, root: Path) -> str:
    p = subprocess.run(["b3sum"], cwd=root, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise GateError("b3sum failed: " + p.stderr.decode(errors="replace"))
    return p.stdout.decode().split()[0]

def b3_file(path: Path, root: Path) -> str:
    return b3_bytes(path.read_bytes(), root)

def sidecar_digest(path: Path) -> str:
    parts = path.read_text().strip().split()
    if not parts:
        raise GateError(f"empty sidecar: {path}")
    return parts[0]

def verify_prior(root: Path) -> None:
    for txt_rel, side_rel, expected, name in [
        (R2_TXT, R2_SIDECAR, R2_B3, "R2"),
        (R3_TXT, R3_SIDECAR, R3_B3, "R3"),
    ]:
        txt, side = root / txt_rel, root / side_rel
        if not txt.is_file() or not side.is_file():
            raise GateError(f"{name} accepted evidence is missing")
        if sidecar_digest(side) != expected or b3_file(txt, root) != expected:
            raise GateError(f"{name} evidence identity mismatch")
        print(f"M0.7 {name} evidence verification: PASS ({expected})", flush=True)

def require_baseline(root: Path) -> None:
    p = subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"], cwd=root)
    if p.returncode != 0:
        raise GateError(f"required R3 baseline {BASELINE} is not an ancestor of HEAD")
    p = subprocess.run(["git", "diff", "--quiet", BASELINE, "--", "src"], cwd=root)
    if p.returncode != 0:
        raise GateError("src/ differs from the sealed R3 baseline")

def isolated_env(base: dict[str, str], temp: Path) -> dict[str, str]:
    env = dict(base)
    env["HOME"] = str(temp / "home")
    env["XDG_CACHE_HOME"] = str(temp / "cache")
    env["XDG_CONFIG_HOME"] = str(temp / "config")
    env["XDG_DATA_HOME"] = str(temp / "data")
    for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    return env

def select_native_intel_icd(candidates: list[Path], machine: str) -> Path:
    machine = machine.lower()
    if machine not in {"x86_64", "amd64"}:
        raise GateError(f"R4 reference runner requires x86_64 userspace, got {machine}")

    unique = sorted(set(candidates))
    native = [
        p for p in unique
        if p.name.endswith(".x86_64.json") or p.name.endswith("_x86_64.json")
    ]
    if len(native) == 1:
        return native[0]

    # Some distributions use an unsuffixed manifest when only one architecture
    # is installed. Accept that only when it is the sole Intel ANV candidate.
    if len(unique) == 1:
        return unique[0]

    raise GateError(
        "expected exactly one native x86_64 Intel ANV ICD manifest; "
        f"native={native}, all Intel ANV candidates={unique}")


def find_intel_icd() -> Path:
    # Fedora multilib installations legitimately provide both i686 and x86_64
    # Intel ANV manifests. R4 runs on the x86_64 i9-9900K reference target, so
    # select the native manifest explicitly instead of requiring the ICD
    # directory to contain only one Intel entry.
    roots = [Path("/usr/share/vulkan/icd.d"), Path("/etc/vulkan/icd.d")]
    found: list[Path] = []
    for d in roots:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            try:
                data = json.loads(p.read_text())
            except Exception:
                continue
            lib = str(data.get("ICD", {}).get("library_path", ""))
            if "libvulkan_intel.so" in lib:
                found.append(p.resolve())

    selected = select_native_intel_icd(found, os.uname().machine)
    print(f"Intel ANV ICD selection: {selected}", flush=True)
    return selected

def first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")

def flatten(text: str) -> str:
    return " | ".join(line.strip() for line in text.splitlines() if line.strip())

def parse_kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if re.fullmatch(r"[a-zA-Z0-9_.-]+", k):
            out[k] = v
    return out

def check_raygen_disassembly(text: str) -> None:
    required = [
        'OpExtension "SPV_EXT_descriptor_heap"',
        "OpCapability DescriptorHeapEXT",
        "OpCapability RayTracingKHR",
        "BuiltIn ResourceHeapEXT",
        "OpConvertUToAccelerationStructureKHR",
        "OpTraceRayKHR",
        "OpTypeAccelerationStructureKHR",
    ]
    for needle in required:
        if needle not in text:
            raise GateError(f"raygen SPIR-V missing required semantic: {needle}")
    if re.search(r"OpDecorate .* (DescriptorSet|Binding) ", text):
        raise GateError("raygen direct-heap SPIR-V unexpectedly contains DescriptorSet/Binding decoration")
    # spirv-dis right-aligns result IDs in many modules, so parse semantic lines
    # without assuming the '%' token begins in column zero. The fixture also
    # contains a legitimate RWStructuredBuffer<uint> runtime array with stride 4;
    # only the uint64 acceleration-structure heap view is constrained to stride 8.
    u64_ids = set(re.findall(r"^\s*(%\S+)\s*=\s*OpTypeInt\s+64\s+0\s*$", text, re.M))
    if not u64_ids:
        raise GateError("raygen SPIR-V has no uint64 type")

    arrays = []
    for result_id, elem_id in re.findall(
        r"^\s*(%\S+)\s*=\s*OpTypeRuntimeArray\s+(%\S+)\s*$", text, re.M):
        if elem_id in u64_ids:
            arrays.append(result_id)
    if not arrays:
        raise GateError("raygen SPIR-V has no runtime array over uint64 for AS heap")

    strides = {
        result_id: int(stride)
        for result_id, stride in re.findall(
            r"^\s*OpDecorate\s+(%\S+)\s+ArrayStride\s+(\d+)\s*$", text, re.M)
    }
    if not any(strides.get(arr) == 8 for arr in arrays):
        raise GateError("raygen AS heap runtime array is not decorated with exact ArrayStride 8")
    bad_as_strides = {arr: strides.get(arr) for arr in arrays if strides.get(arr) != 8}
    if bad_as_strides:
        details = ", ".join(f"{arr}:{stride}" for arr, stride in sorted(bad_as_strides.items()))
        raise GateError(f"raygen uint64 AS runtime array has non-8-byte stride: {details}")
    print("8-byte AS direct-heap SPIR-V semantic gate: PASS", flush=True)

def select_slang_library(root: Path) -> Path:
    exact = root / SLANG_ROOT / "lib/libslang-compiler.so"
    if exact.is_file():
        return exact
    candidates = sorted((root / SLANG_ROOT / "lib").glob("libslang-compiler.so*"))
    if len(candidates) != 1:
        raise GateError(
            "expected exact libslang-compiler.so or one compatible pinned Slang library, "
            f"found {len(candidates)}")
    return candidates[0]


def build_evidence(root: Path, tools: dict[str, str], icd: Path, slang_library: Path, metadata: dict[str, str], native: dict[str, str], spv_paths: dict[str, Path]) -> bytes:
    lines = [
        "ufoai-remaster-m0-rt-descriptor-heap-v1",
        "schema.version=1",
        f"baseline.r3_revision={BASELINE}",
        f"baseline.r2_evidence_blake3_256={R2_B3}",
        f"baseline.r3_evidence_blake3_256={R3_B3}",
        f"tool.cmake={tools['cmake']}",
        f"tool.ninja={tools['ninja']}",
        f"tool.slangc={tools['slangc']}",
        f"tool.spirv_val={tools['spirv_val']}",
        f"tool.spirv_dis={tools['spirv_dis']}",
        f"input.fixture_cmake.sha256={sha256(root / CMAKE)}",
        f"input.fixture_compile_cpp.sha256={sha256(root / CPP_COMPILE)}",
        f"input.fixture_native_cpp.sha256={sha256(root / CPP_NATIVE)}",
        f"input.fixture_shader.sha256={sha256(root / SHADER)}",
        f"input.runner.sha256={sha256(root / RUNNER)}",
        f"input.reference_doc.sha256={sha256(root / REFERENCE_MD)}",
        f"slang.api_header.sha256={sha256(root / SLANG_ROOT / 'include/slang.h')}",
        f"slang.api_library.sha256={sha256(slang_library)}",
        f"vulkan.icd_manifest.sha256={sha256(icd)}",
        "compile.api_linked=PASS",
        "compile.user_state=isolated",
        "compile.profile=spirv_1_6",
        "compile.capability.spvDescriptorHeapEXT=PASS",
        "compile.capability.spvRayTracingKHR=PASS",
        "compile.diagnostics=clean",
        "compile.vulkan_target=1.4",
        "compile.resource_heap_stride=0",
        "compile.unified_resource_heap_stride=PASS",
        f"reflection.target_metadata_heap_use={'PASS' if metadata.get('reflection.uses_bindless_resource_heap') == 'true' else 'FAIL'}",
        f"reflection.root_size_32={'PASS' if metadata.get('reflection.root.size') == '32' else 'FAIL'}",
        f"reflection.root_offsets={metadata.get('reflection.root.offsets', 'missing')}",
        f"spirv.raygen.sha256={sha256(spv_paths['raygen'])}",
        f"spirv.miss.sha256={sha256(spv_paths['miss'])}",
        f"spirv.closesthit.sha256={sha256(spv_paths['closesthit'])}",
        "spirv.validation_vulkan1_4=PASS",
        "spirv.extension_spv_ext_descriptor_heap=PASS",
        "spirv.capability_ray_tracing_khr=PASS",
        "spirv.as_runtime_array_uint64=PASS",
        "spirv.as_array_stride=8",
        "spirv.op_convert_u_to_acceleration_structure_khr=PASS",
        "spirv.op_trace_ray_khr=PASS",
        "spirv.descriptor_set_binding_absent=PASS",
        "native.device=Intel-Arc-B580-0x8086-0xe20b",
        f"native.device_api={native.get('device.api', 'missing')}",
        "native.feature.shader_int64=PASS",
        "native.feature.buffer_device_address=PASS",
        "native.feature.scalar_block_layout=PASS",
        "native.feature.synchronization2=PASS",
        "native.feature.descriptor_heap=PASS",
        "native.feature.shader_untyped_pointers=PASS",
        "native.feature.acceleration_structure=PASS",
        "native.feature.ray_tracing_pipeline=PASS",
        "native.feature.ray_tracing_maintenance1=PASS",
        f"native.resource_heap_alignment={native.get('descriptor_heap.resource_alignment', 'missing')}",
        f"native.buffer_descriptor_size={native.get('descriptor_heap.buffer_descriptor_size', 'missing')}",
        f"native.unified_resource_stride={native.get('descriptor_heap.unified_resource_stride', 'missing')}",
        "native.as_typed_stride=8",
        f"native.as_byte_offset={native.get('descriptor_heap.as_byte_offset', 'missing')}",
        f"native.as_typed_index={native.get('descriptor_heap.as_typed_index', 'missing')}",
        f"native.output_byte_offset={native.get('descriptor_heap.output_byte_offset', 'missing')}",
        f"native.output_typed_index={native.get('descriptor_heap.output_typed_index', 'missing')}",
        f"native.tlas_address_match={'PASS' if native.get('tlas.address_match') == 'true' else 'FAIL'}",
        f"native.trace_hit={'PASS' if native.get('trace.hit_magic', '').lower() == '0xc0ffee42' else 'FAIL'}",
        f"native.validation_warnings={native.get('validation.warning_count', 'missing')}",
        f"native.validation_errors={native.get('validation.error_count', 'missing')}",
        "native.as_publication_api=raw-uint64-device-address",
        "native.as_publication_vkWriteResourceDescriptorsEXT=not-used-by-design",
        "native.trace_path=VK_KHR_ray_tracing_pipeline",
        "source.src_delta_from_r3=none",
        "production.behavior_replacement=none",
        "result=PASS",
    ]
    for line in lines:
        if line.endswith("=FAIL") or "=missing" in line:
            raise GateError("evidence contains failed/missing gate: " + line)
    return ("\n".join(lines) + "\n").encode()

def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    root = repo_root()
    try:
        require_baseline(root)
        verify_prior(root)
        cmake = require_tool("cmake")
        ninja = require_tool("ninja")
        spirv_val = require_tool("spirv-val")
        spirv_dis = require_tool("spirv-dis")
        require_tool("b3sum")
        slangc = root / SLANG_ROOT / "bin/slangc"
        if not slangc.is_file():
            raise GateError(f"pinned Slang is missing: {slangc}")
        if not (root / SLANG_ROOT / "include/slang.h").is_file():
            raise GateError("pinned Slang API headers are missing")
        slang_library = select_slang_library(root)
        icd = find_intel_icd()

        tools = {
            "cmake": first_line(run([cmake, "--version"], cwd=root).stdout),
            "ninja": first_line(run([ninja, "--version"], cwd=root).stdout),
            "slangc": first_line(run([str(slangc), "-version"], cwd=root).stdout),
            "spirv_val": flatten(run([spirv_val, "--version"], cwd=root).stdout),
            "spirv_dis": flatten(run([spirv_dis, "--version"], cwd=root).stdout),
        }
        if tools["slangc"] != "2026.17":
            raise GateError("Slang version is not exactly 2026.17")

        build = root / BUILD
        shutil.rmtree(build, ignore_errors=True)
        print("\n=== CLEAN R4 CONFIGURE ===", flush=True)
        run([cmake, "-S", str(root / FIXTURE), "-B", str(build), "-G", "Ninja",
             "-DCMAKE_BUILD_TYPE=RelWithDebInfo", f"-DSLANG_ROOT={root / SLANG_ROOT}"], cwd=root)
        print("\n=== CLEAN R4 BUILD ===", flush=True)
        run([cmake, "--build", str(build), "--parallel", "8"], cwd=root)

        metadata_path = build / "rt_descriptor_heap.metadata.txt"
        print("\n=== PINNED SLANG API RAY-TRACING COMPILE ===", flush=True)
        with tempfile.TemporaryDirectory(prefix="ufoai-r4-") as td:
            env = isolated_env(os.environ, Path(td))
            compile_proc = run([
                str(build / "m0_rt_descriptor_heap_compile"),
                "--source", str(root / SHADER), "--out-dir", str(build),
                "--metadata", str(metadata_path),
            ], cwd=root, env=env)
            if "warning[" in compile_proc.stdout.lower() or "error[" in compile_proc.stdout.lower():
                raise GateError("Slang API compile emitted warning/error diagnostics")

        spv_paths = {
            "raygen": build / "raygen.spv",
            "miss": build / "miss.spv",
            "closesthit": build / "closesthit.spv",
        }
        dis_texts: dict[str, str] = {}
        print("\n=== SPIR-V 1.6 / VULKAN 1.4 VALIDATION ===", flush=True)
        for name, path in spv_paths.items():
            run([spirv_val, "--target-env", "vulkan1.4", str(path)], cwd=root)
            dis_texts[name] = run([spirv_dis, str(path)], cwd=root).stdout
        check_raygen_disassembly(dis_texts["raygen"])

        metadata = parse_kv(metadata_path.read_text())
        if metadata.get("reflection.root.size") != "32" or metadata.get("reflection.root.offsets") != "0,8,16,24":
            raise GateError("Slang reflection root ABI mismatch")
        if metadata.get("reflection.uses_bindless_resource_heap") != "true":
            raise GateError("Slang target metadata does not confirm heap use")

        print("\n=== NATIVE B580 TLAS 8-BYTE HEAP + TRACERAY ===", flush=True)
        with tempfile.TemporaryDirectory(prefix="ufoai-r4-vk-") as td:
            env = isolated_env(os.environ, Path(td))
            env["VK_DRIVER_FILES"] = str(icd)
            native_proc = run([
                str(build / "m0_rt_descriptor_heap_native"),
                "--raygen", str(spv_paths["raygen"]),
                "--miss", str(spv_paths["miss"]),
                "--closest-hit", str(spv_paths["closesthit"]),
            ], cwd=root, env=env)
        native = parse_kv(native_proc.stdout)
        required_native = {
            "device.vendor_id": "0x8086",
            "device.device_id": "0xe20b",
            "feature.shader_int64": "true",
            "feature.buffer_device_address": "true",
            "feature.scalar_block_layout": "true",
            "feature.synchronization2": "true",
            "feature.descriptor_heap": "true",
            "feature.shader_untyped_pointers": "true",
            "feature.acceleration_structure": "true",
            "feature.ray_tracing_pipeline": "true",
            "feature.ray_tracing_maintenance1": "true",
            "tlas.address_match": "true",
            "trace.hit_magic": "0xc0ffee42",
            "validation.warning_count": "0",
            "validation.error_count": "0",
            "result": "PASS",
        }
        for key, expected in required_native.items():
            if native.get(key, "").lower() != expected.lower():
                raise GateError(f"native R4 field {key} expected {expected}, got {native.get(key)}")

        if native.get("descriptor_heap.unified_resource_stride") != "64":
            raise GateError("native B580 unified image/buffer resource stride is not 64")
        evidence = build_evidence(root, tools, icd, slang_library, metadata, native, spv_paths)
        digest = b3_bytes(evidence, root)
        if args.capture:
            (root / EVIDENCE).write_bytes(evidence)
            (root / SIDECAR).write_text(f"{digest}  {EVIDENCE.name}\n")
            print(f"\nM0.7 R4 RT descriptor-heap capture: PASS ({digest})", flush=True)
        else:
            if not (root / EVIDENCE).is_file() or not (root / SIDECAR).is_file():
                raise GateError("R4 reference evidence/sidecar is missing")
            if (root / EVIDENCE).read_bytes() != evidence:
                raise GateError("R4 regenerated evidence differs from committed/captured reference")
            if sidecar_digest(root / SIDECAR) != digest or b3_file(root / EVIDENCE, root) != digest:
                raise GateError("R4 sidecar/evidence digest mismatch")
            print(f"\nM0.7 R4 RT descriptor-heap verification: PASS ({digest})", flush=True)
        return 0
    except GateError as e:
        print(f"M0.7 R4 RT descriptor-heap gate: FAIL: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
