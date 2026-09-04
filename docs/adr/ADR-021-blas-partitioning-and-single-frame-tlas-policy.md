# ADR-021 — BLAS Partitioning and Single-Frame TLAS Policy

**Status:** Accepted  
**Decision type:** Ray-tracing acceleration-structure architecture  
**Primary target:** Intel Arc B580 / Vulkan 1.4  
**Related:** ADR-013, ADR-015, ADR-019, ADR-020

## Context

The renderer needs one world-space RT scene supporting:

```text
directional shadows
local-light visibility
reflections
DDGI
```

while also supporting:

```text
RMA tile reuse
tactical floor/cutaway visibility
doors and breakables
Jolt-driven rigid presentation objects
GPU-skinned actors/ragdolls
two frames in flight
```

The RT scene is presentation-only and must never feed canonical collision, LOS, pathfinding, damage or simulation state.

## Decision

Use:

```text
many purpose-built BLAS
        |
        v
one shared TLAS per FrameContext
        |
        +-- shadow rays
        +-- reflection rays
        +-- DDGI rays
```

The same TLAS is shared by all production RT lighting effects.

Effect participation is controlled by an 8-bit TLAS instance visibility mask.

## Static map partition

Static presentation-map RT geometry is partitioned by:

```text
presentation tile asset
tactical level
RT geometry class
spatial chunk when required
```

This makes tactical cutaway an instance/TLAS operation rather than an any-hit/material workaround.

Repeated RMA placements reuse the same tile-local BLAS.

## Static build policy

Static BLAS use:

```text
VK_BUILD_ACCELERATION_STRUCTURE_PREFER_FAST_TRACE_BIT_KHR
VK_BUILD_ACCELERATION_STRUCTURE_ALLOW_COMPACTION_BIT_KHR
```

They are built once at map/asset load, compacted, and retained for their lifetime.

Do not set `ALLOW_UPDATE` for ordinary static BLAS.

## Rigid object policy

Rigid doors, inline models, weapons, props and rigid debris use reusable compacted asset BLAS.

Motion is represented only by TLAS instance transforms.

Rigid transforms never require BLAS rebuilding.

## Deforming object policy

GPU-skinned/deforming objects use dynamic BLAS.

Baseline:

```text
one dynamic BLAS per deforming render object per FrameContext
full rebuild when rendered for that frame
PREFER_FAST_BUILD
no compaction
no ALLOW_UPDATE
```

Refit/update remains a B580 benchmark candidate, not the initial production path.

## TLAS policy

Baseline:

```text
one TLAS per FrameContext
full rebuild every rendered frame
PREFER_FAST_TRACE
no compaction
no ALLOW_UPDATE
```

The full rebuild is intentional because the instance set, transforms, masks and cutaway state can change.

TLAS update/refit remains benchmark-only until it proves better on the actual B580.

## Two-frame ownership

With two frames in flight:

```text
FrameContext[0] owns TLAS[0] and dynamic BLAS storage[0]
FrameContext[1] owns TLAS[1] and dynamic BLAS storage[1]
```

Do not overwrite acceleration-structure storage still referenced by an in-flight frame.

Static compacted BLAS are immutable and may be referenced by both frames.

## SBT policy

`instanceShaderBindingTableRecordOffset` is zero for baseline production instances.

Material/geometry selection does not create per-material SBT records.

Specialized RT pipelines remain small; geometry/material identity comes from:

```text
InstanceCustomIndexKHR
GeometryIndex
PrimitiveID
BDA metadata
```

## Canonical isolation

TLAS inclusion, instance masks, presentation cutaway and BLAS transforms have zero canonical authority.

Canonical systems never query remaster RT acceleration structures.

## Consequences

- world-space effects share one coherent RT scene;
- tactical cutaway is clean and consistent;
- static RMA geometry is highly reusable;
- rigid motion is cheap;
- only actual deformation pays a per-frame BLAS build;
- no per-material SBT explosion;
- full rebuilds provide a simple, measurable B580 baseline before refit experiments.
