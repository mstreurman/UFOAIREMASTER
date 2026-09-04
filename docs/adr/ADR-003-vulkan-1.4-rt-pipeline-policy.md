# ADR-003 — Vulkan 1.4 and RT-Pipeline-First Rendering

**Status:** Accepted  
**Decision type:** Graphics API / ray-tracing architecture

## Context

The primary GPU target exposes Vulkan 1.4-class functionality and the required KHR ray-tracing extensions.

The project intends to use hardware RT as a first-class presentation feature.

Two Vulkan mechanisms are available for tracing rays:

- the dedicated RT pipeline;
- inline Ray Query.

The project specifically prefers the RT pipeline model and wants to avoid Ray Query where possible.

## Decision

Use Vulkan 1.4 as the primary graphics API.

Use the following RT facilities as the baseline:

- `VK_KHR_acceleration_structure`;
- `VK_KHR_ray_tracing_pipeline`.

`VK_KHR_ray_query` may remain enabled as an available capability, but it is non-preferred.

## Ray Query rule

Ray Query must not be used as the default implementation for a renderer feature.

A Ray Query implementation requires:

1. a narrowly defined use case;
2. a directly comparable RT-pipeline implementation or benchmark;
3. evidence on the target Arc B580 showing a material benefit;
4. confirmation that the choice does not compromise the larger RT scheduling architecture.

Absent that evidence, use an RT pipeline.

## Intel Arc / Xe2 rationale

The target-specific hardware rationale is documented in `reference/reference-arc-b580-xe2-microarchitecture.md`.

Intel's Arc real-time ray-tracing developer guide describes Ray Query execution as synchronous and notes that it does not use the Thread Sorting Unit to generate coherent shading requests in the way the normal asynchronous RT shader path can. Intel's Xe2 architecture material independently shows the Thread Sorting Unit retained alongside the Xe2 RTU.

Therefore this ADR's RT-pipeline-first policy is not merely a generic API preference. It intentionally preserves access to Intel's hardware-managed asynchronous RT scheduling/coherence path for substantial RT workloads.

This is still not a claim that every RT-pipeline implementation beats every Ray Query implementation on the B580. A narrow Ray Query exception remains allowed only under the benchmark rule above. Such a benchmark must include whole-pass/whole-frame cost, divergence/material-access effects, any extra software sorting/classification, register/payload pressure and SLM/groupshared interaction where applicable.

## Initial RT-pipeline direction

The renderer should favor dedicated, purpose-specific RT pipelines rather than one universal RT pipeline.

Expected categories include:

- shadow/visibility RT pipeline;
- reflection RT pipeline;
- indirect-lighting RT pipeline when implemented.

This is not a requirement that every effect exist in the first implementation.

## Initial shader policy

The initial design should favor:

- recursion depth 1 for normal rendering;
- small ray payloads;
- small hit attributes;
- lean SBT records;
- material data in GPU buffers rather than bloated SBT records;
- aggressive opaque classification;
- avoidance of any-hit shaders where practical;
- terminate-on-first-hit behavior for appropriate visibility/shadow rays;
- indexed and locality-optimized geometry;
- spatially coherent acceleration-structure organization.

These policies remain subject to B580 benchmarking.

## Primary visibility

The initial renderer direction is hybrid:

- rasterization provides primary visibility;
- RT enhances selected presentation effects.

Full path tracing is not the baseline 1080p60 target.

## Performance policy

The 60 FPS target gives a total frame interval of 16.667 ms.

The renderer should maintain useful GPU headroom rather than target an average frame time exactly equal to the display deadline.

Initial ray budgets, reconstruction policy and BLAS/TLAS baselines are now specified by ADR-019 through ADR-021 and architecture 019–028. They remain benchmark-tunable within those accepted policies.

## Current benchmark questions

The following remain measurement questions rather than undecided architecture:

- SIMD16 versus SIMD32 compute-kernel crossover on B580;
- RT-pipeline versus Ray Query crossover for narrowly scoped exceptional workloads;
- async-compute overlap versus serialized RT/denoise scheduling;
- benchmark tuning of static-BLAS chunk thresholds around the accepted partition policy;
- whether any measured workload justifies revisiting the accepted full-TLAS-rebuild or full dynamic-BLAS-BUILD baselines through a later ADR.
