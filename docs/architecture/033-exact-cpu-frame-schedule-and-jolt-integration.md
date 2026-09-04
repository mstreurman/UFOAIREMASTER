# Exact CPU Frame Schedule and Jolt Integration

**Status:** Implementation specification baseline  
**Related ADR:** ADR-023

## 1. CPU frame contexts

Use a small ring independent from GPU FrameContext ownership if helpful, but baseline logical CPU frame execution is:

```text
Frame N:
    canonical/mirror/presentation work
    immutable snapshot publication
```

The render queue allows at most one pending RenderSnapshot.

## 2. Phase 0 — platform/input

Owner:

```text
Main
```

Work:

```text
acquire CPU frame scratch
read timing
drain platform/input events
prepare canonical input
```

No worker dependency.

## 3. Phase 1 — canonical simulation

Owner:

```text
Main only
```

Includes the existing authoritative UFO:AI game/server/client processing needed for the frame.

Canonical ownership includes:

```text
rules
AI
damage
movement
inventory
routing/pathfinding
LOS/visibility
mission/campaign state
```

Do not schedule canonical mutations onto presentation workers in baseline 016.

## 4. Phase 2 — tactical event decode/mirror

Owner:

```text
Main only
```

Pipeline:

```text
canonical/legacy event bytes
    ->
ordered event decode
    ->
TacticalClientMirror mutation
    ->
typed PresentationEvent[]
```

Preserve protocol ordering and scheduler locking semantics.

## 5. Phase 3 — Presentation World structural commit

Owner:

```text
Main
```

Apply structural commands:

```text
spawn/despawn
component add/remove
mesh/material changes
animation-state transitions
Jolt create/destroy commands
audio source structural changes
VFX emitter structural changes
cutaway/floor state
```

After commit:

```text
presentation structural topology frozen for Frame N
```

Workers may then process stable arrays/ranges.

## 6. Phase 4 — animation sample

Lane:

```text
PrimaryOnly
```

Partition primarily by actor.

Each job writes exclusive frame-local pose ranges.

Baseline data path:

```text
animation state
    ->
clip sampling/blending
    ->
local joint pose
```

This is an AVX2/FMA optimization target.

## 7. Phase 5 — hierarchy/socket evaluation

Lane:

```text
PrimaryOnly
```

Partition by actor/skeleton instance.

Pipeline:

```text
local pose
    ->
hierarchy
    ->
model/world joint transforms
    ->
socket/attachment transforms
```

Do not attempt arbitrary cross-joint parallelism within small skeletons.

## 8. Phase 6 — Jolt command commit

Owner:

```text
Main
```

Apply one-way presentation physics commands:

```text
create body
destroy body
kinematic transform
ragdoll activation from current pose
visual impulse
presentation debris spawn
```

All commands originate from canonical/presentation events or Presentation World state.

No Jolt result is applied to canonical simulation.

## 9. Phase 7 — Jolt update

Adapter:

```text
UfoJoltJobSystem : JPH::JobSystemWithBarrier
```

Workers:

```text
Main
+
PrimaryWorker[0..5]
```

SMT helpers:

```text
parked
```

Effective maximum concurrency:

```text
7
```

## 10. Jolt timestep

Baseline:

```cpp
constexpr double kJoltDt = 1.0 / 60.0;
constexpr uint32_t kJoltCollisionSteps = 1;
constexpr uint32_t kJoltMaxCatchupSteps = 2;
```

Accumulator:

```text
presentationDelta -> accumulator
```

Run at most two fixed steps.

If the accumulator remains excessively behind after that:

```text
discard excess presentation-physics backlog
```

rather than stalling canonical simulation or changing canonical time.

## 11. Jolt wait isolation

While Jolt barrier execution is active:

```text
Main/Primary workers execute only Jolt-domain work through the Jolt adapter
```

Do not execute arbitrary jobs that may race with physics-owned state while waiting for Jolt barriers.

## 12. Phase 8 — presentation finalization

After Jolt returns, fan out independent work.

### Ragdoll pose extraction

```text
Jolt body transforms
    ->
ragdoll joint pose
    ->
skin matrices
```

### Normal animated skin palette

```text
evaluated skeleton
    ->
current skin matrices
```

### World transforms

```text
local/entity/socket/Jolt transform
    ->
final presentation transform
```

### Parallel supporting work

```text
audio source transforms
VFX spawn/update preparation
light-list preparation
visibility bounds
render instance metadata
RT instance metadata
material/object classification
```

Use:

```text
PrimaryOnly
SmtFriendly
```

according to kernel profile.

## 13. Phase 9 — snapshot array construction

Build immutable-frame arrays.

Prefer deterministic two-stage packing:

```text
count per partition
    ->
prefix sum
    ->
write fixed exclusive output ranges
```

Avoid ordering-sensitive atomic append for important renderer arrays.

Snapshot includes:

```text
camera/view
instances
lights
bone palette references
material references
RT metadata
cutaway state
VFX data
audio state reference
```

## 14. Phase 10 — seal/publish

Owner:

```text
Main
```

Seal/publish the appropriate one-way presentation products:

```text
RenderSnapshot
AudioStateSnapshot
ordered AudioCommandQueue entries
```

After sealing:

```text
no writer exists
```

Publish RenderSnapshot through a single-producer/single-consumer queue to Render thread.

Maximum pending snapshots:

```text
1
```

If Render cannot consume and queue is full:

```text
Main eventually waits
```

rather than increasing frame latency with a deep queue.

## 15. Render thread

Render thread baseline ownership:

```text
consume RenderSnapshot
acquire GPU FrameContext
drain upload requests
fill mapped frame resources
publish descriptor-heap entries
compile Frame Graph
record Vulkan commands
submit transfer queue
submit graphics/RT queue
present
consume completed GPU timestamps
retire completed GPU resources
```

Workers do not baseline-record Vulkan commands.

## 16. Render/Main overlap

Conceptually:

```text
Main:
    Canonical N
    Presentation N
    Snapshot N
        |
        +----> starts next frame work when allowed

Render:
    finish/submit N-1
        |
        consume Snapshot N
        |
        record/submit N

GPU:
    executes prior/current submitted frames
```

The design avoids deliberately running simulation several frames ahead.

## 17. Upload/background integration

Background jobs may perform:

```text
file/page-cache read preparation
chunk decompression
asset validation
CPU-side conversion needed by runtime asset loading
upload-request construction
```

Prefer SMT workers.

Then:

```text
MPSC UploadRequest queue
    ->
Render thread
    ->
family-2 transfer queue
```

Only the Render thread mutates Vulkan upload/runtime ownership in baseline.

## 18. OpenAL integration

Engine jobs/Main may prepare:

```text
AudioStateSnapshot
source transforms
environment/EFX state
ordered AudioCommandQueue entries
```

`AudioStateSnapshot` is continuous/latest-wins.

`AudioCommandQueue` is ordered and cannot be replaced by a newer snapshot.

Only `AudioControl` calls AL/ALC/EFX according to ADR-024/architecture 035–038.

OpenAL Soft backend/mixer threads remain library-owned.

Do not pin/override internal OpenAL threads until profiling demonstrates a need.

## 19. CPU frame DAG

```text
INPUT
  |
  v
CANONICAL
  |
  v
EVENT DECODE / MIRROR
  |
  v
PRESENTATION STRUCTURAL COMMIT
  |
  +---------------------------+
  |                           |
  v                           v
ANIMATION SAMPLE       EARLY AUDIO/VFX/LIGHT PREP
  |
  v
POSE HIERARCHY
  |
  v
JOLT COMMAND COMMIT
  |
  v
JOLT UPDATE
  |
  +----------------------+----------------------+
  |                      |                      |
  v                      v                      v
RAGDOLL POSE       WORLD TRANSFORMS       AUDIO/VFX FINAL
  |                      |
  +----------+-----------+
             |
             v
      RENDER/RT PREP
             |
             v
       SNAPSHOT BUILD
             |
             v
            SEAL
             |
             v
         RenderThread
             |
             v
   VULKAN FRAME/SUBMISSION
```

## 20. Phase debug validation

Development builds assert:

```text
canonical mutation occurs on Main
mirror mutation occurs on Main
Presentation World structural mutation is not occurring after structural freeze
snapshot writes are within assigned ranges
sealed snapshots are immutable
Vulkan mutation occurs on Render baseline
Jolt-world writes occur only through valid Jolt phase/API
```

## Jolt spatial-unit contract

ADR-028/architecture 051 owns unit conversion.

```text
meters = presentationUnits / 32
```

Jolt output converts back only into presentation transforms and never canonical movement/collision/routing state.

## Presentation gravity baseline

Architecture 060 locks the starting Jolt world gravity:

```text
(0, 0, -9.81) m/s^2
```

with +Z up.

This is presentation-only and never changes canonical projectile/movement physics.
