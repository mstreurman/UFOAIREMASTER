# ADR-027 — Instrumentation, Profiling, Replay, Regression and RT Inspection

**Status:** Accepted  
**Decision type:** Observability / replay / regression architecture  
**Primary target:** Fedora 44 / i9-9900K / Intel Arc B580  
**Related:** ADR-001, ADR-015, ADR-020, ADR-021, ADR-023, ADR-026

## Context

The remaster has multiple high-complexity presentation systems:

```text
custom job system
Vulkan Frame Graph
hardware RT
ReSTIR DI
DDGI
reflection reconstruction
custom GPU allocator
GPU particles
OpenAL Soft
retained UI
Jolt presentation physics
```

Without first-class observability, correctness/performance failures become difficult to reproduce and diagnose.

The project also needs a strong regression system to enforce the defining promise:

```text
canonical gameplay remains unchanged
```

## Decision

Build one shared instrumentation foundation that feeds four major uses:

```text
live developer telemetry
structured trace capture
deterministic replay
automated regression
```

RT-specific visualization and exact-pixel inspection are part of the same instrumentation architecture.

## Instrumentation abstraction

Engine code targets:

```text
ufo::telemetry
```

not a third-party profiler API.

Optional backends/tools may include external profilers/export formats, but engine source instrumentation remains owned by the project.

## Instrumentation levels

```text
Off
Basic
Trace
Deep
```

### Off

Instrumentation compiled out or reduced to negligible required production counters.

### Basic

Used for benchmark/regression runs:

```text
frame timings
subsystem timings
GPU pass timestamps
memory/capacity counters
present timing
```

### Trace

Adds:

```text
CPU scopes
job submit/start/finish
queue waits
async spans
asset/audio/VFX/UI events
```

### Deep

Adds expensive diagnostics:

```text
validation
fine-grained allocation/lifetime events
RT probe shader variants
deep GPU/CPU counters where supported
```

Performance regressions are measured in `Basic`, not `Trace` or `Deep`.

## Hot-path rule

Instrumentation must not require a global mutex or general heap allocation in normal hot paths.

Use per-thread buffers and static/interned event names.

## Profiling

Profile:

```text
Main
Render
Primary workers
SMT workers
AudioControl
GPU Frame Graph passes
transfer queue
present timing
```

Every significant job/barrier/wait reason is observable.

## GPU timing

Every significant Frame Graph pass receives GPU begin/end timestamp instrumentation.

Timestamp query results are consumed asynchronously after the owning FrameContext completes.

Do not block the GPU merely to display current profiling numbers.

## CPU/GPU timeline correlation

Use calibrated timestamp support on the reference B580 where available to correlate:

```text
CPU Main
CPU Render
GPU graphics/RT
GPU transfer
presentation timing
```

onto a common diagnostic timeline.

## Replay split

Implement two independent replay layers:

```text
CanonicalReplay
PresentationReplay
```

and allow a combined `FullReplay`.

### CanonicalReplay

Replays authoritative inputs/state and validates stable semantic canonical hashes.

### PresentationReplay

Replays typed PresentationEvents/presentation actions directly into the remaster presentation stack.

This permits repeatable rendering/audio/UI/VFX benchmarking without rerunning authoritative game logic.

## Regression split

Automated regression has five independent classes:

```text
Canonical
PresentationStructural
Visual
Performance
Resource/Lifetime
```

Canonical regression is strict.

Visual GPU regression is tolerance/perceptual rather than requiring pixel bit identity.

## RT diagnostic tooling

Provide:

```text
RT Visualizer
Render Probe
```

### RT Visualizer

Whole-frame debug representations of RT activity/influence/internal state.

### Render Probe

A developer `+` crosshair selects one exact pixel/world point and captures detailed raster/material/RT/reconstruction information asynchronously.

## RT isolation invariant

Provide a named false-color mode:

```text
RT Isolation
```

where:

```text
NON-RT = pure RED
```

Normal beauty/raster appearance is intentionally hidden.

Only the selected RT information replaces red.

At minimum distinguish:

```text
Current-Ray Activity
Resolved RT Influence
RT Contribution Strength
```

because a temporally reconstructed RT result may influence a pixel even when no fresh ray was launched for that pixel this frame.

## Authority

Instrumentation/replay/debug data never changes canonical game outcomes.

Replay is allowed to inspect/validate canonical state, not alter its semantics.

## Consequences

- performance investigations become repeatable;
- canonical behavior can be guarded by exact semantic hashes;
- B580 renderer experiments use identical presentation workloads;
- intermittent spikes can preserve preceding trace history;
- RT bugs can be investigated at the exact pixel/ray/material level;
- external tools remain optional rather than architectural dependencies.

## Baseline 030 persistence/privacy closure

Architecture 085 fixes reference-v1 trace/replay/probe packing. ADR-040/architecture 086 fix local-only crash diagnostics and prohibit automatic network telemetry in v1. Instrumentation remains non-authoritative.
