# Exact i9-9900K Job System API and Topology

**Status:** Implementation specification baseline  
**Related ADR:** ADR-023  
**Primary CPU:** Intel Core i9-9900K

## 1. Runtime CPU topology

At startup enumerate online CPUs and read Linux topology.

For each logical CPU determine:

```text
core_id
physical_package_id
thread_siblings_list
online state
```

Construct:

```cpp
struct LogicalCpu {
    uint32_t osCpu;
    uint32_t packageId;
    uint32_t coreId;
};

struct PhysicalCore {
    LogicalCpu primary;
    LogicalCpu sibling;
};
```

The i9-9900K target must resolve to:

```text
8 physical cores
2 logical CPUs/core
```

If the target topology is not present, log the actual topology and either use a diagnostic fallback scheduler or reject the B580/9900K optimized runtime according to build policy.

## 2. Logical CPU numbering

Never assume:

```text
0 pairs with 8
1 pairs with 9
...
```

Use discovered sibling relationships.

## 3. Baseline role assignment

Assign eight physical cores:

```text
MainCore
RenderCore
WorkerCore[0..5]
```

Each has:

```text
primary logical CPU
SMT sibling
```

Engine thread policy:

```text
MainCore.primary      -> Main
MainCore.sibling      -> unused by engine

RenderCore.primary    -> Render
RenderCore.sibling    -> unused by engine

WorkerCore[i].primary -> PrimaryWorker[i]

five selected worker siblings:
    SmtWorker[0..4]

one selected worker sibling:
    AudioControl
```

The exact worker sibling assigned to AudioControl is topology/runtime policy and is benchmarked.

The exact choice/order of physical cores is topology/runtime policy.

## 4. Affinity

Each engine-owned fixed thread receives affinity to exactly one logical CPU in the baseline.

Do not migrate Main/Render/worker threads during normal gameplay.

Affinity failures are logged precisely.

No realtime scheduling policy is required.

## 5. Scheduler lanes

```cpp
enum class JobLane : uint8_t {
    PrimaryOnly,
    SmtFriendly,
    Background
};
```

Eligibility:

```text
PrimaryOnly:
    Main helper
    PrimaryWorker[0..5]

SmtFriendly:
    PrimaryWorker[0..5]
    SmtWorker[0..4]
    Main helper only while explicitly waiting

Background:
    prefer SmtWorker[0..4]
    PrimaryWorker only when no frame-critical work exists
```

Render thread does not execute ordinary worker jobs in the baseline.

## 6. Job domains

```cpp
enum class JobDomain : uint8_t {
    Frame,
    Jolt,
    Background
};
```

### Frame

Current-frame presentation work.

### Jolt

Jobs spawned/consumed while Jolt barrier execution is active.

### Background

Streaming/decompression/debug work.

Jolt-domain waits do not execute arbitrary Frame/Background jobs that may touch physics-owned state.

## 7. Public scheduler API

Baseline API:

```cpp
namespace ufo::jobs {

struct JobFence;

using JobFunction = void(*)(void* user);

struct JobDesc {
    JobFunction function;
    void* user;

    JobLane lane;
    JobDomain domain;

    uint32_t debugNameId;
};

JobFence submit(const JobDesc& job);

JobFence parallelFor(
    uint32_t count,
    uint32_t grain,
    JobLane lane,
    JobDomain domain,
    void (*fn)(uint32_t begin, uint32_t end, void* user),
    void* user);

void wait(JobFence& fence);

void beginFrame(CpuFrameContext& frame);
void endFrame(CpuFrameContext& frame);

}
```

Implementation may add internal batch APIs without widening ordinary subsystem coupling.

## 8. Job object

Starting target:

```cpp
struct alignas(64) Job {
    JobFunction function;
    void* user;

    JobFence* completion;

    uint32_t debugNameId;
    uint16_t domain;
    uint8_t lane;
    uint8_t flags;

    uint8_t schedulerPrivate[32];
};

static_assert(sizeof(Job) == 64);
```

Exact private bytes may change while preserving one-cache-line target.

## 9. Frame job allocation

Current-frame jobs allocate from `CpuFrameContext`.

No general heap allocation on ordinary job submission.

Starting capacities:

```text
4096 frame jobs
8192 background job records
```

Overflow policy:

```text
development:
    assert/log exact producer and count

release:
    grow only through an explicitly allocated overflow block
```

Frequent overflow means job granularity/configuration is wrong.

## 10. Worker queues

Each Primary/SMT worker owns a work-stealing deque.

Baseline semantics:

```text
owner:
    push/pop local end

thief:
    steal opposite/oldest end
```

Use a Chase-Lev-style bounded/growable deque or equivalent proven work-stealing design.

Global injection queues exist for jobs submitted from non-worker threads.

Avoid one global mutex queue as the primary scheduler.

## 11. Priority between queues

Worker selection order:

### Primary worker

```text
1. local Frame PrimaryOnly/SmtFriendly
2. injected Frame work
3. steal eligible Frame work
4. eligible Jolt when Jolt domain active
5. Background only if critical queues empty
```

### SMT worker

```text
1. SmtFriendly frame work
2. Background
3. compatible stealing
```

During Jolt baseline:

```text
SMT workers park
```

## 12. Wait behavior

`wait(fence)`:

```text
while incomplete:
    execute compatible jobs
    steal compatible jobs
    if no work:
        short PAUSE loop
        futex sleep
```

Starting active wait:

```text
64 × _mm_pause()
```

then sleep.

No long spin loops.

## 13. Fence

Conceptual:

```cpp
struct alignas(64) JobFence {
    std::atomic<uint32_t> remaining;
    std::atomic<uint32_t> epoch;

    uint32_t futexWord;
    uint8_t padding[...];
};
```

Exact implementation may merge `epoch/futexWord`.

Required properties:

```text
zero heap allocation
multi-job completion
safe worker helping
futex sleep/wake
no lost wake
```

## 14. Job granularity

Starting target:

```text
20–200 microseconds useful work/job
```

Review jobs consistently above:

```text
250–500 microseconds
```

for splitting.

Combine jobs consistently below several microseconds.

These are profiling gates, not ABI constants.

## 15. SIMD policy and lanes

Jobs using aggressive AVX2/FMA loops should default to:

```text
PrimaryOnly
```

Examples:

```text
animation sampling
pose/hierarchy batches
matrix batches
bulk skin preparation
```

This avoids depending on SMT siblings for two heavy vector loops competing on one physical core.

## 16. Cache/data ownership

Prefer range partitioning:

```text
worker writes contiguous exclusive ranges
```

Avoid:

```text
fine-grained shared atomics
false-shared counters
random cross-worker writes
```

Hot worker-owned scheduler state is cache-line separated.

## 17. Randomness

Presentation stochastic work must derive seeds from stable inputs such as:

```text
frame index
stable render/presentation object ID
effect/event ID
sample index
```

Never derive visible randomness from:

```text
worker index
job execution order
completion order
```

## 18. Scheduler telemetry

Record:

```text
jobs submitted by lane/domain
jobs executed per worker
steals attempted/succeeded
futex sleeps/wakes
wait-help time
queue depth peaks
job duration histogram
SMT contribution
frame-critical idle time
```

Debug display should show physical-core role mapping and discovered sibling pairs.
