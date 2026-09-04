# Reference — Intel Arc B580 / Xe2 Microarchitecture

**Status:** Hardware reference  
**Reference date:** 2026-09-04  
**Purpose:** Record static B580/Xe2 hardware facts separately from runtime Vulkan capability queries and project benchmark results.

## 1. Source discipline

This document separates:

```text
STATIC HARDWARE FACTS
    Intel-published product / architecture facts

RUNTIME-QUERIED VULKAN FACTS
    values from the project's user-provided vulkaninfo capture

PROJECT-MEASURED RESULTS
    future UFOAIREMASTER benchmark results
```

Static hardware facts do not replace Vulkan feature/property queries.

Vulkan properties do not prove application performance.

Vendor architecture claims do not replace project benchmarks.

## 2. Authoritative Intel sources

### Intel Arc B580 product specification

Title:

```text
Intel® Arc™ B580 Graphics — Specifications
```

URL:

```text
https://www.intel.com/content/www/us/en/products/sku/241598/intel-arc-b580-graphics/specifications.html
```

Used for B580 SKU configuration, clocks, memory and I/O-level hardware facts.

### Intel oneAPI GPU Optimization Guide

Title:

```text
Intel® Xe GPU Architecture
```

URL:

```text
https://www.intel.com/content/www/us/en/docs/oneapi/optimization-guide-gpu/2025-2/intel-xe-gpu-architecture.html
```

Used for the B580-specific execution-resource/cache/register/work-group table.

### Intel Xe2 architecture deep dive

Title:

```text
Xe2 and Lunar Lake GPU Deep Dive
```

URL:

```text
https://cdrdv2-public.intel.com/824434/2024_Intel_Tech%20Tour%20TW_Xe2%20and%20Lunar%20Lakes%20GPU.pdf
```

Used only for generic Xe2 architectural structure/features, not for B580 SKU cache-capacity values where the B580-specific oneAPI table exists.

### Intel Arc B-Series launch material

Title:

```text
Intel Launches Arc B-Series Graphics Cards
```

URL:

```text
https://newsroom.intel.com/client-computing/intel-launches-arc-b-series-graphics-cards
```

Used for generation-level context: B-Series uses Xe2, second-generation Xe cores/RT hardware and XMX engines.

### Intel Arc real-time ray-tracing developer guide

Title:

```text
Intel® Arc™ Graphics Developer Guide for Real-Time Ray Tracing in Games
```

URL:

```text
https://www.intel.com/content/www/us/en/developer/articles/guide/real-time-ray-tracing-in-games.html
```

Used for Intel's asynchronous ray-tracing / Thread Sorting Unit execution model and for the explicit Intel guidance on synchronous Ray Query behavior, SIMD divergence, any-hit/intersection cost and groupshared/SLM interaction with RT work.

Scope caveat:

```text
the guide was authored for the first Intel Arc / Xe-HPG generation;
it is architecture-family guidance, not a measured B580 performance result
```

The Xe2 source above independently shows a `Thread Sorting Unit` alongside each Xe2 ray-tracing unit, so the asynchronous-RT scheduling rationale remains directly relevant to the Xe2/B580 design. Exact Vulkan performance on the B580 remains project-benchmarked.

## 3. B580 SKU configuration

Intel publishes:

```text
microarchitecture        Xe2
codename                 Battlemage
device/SKU               Arc B580
Xe-cores                 20
render slices             5
ray tracing units         20
XMX engines              160
vector engines           160
graphics clock           2670 MHz
TBP                      190 W

memory                   12 GB GDDR6
memory interface         192 bit
memory speed             19 Gbps
memory bandwidth         456 GB/s

PCIe                     4.0 x8
```

The remaster does not derive runtime limits from marketing clock/TBP figures.

They are capacity/context data only.

## 4. B580 execution-resource table

Intel's B580-specific oneAPI table publishes:

```text
Xe-core count                        20
Vector Engines / Xe-core              8
Vector Engine count                 160
hardware threads / Vector Engine      8
hardware thread count              1280

matrix engine / XMX support          yes
native double precision              yes

GRFs / hardware thread:
    regular mode                     128
    large-register mode              256

register width                       512 bits

L3 cache                              18 MB
L1 cache / Xe-core                   256 KB
SLM / Xe-core                        128 KB
max SLM / work-group                 128 KB

max work-group size                 1024
supported subgroup sizes             16, 32
```

Derived configuration identities:

```text
20 Xe-cores * 8 Vector Engines = 160 Vector Engines
160 Vector Engines * 8 hardware threads = 1280 hardware threads
160 XMX engines / 20 Xe-cores = 8 XMX engines per Xe-core
20 RT units / 20 Xe-cores = 1 RT unit per Xe-core
5 render slices -> 4 Xe-cores per render slice
```

These arithmetic identities describe the published B580 configuration; they are not performance claims.

## 5. Xe2 execution structure

Intel's generic Xe2 architecture material describes a second-generation Xe core with:

```text
8 x 512-bit Vector Engines
8 x 2048-bit XMX engines
native SIMD16 ALUs
SIMD16 and SIMD32 operation support
64-bit atomic support
3-way co-issue:
    FP + INT/extended-math + XMX
```

The B580-specific oneAPI table independently agrees on:

```text
8 Vector Engines / Xe-core
subgroup 16/32
512-bit register width
XMX support
```

Do not copy Lunar-Lake-specific cache-capacity numbers into the B580 profile.

For B580 cache/SLM quantities, use section 4.

## 6. Xe2 ray tracing unit

Intel's Xe2 architecture diagram specifies one new RTU with:

```text
3 traversal pipelines
18 box intersections
2 triangle intersections
BVH cache
```

The B580 product has:

```text
20 RT units
```

Intel's Xe2 render-slice diagram also places a:

```text
Thread Sorting Unit
```

with each Xe2 RTU/Xe-core path. The diagram establishes that thread sorting remains part of the Xe2 ray-tracing architecture; it does not by itself quantify a B580 Ray Query versus RT-pipeline speedup.

The project does not convert these vendor block-throughput figures into an expected ray/frame rate.

Actual performance depends on:

```text
BVH quality
ray coherence/divergence
shader cost
memory behavior
alpha/any-hit use
instance/geometry organization
cache locality
```

and must be measured.

## 7. Xe2 render-front-end facts relevant to benchmarking

Intel's Xe2 architecture material states:

```text
execute indirect:
    natively supported

vertex fetch:
    generation-level throughput improvement

mesh shading:
    generation-level performance improvement with vertex reuse

sampling:
    improved execution including compressed-texture paths

HiZ / Z / stencil:
    generation-level cache/throughput improvements

blending / pixel color cache:
    generation-level improvements
```

The vendor slides include relative improvement figures versus prior architecture.

Those are **not** UFOAIREMASTER performance predictions.

For this project, the important architectural implication is:

```text
native indirect execution strengthens the case for a measured
GPU-driven submission experiment
```

not automatic adoption of mesh shaders or device-generated rendering features.

## 8. B580 tuning implications

### Subgroup size

Because the hardware supports:

```text
16
32
```

the project benchmark policy remains:

```text
subgroup 32:
    default/reference

subgroup 16:
    required alternative benchmark for suitable compute kernels
```

Do not use subgroup 8 on the B580 renderer baseline.

### Register pressure

The published regular/large GRF modes make register pressure a target concern.

High-pressure shader families:

```text
RT closest-hit
reflection reconstruction
ReSTIR
DDGI
denoisers
skinning
particle compaction/sort
```

must be benchmarked with actual pipeline timings.

Avoid expanding payloads/intermediates solely because the ABI permits them.

### SLM pressure

B580 exposes:

```text
128 KB SLM / Xe-core
128 KB max / work-group
```

SLM is a finite shared execution resource.

Large SLM work-groups can reduce concurrent residency.

Therefore:

```text
do not make SLM-heavy overlap with RT a default
benchmark tile/work-group sizes
prefer register/cache solutions when they win whole-frame timing
```

### Cache behavior

Static reference:

```text
L1 / Xe-core    256 KB
L3               18 MB
```

This reinforces existing policies:

```text
coherent material access
small RT shader state
compact GPU records
static BLAS reuse
compressed texture formats
avoid deliberately chaotic bindless access
```

Do not assume the complete frame working set fits cache.

### XMX

B580 has:

```text
160 XMX engines
```

No baseline renderer pass is required to use XMX.

XMX/cooperative-matrix work is accepted only when:

```text
algorithm maps naturally to matrix operations
quality is equivalent or better
whole-frame B580 measurement wins
maintenance/ABI cost is justified
```

### RTU

The Xe2 RTU is traversal-capable enough that the project should continue to prioritize:

```text
coherent rays
opaque geometry
tiny hit shaders
minimal any-hit
good BLAS partitions
low recursion
small payloads
```

rather than increasing ray count just because fixed-function traversal is strong.

### RT pipeline versus Ray Query on Intel Arc

Intel's Arc RT developer guide describes the normal RT-pipeline path as asynchronous: ray work can leave the current shader execution and later resume through hardware-managed dispatch, while the Thread Sorting Unit can group shading requests to improve SIMD coherence.

The same guide explicitly describes Ray Queries as **synchronous** on Intel hardware. In that mode, the TSU is not used to generate coherent shading requests for the queried rays, so a wave can remain blocked by its longest/divergent traversal and divergent hit/material work must be managed by the shader/application rather than benefiting from the normal hardware thread-sorting path.

The guide is Xe-HPG-era guidance, but the Xe2 architecture source independently shows the Thread Sorting Unit retained next to the Xe2 RTU. Therefore the project's accepted target rule remains:

```text
VK_KHR_ray_tracing_pipeline:
    default for substantial world-space RT workloads

VK_KHR_ray_query:
    available capability
    non-preferred
    narrow exception only
    requires a directly comparable RT-pipeline implementation/benchmark
    requires a material whole-workload win on the Arc B580
```

A Ray Query experiment must account for more than traversal time. Measure at least:

```text
RT pass time
whole GPU frame time
frame median / p95 / p99
ray/hit/material divergence where tooling exposes useful counters
shader register/payload pressure
material/resource access coherence
additional hit-sorting/classification passes, if introduced
queue overlap effects
SLM/groupshared footprint and concurrent SLM-heavy work
```

Do not add software hit-sorting/classification merely to imitate a benefit the RT-pipeline/TSU path already provides unless the complete Ray Query design still wins on the B580.

Intel additionally warns that groupshared memory can interfere with RT performance on its Arc RT architecture because the relevant local cache resource services both work types. For Xe2/B580 this is treated as a **benchmark hypothesis**, not as a copied cache-topology claim: Ray Query compute experiments should start with low SLM use and explicitly compare serialized versus concurrent SLM-heavy work before any such overlap becomes baseline.

## 9. Runtime Vulkan authority

The exact runtime Vulkan feature/property authority remains:

```text
reference/reference-arc-b580-vulkan-capabilities.md
```

Examples include:

```text
descriptor sizes
descriptor-heap sizes/alignment
subgroup min/max/default
queue families
memory heaps/budget
RT pipeline features
ray position fetch
AS build limits/alignment
Wayland HDR formats/present modes
```

If a static hardware fact and runtime API limit appear to disagree, implementation follows the runtime Vulkan contract and the discrepancy is investigated.

## 10. Project-measured authority

No performance number in this document is a UFOAIREMASTER benchmark result.

Measured results belong in target-hardware benchmark artifacts and should record:

```text
source commit
renderer build ID
shader/content hashes
Mesa/driver identity
quality settings
RenderExtent
OutputExtent
scene/replay
median / p95 / p99
GPU pass timings
CPU timings
memory high-water
```

## 11. Current design consequences

The current architecture remains appropriate:

```text
raster-primary hybrid rendering
purpose-specific RT pipelines
recursion depth 1
descriptor heap + BDA
subgroup 16/32 benchmark gates
dedicated transfer queue
async compute measured-only
static BLAS compaction/reuse
full TLAS rebuild baseline with benchmark alternatives
GPU-resident particles
compressed textures
small shader-visible ABI records
```

This reference adds hardware traceability; it does not silently turn optional features into requirements.
