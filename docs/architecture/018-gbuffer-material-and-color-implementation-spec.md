# G-Buffer, Material ABI and Color Pipeline Implementation Specification

**Status:** Implementation specification baseline  
**Related ADRs:** ADR-017, ADR-018  
**Primary target:** Intel Arc B580 / Vulkan 1.4

## 1. Renderer color domains

The renderer explicitly distinguishes:

```text
Texture/source color
Scene-linear working color
Display-linear output color
Display-encoded output
```

Never reuse the same `float3` interpretation across these domains without an explicit conversion.

## 2. Source color domain

Color textures:

```text
sRGB primaries / D65
sRGB transfer function
```

GPU sampling from `_SRGB` texture formats yields linear Rec.709/sRGB values.

Data textures:

```text
normal
ORM
masks
height
object data
```

use linear UNORM/SNORM/float formats and do not undergo color-space conversion.

## 3. Working domain

All physically based shading uses:

```text
linear ACEScg/AP1
```

This includes:

```text
base color
light color
radiance
reflection radiance
GI radiance
emissive
fog/volumetric radiance
HDR scene color
bloom source
```

## 4. G-buffer exact layout

### Depth

```text
VK_FORMAT_D32_SFLOAT
```

Usage:

```text
DEPTH_STENCIL_ATTACHMENT
SAMPLED
TRANSFER_SRC where debugging/readback requires
```

Convention:

```text
reverse Z
clear 0
GREATER_OR_EQUAL
```

### G0 — base color + metallic

```text
VK_FORMAT_R16G16B16A16_SFLOAT
```

Layout:

```text
R baseColor ACEScg
G baseColor ACEScg
B baseColor ACEScg
A metallic
```

### G1 — shading normal

```text
VK_FORMAT_R16G16_SNORM
```

Layout:

```text
RG = octahedral world-space normal
```

The stored normal is the final shading normal after normal-map application.

### G2 — roughness + AO

```text
VK_FORMAT_R8G8_UNORM
```

Layout:

```text
R perceptual roughness
G ambient/material occlusion
```

### G3 — velocity

```text
VK_FORMAT_R16G16_SFLOAT
```

Layout:

```text
RG = previousUV - currentUV
```

### G4 — object ID

```text
VK_FORMAT_R32_UINT
```

Layout:

```text
32-bit renderer object identity
```

Background:

```text
0xffffffff
```

## 5. Raw pixel cost

Nominal payload:

```text
Depth   4 bytes
G0      8 bytes
G1      4 bytes
G2      2 bytes
G3      4 bytes
G4      4 bytes
----------------
Total  26 bytes/pixel
```

At the 1920x1080 qualification RenderExtent:

```text
~51.4 MiB raw pixel payload
```

This figure excludes tiling/compression, alignment, transient duplication and other render targets.

## 6. Normal encode/decode

Use standard octahedral encoding.

Input:

```text
normalized world-space float3
```

Stored:

```text
R16G16_SNORM
```

Decode returns normalized world-space shading normal.

All deferred/RT reconstruction code uses the same Slang helper.

## 7. Position reconstruction

Do not store world position in the G-buffer.

Reconstruct from:

```text
depth
pixel/UV
inverse view-projection
```

or an equivalent stable camera reconstruction path.

## 8. Material texture sampling

### Base color

```text
sample BC7_SRGB
hardware decode to linear Rec.709
multiply baseColorFactor
convert Rec.709 linear -> ACEScg
```

### Normal

```text
sample BC5_UNORM
remap XY to [-1, 1]
reconstruct Z
apply normalScale
transform tangent -> world
normalize
oct encode to G1
```

### ORM

```text
R = AO
G = roughness
B = metallic
```

Apply:

```text
roughness *= roughnessFactor
metallic *= metallicFactor
AO = lerp(1, sampledAO, occlusionStrength)
```

Then clamp to expected material ranges.

### Emissive

```text
sample BC7_SRGB
hardware decode
multiply emissiveFactor
multiply emissiveStrength
convert to ACEScg
```

Do not write to G-buffer.

## 9. Material ABI v1

```cpp
struct alignas(16) GpuMaterial {
    uint32_t baseColorTexture;
    uint32_t normalTexture;
    uint32_t ormTexture;
    uint32_t emissiveTexture;

    uint32_t samplerIndex;
    uint32_t flags;
    uint32_t materialClass;
    uint32_t reserved0;

    float baseColorFactor[4];

    float emissiveFactorAndStrength[4];

    float roughnessFactor;
    float metallicFactor;
    float normalScale;
    float occlusionStrength;

    float alphaCutoff;
    float ior;
    float specularFactor;
    float reserved1;
};

static_assert(sizeof(GpuMaterial) == 96);
static_assert(alignof(GpuMaterial) == 16);
```

Slang reflection must verify field offsets and total size.

## 10. Material class enum

Exact material ABI-v1 values:

```cpp
enum class MaterialClass : uint32_t {
    StandardPbr = 0,
    Unlit       = 1,
    Glass       = 2,
    Water       = 3,
    Decal       = 4
};
```

Do not reorder accepted numeric values once runtime assets ship without bumping the material ABI version.

## 11. Material flags

Exact material ABI-v1 bit assignment:

```cpp
enum MaterialFlags : uint32_t {
    Material_AlphaMask          = 1u << 0,
    Material_AlphaBlend         = 1u << 1,
    Material_DoubleSided        = 1u << 2,

    Material_CastsShadow        = 1u << 3,
    Material_RtVisible          = 1u << 4,
    Material_ReflectionEligible = 1u << 5,
    Material_GiEligible         = 1u << 6,

    Material_Emissive           = 1u << 7,
    Material_ReceivesDecals     = 1u << 8
};
```

Bits 9..31 are reserved zero in material ABI v1.

## 12. BRDF module

One shared Slang module implements:

```text
Fresnel
GGX distribution
Smith correlated visibility
dielectric F0
metallic interpolation
Lambert diffuse
energy-conserving combination
```

Used by:

```text
deferred raster lighting
forward transparency where appropriate
RT reflection shading
RT GI shading
debug material preview
```

## 13. Deferred lighting output

Primary scene color:

```text
VK_FORMAT_R16G16B16A16_SFLOAT
```

Meaning:

```text
RGB = linear ACEScg scene radiance
A = reserved/renderer-defined
```

Do not treat alpha as canonical material opacity in the deferred scene target.

## 14. Emissive resolve

After deferred lighting:

```text
material/object selection
    ->
emissive texture/factor lookup
    ->
ACEScg radiance
    ->
add to SceneColor
```

Implementation may use material/object classification to avoid shading all pixels.

Exact compaction strategy remains a performance decision.

## 15. Forward HDR

True transparency, glass, water, particles and selected VFX write into the same linear ACEScg HDR scene.

Their exact material models remain separately specifiable.

## 16. Exposure

Exposure operates on scene-linear luminance.

Architecture requirements:

```text
deterministic manual exposure mode
automatic exposure mode
debug histogram/average telemetry
stable exposure value used by all post stages for one frame
```

Exact meter weighting, percentile range and adaptation speeds remain open.

## 17. Bloom

Bloom operates in the HDR scene pipeline.

It must preserve hue and wide-gamut values.

Exact threshold, knee, mip chain and intensity remain artistic/benchmark choices.

## 18. Creative grade

Creative color grading occurs before the ACES 2 output transform.

The baseline supports:

```text
matrix/parameter grading
optional 3D LUT later
```

Do not bake the display transfer function into creative LUTs.

## 19. ACES conversion

Working:

```text
ACEScg AP1
```

Convert to:

```text
ACES2065-1 AP0
```

before the accepted ACES 2 rendering-transform implementation where required by the selected implementation interface.

The conversion matrices/constants are centralized in one shader/color module.

## 20. HDR output transform

Output target descriptor:

```cpp
struct HdrOutputTarget {
    float peakNits;
    float referenceWhiteNits = 203.0f;

    ColorPrimaries primaries = ColorPrimaries::Rec2020;
    WhitePoint white = WhitePoint::D65;
};
```

ACES 2 output transform produces display-linear Rec.2020 values corresponding to the target luminance range.

`peakNits` is initialized from the resolved runtime output descriptor/policy owned by architectures 072/090; production code must not initialize every HDR output to the 600-nit qualification value. `referenceWhiteNits = 203` remains the accepted HDR graphics/reference-white policy used consistently by ADR-018/026 and architectures 045/072.

## 21. HDR UI composition

UI source:

```text
sRGB artwork
```

Process:

```text
sRGB decode
linear Rec.709
Rec.709 -> Rec.2020
scale white to 203 nits
alpha composite into display-linear Rec.2020 output
```

UI bypasses:

```text
scene exposure
bloom
scene creative grading unless intentionally authored otherwise
```

## 22. PQ encode

After scene + UI composition:

```text
display-linear absolute luminance
0..activeOutputPeakNits
    ->
ST.2084/PQ
    ->
normalized channel code
    ->
10-bit swapchain
```

Clamp only at the final display-target boundary as required by the output transform.

## 23. HDR swapchain contract

Preferred:

```text
VK_FORMAT_A2B10G10R10_UNORM_PACK32
VK_COLOR_SPACE_HDR10_ST2084_EXT
```

Verify surface support at runtime.

HDR mode is unavailable if the active native surface does not expose the required pair.

## 24. HDR metadata

Conceptual initial values:

```text
displayPrimaryRed   = Rec.2020 red
displayPrimaryGreen = Rec.2020 green
displayPrimaryBlue  = Rec.2020 blue
whitePoint          = D65

maxLuminance             = 600
minLuminance             = 0
maxContentLightLevel     = 600
maxFrameAverageLightLevel = 0
```

Zero-valued unknown fields are not claimed to be measured display properties.

## 25. SDR output

SDR pipeline starts from the same scene-linear ACEScg source.

Output target:

```text
Rec.709 / D65
100 nits
```

Then:

```text
sRGB encoding
VK_FORMAT_B8G8R8A8_SRGB or selected supported SRGB format
VK_COLOR_SPACE_SRGB_NONLINEAR_KHR
```

Exact preferred channel ordering is chosen from native surface support.

## 26. Format startup validation

At device initialization, query selected formats with:

```text
vkGetPhysicalDeviceFormatProperties2
vkGetPhysicalDeviceImageFormatProperties2 where needed
```

Validate at minimum:

```text
D32_SFLOAT:
    depth attachment
    sampled image

RGBA16_SFLOAT:
    color attachment
    sampled image
    storage image where required

RG16_SNORM:
    color attachment
    sampled image

RG8_UNORM:
    color attachment
    sampled image

RG16_SFLOAT:
    color attachment
    sampled image

R32_UINT:
    color attachment
    sampled image
```

If the B580 renderer contract is not met, log exact missing capability and fail renderer initialization.

## 27. Debug views

Required debug views:

```text
base color
metallic
normal
roughness
AO
motion vectors
object IDs
depth
HDR scene luminance
exposure
pre-output ACEScg
display-linear Rec.2020
PQ output
```

This is required for reliable color/material debugging.

## 28. Implementation / quality tuning

Resolved by ADR-036 / architecture 084:

```text
glass shading baseline
water shading baseline
transparency OIT strategy
shared raster/RT alpha-test behavior
ray-origin offset contract
```

Still intentionally implementation/content/benchmark-tunable rather than cross-subsystem architecture blockers:

```text
auto-exposure meter implementation within the requirements of section 16
adaptation speeds
bloom kernel/constants within the HDR requirements of section 17
optional creative 3D-LUT authoring format
exact emissive pixel compaction
pre-exposure unless later profiling justifies it
```

World-space decal implementation is resolved by ADR-025 and architecture 040.

## Transform/tangent authority

Architecture 051 owns world axes/handedness, matrix semantics, CCW front faces and tangent-sign reconstruction.

G-buffer normal/tangent evaluation consumes that same convention.

## Motion-vector jitter authority

Architecture 057 owns G3 temporal semantics.

G3 is jitter-inclusive:

```text
previousJitteredUV - currentJitteredUV
```

and temporal reprojection adds no separate jitter delta.

## Texture-coordinate orientation authority

Architecture 060 owns runtime UV orientation and tangent-space normal-map Y convention.

Raster and RT hit material reconstruction must use the same normalized orientation.

## Material numeric ABI authority

Architecture 070 confirms these numeric MaterialClass and MaterialFlags values are exact ABI-v1 values.
