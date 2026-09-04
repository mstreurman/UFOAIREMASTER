# Acceleration-Structure Frame-Graph Lifecycle and B580 Benchmarks

**Status:** Architecture baseline  
**Related ADR:** ADR-021

## 1. Map/asset-load path

```text
presentation asset load
        |
        v
upload RT-ready vertex/index buffers
        |
        v
build static/rigid BLAS
        |
        v
query compacted sizes
        |
        v
compact
        |
        v
publish immutable BLAS addresses
```

Published BLAS carry readiness tokens if the build/compaction occurs asynchronously.

## 2. Per-frame path

```text
Presentation World transforms
        |
        +------------------------------+
        |                              |
        v                              v
CPU TLAS instance preparation     GPU skinning
                                       |
                                       v
                              Dynamic BLAS Build
                                       |
                                       v
                           finalize instance BLAS refs
                                       |
                                       v
                                  TLAS Build
                                       |
                 +---------------------+------------------+
                 |                     |                  |
                 v                     v                  v
              Shadows             Reflections           DDGI
```

The CPU may prepare most instance metadata before dynamic BLAS completion, but TLAS build waits for all referenced dynamic BLAS builds.

## 3. Frame Graph resource states

### Skinned vertices

```text
Compute skinning:
    StorageWrite

    ->

Dynamic BLAS:
    AccelBuildInputRead
```

### Dynamic BLAS

```text
Dynamic BLAS:
    BuildWrite

    ->

TLAS:
    BuildRead
```

### TLAS

```text
TLAS:
    BuildWrite

    ->

RT:
    ShaderRead
```

These dependencies use the previously locked Frame Graph Synchronization2 mapping.

## 4. Build queue

Baseline AS builds occur on the main graphics/compute/RT queue.

Do not move BLAS/TLAS builds to the separate compute queue until overlap is measured on the B580.

This avoids introducing queue-ownership/scheduling complexity before evidence.

## 5. Scratch allocator

Use the centralized AS scratch allocator.

Reference B580 minimum alignment:

```text
64 bytes
```

Each simultaneously eligible build receives a non-overlapping scratch slice.

Scratch memory is transient and reused after GPU completion.

## 6. Static AS storage

Final compacted static BLAS storage is:

```text
device-local
long-lived
immutable
```

Track:

```text
uncompacted bytes
compacted bytes
compaction ratio
build time
compaction time
```

for benchmark telemetry.

## 7. Dynamic AS storage

Dynamic deforming BLAS storage is:

```text
device-local
FrameContext-owned/double-buffered
non-compacted
```

It persists at sufficient capacity to avoid allocation churn.

## 8. TLAS storage

TLAS storage is:

```text
device-local
one allocation/capacity per FrameContext
non-compacted
```

Scratch comes from the frame AS scratch arena.

## 9. Direct builds only

The reference B580 reports:

```text
accelerationStructureIndirectBuild = false
```

The baseline therefore uses direct:

```text
vkCmdBuildAccelerationStructuresKHR
```

with CPU-known build range/count data.

Do not architect around indirect AS build commands.

## 10. Static BLAS benchmark matrix

Measure static chunk target/ceiling combinations:

```text
32k / 64k triangles
64k / 128k triangles
128k / 256k triangles
```

Measure:

```text
load build time
compaction time
final memory
shadow traversal time
reflection traversal time
DDGI traversal time
```

The 65k target / 131k ceiling remains baseline until measurements justify change.

## 11. Dynamic actor BLAS benchmark matrix

Measure:

```text
full BUILD + PREFER_FAST_BUILD
full BUILD + no preference
ALLOW_UPDATE + UPDATE
```

for:

```text
8 actors
16 actors
32 actors
64 actors
```

across:

```text
idle animation
running
large animation deformation
ragdoll
```

Record:

```text
build time
scratch size
AS size
subsequent RT time
total frame impact
```

An UPDATE path is accepted only on total-frame improvement, not build time alone.

## 12. TLAS benchmark matrix

Compare full rebuild:

```text
PREFER_FAST_TRACE
PREFER_FAST_BUILD
no preference
```

Then separately compare:

```text
ALLOW_UPDATE + UPDATE
```

for representative instance counts and transform churn.

Measure combined:

```text
TLAS build/update time
shadow traversal
reflection traversal
DDGI traversal
```

Baseline remains full BUILD + `PREFER_FAST_TRACE` until evidence says otherwise.

## 13. Instance-order benchmark

Compare deterministic baseline ordering with:

```text
Morton/spatial centroid ordering
BLAS-address grouping
opacity-class grouping
```

Only adopt alternative ordering if total RT time improves reliably without harming determinism/debuggability.

## 14. Alpha geometry benchmark

Test:

```text
separate static alpha BLAS
mixed opaque/alpha BLAS
```

using:

```text
fences
foliage
grates
```

Measure:

```text
any-hit invocation cost
BLAS build size
TLAS instance count
shadow traversal
reflection traversal
```

Production baseline remains separate static opacity classes.

## 15. Cutaway benchmark

Exercise:

```text
show all floors
hide one upper floor
rapid floor switching
door/breakable transition
```

Verify:

```text
raster and RT agree on visibility
TLAS instance list changes correctly
shadow/reflection history invalidates appropriately
DDGI dirty marking occurs
canonical state is unchanged
```

## 16. AS debug telemetry

Expose:

```text
static BLAS count
dynamic BLAS count
TLAS instance count

opaque instance count
alpha-test instance count

static BLAS bytes
dynamic BLAS bytes
TLAS bytes
scratch peak bytes

dynamic BLAS build ms
TLAS build ms

per-BLAS triangle count histogram
compaction ratio histogram
```

## 17. Debug visualization

Required developer views:

```text
BLAS AABBs
TLAS instance AABBs
instance mask
tactical-level ownership
static/dynamic class
opaque/alpha class
renderObjectId
BLAS reuse count
```

## 18. Failure policy

Renderer initialization/runtime must report precise errors for:

```text
invalid BLAS address
24-bit custom-index overflow
AS storage allocation failure
scratch allocation failure
missing static BLAS readiness
TLAS capacity growth failure
invalid tactical-level mapping
```

Do not silently remove required world geometry from RT because an AS build failed.

Presentation subsystem failure may degrade presentation globally, but must not modify canonical game state.

## Dynamic BLAS skinned-position binding

Architecture 059 owns the exact `GpuSkinningJob` output addresses.

For a skinned deforming object:

```text
GPU skinning writes outputCurrentPositionAddress
    ->
dynamic BLAS BUILD reads that position stream
```

The output belongs to the active FrameContext and never aliases the other in-flight frame.

## Ray position-fetch benchmark

Architecture 073 requires a measured comparison between:

```text
existing BDA vertex-position reconstruction

and

VK_KHR_ray_tracing_position_fetch where applicable
```

including BLAS flags/size/build cost and whole affected reflection/DDGI frame time.

Position fetch remains optional until that target result exists.
