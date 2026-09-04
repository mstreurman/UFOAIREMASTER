# Exact BLAS Partitioning, Build and Lifetime Policy

**Status:** Implementation specification baseline  
**Related ADR:** ADR-021  
**Primary target:** Intel Arc B580 / BMG G21

## 1. BLAS classes

The runtime recognizes these production BLAS classes:

```text
StaticMapOpaque
StaticMapAlphaTest

RigidAssetOpaque
RigidAssetAlphaTest

DynamicDeforming

TransientGenerated
```

`TransientGenerated` is exceptional and not expected to carry major scene geometry.

## 2. Geometry baseline

Production BLAS use indexed triangles.

The presentation asset compiler emits RT-ready indexed geometry.

Baseline does not depend on:

```text
procedural AABB geometry
curve primitives
camera-dependent RT LOD switching
pre-serialized driver acceleration structures
```

## 3. Static map partition key

Static map BLAS identity:

```text
{
    presentationTileAssetId,
    tacticalLevel,
    rtGeometryClass,
    chunkIndex
}
```

Where:

```text
rtGeometryClass =
    Opaque
    AlphaTest
```

The tactical-level split is mandatory.

A BLAS may not span multiple independently hideable tactical levels.

## 4. Why tactical level is a BLAS boundary

TLAS visibility is per instance.

If floors 2 and 3 were stored in one BLAS instance, hiding floor 3 would require:

```text
shader-side filtering
any-hit filtering
or hiding both floors
```

All are undesirable.

Instead:

```text
tile asset
    |
    +-- level 0 opaque BLAS
    +-- level 0 alpha BLAS
    +-- level 1 opaque BLAS
    +-- level 1 alpha BLAS
    ...
```

Cutaway then omits the relevant TLAS instances.

## 5. RMA sharing

BLAS geometry is stored in tile-local coordinates.

Each placement of an RMA tile references the same compacted BLAS and supplies a different TLAS transform.

Example:

```text
hospital_a / level 0 / opaque BLAS
       |
       +-- TLAS instance placement A
       +-- TLAS instance placement B
       +-- TLAS instance placement C
```

Do not rebuild identical static BLAS for repeated placements.

## 6. Large static chunk split

Starting compiler policy:

```text
target approximately 65,536 triangles/chunk
hard starting ceiling 131,072 triangles/chunk
```

If a `{tile, level, class}` partition exceeds the ceiling:

```text
1. calculate geometry-section centroids
2. split spatially on the longest AABB axis
3. preserve whole triangle/material sections where practical
4. recurse until each chunk <= 131,072 triangles
5. prefer balanced chunks near the 65,536 target
```

These triangle thresholds are B580 benchmark starting constants.

The architectural invariant is the spatial/tactical/class partition, not the exact triangle number.

## 7. Static geometry sections

A static BLAS may contain multiple `VkAccelerationStructureGeometryKHR` triangle geometries.

Each geometry section is homogeneous for:

```text
vertex/index interpretation
material metadata mapping
opacity class
```

Opaque sections use:

```text
VK_GEOMETRY_OPAQUE_BIT_KHR
```

Alpha-tested sections are non-opaque and use:

```text
VK_GEOMETRY_NO_DUPLICATE_ANY_HIT_INVOCATION_BIT_KHR
```

where appropriate.

## 8. Static BLAS build flags

At map/asset load:

```text
PREFER_FAST_TRACE
ALLOW_COMPACTION
```

Do not set:

```text
ALLOW_UPDATE
LOW_MEMORY
ALLOW_DATA_ACCESS
```

in the baseline.

`ALLOW_DATA_ACCESS` may be enabled later only if the position-fetch path is adopted and benchmarked.

## 9. Static build/compaction sequence

```text
RT-ready geometry available
        |
        v
query build sizes
        |
        v
allocate temporary BLAS storage
allocate aligned scratch
        |
        v
vkCmdBuildAccelerationStructuresKHR
        |
        v
query compacted size
        |
        v
allocate final compacted storage
        |
        v
vkCmdCopyAccelerationStructureKHR
COMPACT
        |
        v
publish immutable BLAS
        |
        v
retire temporary storage
```

Static builds may be batched.

Compaction occurs off the render-critical frame path.

## 10. No shipped Vulkan BLAS binaries

Presentation assets ship optimized RT geometry/metadata.

They do not ship driver-specific serialized acceleration structures as the baseline.

BLAS are constructed for the current B580/Mesa Vulkan implementation at runtime/map load.

## 11. Rigid reusable asset BLAS

Used by:

```text
doors
breakables
inline brush-model presentation meshes
weapons
rigid props
pre-authored debris/fragments
other non-deforming meshes
```

Identity is asset-based rather than entity-based.

Conceptually:

```text
{
    meshAssetId,
    rtGeometryClass,
    rtLodId
}
```

Baseline uses one dedicated RT LOD per asset.

The same compacted BLAS may be referenced by many TLAS instances.

## 12. Rigid movement

A moving rigid object changes:

```text
TLAS instance transform
```

only.

Do not rebuild BLAS for:

```text
translation
rotation
uniform/non-uniform affine scale supported by instance transform
Jolt rigid-body motion
door animation
weapon attachment/socket motion
```

## 13. Breakables

An intact breakable references its intact reusable BLAS.

On the presentation response to canonical break/destruction:

```text
intact TLAS instance removed
presentation debris/fragment instances created as appropriate
```

Canonical break state remains authoritative.

RT geometry does not decide whether the object is broken.

## 14. Dynamic deforming BLAS

Used for:

```text
skinned actors
skinned aliens
ragdoll-deformed render meshes
other truly vertex-deforming presentation meshes
```

Baseline granularity:

```text
one BLAS per deforming render object per active FrameContext
```

A dynamic BLAS may contain multiple geometry sections.

Unlike large static map partitions, an actor is not split into one BLAS per material.

## 15. Dynamic geometry flags

Per geometry section:

```text
opaque:
    VK_GEOMETRY_OPAQUE_BIT_KHR

alpha-tested:
    non-opaque
    optional NO_DUPLICATE_ANY_HIT
```

Therefore one actor BLAS may contain both opaque and alpha-tested sections if necessary.

The instance must not force all geometry opaque when mixed.

## 16. Dynamic BLAS build flags

Baseline:

```text
VK_BUILD_ACCELERATION_STRUCTURE_PREFER_FAST_BUILD_BIT_KHR
```

Do not set:

```text
ALLOW_COMPACTION
ALLOW_UPDATE
```

The Vulkan specification notes that allowing update/compaction may add build time/memory overhead; the baseline avoids paying those costs until needed.

## 17. Dynamic BLAS schedule

Every rendered frame:

```text
GPU compute skinning
        |
        v
current skinned vertex buffer
        |
        v
Dynamic BLAS Build
        |
        v
TLAS Build
```

The BLAS consumes:

```text
current skinned positions
stable/static index topology
```

Previous skinned positions are retained for motion/reconstruction but are not BLAS build input.

## 18. Dynamic two-frame storage

For two frames in flight:

```text
deforming object
    |
    +-- BLAS storage slot FrameContext 0
    +-- BLAS storage slot FrameContext 1
```

Build the current frame into that frame's slot.

Do not update the BLAS referenced by the other in-flight frame.

## 19. Dynamic build sizing

For stable topology, query build-size requirements from the known maximum geometry/primitive counts.

Persistent per-frame slots may reuse that capacity.

If topology/asset changes, invalidate and resize the object's dynamic BLAS slots.

## 20. Dynamic build batching

Collect dynamic BLAS builds after skinning.

Use `vkCmdBuildAccelerationStructuresKHR` with multiple build infos where useful.

Concurrent entries receive non-overlapping scratch slices.

Scratch offsets obey the B580 reference requirement:

```text
minAccelerationStructureScratchOffsetAlignment = 64 bytes
```

The exact maximum concurrent batch/scratch budget is benchmark-tuned.

## 21. No baseline refit

Even though skinned topology is stable, baseline uses full dynamic BLAS rebuilds.

Benchmark later:

```text
full rebuild
vs
ALLOW_UPDATE + UPDATE
```

using actual:

```text
actor counts
animation deformation
ragdoll deformation
BLAS build time
RT traversal time
memory
```

Refit becomes production only if it wins the real B580 frame.

## 22. Transient generated geometry

If presentation generates a genuinely new triangle mesh:

```text
build PREFER_FAST_BUILD once
```

Then, if it becomes rigid:

```text
reuse that BLAS with TLAS transforms for its lifetime
```

Prefer pre-authored reusable fragment assets over generating many tiny BLAS.

## 23. Excluded geometry

Baseline RT TLAS excludes:

```text
pure particles
screen-space/UI
decals
non-geometric volumetrics
ordinary alpha-blended transparent surfaces
```

Glass/water RT participation remains part of their future material specification.

## 24. RT LOD

Baseline uses a fixed presentation RT LOD per mesh asset.

Do not switch RT geometry purely from camera visibility or screen size.

Off-screen objects can be visible in reflections/GI, so screen-space LOD truth is not appropriate for the baseline RT world.
