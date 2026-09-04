# ReSTIR DI History and Local Direct Reconstruction

**Status:** Implementation specification baseline  
**Related ADR:** ADR-020

## 1. Principle

ReSTIR reservoir reuse is the primary temporal reconstruction for local direct lighting.

Do not add a second long-lived radiance accumulator after the final local visibility ray.

## 2. Reservoir ABI

Starting 32-byte record:

```cpp
struct DirectReservoir {
    uint32_t lightId;
    uint32_t lightGeneration;

    uint32_t sampleParam0;
    uint32_t sampleParam1;

    float weightSum;
    float selectedTarget;
    float finalWeight;

    uint32_t packedMAgeFlags;
};

static_assert(sizeof(DirectReservoir) == 32);
```

Exact `packedMAgeFlags` bit allocation and sample-parameter encoding are defined by architecture 057.

Shader reflection verifies the 32-bit field's location/size; it does not invent packed semantic bit allocation.

## 3. Half-resolution domain

Baseline local-direct resolution:

```text
HalfRenderExtent = ceil(RenderExtent / 2)
qualification example = 960x540
```

Persistent reservoir buffers are double-buffered for two temporal states.

## 4. Initial candidates

Starting baseline:

```text
8 fresh light candidates per half-resolution pixel
```

Architecture 067 owns the exact deterministic local-light alias proposal, qLight/qShape/qFresh, target and weighted-reservoir math.

Candidate generation itself does not trace visibility rays.

## 5. Temporal reuse

Reproject using primary-surface motion.

Select one compatible previous reservoir.

Validate:

```text
surface reprojection valid
depth/plane compatibility
normal compatibility
light ID still exists
light generation still matches
light remains active/eligible
```

A reservoir from a destroyed/recycled light is invalid.

## 6. Temporal M clamp

Prevent old reservoirs from accumulating unbounded effective sample count.

Starting clamp:

```text
previous.M <= 20 * current.M
```

The exact constant remains benchmark-tunable.

## 7. Spatial reuse

Starting baseline:

```text
4 spatial reservoir candidates
radius = 8 half-resolution pixels
deterministic 8-direction rotated pattern
```

Compatibility tests:

```text
depth plane
world normal
surface orientation
material/light eligibility
```

Do not spatially reuse across obviously unrelated geometry.

## 8. Final visibility

After temporal/spatial reservoir selection:

```text
one selected local-light sample
    |
    v
one world-space RT visibility ray
```

The RT visibility result is incorporated into the direct-light estimator.

No screen-space occlusion fallback.

## 9. Local direct cleanup

After visibility:

```text
one 3x3 edge-aware half-resolution cleanup pass
```

This pass is intentionally small.

Inputs:

```text
direct radiance
depth
normal
roughness
object ID
reservoir/sample confidence
```

## 10. Full-resolution upsample

Guided `HalfRenderExtent -> RenderExtent` upsample (960x540 -> 1920x1080 in the qualification profile).

Weights:

```text
bilinear distance
depth plane
normal
roughness
object ID preference
```

Object ID is a strong edge signal but may be softened for continuous static geometry where necessary.

## 11. History invalidation

Reservoir history invalidates on:

```text
camera cut
resolution/layout change
light generation change
major light-list rebuild
presentation cutaway change affecting visibility/light eligibility
surface disocclusion
```

Normal light motion does not automatically invalidate the reservoir if the light generation remains stable; the target PDF/weight update handles the changed configuration.

## 12. Debug outputs

Required:

```text
selected light ID
reservoir M
reservoir age
weightSum
finalWeight
temporal-source accepted/rejected
spatial-source IDs
visibility result
half-res radiance
full-res upsampled radiance
```

## Light identity authority

Architecture 057 owns `lightId + lightGeneration` allocation/reuse semantics.

Architecture 059 owns the revised `GpuLight` record carrying both values.

## Exact estimator authority

Architecture 067 owns proposal, target, fresh/temporal/spatial weights, M saturation, finalWeight, final RGB estimator and sample codecs.

Architecture 068 owns deterministic random stream assignment.
