# Volumetrics, VFX Lights, Ribbons/Beams and Jolt Debris

**Status:** Implementation specification baseline  
**Related ADR:** ADR-025

## 1. World-space volumetric emitters

Major smoke/fog/gas is represented as persistent world-space emitters.

Starting emitter shapes:

```text
Sphere
Box
Capsule
```

Conceptual data:

```cpp
struct VolumeEmitter {
    Transform transform;
    VolumeShape shape;

    float density;
    float extinction;
    float anisotropy;
    float lifetime;

    float scatteringAcesCg[3];
    float emissionAcesCg[3];

    uint32_t noiseProfile;
    uint32_t tacticalLevel;
    uint32_t flags;
};
```

## 2. Froxel representation

The camera/view integration structure is a froxel grid.

Baseline:

```text
160 x 90 x 64
= 921,600 froxels
```

Z distribution is depth-aware/logarithmic.

The grid is a reconstruction/integration representation.

World-space emitter state remains the actual presentation density source.

## 3. Volume injection

For each relevant emitter:

```text
world bounds
    ->
froxel overlap bounds
    ->
density/extinction/scattering/emission injection
```

Do not raster hundreds of alpha smoke sprites as the only representation of major smoke.

## 4. Froxel data

Initial logical quantities:

```text
extinction/density
scattering coefficient/color
emission
lighting/in-scattering
integrated transmittance/radiance
```

Use FP16 storage where visual range/precision permits.

Exact format packing remains implementation work.

## 5. Ambient volumetric lighting

DDGI provides low-frequency world-space ambient/diffuse lighting input.

Gather DDGI at representative froxel/world positions as appropriate.

## 6. Directional volumetric shadowing

Use a coarser 3D visibility lattice rather than tracing every froxel.

Starting lattice:

```text
40 x 23 x 32
= 29,440 samples
```

At each sample:

```text
world position
    ->
world-space directional-light RT visibility ray
```

The full starting lattice therefore contributes at most:

```text
29,440 RT traversals
```

to the frame when every lattice sample is updated. These rays count against the aggregate RT traversal ceiling owned by architecture 019; they are not an unaccounted VFX-only ray budget.

Then:

```text
temporal accumulation
    ->
3D interpolation
    ->
froxel lighting
```

This preserves world-space shadow truth.

## 7. Local volumetric lights

Local lights may inject analytic unshadowed/scaled lighting initially.

World-space local-light visibility for volumetrics is benchmark-driven.

Do not automatically multiply RT ray counts by every local light/froxel.

## 8. Volumetric temporal history

History validation considers:

```text
camera transform
froxel/world reprojection
cutaway state
volume emitter changes
major light changes
```

Temporal reconstruction is allowed because underlying density/light data remains world-space.

## 9. Volume composition

Relevant order:

```text
GBuffer
MaterialDecals
RT direct/GI
DeferredLighting
EmissiveDecals

VolumeInject
VolumeDirectionalVisibility
VolumeLight
VolumeIntegrate
VolumeComposite

glass/water
particles/ribbons
```

Exact transparent ordering with future glass/water is finalized with transparency implementation.

## 10. Transient VFX lights

Starting capacity:

```text
256 active transient lights
```

Spawned by events such as:

```text
explosion
muzzle flash
plasma discharge
alien energy pulse
electrical arc
burning debris
```

They become normal presentation light records and enter:

```text
local light candidate generation
ReSTIR DI
world-space RT visibility
reflection hit direct-light sampling where selected
DDGI dirty marking
```

## 11. VFX-light lifetime

VFX light state is explicit:

```text
position
radius
color/intensity
lifetime
curve
priority
stable light ID/generation
```

Do not infer lighting from the rendered alpha particle image.

## 12. Ribbons and beams

Separate from ordinary particles.

Conceptual primitives:

```text
Beam:
    start world point
    end world point
    width
    material
    lifetime

Ribbon:
    ordered world-space control points
    widths
    ages
    material
```

GPU expands into camera-facing strip geometry.

## 13. Beam authority

A beam/tracer receives canonical/presentation start/end/impact data.

The beam itself does not perform hit detection or damage.

Example:

```text
canonical shot resolved
    ->
PresentationEvent { origin, impact, weapon type }
    ->
beam/tracer presentation
```

## 14. Ribbon histories

Trail/ribbon points are presentation history.

Examples:

```text
rocket trails
smoke trails
plasma streaks
electrical arcs
```

Lifetime continues while hidden by cutaway unless emitter policy kills it.

## 15. Jolt rigid debris boundary

Use Jolt for:

```text
shell casings
large fragments
equipment pieces
physical chunks
rigid secondary debris
```

Starting active rigid-debris cap:

```text
256
```

Ragdoll bodies are tracked separately from this debris cap.

## 16. Debris overflow

If rigid-debris capacity is exhausted:

```text
retain highest-priority/nearest/critical debris
downgrade lower-value new debris to non-physical GPU VFX
```

No canonical state changes.

## 17. No GPU particle collision authority

GPU particles may use:

```text
gravity
drag
analytic emitter-local constraints
```

but ordinary baseline particles do not query canonical collision, Jolt or screen depth for physics.

Jolt handles the smaller set requiring meaningful collisions.

## 18. Cutaway

### Volume emitters

```text
hidden level -> not injected
lifetime continues
```

### Ribbons/beams

```text
visible only according to presentation cutaway rules
history/lifetime continues
```

### Jolt debris

Physics may continue presentation-only.

If a hidden level makes debris irrelevant, quality policy may sleep/retire low-value bodies, never canonical objects.

## 19. Debug views

Required:

```text
volume emitter bounds
froxel density
froxel lighting
directional visibility lattice
VFX light bounds/intensity/priority
beam/ribbon control points
Jolt debris pool usage
debris downgrade count
```

## VFX light identity authority

Architecture 057 owns `lightId + lightGeneration` allocation/reuse.

Architecture 059 owns the exact `GpuLight` identity fields.

Transient VFX light reuse increments generation so ReSTIR history cannot alias a new light lifetime.
