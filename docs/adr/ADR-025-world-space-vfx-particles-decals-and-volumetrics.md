# ADR-025 — World-Space VFX, Particles, Decals and Volumetrics

**Status:** Accepted  
**Decision type:** Presentation VFX architecture  
**Primary target:** Intel Arc B580 / Vulkan 1.4  
**Related:** ADR-001, ADR-007, ADR-019, ADR-020, ADR-021

## Context

The remaster needs a modern VFX system for:

```text
muzzle flashes
weapon impacts
sparks
smoke
dust
blood
scorch marks
beams/tracers
volumetric effects
temporary lights
rigid presentation debris
```

while preserving the project-wide invariant:

```text
presentation may react to canonical events
presentation may never become canonical authority
```

## Decision

Split VFX into four main runtime classes:

```text
GPU particles
world-space decals
world-space volumetric emitters
Jolt-backed rigid debris
```

Additional presentation primitives:

```text
ribbons/beams/tracers
transient world-space lights
```

All originate from ordered PresentationEvents or Presentation World state.

## Authority rule

VFX never decides:

```text
damage
hit results
collision
LOS
cover
AI
routing
pathfinding
mission state
```

A canonical event may spawn VFX.

VFX output never feeds canonical state.

## GPU particles

Most high-count particles execute entirely on the GPU after a CPU spawn command.

Baseline limits:

```text
262,144 live particles
32,768 spawns/frame
65,536 sorted alpha-visible particles
131,072 additive-visible particles
```

These are renderer capacity/budget values.

## Particle collision

Do not use screen-depth collision as the baseline.

Ordinary sparks/smoke/dust usually have no collision.

Physical shell casings/chunks use Jolt.

Do not add RayQuery solely to make cosmetic particles bounce.

## Decals

Persistent decals are world-space projector volumes.

They modify material G-buffer data but do not modify:

```text
depth
motion vectors
object identity
canonical geometry
```

Significant decals may participate in bounded RT-hit material reconstruction.

## Volumetrics

Major smoke/fog is represented by world-space volume emitters.

A froxel grid is a reconstruction/integration representation, not the authoritative source of density.

Baseline froxel grid:

```text
160 x 90 x 64
```

## Rigid debris

Physical secondary fragments use presentation-only Jolt bodies.

Starting active rigid-debris cap:

```text
256
```

Overflow degrades low-value rigid debris into non-physical VFX.

## Transient VFX lights

Explosions and other important luminous effects emit explicit world-space `GpuLight` entries.

They participate in the existing world-space direct-light/RT system.

Do not infer important lighting from alpha sprite pixels.

Starting transient-light cap:

```text
256
```

## Cutaway

Presentation cutaway affects rendering/injection visibility.

It does not pause VFX lifetimes or change canonical state.

## Consequences

- high particle counts remain GPU-driven;
- physical debris is bounded and isolated in Jolt;
- decals remain consistent in raster and important RT hits;
- volumetric effects are world-space rather than sprite-only;
- VFX lighting participates in actual world-space lighting;
- no screen-space-only VFX physics is introduced.

## Baseline 030 production-ABI closure

Architecture 085 fixes the first explicit particle state/material records. Any later compact GPU format is separately versioned and benchmark-gated. The accepted VFX ownership, capacities and non-authoritative boundaries above are unchanged.
