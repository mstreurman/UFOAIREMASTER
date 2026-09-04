# ADR-019 — World-Space Ray-Traced Lighting Policy

**Status:** Accepted  
**Decision type:** Renderer lighting/visibility architecture  
**Primary target:** Intel Arc B580 / Vulkan 1.4 hardware RT  
**Related:** ADR-015, ADR-017, ADR-018

## Context

The remaster is explicitly targeting hardware ray tracing on Intel Arc B580.

The project does not want lighting effects whose visibility/radiance solution is fundamentally limited to what is already present in the current camera depth/color buffers.

The renderer still benefits from screen-space data for:

- ray launch points;
- motion-vector reprojection;
- temporal history;
- denoising;
- edge-aware reconstruction;
- object/history validation.

Those uses do not need to define the underlying visibility truth.

## Decision

The renderer follows this rule:

```text
WORLD-SPACE TRUTH
SCREEN-SPACE RECONSTRUCTION
```

Meaning:

1. Primary camera visibility is rasterized.
2. Secondary visibility/radiance uses world-space scene data through TLAS/BLAS or world-space lighting structures.
3. Screen-space history/filtering may reconstruct sparse/noisy results.
4. Screen-space methods must not become the authoritative source for shadows, reflections, AO or diffuse GI.

## Baseline world-space techniques

Use:

```text
hardware RT directional shadows
hardware RT local-light visibility
hardware RT reflections
world-space DDGI diffuse GI
world-space environment/sky fallback
```

## Not part of baseline

Do not use as baseline lighting solutions:

```text
SSR
SSAO
SSGI
screen-space contact shadows
screen-space-only reflection fallback
depth-buffer-only secondary visibility
```

These may exist only as debugging/comparison experiments unless this ADR is intentionally revised.

## Reflection miss policy

A reflection miss resolves to world/environment radiance:

```text
RT reflection
    |
    +-- hit  -> shade actual world-space hit
    |
    +-- miss -> environment / sky / world radiance
```

Do not fall back to SSR.

## Screen-space processing allowed

Allowed reconstruction inputs include:

```text
depth
normal
roughness
motion vectors
object ID
hit distance
previous-frame radiance
confidence/history length
```

These may be used for:

```text
temporal accumulation
history rejection
variance estimation
spatial denoising
half-resolution reconstruction
checkerboard reconstruction
```

The reconstruction stage may smooth/estimate a ray-traced signal.

It must not fabricate off-screen geometry visibility from the depth buffer.

## GI

Diffuse GI baseline is world-space DDGI.

This choice prioritizes:

- camera-independent lighting history;
- stability under tactical camera pans/rotations;
- persistence across view changes;
- efficient fixed ray budgets independent of 1080p pixel count.

Screen-space GI is not the fallback.

## Consequences

The renderer spends hardware RT budget on actual scene traversal rather than reproducing traditional screen-space approximations.

Quality scaling reduces world-space ray frequency/resolution before introducing screen-space-only substitutes.
