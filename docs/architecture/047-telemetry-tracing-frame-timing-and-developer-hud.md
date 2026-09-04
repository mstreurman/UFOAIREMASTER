# Telemetry, Tracing, Frame Timing and Developer HUD

**Status:** Implementation specification baseline  
**Related ADR:** ADR-027

## 1. Namespace

```cpp
namespace ufo::telemetry;
```

Project instrumentation macros/functions may include:

```cpp
UFO_PROFILE_SCOPE("Presentation.Animation");
UFO_TRACE_INSTANT("ActorKilled", actorId);
UFO_COUNTER("Render.VisibleInstances", visibleCount);
UFO_GPU_SCOPE(cmd, "RTReflection");
```

Macros resolve through the internal telemetry layer.

## 2. Static/interned names

Hot-path events use:

```text
static string literal
    ->
compile/startup interned NameId
```

Trace records store `NameId`, not copied strings.

Dynamic object names are metadata referenced by stable IDs.

## 3. Per-thread recorders

Each fixed engine thread gets an independent ring/chunk recorder.

Baseline threads:

```text
Main
Render
PrimaryWorker[0..5]
SmtWorker[0..4]
AudioControl
```

No global recording mutex.

## 4. CPU trace event

Conceptual compact event:

```cpp
struct TraceEvent {
    uint64_t timestampNs;

    uint32_t nameId;
    uint16_t threadId;
    uint8_t type;
    uint8_t category;

    uint64_t payload;
};
```

Architecture 085 fixes the reference-v1 trace record envelope; the in-memory semantic event fields above remain the baseline instrumentation contract.

## 5. CPU clock

Baseline trace clock:

```text
CLOCK_MONOTONIC_RAW
```

Use one monotonic nanosecond domain.

An `RDTSCP` fast path may be added only after measuring instrumentation overhead and validating stable conversion/calibration.

## 6. Trace event types

At minimum:

```text
ScopeBegin
ScopeEnd
Instant
Counter
AsyncBegin
AsyncEnd
Flow
WaitBegin
WaitEnd
Metadata
```

## 7. Job-system instrumentation

Every job may expose:

```text
submit timestamp
start timestamp
finish timestamp
lane
domain
worker
stolen/not stolen
```

Derived:

```text
queue delay
execution time
steal rate
worker utilization
barrier tail
```

## 8. Wait reasons

All material engine waits use explicit reason IDs.

Baseline:

```text
WaitJobFence
WaitRenderSnapshot
WaitFrameContext
WaitAcquireImage
WaitGraphicsTimeline
WaitTransferTimeline
WaitPresent
WaitAsset
WaitAudioResult
FutexIdle
```

Do not leave important blocking time as anonymous thread gaps.

## 9. GPU Frame Graph timestamps

Each significant pass owns:

```text
timestamp begin
timestamp end
```

from a per-FrameContext query allocation.

Results are consumed after relevant timeline completion.

Never call:

```text
vkQueueWaitIdle
```

to refresh the profiler.

## 10. GPU pass metadata

For each timed pass record:

```text
pass name
queue
FrameGraph pass ID
start/end query
duration
dispatch/draw/ray counts where meaningful
```

## 11. CPU/GPU clock correlation

When supported on the reference device, periodically capture calibrated timestamp correlation samples.

Use these to align:

```text
CPU submit
GPU start
GPU end
```

on one trace timeline.

Record maximum deviation/error metadata from the calibration mechanism.

## 12. Present timing

Native Wayland reference path should instrument the supported presentation timing data.

Track where supported:

```text
present queue timing
first-pixel/display timing
present interval
missed/late present behavior
```

Use a common FrameId/PresentId to correlate:

```text
input
canonical consumption
snapshot seal
queue submit
GPU execution
present
display
```

## 13. Input-to-display metric

Preferred headline latency timeline:

```text
input event timestamp
    ->
canonical/input consumption
    ->
RenderSnapshot seal
    ->
GPU submit
    ->
GPU completion
    ->
first pixel out
```

When true first-pixel timing is unavailable, report the reduced metric explicitly rather than presenting it as full end-to-end latency.

## 14. Vulkan object names

All significant Vulkan objects use stable debug names.

Examples:

```text
Image/GBuffer/Depth
Image/Reflection/History0
Buffer/GpuMaterial
Buffer/ParticleStateA
BLAS/Map/Hospital/L2/Opaque/3
BLAS/Actor/Ortnok/Frame1
TLAS/Frame0
Pipeline/RT/Reflection
Pipeline/Compute/ReflectionAtrous2
```

## 15. Vulkan command labels

Frame Graph pass labels match internal profiling names where practical.

External GPU tools should display the same semantic pass structure as the engine HUD/trace.

## 16. Counters

Basic counters include:

```text
visible instances
lights
RT rays by effect
BLAS/TLAS build counts
particle counts
decals
volumetric emitters
allocator bytes
descriptor usage
audio voices
UI nodes/draws
asset upload bytes
```

## 17. Rolling history

Developer HUD keeps approximately:

```text
1024 frames
```

of reduced telemetry.

Detailed trace capture uses a bounded rolling event buffer sized in bytes/time rather than unbounded frame history.

## 18. Developer HUD pages

### Frame

```text
CPU frame
snapshot-ready
render-submit
GPU frame
present latency
deadline misses
```

### CPU

```text
canonical
mirror
animation
Jolt
snapshot
UI
jobs
steals
waits
```

### GPU

```text
Frame Graph pass times
ray counts
BLAS/TLAS
particles
volumetrics
```

### Memory

```text
VRAM budget
allocated/resident
allocator classes
fragmentation
AS
transient peak
```

### Assets

```text
read/decode/upload
queue age
bytes/s
```

### Audio

```text
logical/physical/virtual voices
HRTF
occlusion
stream underruns
```

### UI

```text
node count
dirty count
shape cache
glyph atlas
draw count
```

### VFX

```text
particles
sort count
decals
volumes
VFX lights
Jolt debris
```

### RT

```text
effect ray counts
history acceptance
ReSTIR stats
DDGI stats
probe/visualizer state
```

## 19. HUD update rate

Underlying counters collect at native rate.

Heavy developer text/graph presentation may update at:

```text
4–10 Hz
```

to avoid making the profiler UI itself a notable workload.

## 20. Capture-on-spike

Maintain rolling Trace history and allow automatic freeze/export on triggers.

Starting capture window:

```text
240 frames before
trigger frame
120 frames after
```

Potential triggers:

```text
CPU frame > threshold
GPU frame > threshold
input/display latency > threshold
allocator critical pressure
validation error
stream underrun
manual developer trigger
```

## 21. Instrumentation overhead targets

Engineering targets, not measured facts:

```text
Basic:
    zero general heap allocation/frame
    <= 0.10 ms aggregate CPU overhead target

Trace active:
    <= ~2% CPU perturbation target at normal trace density
```

Measure and report instrumentation overhead as a regression target itself.

## Target extent and allocator telemetry

Baseline 026 telemetry records:

```text
RenderExtent
OutputExtent
UiRasterExtent

allocator committed bytes by pool
allocator live bytes by pool
allocator retained/cached bytes by pool
per-pool committed/live high-water
texture evictable/pending-retirement bytes
```

This is required for architecture 072/074 target-hardware optimization decisions.

## Baseline 030 trace-format closure

The semantic trace event model remains accepted. Architecture 085 fixes reference-v1 persistent trace packing; ADR-040/architecture 086 require local-only crash diagnostics with no automatic network telemetry.
