# Light, ReSTIR, DDGI and Temporal History v1 ABI

**Status:** Exact implementation specification  
**Related ADR:** ADR-020, ADR-029

## 1. Light identity

```cpp
struct LightId {
    uint32_t slot;
    uint32_t generation;
};
```

GPU representation stores the two fields separately.

Invalid:

```text
slot = 0xffffffff
generation = 0
```

## 2. Light registry

Main owns the light registry.

Creation/destruction requests are applied in the deterministic structural ordering defined by architecture 058.

A new slot starts:

```text
generation = 1
```

If a freed slot is reused:

```text
generation++
```

Generation zero is never assigned.

On 32-bit generation wrap the slot is permanently retired rather than aliasing an old history identity.

## 3. GpuLight identity rule

`GpuLight.lightId` is the registry slot.

`GpuLight.lightGeneration` is the current slot generation.

ReSTIR history stores both and validates both.

## 4. ReSTIR packed field

Exact `packedMAgeFlags`:

```text
bits  0..15  M                  uint16
bits 16..23  age                uint8
bit      24  valid
bits 25..27  sampleType         uint3
bit      28  temporalReused
bit      29  spatialReused
bit      30  visibilityKnown
bit      31  reserved = 0
```

`M` saturates at `65535`.

`age` saturates at `255`.

## 5. ReSTIR sample type

```cpp
enum DirectSampleType : uint32_t {
    DeltaCenter     = 0,
    RectUv          = 1,
    DiskUv          = 2,
    LineT           = 3,
    SphereDirection = 4,
    Reserved5       = 5,
    Reserved6       = 6,
    Invalid         = 7
};
```

`sampleParam0/1` meaning:

```text
DeltaCenter:
    both zero

RectUv / DiskUv:
    sampleParam0 = U16 U in low bits, U16 V in high bits
    sampleParam1 = 0

LineT:
    sampleParam0 low U16 = normalized T
    remaining bits zero

SphereDirection:
    sampleParam0 = octahedral SNORM16x2 direction
    sampleParam1 = 0
```

## 6. Reservoir validity

A reservoir is invalid if any are true:

```text
valid bit = 0
lightId invalid
light slot no longer active
light generation mismatch
current surface validation fails
sample type incompatible with current light type
```

## 7. DDGI volume metadata

```cpp
struct GpuDdgiVolume {
    float originPu[4];
    float spacingPu[4];

    uint32_t gridX;
    uint32_t gridY;
    uint32_t gridZ;
    uint32_t firstProbeIndex;

    uint32_t probeCount;
    uint32_t flags;
    uint32_t reserved0;
    uint32_t reserved1;
};

static_assert(sizeof(GpuDdgiVolume) == 64);
```

`originPu.xyz` and `spacingPu.xyz` are presentation units.

## 8. DDGI probe metadata

```cpp
struct GpuDdgiProbeMetadata {
    float relocationPu[3];
    float hysteresis;

    uint32_t volumeIndex;
    uint32_t state;
    uint32_t age;
    uint32_t flags;

    uint32_t irradianceTileX;
    uint32_t irradianceTileY;
    uint32_t distanceTileX;
    uint32_t distanceTileY;

    float confidence;
    float dirtyWeight;
    uint32_t lastUpdateFrame;
    uint32_t reserved0;
};

static_assert(sizeof(GpuDdgiProbeMetadata) == 64);
```

## 9. Probe state enum

```cpp
enum DdgiProbeState : uint32_t {
    Active                       = 0,
    InactiveInsideGeometry       = 1,
    InactiveOutsidePresentation  = 2,
    NeedsRelocation              = 3
};
```

Unknown values are invalid for ABI v1.

## 10. Probe flags

```text
bit 0  LightingDirty
bit 1  GeometryDirty
bit 2  RelocatedThisUpdate
bit 3  ResetHistory
bits 4..31 reserved = 0
```

## 11. DDGI image addressing

The probe metadata stores absolute tile origins in the persistent DDGI irradiance/distance images.

The image dimensions are queried from the bound image; the metadata does not assume a fixed total atlas width/height.

Per-probe tile sizes remain:

```text
irradiance 8x8
distance   16x16
```

The atlas allocator may repack probes only at a history reset/relocation boundary where metadata and histories are updated coherently.

## 12. Temporal jitter convention

G3 stores jitter-inclusive motion:

```text
currentJitteredUV  = UV from current jittered projection
previousJitteredUV = UV from previous jittered projection

velocity = previousJitteredUV - currentJitteredUV
```

Temporal reprojection from the current rendered UV:

```text
previousUV = currentUV + velocity
```

No pass adds:

```text
previousJitter - currentJitter
```

again.

## 13. View matrices

`worldToClip` contains current jitter.

`previousWorldToClip` contains previous jitter.

`jitterCurrentPrevious` remains available for:

```text
diagnostics
sample generation
algorithms that explicitly need jitter magnitudes
```

but not for an additional G3 reprojection correction.

## Screen-space mapping authority

Architecture 063 owns:

```text
positive-height Vulkan viewport
ndc -> renderUV
pixel-center convention
jitter sign
```

The jitter-inclusive velocity equations in this document are evaluated in that exact rendered-UV convention.

## Sample codec authority

Architecture 067 owns exact UNORM16/SNORM16/oct/disk sample codecs and known-answer tests.

## DDGI disk-cache boundary

The structures in this document are the shader-visible/runtime ABI. They are **not** an on-disk cache ABI. ADR-044/architecture 088 define the disposable `RDGI` warm-start container; architecture 085 defines its reference-v1 semantic records. Loading an `RDGI` cache must reconstruct valid runtime state conforming to this document before publication to shaders.

