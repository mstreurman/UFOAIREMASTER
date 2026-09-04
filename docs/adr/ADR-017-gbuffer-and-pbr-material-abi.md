# ADR-017 — G-Buffer and PBR Material ABI

**Status:** Accepted  
**Decision type:** Renderer material/deferred shading architecture  
**Primary GPU:** Intel Arc B580 / Vulkan 1.4  
**Qualification target:** RenderExtent 1920x1080 @ near 60 FPS; runtime RenderExtent is selectable

## Context

The remaster renderer uses:

```text
raster primary visibility
RT shadows/reflections/selected GI
compute reconstruction/denoising
deferred lighting
forward transparency
HDR post
```

The G-buffer therefore needs to support:

- deferred PBR lighting;
- RT reconstruction inputs;
- temporal denoising;
- motion vectors;
- stable object identity;
- a wide-gamut HDR working pipeline;
- efficient bandwidth at the 1080p B580 qualification profile, with allocations derived from the active RenderExtent.

## Decision

The primary G-buffer is:

```text
Depth  VK_FORMAT_D32_SFLOAT
G0     VK_FORMAT_R16G16B16A16_SFLOAT
G1     VK_FORMAT_R16G16_SNORM
G2     VK_FORMAT_R8G8_UNORM
G3     VK_FORMAT_R16G16_SFLOAT
G4     VK_FORMAT_R32_UINT
```

Logical contents:

```text
Depth:
    reversed-Z depth

G0:
    RGB = linear ACEScg/AP1 base color
    A   = metallic

G1:
    octahedral-encoded world-space shading normal

G2:
    R = perceptual roughness
    G = material ambient occlusion

G3:
    motion vector in UV space

G4:
    stable 32-bit GPU object ID
```

## Reversed-Z

Baseline depth convention:

```text
near = 1.0
far = 0.0
clear = 0.0
compare = GREATER_OR_EQUAL
```

An infinite/reversed projection is preferred where practical.

## Motion convention

Store jitter-inclusive motion:

```text
velocity = previousJitteredUV - currentJitteredUV
```

Therefore reprojection is:

```text
previousUV = currentUV + velocity
```

Current/previous clip transforms already contain their respective jitter; temporal passes do not add jitter delta again.

Architecture 057 is the exact temporal convention authority.

Motion includes:

- camera motion;
- rigid entity motion;
- skeletal deformation.

## Object identity

The G-buffer does not store the full 64-bit `PresentationEntityId`.

Use the renderer-owned stable 32-bit `RenderObjectId` defined by architecture 052/058.

```text
0xffffffff = background/no-object
```

The GPU ID is monotonic and not generation-packed/reused within a Presentation World lifetime.

Static raster/RT identity allocation is defined by architecture 058.

## Material model

Baseline material shading is metallic/roughness PBR.

Specular model:

```text
GGX / Trowbridge-Reitz NDF
Smith height-correlated visibility
Schlick Fresnel
```

Diffuse baseline:

```text
Lambert
```

Dielectric F0 derives from IOR:

```text
F0 = ((ior - 1) / (ior + 1))^2 * specularFactor
```

Default:

```text
ior = 1.5
specularFactor = 1.0
```

Metallic surfaces use base color as their colored F0 and suppress diffuse according to metallic factor.

## Roughness

G-buffer roughness is perceptual roughness.

Baseline shader clamp:

```text
perceptualRoughness >= 0.045
```

BRDF alpha:

```text
alpha = perceptualRoughness^2
```

## AO

Material AO affects appropriate indirect lighting only.

It must not directly attenuate canonical direct-light energy.

## Transparency

Deferred G-buffer accepts:

```text
Opaque
AlphaMask
```

True alpha blend, glass, water and similar materials render in forward HDR passes.

## Emissive

Emissive is not stored in a dedicated full-screen G-buffer attachment.

Emissive materials are resolved into the HDR scene color after deferred lighting and before bloom/post.

## Runtime texture conventions

Baseline runtime textures:

```text
base color:
    BC7_SRGB
    RGB = base color
    A = alpha coverage

normal:
    BC5_UNORM
    tangent-space XY
    reconstruct Z

ORM:
    BC7_UNORM
    R = ambient occlusion
    G = roughness
    B = metallic

emissive:
    BC7_SRGB
    RGB = emissive color
```

## GpuMaterial v1

The baseline ABI is 96 bytes:

```cpp
struct GpuMaterial {
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
```

Invalid texture index:

```text
0xffffffff
```

## Material classes

Initial enum:

```text
StandardPbr
Unlit
Glass
Water
Decal
```

## Material flags

Initial flag families:

```text
AlphaMask
AlphaBlend
DoubleSided

CastsShadow
RtVisible
ReflectionEligible
GiEligible

Emissive
ReceivesDecals
```

Texture presence is determined from texture IDs rather than duplicated presence flags.

## Raster/RT material consistency

Raster and ray tracing share one Slang material/BRDF implementation module.

Do not maintain separate PBR equations for raster and RT.

## Format validation

The reference `vulkaninfo` capture does not contain a complete per-format feature table for every selected G-buffer format.

At startup the renderer must validate required attachment/sample/storage capabilities with `vkGetPhysicalDeviceFormatProperties2`.

For the B580 target, missing required support is a renderer startup error rather than an undocumented alternate G-buffer format.

## Consequences

This design favors:

- material precision;
- stable temporal data;
- wide-gamut HDR;
- direct RT reconstruction inputs;
- straightforward debugging;

over minimizing every byte of G-buffer bandwidth.
