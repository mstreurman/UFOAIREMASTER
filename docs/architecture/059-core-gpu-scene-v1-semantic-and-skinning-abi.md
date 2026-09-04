# Core GPU Scene v1 Semantic and Skinning ABI Closure

**Status:** Exact implementation specification  
**Related ADR:** ADR-017, ADR-021, ADR-029  
**Supersedes for core struct layout:** architecture 053 sections 3–14

## 1. Common sentinel

```cpp
constexpr uint32_t kInvalidGpuIndex = 0xffffffffu;
```

Reserved fields/bits are written as zero.


## 2. `GpuAffine3x4Rows`

```cpp
struct GpuAffine3x4Rows {
    float row0[4];
    float row1[4];
    float row2[4];
};

static_assert(sizeof(GpuAffine3x4Rows) == 48);
```

Semantic transform interpretation is owned by architecture 051.

## 3. `GpuBounds`

```cpp
struct GpuBounds {
    float minPu[4];
    float maxPu[4];
};

static_assert(sizeof(GpuBounds) == 32);
```

XYZ are presentation units.

`w` components are reserved zero.

## 4. `GpuSceneRoot`

```cpp
struct GpuSceneRoot {
    uint64_t instances;
    uint64_t meshes;
    uint64_t materials;
    uint64_t lights;
    uint64_t bonePalettes;
    uint64_t drawData;
    uint64_t rtInstanceData;
    uint64_t rtGeometryData;
    uint64_t bounds;
    uint64_t skinningJobs;
    uint64_t ddgiVolumes;
    uint64_t ddgiProbeMetadata;

    uint32_t instanceCount;
    uint32_t meshCount;
    uint32_t materialCount;
    uint32_t lightCount;
    uint32_t bonePaletteCount;
    uint32_t drawCount;
    uint32_t rtInstanceCount;
    uint32_t rtGeometryCount;
    uint32_t boundsCount;
    uint32_t skinningJobCount;
    uint32_t ddgiVolumeCount;
    uint32_t ddgiProbeCount;

    uint32_t frameTlasHeapIndex;
    uint32_t reserved1;
    uint32_t reserved2;
    uint32_t reserved3;
};

static_assert(sizeof(GpuSceneRoot) == 160);
```

All addresses/counts are coherent for one active FrameContext root.

`frameTlasHeapIndex` is the active FrameContext's typed `ResourceDescriptorHeap` index for `RaytracingAccelerationStructure`. Its exact Slang/Vulkan publication representation is qualified by architectures 087/089 before RT production use. `0xffffffff` means no valid TLAS handle and is forbidden for passes that trace rays.

## 5. `GpuInstance`

```cpp
struct GpuInstance {
    GpuAffine3x4Rows currentWorldFromObject;
    GpuAffine3x4Rows previousWorldFromObject;

    uint32_t meshIndex;
    uint32_t materialOverrideIndex;
    uint32_t renderObjectId;
    uint32_t flags;

    uint32_t bonePaletteIndex;
    uint32_t reserved0;
    uint32_t rtInstanceDataIndex;
    uint32_t skinningJobIndex;
};

static_assert(sizeof(GpuInstance) == 128);
```

## 6. Instance flags

```text
bit 0 Visible
bit 1 Skinned
bit 2 StaticMap
bit 3 Rigid
bit 4 DynamicDeforming
bits 5..31 reserved = 0
```

## 7. `GpuMesh`

```cpp
struct GpuMesh {
    uint64_t positionAddress;
    uint64_t normalAddress;
    uint64_t tangentAddress;
    uint64_t texcoordAddress;
    uint64_t jointIndexAddress;
    uint64_t jointWeightAddress;
    uint64_t indexAddress;
    uint64_t sectionAddress;

    uint32_t vertexCount;
    uint32_t indexCount;
    uint32_t indexType;
    uint32_t sectionCount;

    uint32_t positionStride;
    uint32_t normalStride;
    uint32_t tangentStride;
    uint32_t texcoordStride;

    uint32_t jointIndexStride;
    uint32_t jointWeightStride;
    uint32_t skinFormat;
    uint32_t flags;

    uint32_t rtGeometryMetaBase;
    uint32_t boundsIndex;
    uint32_t reserved0;
    uint32_t reserved1;
};

static_assert(sizeof(GpuMesh) == 128);
```

`skinFormat` uses the exact `GpuSkinFormat` enum defined by architecture 063.

ABI v1 requires:

```text
EightInfluenceU16F32 = 0
```

Later compressed formats may add new enum values; format zero is immutable after ABI v1 ships.

## 8. Mesh flags

```text
bit 0 HasNormal
bit 1 HasTangent
bit 2 HasTexcoord
bit 3 HasSkin
bit 4 RtCapable
bits 5..31 reserved = 0
```

## 9. Mesh section

```cpp
struct GpuMeshSection {
    uint32_t firstIndex;
    uint32_t indexCount;
    int32_t  baseVertex;
    uint32_t materialIndex;

    uint32_t rtGeometryRelativeIndex;
    uint32_t flags;
    uint32_t boundsIndex;
    uint32_t reserved0;
};

static_assert(sizeof(GpuMeshSection) == 32);
```

`rtGeometryRelativeIndex` is relative to `GpuMesh.rtGeometryMetaBase`.

Invalid means this section has no asset-level RT geometry metadata.

## 10. Section flags

```text
bit 0 Opaque
bit 1 AlphaTest
bit 2 Transparent
bit 3 DoubleSided
bit 4 RtVisible
bit 5 Emissive
bits 6..31 reserved = 0
```

`Opaque`, `AlphaTest` and `Transparent` are mutually exclusive primary opacity classes.

## 11. `GpuLight`

```cpp
struct GpuLight {
    float positionRange[4];
    float directionCosOuter[4];
    float colorIntensity[4];
    float shape[4];

    uint32_t type;
    uint32_t flags;
    uint32_t lightId;
    uint32_t lightGeneration;

    uint32_t reserved0;
    uint32_t reserved1;
    uint32_t reserved2;
    uint32_t reserved3;
};

static_assert(sizeof(GpuLight) == 96);
```

No orphan `shadowDataIndex` exists in ABI v1.

## 12. Light type

```cpp
enum GpuLightType : uint32_t {
    Point = 0,
    Spot  = 1,
    Rect  = 2,
    Disk  = 3,
    Line  = 4
};
```

Values `5..0xffffffff` are invalid/reserved in ABI v1.

The dominant directional sun uses the dedicated sun path and is not stored in local `GpuLight[]`.

Exact per-type orientation/shape/intensity semantics are owned by architecture 062.

## 13. Light flags

```text
bit 0 Active
bit 1 TransientVfx
bit 2 AffectsLocalDirect
bit 3 AffectsDdgi
bit 4 AffectsVolumetrics
bits 5..31 reserved = 0
```

## 14. `GpuBonePalette`

Unchanged:

```cpp
struct GpuBonePalette {
    uint64_t currentMatrixAddress;
    uint64_t previousMatrixAddress;

    uint32_t jointCount;
    uint32_t flags;
    uint32_t reserved0;
    uint32_t reserved1;
};

static_assert(sizeof(GpuBonePalette) == 32);
```

## 15. `GpuDrawData`

```cpp
struct GpuDrawData {
    uint32_t instanceIndex;
    uint32_t meshIndex;
    uint32_t materialIndex;
    uint32_t sectionIndex;

    uint32_t renderObjectId;
    uint32_t firstIndex;
    uint32_t indexCount;
    int32_t  baseVertex;

    uint32_t flags;
    uint32_t reserved0;
    uint32_t reserved1;
    uint32_t reserved2;
};

static_assert(sizeof(GpuDrawData) == 48);
```

Raster G4 uses `renderObjectId`.

## 16. Draw flags

```text
bit 0 Skinned
bit 1 AlphaTest
bit 2 Transparent
bit 3 DoubleSided
bits 4..31 reserved = 0
```

## 17. `GpuRtInstanceData`

```cpp
struct alignas(16) GpuRtInstanceData {
    uint32_t renderObjectId;
    uint32_t geometryMetaBase;
    uint32_t geometryCount;
    uint32_t gpuInstanceIndex;

    uint32_t flags;
    uint32_t tacticalLevel;
    uint32_t rtMask;
    uint32_t reserved0;
};

static_assert(sizeof(GpuRtInstanceData) == 32);
```

`gpuInstanceIndex` targets `GpuSceneRoot.instances` or is invalid for static partition instances with no matching ordinary `GpuInstance`.

The previous orphan `transformIndex` is removed.

## 18. `GpuRtGeometryData`

```cpp
struct GpuRtGeometryData {
    uint64_t currentPositionAddress;
    uint64_t previousPositionAddress;
    uint64_t normalAddress;
    uint64_t tangentAddress;
    uint64_t texcoordAddress;
    uint64_t indexAddress;

    uint32_t materialIndex;
    uint32_t vertexStride;
    uint32_t indexTypeAndFlags;
    uint32_t renderObjectIdOverride;
};

static_assert(sizeof(GpuRtGeometryData) == 64);
```

`renderObjectIdOverride` follows architecture 058.

## 19. RT geometry flags

`indexTypeAndFlags`:

```text
bits 0..1 GpuIndexType
    0 UInt16
    1 UInt32
    2..3 reserved/invalid

bit  2 Opaque
bit  3 AlphaTest
bit  4 DoubleSided
bit  5 RtVisibleEmissiveOverlayAllowed
bits 6..31 reserved = 0
```

## 20. `GpuSkinningJob`

```cpp
struct GpuSkinningJob {
    uint64_t inputPositionAddress;
    uint64_t inputNormalAddress;
    uint64_t inputTangentAddress;
    uint64_t jointIndexAddress;
    uint64_t jointWeightAddress;

    uint64_t outputCurrentPositionAddress;
    uint64_t outputPreviousPositionAddress;
    uint64_t outputCurrentNormalAddress;
    uint64_t outputCurrentTangentAddress;

    uint32_t vertexCount;
    uint32_t positionStride;
    uint32_t normalStride;
    uint32_t tangentStride;
    uint32_t jointIndexStride;
    uint32_t jointWeightStride;
    uint32_t bonePaletteIndex;
    uint32_t instanceIndex;

    uint32_t skinFormat;
    uint32_t flags;
    uint32_t reserved0;
    uint32_t reserved1;
    uint32_t reserved2;
    uint32_t reserved3;
};

static_assert(sizeof(GpuSkinningJob) == 128);
```

## 21. Skinning job semantics

The job binds immutable bind streams to FrameContext-owned output streams.

Required output:

```text
current skinned position
previous skinned position
current skinned normal
current skinned tangent
```

Raster uses the current skinned streams.

Dynamic BLAS uses `outputCurrentPositionAddress`.

Temporal motion can use previous skinned position/output transforms.

No output stream aliases the other in-flight FrameContext.

## 22. FrameConstants

```cpp
struct FrameConstants {
    uint32_t frameIndex;
    uint32_t frameContextIndex;
    uint32_t renderWidth;
    uint32_t renderHeight;

    float deltaSeconds;
    float presentationTimeLowSeconds;
    float invRenderWidth;
    float invRenderHeight;

    uint32_t frameFlags;
    uint32_t debugMode;
    uint32_t randomSeedLo;
    uint32_t randomSeedHi;

    float exposureScale;
    float outputReferenceWhiteNits;
    float outputPeakNits;
    float presentationTimeHighSeconds;
};

static_assert(sizeof(FrameConstants) == 64);
```

Output values:

```text
HDR: reference white 203, peak 600
SDR: reference white 100, peak 100
```

## 23. Frame flags

```text
bit 0 HdrOutput
bit 1 SdrOutput
bit 2 DiagnosticOutput
bits 3..31 reserved = 0
```

Exactly one of HdrOutput/SdrOutput is set.

## 24. `ViewConstants`

```cpp
struct ViewConstants {
    float worldToView[16];
    float viewToClip[16];
    float worldToClip[16];
    float clipToWorld[16];
    float previousWorldToClip[16];

    float cameraPositionNear[4];
    float cameraForwardFar[4];
    float jitterCurrentPrevious[4];

    uint32_t viewportWidth;
    uint32_t viewportHeight;
    uint32_t viewIndex;
    uint32_t viewFlags;
};

static_assert(sizeof(ViewConstants) == 384);
```

Generic matrices are column-major and use architecture-051 column-vector semantics.

`worldToClip` contains current jitter.

`previousWorldToClip` contains previous jitter.

`jitterCurrentPrevious` stores current X/Y then previous X/Y NDC jitter values; G3 reprojection does not add them a second time.


## 25. Index/address target rules

```text
GpuMesh.boundsIndex
    -> GpuSceneRoot.bounds[]

GpuMeshSection.boundsIndex
    -> GpuSceneRoot.bounds[]

GpuInstance.rtInstanceDataIndex
    -> GpuSceneRoot.rtInstanceData[]

GpuInstance.skinningJobIndex
    -> GpuSceneRoot.skinningJobs[]

GpuMesh.rtGeometryMetaBase
    -> base index in GpuSceneRoot.rtGeometryData[]

GpuMeshSection.rtGeometryRelativeIndex
    -> relative offset from that mesh base

GpuRtInstanceData.geometryMetaBase
    -> actual contiguous RT-geometry base used by the instantiated BLAS/TLAS entry

GpuRtInstanceData.gpuInstanceIndex
    -> GpuSceneRoot.instances[] or invalid

GpuRtGeometryData.renderObjectIdOverride
    -> valid static identity or invalid/inherit
```

Every optional index uses `kInvalidGpuIndex`.

No shader-visible field may refer to an undocumented implicit array.

## 26. ABI scope

This document closes the semantic targets of fields used by the current renderer.

Asset-compression choices such as exact JNT0/WGT0 packing remain a separate content-pipeline decision and do not change these GPU address/stride/output bindings.

## Index/skin enum authority

Architecture 063 owns:

```text
GpuIndexType
GpuSkinFormat
```

`GpuMesh.indexType` and RT `indexTypeAndFlags` must use the same numeric index-type values.

`GpuMesh.skinFormat` and `GpuSkinningJob.skinFormat` must match.

## Light semantic authority

Architecture 062 owns the exact meanings and authoring units of:

```text
positionRange
directionCosOuter
colorIntensity
shape
GpuLightType
```

No shader/pass may reinterpret those fields locally.

## Frame time and stochastic-seed authority

Architecture 064 owns deterministic stochastic stream derivation.

`randomSeedLo/randomSeedHi` store the immutable 64-bit presentation stochastic seed rather than mutable RNG state.

Architecture 071 owns split GPU presentation time:

```text
presentationTimeHighSeconds
presentationTimeLowSeconds
```

These are not identity, ordering or RNG-counter inputs.

## Draw ownership authority

Architecture 071 removes the ambiguous instance-level draw index.

`GpuInstance.reserved0` is zero. Raster draws are selected explicitly through `GpuRasterDrawPassData.drawDataIndex`.
