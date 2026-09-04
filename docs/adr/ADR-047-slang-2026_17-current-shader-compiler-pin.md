# ADR-047 — Slang v2026.17 Current Shader-Compiler Pin

**Status:** Accepted  
**Date:** 2026-09-04  
**Decision:** `DEPS-SLANG-001` current compiler identity  
**Supersedes:** ADR-041 for Slang release/artifact identity; preserves ADR-034 acquisition policy  
**Related:** ADR-022, ADR-029, ADR-045, architecture 029/056/087/089

## Context

The project policy is to use the latest deliberately verified Slang release for the descriptor-heap shader toolchain, while still pinning an exact release/artifact per documentation baseline for reproducibility.

During the Baseline-038 deep audit, upstream released Slang v2026.17 on 2026-09-04. The prior v2026.16.1 pin therefore became stale after Baseline 038 was packaged.

The v2026.17 release reports no breaking changes and retains the compiler features the project depends on for the heap-first Vulkan renderer:

```text
SPIR-V target / spirv_1_6
spvDescriptorHeapEXT capability
ResourceDescriptorHeap[]
SamplerDescriptorHeap[]
SPIRVResourceHeapStride
SPIRVSamplerHeapStride
SPIRVUnifiedDescriptorHeapStride
reflection/compiler API used by ufo-shaderc
```

The project adopts it as the current compiler baseline and re-runs the descriptor-heap/reflection/ABI fixtures rather than assuming compatibility merely because the release reports no breaking changes.

## Decision

Pin the project shader compiler to:

```text
release: v2026.17
release commit: 5bcb1c031b7873444f745b757a35e25567bbe043
artifact: slang-2026.17-linux-x86_64-glibc-2.27.tar.gz
SHA-256: e8162da376858faf7d00dc9a94be52a8ff014d14c35c5f8e49c97688ec57bb7b
license: Apache-2.0 WITH LLVM-exception
runtime game dependency: NO
```

The exact artifact is a build-time tool input. It is not linked as a required shipped-game runtime dependency.

## Local installation state

The broad workstation capture at `2026-09-04T10:41:03+02:00` correctly recorded that shader `slangc` was not yet provisioned at that time. A later explicit provisioning/readiness run on the same workstation supersedes that installation-state observation:

```text
project tool cache: tools/slang/v2026.17/
slangc: tools/slang/v2026.17/bin/slangc
reported version: 2026.17
artifact SHA-256 verification: PASS
Vulkan header/link descriptor-heap smoke: PASS
Slang DescriptorHeapEXT SPIR-V emission: PASS
spirv-val --target-env vulkan1.4: PASS
DescriptorHeapEXT ResourceHeapEXT/SamplerHeapEXT inspection: PASS
conventional DescriptorSet/Binding decorations in heap fixture: NONE
```

The installed Fedora RPM named `slang-2.3.3-9.fc44.x86_64` remains the unrelated S-Lang terminal/programming library and does **not** satisfy this dependency. The project-local v2026.17 tool cache is the authoritative shader-Slang installation for M0.

## Required upgrade invalidation and validation

Moving from v2026.16.1 to v2026.17 requires:

```text
invalidate/rebuild all .rshader packages by compiler identity
invalidate dependent pipeline-binary caches
regenerate normalized reflection/C++ ABI checks
run column-major layout fixture
run SPIR-V validation for all package variants
run architecture-087 descriptor-heap fixtures
run B580 shader/pipeline timing qualification
record exact compiler identity in the build manifest
```

Architecture 087/089 remain authoritative for the production descriptor-heap ABI. A compiler update does not authorize a descriptor-buffer fallback or an undocumented shader-binding ABI change.

## Future updates

“Use latest Slang” does not mean ordinary builds follow a moving tag. A future release becomes current only after its release artifact/hash are recorded and the same ABI/conformance/benchmark qualification is performed in a new baseline.
