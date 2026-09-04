# Denoiser Frame-Graph Passes and B580 Benchmark Plan

**Status:** Architecture baseline  
**Related ADR:** ADR-020

## 1. Frame-graph pass order

Relevant sequence:

```text
GBuffer
TLAS

RTDirectionalShadow
ShadowCheckerboardResolve
ShadowTemporal
ShadowFilterHorizontal
ShadowFilterVertical

ReSTIRInitial
ReSTIRTemporal
ReSTIRSpatial
RTLocalVisibility
LocalDirectCleanup
LocalDirectUpsample

DDGITrace
DDGIBlendIrradiance
DDGIBlendDistance
DDGIRelocateClassify
DDGIGather

DeferredLighting

RTReflection
ReflectionTemporal
ReflectionMomentsVariance
ReflectionAtrousStride1
ReflectionAtrousStride2
ReflectionAtrousStride4
ReflectionUpsample
ReflectionComposite
```

Passes may be skipped by effect quality/state, but dependencies remain explicit.

## 2. Shared compute baseline

Start with:

```text
workgroup = 8x8 = 64 threads
```

Use normal B580 subgroup behavior initially.

Benchmark required subgroup size:

```text
32
16
```

for:

```text
ShadowCheckerboardResolve
ShadowTemporal
ReflectionTemporal
ReflectionAtrous*
DDGIBlend*
DDGIGather
```

## 3. Shared-memory policy

Initial kernels should avoid large shared-memory/SLM tiles.

Prefer:

```text
texture/sampler cache
read-only image access
coherent dispatch ordering
small register footprints
```

Add SLM tiling only after measured B580 gains.

## 4. Precision policy

History/radiance remains FP16 where specified.

Compute intermediates use FP32 unless an explicitly validated FP16 path improves performance without visible instability.

Do not force half precision merely because the B580 supports it.

## 5. Timestamp requirements

Measure each pass independently:

```text
ShadowCheckerboardResolve
ShadowTemporal
ShadowFilterH
ShadowFilterV

ReSTIRInitial
ReSTIRTemporal
ReSTIRSpatial
LocalVisibility
LocalDirectCleanup
LocalDirectUpsample

DDGITrace
DDGIBlendIrradiance
DDGIBlendDistance
DDGIRelocateClassify
DDGIGather

ReflectionTrace
ReflectionTemporal
ReflectionMomentsVariance
ReflectionAtrous1
ReflectionAtrous2
ReflectionAtrous4
ReflectionUpsample
ReflectionComposite
```

## 6. Provisional effect budget

Previous RT architecture starting targets remain:

```text
directional + local direct RT/reconstruction:
    <= 2.0 ms

reflections + reconstruction:
    <= 2.1 ms

DDGI update + gather:
    <= 0.7 ms
```

These are benchmark targets, not measured performance.

## 7. Quality stability metrics

Benchmark not only average GPU time but:

```text
history rejection rate
history age distribution
variance
disocclusion recovery frames
ghosting severity
reflection sharpness loss
shadow edge lag
DDGI lighting response time
```

## 8. Test motions

Include:

```text
slow camera pan
fast 180-degree camera rotation
zoom change
floor/cutaway change
door open/close
breakable destruction
actor sprint
ragdoll movement
fast moving light
muzzle flash
large emissive VFX
```

## 9. Reflection-specific benchmark matrix

Compare:

```text
primary motion only
secondary-hit motion
roughness-blended primary/secondary motion
```

Compare history maxima:

```text
4/16
4/24
8/24
```

Compare à-trous:

```text
2 iterations
3 iterations
```

Compare required subgroup:

```text
16
32
```

## 10. Shadow benchmark matrix

Compare:

```text
checkerboard patterns
history length 8/16
penumbra history 2/4/8
7-tap separable vs compact 5-tap
subgroup 16/32
```

## 11. ReSTIR benchmark matrix

Compare:

```text
fresh candidates:
    2 / 4 / 8

spatial reservoirs:
    0 / 2 / 4

spatial radius:
    4 / 8 / 16 half-res pixels

M clamp:
    10x / 20x / 40x
```

Final visibility remains world-space RT in every production candidate.

## 12. DDGI benchmark matrix

Compare:

```text
probe updates/frame:
    128 / 256 / 512

rays/probe:
    64 / 96 / 128

stable hysteresis:
    0.95 / 0.97 / 0.985

dirty hysteresis:
    0.75 / 0.85 / 0.90

subgroup:
    16 / 32
```

## 13. Acceptance criterion

A faster variant is accepted only if it:

```text
preserves world-space truth
does not create objectionable temporal lag/ghosting
fits the 60 FPS budget more reliably
does not increase canonical coupling
```

Benchmark result, not generic GPU folklore, decides B580 tuning.

## XMX/cooperative-matrix scope

The B580 hardware reference records 160 XMX engines.

Architecture 073 keeps XMX/cooperative matrices non-baseline for the current temporal/edge-aware/à-trous denoisers.

A matrix path is investigated only if a future reconstruction stage maps naturally to matrix operations and wins target quality/performance measurements.
