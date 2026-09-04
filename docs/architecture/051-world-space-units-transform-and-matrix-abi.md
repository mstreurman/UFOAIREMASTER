# World Space, Units, Transform and Matrix ABI

**Status:** Exact implementation specification  
**Related ADR:** ADR-028  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`

## 1. Canonical coordinates remain unchanged

The pinned source defines:

```text
UNIT_SIZE   = 32
UNIT_HEIGHT = 64
```

Canonical routing/collision/gameplay remains in its existing coordinate system.

Presentation extraction preserves the same numerical XYZ axes.

## 2. Presentation World axes

```text
right-handed
+X = legacy +X
+Y = legacy +Y
+Z = up
```

XY is the tactical horizontal plane.

Imported authoring formats with another convention are converted offline.

## 3. Physical scale

Locked:

```text
32 presentation units = 1 meter
1 presentation unit   = 0.03125 m
UNIT_SIZE 32          = 1.0 m
UNIT_HEIGHT 64        = 2.0 m
```

Renderer/map/animation world data may remain in presentation units.

Physical-style subsystem boundaries use meters.

## 4. Jolt conversion

```text
position_m    = position_pu / 32
distance_m    = distance_pu / 32
velocity_mps  = velocity_pu_per_s / 32

position_pu        = position_m * 32
velocity_pu_per_s  = velocity_mps * 32
```

Jolt output writes presentation transforms only.

## 5. OpenAL conversion

World-spatial OpenAL coordinates use:

```text
meters = presentationUnits / 32
```

Listener, emitters, reference distance and max distance use the same meter scale.

## 6. Generic transform semantics

Use column-vector semantics:

```text
p_parent = parentFromObject * p_object
p_world  = worldFromParent * p_parent

worldFromObject =
    worldFromParent * parentFromObject
```

New APIs should encode transform direction in names.

## 7. Generic matrix ABI

Generic remaster CPU `Mat4f` and Slang `float4x4` use:

```text
column-major storage
column-vector semantics
```

The Slang compile/reflection path validates this convention.

## 8. Explicit packed affine semantics

The exact `GpuAffine3x4Rows` byte layout is owned by architecture 059.

Semantic evaluation is:

```text
x' = dot(row0, float4(x,y,z,1))
y' = dot(row1, float4(x,y,z,1))
z' = dot(row2, float4(x,y,z,1))
```

The packed record is an explicit serialization format, not a raw alias of `Mat4f`.

## 9. `VkTransformMatrixKHR`

Populate the Vulkan 3x4 transform explicitly from semantic transform rows.

Do not:

```text
memcpy a generic Mat4
reinterpret_cast matrix memory
depend on compiler matrix packing
```

Tests compare basis-point transforms across CPU, Slang, packed affine and Vulkan AS representations.

## 10. Quaternion convention

```text
components = (x,y,z,w)
Hamilton product
right-handed active rotations
unit quaternions
```

`q` and `-q` represent the same orientation.

## 11. Geometry winding

Runtime presentation geometry is normalized offline to:

```text
counter-clockwise front face when viewed from outside
```

Baseline Vulkan raster state:

```text
VK_FRONT_FACE_COUNTER_CLOCKWISE
```

RT uses the same normalized geometry.

## 12. Tangent basis

```text
N = normal
T = tangent.xyz
sign = tangent.w

B = sign * cross(N, T)
```

All are expressed in the same right-handed presentation basis.

## 13. Camera/depth

World remains right-handed/Z-up.

Projection code converts explicitly into Vulkan clip conventions.

Depth remains:

```text
reversed Z
Vulkan 0..1 depth range
```

World data is not globally axis-flipped to satisfy clip-space conventions.

## 14. Unit-explicit naming

Where ambiguity is possible use:

```text
positionPu / distancePu / radiusPu
positionM  / distanceM  / radiusM
```

Ray biases and renderer/map distances are presentation units unless explicitly stated otherwise.

## 15. Required tests

```text
legacy position -> presentation unchanged numerically
32 PU -> 1.0 m
64 PU Z -> 2.0 m
CPU Mat4 == Slang transform
packed affine == generic transform
VkTransformMatrixKHR == generic transform
CCW front-face test
tangent-sign reconstruction
Jolt transform round-trip
OpenAL relative-distance conversion
```

## Raster front-face validation authority

Architecture 069 validates CCW outside-facing geometry with `VK_FRONT_FACE_COUNTER_CLOCKWISE` under the accepted projection/viewport convention.
