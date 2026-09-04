# Shared Temporal Validation and Directional Shadow Reconstruction

**Status:** Implementation specification baseline  
**Related ADR:** ADR-020

## 1. Shared previous-frame surface cache

Preserve:

```text
PreviousDepth      VK_FORMAT_R32_SFLOAT
PreviousNormal     VK_FORMAT_R16G16_SNORM
PreviousRoughness  VK_FORMAT_R8_UNORM
PreviousObjectId   VK_FORMAT_R32_UINT
```

Current motion vectors come from jittered current/previous projections:

```text
G3 = VK_FORMAT_R16G16_SFLOAT
velocity = previousJitteredUV - currentJitteredUV
```

Reprojection:

```text
previousUV = currentUV + velocity
```

`worldToClip` includes current jitter and `previousWorldToClip` includes previous jitter.

Temporal passes do not add a jitter delta a second time.

Exact semantics are owned by architecture 057.

## 2. Temporal sample search

For each current pixel:

```text
1. reproject to previousUV
2. test the four surrounding previous-frame texels individually
3. if no valid sample remains, test a wider 3x3 neighborhood
4. if still invalid, declare disocclusion and discard history
```

No bilinear interpolation across invalid geometry boundaries.

## 3. Shared surface validation

Starting validation criteria:

```text
previousUV inside viewport
object ID match
normal compatibility
depth/plane compatibility
motion validity
```

Starting normal threshold:

```text
dot(currentNormal, previousNormal) >= 0.90
```

Starting depth/plane tolerance:

```text
max(
    1.5 * worldPixelRadius,
    0.0025 * viewDistance
)
```

These are initial values subject to visual/B580 validation.

For fast skeletal/rigid motion, aggressive rejection is preferred over ghosting.

## 4. Directional shadow raw output

RT directional shadow emits:

```text
ShadowRaw
VK_FORMAT_R16G16_SFLOAT
```

Channels:

```text
R = visibility
    0 blocked
    1 visible

G = penumbra radius in world units

G < 0 means:
    pixel was not ray-sampled in the current checkerboard pattern
```

## 5. Penumbra estimate

Convert raw blocker/hit distance to a useful penumbra estimate immediately after trace.

Starting approximation:

```text
penumbraWorld =
    tan(lightAngularRadius)
    * receiverToBlockerDistance
```

The exact finite-light model may be refined without changing the history ABI.

## 6. Shadow reconstruction passes

```text
RTDirectionalShadow
        |
        v
ShadowCheckerboardResolve
        |
        v
ShadowTemporal
        |
        v
ShadowFilterHorizontal
        |
        v
ShadowFilterVertical
        |
        v
ShadowVisibilityFullRes
```

## 7. Checkerboard resolve

Operate at full active RenderExtent resolution (1920x1080 in the qualification profile).

Unsampled pixels gather a 3x3 neighborhood of sampled neighbors.

Accept neighbors only when surface-compatible by:

```text
depth/plane
normal
object/material edge confidence
```

Produce a complete current-frame estimate:

```text
visibility
penumbraWorld
confidence
```

## 8. Shadow history

Persistent resources:

```text
ShadowHistory
    VK_FORMAT_R16G16_SFLOAT
    R visibility
    G penumbraWorld

ShadowMoments
    VK_FORMAT_R16G16_SFLOAT
    R first visibility moment
    G second visibility moment

ShadowHistoryLength
    VK_FORMAT_R8_UINT
```

Moments:

```text
m1 = E[x]
m2 = E[x^2]
variance = max(m2 - m1*m1, 0)
```

## 9. History limits

Starting maximum history:

```text
visibility:
    16 frames

penumbra:
    4 frames
```

Penumbra must respond faster than the averaged visibility term.

## 10. History clamp

Before temporal blend:

```text
compute current 3x3 visibility mean/variance
clamp reprojected visibility history to:

mean - 2*sigma
...
mean + 2*sigma
```

Clamp penumbra independently to a local min/max range.

## 11. Shadow temporal blend

History weight increases with:

```text
valid history length
surface confidence
stable motion
```

History weight decreases with:

```text
disocclusion
large blocker/penumbra change
large motion
lighting/cutaway invalidation
```

Exact weight curve remains tunable.

## 12. Spatial shadow filtering

Use two separable passes:

```text
horizontal
vertical
```

Starting kernel:

```text
7 taps each pass
```

Dynamic radius:

```text
radiusPixels =
    clamp(
        penumbraWorld / worldPixelSize,
        1,
        12
    )
```

Weights:

```text
spatial kernel
depth-plane similarity
normal similarity
```

Object ID is not a mandatory hard spatial boundary, because adjacent BSP/render clusters may form one continuous surface.

## 13. Invalidations

Reset or sharply reduce shadow history on:

```text
camera cut
tactical cutaway topology change affecting sample
object generation change
large world transform discontinuity
sun/light direction discontinuity
renderer resize
HDR/SDR mode switch only if history storage changes
```

Normal camera pans/rotation do not globally clear the history.

## Screen-space mapping authority

Architecture 063 supplies the exact clip/NDC->render-UV helper used by all temporal reprojection.

No shadow/reflection/ReSTIR temporal pass introduces its own Y flip.
