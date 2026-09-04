# Canonical/Presentation Replay and Regression Harness

**Status:** Implementation specification baseline  
**Related ADR:** ADR-027

## 1. Replay modes

```cpp
enum class ReplayMode {
    Canonical,
    Presentation,
    Full
};
```

## 2. Canonical replay goal

Answer exactly:

```text
Did the authoritative game produce the same semantic state?
```

Capture enough inputs/state to reproduce:

```text
initial canonical checkpoint
map/content identity
ordered player/client commands
network/external authoritative inputs where applicable
canonical RNG seed/state requirements
canonical timing inputs that affect simulation
```

## 3. Canonical semantic hash

Do not hash raw C/C++ memory.

Create a stable semantic serialization with:

```text
defined field order
defined integer widths
defined floating representation where applicable
stable container ordering
no pointers
no padding
no uninitialized bytes
```

Then:

```text
BLAKE3-256
```

hash each defined checkpoint.

## 4. Canonical checkpoint cadence

Checkpoint at meaningful synchronization boundaries such as:

```text
canonical command batch
server/game tick/batch
tactical event flush boundary
campaign action boundary
save/load boundary
```

Exact cadence is subsystem-specific.

## 5. First divergence

On hash mismatch:

```text
find first mismatching checkpoint
    ->
rerun/dump semantic state around it
    ->
produce object/field-level diff
```

Long replays may use checkpoint binary search.

## 6. RNG audit

Before canonical replay can be declared deterministic, audit authoritative code for:

```text
rand/random APIs
wall-clock reads
unordered iteration affecting outcome
implicit non-stable seeds
platform-dependent numeric behavior
```

Centralize or record only what is necessary.

Presentation-only randomness does not become canonical state.

## 7. Presentation replay goal

Answer:

```text
Can we reproduce the same presentation workload independent of game simulation?
```

Capture/replay:

```text
typed PresentationEvents
Tactical Client Mirror update stream as needed
camera actions
cutaway/floor actions
UI presentation actions
presentation timing
stable presentation random seeds/IDs
```

## 8. Presentation replay targets

Replay directly into:

```text
Presentation World
Animation
Jolt
VFX
Audio
Renderer
UI
```

This is the main repeatable B580 performance/render-quality workload.

## 9. Full replay

```text
CanonicalReplay
    ->
PresentationEvents
    ->
PresentationReplay
```

Validate:

```text
canonical hashes
event-stream hash
presentation structural hashes
visual output
performance
resource/lifetime state
```

## 10. Replay file

Use common remaster chunk-container conventions.

Extension:

```text
.uforeplay
```

Initial logical chunks:

```text
HEAD
BUILD
CONT
INIT
INPT
RAND
HASH
EVNT
CAMR
UIIN
MARK
CHKP
DEPS
```

## 11. Replay identity

Store:

```text
replay format version
source commit/build ID
compiler/build configuration
canonical content hash
map/BSP hash
presentation asset manifest hash
shader-package identity where relevant
```

Replay runner must clearly report incompatibility rather than silently interpreting mismatched formats/content.

## 12. Seeking/checkpoints

Large captures may store periodic:

```text
CHKP
```

state checkpoints.

Allow seeking to benchmark/debug intervals without replaying an entire long capture from the beginning.

## 13. Time domains

Maintain distinct:

```text
CanonicalTime
PresentationTime
RenderFrameId
```

Replay must not make canonical simulation timing depend on current render frame rate.

## 14. Presentation structural regression

Hash/compare stable structures such as:

```text
PresentationEvent sequence
PresentationEntity creation/destruction
RenderSnapshot semantic counts/IDs
Audio logical command sequence
UiIntent/view-model sequence where relevant
```

Do not hash raw GPU memory.

## 15. Regression classes

### Canonical

Strict semantic equality.

### PresentationStructural

Stable semantic/event equality where specified.

### Visual

Tolerance/perceptual comparison.

### Performance

Statistical latency/timing comparison.

### Resource/Lifetime

Memory/capacity/leak validation.

## 16. Canonical regression corpus

Include:

```text
movement
reaction fire
weapon fire
grenades
doors
inventory
LOS/visibility
AI turns
multi-floor tactical maps
RMA maps
mission completion
campaign transitions
research
production
aircraft
save/load
```

Extend the existing test suite rather than replacing it.

## 17. Visual regression capture

Fixed settings:

```text
fixed replay
fixed camera
fixed RenderExtent selected by the replay manifest (qualification case 1920x1080)
fixed OutputExtent for the regression case
fixed HDR or SDR mode
fixed quality configuration
fixed presentation RNG seeds
dynamic quality scaling disabled
```

Capture useful stages such as:

```text
SceneColor before output transform
display-linear final image
selected diagnostic buffers
```

Use FP16/HDR-capable captures for renderer regression where required.

## 18. Visual comparison

Do not require Vulkan pixel bit identity.

Compare:

```text
mean absolute error
percentile error
bounded max error
structural/perceptual similarity
region-specific tolerances
```

UI may additionally compare semantic:

```text
node bounds
glyph runs
clips
draw instances
```

more strictly.

## 19. Performance benchmark protocol

Starting reference protocol:

```text
warm-up:
    300 frames

measurement:
    1800 frames
```

At 60 Hz:

```text
~5 seconds warm-up
~30 seconds measurement
```

No fixed duration is architectural; benchmark scenes may override.

## 20. Performance statistics

Report:

```text
median
p90
p95
p99
maximum
deadline misses
```

For:

```text
snapshot-ready latency
render-submit latency
GPU frame
major GPU pass groups
input-to-display where available
```

Average FPS is not the primary regression metric.

## 21. Regression threshold policy

Do not permanently hard-code a universal relative percentage before measuring reference-run noise.

Threshold combines:

```text
measured statistical noise
meaningful absolute delta
meaningful relative delta
```

Starting experimental gates may use values such as:

```text
median:
    max(0.05 ms, 5%)

p99:
    max(0.10 ms, 8%)
```

but these are tuning values, not architecture invariants.

## 22. Hardware-keyed baseline identity

Performance baseline key includes:

```text
CPU model/topology
GPU device ID/UUID
driver identity/version
Mesa version
kernel
compiler/build type
shader package hashes
asset/content hash
resolution
HDR/SDR
present mode
HRTF mode
quality configuration
```

Do not compare arbitrary hardware/driver runs as if equivalent.

## 23. Resource regression

Record:

```text
peak VRAM committed/resident
allocator class peaks
transient peak
static/dynamic AS memory
texture residency
DDGI
particle buffers
CPU arenas
staging
glyph atlas
```

## 24. Lifetime regression

Generational pools/caches expose:

```text
created
destroyed
alive
peak
```

After benchmark teardown/drain, non-persistent resources should return to expected baseline counts.

Persistent global caches are explicitly tagged.

## 25. Validation configuration

Separate correctness run enables expensive diagnostics:

```text
Vulkan validation
sync validation
GPU-assisted validation when useful
OpenAL debug
allocator assertions
Frame Graph validation
authority-boundary assertions
```

Performance timings from validation runs are not accepted as benchmark data.

## 26. Output report

Regression output includes:

```text
test/replay identity
build/hardware identity
pass/fail by regression class
first canonical divergence if any
visual metrics
performance deltas
memory deltas
validation failures
trace/probe artifact references
```

## Deterministic structural presentation ordering

Architecture 058 is required for exact PresentationStructural regression.

Regression hashes the sorted structural command sequence and resulting stable identity allocation.

Unordered worker completion is never hashed as semantic presentation order.

## Deterministic stochastic presentation streams

Architecture 064 owns the counter-based stochastic RNG contract.

Presentation replay records one:

```text
uint64 presentationRandomSeed
```

and derives effect samples from stable semantic counters.

Replay correctness must not depend on worker/dispatch/wave execution order or on recording every generated random number.

## Exact production RNG streams

Architecture 068 owns production stochastic stream assignment.

Replay/settings identity includes candidate/ray-count and stream-allocation configuration.

## Extent regression coverage

Architecture 072 requires at least:

```text
qualification identity case:
    RenderExtent 1920x1080
    OutputExtent 1920x1080

scaled-output case:
    RenderExtent 1920x1080
    fixed larger OutputExtent supported by the test environment

native non-1080 case:
    RenderExtent = OutputExtent
    exact non-1080 extent recorded in the replay manifest
```

The replay/regression manifest records both extents.

Changing only OutputExtent must not change canonical or Presentation World semantics.

## Baseline 030 replay-format closure

The `.uforeplay` logical chunks and semantic regression classes remain accepted. Architecture 085 now fixes the reference-v1 chunk envelope and version/CRC/skip rules; optional compact encodings require new explicit versions.
