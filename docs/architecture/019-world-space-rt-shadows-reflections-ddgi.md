# World-Space RT Shadows, Reflections and DDGI

**Status:** Architecture baseline / benchmark starting point  
**Related ADR:** ADR-019  
**Primary target:** Intel Arc B580 / BMG G21  
**Qualification RenderExtent:** 1920x1080 @ near 60 FPS; runtime RenderExtent selectable

## 1. Fundamental split

```text
Raster:
    primary camera visibility

RT:
    world-space secondary visibility

DDGI:
    world-space diffuse-light cache

Screen-space:
    reconstruction/denoising only
```

The G-buffer selects visible launch surfaces but does not limit what rays can hit.

## 2. Specialized RT pipelines

Maintain separate RT pipelines:

```text
RTDirectionalShadow
RTLocalVisibility
RTReflection
RTDDGI
```

No general-purpose RT uber-pipeline.

Each pipeline has:

```text
own VkPipeline
own SBT
own payload contract
own ray flags
own benchmark timings
```

## 3. Directional-light shadows

### Launch domain

Full active RenderExtent visible-surface grid. The qualification case is 1920x1080.

Baseline sampling:

```text
checkerboard 0.5 rays/pixel/frame
```

Ray count:

```text
qualification example:
1920 * 1080 * 0.5
= 1,036,800 rays/frame

runtime ray count derives from active RenderExtent
```

### Ray

Origin:

```text
reconstructed world-space surface position
+ normal-scaled bias
```

Direction:

```text
sample dominant directional-light angular disk
```

Baseline ray flags:

```text
TERMINATE_ON_FIRST_HIT
SKIP_CLOSEST_HIT
OPAQUE where geometry class permits
```

Payload is minimal.

### Output

Store at least:

```text
visibility
blocker/hit distance
confidence/sample state
```

Blocker distance feeds soft-shadow reconstruction.

### Alpha-tested geometry

Opaque geometry avoids any-hit.

Alpha-tested RT geometry is kept in a separate geometry/BLAS classification where practical.

Allowed any-hit program is minimal:

```text
fetch alpha
compare alphaCutoff
ignore or accept hit
```

No general material shading in shadow any-hit.

## 4. Local-light direct lighting

### Baseline selection method

Use ReSTIR DI for local-light sample selection.

This is a sampling/reuse algorithm over world-space lights.

The final visibility result remains a real world-space RT ray.

### Resolution

Baseline local-direct grid:

```text
HalfRenderExtent = ceil(RenderExtent / 2)
qualification example = 960x540
```

### Reservoir candidates

Starting configuration:

```text
8 fresh local-light candidates
1 temporally reprojected reservoir
4 spatial-neighbor reservoirs
```

These values are benchmark starting points, not permanent content constants.

### Final visibility

One selected light sample launches one world-space shadow/visibility ray.

Maximum:

```text
qualification example:
960 * 540
= 518,400 visibility rays/frame
```

### Output

Store direct-light estimate suitable for DeferredLighting:

```text
selected light radiance contribution
visibility
sample metadata/confidence
```

The dominant sun/directional light remains outside this local-light ReSTIR path.

## 5. Reflections

### Launch resolution

Baseline reflection grid:

```text
HalfRenderExtent = ceil(RenderExtent / 2)
qualification example = 960x540
```

Maximum primary reflection rays:

```text
518,400/frame
```

### Eligibility

Reflection eligibility is material/view dependent.

Baseline starting thresholds:

```text
roughness <= 0.50:
    full RT eligibility

0.50 < roughness < 0.65:
    fade/downweight dedicated reflection RT

roughness >= 0.65:
    no dedicated reflection ray
```

These thresholds may move after material/scene benchmarks.

### Direction sampling

Near mirror:

```text
roughness < approximately 0.05
-> deterministic mirror reflection
```

Otherwise:

```text
GGX VNDF world-space sample
```

### Hit contract

Closest-hit remains intentionally small.

Conceptual payload:

```cpp
struct ReflectionHit {
    uint32_t instanceId;
    uint32_t primitiveId;
    uint32_t packedBarycentrics;
    float hitT;
};
```

Miss:

```text
instanceId = 0xffffffff
```

The hit shader does not execute the full PBR material model.

### Hit reconstruction

After traversal returns:

```text
instance ID
primitive ID
barycentrics
hit distance
    |
    v
BDA mesh/material data
    |
    v
world-space hit reconstruction
```

### Reflection hit shading

Baseline one-bounce outgoing radiance includes:

```text
emissive
environment/sky
one selected direct-light contribution
DDGI diffuse contribution
```

Do not trace recursive reflection rays.

### Secondary direct visibility

Reflection hits may launch one additional first-hit local/direct visibility ray.

Cap average secondary reflection visibility to:

```text
0.5 rays per primary reflection pixel
```

Maximum:

```text
primary reflection rays      518,400
secondary visibility max     259,200
------------------------------------
reflection traversal ceiling 777,600/frame
```

## 6. Reflection misses

Misses resolve through:

```text
environment map / sky radiance / future world-radiance representation
```

No SSR fallback.

## 7. Diffuse GI

### Baseline

Use world-space DDGI.

The probe solution is independent of the current camera framebuffer.

### Probe placement

Initial tactical-map-aware spacing:

```text
XY:
    approximately one probe every 2 canonical tactical cells

Z:
    approximately two probe layers per tactical level
```

Exact placement is adjusted by:

```text
walkable/occupied geometry
probe relocation
probe classification
map bounds
cutaway/tactical level state
```

### Probe data

Initial logical data per probe:

```text
irradiance octahedral field
visibility/distance moments octahedral field
probe position/state
history age/confidence
```

Starting texture resolutions:

```text
irradiance:
    8x8

distance/visibility:
    16x16
```

FP16 is the baseline storage family unless measured quality/memory suggests another representation.

### Probe update budget

Starting budget:

```text
512 probes/frame
128 rays/probe
```

Primary GI rays:

```text
512 * 128
= 65,536 rays/frame
```

Optional direct-light visibility at GI hits:

```text
<= 65,536 rays/frame
```

Maximum DDGI traversal ceiling:

```text
131,072 rays/frame
```

### Probe ray shading

A DDGI hit may accumulate:

```text
emissive
selected direct light
previous-frame DDGI irradiance
```

Previous probe irradiance provides multi-bounce feedback without recursive diffuse path tracing.

### Probe scheduling priority

Starting priority order:

```text
1. newly activated probes
2. lighting-dirty probes
3. probes near currently visible/active tactical region
4. round-robin remaining probes
```

Camera visibility may influence update priority, but never defines what geometry a probe ray can see.

## 8. Tactical-level cutaway

Presentation cutaway state affects presentation RT participation.

If an upper tactical level is visually hidden:

```text
its presentation instances are excluded from the appropriate RT visibility masks/TLAS instance state
```

so hidden floors do not continue casting presentation shadows/reflections/GI.

This remains separate from canonical LOS/pathfinding.

## 9. Aggregate baseline RT traversal ceiling

Architecture 041 adds the baseline volumetric directional-visibility lattice to the same global RT accounting.

Starting maximum:

```text
Directional shadow                       1,036,800
Local ReSTIR visibility                    518,400
Reflections                                777,600
DDGI                                       131,072
Volumetric directional visibility           29,440
---------------------------------------------------
Aggregate total                          2,493,312
```

At 60 FPS:

```text
approximately 149.6 million maximum traversals/second
```

This is the aggregate scheduler/quality ceiling for the currently accepted baseline effects when the full volumetric visibility lattice is updated in the frame.

It is not a prediction of B580 frame time.

Different ray classes have different traversal, hit-shader, memory and coherence costs.

Any future local-light volumetric RT visibility must consume an explicitly budgeted portion of this global RT scheduling policy or require a later budget revision; it is not implicitly free additional traversal work.

## 10. GPU-time starting gates

Benchmark targets:

```text
Directional + local direct RT/reconstruction:
    target <= 2.0 ms

Reflections + reconstruction:
    target <= 2.1 ms

DDGI update + gather:
    target <= 0.7 ms

Combined core lighting RT/reconstruction:
    target around 4.8 ms
    provisional hard ceiling around 5.5 ms
```

These core-lighting gates cover directional/local direct RT, reflections and DDGI. Volumetric/VFX GPU time is budgeted separately by architecture 042 even though volumetric RT rays count toward the aggregate traversal ceiling above.

These are engineering targets, not measured B580 results.

Actual pass timers control scaling.

## 11. Ray origin bias

All ray classes require a common robust origin-bias helper.

Inputs may include:

```text
world-space position
geometric normal
shading normal
ray direction
world scale
surface class
```

Avoid per-effect ad-hoc epsilons.

Exact bias formula is benchmark/validation work.

## 12. Geometry classes

Presentation RT geometry should distinguish at least:

```text
Opaque
AlphaTest
Transparent/Excluded
```

Transparent/glass behavior in RT remains separately defined.

Normal opaque structural geometry should not pay alpha-test any-hit cost.

## 13. No RayQuery baseline

All above world-space rays use RT pipelines by default.

RayQuery remains exceptional/non-preferred and requires measured B580 evidence before replacing an RT pipeline path.

## Baseline 031 edge-material closure

ADR-036 and architecture 084 are normative for the shared robust ray-origin helper, raster/RT alpha-test parity, weighted-blended OIT, specialized glass/water paths and the v1 prohibition on recursive transmissive RT. Existing RT-pipeline-first policy is unchanged.
