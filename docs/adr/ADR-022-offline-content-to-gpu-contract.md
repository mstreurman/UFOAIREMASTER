# ADR-022 — Offline Content-to-GPU Contract

**Status:** Accepted  
**Decision type:** Shader/content/runtime asset architecture  
**Primary target:** Fedora 44 / Intel Arc B580 / Vulkan 1.4  
**Related:** ADR-015, ADR-017, ADR-021

## Context

The remaster renderer is deliberately specialized for:

```text
Fedora 44
Intel Core i9-9900K
Intel Arc B580 / BMG G21
Vulkan 1.4
```

Runtime parsing of authoring formats would duplicate work, increase load-time complexity, complicate validation and make renderer behavior depend on toolchain libraries that should not ship with the game.

The renderer already has a stable GPU ABI based on:

```text
Slang/SPIR-V
descriptor heaps
Buffer Device Address
fixed material/scene structs
RT metadata
```

## Decision

All renderer-facing content is compiled offline into remaster runtime formats.

Production runtime does not parse or compile authoring formats.

Pipeline:

```text
authoring/source content
        |
        v
offline remaster compilers
        |
        +-- .rshader
        +-- .rmesh
        +-- .rskel
        +-- .ranim
        +-- .rmat
        +-- .rmap
        +-- .ktx2
        |
        v
runtime asset loader
        |
        v
GPU allocator / descriptor system / BLAS builder
```

## Shader compiler

Use a dedicated build tool:

```text
ufo-shaderc
```

linked against a pinned Slang compiler library.

Production `ufo` does not link Slang and performs no runtime shader compilation.

## Slang baseline

Initial pinned compiler:

```text
Slang v2026.17
```

Target:

```text
SPIR-V 1.6
Vulkan 1.4
Vulkan memory model
scalar block layout
column-major matrix layout
```

The compiler session explicitly selects column-major layout; it never relies on the Slang default.

The compiler version is part of every shader-package and pipeline-binary identity.

Changing Slang is an explicit toolchain upgrade, not an automatic "latest" dependency.

## Runtime file family

Use:

```text
.rshader
.rmesh
.rskel
.ranim
.rmat
.rmap
.rui
.ktx2
```

KTX2 remains a standard texture container.

Architecture 031 is the current runtime asset-family registry and may add accepted family members without changing this ADR's offline-content-to-GPU contract.

Custom `.r*` files share a common chunked little-endian container.

## Shader ABI authority

Slang reflection is authoritative for shader-visible struct layout and resource metadata.

Offline compilation generates C++ ABI assertions.

If C++ and shader layouts disagree, the build fails.

## Asset identity

Each remaster asset has:

```text
AssetId128
ContentHash256
```

`AssetId128` is derived deterministically from a normalized virtual asset path.

`ContentHash256` is BLAKE3-256 over compiled content or the defined canonical payload for that asset type.

## GPU allocation

Use a custom B580-specific Vulkan allocator.

Do not make VMA an architectural dependency.

Long-lived resources use suballocated free-list pools.

Frame/transient resources use linear arenas.

Buffer Device Address is a first-class allocation property.

## B580 memory features

The reference B580 exposes and uses:

```text
VK_EXT_memory_budget
```

The Mesa 26.2.2 B580 device section does not expose `VK_EXT_memory_priority` or `VK_EXT_pageable_device_local_memory`. Allocation/residency priority classes remain project-owned policy used to drive streaming, eviction and commitment decisions; they are not Vulkan memory-priority values on this target.

## Runtime authoring-format policy

Production runtime does not contain baseline importers for:

```text
glTF
OBJ
MD2/MD3
authoring image formats
Slang source
.map source
material authoring files
```

Conversion belongs to offline tools.

Legacy formats may still be read by migration/conversion tools.

## Consequences

- runtime files directly match renderer needs;
- shader ABI mismatches fail during build;
- pipeline cache identity is deterministic;
- map/mesh data is already RT-ready;
- runtime dependency count is reduced;
- asset format versioning becomes explicit;
- content rebuilds are reproducible and cacheable.

## Exact asset identity/hash authority

Architecture 066 owns exact NormalizeAssetPathV1, AssetId128, common `.r*` header/chunk, CRC, ContentHash and SourceHash.
