# B580 / i9-9900K Optimization Benchmark Gates

**Status:** Target optimization acceptance specification  
**Related ADR:** ADR-032  
**Reference:** `reference/reference-arc-b580-xe2-microarchitecture.md`

## 1. Principle

An optimization becomes target baseline only when it improves the **whole relevant workload** on the reference machine.

Do not promote a change from:

```text
vendor capability
isolated instruction throughput
single microbenchmark
one synthetic scene
```

alone.

## 2. Common benchmark identity

Every accepted run records:

```text
source commit
renderer build ID
compiler/link profile
Slang/ufo-shaderc identity
shader package hashes
content hashes
Mesa/driver identity
RenderExtent
OutputExtent
HDR/SDR mode
quality configuration
replay/scene identity
presentation RNG seed/config
```

## 3. Common measurements

Record at least:

```text
frame CPU median / p95 / p99
GPU frame median / p95 / p99
Render-thread submit/record time
snapshot-ready latency
selected pass timings
heap budget/usage
allocator committed high-water
thermal/sustained-run behavior
visual regression result
canonical regression result
```

No optimization may change canonical gameplay results.

## 4. CPU compiler profile gate

Reference CPU:

```text
Intel Core i9-9900K
8C/16T
AVX2/FMA
```

Compare:

```text
A:
    current normal optimized target build

B:
    -O3 target build

C:
    LTO/IPO target build

D:
    LTO/IPO + PGO target build
```

All retain:

```text
-march=native
-mtune=native
no global -ffast-math
```

PGO training set includes:

```text
campaign/frontend transitions
large tactical RMA load
actor-heavy tactical frame
combat/VFX frame
asset streaming/load
renderer submission
```

Accept only if:

```text
canonical regression passes
presentation structural regression passes
no material p95/p99 regression
sustained CPU frequency/thermal behavior remains acceptable
whole-frame or critical-path CPU time materially improves
```

## 5. GPU-driven submission gate

Initial renderer may use CPU visibility/draw submission.

A mandatory post-bring-up comparison is:

```text
A:
    CPU classification/visibility
    CPU draw list generation
    CPU indirect/direct submission preparation

B:
    GPU classification/culling
    GPU indirect command/data generation
    Vulkan indirect submission
```

Required scenes:

```text
large RMA
many repeated props
actor-heavy tactical
debris-heavy combat
high decal/particle density
```

Measure:

```text
Main CPU
Render CPU
GPU cull/build pass
raster GPU
total GPU
frame p95/p99
latency
```

Accept GPU-driven path only for a whole-frame win.

Intel Xe2's native execute-indirect support is motivation for this test, not proof of benefit.

Mesh shaders are not required for this experiment.

## 6. Skinning format gate

Reference/debug ABI:

```text
GpuSkinFormat::EightInfluenceU16F32
8 x uint16 joint
8 x float32 weight
48 bytes/vertex influence payload
```

Benchmark production candidates:

```text
Candidate A:
    reference format 0

Candidate B:
    8 x U16 joint
    8 x UNORM16 weight

Candidate C:
    qualifying assets:
    4 x U16 joint
    4 x UNORM16 weight

Candidate D:
    another packed format only if content/tooling shows value
```

Measure:

```text
asset size
VRAM
vertex/influence bandwidth
GPU skinning
dynamic BLAS dependency latency
animation error
offline conversion cost
```

Do not reduce influences globally solely to save bytes.

Offline qualification may choose compact formats per asset.

## 7. RT position-fetch gate

The reference Vulkan device exposes:

```text
rayTracingPositionFetch = true
```

Compare:

```text
A:
    existing BDA position/index/material reconstruction

B:
    VK_KHR_ray_tracing_position_fetch where applicable
    with required AS build flags
```

Measure:

```text
BLAS size
BLAS build time
dynamic BLAS time
RT traversal + hit shader time
GpuRtGeometryData traffic
reflection
DDGI
whole GPU frame
```

Accept only if total affected frame work wins.

## 8. Subgroup/work-group gate

B580 supports:

```text
subgroup 16
subgroup 32
max work-group 1024
SLM 128 KB/Xe-core
max SLM 128 KB/work-group
```

Required alternatives for suitable kernels:

```text
subgroup 32 reference
subgroup 16 alternative

multiple work-group sizes
multiple SLM footprints
```

Target kernels:

```text
skinning
particle compaction
particle sort
denoisers
ReSTIR
DDGI
reflection reconstruction
selected post
```

Measure whole pass and frame, not occupancy estimates alone.

## 9. Register-pressure gate

B580 hardware reference records:

```text
128 GRF regular mode
256 GRF large-register mode
512-bit register width
```

High-pressure shader changes require:

```text
pipeline timing
spill/regression observation where tooling exposes it
payload/intermediate size review
```

Particularly:

```text
closest-hit
reflection
ReSTIR
DDGI
complex denoise
```

Do not enlarge payloads or material state without a measured need.

## 10. Transient aliasing trigger

Baseline Frame Graph does not intra-frame alias.

Benchmark aliasing only after measured representative memory data shows a meaningful reason, for example:

```text
FrameTransient committed/high-water becomes a significant
fraction of current Vulkan heap budget
```

Any aliasing experiment must preserve:

```text
clear lifetime ownership
debuggability
Sync2 correctness
capture/probe behavior
```

No aliasing is added merely because it can save theoretical bytes.

## 11. XMX / cooperative-matrix trigger

B580 contains 160 XMX engines.

No baseline pass is forced onto XMX.

An experiment is justified only when a pass naturally maps to matrix/tile operations, for example a future learned or matrix-heavy reconstruction stage.

Acceptance requires:

```text
same/better visual quality
whole-pass speedup
no harmful async/resource contention
maintainable Slang/Vulkan ABI
```

Stencil/à-trous filters remain normal compute unless an actual matrix formulation wins.

## 12. SPIR-V optimization gate

Compare representative shader packages:

```text
Slang optimized output
vs
Slang output + selected spirv-opt pipeline
```

Use:

```text
G-buffer
skinning
RT closest-hit
ReSTIR
reflection
DDGI
VFX
UI/output
```

Accept only if:

```text
spirv-val passes
reflection/ABI is unchanged
debug tooling remains usable
target B580 pipeline/pass timing improves
```

## 13. Async compute remains measured-only

Separate compute family availability does not make async compute baseline.

Use the existing whole-frame rule:

```text
enable only if overlap improves target frame
without harming RT/cache/bandwidth/latency
```

## 14. Target benchmark scene set

Maintain stable representative captures/replays for:

```text
large RMA / static geometry
actor-heavy
many dynamic skinned actors
debris/VFX heavy
many local lights/ReSTIR stress
reflection-heavy surfaces
DDGI update stress
UI-heavy screen
asset-load/streaming transition
```

Add combined worst-reasonable cases so subsystem optimizations are tested together.

## 15. Optimization status labels

Every target-sensitive architecture choice should be classifiable as:

```text
LOCKED BY CONTRACT
    correctness/ABI decision

REFERENCE BASELINE
    first implementation

BENCHMARK CANDIDATE
    alternative to measure

MEASURED WIN
    accepted target result with artifact

REJECTED ON TARGET
    tested and not adopted
```

Do not call a benchmark candidate “optimized” before measurement.

## 16. RT-pipeline versus Ray Query exception gate

ADR-003 already locks `VK_KHR_ray_tracing_pipeline` as the default RT mechanism. This section defines the benchmark required before a narrow `VK_KHR_ray_query` exception may be accepted.

Intel-specific rationale is recorded in `reference/reference-arc-b580-xe2-microarchitecture.md`: Intel documents Ray Query as synchronous on Arc and describes the normal RT shader path as able to use the Thread Sorting Unit for hardware-managed shading coherence; Intel's Xe2 material retains the Thread Sorting Unit beside the Xe2 RTU.

Compare:

```text
A:
    accepted purpose-specific VK_KHR_ray_tracing_pipeline implementation

B:
    narrowly scoped VK_KHR_ray_query implementation
```

The two candidates must implement equivalent visibility/lighting semantics and equivalent quality.

Required measurements:

```text
RT pass median / p95 / p99
whole GPU frame median / p95 / p99
CPU submission/dispatch cost
ray count and hit rate
shader/register/payload pressure where tooling exposes it
material/resource divergence indicators where available
software hit sorting/classification cost, if B needs it
SLM/groupshared footprint
serialized vs concurrent SLM-heavy work when relevant
queue-overlap effect
visual regression result
```

Required scenes include at least:

```text
coherent visibility/shadow rays
highly divergent visibility/shadow rays
reflection-heavy material divergence
alpha-tested/any-hit stress where the feature uses it
combined RT + compute/denoise pressure
```

Acceptance rule:

```text
Ray Query remains rejected as the target baseline unless B produces
a material, repeatable whole-workload win on the Arc B580 without
compromising frame-tail behavior, RT scheduling, visual correctness
or maintainability.
```

A microbenchmark win in traversal alone is insufficient. Extra software sorting/classification added to recover coherence is charged to candidate B in full.

