# CPU Ownership, Determinism, Budgets and i9-9900K Benchmarks

**Status:** Architecture baseline  
**Related ADR:** ADR-023

## 1. Ownership table

| Data/system | Baseline writer |
|---|---|
| Canonical simulation | Main |
| Tactical Client Mirror | Main |
| Presentation World structure | Main |
| Animation frame ranges | Assigned workers |
| Skeleton/pose frame ranges | Assigned workers |
| Jolt world | Jolt phase/domain |
| RenderSnapshot ranges | Assigned workers, then sealed |
| AudioStateSnapshot preparation | Assigned workers/Main, then latest-wins publication |
| AudioCommandQueue | Main producer -> AudioControl consumer, ordered SPSC |
| Vulkan Frame Graph | Render |
| Descriptor-heap publication/writes | Render |
| Vulkan queue submissions | Render |
| GPU allocator mutation | Render |
| Background asset decode scratch | Background workers |
| OpenAL/ALC/EFX runtime objects | AudioControl |

This ownership model is preferred over broad mutex protection.

## 2. Canonical determinism

Scheduler/job completion order has no authority over:

```text
game rules
AI
damage
movement
inventory
routing
LOS
campaign/tactical outcomes
```

Canonical simulation remains ordered according to its existing game architecture.

## 3. Presentation reproducibility

Presentation output should remain reproducible where practical.

Use:

```text
stable entity/render IDs
fixed output ranges
stable sorting keys
frame/event-based random seeds
```

Avoid:

```text
worker-completion-order output
unordered visible atomic append
thread-index random seeds
```

## 4. Snapshot determinism

Important arrays use:

```text
partition
count
prefix sum
exclusive fill
```

or deterministic preassigned ranges.

If a system intentionally uses unordered processing because order has no semantic/render consequence, document it.

## 5. Provisional CPU budget gates

These are targets for profiling, not measured results.

### Main/presentation path

```text
canonical + mirror:
    <= 1.5 ms target

animation + pose:
    <= 1.0 ms target

Jolt:
    <= 1.0 ms normal-scene target

presentation finalization + snapshots:
    <= 1.0 ms target

snapshot ready:
    <= ~4.5 ms after CPU frame start
```

### Render thread

```text
snapshot consumption
GPU data population
Frame Graph compile
command record
submit

target:
    <= 2.0 ms
```

### Warning gate

CPU submission later than approximately:

```text
8 ms after frame start
```

is a provisional warning condition.

The hard display frame deadline remains:

```text
16.667 ms
```

## 6. Benchmark scenes

CPU benchmark suite should include:

```text
empty/simple tactical map
32 actors active
64 actors stress
animation-heavy squad
ragdoll-heavy scene
large RMA map
many lights/VFX
large asset streaming burst
cutaway/floor switching
door/breakable events
campaign/geoscape presentation
```

## 7. Scheduler mode matrix

Benchmark:

```text
A:
    6 Primary workers only

B:
    6 Primary + 5 scheduler SMT helpers for SmtFriendly/Background
    AudioControl remains on the reserved sixth worker-core SMT sibling

C:
    SMT permitted for Jolt

D:
    SMT permitted for animation
```

Production defaults remain:

```text
animation -> PrimaryOnly
Jolt      -> PrimaryOnly
small presentation jobs -> SmtFriendly
background -> SMT-preferred
```

until measurements justify a change.

## 8. Worker-count matrix

Also benchmark reduced primary worker counts:

```text
4
5
6
```

to detect whether reserving more physical-core headroom for OS/OpenAL/driver behavior improves total frame consistency.

Do not assume maximum worker count always minimizes frame time.

## 9. Affinity benchmark

Compare:

```text
fixed baseline affinity
Linux unrestricted migration
alternative physical core choice for Main/Render
```

Track:

```text
median frame CPU time
95th percentile
99th percentile
context switches
migrations
cache-related performance counters where tooling permits
```

Baseline remains explicit affinity unless measurements show a better stable policy.

## 10. Job granularity benchmark

Histogram:

```text
< 5 us
5–20 us
20–50 us
50–100 us
100–200 us
200–500 us
> 500 us
```

Goal:

```text
most important parallel work ~20–200 us
```

Large tails indicate poor partitioning.

A flood of sub-5-us jobs indicates scheduler overhead waste.

## 11. AVX2 benchmark policy

For each hand/vectorized kernel compare:

```text
compiler baseline
auto-vectorized native build
explicit AVX2/FMA implementation
```

Measure:

```text
single-worker throughput
six-worker scaling
six-worker + SMT interference
```

Retain specialized code only for measured target gains.

## 12. Jolt benchmark matrix

Measure:

```text
1, 2 collision steps
4, 5, 6 Primary workers
SMT off/on
```

scenes:

```text
no dynamic bodies
normal debris
many rigid pieces
multiple ragdolls
worst expected visual physics stress
```

Production baseline remains:

```text
60 Hz
1 collision step
6 Primary workers + Main
SMT off
```

until measured otherwise.

## 13. Render command recording benchmark

Baseline:

```text
Render thread records all Vulkan commands
```

Only consider worker/secondary-command-buffer recording if Render-thread profiling shows meaningful CPU pressure.

A change must improve total CPU submission latency, not only command-record microbenchmarks.

## 14. Background work throttling

Track:

```text
frame-critical queue non-empty duration
background jobs executed on physical workers
SMT background utilization
asset decode backlog
```

Under sustained CPU pressure:

```text
throttle/defer background work
```

before violating current-frame deadlines.

## 15. Linux scheduling assumptions

Baseline:

```text
normal SCHED_OTHER
explicit affinity
no realtime priority
no root requirement
```

Do not make performance depend on privileged scheduler configuration.

## 16. Power/frequency telemetry

When benchmarking, record if practical:

```text
CPU frequency
thermal throttling state
package temperature
background system load
```

because 9900K turbo behavior can materially affect short benchmark runs.

Benchmark acceptance should use sustained runs, not only warm-up bursts.

## 17. Acceptance rule

A scheduler optimization is accepted only if it improves one or more of:

```text
median frame CPU time
95th/99th percentile
snapshot-ready latency
render-submit latency
background throughput without frame regression
```

without:

```text
canonical behavior change
new race/deadlock risk
presentation nondeterminism that harms debugging
unacceptable input-latency increase
```

## Budget-accounting authority

Architecture 055 defines parent/child/concurrent accounting.

The `snapshot ready <= ~4.5 ms` target is the parent Main/presentation gate; UI/audio preparation subtargets inside publication are attribution, not extra time blindly added on top.

## Compiler/link target-build gate

Architecture 073 requires the i9-9900K target build to benchmark:

```text
normal optimized
-O3
LTO/IPO
LTO/IPO + PGO
```

with canonical/presentation regression and sustained frame p95/p99.

`-march=native -mtune=native` remains target baseline; global fast-math remains prohibited.
