# ADR-020 — Effect-Specific RT Denoising and Reconstruction

**Status:** Accepted  
**Decision type:** RT reconstruction / temporal filtering  
**Primary target:** Intel Arc B580 / Vulkan 1.4  
**Related:** ADR-019

## Context

The renderer produces several sparse/noisy world-space lighting signals:

- directional RT shadow visibility;
- local direct-light estimates from ReSTIR DI;
- half-resolution one-bounce RT reflections;
- world-space DDGI probe lighting.

These signals have different statistical behavior and different notions of valid history.

A single generic denoiser would either over-blur sharp signals or fail to stabilize noisy radiance.

## Decision

Use separate reconstruction paths:

```text
Directional shadow:
    shadow-specific temporal + penumbra-aware spatial filtering

Local direct:
    ReSTIR reservoir temporal/spatial reuse
    plus minimal edge-aware cleanup/upsample

Reflections:
    radiance temporal accumulation
    moments/variance
    roughness-aware à-trous filtering
    guided full-resolution upsample

DDGI:
    world-space probe hysteresis
    distance/visibility filtering
    no screen-space temporal denoiser
```

## One temporal feedback system per signal

The renderer does not stack independent long temporal histories for one signal.

Baseline ownership:

```text
Directional shadow -> shadow history
Local direct        -> ReSTIR reservoir history
Reflections         -> reflection radiance history
DDGI                -> probe history/hysteresis
```

This reduces latency and ghosting.

## Shared temporal surface validation

Screen-space reconstruction may use a common previous-frame surface cache:

```text
linear/view depth
world normal
roughness
object ID
motion vectors
```

These data validate whether a previous screen-space sample still corresponds to the same visible surface.

They do not define world-space visibility.

## World-space policy preserved

All reconstructed signals originate from:

```text
world-space RT traversal
or
world-space DDGI probes
```

Screen-space processing may reconstruct/filter those signals only.

The renderer still follows:

```text
WORLD-SPACE TRUTH
SCREEN-SPACE RECONSTRUCTION
```

## B580 execution policy

Initial compute reconstruction uses:

```text
8x8 workgroups
default subgroup behavior
```

Benchmark:

```text
required subgroup 32
vs
required subgroup 16
```

for hot reconstruction kernels.

Large shared-memory/SLM tiling is not assumed initially.

## Consequences

- shadows retain contact/edge quality;
- local direct does not acquire a second long radiance history on top of reservoirs;
- sharp reflections react quickly;
- rough reflections accumulate longer histories;
- DDGI survives camera changes independently of screen-space histories.
