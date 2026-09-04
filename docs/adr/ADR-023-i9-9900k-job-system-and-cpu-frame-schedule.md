# ADR-023 — i9-9900K Job System and CPU Frame Schedule

**Status:** Accepted  
**Decision type:** CPU scheduling / frame execution architecture  
**Primary CPU:** Intel Core i9-9900K, 8C/16T  
**Primary platform:** Fedora 44 Linux  
**Related:** ADR-001, ADR-006, ADR-007, ADR-011, ADR-012

## Context

The remaster must use the i9-9900K effectively while preserving:

```text
canonical gameplay ordering
Presentation World isolation
Jolt non-authority
low input latency
deterministic presentation outputs where practical
a 16.667 ms frame deadline
```

The CPU has eight physical cores with SMT.

SMT siblings share core execution resources and are not treated as sixteen independent physical cores.

## Decision

Use a fixed OS-thread scheduler designed around physical-core-first execution.

The engine owns:

```text
1 Main thread
1 Render thread
6 Primary worker threads
5 optional SMT helper threads
1 AudioControl thread on a worker-core SMT sibling
```

The SMT siblings of Main and Render are left unused by the engine in the baseline.

ADR-024 reserves one worker-core SMT sibling for AudioControl; the other five worker-core siblings remain scheduler SMT helpers.

Normal frame-critical execution is designed to succeed using:

```text
Main
Render
6 Primary workers
```

only.

SMT helpers provide optional throughput for suitable presentation/background work.

## Topology discovery

Never assume Linux logical CPU numbering.

Discover topology using Linux CPU topology information and construct eight physical-core sibling groups.

Affinity is applied explicitly using normal pthread/Linux affinity mechanisms.

Baseline uses ordinary Linux scheduling:

```text
SCHED_OTHER
```

No realtime/root-required scheduling policy is required.

## Reserved physical roles

After topology discovery:

```text
one physical core -> Main
one physical core -> Render
six physical cores -> Primary workers
```

Prefer not to place Main/Render on the physical core most burdened by Linux housekeeping when a stable better choice can be determined.

Exact logical CPU IDs remain runtime-discovered.

## Job lanes

Three scheduling lanes are accepted:

```text
PrimaryOnly
SmtFriendly
Background
```

### PrimaryOnly

For critical/heavy work such as:

```text
AVX2 animation sampling
skeleton hierarchy
Jolt
large presentation transforms
critical visibility/instance preparation
```

### SmtFriendly

For smaller/latency-bound work:

```text
packing
audio preparation
VFX bookkeeping
light preparation
small independent transforms
```

### Background

For work that may drift:

```text
asset decompression
streaming preparation
shader hot-reload bookkeeping
debug export
cache maintenance
```

Background work must not starve frame-critical work.

## No fibers

The scheduler uses ordinary fixed OS threads and run-to-completion jobs.

No fiber/coroutine job scheduler is an architectural dependency.

## Jolt integration

Implement a custom adapter based on:

```text
JPH::JobSystemWithBarrier
```

Jolt update uses:

```text
Main thread
+
6 Primary workers
```

for effective maximum concurrency:

```text
7
```

SMT helpers are parked during baseline Jolt update.

Jolt runs at:

```text
60 Hz fixed timestep
1 collision step
maximum 2 catch-up steps
```

If presentation physics falls far behind, excess presentation backlog is discarded rather than changing canonical game timing.

## Canonical ownership

Canonical simulation and ordered tactical event decode remain Main-thread-owned.

Worker scheduling completion order must never affect canonical outcomes.

## Render ownership

The Render thread owns baseline Vulkan runtime mutation:

```text
Frame Graph
descriptor-heap publication writes
GPU allocator mutation
command recording
queue submission
present
```

Workers do not record Vulkan command buffers initially.

## Snapshot boundary

Main/workers produce/publish the one-way presentation products:

```text
RenderSnapshot
AudioStateSnapshot
ordered AudioCommandQueue entries
```

after presentation finalization.

`AudioStateSnapshot` is continuous/latest-wins; `AudioCommandQueue` preserves discrete command ordering according to ADR-024.

The render snapshot queue has at most one pending snapshot.

Do not allow CPU simulation to run many frames ahead and increase input latency.

## Consequences

- physical cores carry the 60 FPS critical path;
- SMT provides optional spare throughput;
- canonical game logic stays straightforward;
- Vulkan ownership remains simple;
- Jolt integrates without fiber-specific complexity;
- frame scheduling is measurable and reproducible on the target CPU.
