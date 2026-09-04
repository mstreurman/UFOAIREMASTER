# ADR-011 — Custom Component-Based Presentation World Data Model

**Status:** Accepted  
**Decision type:** Presentation runtime architecture  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`

## Context

The existing battlescape client local-entity representation mixes tactical mirror state, interaction state, animation state, renderer pointers, sound/VFX state and timing.

The remaster requires a presentation-owned runtime that can feed Vulkan, Jolt, OpenAL Soft and animation without turning any of those systems into canonical gameplay authorities.

A general third-party ECS is not required for this problem. Entity counts are moderate, the target CPU is fixed, and the presentation data flow is unusually specific.

## Decision

The remaster will implement a purpose-built, component-based `PresentationWorld`.

It is not a new canonical game world.

### Entity identity

Presentation entities use a 64-bit generational identity conceptually composed of:

```text
32-bit slot/index
32-bit generation
```

Canonical entity IDs and presentation entity IDs are different C++ types.

Renderer instance IDs, Jolt body IDs and audio-emitter IDs are also separate types.

### Entity records

The central entity record remains small and stores identity/lifetime metadata, a component mask and optional canonical-source binding.

Large component payloads are stored in dense component stores rather than embedded in the entity record.

### Component storage

The baseline component-storage strategy is:

- dense component arrays;
- sparse entity-to-component lookup;
- contiguous iteration;
- controlled structural mutation;
- SIMD-aware alignment for hot arrays;
- no requirement to use an archetype ECS.

Initial component families include:

- transforms;
- renderables;
- skeletons;
- animation state;
- physics proxies;
- audio emitters;
- lights;
- particles/VFX;
- attachments;
- lifetimes.

### Canonical binding

A presentation entity may:

- map one-to-one to a canonical entity;
- be one of multiple presentation entities associated with one canonical source;
- have no canonical source at all.

Examples of presentation-only entities include shell casings, debris, transient lights, smoke, blood and purely visual props.

### Native subsystem handles

Raw Vulkan, Jolt and OpenAL handles do not become general Presentation World data.

Presentation components use remaster-owned typed handles and subsystem adapters.

### Structural changes

Entity creation/destruction and add/remove-component operations occur at controlled synchronization points.

Parallel update phases do not perform arbitrary structural mutation.

Deferred world-command buffers may be used for structural requests.

### Destruction

Destruction is staged.

An entity may be marked pending-destroy during a frame and is dismantled at a known cleanup phase before its slot generation is incremented and recycled.

## Immutable extraction boundary

The mutable Presentation World is not directly traversed by the Vulkan renderer.

Each frame it produces immutable extraction data, including a `RenderSnapshot` and later an audio snapshot/command stream.

CPU Presentation World layout and GPU scene layout are intentionally independent.

## CPU target

Data layout is optimized for the Intel Core i9-9900K where profiling justifies it.

AVX2/FMA-aware layout and job splitting are first-class options, but exact AoS/SoA/AoSoA choices remain benchmark-driven.

## Consequences

This decision:

- removes `le_t` as the future renderer data model;
- provides stale-handle protection through generations;
- makes presentation-only entities natural;
- creates clear ownership boundaries for Vulkan/Jolt/OpenAL;
- supports contiguous extraction and future job-system parallelism;
- keeps canonical simulation independent from presentation runtime implementation.
