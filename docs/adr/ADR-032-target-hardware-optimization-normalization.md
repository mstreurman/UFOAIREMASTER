# ADR-032 — Target Hardware Optimization Normalization

**Status:** Accepted  
**Decision type:** Target-hardware implementation-contract normalization  
**Primary target:** Fedora 44 / Intel Core i9-9900K / Intel Arc B580 Xe2  
**Related:** ADR-008, ADR-015, ADR-019, ADR-022, ADR-030, ADR-031

## Context

The Baseline-025 hardware-optimization audit found that the architecture was strongly target-aware but still contained:

```text
one stale descriptor-capacity policy
no exact RenderExtent/OutputExtent separation
ambiguous allocator eager-vs-lazy commitment
a memory-pressure mip policy incompatible with immutable live persistent sampled-image heap entries
no dedicated static B580/Xe2 hardware reference
missing mandatory benchmark gates for several target-sensitive optimizations
```

## Decision 1 — scene render extent is separate from output extent

The primary **qualification profile** remains:

```text
RenderExtent = 1920x1080
60 FPS target
```

`RenderExtent` is nevertheless runtime-configurable. It may follow the selected output extent for native rendering or use an explicitly selected internal render resolution. No renderer ABI may assume that 1920x1080 is the only legal runtime extent.

The Vulkan swapchain uses the actual current WSI/surface-supported:

```text
OutputExtent
```

The two are never aliases by assumption. Runtime output resolution/display/refresh/HDR selection is owned by ADR-046 and architecture 072/081/090.

UI retains:

```text
UiLogicalExtent = 1920x1080 logical units
UiRasterExtent  = OutputExtent
```

Architecture 072 owns the exact composition path.

## Decision 2 — B580 descriptor ABI is fixed

Remove the old runtime sampled-image capacity ladder.

ABI v1 is exactly:

```text
sampledImages[65536]
samplers[256]
```

Startup validates the fixed layout.

An incompatible device does not mutate ABI v1 to a smaller table.

A future fallback renderer requires a distinct ABI/version.

## Decision 3 — GPU allocator pools grow lazily

The block sizes in architecture 030 are:

```text
allocation/growth units
```

not mandatory eager startup commitments.

Logical pools initially own zero backing blocks unless a specifically documented bootstrap resource requires memory.

FrameContext arenas allocate/grow on first demand and retain useful blocks for reuse subject to pressure/trim policy.

## Decision 4 — baseline texture residency is whole-view immutable residency

A live persistent sampled-image heap texture:

```text
has its published baseline mip set
keeps the same view/descriptor identity
remains SHADER_READ_ONLY_OPTIMAL
```

Pressure may:

```text
stop prefetch
delay optional uploads
evict whole unreferenced texture assets after safe retirement
```

Pressure may not:

```text
strip mips from a live published view
silently rewrite a live persistent sampled-image heap texture view
```

True partial/sparse mip residency is a future explicit architecture change.

## Decision 5 — static B580/Xe2 hardware facts are documented

Add:

```text
reference/reference-arc-b580-xe2-microarchitecture.md
```

Static hardware facts, runtime Vulkan facts and measured project results remain separate authorities.

## Decision 6 — optimization claims require target measurements

The following become mandatory benchmark milestones rather than vague future possibilities:

```text
CPU compiler:
    normal optimized
    -O3
    LTO
    LTO + PGO

scene submission:
    CPU visibility/submission
    vs GPU classification/culling + indirect submission

skinning:
    reference EightInfluenceU16F32
    vs compact production candidates

ray position access:
    existing BDA geometry fetch
    vs VK_KHR_ray_tracing_position_fetch path

RT mechanism for narrowly scoped exceptions only:
    accepted VK_KHR_ray_tracing_pipeline baseline
    vs VK_KHR_ray_query candidate
    with Intel TSU/divergence/SLM effects included in whole-workload measurement

optional only on pressure/fit:
    transient resource aliasing
    cooperative-matrix/XMX experiments
    extra spirv-opt pipeline
```

Acceptance is based on whole-frame target-machine results, not isolated microbenchmark wins.

## Decision 7 — no feature-chasing

The following remain non-baseline unless measurement proves project benefit:

```text
mesh shaders
shader objects
graphics pipeline libraries
cooperative matrices
fragment shading rate
default async compute
default RayQuery renderer path
path-traced primary visibility
```

The B580 target is optimized by coherent use of relevant hardware, not by enabling every exposed feature.

## Consequence

Baseline 026 becomes explicitly optimized **for measurement on** the B580/9900K target while preserving a simple first implementation.

The architecture does not claim measured optimality until target benchmark artifacts exist.
