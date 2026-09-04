# Exact TLAS, Instance ABI, Mask and Visibility Policy

**Status:** Implementation specification baseline  
**Related ADR:** ADR-021

## 1. One shared TLAS

Each active FrameContext owns one production TLAS.

That TLAS is used by:

```text
RTDirectionalShadow
RTLocalVisibility
RTReflection
RTDDGI
```

Different ray classes use different cull masks against the same instance set.

Do not build one TLAS per effect in the baseline.

## 2. TLAS rebuild cadence

Build once per rendered frame after all current dynamic BLAS builds complete.

Baseline flags:

```text
VK_BUILD_ACCELERATION_STRUCTURE_PREFER_FAST_TRACE_BIT_KHR
```

Do not set:

```text
ALLOW_UPDATE
ALLOW_COMPACTION
```

Baseline mode:

```text
VK_BUILD_ACCELERATION_STRUCTURE_MODE_BUILD_KHR
```

every frame.

## 3. Why full rebuild

The frame can change:

```text
actor transforms
Jolt rigid transforms
skinned BLAS addresses
door transforms
breakable presence
cutaway/floor visibility
presentation effect participation
spawn/despawn state
```

Full rebuild gives a simple and high-quality traversal baseline.

`UPDATE` is benchmark-only until B580 measurements demonstrate a win.

## 4. Two TLAS objects

With two frames in flight:

```text
FrameContext 0:
    TLAS[0]

FrameContext 1:
    TLAS[1]
```

A FrameContext's TLAS storage is reused only after that context's graphics timeline completion.

## 5. TLAS capacity

Each FrameContext tracks:

```text
instanceCapacity
actualInstanceCount
TLAS storage size
scratch size
```

Starting capacity allocation:

```text
minimum capacity = 1024 instances
growth = next power of two >= required count
```

Use `vkGetAccelerationStructureBuildSizesKHR` for the capacity count.

Do not reallocate every time actual instance count changes slightly.

## 6. TLAS input buffer

One `VkAccelerationStructureInstanceKHR`-compatible 64-byte record per included instance.

The baseline uses an explicit raw layout rather than depending on C/C++ bitfield ordering:

```cpp
struct alignas(16) TlasInstanceInput {
    VkTransformMatrixKHR transform;      // 48 bytes

    uint32_t customIndexAndMask;
    uint32_t sbtOffsetAndFlags;

    uint64_t accelerationStructureReference;
};

static_assert(sizeof(TlasInstanceInput) == 64);
```

Packing:

```text
customIndexAndMask:
    bits  0..23 = instanceCustomIndex
    bits 24..31 = mask

sbtOffsetAndFlags:
    bits  0..23 = instanceShaderBindingTableRecordOffset
    bits 24..31 = VkGeometryInstanceFlagsKHR
```

This matches Vulkan's defined instance bit pattern.

## 7. Input memory

Preferred B580 allocation:

```text
DEVICE_LOCAL
HOST_VISIBLE
HOST_COHERENT
```

per FrameContext, persistently mapped.

CPU writes the dense instance array directly.

If later measurements prefer staged/device-only storage, the public ABI does not change.

## 8. Dense instance custom index

`instanceCustomIndex` is a dense frame-local index into:

```text
GpuRtInstanceData[]
```

Constraint:

```text
instanceCustomIndex < 0x01000000
```

because Vulkan provides 24 bits.

The renderer fails loudly if the limit is exceeded.

The frame-local index is not used as temporal object identity.

## 9. Stable temporal identity

Architecture 059 is the exact 32-byte `GpuRtInstanceData` layout owner.

This document owns the RT semantics of its fields.


Reflection history stores the resolved hit `RenderObjectId`, not the dense TLAS custom index.

For ordinary rigid/dynamic geometry the resolved ID is `GpuRtInstanceData.renderObjectId`.

For static map geometry, `GpuRtGeometryData.renderObjectIdOverride` may provide the finer stable identity required by architecture 058.

## 10. Geometry metadata lookup

Hit shaders use:

```text
InstanceCustomIndexKHR
    ->
GpuRtInstanceData

GeometryIndex
    ->
GpuRtGeometryData[geometryMetaBase + GeometryIndex]

PrimitiveID + barycentrics
    ->
triangle attributes
```

`GpuRtGeometryData` exact packing is owned by architecture 059.

It includes:

```text
current/previous position address
normal/tangent/UV/index addresses
material/index/geometry flags
renderObjectIdOverride
```

## 11. SBT offset

Baseline:

```text
instanceShaderBindingTableRecordOffset = 0
```

for all normal production instances.

There is no per-material SBT selection.

Specialized RT pipelines have their own compact SBTs.

Opacity behavior comes from geometry/instance opacity flags.

## 12. RT effect visibility-mask ABI

Reserve instance mask bits:

```cpp
enum RtVisibilityMask : uint8_t {
    RtMask_Shadow     = 1u << 0,
    RtMask_Reflection = 1u << 1,
    RtMask_GI         = 1u << 2,

    RtMask_Debug      = 1u << 7
};
```

Bits 3..6 remain reserved.

Normal world geometry commonly uses:

```text
Shadow | Reflection | GI
= 0x07
```

## 13. Ray cull masks

Production ray classes use:

```text
directional shadow:
    cullMask = RtMask_Shadow

local direct visibility:
    cullMask = RtMask_Shadow

reflection:
    cullMask = RtMask_Reflection

DDGI:
    cullMask = RtMask_GI
```

Thus a single TLAS can represent effect participation without separate acceleration structures.

## 14. Instance inclusion

An entity/cluster is included only if:

```text
presentation entity is alive
RT geometry is ready
current presentation cutaway permits it
rtMask != 0
BLAS address is valid
```

Instances with effective mask zero are omitted rather than emitted with mask zero.

## 15. Tactical cutaway

Static map partitioning guarantees that each independently hideable tactical level has separate BLAS instances.

When a level is presentation-hidden:

```text
do not emit those static level instances
do not emit presentation entities assigned solely to that hidden level where policy requires
```

This removes the geometry from:

```text
shadow rays
reflection rays
DDGI rays
```

consistently.

Canonical LOS/pathfinding are unchanged.

## 16. Rigid transforms

TLAS transform comes from the current Presentation World transform.

This applies to:

```text
tile placement
doors
weapons
props
Jolt rigid bodies
rigid debris
```

The BLAS remains in mesh/tile local coordinates.

## 17. Deforming object transform

A skinned/deforming BLAS contains vertices in the object's local skinned space chosen by the skinning pipeline.

The TLAS instance applies the object's current world/root transform.

When `gpuInstanceIndex` is valid, current/previous transforms come from `GpuInstance.currentWorldFromObject` and `GpuInstance.previousWorldFromObject`. There is no separate transform-index array.

## 18. Instance opacity flags

### All-opaque BLAS

Set:

```text
VK_GEOMETRY_INSTANCE_FORCE_OPAQUE_BIT_KHR
```

### Alpha-test-only BLAS

Set:

```text
VK_GEOMETRY_INSTANCE_FORCE_NO_OPAQUE_BIT_KHR
```

### Mixed BLAS

Set neither force flag.

Per-geometry `VK_GEOMETRY_OPAQUE_BIT_KHR` determines any-hit behavior.

## 19. Triangle facing

Baseline rays do not depend on front/back-face culling for ordinary visibility.

Asset geometry has a normalized winding convention.

If an instance transform has a negative determinant/mirrors handedness, set:

```text
VK_GEOMETRY_INSTANCE_TRIANGLE_FLIP_FACING_BIT_KHR
```

so hit-facing semantics remain consistent.

Do not use `TRIANGLE_FACING_CULL_DISABLE` as a default workaround.

## 20. Double-sided materials

Double-sided shading is a material/shading-normal concern.

It does not require duplicating triangles or creating another BLAS.

Because baseline rays do not use face-cull ray flags, both sides remain intersectable.

## 21. Instance ordering

Baseline TLAS input order is deterministic.

Starting sort key:

```text
tacticalLevel
RT geometry class
resolved stable RenderObjectId / deterministic static identity key
```

The dense `GpuRtInstanceData` table follows the same order.

Spatial/Morton instance reordering is a B580 benchmark candidate, not baseline.

## 22. Canonical/presentation identity

For canonical-backed presentation entities:

```text
GpuRtInstanceData.renderObjectId
    ->
PresentationEntity
    ->
optional CanonicalEntityId
```

No Vulkan shader or TLAS instance exposes a writable path back to canonical state.

For presentation-only debris/props:

```text
no canonical source is required
```

## Transform/winding authority

Architecture 051 owns transforms and normalized winding.

`VkTransformMatrixKHR` is written explicitly from semantic transform rows rather than raw-copying a generic CPU matrix.

RT and raster consume the same offline-normalized counter-clockwise presentation geometry.

## Static identity authority

Architecture 058 defines deterministic static identity allocation and the geometry-level RT identity override.

A BLAS/TLAS partition is not automatically the temporal object identity.
