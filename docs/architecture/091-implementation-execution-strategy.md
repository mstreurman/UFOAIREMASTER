# Implementation Execution Strategy

**Status:** Accepted execution strategy for implementation work beginning after Baseline 041  
**Primary target:** Fedora 44 / Intel Core i9-9900K / Intel Arc B580  
**Canonical source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Milestone authority:** architecture 080  
**Purpose:** Define how the M0-M13 roadmap is executed, integrated, tested, measured, rolled back and eventually allowed to delete legacy presentation code.

## 1. Why this document exists

Architecture 080 defines **what order the milestones occur in**. It intentionally does not define the day-to-day implementation method inside those milestones.

This document supplies that missing execution layer.

The project will not use a flag-day rewrite. It will use a **risk-first, vertical-slice migration** with canonical gameplay continuously runnable and with old presentation paths retained until their explicit removal gates are satisfied.

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
        +--> switch defaults only after parity evidence
        |
        +--> delete legacy code only in a later change after rollback evidence exists
```

## 2. Non-negotiable implementation invariants

Every implementation change must preserve these project-level rules:

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

Do not first build every low-level subsystem to theoretical completion and only integrate them near the end. Each major foundation must acquire a real end-to-end consumer as early as practical.

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
R8  shipped-cinematic FFmpeg corpus qualification before decoder retirement
R9  raster/RT geometry parity fixture before RT lighting migration
```

A fixture proving a future subsystem contract does **not** move that subsystem's production milestone earlier. It only burns down a known risk before the project has accumulated dependencies on the assumption.

## 5. Implementation lanes

Implementation may proceed in parallel only where architecture 080 ordering constraints remain satisfied.

### Lane A — Preservation and canonical boundaries

Owns:

```text
canonical regression corpus
protocol/event fixtures
spatial-service wrappers
immutable snapshot/publication boundaries
replay hashes
canonical-state assertions
```

This lane starts in M0 and remains active through M13.

### Lane B — Platform and renderer foundation

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
```

This lane is the critical path through M2-M4.

### Lane C — Content and runtime assets

Owns:

```text
source identity
conversion tools
.r* containers
shader packaging
runtime asset registry
representative conversion corpus
```

It starts early enough that M4 never depends on ad-hoc legacy resource ownership.

### Lane D — Presentation subsystem migration

Owns incremental migration of:

```text
tactical presentation
strategic/Geoscape presentation
retained UI
OpenAL audio
VFX
Jolt presentation physics
cinematics
```

Each subsystem retains an explicit compatibility/fallback boundary until its exit gate is satisfied.

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
```

This is continuous; M12 is when target specialization becomes the dominant work rather than when measurement first begins.

## 6. Gate model for every mergeable implementation unit

Not every change needs every gate, but each change must explicitly identify the applicable gates.

### G0 — Build gate

```text
configured supported build succeeds
warnings/errors introduced by the change are resolved
new generated outputs are reproducible where applicable
```

### G1 — Component gate

```text
new unit/component tests pass
failure paths are exercised where practical
ABI/layout/static assertions pass where applicable
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
legacy/new comparison performed where the milestone requires parity
known intentional differences are documented
```

### G4 — API/validation gate

Examples:

```text
Vulkan validation clean
SPIR-V validates
shader ABI/reflection checks pass
OpenAL device/context errors checked
container/header/hash validators pass
```

### G5 — Stress/sanitizer gate

Applied to concurrency, lifetime, physics, streaming, allocator and similar risk-heavy code.

```text
long-running stress test where specified
ASAN/UBSAN or equivalent practical sanitizer pass
finite-state/lifetime invariants continuously asserted
```

### G6 — Performance gate

Required only when accepting/rejecting an optimization or satisfying a milestone budget.

```text
reference machine/toolchain recorded
before/after capture exists
CPU/GPU timing provenance recorded
quality settings recorded
regression threshold interpreted against architecture 073/055
```

### G7 — Clean-bootstrap gate

Required for M0 exit and again before M13 release closure.

```text
clean checkout
reproducible dependency/vendor/tool state
configure
build
tests
launch/smoke
```

## 7. Legacy/new selection and rollback rule

During migration, legacy and new presentation implementations may coexist behind compatibility adapters or selection mechanisms.

The required sequence is:

```text
1. introduce new seam/path without deleting old path
2. prove new path through applicable G0-G6 gates
3. make the new path selectable
4. make the new path the default only after milestone exit evidence exists
5. retain the old path long enough to provide a real rollback point
6. remove the old path in a later change only after source-boundary removal scans pass
```

Do not combine "new implementation becomes default" and "legacy implementation is deleted" into the same risky integration change.

Runtime selection mechanisms are migration tools unless their owning architecture explicitly requires them as permanent user-facing settings.

## 8. Canonical-code touch policy

Changes under canonical authority such as `src/game/`, server/common spatial services and canonical campaign state must be minimized.

Permitted implementation motives include:

```text
read-only publication/adaptation seam
instrumentation/reference capture
behavior-preserving optimization with canonical regression proof
bug fix explicitly accepted as a canonical change
```

Presentation convenience is not a valid reason to move gameplay decisions into renderer/audio/Jolt/UI code or to weaken a canonical boundary.

Where a legacy call mixes canonical and presentation responsibilities, split the interface before replacing the implementation.

## 9. Dependency ownership strategy

Dependency handling follows the already accepted Baseline-041 state:

```text
Slang v2026.17
    project-local provisioned tool cache
    exact artifact hash/pin
    not a source dependency to commit as arbitrary binaries

Jolt v5.6.0
    vendored source under third_party/JoltPhysics/
    exact commit + vendor manifest BLAKE3-256
    static project dependency

FFmpeg / SDL3 / OpenAL / Vulkan platform development packages
    reference Fedora package/toolchain state recorded
    configure-time capability/version checks
```

Generated build trees and local binary tool caches are not project source.

Vendored dependency modifications must update their patch list/vendor identity rather than becoming unrecorded local edits.

## 10. M0 execution strategy

M0 is not "start rewriting the renderer." It creates the safe implementation runway.

Recommended M0 work order:

```text
M0.1 repository ownership/ignore hygiene
M0.2 CMake presets/options and dependency discovery
M0.3 exact tool/RPM/vendor manifest capture
M0.4 clean canonical legacy build + launch smoke
M0.5 canonical regression/replay/reference harness
M0.6 feature-selection/compatibility scaffolding without behavior replacement
M0.7 standalone high-risk conformance fixtures that do not require production integration
M0.8 clean-checkout reproducibility proof
```

M0 exit means another clean checkout can reproduce the known environment and preservation evidence without relying on undocumented workstation state.

## 11. M1-M4 critical path

The shortest useful path to a real Vulkan tactical scene is:

```text
M1 canonical snapshot/event seams
    |
M2 SDL3 + Vulkan device + descriptor heap + allocator + frame contexts
    |
M2 Frame Graph + output/swapchain + debug/validation
    |
M3 shader package + representative runtime asset path
    |
M4 Presentation World static geometry + one model/material path
    |
M4 camera + basic G-buffer/deferred lighting
    |
M4 animation/skinning path
```

The first useful Vulkan target should be deliberately narrow. It should prove the actual production contracts rather than create a throw-away renderer architecture.

A diagnostic clear/triangle is valid for platform bring-up, but production objects should enter through the accepted descriptor-heap/GPU-scene/asset contracts rather than a temporary descriptor-set renderer that will later be rewritten.

## 12. Jolt strategy

Jolt has two distinct readiness states:

```text
dependency/build readiness
production presentation-physics qualification
```

Baseline 041 closes the first state.

Before broad ragdoll/debris integration depends on Jolt v5.6.0, execute the architecture-082 stress harness:

```text
>=256 dynamic bodies
contact-heavy stacking
ragdoll constraints
sleep/wake repetition
>=10 minutes
finite transforms and velocities every tick
ASAN/UBSAN where practical
```

If v5.6.0 reproduces the tracked non-finite failure, stop production integration and evaluate the already documented v5.5.0 fallback. Do not work around non-finite state inside presentation consumers.

## 13. Descriptor-heap strategy

Descriptor heap is not an optional late optimization.

The implementation sequence is:

```text
query and record exact B580 heap properties
allocate aligned SamplerHeap and ResourceHeap address ranges
prove write/bind/push-data commands in a native fixture
prove Slang sampled-image/storage-image/sampler/buffer/CBV cases
prove mixed resource byte allocation
prove AS 8-byte heap entries separately
prove non-uniform access behavior
freeze ShaderBindingAbiHash256 v2 fixture
only then make general renderer resources depend on the binding layer
```

No production descriptor-set renderer is built as a temporary fallback.

## 14. Performance strategy

Performance work starts with measurement but specialization is accepted only through evidence.

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

## 15. Commit/integration discipline

Implementation history should stay bisectable.

Preferred change shape:

```text
one contract or vertical slice per change
buildable at every integration point
no unrelated cleanup mixed with behavioral migration
format/mechanical churn separated from semantic changes
new default separated from legacy deletion
benchmark-driven optimization includes its measurement artifact/reference
```

Large generated/vendor content changes should be isolated so source review remains possible.

The exact Git branching workflow is repository-process policy rather than engine architecture; this strategy requires only that integration points remain buildable, reviewable and bisectable.

## 16. Definition of done for a milestone

A milestone is complete only when all of the following are true:

```text
its architecture-080 work list is implemented
applicable G0-G7 gates pass
new source ownership is documented
legacy fallback/removal state is explicit
known deviations are documented
performance evidence exists where required
rollback path is still valid or the legacy removal gate is explicitly satisfied
clean status/evidence is captured in the documentation baseline
```

"The code seems to work" is not a milestone exit condition.

## 17. Definition of done for legacy removal

A legacy subsystem may be removed only when:

```text
new path has already been defaulted and validated in an earlier integration step
all production consumers are migrated or intentionally removed
source scans find no unclassified includes/calls/globals from the old subsystem
canonical regression evidence remains unchanged
presentation parity/acceptance evidence passes
rollback is available from version control even though runtime fallback is being removed
build/package/license state remains reproducible
```

For renderer and sound specifically, architecture 076 remains the callsite/removal authority.

## 18. Initial implementation sequence after Baseline 042

The recommended first implementation queue is:

```text
1. repository ownership/ignore hygiene
2. CMake presets + dependency/vendor verification
3. canonical clean-build/launch/reference harness
4. M0 feature-selection scaffolding
5. native VK_EXT_descriptor_heap execution fixture
6. Slang descriptor-heap ABI/package fixture
7. Jolt >=256-body >=10-minute stress qualification
8. SDL3/Vulkan platform bootstrap under the new presentation selection
9. frame-context + allocator + descriptor-heap runtime
10. Frame Graph + swapchain diagnostic frame
11. representative .rshader/.r* asset pipeline slice
12. Presentation World -> first real Vulkan tactical scene slice
```

Items 5-7 intentionally pull high-risk qualification work forward while M0/M1/M2 are still cheap to change.

## 19. Relationship to the roadmap

Architecture 080 remains authoritative for milestone ordering and ownership.

This document adds the execution rule:

```text
architecture 080 = what milestone comes when
architecture 091 = how every milestone is implemented safely
```

If an implementation plan conflicts with architecture 080's hard ordering constraints, architecture 080 wins. If a milestone plan omits the preservation, gate, rollback or vertical-slice rules defined here, the milestone plan is incomplete.
