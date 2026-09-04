# Transparency, Glass, Water, Alpha-Test and Ray-Offset Contract

**Status:** Implementation specification baseline  
**Authority:** ADR-036

## 1. Pass classification

Every material resolves to exactly one baseline visibility class:

```text
Opaque
AlphaTest
TransparentOIT
GlassForward
WaterForward
```

Classification is asset/material data and is shared by raster, RT geometry classification and debug views.

## 2. Alpha test

`AlphaTest` uses the same:

```text
base-color alpha texture source
UV transform/sampler semantics
alpha cutoff scalar
```

in raster and RT. RT may use any-hit only where alpha testing actually requires it. Opaque geometry must not pay any-hit cost.

## 3. Weighted blended OIT

Ordinary translucent surfaces render after opaque/deferred lighting into accumulation/revealage targets, then composite over lit scene color. They do not write the opaque G-buffer and are excluded from baseline RT transmission.

OIT is presentation-only; sorting/order differences may not change canonical state.

## 4. Glass

Glass uses a forward path with:

```text
material base tint/opacity
roughness/Fresnel
scene-color + scene-depth refraction approximation
eligible RT reflection result when enabled
fallback environment/reflection approximation when RT tier disables it
```

No recursive transmissive RT and no glass-through-glass recursive ray tree in v1.

## 5. Water

Water uses a dedicated forward material with authored normal/roughness, scene-depth/color interaction, reflection/refraction approximation and optional eligible RT reflection input. Water presentation never replaces canonical BSP/content collision.

## 6. Shared robust RT ray origin

All world-space RT ray classes call a single helper conceptually:

```text
OffsetRayOriginV1(position, geometricNormal, outgoingDirection, worldScale)
```

Requirements:

```text
offset to the side of the surface selected by outgoingDirection dot geometricNormal
scale epsilon from representable position magnitude and project world-unit scale
never use shading normal for self-intersection side selection
apply consistently to shadow, reflection, DDGI and future approved ray classes
validate thin geometry, coplanar surfaces, large coordinates and alpha-tested surfaces
```

The implementation may use a proven floating-point bit-offset technique plus a small near-origin fallback, but one helper owns the behavior and regression tests.

## 7. Validation

Required scenes include fences/foliage, thin glass, overlapping translucent sprites, shallow/deep water, coplanar decals nearby, large-coordinate geometry and grazing-angle RT rays. Raster/RT alpha classification must agree in debug output.
