# Implementation Execution Strategy

**Status:** Accepted execution strategy — revised after M0 qualification for progressive legacy retirement  
**Primary target:** Fedora 44 / Intel Core i9-9900K / Intel Arc B580  
**Canonical source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Qualified remaster planning head:** `b0eb12631c71e90b7c3d1f6d19e618e7656c80be`  
**Milestone authority:** architecture 080  
**Language/toolchain authority:** architecture 092  
**Purpose:** Define how the M0-M13 roadmap is executed, integrated, tested, measured, rolled back and allowed to retire obsolete presentation implementations as soon as their replacements are proven.

## 1. Why this document exists

Architecture 080 defines **what order the milestones occur in**. This document defines the production method used inside those milestones.

The project does not use a flag-day rewrite. It uses a **risk-first, vertical-slice migration** with canonical gameplay continuously runnable.

The important post-M0 refinement is that legacy presentation implementations are not retained until release by default. A legacy path remains only while it is a useful, tested migration/rollback mechanism for the subsystem currently replacing it.

The execution model is:

```text
preserve canonical behavior
        |
        +--> prove high-risk dependencies/contracts in isolation
        |
        +--> establish modern platform/render/runtime foundations
        |
        +--> migrate one observable presentation slice at a time
        |
        +--> switch that slice to the modern default after parity evidence
        |
        +--> keep a short real rollback window
        |
        +--> delete the obsolete implementation in a separate change
        |
        +--> continue without carrying dead backends
```

For graphics this means complete OpenGL decommission in M7. For sound it means old-mixer decommission in M8. M13 is release hardening, not deferred backend replacement.

## 2. Non-negotiable implementation invariants

Every implementation change must preserve:

```text
canonical UFO:AI gameplay remains authoritative
presentation receives canonical state/events; it does not feed simulation answers back
canonical tracing/LOS/pathfinding/collision remain canonical services
Vulkan RT never becomes gameplay LOS or projectile authority
Jolt never becomes canonical collision or movement authority
OpenAL state never becomes gameplay authority
animation/root motion never becomes canonical movement authority
runtime display/audio configuration remains selectable
B580/i9-9900K remains the primary optimization and qualification target
VK_EXT_descriptor_heap is the production renderer binding model from first Vulkan renderer implementation
OpenGL is a temporary migration backend, not a permanent remaster backend
legacy gameplay/UI/mod ABI compatibility is not a design constraint
accepted legacy source content is imported/converted without preserving obsolete runtime ownership
retained canonical/legacy targets stay C++11 initially; new remaster runtime targets use strict C++26
shared canonical/remaster bridge headers remain C++11-compatible
Vulkan runtime requires core >=1.4 without a patch-level 1.4.x minimum
Slang compiler identity remains exact/pinned and hash-qualified
OpenAL production qualification uses OpenAL Soft >=1.25.2 with required EFX/HRTF capabilities
```

A change that cannot demonstrate where it sits relative to these invariants is not ready to merge.

## 3. Work is organized as vertical slices

A vertical slice is the smallest change that crosses all layers necessary to prove a useful contract without replacing more legacy behavior than necessary.

Preferred slice shape:

```text
canonical source/event/snapshot input
        -> adapter/publication seam
        -> new presentation representation
        -> new subsystem execution
        -> visible/audible/debuggable output
        -> regression/validation evidence
```

Examples:

```text
EV_ACTOR_MOVE
    -> Presentation World event projection
    -> render snapshot transform
    -> Vulkan scene upload
    -> one visible actor moving correctly
    -> canonical replay hash unchanged

EV_SOUND
    -> typed AudioCommand
    -> AudioControl thread
    -> OpenAL source
    -> logical-command + audible smoke evidence
    -> no canonical state dependency on source lifetime
```

Do not build every low-level subsystem to theoretical completion before integration. Each major foundation must acquire a real end-to-end consumer as early as practical.

## 4. Risk-burn-down lane runs ahead of feature migration

High-risk assumptions must be proved with small standalone or minimally integrated fixtures before broad production code depends on them.

Priority risk fixtures are:

```text
R1  canonical preservation/replay/reference harness
R2  native VK_EXT_descriptor_heap sampler/resource execution fixture
R3  Slang -> SPV_EXT_descriptor_heap ABI/reflection/package fixture
R4  8-byte acceleration-structure heap + TraceRay/ray-query conformance fixture
R5  Jolt v5.6.0 >=256-body >=10-minute finite-transform sleep/wake stress fixture
R6  SDL3/Wayland resize/fullscreen/display/HDR lifecycle fixture
R7  representative asset conversion + deterministic load fixture
R8  Vulkan cinematic frame upload/display fixture before OpenGL decommission
R9  shipped-cinematic FFmpeg corpus qualification before legacy decoder retirement
R10 raster/RT geometry parity fixture before RT lighting migration
R11 strict C++11 bridge + strict C++26 runtime mixed compile/link/run fixture before typed-intent/runtime expansion
```

M0 has already closed the initial high-risk qualification set needed to start implementation. Later fixtures remain risk-burn-down work and do not by themselves advance a production milestone.

## 5. Implementation lanes

Implementation may proceed in parallel only where architecture 080 ordering constraints remain satisfied.

### Lane A — Preservation and canonical boundaries

Owns:

```text
canonical regression corpus
protocol/event fixtures
spatial-service wrappers
immutable snapshot/publication boundaries
typed intent seams
replay hashes
canonical-state assertions
```

This lane starts in M0 and remains active through M13.

### Lane B — Platform, renderer and renderer retirement

Owns:

```text
SDL3 platform bootstrap
Vulkan instance/device/surface
feature negotiation
frame contexts
memory allocator
VK_EXT_descriptor_heap
Frame Graph
swapchain/output state
shader/package runtime
GPU scene
OpenGL consumer retirement
OpenGL source/build dependency removal
```

This lane is the critical path through M2-M7.

### Lane C — Content and runtime assets

Owns:

```text
source identity
conversion tools
.r* containers
shader packaging
runtime asset registry
representative shipped conversion corpus
legacy source-content import corpus
```

Legacy compatibility in this lane is deliberately limited to supported **source content** such as maps/RMA, models/animations, textures/material inputs and audio source files.

This lane does not preserve a general legacy mod framework, old GUI ABI, old renderer ABI, `fs_gamedir` semantics as a permanent contract, or source-patch compatibility.

### Lane D — Presentation subsystem migration

Owns incremental migration of:

```text
tactical presentation
strategic/Geoscape presentation
retained UI
cinematic frame presentation
OpenAL audio
VFX
Jolt presentation physics
full FFmpeg cinematic runtime
```

Each subsystem retains a compatibility/fallback boundary only until its exit/default/soak/decommission sequence is complete.

### Lane E — Qualification and optimization

Owns:

```text
validation-layer runs
sanitizers
stress tests
B580/i9-9900K benchmark captures
HDR/output qualification
memory/residency telemetry
before/after optimization evidence
release completeness scans
clean-bootstrap release proof
```

This is continuous. M12 is when specialization becomes dominant work rather than when measurement first begins.

## 6. Gate model for every mergeable implementation unit

Not every change needs every gate, but each change must explicitly identify the applicable gates.

### G0 — Build gate

```text
configured supported build succeeds
retained legacy/bridge targets compile under their explicit C++11 policy where applicable
new remaster runtime targets compile under strict C++26 with extensions disabled
warnings/errors introduced by the change are resolved
no inherited global C++0x flag overrides target language ownership
new generated outputs are reproducible where applicable
```

### G1 — Component gate

```text
new unit/component tests pass
failure paths are exercised where practical
ABI/layout/static assertions pass where applicable
mixed C++11 producer / C++26 consumer compile-link-run contract passes where the language boundary is touched
```

### G2 — Canonical-preservation gate

Required for any change touching a canonical-facing seam.

```text
canonical event/protocol/reference behavior unchanged
canonical replay/reference hashes unchanged where defined
no presentation result is consumed as canonical input
```

### G3 — Presentation-regression gate

```text
expected presentation output/command/state captured
legacy/new comparison performed while the legacy reference still exists
known intentional differences are documented
```

After an owning legacy subsystem has been decommissioned, preserved captures/reference artifacts replace runtime A/B as the historical comparison source.

### G4 — API/validation gate

Examples:

```text
Vulkan validation clean
SPIR-V validates
shader ABI/reflection checks pass
OpenAL device/context errors checked
container/header/hash validators pass
SDL3 lifecycle diagnostics clean
```

### G5 — Stress/sanitizer gate

Applied to concurrency, lifetime, physics, streaming, allocator and similar risk-heavy code.

```text
long-running stress test where specified
ASAN/UBSAN or equivalent practical sanitizer pass
finite-state/lifetime invariants continuously asserted
```

### G6 — Performance gate

Required when accepting/rejecting an optimization or satisfying a milestone budget.

```text
reference machine/toolchain recorded
before/after capture exists
CPU/GPU timing provenance recorded
quality settings recorded
regression threshold interpreted against architecture 073/055
```

### G7 — Clean-bootstrap gate

Required for M0 closure and M13 release closure, and may be required for a major decommission gate when build dependencies change materially.

```text
clean checkout
reproducible dependency/vendor/tool state
configure
build
tests
launch/smoke
```

## 7. Default, rollback and decommission rule

A replacement follows this sequence:

```text
1. introduce the new seam/path without deleting the old path
2. prove the new path through applicable G0-G6 gates
3. make the new path selectable
4. make the new path the production default only after milestone evidence exists
5. retain the old path long enough to exercise a real rollback point
6. run source-boundary/removal scans
7. delete the old path in a later change
8. rerun applicable build/regression/validation/bootstrap gates
9. use version control, not a dead runtime backend, as rollback after deletion
```

Do not combine **new default** and **legacy deletion** in the same risky integration change.

Runtime selection mechanisms are migration tools unless an owning architecture explicitly requires them as permanent user-facing settings.

A legacy subsystem must not be retained merely for hypothetical compatibility once its replacement has passed this sequence.

## 8. Canonical-code touch policy

Changes under canonical authority such as `src/game/`, server/common spatial services and canonical campaign state must be minimized.

Permitted motives include:

```text
read-only publication/adaptation seam
instrumentation/reference capture
behavior-preserving optimization with canonical regression proof
bug fix explicitly accepted as a canonical change
```

Presentation convenience is not a valid reason to move gameplay decisions into renderer/audio/Jolt/UI code or weaken a canonical boundary.

Where a legacy call mixes canonical and presentation responsibilities, split the interface before replacing the implementation.

## 9. Legacy content and mod-compatibility production policy

The remaster does **not** promise drop-in compatibility for the historical UFO:AI mod ecosystem.

Not protected as compatibility contracts:

```text
gameplay/config override mods
old total conversions
legacy GUI/HUD definitions
legacy Lua callback ABI
OpenGL renderer imports/state
old mixer/source internals
private C/C++ structures
source patches
undefined behavior
fs_gamedir behavior as a permanent public ABI
```

Supported legacy compatibility work is limited to accepted source-content import:

```text
maps / RMA source content
models / skeletons / animations where supported
textures / presentation material inputs
audio / music / sample files
```

Importers may translate old source formats into new runtime containers. Runtime ownership and parser architecture are free to change.

For maps, canonical BSP/entity/spatial semantics remain authoritative. Presentation conversion must not replace canonical collision, routing, LOS, trigger, spawn, door, mission or other gameplay-authoritative behavior.

A future remaster mod API may be designed separately as a versioned modern interface. It is not constrained by historical renderer/UI/internal ABI compatibility.

## 10. Dependency ownership strategy

Dependency handling follows the accepted project state:

```text
C++ toolchain
    GCC 16.2.x primary C++26 compiler family
    retained canonical/legacy targets C++11 initially
    new remaster runtime targets strict C++26
    shared bridge headers C++11-compatible
    one compatible libstdc++ ABI configuration across in-process targets
    CMake >=3.25 for CXX_STANDARD 26 awareness

Vulkan
    runtime core API >=1.4
    accepted current Vulkan 1.4.x headers/registry/validation tooling
    no patch-level 1.4.x runtime minimum
    required extensions/features capability-tested

Slang v2026.17
    project-local provisioned tool cache
    exact artifact hash/pin
    update only through explicit reprovisioning/qualification

OpenAL / OpenAL Soft
    stable OpenAL 1.1 API contract
    OpenAL Soft >=1.25.2 reference implementation for production audio qualification
    require ALC_EXT_EFX + ALC_SOFT_HRTF + >=2 auxiliary sends/source on the reference target
    optional SOFT extensions capability-probed
    current workstation 1.24.2 remains evidence but requires upgrade/requalification before M8 closure

Jolt v5.6.0
    vendored source under third_party/JoltPhysics/
    exact commit + vendor manifest identity
    static project dependency

FFmpeg / SDL3 platform development packages
    reference Fedora package/toolchain state recorded
    configure-time capability/version checks
```

Generated build trees and local binary tool caches are not project source.

Vendored dependency modifications must update their patch list/vendor identity rather than become unrecorded local edits.

OpenGL development/runtime packages may remain during migration only while the legacy renderer still builds. M7 decommission must prove the remaster configures/builds without the obsolete OpenGL renderer dependency set.

## 11. M0 qualification state

M0 is complete and sealed. It is no longer the current production phase.

The sealed state provides:

```text
reproducible clean checkout/bootstrap
canonical legacy build + launch reference
canonical regression/replay/reference corpus
migration feature-selection scaffolding
descriptor-heap qualification
Slang descriptor-heap qualification
acceleration-structure heap qualification
Jolt stress qualification
clean-checkout reproducibility evidence
```

Implementation now begins at M1.

## 12. M1-M4 critical path

The shortest useful path to a real Vulkan tactical scene is:

```text
M1 canonical snapshot/event seams + C++11/C++26 target boundary + typed intent seams
    |
M2 SDL3 + Vulkan device + descriptor heap + allocator + frame contexts
    |
M2 Frame Graph + output/swapchain + debug/validation
    |
M3 shader package + representative runtime asset/content-import path
    |
M4 Presentation World static geometry + one model/material path
    |
M4 camera + basic G-buffer/deferred lighting
    |
M4 animation/skinning path
```

The first useful Vulkan target should be deliberately narrow and should prove production contracts rather than create a throw-away renderer.

A diagnostic clear/triangle is valid for platform bring-up, but production objects must enter through accepted descriptor-heap/GPU-scene/asset contracts rather than a temporary descriptor-set renderer.

## 13. OpenGL retirement strategy

OpenGL retirement is progressive, not postponed to M13.

### M5 — tactical retirement

Required sequence:

```text
complete tactical event/presentation parity
default Vulkan tactical presentation in a separate change
soak/validate against canonical and presentation corpus
remove tactical-only direct R_*/OpenGL ownership in later changes
```

Shared OpenGL infrastructure may remain if strategic/UI/video consumers still require it.

### M6 — strategic/Geoscape retirement

Required sequence:

```text
migrate StrategicSnapshot/scene/UI coupling
default Vulkan strategic/Geoscape presentation
soak/validate
remove Geoscape-specific renderer ownership and raw buffers
```

### M7 — final OpenGL decommission

Before deleting the renderer implementation, all of the following must already be modern-owned:

```text
tactical world rendering
strategic/Geoscape rendering
UI/text/2D drawing
image/model runtime ownership
cinematic frame upload/display
window/surface lifecycle
```

Then:

```text
default retained UI/Vulkan video presentation
soak/validate in earlier changes
scan all production R_* imports/raw renderer pointers/OpenGL calls
remove legacy renderer source families
remove SDL GL context creation
remove GL state/program/framebuffer machinery
remove renderer fallback selection
remove obsolete OpenGL build/link dependencies
rerun build/canonical/presentation/validation/clean-bootstrap gates as applicable
```

After M7, OpenGL is not an available runtime rollback backend. Rollback is version control.

M8-M13 must not reintroduce OpenGL assumptions.

## 14. OpenAL and old-mixer retirement strategy

OpenAL follows the same production discipline.

```text
typed AudioCommand path exists first
OpenAL Soft >=1.25.2 reference implementation and required EFX/HRTF capabilities are qualified
OpenAL runtime becomes selectable
logical/audible regression evidence passes
OpenAL becomes production default
a real rollback window is exercised
old mixer/source implementation is removed in a later change
```

M8 exit requires old-mixer decommission. M13 must not carry an old audio backend merely for cleanup.

## 15. Jolt strategy

Jolt has two distinct readiness states:

```text
dependency/build readiness
production presentation-physics qualification
```

M0 closes the initial dependency and stress-qualification state for the accepted pin.

Broad ragdoll/debris integration must still preserve:

```text
presentation-only authority
finite transforms/velocities
bounded lifetime
canonical replay invariance
CPU/GPU budget evidence
```

If production integration uncovers a pin-specific non-finite regression, stop the affected presentation feature and reopen the documented dependency gate rather than masking invalid state in consumers.

## 16. Descriptor-heap strategy

Descriptor heap is not an optional late optimization.

The implementation sequence is:

```text
query and record exact B580 heap properties
allocate aligned SamplerHeap and ResourceHeap address ranges
use the already-qualified native write/bind/push-data behavior
use the already-qualified Slang resource ABI
preserve the accepted 8-byte AS heap representation
freeze/validate ShaderBindingAbiHash256 fixtures
make general renderer resources depend on the production binding layer
```

No production descriptor-set renderer is built as a temporary fallback.

## 17. Performance strategy

Performance work starts with measurement, but specialization is accepted only through evidence.

### From day one

Record enough telemetry to know:

```text
CPU frame phases
GPU passes
queue overlap
allocation/residency pressure
pipeline/shader compilation behavior
presentation job counts
frame pacing/tail behavior
```

### Before M12

Prefer architectural correctness and representative data over micro-optimization, except where a target-specific decision determines a public ABI, queue model or resource layout.

### M12

Use architecture 073 gates for:

```text
i9-9900K AVX2/FMA kernels
worker placement/topology decisions
B580 subgroup/workgroup sizes
RT-pipeline vs narrowly scoped ray-query exceptions
allocator/residency thresholds
GPU-driven submission choices
PGO/LTO
compression/tuning
```

"Faster on another machine" does not replace evidence on the B580/i9-9900K qualification target.

## 18. Commit/integration discipline

Implementation history must stay bisectable.

Preferred change shape:

```text
one contract or vertical slice per change
buildable at every integration point
no unrelated cleanup mixed with behavioral migration
format/mechanical churn separated from semantic changes
new default separated from legacy deletion
legacy deletion separated by subsystem instead of one giant final purge
benchmark-driven optimization includes measurement evidence
```

Large generated/vendor content changes should be isolated so source review remains possible.

The exact Git branching workflow is repository-process policy rather than engine architecture; this strategy requires only buildable, reviewable and bisectable integration points.

## 19. Definition of done for a milestone

A milestone is complete only when:

```text
its architecture-080 work list is implemented
applicable G0-G7 gates pass
new source ownership is documented
legacy fallback/removal state is explicit
known deviations are documented
performance evidence exists where required
rollback state matches the milestone policy
clean status/evidence is captured in the documentation baseline
```

"The code seems to work" is not a milestone exit condition.

## 20. Definition of done for legacy removal

A legacy subsystem may be removed only when:

```text
new path was already defaulted in an earlier integration change
all production consumers are migrated or intentionally removed
a real rollback window existed before deletion
source scans find no unclassified includes/calls/globals from the old subsystem
canonical regression evidence remains unchanged
presentation parity/acceptance evidence passes
version control provides post-deletion rollback
build/package/license state remains reproducible
```

For renderer and sound specifically, architecture 076 remains the callsite/removal authority.

Removal is not delayed to M13 once these conditions are met.

## 21. Current production sequence after M0

The recommended implementation queue is now:

```text
1. M1 canonical spatial wrappers/tests
2. M1 immutable tactical/strategic publication seams
3. M1 typed presentation IDs and intent dispatch
4. M2 SDL3/Vulkan production platform bootstrap
5. M2 frame contexts + allocator + descriptor-heap runtime
6. M2 Frame Graph + swapchain/output diagnostic frame
7. M3 representative .rshader/.r* asset pipeline
8. M3 legacy source-content import fixtures for maps/models/textures/audio
9. M4 Presentation World -> first real Vulkan tactical scene
10. M5 complete tactical presentation parity
11. M5 default Vulkan tactical presentation, soak, then delete tactical GL ownership
12. M6 migrate strategic/Geoscape presentation, default it, then delete strategic GL ownership
13. M7 complete retained UI/text/2D + Vulkan cinematic frame display
14. M7 default/soak those paths, then fully decommission OpenGL
15. M8 complete OpenAL/EFX production audio, default/soak, then remove old mixer
16. M9 VFX + Jolt presentation physics
17. M10 RT lighting/reconstruction
18. M11 complete FFmpeg cinematic runtime
19. M12 target specialization
20. M13 release hardening/packaging
```

This sequence deliberately prevents OpenGL and the old mixer from surviving simply because release cleanup has not started.

## 22. Relationship to the roadmap

Architecture 080 remains authoritative for milestone ordering and ownership.

```text
architecture 080 = what milestone comes when and when legacy systems are decommissioned
architecture 091 = how every milestone/default/rollback/deletion change is implemented safely
```

If an implementation plan conflicts with architecture 080's hard ordering constraints, architecture 080 wins. If a milestone plan omits the preservation, gate, rollback, progressive-retirement or vertical-slice rules defined here, the milestone plan is incomplete.
