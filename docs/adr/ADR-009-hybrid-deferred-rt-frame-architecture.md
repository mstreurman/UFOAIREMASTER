# ADR-009 — Hybrid Deferred + Dedicated RT Frame Architecture

**Status:** Accepted  
**Decision type:** Renderer architecture

## Decision

The remaster renderer will use a hybrid deferred architecture optimized for the Intel Arc B580.

Primary visibility is rasterized.

Dedicated ray-tracing pipelines provide selected presentation effects.

The renderer baseline is:

- deferred opaque raster path;
- rasterized primary camera visibility;
- dedicated RT shadow pipeline;
- dedicated RT reflection pipeline;
- dedicated/selective RT indirect-lighting pipeline;
- temporal RT reconstruction/denoising;
- deferred lighting;
- forward transparency and presentation VFX;
- linear HDR composition;
- BT.2020/ST2084 PQ output path;
- a 1920×1080 / near-60-FPS primary qualification profile, with runtime-selectable RenderExtent/output mode per ADR-046.

## Explicit non-goals

The baseline is not:

- a full path tracer;
- a ray-traced primary-visibility renderer;
- a Ray-Query-first renderer;
- a generic lowest-common-denominator cross-vendor renderer;
- an SDL GPU renderer;
- an architecture that requires upscaling to reach 1080p60 on the target B580.

## Vulkan execution baseline

Use:

- Vulkan 1.4;
- Dynamic Rendering;
- Synchronization2;
- timeline-semaphore-style internal progress tracking;
- two frames in flight initially;
- frame-graph-managed resource dependencies;
- dedicated transfer work where useful;
- async compute only after profiling proves a gain.

## Scene boundary

The renderer consumes Presentation World data.

The renderer does not directly consume canonical gameplay structures as its internal scene model.

Jolt physics also communicates through Presentation World.

## Consequences

This architecture spends RT hardware on the effects with the highest expected visual return while keeping primary visibility predictable and efficient.

It also provides a clean boundary between canonical game state and the modern presentation runtime.
