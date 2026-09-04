# Reflection Temporal, Variance and À-Trous Reconstruction

**Status:** Implementation specification baseline  
**Related ADR:** ADR-020  
**Input resolution:** HalfRenderExtent = ceil(RenderExtent / 2)  
**Qualification example:** 960x540 -> RenderExtent 1920x1080

## 1. Raw reflection outputs

The reflection trace produces:

```text
ReflectionRawRadiance
    VK_FORMAT_R16G16B16A16_SFLOAT

    RGB = scene-linear ACEScg reflection estimator
    A   = hit distance

ReflectionHitId
    VK_FORMAT_R32_UINT

ReflectionSecondaryMotion
    VK_FORMAT_R16G16_SFLOAT
```

Miss ID:

```text
0xffffffff
```

## 2. Secondary motion

For a reflection hit, use:

```text
instance ID
primitive ID
barycentrics
```

to reconstruct the hit's previous world-space position from previous instance/skinning data.

Project that position into the previous camera to obtain:

```text
secondaryPrevUV
```

Primary surface motion provides:

```text
primaryPrevUV
```

## 3. Motion blend

Starting rule:

```text
r = saturate(roughness / 0.65)
secondaryWeight = (1 - r)^2

previousUV =
    lerp(
        primaryPrevUV,
        secondaryPrevUV,
        secondaryWeight
    )
```

Meaning:

```text
sharp reflection:
    track reflected hit strongly

rough reflection:
    increasingly track primary surface
```

## 4. Reflection temporal validation

Use shared 2x2 previous-tap validation with 3x3 fallback.

Additional reflection-specific checks follow.

### Normal threshold

Starting roughness-dependent threshold:

```text
angle =
    lerp(
        5 degrees,
        25 degrees,
        saturate(roughness / 0.65)
    )

dot(Ncurrent, Nprevious) >= cos(angle)
```

### Roughness

Starting tolerance:

```text
abs(currentRoughness - previousRoughness)
<=
0.05 + 0.10 * currentRoughness
```

### Hit distance

Starting logarithmic compatibility:

```text
abs(
    log2(
        (currentHitT + epsilon)
        /
        (historyHitT + epsilon)
    )
)
<
lerp(
    0.25,
    1.0,
    saturate(roughness / 0.65)
)
```

### Secondary object ID

For:

```text
roughness < 0.20
```

require:

```text
current secondary hit object == previous secondary hit object
```

or both must be misses.

For rougher surfaces, an ID change reduces confidence rather than forcing an unconditional reject.

## 5. Reflection history resources

Persistent:

```text
ReflectionHistoryRadiance
    VK_FORMAT_R16G16B16A16_SFLOAT

ReflectionMoments
    VK_FORMAT_R16G16_SFLOAT

ReflectionHistoryLength
    VK_FORMAT_R8_UINT

ReflectionHistoryHitId
    VK_FORMAT_R32_UINT
```

Moments are luminance moments:

```text
m1 = E[luminance]
m2 = E[luminance^2]
variance = max(m2 - m1*m1, 0)
```

## 6. Roughness-dependent history

Starting maximum history:

```text
r = saturate(roughness / 0.65)

maxHistory =
    round(
        lerp(
            4,
            24,
            r*r
        )
    )
```

Interpretation:

```text
near-mirror:
    about 4 frames

medium roughness:
    about 9..15 frames

rough eligible reflection:
    up to 24 frames
```

Sharp deterministic rays should react quickly.

Noisy rough reflections receive longer accumulation.

## 7. Reflection history clamp

Before blend:

```text
current 3x3 half-resolution neighborhood
    |
    v
luminance mean + variance
    |
    v
clamp reprojected history luminance to
mean +/- 2*sigma
```

Preserve chroma direction as much as practical while clamping luminance magnitude.

Exact chroma-clamp method remains tunable.

## 8. Reflection temporal pass

Output:

```text
temporally accumulated radiance
updated hit distance
updated moments
history length
confidence
```

High-confidence stable samples receive stronger history.

Disocclusion or failed secondary-hit validation favors current data.

## 9. À-trous spatial filtering

Operate at HalfRenderExtent (960x540 in the qualification profile).

Three starting iterations:

```text
iteration 0:
    stride 1

iteration 1:
    stride 2

iteration 2:
    stride 4
```

Each uses a sparse 5x5 kernel.

Weight product:

```text
w =
    spatial
  * depth
  * normal
  * roughness
  * hitDistance
  * luminanceVariance
```

## 10. Roughness-dependent filter count

Starting policy:

```text
roughness < 0.08:
    no broad à-trous blur

0.08 <= roughness <= 0.30:
    iterations stride 1 and 2

roughness > 0.30:
    iterations stride 1, 2 and 4
```

A small prefilter may still run for isolated fireflies even on near-mirror surfaces.

## 11. Hit-distance weighting

Hit-distance similarity should become more permissive as roughness increases.

Sharp reflections strongly reject unrelated hit distances.

Rough reflections may blend a wider spatial hit distribution.

Exact function is benchmark-tunable.

## 12. Full-resolution upsample

Guided reconstruction:

```text
HalfRenderExtent
    ->
RenderExtent

qualification example: 960x540 -> 1920x1080
```

Use a 3x3 half-resolution neighborhood.

Weights:

```text
bilinear location
depth plane
normal
roughness
object ID
history confidence
```

For very sharp reflections, object ID is effectively a hard edge.

For rough surfaces it is a strong but not absolute weight.

## 13. Composite

Full-resolution denoised reflection remains:

```text
linear ACEScg
```

Composite through the physically based reflection term into the HDR scene.

Do not treat denoised radiance as already tone-mapped/display data.

## 14. Required debug views

```text
raw radiance
raw hit distance
secondary hit ID
secondary motion
selected temporal motion
history accepted/rejected
history length
moments
variance
history confidence
à-trous iteration output
full-res upsample
```
