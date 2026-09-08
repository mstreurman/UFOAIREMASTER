# Implementation and Migration Roadmap

**Status:** Accepted executable sequencing baseline — revised after M0 qualification for progressive legacy retirement  
**Primary target:** Fedora 44 / i9-9900K / Arc B580  
**Canonical source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Qualified remaster planning head:** `b0eb12631c71e90b7c3d1f6d19e618e7656c80be`  
**Execution strategy:** architecture 091  
**Language/toolchain authority:** architecture 092

## 1. Purpose

This document defines the implementation order for the UFO: Alien Invasion remaster.

The project remains an incremental migration rather than a flag-day rewrite, but legacy presentation implementations are no longer retained until final release merely for historical compatibility. They remain only as temporary migration and rollback paths while their replacement is being proven.

The production goal is:

```text
preserve canonical game behavior
        |
        +--> build modern presentation/runtime seams
        |
        +--> migrate one production consumer family
        |
        +--> default the proven new path
        |
        +--> retain a short real rollback window
        |
        +--> delete the obsolete legacy implementation
        |
        +--> continue forward without carrying dead backends
```

The original upstream UFO:AI project remains the reference for players who want the classic OpenGL implementation. The remaster does not preserve OpenGL as a permanent user-facing renderer.

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

Additional rules:

```text
canonical gameplay remains authoritative
new default and legacy deletion remain separate changes
legacy fallbacks are temporary migration tools unless a later architecture explicitly makes one permanent
legacy code is removed as soon as its owning replacement and decommission gates pass
M13 is not a holding area for obsolete renderer/audio implementations
accepted legacy source-content import does not imply preservation of the old runtime/mod ABI
retained canonical/legacy targets stay C++11 initially; new remaster runtime targets use strict C++26
shared canonical/remaster bridge headers remain C++11-compatible until the lower side is deliberately migrated
language standards are assigned per target; no global C++0x flag is the remaster language policy
```

Architecture 091 defines the common execution method: risk-first vertical slices, G0-G7 gates, dependency ownership, rollback discipline, progressive legacy retirement and clean-bootstrap evidence.

## 3. M0 — Reproducible bootstrap and preservation harness — COMPLETE

Authorities:

```text
ADR-033 / architecture 081      SDL3 Fedora platform
ADR-034 / architecture 082      Jolt pin/integration
ADR-034/047 / architecture 029  Slang acquisition/compiler pin
```

Completed work:

```text
source/toolchain manifest and reproducible Fedora bootstrap
CMake presets/toolchain options and build modes
canonical regression/replay/reference harness
legacy clean-build + launch smoke
feature-selection scaffolding
descriptor-heap native and Slang qualification
acceleration-structure heap qualification
Jolt stress qualification
clean-checkout reproducibility proof
```

Exit is sealed at the qualified remaster planning head named above.

Rollback: none; M0 did not replace production game behavior.

## 4. M1 — Canonical boundary shims

Authorities:

```text
architecture 075
architecture 077
architecture 078
architecture 092
```

Work:

```text
formalize canonical spatial service wrappers/tests
introduce typed presentation IDs where needed
introduce tactical/strategic immutable publication boundaries
establish and qualify C++11 legacy/bridge + strict C++26 remaster target ownership
introduce typed intent dispatch without changing rules — qualified mechanism + first strategic/tactical seed catalogs
extract callback-owned strategic validation/mutation into campaign-owned Try... helpers — Aircraft + Geoscape first slice covers start/stop/destination/pursuit/homebase
extract Base + Installation lifecycle owners — qualified build/rename base and build/rename/destroy installation slice
extract base-facility build/destroy owners — normalize current base-scoped facility index and post-confirmation destruction semantics; move base_init UI refresh out of low-level canonical build/destroy; keep DestroyAntimatterFacility fail-closed as an internal breach-event mismatch
map Research + Production immutable publication identities — publish TechnologyId and current (BaseId, queueIndex) queue location/state; keep production mutations fail-closed until a stable ProductionId or explicit queue revision/generation prevents stale-index mutation
complete M1 canonical identity audit — reserve FacilityId/TransferId/DefenceSlotId, classify current runtime/direct/sidecar/structural/definition/context identities, expand the C++11 identity contract to every declared domain, and lock stale-index migration debt before further owner extraction
extract Research scientist-assignment owners — qualify exact +/-1 typed scientist changes, canonical max assignment and stop; keep legacy sign-only command normalization/UI refresh and move no-lab popup out of canonical research core
establish stable ProductionId — add runtime-only canonical production identity that follows logical jobs across queue move/compaction, regenerate identity on load without changing save format, publish ProductionId alongside queueIndex order metadata, and migrate production submit APIs away from queue-index identity while keeping mutation fail-closed
complete source-derived presentation-action scope + five-way authority classification, including direct input hooks/protocol callsites, before defining the remaining authoritative intent vocabulary
keep existing consumers behind temporary adapters
define explicit presentation-facing ownership rather than expose raw canonical pointers
```

Compatibility policy for M1:

```text
do not design the new boundaries around legacy GUI/mod/renderer ABI compatibility
do not preserve old OpenGL-style R_* ownership as a future extension interface
do not make legacy Lua/UI callback behavior a permanent public contract
```

Exit:

```text
canonical behavior hashes/reference tests unchanged
new presentation consumers can read immutable snapshots/events without raw canonical pointers
new typed intents can reach canonical strategic owners and tactical server authority without changing rules — qualified by strategic + tactical seed catalogs
presentation-originated action surface is mechanically inventoried and classified before the remaining intent vocabulary is sealed
legacy consumers still function through adapters
mixed C++11/C++26 bridge compile/link qualification passes before modern runtime expansion
```

Rollback: feature selection routes presentation back to existing legacy consumers.

## 5. M2 — Vulkan device/platform foundation

Authorities:

```text
ADR-033 / architecture 081
ADR-045 / architecture 087/089
architecture 072 for output/swapchain extents
```

Work:

```text
SDL3 window/surface/event integration
Vulkan instance/device/feature chain with core >=1.4; accepted current 1.4.x tooling/registry tracked without a patch-level runtime pin
queues/frame contexts
allocator/descriptor heap
descriptor-heap Slang/SPIR-V/native production fixtures
pipeline cache
Frame Graph
swapchain/output contract
debug labels/validation
```

Initial render target may be a diagnostic clear/triangle. No production OpenGL consumer is removed yet.

Exit:

```text
validation-clean resize/fullscreen/swapchain lifecycle
B580 required features verified
frame-context lifetime tests pass
production binding path uses VK_EXT_descriptor_heap
```

Rollback: legacy renderer remains selectable.

## 6. M3 — Offline content/runtime asset foundation

Work:

```text
asset IDs/source hashes
rmesh/rskel/ranim/rmat/rmap/rshader loaders
Slang shader build path
legacy map/model/material conversion
legacy texture-source conversion
legacy audio-source identity/transcode preparation for M8
runtime asset registry
representative legacy source-content corpus
```

### Legacy source-content compatibility scope

The remaster supports **legacy source-content import**, not broad legacy mod compatibility.

Supported compatibility targets:

```text
maps / RMA source content
models / skeletons / animations where supported by the legacy source formats
textures and presentation material inputs
audio / music / sample source content
```

Not compatibility targets:

```text
legacy gameplay/configuration mods
legacy fs_gamedir behavior as a permanent mod ABI
legacy HUD/UI mods
legacy Lua callback ABI
legacy renderer/OpenGL extensions
legacy mixer internals
source-patch total conversions
private C/C++ structures or undefined engine behavior
```

Legacy source content may be converted offline into remaster runtime formats. Preserving an input format does not require preserving its old runtime loader.

Map handling remains special: canonical BSP/entity/spatial semantics stay authoritative, while `.rmap` and other presentation assets remain non-authoritative derivatives.

Exit:

```text
representative shipped assets compile/load deterministically
representative accepted legacy source content imports deterministically
source-hash mismatch is detected
shader ABI reflection checks pass
map conversion cannot replace canonical collision/routing/LOS/entity authority
```

Rollback: shipped content may continue to use the legacy asset path per feature until the corresponding production consumer migrates.

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
production objects enter through accepted asset/GPU-scene/binding contracts
```

Rollback: renderer feature flag remains available.

## 8. M5 — Tactical presentation parity and tactical OpenGL retirement

Work:

```text
complete tactical EV_* migration
animation transitions
selection/target overlays
world labels/interaction markers
basic particles/decals/lights
tactical audio-command publication path
make Vulkan the production tactical presentation default after parity evidence
remove dead tactical-only OpenGL callsites/ownership in later changes
```

Exit:

```text
complete tactical event catalog handled by the new path or an explicitly bounded non-OpenGL compatibility seam
canonical tactical replay hashes unchanged
presentation regression corpus passes accepted tolerances
Vulkan tactical path has been defaulted and soaked before tactical legacy deletion
no tactical production consumer requires direct OpenGL renderer state
```

Rollback:

```text
before tactical legacy deletion: runtime/feature selection
after deletion: version control
```

This is the first milestone where progressive OpenGL removal begins.

## 9. M6 — Strategic/campaign/Geoscape migration and strategic OpenGL retirement

Authorities:

```text
architecture 077–078
```

Work:

```text
consume/extend the qualified M1 StrategicSnapshot publication
strategic typed view models
StrategicIntent routing
Geoscape strategic scene extraction
radar/overlay data ownership conversion
campaign audio adapter
screen-by-screen legacy UI migration
make Vulkan the production Geoscape/strategic presentation default after parity evidence
remove dead Geoscape-specific OpenGL ownership in later changes
```

Exit:

```text
no production campaign direct cgi->R_* coupling
no raw renderer Geoscape buffer sharing
migrated screens have no direct canonical mutation from UI nodes
save/load rebuilds presentation correctly
no strategic/Geoscape production consumer requires direct OpenGL renderer state
```

Rollback:

```text
before strategic legacy deletion: per-screen/per-scene compatibility path
after deletion: version control
```

## 10. M7 — Retained UI/input and complete OpenGL decommission

Authorities:

```text
architecture 081 for SDL3 normalized controller/text/IME events
architecture 043-046 for retained UI semantics
architecture 076 for renderer removal callsites/gates
architecture 079/083 for the cinematic presentation boundary
```

Work:

```text
retained UI runtime
Vulkan text/glyph/2D renderer
keyboard/mouse/controller navigation
text input/IME
accessibility/focus
remaining campaign + tactical screens
minimal Vulkan cinematic frame upload/display bridge
remove remaining legacy renderer-owned image/model/UI/video presentation ownership
remove SDL OpenGL context creation
remove GLSL/OpenGL renderer state/program/framebuffer machinery
remove OpenGL build/link dependencies that are no longer required
remove legacy renderer selection after a separate default/soak step
```

The cinematic work here is intentionally limited to **presentation ownership** needed to stop OpenGL from surviving until M11. Full FFmpeg decode/stream/A-V behavior remains M11.

### OpenGL Decommission Gate

Full OpenGL deletion is allowed only after separate defaulting and soak changes have already established:

```text
Vulkan tactical presentation default and accepted
Vulkan strategic/Geoscape presentation default and accepted
retained UI/text/2D replacement default and accepted
image/model runtime ownership migrated
cinematic frame display no longer requires OpenGL
all production R_* imports/raw renderer pointers are removed or non-OpenGL compatibility-only and unused
source scan finds no unclassified production OpenGL calls/globals/context dependencies
canonical regression hashes remain unchanged
presentation regression/validation evidence passes
clean build succeeds without the legacy OpenGL renderer
```

Exit:

```text
legacy production node/data APIs no longer required
all authoritative UI actions are typed intents
input/resizing/DPI regression suite passes
no production OpenGL renderer implementation remains
no SDL GL context is created by the remaster
Vulkan is the only production graphics backend
```

Rollback:

```text
before full decommission: screen/subsystem feature selection
after full decommission: version control only
```

M8 and all later milestones are Vulkan-only.

## 11. M8 — OpenAL/EFX production audio and legacy mixer decommission

Work:

```text
AudioControl thread
voice virtualization
streaming/music
OpenAL Soft >=1.25.2 reference implementation qualification
OpenAL 1.1 + required EFX/HRTF capability checks and >=2 auxiliary sends/source
EFX environments/HRTF
acoustic scene/portals/occlusion
strategic+tactical command adapters
accepted legacy audio-source import through the new asset path
make OpenAL the production audio default after parity evidence
remove old mixer/source implementation in a later change
```

Exit:

```text
logical audio-command regression passes
no gameplay authority depends on audio state
CPU/audio budgets pass on i9-9900K
reference audio runtime satisfies OpenAL Soft >=1.25.2, ALC_EXT_EFX, ALC_SOFT_HRTF and >=2 auxiliary sends/source
all production sound consumers route through typed audio commands/new ownership
old mixer/source implementation and permanent fallback are removed
```

Rollback:

```text
before old-mixer deletion: legacy sound selection
after deletion: version control
```

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

Rollback: effect-class feature flags/fallbacks inside the modern Vulkan presentation stack.

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

Rollback: per-effect raster/non-RT quality fallbacks inside the Vulkan renderer.

## 14. M11 — Cinematic/video completion

Authorities:

```text
ADR-035
architecture 079
architecture 083
```

Work:

```text
FFmpeg demux/decode integration
streaming and buffering
audio/video synchronization
skip/transition behavior
color/output integration
shipped cinematic corpus qualification
remove any obsolete legacy decoder/runtime ownership
```

The Vulkan frame upload/display path already exists from M7.

Exit:

```text
all shipped cinematic corpus plays with correct A/V/skip/transition behavior
cinematic presentation uses Vulkan + new audio ownership only
no legacy immediate renderer/audio ownership remains in the cinematic path
```

Rollback: modern cinematic feature flags or version control; OpenGL is not a rollback backend.

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

## 16. M13 — Release hardening and packaging

Work:

```text
remove obsolete migration flags/adapters whose rollback windows have closed
remove unused legacy runtime parsers while retaining accepted offline source-content import where required
final source/dependency/ownership cleanup
final Fedora install/RPM/desktop integration
split debug symbols/build IDs
license/dependency inventory
release crash-diagnostics/symbol qualification
final clean-bootstrap and completeness audit
```

M13 does **not** carry the responsibility for deleting OpenGL or the old mixer; those are production decommission gates in M7 and M8 respectively.

Exit:

```text
clean source scan finds no unclassified legacy production dependency
clean build/test/install from documented bootstrap
final completeness + supersession audit passes
release packaging is reproducible
```

## 17. Ordering constraints

Hard ordering:

```text
M0 complete before implementation migration
M1 before deleting canonical-facing legacy adapters
M2 before Vulkan production presentation
M3 before production new renderer asset use
M4 before tactical Vulkan parity work
M5 before deleting tactical OpenGL presentation ownership
M6 before deleting strategic/Geoscape OpenGL presentation ownership
M7 before any milestone may assume OpenGL is absent
M7 completes full OpenGL decommission
M8 completes old-mixer decommission
M9 uses accepted Jolt/particle authorities
M10 requires stable raster geometry/material/AS contracts
M11 depends on the Vulkan cinematic display bridge established in M7
M12 specializes the modern-only production stack
M13 is last and performs release hardening, not deferred backend migration
```

Parallel work is allowed where these dependencies are respected.

## 18. Production retirement policy

Legacy implementation removal is **progressive**.

```text
M5  begin tactical OpenGL deletion
M6  delete strategic/Geoscape OpenGL ownership
M7  delete remaining UI/text/video-display/OpenGL infrastructure
M8  delete old mixer/audio runtime
M13 delete only residual migration scaffolding and obsolete parsers
```

A subsystem does not stay in the tree merely because it could be useful as a hypothetical compatibility backend. Once its replacement is proven, defaulted, soaked and separately decommissioned, version control is the rollback mechanism.

This policy keeps the production architecture moving toward one coherent runtime rather than maintaining two engines indefinitely.
## M1 authoritative intent surface v1 qualification — 2026-09-08

The source-derived authority classification and complete typed authoritative surface are now qualified at their stated migration scope.

Qualified surface:

```text
57/57 strategic authoritative semantics typed
15/15 tactical authoritative semantics typed
```

Current bridge state intentionally remains fail-closed where canonical owner extraction is pending:

```text
strategic: 3/57 canonical-applied, 54/57 fail-closed
tactical: 13/15 server-forwarded, 2/15 fail-closed
```

Canonical preservation passed twice at 104/104 with trace repeatability and M0.5 digest verification, and both fresh legacy/remaster production builds passed.

The next M1 implementation work is canonical owner/request-helper extraction. No further action-classification pass is required before that work.
