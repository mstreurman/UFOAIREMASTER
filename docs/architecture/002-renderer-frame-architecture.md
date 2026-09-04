# Renderer and Frame Architecture

**Status:** Accepted baseline architecture  
**Primary target:** Intel Arc B580 / Xe2  
**Platform:** Fedora Linux 44  
**API:** Vulkan 1.4  
**Qualification profile:** RenderExtent 1920×1080, sustained close to 60 FPS; runtime RenderExtent/OutputExtent/display/refresh/HDR are selectable; DisplayHDR 600-class quality target  
**RT policy:** RT-pipeline-first; Ray Query exceptional

## 1. Architectural goal

The renderer is a B580-first hybrid renderer.

Primary visibility is rasterized.

Hardware ray tracing is spent on high-value lighting/presentation effects rather than on primary camera rays.

The baseline principle is:

```text
Raster   = primary visibility / material identification
RT       = shadows / reflections / selected indirect lighting
Compute  = reconstruction / denoising / post-processing
```

The renderer is not designed as a generic cross-vendor abstraction first.

## 2. Core frame architecture

The baseline frame is:

```text
CPU FRAME N
|
+-- consume canonical UFO:AI events/state
+-- update immutable presentation snapshot
+-- update animation
+-- update Jolt presentation physics
+-- update Presentation World transforms
+-- prepare visible instances / scene data
+-- generate GPU work
       |
       v
GPU FRAME N
|
+-- upload / streaming copies
+-- BLAS maintenance
+-- TLAS build
+-- optional depth prepass
+-- G-buffer raster
+-- RT shadows
+-- RT reflections
+-- selective RT indirect lighting
+-- RT reconstruction / denoising
+-- deferred lighting
+-- forward transparency
+-- particles / volumetrics / presentation FX
+-- HDR post-processing
+-- UI composition
+-- BT.2020 + ST2084/PQ output encoding
+-- present
       |
       v
runtime-selected RenderExtent/OutputExtent; qualification profile = 1920×1080 @ 60 Hz, DisplayHDR 600-class
```

This is a high-level logical ordering only.

The exact resource/hazard execution graph is owned by ADR-016 and architecture 015–017; later VFX/UI/diagnostic documents add declared passes through that Frame Graph contract.

## 3. Primary visibility

Primary camera visibility is rasterized.

The renderer will not use path-traced or ray-traced primary visibility as the baseline.

Reasons:

- preserves RT budget for high-value effects;
- reduces RT shader pressure;
- gives deterministic material/depth inputs for later passes;
- aligns with the B580 target's strengths for hybrid RT workloads;
- better fits the native 1080p60 target.

## 4. Deferred opaque path

The baseline opaque renderer is deferred.

The accepted G-buffer is owned by ADR-017 and architecture 018:

```text
Depth D32_SFLOAT reversed-Z
G0    RGBA16F base color in ACEScg + metalness
G1    RG16_SNORM octahedral world shading normal
G2    RG8_UNORM perceptual roughness + AO
G3    RG16F motion (previousUV-currentUV)
G4    R32_UINT stable renderer object ID
```

The goal is to provide sufficient reconstruction data for:

- deferred lighting;
- RT ray generation;
- temporal denoising;
- reprojection;
- material classification.

## 5. Dedicated RT pipelines

The renderer should use purpose-specific RT pipelines rather than one universal RT pipeline.

Initial categories:

```text
RT Pipeline A — Shadows
RT Pipeline B — Reflections
RT Pipeline C — Indirect Lighting
```

Each pipeline should remain as small and coherent as practical.

### 5.1 Shadows

Shadow/visibility rays should favor:

- terminate-on-first-hit;
- opaque geometry;
- minimal payloads;
- skipping closest-hit where possible;
- avoiding any-hit shaders where practical.

Alpha-tested geometry should be isolated or otherwise handled carefully so it does not force any-hit behavior across the entire scene.

### 5.2 Reflections

Reflection tracing should:

- use recursion depth 1;
- trace only where material contribution is meaningful;
- use roughness/material gating;
- output compact hit/radiance data;
- rely on temporal/spatial reconstruction.

The final frame remains native 1080p even if a specific RT auxiliary buffer is rendered sparsely or at reduced resolution.

### 5.3 Indirect lighting

Indirect-lighting RT is the most scalable RT feature.

The baseline target may use sparse or low-sample RT diffuse lighting with temporal accumulation.

Recursive multi-bounce TraceRay chains are not the baseline.

Additional bounces, if ever implemented, should favor iterative multi-pass approaches.

## 6. Ray Query policy

`VK_KHR_ray_query` is available on the primary GPU but is non-preferred.

The renderer must not be designed around inline Ray Query.

A Ray Query path requires target-hardware benchmark evidence showing a clear advantage over an RT-pipeline implementation for that narrowly defined workload.

## 7. RT payload and SBT policy

The target Arc B580 reported:

- shader group handle size: 32 bytes;
- shader group handle alignment: 16 bytes;
- shader group base alignment: 16 bytes;
- max hit attribute size: 32 bytes.

The renderer should therefore keep Shader Binding Table records lean.

Preferred concept:

```text
SBT = shader/dispatch identity
GPU buffers = material and scene data
```

Material state should live in GPU buffers addressed by material/geometry/instance IDs.

Do not turn the SBT into a material database.

## 8. Recursion policy

The hardware reports a maximum recursion depth far above project needs.

The project baseline remains:

```text
normal supported RT recursion depth = 1
```

Deep RT recursion is not part of the 1080p60 design.

## 9. Acceleration-structure schedule

### Static geometry

At level load:

```text
build static BLAS
        |
        +-- optimize for trace
        +-- compact
        +-- retain for level lifetime
```

Static tactical environment geometry should not be rebuilt every frame.

### Dynamic geometry

Dynamic BLAS candidates include:

- soldiers;
- aliens;
- doors;
- moving props;
- presentation-only rigid bodies where needed.

### TLAS

ADR-021 locks one TLAS per FrameContext with a full TLAS rebuild each frame.

Baseline TLAS builds use `PREFER_FAST_TRACE`; update/refit remains a B580 benchmark candidate.

## 10. BLAS organization

ADR-021 and architecture documents 026-028 define exact baseline partitioning.

Static presentation-map geometry is partitioned by:

```text
tile asset
tactical level
opacity class
spatial chunk when needed
```

Repeated RMA placements share tile-local compacted BLAS.

Rigid objects reuse asset BLAS and move through TLAS transforms.

Only truly deforming/skinned geometry uses per-frame dynamic BLAS.

Geometry remains indexed and cache-conscious.

## 11. Reconstruction and denoising

RT outputs should be designed for temporal reconstruction.

Inputs should include, as applicable:

- radiance;
- depth;
- normal;
- roughness;
- motion vectors;
- history;
- hit distance;
- confidence/variance data.

Baseline flow:

```text
RT output
  |
  v
temporal accumulation
  |
  v
history rejection
  |
  v
variance estimation
  |
  v
spatial filtering
  |
  v
resolved RT contribution
```

The reconstruction/denoiser architecture is owned by ADR-020 and architecture 021–025.

This overview intentionally does not redefine those accepted algorithms.

## 12. B580 subgroup strategy

The primary B580 reports:

```text
default subgroup size = 32
minimum subgroup size = 16
maximum subgroup size = 32
```

RT-adjacent compute workloads should explicitly benchmark subgroup 16 vs subgroup 32.

Potential candidates:

- temporal denoising;
- spatial filtering;
- ray result compaction;
- material classification;
- light-list processing;
- RT preparation.

No subgroup size is forced globally before profiling.

## 13. Queue architecture

The initial architecture favors predictable serialized graphics/RT scheduling.

Start with:

```text
graphics/RT queue:
    raster
    RT
    denoise
    lighting
    transparency
    post
```

A dedicated transfer queue may be used for streaming/uploads where advantageous.

Async compute is not assumed to be beneficial.

Compute/RT overlap should only be introduced after B580 profiling proves a gain.

## 14. Synchronization model

Use modern Vulkan synchronization:

- `vkQueueSubmit2`;
- `VkDependencyInfo`;
- `VkMemoryBarrier2`;
- `VkBufferMemoryBarrier2`;
- `VkImageMemoryBarrier2`.

The frame graph should emit precise barriers.

Avoid broad all-commands/all-commands synchronization except where genuinely required.

## 15. Timeline semaphore model

Internal GPU progress should be tracked through timeline-semaphore-style monotonic progress.

Conceptually:

```text
upload complete
AS complete
G-buffer complete
RT complete
lighting complete
frame complete
```

WSI acquire/present synchronization remains compatible with the platform's required binary semaphore model.

## 16. Frames in flight

Initial target:

```text
2 frames in flight
```

This provides CPU/GPU overlap without unnecessarily increasing latency or transient resource duplication.

This remains subject to frame-pacing measurement.

## 17. Dynamic Rendering

Use Vulkan Dynamic Rendering rather than architecting the new renderer around legacy fixed `VkRenderPass`/`VkFramebuffer` objects.

This simplifies:

- frame-graph pass creation;
- changing pass composition;
- attachment lifetime management;
- modern synchronization.

## 18. Frame graph

Use a small explicit frame graph.

Each pass declares:

- resources read;
- resources written;
- pipeline stages;
- queue;
- resource state;
- lifetime.

The frame graph is responsible for:

- resource lifetime tracking;
- transient allocation opportunities;
- image transitions;
- synchronization;
- pass timing;
- debug visualization.

The frame graph does not own gameplay state.

## 19. GPU scene model

The renderer should move toward a GPU-oriented scene representation based on large arrays/buffers and stable IDs.

Conceptual resources:

```text
global texture table
global sampler table
material buffer
mesh buffer
instance buffer
light buffer
device-addressable geometry data
```

Example conceptual instance record:

```text
transform
mesh index
material index
flags
RenderObjectId

CPU debug/presentation registries may map `RenderObjectId` back to `PresentationEntityId`; the two are not the same ABI identity.
```

The same identifiers should be usable by:

- raster;
- RT closest-hit;
- lighting;
- denoiser;
- debug tooling.

Descriptor/bindless implementation is locked by ADR-015 and architecture 013, 029, 052 and 053.

This overview intentionally does not redefine that ABI.

## 20. GPU-driven submission

CPU visibility/draw submission remains acceptable for initial renderer bring-up.

After bring-up, architecture 073 requires a target-machine benchmark comparing:

```text
CPU classification + CPU draw-list/submission preparation

vs

GPU classification/culling + GPU indirect command/data generation
```

Required stress cases include:

- large RMA scenes;
- many repeated props;
- actor-heavy tactical scenes;
- debris-heavy combat;
- high decal/particle density.

Intel Xe2 native execute-indirect support is a reason to benchmark this path, not proof that it wins this renderer.

Mesh shaders are not required for the comparison.

Adopt GPU-driven submission only when the whole-frame B580/9900K result improves without unacceptable latency/regression.

## 21. Presentation World

The renderer-facing CPU scene is a **Presentation World**, not the canonical game state and not legacy `le_t`.

Conceptual components:

```text
Presentation Entity
|
+-- Transform
+-- Renderable
+-- Skeleton
+-- Light
+-- AudioEmitter
+-- ParticleEmitter
+-- PhysicsProxy
+-- PresentationFlags
```

Canonical entities may map to one or more presentation entities.

Presentation-only entities may exist without any canonical counterpart.

## 22. Jolt integration boundary

Jolt communicates through Presentation World.

Not:

```text
Jolt rigid body
        |
        v
Vulkan object directly
```

Instead:

```text
Jolt
 |
 v
Presentation World transform/skeleton
 |
 v
GPU scene
 |
 v
Vulkan
```

This maintains subsystem isolation.

## 23. HDR pipeline

The accepted HDR/color pipeline is owned by ADR-018 and architecture 018.

Baseline:

```text
linear ACEScg/AP1 SceneColor (RGBA16F)
        |
        v
scene post/exposure/bloom only where explicitly enabled
        |
        v
ACES 2 output transform
        |
        v
display-linear Rec.2020 / D65, runtime-resolved HDR peak (600-nit qualification example)
        |
        v
ordinary UI composite at 203-nit graphics/reference white
        |
        v
ST2084/PQ encoding
        |
        v
10-bit HDR10 swapchain on native Wayland
```

SDR uses the same scene representation with the accepted Rec.709/100-nit/sRGB fallback.

## 24. UI composition

UI is composed late in the display pipeline according to ADR-026/architecture 045.

Ordinary HDR UI uses 203-nit graphics/reference white and bypasses scene exposure, bloom and creative scene grading.

## 25. Initial performance philosophy

For the 60 Hz qualification profile, the frame-budget reference is:

```text
16.667 ms
```

The renderer should remain close to sustained 60 FPS on the B580/i9-9900K qualification machine with useful headroom where practical. Other user-selected refresh rates/resolutions have their own measured budgets and do not redefine the 1080p60 acceptance profile.

Per-pass engineering gates now exist in the owning subsystem specifications. They remain benchmark-tunable rather than measured guarantees.

## 26. Current implementation/benchmark tuning questions — not project decisions

The major renderer architecture is locked by later ADRs/specifications. The items below are implementation/measurement tuning questions, **not unresolved project architecture decisions**:

- whether a depth prepass is beneficial on representative scenes;
- benchmark tuning around the accepted static-BLAS chunk thresholds;
- whether any measured case justifies dynamic BLAS update/refit instead of the accepted full-BUILD baseline;
- whether async-compute overlap materially improves B580 frame tails without resource contention;
- exact implementation/tuning constants for bloom/exposure/transparency/glass/water;
- benchmark-driven quality-scaling thresholds.

Current authority for G-buffer/PBR/HDR/descriptor/allocator/shader/RT/AS policy is in ADR-015 through ADR-022 and architecture 012–031.

## VFX integration refinement

ADR-025 and architecture documents 039-042 add the presentation VFX pipeline:

```text
MaterialDecals
EmissiveDecals
VolumeInject / VolumeLighting / VolumeIntegrate
GPU particle spawn/simulate/compact/classify/sort/indirect
ParticleRender
Ribbon/BeamRender
```

Major VFX density/light inputs remain world-space.

GPU particle simulation is cosmetic and does not query canonical collision.

Rigid physical debris is delegated to presentation-only Jolt.

## UI integration refinement

ADR-026 and architecture documents 043-046 define the remaster UI path.

Ordinary game UI is rendered after the scene has been transformed into display-linear output:

```text
ACES scene output
    ->
display-linear Rec.2020
    ->
UiComposite at 203-nit reference white
    ->
PQ
    ->
present
```

UI bypasses scene exposure, bloom and scene creative grading.

World-space interaction overlays remain Presentation World data and are not forced into the retained 2D UI tree.

## Extent authority

Architecture 072 owns the exact separation of:

```text
RenderExtent
OutputExtent
UiLogicalExtent
UiRasterExtent
```

All scene-resolution budgets and RT launch grids in this overview refer to RenderExtent unless explicitly identified as output-resolution work.
