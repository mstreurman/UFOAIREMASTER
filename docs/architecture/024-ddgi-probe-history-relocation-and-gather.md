# DDGI Probe History, Relocation, Classification and Gather

**Status:** Implementation specification baseline  
**Related ADR:** ADR-020

## 1. Principle

DDGI temporal filtering occurs in world-space probe state.

Do not add a screen-space GI temporal denoiser after gather.

## 2. Probe data

Initial logical resources:

```text
DDGIRayData
    VK_FORMAT_R16G16B16A16_SFLOAT

    RGB = traced scene-linear ACEScg radiance
    A   = signed hit-distance/backface indicator

DDGIIrradiance
    VK_FORMAT_R16G16B16A16_SFLOAT

    RGB = scene-linear ACEScg irradiance
    A   = reserved/confidence

DDGIDistance
    VK_FORMAT_R16G16_SFLOAT

    R = mean distance
    G = second distance moment

DDGIProbeMetadata
    structured GPU buffer using exact `GpuDdgiProbeMetadata`

DDGIVolumeMetadata
    structured GPU buffer using exact `GpuDdgiVolume`
```

The exact records are defined by architecture 057 and addressed from the per-FrameContext `GpuSceneRoot` defined by architecture 059.

Irradiance remains scene-linear ACEScg.

No gamma encoding is used for the baseline FP16 probe representation.

## 3. Octahedral storage

Starting probe texel resolution:

```text
irradiance:
    8x8 octahedral

distance:
    16x16 octahedral
```

Physical atlas allocation remains an allocator implementation detail, but shader-visible addressing is exact:

```text
GpuDdgiProbeMetadata stores absolute irradiance/distance tile origins
irradiance tile = 8x8
distance tile   = 16x16
```

Repacking updates metadata/history coherently at an allowed reset boundary.

## 4. Probe trace ray classes

Per updated probe:

```text
lighting rays
fixed relocation/classification rays when required
```

Starting lighting budget:

```text
128 rays/probe
```

When relocation/classification is active, reserve:

```text
32 fixed rays/probe
```

Fixed rays are not blended as ordinary lighting samples.

## 5. Probe irradiance blend

For each irradiance texel:

```text
newValue =
    lerp(
        newSample,
        previousValue,
        hysteresis
    )
```

Starting hysteresis:

```text
stable probe:
    0.97

new/reset probe:
    0.0

lighting-dirty probe:
    0.85
```

Lighting-dirty probes ramp toward 0.97 over approximately eight successful updates.

Exact ramp curve is tunable.

## 6. Probe distance blend

Distance moments maintain visibility/leak-reduction information.

Use independent hysteresis rather than blindly sharing irradiance history weights if scene geometry changed.

A probe relocation or nearby geometry topology change sharply reduces/reset distance history.

## 7. Probe relocation

Probe relocation uses fixed diagnostic rays to detect probes:

```text
inside geometry
too near surfaces
in invalid cavities
```

Relocation changes only presentation GI probe position.

It does not affect canonical tactical positions/collision.

After meaningful relocation:

```text
reset or strongly reduce irradiance history
reset distance history
reset confidence/age
```

## 8. Probe classification

Classify probes at least:

```text
Active
InactiveInsideGeometry
InactiveOutsidePresentationRegion
NeedsRelocation
```

Inactive probes are not included in normal update scheduling/gather.

Exact enum may gain states later.

## 9. Probe scheduling

Starting priority:

```text
1. newly activated/reset probes
2. lighting-dirty probes
3. probes near active/visible tactical region
4. oldest normal probes
```

Visibility affects scheduling priority only.

It does not alter world-space ray traversal truth.

## 10. Lighting-dirty marking

Presentation lighting changes mark nearby probes dirty.

Candidates:

```text
light created/destroyed
large light transform/radius/intensity change
door/breakable presentation visibility change
major emissive state change
tactical cutaway RT visibility change
```

Exact dirty radius/propagation policy remains tunable.

## 11. Gather

Full-resolution visible surfaces gather DDGI using:

```text
world position
world normal
probe positions
irradiance
distance moments
probe validity
```

Interpolation weights include:

```text
trilinear/spatial weight
normal-facing weight
visibility/distance weight
probe activity/confidence
```

No depth-buffer-only GI visibility approximation.

## 12. Multi-bounce feedback

Probe ray-hit shading may include previous DDGI irradiance.

This provides approximate multi-bounce diffuse feedback without recursive diffuse RT.

Prevent unstable energy growth through:

```text
BRDF energy conservation
bounded feedback contribution
history reset on invalid topology/lighting changes
```

Exact feedback gain remains a benchmark/artistic parameter.

## 13. Cutaway handling

When presentation cutaway hides floors/geometry:

```text
RT instance visibility updates
probe dirty marking
affected probe history confidence reduction/reset
```

Canonical LOS/pathfinding remain untouched.

## 14. Camera changes

Camera pan/rotation/zoom:

```text
do not invalidate DDGI world history
```

Only probe-region activation priorities may change.

This is a primary reason DDGI is used instead of screen-space GI.

## 15. Debug views

Required:

```text
probe position
probe state/classification
probe relocation offset
probe age
probe hysteresis
dirty state
irradiance octahedron
distance moments
ray directions
backface/fixed-ray result
full-resolution gather contribution
```

## 12. Warm-start persistence

ADR-044 accepts a disposable `RDGI` disk cache for compatible DDGI history. Architecture 088 owns the exact cache container, identity key, location, validation and atomic-write rules.

Warm-start data may seed:

```text
probe relocation/classification state
irradiance history
distance-moment history
```

It never changes scheduling truth, canonical geometry, gameplay state or the validity rules above. Rejected/missing caches simply start from reset history and converge normally.

