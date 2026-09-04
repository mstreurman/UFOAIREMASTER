# Render Probe Crosshair: Material, Ray and Temporal Inspector

**Status:** Implementation specification baseline  
**Related ADR:** ADR-027

## 1. Purpose

Provide an exact-pixel developer probe that answers:

```text
What surface is under this pixel?
What material/texture produced it?
What RT systems apply?
Why is it shadowed/not shadowed?
What did the ray hit?
Where did reflection/indirect light come from?
Why was temporal history accepted/rejected?
```

## 2. Crosshair

Developer overlay displays:

```text
    |
----+----
    |
```

The exact center pixel is the probe sample.

Support:

```text
move with pointer
lock/unlock probe
center-screen fixed mode
```

The UI displays the captured frame ID.

## 3. Request

Conceptual:

```cpp
struct RenderProbeRequest {
    uint64_t requestId;
    uint64_t frameIndex;

    uint32_t pixelX;
    uint32_t pixelY;

    uint32_t flags;
};
```

At most a very small number of probes are active; baseline assumes one.

## 4. Asynchronous readback

Flow:

```text
CPU request
    ->
Frame Graph RenderProbeCapture pass
    ->
GPU probe record
    ->
FrameContext readback
    ->
timeline completion
    ->
CPU decode
    ->
developer UI
```

Do not stall with:

```text
vkQueueWaitIdle
```

Probe data may appear 1–2 frames after request.

## 5. Primary surface data

Capture:

```text
screen pixel
normalized UV
raw reversed-Z depth
view/linear distance
world position
geometric normal
shading normal
tangent/bitangent basis where relevant
surface UV
tactical level
RenderObjectId
PresentationEntityId mapping if available
```

## 6. RT identity

Capture where applicable:

```text
TLAS custom index
GpuRtInstanceData index
geometry index
primitive ID
barycentrics
instance mask
instance flags
BLAS semantic identity
```

## 7. Material data

Capture:

```text
material AssetId
material virtual path/name resolved on CPU
MaterialClass
material flags

base color
metalness
perceptual roughness
alpha roughness
AO
IOR
F0
emissive
alpha cutoff
```

Report both authored factors and final sampled/evaluated values where useful.

## 8. Texture inspection

For each relevant texture:

```text
AssetId
virtual path resolved on CPU
descriptor index
sampler index
UV
chosen mip/LOD
sampled encoded value
decoded/evaluated value
```

At minimum:

```text
BaseColor
Normal
ORM
Emissive
```

For raster samples, capture the actual raster LOD decision where available.

For RT material samples, report the explicit RT LOD policy/result used by the production RT material path.

## 9. Directional sun inspection

Capture:

```text
directional-light eligibility
ray mask
ray flags
ray origin
origin bias
ray direction
max distance
visibility
```

If blocked, capture:

```text
blocker RenderObjectId
TLAS custom index
geometry index
primitive ID
hit distance
blocker material
opaque/alpha-test result
```

## 10. Production-equivalent ray setup

Probe rays reuse shared Slang functions such as:

```text
BuildDirectionalShadowRay
BuildReflectionRay
BuildDdgiRay
```

The probe must use:

```text
same world position
same normals
same bias
same direction
same TLAS
same instance mask
same flags
same alpha-test semantics
```

as production.

A diagnostic ray that disagrees because its setup differs from the production constructor is unacceptable.

A newly launched diagnostic ray is not automatically the historical production sample that produced a temporally reconstructed displayed value.

The inspector therefore separates:

```text
Displayed Result Provenance
Diagnostic Re-trace
```

according to architecture 055.

## 11. Reflection inspection

Capture:

```text
eligibility
roughness policy result
sample/seed identity
ray origin
ray direction
min/max distance
hit/miss
```

On hit:

```text
hit object
geometry
primitive
barycentrics
distance
hit material
hit texture LOD
raw hit radiance
```

On miss:

```text
environment/fallback identity
sampled radiance
```

## 12. Reflection reconstruction pipeline

At probe pixel expose values through the pipeline:

```text
raw RT reflection
temporal reflection
variance
Atrous1
Atrous2
Atrous4
upsampled result
final reflection contribution
```

Exact stages follow the accepted reconstruction implementation.

## 13. Temporal validation inspector

Report:

```text
current UV
reprojected previous UV
current/previous ObjectId
normal similarity
plane/depth delta and tolerance
roughness current/previous
hit identity current/previous
history length
accept/reject
reject bitmask/reason
```

## 14. ReSTIR inspector

Expose:

```text
half/full-res coordinate
selected light ID
fresh candidate count
reservoir M
reservoir weight/target values
temporal candidate accepted/rejected
spatial candidate count
accepted spatial count
previous M
M clamp status
final visibility
blocker identity
final direct contribution
```

Exact mathematical fields mirror the final reservoir ABI.

## 15. DDGI inspector

Expose:

```text
volume ID
surrounding probe IDs
probe weights
probe classification
probe relocation
probe age/update frame
probe irradiance
probe distance/visibility data
final gathered irradiance
final indirect contribution
```

## 16. RT isolation explanation

The probe always explains the selected pixel's current RT Isolation classification.

Examples:

```text
ResolvedRT:
    Reflection + DDGI

CurrentRay:
    Reflection only
```

For pure-red/no-RT pixels, report reasons such as:

```text
Reflection:
    RoughnessTooHigh

Directional:
    NoDirectionalLight

Local:
    NoSelectedLight

DDGI:
    OutsideVolume
```

"Red" must be explainable.

## 17. Selected-ray world visualization

When probe is locked, optionally render world debug lines:

```text
white:
    camera -> primary point

yellow:
    directional shadow ray

cyan:
    reflection ray

green:
    DDGI/probe relation

red:
    traversed segment to blocker/hit
```

Render hit markers.

This geometry is debug presentation only.

## 18. Blocker inspection

Developer UI may promote a reported blocker/hit object into the selected probe subject.

Then inspect:

```text
BLAS class
partition key
tactical level
opacity class
chunk
instance mask
instance flags
material
primitive
```

## 19. Probe GPU record

Use a verbose fixed/structured diagnostic record.

Conceptual:

```cpp
struct GpuRenderProbeRecord {
    ProbePrimarySurface primary;
    ProbeMaterial material;
    ProbeDirectional sun;
    ProbeRestir restir;
    ProbeReflection reflection;
    ProbeDdgi ddgi;
    ProbeTemporal temporal;
};
```

Several kilobytes are acceptable.

Do not over-optimize a one-record debug ABI at the cost of inspectability.

## 20. CPU resource-name resolution

GPU records numeric IDs:

```text
material index
descriptor index
AssetId
RenderObjectId
```

CPU developer tooling resolves:

```text
AssetId -> virtual path/name
descriptor index -> runtime texture/resource
RenderObjectId -> presentation debug name
```

No GPU debug strings are required.

## 21. Probe capture artifact

Provide developer action:

```text
Capture Probe
```

Output extension:

```text
.ufoprobe
```

Capture includes:

```text
build/content identity
frame ID
camera
pixel
primary surface
material
texture references/sample data
RT rays
blockers/hits
ReSTIR
DDGI
temporal state
renderer settings
```

Optional diagnostic image crops:

```text
beauty
G-buffer
shadow
reflection
selected RT debug
```

around the probe may be attached in a future implementation.

## 22. Deep trace escalation

Developer action:

```text
Capture next frame with Deep instrumentation
```

associates:

```text
Render Probe
CPU trace
GPU pass trace
Frame Graph metadata
RT counters
```

for the same diagnostic frame.

## 23. Shader variants

Compile from shared Slang source:

```text
Production
Visualization
Probe
```

Production shadow/reflection payloads remain minimal.

Probe variants may capture:

```text
instance
geometry
primitive
hit distance
material
alpha decision
```

without permanently increasing production payload size.

## 24. Acceptance criterion

The first working RT renderer is not considered sufficiently observable until a developer can select a pixel and determine:

```text
surface/object identity
material/texture identity
sun visibility/blocker
reflection ray result
local-light/ReSTIR state
DDGI contribution
temporal accept/reject reason
RT Isolation classification
```

## Production provenance record

Visualization/Probe variants may retain:

```text
sampledThisFrame
sourceFrameIndex
sample/random identity
history weight/length
effect class
```

DDGI records relevant probe IDs/update frames rather than claiming the screen pixel launched a probe ray.

`.ufoprobe` stores displayed provenance and diagnostic re-trace separately.

## Probe capture/composite ordering

Scene/material/RT probe capture occurs before developer UI and crosshair composition.

The `+` overlay and inspector panel:

```text
do not write G-buffer data
do not change RT Isolation classification
do not affect the pixel/material being inspected
```

They are composited after the forensic capture point.

Architecture 060 owns this ordering.
