# Vulkan Screen-Space, Index and Skin-Format Contract

**Status:** Exact implementation specification  
**Related ADR:** ADR-030  
**Related architecture:** 017, 018, 051, 057, 059, 060

## 1. Vulkan viewport

Baseline uses:

```text
viewport.x      = 0
viewport.y      = 0
viewport.width  = RenderExtent.width
viewport.height = RenderExtent.height
minDepth        = 0
maxDepth        = 1
```

No negative-height viewport is used.

## 2. Clip to NDC

```text
ndc = clip.xyz / clip.w
```

Accepted depth:

```text
0..1
reversed-Z projection
```

## 3. NDC to rendered UV

```text
renderUV.x = ndc.x * 0.5 + 0.5
renderUV.y = ndc.y * 0.5 + 0.5
```

Therefore:

```text
renderUV (0,0) = top-left
+U = right
+V = down
```

The projection builder owns the sign needed so camera/world visual up appears toward decreasing render-UV Y.

No later pass flips Y again.

## 4. Pixel centers

Pixel `(x,y)` center:

```text
pixelUV =
    ((x + 0.5) / RenderExtent.width,
     (y + 0.5) / RenderExtent.height)
```

Integer pixel-to-UV conversion uses this convention unless a pass explicitly samples texel corners for a mathematical reason.

## 5. Projection jitter

`jitterCurrentPrevious` stores NDC offsets.

Apply current jitter during projection:

```text
clip.xy += jitterNdc.xy * clip.w
```

With the accepted NDC->UV map:

```text
+jitterX moves right
+jitterY moves down
```

in rendered UV.

## 6. Motion vectors

```text
currentJitteredUV
previousJitteredUV

velocity =
    previousJitteredUV - currentJitteredUV
```

Reprojection:

```text
previousUV = currentUV + velocity
```

No extra viewport Y inversion or jitter-delta correction is applied afterward.

## 7. Reference helper

Shared semantic helper:

```cpp
float2 RenderUvFromClip(float4 clip) {
    float2 ndc = clip.xy / clip.w;
    return ndc * 0.5f + 0.5f;
}
```

C++ reference tests and Slang use equivalent arithmetic.

## 8. GpuIndexType

```cpp
enum GpuIndexType : uint32_t {
    UInt16 = 0,
    UInt32 = 1
};
```

`GpuMesh.indexType` uses this enum.

RT `indexTypeAndFlags` bits `0..1` encode the same numeric values.

Values `2..3` are reserved/invalid.

## 9. Initial skin format

```cpp
enum GpuSkinFormat : uint32_t {
    EightInfluenceU16F32 = 0
};
```

ABI v1 format zero:

### Joint stream

Per vertex:

```text
uint16 joint[8]
```

Stride:

```text
16 bytes
```

### Weight stream

Per vertex:

```text
float weight[8]
```

Stride:

```text
32 bytes
```

Total baseline uncompressed skin influence data:

```text
48 bytes/vertex
```

## 10. Influence normalization

Offline compiler:

```text
sort influences deterministically by descending absolute weight,
tie-break by joint index
keep up to eight
reject materially significant discarded weight above validation tolerance
clamp negative authored weights to content error
renormalize retained non-negative weights to sum 1
```

If fewer than eight:

```text
remaining weight = 0
remaining joint index = 0
```

A rigid vertex may use:

```text
weight[0] = 1
joint[0] = root/assigned joint
```

## 11. Skin-format evolution

Later compressed formats may be added as new enum values.

They must decode to the same conceptual eight-influence input before the skinning math.

Changing format zero is forbidden after ABI v1 ships.

## 12. GPU skinning

`GpuSkinningJob.skinFormat` must equal the owning `GpuMesh.skinFormat`.

Mismatch is a validation failure.

The skinning shader switches only on accepted enum values and never infers format from stride alone.

## Raster front-face parity authority

Architecture 069 owns CPU signed-area, Vulkan raster and RT parity validation for the accepted front-face convention.

## Render-vs-output extent authority

The `renderUV` domain in this document addresses RenderExtent scene images.

Architecture 072 owns OutputExtent/swapchain coordinates and final scene scaling.

Do not use `renderUV` to address output-resolution UI/swapchain images when OutputExtent differs.
