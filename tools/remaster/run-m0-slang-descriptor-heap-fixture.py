#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

BASELINE_REVISION = "386e2bd1aa840f1194a8b7fcaeb189bcff5ba46b"
R2_EVIDENCE_B3 = "a31f501b96a5cc3467a67c8025a4f7ca585c47fa94c1887c4469c7595c59e594"
R2_EVIDENCE_REL = Path("docs/reference/reference-m0-descriptor-heap.txt")
R2_SIDECAR_REL = Path("docs/reference/reference-m0-descriptor-heap.b3")

FIXTURE_DIR_REL = Path("tools/remaster/slang_descriptor_heap_fixture")
FIXTURE_CMAKE_REL = FIXTURE_DIR_REL / "CMakeLists.txt"
FIXTURE_CPP_REL = FIXTURE_DIR_REL / "slang_descriptor_heap_api.cpp"
FIXTURE_SHADER_REL = FIXTURE_DIR_REL / "slang_descriptor_heap_fixture.slang"
RUNNER_REL = Path("tools/remaster/run-m0-slang-descriptor-heap-fixture.py")
REFERENCE_DOC_REL = Path("docs/reference/reference-m0-slang-descriptor-heap.md")
EVIDENCE_REL = Path("docs/reference/reference-m0-slang-descriptor-heap.txt")
SIDECAR_REL = Path("docs/reference/reference-m0-slang-descriptor-heap.b3")
BUILD_REL = Path("build-m0-slang-descriptor-heap-f44")
SLANG_ROOT_REL = Path("tools/slang/v2026.17")

ABI_DOMAIN = b"UFOAIREMASTER:ShaderBindingABI:v2\0"
CONTENT_DOMAIN = b"UFOAIREMASTER:ContentHash:v1\0"
TOOLCHAIN_DOMAIN = b"UFOAIREMASTER:ToolchainConfig:v1\0"
SOURCE_DOMAIN = b"UFOAIREMASTER:SourceHash:v1\0"
RSHADER_MAGIC = b"RSHD"
CHUNK_ORDER = (b"META", b"ENTR", b"SPV0", b"REFL", b"DEPS", b"NAME")


class GateError(RuntimeError):
    pass


def run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None,
        check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(args), flush=True)
    proc = subprocess.run(
        args, cwd=cwd, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n", flush=True)
    if check and proc.returncode != 0:
        raise GateError(f"command failed ({proc.returncode}): {' '.join(args)}")
    return proc


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        raise GateError("not inside a Git work tree")
    return Path(proc.stdout.strip()).resolve()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def b3_bytes(root: Path, data: bytes) -> str:
    proc = subprocess.run(
        ["b3sum"], cwd=root, input=data,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        raise GateError(f"b3sum failed: {proc.stderr.decode(errors='replace')}")
    parts = proc.stdout.decode().strip().split()
    if not parts:
        raise GateError("b3sum produced no digest")
    return parts[0]


def b3_file(root: Path, path: Path) -> str:
    return b3_bytes(root, path.read_bytes())


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise GateError(f"required tool is missing: {name}")
    return path


def sidecar_digest(path: Path) -> str:
    parts = path.read_text(encoding="utf-8").strip().split()
    if not parts:
        raise GateError(f"empty sidecar: {path}")
    return parts[0]


def verify_r2(root: Path) -> None:
    evidence = root / R2_EVIDENCE_REL
    sidecar = root / R2_SIDECAR_REL
    if not evidence.is_file() or not sidecar.is_file():
        raise GateError("R2 descriptor-heap evidence is missing")
    if sidecar_digest(sidecar) != R2_EVIDENCE_B3:
        raise GateError("R2 evidence sidecar identity does not match accepted R2 gate")
    actual = b3_file(root, evidence)
    if actual != R2_EVIDENCE_B3:
        raise GateError(f"R2 evidence digest mismatch: {actual}")
    print(f"M0.7 R2 evidence verification: PASS ({actual})", flush=True)


def require_baseline(root: Path) -> None:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_REVISION, "HEAD"],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if proc.returncode != 0:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        raise GateError(f"HEAD {head} is not a descendant of R2 baseline {BASELINE_REVISION}")
    src_delta = subprocess.check_output(
        ["git", "diff", "--name-only", BASELINE_REVISION, "--", "src"],
        cwd=root, text=True).strip()
    src_status = subprocess.check_output(
        ["git", "status", "--porcelain", "--", "src"], cwd=root, text=True).strip()
    if src_delta or src_status:
        raise GateError("R3 must not change canonical/production src/")


def find_slang_distribution(root: Path) -> tuple[Path, Path, Path, Path]:
    slang_root = root / SLANG_ROOT_REL
    slangc = slang_root / "bin" / "slangc"
    include_dir = slang_root / "include"
    header = include_dir / "slang.h"
    comptr = include_dir / "slang-com-ptr.h"
    if not slangc.is_file() or not os.access(slangc, os.X_OK):
        raise GateError(f"pinned Slang compiler missing: {slangc}")
    if not header.is_file() or not comptr.is_file():
        raise GateError(
            "R3 requires the full pinned Slang v2026.17 distribution, including include/slang.h "
            "and include/slang-com-ptr.h. Re-provision the accepted v2026.17 distribution; "
            "do not substitute system Slang headers.")
    candidates = []
    for libdir in (slang_root / "lib", slang_root / "lib64", slang_root / "bin"):
        for name in ("libslang-compiler.so", "libslang.so"):
            path = libdir / name
            if path.is_file():
                candidates.append(path)
    if not candidates:
        raise GateError(
            "R3 requires the pinned Slang compiler API shared library "
            "(libslang-compiler.so or compatibility libslang.so) in the v2026.17 distribution")
    library = candidates[0]
    return slang_root, slangc, header, library


def isolated_env(build: Path) -> dict[str, str]:
    state = build / "qualification-state"
    home = state / "home"
    xdg_cache = state / "xdg-cache"
    xdg_config = state / "xdg-config"
    xdg_data = state / "xdg-data"
    for path in (home, xdg_cache, xdg_config, xdg_data):
        path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "HOME": str(home),
        "XDG_CACHE_HOME": str(xdg_cache),
        "XDG_CONFIG_HOME": str(xdg_config),
        "XDG_DATA_HOME": str(xdg_data),
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
    })
    return env


def parse_kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise GateError(f"non key=value metadata line: {raw!r}")
        key, value = line.split("=", 1)
        if key in out:
            raise GateError(f"duplicate metadata key: {key}")
        out[key] = value
    return out


def require_metadata(meta: dict[str, str]) -> None:
    expected = {
        "metadata.schema": "1",
        "target.format": "SPIRV",
        "target.profile": "spirv_1_6",
        "target.vulkan": "vulkan1.4",
        "target.capability.spvDescriptorHeapEXT": "true",
        "target.capability.vk_mem_model": "true",
        "target.fixture_profile_capabilities": (
            "SPV_GOOGLE_user_type,spvDerivativeControl,spvImageQuery,spvImageGatherExtended,"
            "spvSparseResidency,spvMinLod,spvFragmentFullyCoveredEXT"
        ),
        "target.scalar_layout": "true",
        "target.matrix_default": "column-major",
        "target.resource_heap_stride": "0",
        "target.sampler_heap_stride": "0",
        "target.unified_resource_heap_stride": "true",
        "target.optimization": "maximal",
        "reflection.uses_bindless_resource_heap": "true",
        "reflection.root.size": "32",
        "reflection.root.field_count": "4",
        "reflection.root.offsets": "0,8,16,24",
        "reflection.matrix_probe.offsets": "0,64,76",
        "reflection.matrix.layout": "column-major",
    }
    for key, value in expected.items():
        actual = meta.get(key)
        if actual != value:
            raise GateError(f"metadata mismatch {key}: expected {value!r}, got {actual!r}")
    if not meta.get("slang.version", "").startswith("2026.17"):
        raise GateError(f"Slang API version is not pinned v2026.17: {meta.get('slang.version')!r}")
    if int(meta.get("reflection.matrix_probe.size", "0")) < 80:
        raise GateError("MatrixAbiProbe reflected size is unexpectedly smaller than 80 bytes")


def require_spirv_semantics(disasm: str) -> None:
    required = (
        'OpExtension "SPV_EXT_descriptor_heap"',
        "OpCapability DescriptorHeapEXT",
        "BuiltIn ResourceHeapEXT",
        "BuiltIn SamplerHeapEXT",
        "OpUntypedAccessChainKHR",
        "OpConstantSizeOfEXT",
        "ArrayStrideIdEXT",
        "OpSpecConstantOp %bool UGreaterThan",
        "OpSpecConstantOp %uint Select",
        'OpEntryPoint GLCompute',
    )
    for token in required:
        if token not in disasm:
            raise GateError(f"SPIR-V is missing required descriptor-heap token: {token}")
    if " DescriptorSet " in disasm or " Binding " in disasm:
        bad = [line for line in disasm.splitlines() if " DescriptorSet " in line or " Binding " in line]
        raise GateError("direct heap SPIR-V contains DescriptorSet/Binding decorations:\n" + "\n".join(bad[:20]))
    memory_lines = [line.strip() for line in disasm.splitlines() if "OpMemoryModel" in line]
    if len(memory_lines) != 1 or "Vulkan" not in memory_lines[0]:
        raise GateError(f"expected exactly one Vulkan memory model, got: {memory_lines}")
    # Under DescriptorHeapEXT heap accesses are non-uniform by default; an emitted NonUniform
    # decoration is not required and is deliberately not asserted either way.
    if "AccelerationStructure" in disasm or "RayQuery" in disasm or "TraceRay" in disasm:
        raise GateError("R3 shader unexpectedly contains acceleration-structure/ray operations reserved for R4")


def le_u32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def le_u64(value: int) -> bytes:
    return struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)


def fourcc(raw: bytes) -> int:
    if len(raw) != 4:
        raise ValueError(raw)
    return int.from_bytes(raw, "little")


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def crc32c(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0x82F63B78 if (crc & 1) else 0)
    return crc ^ 0xFFFFFFFF


def binding_abi_hash(root: Path) -> str:
    values = [
        2,          # bindingAbiVersion
        1,          # bindingModel = VK_EXT_descriptor_heap
        32,         # rootSizeBytes
        1,          # rootVersion
        65536,      # sampledImageCapacity
        256,        # samplerCapacity
        0xFFFFFFFF, # invalidHandle
        1,          # tlasHandleSemanticVersion
        1,          # slangSpvDescriptorHeapEXT
        1,          # unifiedResourceHeapStride
        0,          # explicitResourceStrideBytes
        0,          # explicitSamplerStrideBytes
        *([0] * 8),
    ]
    stream = ABI_DOMAIN + b"".join(le_u32(v) for v in values)
    return b3_bytes(root, stream)


def canonical_manifest(records: dict[str, str]) -> bytes:
    out = bytearray()
    for key in sorted(records, key=lambda x: x.encode("utf-8")):
        kb = key.encode("utf-8")
        vb = records[key].encode("utf-8")
        out += le_u32(len(kb)) + kb + le_u32(len(vb)) + vb
    return bytes(out)


def source_hash(root: Path, shader_rel: Path, shader_bytes: bytes, slang_version: str) -> tuple[str, str, str]:
    toolchain_records = {
        "binding_abi": "ShaderBindingABI:v2",
        "matrix_layout": "column-major",
        "optimization": "maximal",
        "scalar_block_layout": "true",
        "slang.api": "linked",
        "slang.version": slang_version,
        "spirv.profile": "spirv_1_6",
        "spirv.fixture_profile_capabilities": (
            "SPV_GOOGLE_user_type,spvDerivativeControl,spvImageQuery,spvImageGatherExtended,"
            "spvSparseResidency,spvMinLod,spvFragmentFullyCoveredEXT"
        ),
        "spirv.resource_heap_stride": "0",
        "spirv.sampler_heap_stride": "0",
        "spirv.spvDescriptorHeapEXT": "true",
        "spirv.unified_resource_heap_stride": "true",
        "vulkan.memory_model": "true",
        "vulkan.target": "1.4",
    }
    toolchain_hash = b3_bytes(root, TOOLCHAIN_DOMAIN + canonical_manifest(toolchain_records))
    raw_hash = b3_bytes(root, shader_bytes)
    normalized = shader_rel.as_posix().encode("ascii")
    stream = bytearray(SOURCE_DOMAIN)
    stream += le_u32(1)
    stream += le_u32(len(normalized)) + normalized
    stream += bytes.fromhex(toolchain_hash)
    stream += le_u32(1)
    stream += le_u32(len(normalized)) + normalized + bytes.fromhex(raw_hash)
    source = b3_bytes(root, bytes(stream))
    return source, toolchain_hash, raw_hash


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def make_name_table(strings: list[str]) -> tuple[bytes, dict[str, int]]:
    unique: list[str] = []
    for value in strings:
        if value not in unique:
            unique.append(value)
    mapping = {value: i for i, value in enumerate(unique)}
    return b"".join(s.encode("utf-8") + b"\0" for s in unique), mapping


def build_rshader(
    root: Path,
    output: Path,
    spv: bytes,
    normalized_meta: dict[str, str],
    shader_rel: Path,
    shader_bytes: bytes,
) -> dict[str, str]:
    slang_version = normalized_meta["slang.version"]
    abi_hash = binding_abi_hash(root)
    source_digest, toolchain_hash, raw_source_hash = source_hash(
        root, shader_rel, shader_bytes, slang_version)

    name_payload, names = make_name_table([
        "computeMain",
        slang_version,
        "ufo-shaderc-r3-fixture-v1",
        "spirv_1_6",
        "vulkan1.4",
    ])

    required_caps = (
        (1 << 0)  # DescriptorHeap
        | (1 << 1)  # BufferDeviceAddress baseline binding ABI
        | (1 << 4)  # ScalarBlockLayout
        | (1 << 5)  # VulkanMemoryModel
        | (1 << 11) # ShaderUntypedPointers
    )
    meta_payload = struct.pack(
        "<8I32sQ24s",
        1,  # shaderPackageVersion
        2,  # rendererShaderAbiVersion / ShaderBindingABI v2 generation
        2,  # metaVersion
        names[slang_version],
        names["ufo-shaderc-r3-fixture-v1"],
        names["spirv_1_6"],
        names["vulkan1.4"],
        0,
        bytes.fromhex(abi_hash),
        required_caps,
        bytes(24),
    )
    if len(meta_payload) != 96:
        raise GateError(f"RshaderMetaV2 size is {len(meta_payload)}, expected 96")

    entry_payload = canonical_json({
        "entryPointId": 0,
        "nameStringIndex": names["computeMain"],
        "shaderStage": "compute",
        "spirvChunk": "SPV0",
        "spirvEntryPoint": "computeMain",
        "requiredSubgroupSize": None,
    })
    refl_payload = canonical_json({
        "bindingModel": "VK_EXT_descriptor_heap",
        "descriptorHeap": True,
        "matrixDefault": "column-major",
        "rootOffsets": [0, 8, 16, 24],
        "rootSize": 32,
        "scalarBlockLayout": True,
        "sourceNonUniformPolicy": "divergent heap indices explicitly marked",
        "targetMetadataUsesBindlessResourceHeap": True,
        "unifiedImageBufferResourceStride": True,
        "vulkanMemoryModel": True,
    })
    deps_payload = canonical_json({
        "primary": shader_rel.as_posix(),
        "rawSourceHash256": raw_source_hash,
        "sourceHash256": source_digest,
        "toolchainConfigHash256": toolchain_hash,
    })

    payloads = {
        b"META": meta_payload,
        b"ENTR": entry_payload,
        b"SPV0": spv,
        b"REFL": refl_payload,
        b"DEPS": deps_payload,
        b"NAME": name_payload,
    }

    content_stream = bytearray(CONTENT_DOMAIN)
    content_stream += RSHADER_MAGIC + struct.pack("<HHII", 1, 0, 0, len(CHUNK_ORDER))
    for kind in CHUNK_ORDER:
        payload = payloads[kind]
        content_stream += le_u32(fourcc(kind)) + le_u32(0) + le_u64(len(payload)) + payload
    content_hash = b3_bytes(root, bytes(content_stream))

    table_offset = 128
    table_size = len(CHUNK_ORDER) * 48
    cursor = align_up(table_offset + table_size, 64)
    descriptors: list[tuple[bytes, int, int, int]] = []
    for kind in CHUNK_ORDER:
        cursor = align_up(cursor, 64)
        payload = payloads[kind]
        descriptors.append((kind, cursor, len(payload), crc32c(payload)))
        cursor += len(payload)
    file_size = cursor

    data = bytearray(file_size)
    header = bytearray(128)
    header[0:4] = RSHADER_MAGIC
    struct.pack_into("<HHIIQQ", header, 4, 1, 0, 0, len(CHUNK_ORDER), file_size, table_offset)
    header[32:64] = bytes.fromhex(content_hash)
    header[64:96] = bytes.fromhex(source_digest)
    data[:128] = header

    table = bytearray()
    for kind, offset, size, crc in descriptors:
        table += struct.pack("<IIQQQIIQ", fourcc(kind), 0, offset, size, size, 64, crc, 0)
        data[offset:offset + size] = payloads[kind]
    data[table_offset:table_offset + len(table)] = table
    output.write_bytes(data)

    return {
        "binding_abi_blake3_256": abi_hash,
        "content_blake3_256": content_hash,
        "source_blake3_256": source_digest,
        "toolchain_config_blake3_256": toolchain_hash,
        "raw_source_blake3_256": raw_source_hash,
        "package_sha256": sha256_file(output),
        "package_blake3_256": b3_file(root, output),
        "package_size": str(file_size),
    }


def verify_rshader(root: Path, path: Path, expected: dict[str, str]) -> None:
    data = path.read_bytes()
    if len(data) < 128 or data[:4] != RSHADER_MAGIC:
        raise GateError("invalid RSHD common header")
    major, minor, flags, count, file_size, table_offset = struct.unpack_from("<HHIIQQ", data, 4)
    if (major, minor, flags, count, file_size, table_offset) != (1, 0, 0, 6, len(data), 128):
        raise GateError("unexpected RSHD common header fields")
    if data[96:128] != bytes(32):
        raise GateError("RSHD reserved header bytes are not zero")
    if data[32:64].hex() != expected["content_blake3_256"]:
        raise GateError("RSHD content hash header mismatch")
    if data[64:96].hex() != expected["source_blake3_256"]:
        raise GateError("RSHD source hash header mismatch")

    seen: list[bytes] = []
    parsed_payloads: dict[bytes, bytes] = {}
    for i in range(count):
        off = table_offset + i * 48
        t, cflags, p_off, stored, uncomp, alignment, crc, reserved = struct.unpack_from("<IIQQQIIQ", data, off)
        kind = t.to_bytes(4, "little")
        seen.append(kind)
        if cflags != 0 or stored != uncomp or alignment != 64 or reserved != 0:
            raise GateError(f"invalid chunk descriptor for {kind!r}")
        if p_off % 64 != 0 or p_off + stored > len(data):
            raise GateError(f"invalid chunk placement for {kind!r}")
        payload = data[p_off:p_off + stored]
        parsed_payloads[kind] = payload
        if crc32c(payload) != crc:
            raise GateError(f"CRC32C mismatch for {kind!r}")
        if kind == b"META":
            if len(payload) != 96:
                raise GateError("META v2 is not 96 bytes")
            values = struct.unpack("<8I32sQ24s", payload)
            if values[0:3] != (1, 2, 2):
                raise GateError("META version tuple mismatch")
            if values[7] != 0 or values[10] != bytes(24):
                raise GateError("META reserved fields are nonzero")
            if values[8].hex() != expected["binding_abi_blake3_256"]:
                raise GateError("META ShaderBindingAbiHash256 mismatch")
    if tuple(seen) != CHUNK_ORDER:
        raise GateError(f"noncanonical chunk order: {seen}")
    content_stream = bytearray(CONTENT_DOMAIN)
    content_stream += RSHADER_MAGIC + struct.pack("<HHII", major, minor, flags, count)
    for kind in CHUNK_ORDER:
        payload = parsed_payloads[kind]
        content_stream += le_u32(fourcc(kind)) + le_u32(0) + le_u64(len(payload)) + payload
    recomputed = b3_bytes(root, bytes(content_stream))
    if recomputed != data[32:64].hex():
        raise GateError("independently recomputed RSHD ContentHash256 mismatch")


def evidence_bytes(
    root: Path,
    tool_versions: dict[str, str],
    slang_header: Path,
    slang_library: Path,
    spv: Path,
    metadata_path: Path,
    package: Path,
    package_info: dict[str, str],
) -> bytes:
    records: list[tuple[str, str]] = []
    add = records.append
    add(("schema.version", "1"))
    add(("baseline.r2_revision", BASELINE_REVISION))
    add(("baseline.r2_evidence_blake3_256", R2_EVIDENCE_B3))
    for key in sorted(tool_versions):
        add((f"tool.{key}", tool_versions[key]))
    for label, rel in (
        ("fixture_cmake", FIXTURE_CMAKE_REL),
        ("fixture_cpp", FIXTURE_CPP_REL),
        ("fixture_shader", FIXTURE_SHADER_REL),
        ("runner", RUNNER_REL),
        ("reference_doc", REFERENCE_DOC_REL),
    ):
        add((f"input.{label}.sha256", sha256_file(root / rel)))
    add(("slang.api_header.sha256", sha256_file(slang_header)))
    add(("slang.api_library.sha256", sha256_file(slang_library)))
    add(("compile.api_linked", "PASS"))
    add(("compile.user_state", "isolated"))
    add(("compile.profile", "spirv_1_6"))
    add((
        "compile.fixture_profile_capabilities",
        "SPV_GOOGLE_user_type,spvDerivativeControl,spvImageQuery,spvImageGatherExtended,"
        "spvSparseResidency,spvMinLod,spvFragmentFullyCoveredEXT",
    ))
    add(("compile.diagnostics", "clean"))
    add(("compile.vulkan_target", "1.4"))
    add(("compile.capability.spvDescriptorHeapEXT", "PASS"))
    add(("compile.scalar_block_layout", "PASS"))
    add(("compile.vulkan_memory_model", "PASS"))
    add(("compile.matrix_default", "column-major"))
    add(("compile.resource_heap_stride", "0"))
    add(("compile.sampler_heap_stride", "0"))
    add(("compile.unified_resource_heap_stride", "PASS"))
    add(("reflection.target_metadata_heap_use", "PASS"))
    add(("reflection.root_size_32", "PASS"))
    add(("reflection.root_offsets", "0,8,16,24"))
    add(("reflection.matrix_column_major", "PASS"))
    add(("spirv.validation_vulkan1_4", "PASS"))
    add(("spirv.extension_spv_ext_descriptor_heap", "PASS"))
    add(("spirv.descriptor_set_binding_absent", "PASS"))
    add(("spirv.resource_sampler_heap_builtins", "PASS"))
    add(("spirv.unified_image_buffer_stride", "PASS"))
    add(("spirv.acceleration_structure_scope", "DEFERRED-R4"))
    add(("spirv.sha256", sha256_file(spv)))
    add(("normalized_metadata.sha256", sha256_file(metadata_path)))
    for key in sorted(package_info):
        add((f"rshader.{key}", package_info[key]))
    add(("rshader.common_header", "PASS"))
    add(("rshader.chunk_order", "META,ENTR,SPV0,REFL,DEPS,NAME"))
    add(("rshader.meta_v2_size", "96"))
    add(("rshader.repeatability", "PASS"))
    add(("source.src_delta_from_r2", "none"))
    add(("production.behavior_replacement", "none"))
    add(("result", "PASS"))
    text = "ufoai-remaster-m0-slang-descriptor-heap-v1\n" + "".join(f"{k}={v}\n" for k, v in records)
    return text.encode("utf-8")


def execute(root: Path) -> bytes:
    print("=== M0.7 R3 SLANG SPV_EXT_descriptor_heap ABI/REFLECTION/PACKAGE FIXTURE ===", flush=True)
    require_baseline(root)
    verify_r2(root)

    cmake = require_tool("cmake")
    ninja = require_tool("ninja")
    spirv_val = require_tool("spirv-val")
    spirv_dis = require_tool("spirv-dis")
    require_tool("b3sum")
    slang_root, slangc, slang_header, slang_library = find_slang_distribution(root)

    tool_versions: dict[str, str] = {}
    for key, cmd in (
        ("cmake", [cmake, "--version"]),
        ("ninja", [ninja, "--version"]),
        ("slangc", [str(slangc), "-version"]),
        ("spirv_val", [spirv_val, "--version"]),
        ("spirv_dis", [spirv_dis, "--version"]),
    ):
        proc = run(cmd, cwd=root)
        tool_versions[key] = " | ".join(line.strip() for line in proc.stdout.splitlines() if line.strip())
    if "2026.17" not in tool_versions["slangc"]:
        raise GateError("slangc is not pinned v2026.17")

    build = root / BUILD_REL
    if build.exists():
        shutil.rmtree(build)

    print("\n=== CLEAN API-LINKED FIXTURE CONFIGURE ===", flush=True)
    run([
        cmake, "-S", str(root / FIXTURE_DIR_REL), "-B", str(build), "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo", f"-DSLANG_ROOT={slang_root}",
    ], cwd=root)

    print("\n=== CLEAN API-LINKED FIXTURE BUILD ===", flush=True)
    run([cmake, "--build", str(build), "--parallel", "8"], cwd=root)

    api_binary = build / "m0_slang_descriptor_heap_api"
    spv = build / "slang_descriptor_heap_fixture.spv"
    metadata_path = build / "slang_descriptor_heap_fixture.metadata.txt"
    source = root / FIXTURE_SHADER_REL

    print("\n=== PINNED SLANG API COMPILE + TARGET METADATA ===", flush=True)
    api_run = run([
        str(api_binary), "--source", str(source), "--entry", "computeMain",
        "--spv", str(spv), "--metadata", str(metadata_path),
    ], cwd=root, env=isolated_env(build))
    if "slang.api_linked=true" not in api_run.stdout or "result=PASS" not in api_run.stdout:
        raise GateError("Slang API fixture did not report PASS")
    diagnostic_lines = []
    for line in api_run.stdout.splitlines():
        lowered = line.lstrip().lower()
        if (
            lowered.startswith("warning[")
            or lowered.startswith("warning:")
            or lowered.startswith("error[")
            or lowered.startswith("error:")
        ):
            diagnostic_lines.append(line)
    if diagnostic_lines:
        raise GateError(
            "Slang emitted warning/error diagnostics under the explicit R3 profile:\n"
            + "\n".join(diagnostic_lines[:20])
        )
    meta = parse_kv(metadata_path.read_text(encoding="utf-8"))
    require_metadata(meta)

    print("\n=== SPIR-V 1.6 / VULKAN 1.4 VALIDATION ===", flush=True)
    run([spirv_val, "--target-env", "vulkan1.4", str(spv)], cwd=root)
    dis = run([spirv_dis, str(spv)], cwd=root).stdout
    require_spirv_semantics(dis)
    print("direct descriptor-heap SPIR-V semantic gate: PASS", flush=True)

    print("\n=== DETERMINISTIC .rshader PACKAGE ===", flush=True)
    package1 = build / "descriptor_heap_fixture-a.rshader"
    package2 = build / "descriptor_heap_fixture-b.rshader"
    info1 = build_rshader(root, package1, spv.read_bytes(), meta, FIXTURE_SHADER_REL, source.read_bytes())
    info2 = build_rshader(root, package2, spv.read_bytes(), meta, FIXTURE_SHADER_REL, source.read_bytes())
    verify_rshader(root, package1, info1)
    verify_rshader(root, package2, info2)
    if package1.read_bytes() != package2.read_bytes() or info1 != info2:
        raise GateError("repeated .rshader package build is not byte-identical")
    print(f"rshader.package_sha256={info1['package_sha256']}")
    print(f"rshader.binding_abi_blake3_256={info1['binding_abi_blake3_256']}")
    print("deterministic .rshader package: PASS", flush=True)

    return evidence_bytes(root, tool_versions, slang_header, slang_library, spv, metadata_path, package1, info1)


def main() -> int:
    parser = argparse.ArgumentParser(description="UFOAIREMASTER M0.7 R3 Slang descriptor-heap gate")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--capture", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    try:
        root = repo_root()
        evidence = execute(root)
        digest = b3_bytes(root, evidence)
        evidence_path = root / EVIDENCE_REL
        sidecar_path = root / SIDECAR_REL

        if args.capture:
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_bytes(evidence)
            sidecar_path.write_text(f"{digest}  {EVIDENCE_REL.name}\n", encoding="utf-8")
            print(f"\nM0.7 R3 Slang descriptor-heap capture: PASS ({digest})")
            return 0

        if not evidence_path.is_file() or not sidecar_path.is_file():
            raise GateError("R3 reference evidence is missing; run --capture first")
        stored = evidence_path.read_bytes()
        stored_sidecar = sidecar_digest(sidecar_path)
        if stored != evidence:
            raise GateError("R3 regenerated evidence differs from stored reference")
        if stored_sidecar != digest:
            raise GateError(f"R3 sidecar digest mismatch: stored {stored_sidecar}, regenerated {digest}")
        print(f"\nM0.7 R3 Slang descriptor-heap verification: PASS ({digest})")
        return 0
    except GateError as e:
        print(f"M0.7 R3 Slang descriptor-heap gate: FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
