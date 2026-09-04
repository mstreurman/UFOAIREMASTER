# Slang Shader Compiler and `.rshader` Package Specification

**Status:** Implementation specification baseline  
**Related ADR:** ADR-022  
**Compiler baseline:** Slang v2026.17 (ADR-047)

## 1. Tool

Create:

```text
tools/ufo-shaderc
```

The build tool links against the pinned Slang compiler API.

Do not implement the authoritative compiler path by scraping `slangc` textual output or JSON.

The Slang API is used for:

```text
compilation
entry-point enumeration
reflection
layout validation
dependency collection
diagnostics
SPIR-V extraction
```

`slangc` may remain useful for developer experiments.

## 2. Production runtime

Production renderer loads `.rshader`.

It does not:

```text
compile Slang
invoke slangc
link libslang
parse source modules
run spirv-opt at startup
```

Developer hot reload means rebuilding `.rshader` externally, then reloading the package.

## 3. Compiler pin

Current toolchain pin:

```text
Slang v2026.17
```

As of the Baseline-039 verification date, v2026.17 is the latest upstream GitHub release. It is nevertheless treated as a fixed reproducibility pin for each baseline; updating again requires the explicit reproducibility/qualification steps below.

Exact accepted artifact:

```text
slang-2026.17-linux-x86_64-glibc-2.27.tar.gz
SHA-256 e8162da376858faf7d00dc9a94be52a8ff014d14c35c5f8e49c97688ec57bb7b
```

The exact release/tag and approved hash are also recorded by the third-party toolchain manifest.

A compiler update requires:

```text
toolchain manifest change
shader rebuild
ABI validation
B580 shader/pipeline benchmark
pipeline-binary cache invalidation
```

## 4. Target settings

Baseline compiler intent:

```text
target:
    SPIR-V

profile:
    spirv_1_6

Vulkan:
    1.4

layout:
    scalar

matrix layout:
    column-major

memory model:
    Vulkan memory model
```

`ufo-shaderc` must explicitly configure:

```text
SLANG_MATRIX_LAYOUT_COLUMN_MAJOR
```

(or the equivalent compiler option).

Do not rely on Slang's default matrix layout.

Release shader packages are optimized.

Developer packages retain useful source/debug identity but runtime behavior must not depend on embedded debug names.


## 4.1 Descriptor-heap compiler capability

Slang v2026.17 can lower descriptor handles to `SPV_EXT_descriptor_heap` when the `spvDescriptorHeapEXT` capability is requested. It also accepts direct:

```text
ResourceDescriptorHeap[index]
SamplerDescriptorHeap[index]
```

source syntax and supports explicit resource/sampler heap stride controls, including unified resource-heap stride mode.

ADR-045 / Baseline 036 accepts this compiler capability as the production binding path. Architecture 056/061/070/089 are the current heap ABI authorities; architecture 013 is superseded for production binding.

`ufo-shaderc` must prove the accepted descriptor-heap path on the pinned compiler before renderer-scale use:

```text
SPIR-V 1.6 + Vulkan 1.4 validation
spvDescriptorHeapEXT capability emission
resource-heap and sampler-heap direct indexing
non-uniform resource indexing correctness
ConstantBuffer / structured/storage buffer descriptor-type correctness
sampled/storage image correctness
acceleration-structure access required by RT pipelines
reflection/metadata detection of bindless heap use
column-major ABI invariants unchanged
```

The runtime must independently confirm `VK_EXT_descriptor_heap` on the actual B580 driver; compiler support alone is insufficient.

## 5. Validation

Every compiled SPIR-V module is passed through `spirv-val` using the Vulkan/SPIR-V environment matching the renderer target. The Fedora 44 reference toolchain currently provides SPIR-V Tools 2026.1; the locally executed DescriptorHeapEXT smoke passes:

```text
spirv-val --target-env vulkan1.4 <module.spv>
```

Newer SPIR-V Tools builds may expose explicit descriptor-layout validator options. When those options are present, the reference B580 values may be supplied as an additional static check:

```text
--buffer-descriptor-layout 64:64
--image-descriptor-layout 64:64
--sampler-descriptor-layout 32:32
```

Those optional CLI switches are **not** a Fedora-44/M0 dependency requirement. The authoritative runtime-layout qualification remains the native B580 descriptor-heap fixture using queried `VkPhysicalDeviceDescriptorHeapPropertiesEXT` values plus exact heap write/read behavior.

These are qualification-device values, not universal serialized shader ABI constants. Architecture 087 owns the descriptor-heap conformance fixture and the direct-AS exception.

Failure stops the content build.

`spirv-opt` may be evaluated later, but it is not a required separate optimizer if the pinned Slang path already emits suitable optimized SPIR-V.

## 6. Shader source organization

Baseline layout:

```text
shaders/
    abi/
        renderer_abi.slang

    common/
        math.slang
        color.slang
        pbr.slang
        geometry.slang
        rt_common.slang

    raster/
    compute/
    rt/
    post/
```

`renderer_abi.slang` owns the stable shader-visible ABI.

## 7. Stable renderer ABI content

At minimum:

```text
GpuMaterial
GpuInstance
GpuMesh / GpuMeshSection
GpuRtInstanceData
GpuRtGeometryData
GpuLight
GpuBonePalette
GpuDrawData
GpuBounds
GpuSkinningJob
GpuSceneRoot
FrameConstants
ViewConstants
GpuShaderRoot
ReSTIR reservoir ABI
DDGI metadata ABI
descriptor-heap handle definitions
```

Exact current core field order/sizes are owned by architecture 059 together with architecture 018 for `GpuMaterial`.

Architecture 057 owns ReSTIR/DDGI temporal metadata and architecture 056 owns the root/descriptor ABI.

Individual shaders import these definitions instead of redeclaring them.

## 8. Descriptor-heap ABI

Production shaders use direct heap indexing:

```text
ResourceDescriptorHeap[index]
SamplerDescriptorHeap[index]
```

Persistent content images and samplers use the fixed logical registries owned by architectures 061/089. Frame/pass sampled/storage resources use typed indices allocated from the active FrameContext resource-heap arena.

`GpuSceneRoot.frameTlasHeapIndex` carries the active FrameContext TLAS heap handle.

Large structured buffers remain BDA-addressed where previously specified.

Production direct-heap shader code must not declare ad-hoc Vulkan descriptor-set/binding numbers. Static binding mappings are reserved for an explicitly documented compatibility need, not the baseline shader style.

## 9. Reflection normalization

`ufo-shaderc` converts Slang reflection into a renderer-owned normalized metadata representation.

Do not serialize raw Slang object layouts/pointers.

Normalized reflection records:

```text
entry points
stages
descriptor-heap use / handle family
resource/sampler heap stride mode
push-data/root requirements
specialization constants
shader-visible struct sizes
member offsets
member sizes/alignments where exposed
required capabilities
```

## 10. C++ ABI generation

Generate:

```text
generated/renderer_shader_abi.hpp
generated/renderer_shader_abi_checks.hpp
```

The generated check file contains assertions such as:

```cpp
static_assert(sizeof(GpuMaterial) == 96);
static_assert(offsetof(GpuMaterial, roughnessFactor) == 64);
static_assert(sizeof(GpuRtInstanceData) == 32);
```

Exact assertions are generated from reflection rather than duplicated manually.

A mismatch is a build error.

## 11. Shader package identity

Shader package content identity includes:

```text
exact Slang version
compiler/tool build ID
target/profile
compiler options
shader ABI version
all imported source bytes
entry-point list
specialization schema
normalized reflection
SPIR-V bytes
```

Hash:

```text
BLAKE3-256
```

This hash is fed into pipeline description/pipeline-binary cache identity together with the exact `ShaderBindingAbiHash256` from architecture 061.

## 12. `.rshader` container

Magic:

```text
RSHD
```

Common asset-container header is followed by chunks.

Required chunks:

```text
META
ENTR
SPV0
REFL
DEPS
```

Optional/conditional chunks:

```text
PUSH
SPEC
RTGP
DBUG
NAME
```

## 13. META

Contains:

```text
shader package version
renderer shader ABI version
Slang version
ufo-shaderc build ID
SPIR-V target version
Vulkan target
ShaderBindingAbiHash256
```

## 14. ENTR

Entry-point table records:

```text
stable entry-point ID
name/string index
shader stage
SPIR-V module/chunk index
SPIR-V entry-point string
required subgroup-size policy if any
```

The runtime does not discover arbitrary entry points by parsing source/reflection.

## 15. SPV0

Contains one or more validated SPIR-V modules.

Each module is stored as native SPIR-V word data.

Module offsets are 4-byte aligned at minimum and container chunks remain 64-byte aligned.

## 16. REFL

Contains normalized renderer reflection.

Runtime uses this for:

```text
developer validation
shader-binding ABI compatibility checks
diagnostics
```

Production heap binding is renderer-owned and fixed by architecture 089; runtime does not derive a descriptor model from arbitrary reflection. Heap pipelines use a null Vulkan pipeline layout.

## 17. RTGP

RT package group table defines groups for the specialized pipeline.

Example reflection package:

```text
raygen:
    ReflectionRayGen

miss:
    ReflectionMiss

hit groups:
    OpaqueHit
    AlphaTestHit
```

The runtime should not infer hit-group intent from entry-point names.

## 18. Dependency table

`DEPS` contains stable dependencies:

```text
module virtual path
AssetId/source ID
content hash
```

Used by incremental builds and diagnostics.

## 19. Pipeline families

Baseline packages are specialized.

Examples:

```text
gbuffer.rshader
deferred-lighting.rshader
shadow-rt.rshader
reflection-rt.rshader
ddgi-rt.rshader
reflection-denoise.rshader
hdr-output.rshader
```

Do not create one renderer-wide uber package.

## 20. Permutations

Prefer:

```text
specialization constants
runtime material flags
separate genuinely different pipeline packages
```

over uncontrolled preprocessor permutation explosion.

A permutation must correspond to a measured architectural state difference.

## 21. Pipeline binary integration

Pipeline persistent identity contains:

```text
.rshader ContentHash256
ShaderBindingAbiHash256
pipeline description hash
device/driver identity
pipeline global key
renderer build ID
```

Changing the shader package automatically invalidates stale `VK_KHR_pipeline_binary` entries.

## 22. Failure policy

Runtime rejects a package for:

```text
unknown major version
content hash failure
wrong shader ABI version
unsupported required capability
missing required entry point
shader-binding ABI incompatibility
invalid chunk bounds/alignment
```

Do not attempt runtime recompilation to repair an invalid package.

## Instrumentation shader variants

ADR-027 permits specialized diagnostic shader packages compiled from the same shared Slang modules:

```text
Production
Visualization
Probe
```

Production RT payload/attribute sizes remain minimal.

Visualization/Probe variants may write expanded diagnostic data such as:

```text
RT participation masks
temporal rejection reasons
blocker/hit identity
sampled material/texture metadata
```

Shared ray/material helper functions are used so debug behavior matches production ray construction and material evaluation.

## Exact shader-root authority

Architecture 056 owns:

```text
GpuShaderRoot
descriptor-heap root/handle contract
per-FrameContext root lifetime
column-major Slang session configuration
```

Architecture 059 supersedes architecture 053 for the revised core GPU v1 semantic layouts.

Architecture 057 owns the exact ReSTIR/DDGI shader-visible temporal metadata.

## Descriptor-heap binding cache identity

Architecture 061/070 normalize and hash the shader-visible heap contract:

```text
descriptor-heap binding model
spvDescriptorHeapEXT requirement
unified resource-heap stride mode
GpuShaderRoot size/version
persistent sampled-image/sampler capacities
heap-handle semantic versions
```

A shader-visible binding ABI change invalidates package/pipeline-binary compatibility. Physical heap allocation size is runtime/tuning state and is not itself shader ABI.

## Target SPIR-V optimization comparison

Architecture 073 requires a bounded B580 comparison of:

```text
Slang optimized output
vs
Slang + selected spirv-opt pipeline
```

for representative raster/RT/compute/UI shaders.

No extra optimization stage is accepted unless SPIR-V validation/ABI/debugging remain correct and target pass/frame timing improves.

## Current acquisition closure

The compiler version is **Slang v2026.17** under ADR-047. The official `slang-2026.17-linux-x86_64-glibc-2.27.tar.gz` build-time artifact is pinned at SHA-256 `e8162da376858faf7d00dc9a94be52a8ff014d14c35c5f8e49c97688ec57bb7b`; source-build is fallback-only. The later 2026-09-04T12:02:48+02:00 readiness run confirms that exact artifact is hash-verified and provisioned at `tools/slang/v2026.17/`, reports `slangc` version `2026.17`, emits the DescriptorHeapEXT smoke module, and passes Fedora SPIR-V Tools 2026.1 Vulkan-1.4 validation.
