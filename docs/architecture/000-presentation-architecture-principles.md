# Presentation Architecture Principles

**Status:** Accepted baseline  
**Scope:** High-level architecture boundary between canonical UFO: Alien Invasion gameplay and the remaster presentation runtime.

## 1. One-way authority

The architectural boundary is intentionally one-way:

```text
Canonical UFO:AI Game / Simulation
        |
        | read-only state + events
        v
Remaster Presentation Runtime
        |
        +-- Vulkan renderer
        +-- animation
        +-- visual effects
        +-- presentation physics
        +-- UI presentation
        +-- OpenAL Soft audio
        +-- EFX environmental audio

NO PRESENTATION FEEDBACK INTO CANONICAL GAME STATE
```

The canonical game is authoritative.

The presentation runtime is observational and expressive.

## 2. Dual representation is allowed

The same logical object may have a canonical representation and a richer presentation representation.

Example:

```text
Canonical wall
  - authoritative gameplay position/state
  - canonical LOS result
  - canonical collision
  - canonical damage/destruction state

Presentation wall
  - high-resolution geometry
  - PBR material
  - RT acceleration-structure geometry
  - shadow/reflection participation
  - visual debris
  - acoustic presentation
```

The presentation representation must follow canonical state, not replace it.

## 3. No shortcut through presentation systems

Presentation systems must not become alternate implementations of canonical mechanics.

In particular:

- Vulkan RT visibility must not replace canonical LOS.
- GPU depth must not replace canonical visibility rules.
- presentation-physics collision must not replace canonical collision.
- RT hit results must not determine gameplay projectile hits.
- EFX occlusion must not determine gameplay detection.
- animation root motion must not determine canonical unit movement.

## 4. Primary presentation stack

### Graphics

- Vulkan 1.4;
- Arc B580 / Xe2 as primary GPU target;
- rasterized primary visibility;
- selective hardware RT;
- separate RT pipelines by effect;
- HDR scene rendering;
- DisplayHDR 600-class 1080p60 performance/quality qualification target;
- runtime-selectable display, resolution, refresh rate and HDR state.

### Audio

- OpenAL Soft;
- EFX 1.0;
- 3D positional audio;
- environmental reverberation and filtering;
- optional/device-dependent HRTF.

### Physics

- Jolt Physics;
- presentation-only;
- non-authoritative;
- i9-9900K-optimized where useful;
- no state feedback into canonical gameplay.

### Platform

- Fedora Linux 44 is the primary supported platform;
- KDE Plasma / Wayland is the reference session;
- Linux/Fedora-specific implementation choices are acceptable;
- Vulkan is used directly for graphics.

## 5. Renderer philosophy

The renderer is optimized for the Arc B580 rather than designed first as a lowest-common-denominator abstraction.

Portability may be added where it does not compromise the primary target.

The preferred frame-level direction is:

```text
Canonical presentation snapshot/events
        |
        v
Presentation scene update
        |
        v
GPU scene upload / AS maintenance
        |
        v
Raster primary visibility
        |
        +--> RT shadows
        +--> RT reflections
        +--> selective RT indirect-lighting presentation
        |
        v
RT reconstruction / denoising
        |
        v
Lighting / composition
        |
        v
HDR post-processing
        |
        v
HDR output transform
        |
        v
user-selected output configuration; B580/i9-9900K qualification = 1920x1080 @ ~60 FPS, DisplayHDR 600-class
```

This is the high-level renderer direction. The finalized baseline Frame Graph ownership/API is defined by ADR-016 and architecture 015–017.

## 6. RT pipeline policy

`VK_KHR_ray_tracing_pipeline` is the preferred mechanism for substantial ray-traced effects.

`VK_KHR_ray_query` is non-preferred.

Ray Query may only be introduced for a narrowly scoped use case after B580 benchmark evidence shows it is materially better than the RT-pipeline alternative and does not undermine the renderer's RT scheduling strategy.

## 7. Current architecture status

The core tactical-presentation/renderer architecture areas that were pending when this overview was first written are now covered by later accepted ADRs/specifications. Baseline 029/030 audits also identified whole-project platform, strategic/campaign, dependency and production-ABI closure work; therefore this list must not be read as a claim that every implementation-shaping decision is complete:

```text
Frame Graph / synchronization        ADR-016, architecture 015–017
allocator / descriptor architecture ADR-015, architecture 013–014, 030
Slang / shader packages             architecture 029
BLAS / TLAS policy                  ADR-021, architecture 026–028
RT algorithms/reconstruction        ADR-019/020, architecture 019–025
HDR/color                           ADR-018, architecture 018
Jolt presentation physics           ADR-007/023, architecture 033
runtime asset/material family       ADR-017/022, architecture 018/031
animation runtime                   ADR-012, architecture 007
audio                               ADR-024, architecture 035–038
VFX                                 ADR-025, architecture 039–042
UI                                  ADR-026, architecture 043–046
instrumentation/replay/regression   ADR-027, architecture 047–050
```

Baseline 030 added source-boundary closure and an executable migration roadmap in architecture 075–080. Baseline 031 resolved that decision register and added the production ABI/platform/dependency closures. Baseline 032 exposed three additional presentation-fidelity/persistence choices; Baseline 034 resolves all three in ADR-042–044 and architecture 088. Baseline 036 accepts the separately introduced descriptor-heap decision: ADR-045 and architecture 089 make `VK_EXT_descriptor_heap` the production binding model from initial renderer implementation, while architecture 087 remains its qualification contract.
