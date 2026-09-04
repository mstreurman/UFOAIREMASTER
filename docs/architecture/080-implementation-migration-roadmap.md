# Implementation and Migration Roadmap

**Status:** Executable sequencing baseline — prerequisite decisions resolved in Baseline 031  
**Primary target:** Fedora 44 / i9-9900K / Arc B580  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`
**Execution strategy:** architecture 091

## 1. Purpose

This document closes `B029-003`: the design set needs a concrete order of work that can be implemented, tested and rolled back without attempting a flag-day rewrite.

Baseline 031 resolves the project choices that were named gates in Baseline 030. Milestones below now reference accepted authorities directly.

## 2. Rules for every milestone

Every milestone must define and satisfy:

```text
source modules touched
new modules introduced
legacy path retained/removed
feature flag / selection mechanism
build/test commands
canonical regression tests
presentation regression tests
performance captures where relevant
asset/compiler steps where relevant
exit criteria
rollback path
```

A milestone does not delete its legacy path before parity/exit evidence exists.

Architecture 091 defines the common execution method for all milestones: risk-first vertical slices, G0-G7 merge gates, dependency ownership, rollback discipline, and the rule that default-switch and legacy-deletion changes are separated.

## 3. M0 — Reproducible bootstrap and preservation harness

Authorities:

```text
ADR-033 / architecture 081      SDL3 Fedora platform
ADR-034 / architecture 082      Jolt pin/integration
ADR-034/047 / architecture 029  Slang acquisition/compiler pin
```

Work:

```text
freeze source/toolchain manifest, including exact reference RPM NEVRAs/tool versions and a manifest hash
make Fedora dependency/bootstrap script reproducible
establish CMake presets/toolchain options
establish debug/release/benchmark build modes
capture canonical regression corpus
capture current build/run smoke tests
establish feature flags for old/new presentation systems
```

Exit:

```text
clean checkout -> documented dependency state -> configure -> build -> tests
canonical reference corpus reproducible
legacy game still runs
```

Rollback: none; this phase does not replace production presentation behavior.

## 4. M1 — Canonical boundary shims

Authority:

```text
architecture 075
architecture 077
architecture 078
```

Work:

```text
formalize canonical spatial service wrappers/tests
introduce typed presentation IDs where needed
introduce tactical/strategic immutable publication boundaries
introduce typed intent dispatch without changing rules
keep legacy consumers behind adapters
```

Exit:

```text
canonical behavior hashes/reference tests unchanged
new presentation consumers can read snapshots without raw canonical pointers
```

Rollback: feature flag routes presentation back to legacy consumers.

## 5. M2 — Vulkan device/platform foundation

Authorities:

```text
ADR-033 / architecture 081
ADR-045 / architecture 087/089
architecture 072 for output/swapchain extents
```

Work:

```text
window/surface/event integration
Vulkan instance/device/feature chain
queues/frame contexts
allocator/descriptor heap
descriptor-heap Slang/SPIR-V/native smoke fixtures
pipeline cache
Frame Graph
swapchain/output contract
debug labels/validation
```

Initial render target may be a diagnostic clear/triangle; no gameplay rendering removal yet.

Exit:

```text
validation-clean resize/fullscreen/swapchain lifecycle
B580 required features verified
frame-context lifetime tests pass
```

Rollback: legacy renderer remains selectable.

## 6. M3 — Offline content/runtime asset foundation

Work:

```text
asset IDs/source hashes
rmesh/rskel/ranim/rmat/rmap/rshader loaders
Slang shader build path
legacy map/model/material conversion
runtime asset registry
```

Do not require final compression optimizations to ship the first reference implementation; versioned uncompressed/reference representations are permitted where an owning ABI explicitly allows them.

Exit:

```text
representative shipped assets compile/load deterministically
source-hash mismatch is detected
shader ABI reflection checks pass
```

Rollback: legacy asset path remains available per feature.

## 7. M4 — Presentation World + basic raster scene

Work:

```text
Presentation World/event bridge
render snapshot extraction
static BSP/world geometry
models/materials/textures
CPU skeleton evaluation
GPU compute skinning
G-buffer/deferred lighting
basic camera/visibility
```

Exit:

```text
tactical scene visually navigable on Vulkan
canonical movement/events unchanged
raster/RT geometry parity diagnostics available
```

Rollback: renderer feature flag.

## 8. M5 — Tactical presentation parity

Work:

```text
complete tactical EV_* migration
animation transitions
selection/target overlays
world labels/interaction markers
basic particles/decals/lights
tactical audio command path
```

Exit:

```text
complete tactical event catalog handled or intentionally legacy-fallback
canonical tactical replay hashes unchanged
presentation regression corpus passes accepted tolerances
```

Rollback: per-event/subsystem legacy fallback until parity.

## 9. M6 — Strategic/campaign/Geoscape migration

Authority:

```text
architecture 077–078
```

Work:

```text
StrategicSnapshot publication
strategic typed view models
StrategicIntent routing
Geoscape strategic scene extraction
radar/overlay data ownership conversion
campaign audio adapter
screen-by-screen legacy UI migration
```

Exit:

```text
no production campaign direct cgi->R_* coupling
no raw renderer Geoscape buffer sharing
migrated screens have no direct canonical mutation from UI nodes
save/load rebuilds presentation correctly
```

Rollback: per-screen compatibility path.

## 10. M7 — Retained UI and input completion

Authority:

```text
architecture 081 for SDL3 normalized controller/text/IME events
architecture 043-046 for retained UI semantics
```

Work:

```text
retained UI runtime
text/glyph renderer
keyboard/mouse/controller navigation
text input/IME
accessibility/focus
remaining campaign + tactical screens
```

Exit:

```text
legacy production node/data APIs no longer required
all authoritative actions are typed intents
input/resizing/DPI regression suite passes
```

Rollback: screen-level legacy compatibility while migration remains incomplete.

## 11. M8 — OpenAL/EFX production audio

Work:

```text
AudioControl thread
voice virtualization
streaming/music
EFX environments/HRTF
acoustic scene/portals/occlusion
strategic+tactical command adapters
```

Exit:

```text
logical audio-command regression passes
no gameplay authority depends on audio state
CPU/audio budgets pass on i9-9900K
```

Rollback: legacy sound path selectable until final parity.

## 12. M9 — VFX + Jolt presentation physics

Authorities:

```text
ADR-034 / architecture 082 for Jolt
ADR-037 for ragdoll scope
ADR-039 / architecture 085 for particle reference-v1 ABI
```

Work:

```text
GPU particles
world decals
volumetrics/lights/ribbons/beams
Jolt debris/ragdoll presentation
presentation collision layers
```

Exit:

```text
presentation physics cannot affect canonical outcomes
VFX/Jolt stress replay meets CPU/GPU budgets
```

Rollback: effect-class feature flags/fallbacks.

## 13. M10 — Hardware RT lighting and reconstruction

Work:

```text
BLAS/TLAS lifecycle
RT directional shadows
RT local visibility/ReSTIR DI
RT reflections
DDGI
reconstruction/denoisers
false-color/probe diagnostics
```

Policy:

```text
RT pipeline first
Ray Query only through architecture 073 benchmark gate
```

Exit:

```text
raster/RT geometry parity tests pass
B580 frame/tail budgets pass at target quality tier
no RT feature changes canonical LOS/collision
```

Rollback: per-effect raster/non-RT quality fallbacks where specified.

## 14. M11 — Cinematic/video migration

Authorities:

```text
ADR-035
architecture 079
architecture 083
```

Exit:

```text
all shipped cinematic corpus plays with correct A/V/skip/transition behavior
no legacy immediate renderer/audio ownership remains in cinematic path
```

## 15. M12 — Performance specialization

Work:

```text
i9-9900K AVX2/FMA specialization where benchmarked
PGO/LTO evaluation
B580 subgroup/workgroup tuning
GPU-driven submission benchmarks
RT pipeline/ray-query exceptions only if proven
allocator/residency tuning
compression tuning
```

Exit:

```text
optimization gates have reproducible before/after captures
no semantic regression
```

## 16. M13 — Legacy removal and release packaging

Work:

```text
remove dead OpenGL/legacy renderer paths
remove dead old mixer paths
remove obsolete UI compatibility
remove unused legacy runtime parsers
final Fedora install/RPM/desktop integration
split debug symbols/build IDs
license/dependency inventory
```

Exit:

```text
clean source scan finds no unclassified legacy production dependency
clean build/test/install from documented bootstrap
final completeness + supersession audit passes
```

## 17. Ordering constraints

Hard ordering:

```text
M0 before all implementation work
M1 before deleting any canonical-facing legacy adapters
M2 before Vulkan renderer migration
M3 before production new renderer asset use
M4 before RT
M6 before deleting campaign direct renderer/UI coupling
M7 before deleting legacy UI
M8 before deleting legacy sound
M9 uses the accepted Jolt/particle authorities from Baseline 031
M10 requires stable raster geometry/material/AS contracts
M11 uses the accepted FFmpeg cinematic authority
M13 last
```

Parallel work is allowed where these dependencies are respected.
