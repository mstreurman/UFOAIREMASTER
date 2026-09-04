# Local-Light Shape, Orientation, Intensity and ReSTIR Sampling

**Status:** Exact implementation specification  
**Related ADR:** ADR-030  
**Related architecture:** 022, 057, 059

## 1. Scope

`GpuLight` represents local direct-light candidates.

The dominant sun uses the dedicated directional-light path and is not placed in `GpuLight[]`.

## 2. Common fields

Architecture 059 owns the exact 96-byte `GpuLight` layout.

This document owns field semantics.

`positionRange.xyz`:

```text
light center/origin in presentation units
```

`positionRange.w` is finite influence range in presentation units.

For center distance `dPu` and range `rPu`:

```text
if rPu <= 0 or dPu >= rPu:
    rangeWindow = 0
else:
    x = clamp(dPu/rPu,0,1)
    rangeWindow = square(max(0,1-x^4))
```

Shared light evaluation multiplies RGB by `rangeWindow`.

`colorIntensity.xyz` is a non-negative linear ACEScg RGB multiplier; it is not required to be normalized to unit luminance or max component 1.

`colorIntensity.w` is the type-specific intensity scalar below.

## 3. Exact light-type enum

```cpp
enum GpuLightType : uint32_t {
    Point = 0,
    Spot  = 1,
    Rect  = 2,
    Disk  = 3,
    Line  = 4
};
```

Values `5..0xffffffff` are invalid/reserved in ABI v1.

## 4. Point

```text
directionCosOuter = (0,0,0,0)

shape.x = sourceRadiusMeters
shape.y = 0
shape.z = 0
shape.w = 0
```

`colorIntensity.w` semantic:

```text
point intensity coefficient in scene-radiance * meter^2
```

Shared evaluation before visibility:

```text
radiance =
    colorIntensity.xyz *
    colorIntensity.w /
    max(distanceMeters^2, distanceEpsilon^2)
```

This is an exact project RGB-radiometric convention, not a claim of spectral photometric accuracy.

A zero source radius is an ideal delta point and uses `DeltaCenter`.

For nonzero source radius, `SphereDirection` decodes a unit direction `d` and reconstructs:

```text
samplePositionPu =
    centerPu + d * sourceRadiusMeters * 32

emitterNormal = d
areaPdf = 1 / (4 * pi * sourceRadiusMeters^2)
```

The sphere sample is uniform in area.

## 5. Spot

```text
directionCosOuter.xyz = normalized forward emission direction
directionCosOuter.w   = cos(outerConeAngle)

shape.x = sourceRadiusMeters
shape.y = cos(innerConeAngle)
shape.z = 0
shape.w = 0
```

Requirements:

```text
-1 <= outer cosine <= inner cosine <= 1
```

`colorIntensity.w` uses the same point/spot scene-radiance*meter^2 intensity coefficient as Point.

Cone attenuation multiplies the inverse-square result through shared Slang light functions.

A zero source radius uses `DeltaCenter`.

A nonzero source radius uses the same exact `SphereDirection` sphere reconstruction/PDF as Point; spot cone attenuation is evaluated from the light center/forward axis to the shading point so the sampled sphere does not redefine the authored cone.

## 6. Rectangle

```text
directionCosOuter.xyz = normalized emitting-face normal
directionCosOuter.w   = halfHeightMeters

shape.xyz = normalized local +right vector
shape.w   = halfWidthMeters
```

Requirements:

```text
right orthogonal to normal within validation tolerance
halfWidth > 0
halfHeight > 0
```

Derived:

```text
up = normalize(cross(normal, right))
```

A `RectUv` sample `(u,v)` is uniform on `[0,1)^2` and maps:

```text
du = (2u - 1) * halfWidth
dv = (2v - 1) * halfHeight

samplePosition =
    center + right * du + up * dv

areaPdf =
    1 / (4 * halfWidth * halfHeight)
```

`colorIntensity.w` semantic:

```text
emitted scene radiance scalar
```

Area-light Monte Carlo evaluation applies the shared emitted-radiance, emitter-cosine, distance and PDF terms exactly once.

## 7. Disk

```text
directionCosOuter.xyz = normalized emitting-face normal
directionCosOuter.w   = 0

shape.xyz = normalized local +right vector
shape.w   = radiusMeters
```

Derived:

```text
up = normalize(cross(normal, right))
```

`DiskUv` is uniform on `[0,1)^2`, mapped through the shared concentric-disk transform, then:

```text
samplePosition =
    center +
    right * disk.x * radius +
    up    * disk.y * radius

areaPdf =
    1 / (pi * radius^2)
```

`colorIntensity.w` semantic:

```text
emitted scene radiance scalar
```

Disk evaluation uses the same area-emitter radiance convention as Rect.

## 8. Line

```text
directionCosOuter.xyz = normalized line-axis direction
directionCosOuter.w   = halfLengthMeters

shape = (0,0,0,0)
```

ABI v1 line lights are zero-radius line emitters.

`LineT` is uniform on `[0,1)`:

```text
offset = (2t - 1) * halfLength

samplePosition =
    center + axis * offset

lengthPdf =
    1 / (2 * halfLength)
```

`colorIntensity.w` semantic:

```text
emitted line intensity coefficient per meter
```

The line estimator multiplies by the sampled line-length/PDF term in the shared evaluation module.

## 9. Meter conversion

`positionRange.xyz` is presentation units.

Shape dimensions are stored in meters deliberately because they represent physical emitter size.

Conversion at light extraction:

```text
meters = presentationUnits / 32
```

Sampling reconstructs the sample offset in meters, then converts the offset to presentation units when combining with `positionRange.xyz`.

## 10. Shared evaluation

One Slang module owns:

```text
light sample reconstruction
sample area/length PDF
distance/geometry factor
spot attenuation
emitter normal/orientation
target-function evaluation
```

Fresh ReSTIR candidates and reused-reservoir reconstruction call the same functions.

## 11. PDF consistency

The sample type stored in the reservoir must match the light type:

```text
Point -> DeltaCenter or SphereDirection if finite-radius policy uses it
Spot  -> DeltaCenter or SphereDirection if finite-radius policy uses it
Rect  -> RectUv
Disk  -> DiskUv
Line  -> LineT
```

A mismatch invalidates the reservoir.

## 12. VFX lights

Transient VFX lights use the same exact `GpuLight` semantics and identity/generation registry.

Typical VFX light types:

```text
Point
Spot
```

Area VFX lights are allowed only if authored with the complete required orientation/shape data.

## 13. Intensity calibration

The type-specific numerical semantics above are ABI/content semantics and are consumed by one shared PBR light-evaluation module.

Exposure/content calibration may tune artistic scale, but a type's numerical formula cannot vary by pass.
