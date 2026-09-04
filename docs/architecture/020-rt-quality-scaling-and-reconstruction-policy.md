# RT Quality Scaling and Reconstruction Policy

**Status:** Architecture baseline  
**Related:** ADR-019, architecture/019

## 1. Quality principle

Primary qualification raster profile remains:

```text
RenderExtent = 1920x1080
target = near 60 FPS
```

Runtime RenderExtent is selectable; RT launch/reconstruction dimensions derive from the active RenderExtent.

RT effects may use sparse/checkerboard/half-resolution launch grids while still tracing full world-space geometry.

Reducing launch density is allowed.

Replacing RT with screen-space-only approximations is not the baseline quality strategy.

## 2. Screen-space reconstruction

Allowed reconstruction signals:

```text
depth
world normal
roughness
motion vector
object ID
hit distance
sample confidence
history length
previous radiance/visibility
```

Reconstruction may use:

```text
temporal reprojection
history rejection
variance estimation
edge-aware spatial filtering
checkerboard resolve
half-resolution upsampling
```

## 3. History rejection

Reject or strongly downweight history when:

```text
object ID changes
depth mismatch exceeds threshold
normal mismatch exceeds threshold
motion is invalid
surface roughness/material class changes materially
presentation cutaway state changes
RT instance visibility changed incompatibly
```

Exact thresholds remain denoiser design parameters.

## 4. Directional-shadow scaling ladder

Protect directional shadows strongly for tactical readability.

Baseline:

```text
0.5 rpp checkerboard at active RenderExtent (1080p in the qualification profile)
```

Scaling order:

```text
1. reduce soft-shadow sample angular variance/quality
2. reduce temporal refresh density
3. lower launch density only as a later step
```

Do not replace with screen-space contact shadows.

## 5. Local-light scaling ladder

Baseline:

```text
half-res ReSTIR DI
1 final RT visibility ray/pixel
```

Scaling order:

```text
8 fresh candidates -> 4 -> 2
4 spatial reservoirs -> 2 -> 0
half-res full sampling -> half-res checkerboard
reduce eligible local-light set by contribution
```

Do not replace final world-space visibility with screen-space occlusion.

## 6. Reflection scaling ladder

Baseline:

```text
half-res
one primary GGX ray
<= 0.5 secondary visibility average
```

Scaling order:

```text
1. disable secondary direct visibility
2. tighten roughness eligibility
3. reduce reflection launch density/checkerboard
4. reduce maximum reflection distance where visually acceptable
```

Reflection misses remain environment/world-space, never SSR.

## 7. DDGI scaling ladder

Baseline:

```text
512 probe updates/frame
128 rays/probe
```

Scaling order:

```text
512 -> 256 -> 128 probes/frame

then if necessary:
128 -> 96 -> 64 rays/probe
```

Probe density itself is a level/build-time quality choice and should not thrash dynamically every frame.

## 8. GPU-time-driven scaling

Ray count is diagnostic.

GPU time is authoritative.

Track at minimum:

```text
directional RT traversal
directional reconstruction
ReSTIR candidate/reuse
local visibility
reflection traversal
reflection reconstruction
DDGI trace
DDGI update
DDGI gather
```

Quality changes should react to sustained budget misses, not one-frame spikes.

Exact hysteresis/adaptation policy remains open.

## 9. Per-effect history

Each effect owns independent history validity.

Do not share one global "RT history valid" flag.

Examples:

```text
shadow history
local-light reservoir history
reflection radiance history
DDGI probe history
```

A cutaway-level change may invalidate reflections/shadows for changed geometry without discarding unrelated DDGI probes.

## 10. World-space data survives camera changes

Camera pan/rotation may invalidate/reduce screen-space temporal samples.

It does not invalidate:

```text
TLAS/BLAS world geometry
DDGI world probe state
environment/world radiance
persistent light state
```

This is a core benefit of the world-space policy.

## 11. Debug modes

Required debug visualization:

```text
RT launch mask
shadow visibility
shadow hit distance
ReSTIR selected light ID
ReSTIR reservoir age/weight
reflection hit/miss
reflection hit distance
reflection roughness eligibility
DDGI probe positions
DDGI update age
DDGI irradiance
DDGI distance/visibility
RT history confidence
RT ray count per pass
```

## 12. Benchmark scenes

The B580 benchmark suite should include:

```text
open outdoor map with long sun rays
dense indoor map with many local lights
highly reflective UFO interior
alpha-tested foliage/fence stress
large RMA assembly
dynamic actor-heavy scene
door/breakable/cutaway transition
emissive-heavy combat/VFX scene
```

Each records:

```text
ray counts
GPU timestamps
TLAS/BLAS time
RT shader time where tooling exposes it
bandwidth/memory pressure
visual error/stability
```

## 13. Non-baseline experiments

Allowed research modes:

```text
ReSTIR GI
RayQuery comparator
screen-space techniques as debug/reference comparators
mesh-shader visibility
cooperative-matrix denoiser research
```

They are not production fallback paths unless separately accepted.
