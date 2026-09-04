# Exact B580 GPU Memory Allocator

**Status:** Implementation specification baseline  
**Related ADR:** ADR-022  
**Primary GPU:** Intel Arc B580 / Mesa ANV

## 1. Purpose

Provide explicit allocation for:

```text
images
BDA buffers
descriptor heaps
static/dynamic BLAS
TLAS
AS scratch
upload staging
readback
frame-transient resources
```

while respecting the current Vulkan memory budget.

## 2. No VMA dependency

The allocator is renderer-owned.

Reasons:

```text
known B580 target topology
BDA stability requirements
descriptor-heap mapped VRAM
AS-specific pools
project-owned residency priority classes
FrameContext arenas
detailed telemetry
```

This is a target-specific engineering choice, not a claim that VMA is unsuitable generally.

## 3. Allocation architecture

Two fundamental algorithms:

```text
long-lived:
    segregated free-list / best-fit suballocator

frame/transient:
    linear bump arena
```

No per-resource `vkAllocateMemory` except required/selected dedicated allocations.

## 4. Baseline pools and lazy growth block sizes

### Persistent device-local buffers

```text
block size:
    128 MiB

algorithm:
    segregated free list
```

Used by:

```text
mesh streams
GPU scene arrays
material buffers
persistent BDA data
```

### Persistent device-local images

```text
block size:
    256 MiB

algorithm:
    segregated free list
```

Used by:

```text
resident textures
persistent histories
DDGI atlases
long-lived render images
```

### Static AS storage

```text
block size:
    256 MiB

algorithm:
    segregated free list

priority class:
    high
```

### Dynamic AS storage

```text
block size:
    128 MiB

algorithm:
    segregated free list / FrameContext-owned slots
```

### Mapped device-local dynamic

```text
block size:
    64 MiB

memory:
    DEVICE_LOCAL
    HOST_VISIBLE
    HOST_COHERENT

algorithm:
    frame-linear / region suballocation
```

Candidates:

```text
descriptor heaps
frame constants
TLAS input instances
small dynamic scene tables
bone palettes if benchmarked favorable
```

### Frame-transient device local

```text
256 MiB per FrameContext starting reserve
linear
```

### AS scratch

```text
128 MiB per FrameContext starting reserve
linear
64-byte minimum alignment on reference B580
```

### Upload staging

```text
128 MiB per FrameContext starting reserve
HOST_VISIBLE
HOST_COHERENT
HOST_CACHED
ring/linear
```

### Readback

```text
16 MiB per FrameContext starting reserve
HOST_VISIBLE
HOST_COHERENT
HOST_CACHED
ring/linear
```

These are initial growth units/reserves, not hard memory caps.

## 5. Pool growth

Persistent pool:

```text
find compatible block
    |
    +-- allocation found -> suballocate
    |
    +-- no fit -> create next block
```

Later blocks normally retain the pool's starting block size unless a single large resource requires more.

For a resource larger than one normal block:

```text
dedicated or oversized block
```

rather than fragmenting multiple unrelated blocks.

## 6. Free-list details

Long-lived suballocation tracks:

```text
offset
size
alignment
free/occupied
memory type
priority class
device-address capability
```

Free adjacent ranges coalesce immediately.

Prefer best-fit within size classes to reduce fragmentation.

Exact bin thresholds remain implementation detail.

## 7. BDA memory rule

Any Vulkan memory allocation backing buffers whose addresses will be queried uses:

```text
VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT
```

Buffers use:

```text
VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT
```

where their ABI requires BDA.

Do not request BDA flags for unrelated image-only blocks.

## 8. Stable-address rule

BDA-backed buffers do not participate in transparent live defragmentation.

Moving a resource changes its GPU address.

Therefore:

```text
no hidden allocator relocation
```

A BDA resource may move only through an explicit resource migration operation that updates all owning references after GPU completion.

## 9. Descriptor-heap memory

The sampler/resource heap buffers prefer the reference B580 memory type:

```text
DEVICE_LOCAL
HOST_VISIBLE
HOST_COHERENT
```

and remain persistently mapped.

Heap buffer base addresses obey the B580 64-byte sampler/resource heap alignment. Individual slots obey architecture 089's typed descriptor alignment/stride rules (32-byte samplers; 64-byte ordinary image/buffer resource slots on the reference GPU).

Descriptor-heap allocations are separate from generic BDA pools for telemetry/lifetime clarity.

## 10. Memory budget

`VK_EXT_memory_budget` is mandatory for the B580 allocator.

Periodically read:

```text
heapBudget
heapUsage
```

for the device-local heap.

Use current budget, never installed-VRAM size, as the pressure denominator.

## 11. Pressure bands

Starting policy:

```text
usage < 70% budget:
    Normal

70% <= usage < 82%:
    Constrained
    stop aggressive prefetch

82% <= usage < 90%:
    High
    evict whole unreferenced texture assets after safe retirement
    trim safely retired transient/staging/readback cache blocks
    defer low-value residency
    stop speculative prefetch

usage >= 90%:
    Critical
    suspend optional uploads
    evict lowest-priority unreferenced whole assets
    trim safely retired allocator cache blocks
    emit visible developer telemetry
```

Hysteresis should prevent state flapping.

Exact exit thresholds remain implementation constants.

## 12. Project-owned residency priority

The Mesa 26.2.2 B580 device does **not** expose `VK_EXT_memory_priority`. Do not add `VkMemoryPriorityAllocateInfoEXT` or require that extension on the reference target.

The allocator still maintains logical priority classes because they drive **our own** streaming, prefetch, eviction and reclamation decisions.

Starting logical priorities:

```text
1.00:
    active depth/G-buffer/HDR targets
    active descriptor backing storage
    current TLAS/dynamic BLAS

0.90:
    static map BLAS
    core map geometry
    current critical scene data

0.75:
    normal resident meshes/textures

0.50:
    stream cache / lower-value residency

0.25:
    speculative prefetch / disposable cached mips
```

These values are renderer policy only. They are not passed to Vulkan as memory-priority values on B580/ANV 26.2.2.

## 13. Device-local pressure without pageable-local-memory

The Mesa 26.2.2 B580 device does **not** expose `VK_EXT_pageable_device_local_memory`.

Therefore the renderer must not rely on transparent driver paging as a correctness or capacity mechanism. It:

```text
queries VK_EXT_memory_budget
keeps critical allocations inside the device-local budget target
uses project-owned residency/eviction policy for discardable assets
suspends/degrades optional uploads under pressure
ever treats host-visible/system memory as an implicit transparent overflow promise
```

If a future B580 driver exposes pageable device-local memory, it may be evaluated as an optional optimization; the baseline allocator remains correct without it.

## 14. Dedicated allocations

Query:

```text
VkMemoryDedicatedRequirements
```

through resource memory requirements.

Use dedicated allocation when:

```text
requiresDedicatedAllocation = true
```

Strongly consider dedicated allocation when:

```text
prefersDedicatedAllocation = true
```

or a resource is larger than approximately half its normal pool block size.

This threshold is tunable.

## 15. Image/buffer separation

Images and generic persistent buffers do not share ordinary allocator blocks.

Reasons:

```text
different usage patterns
different memory requirements
clearer priority groups
simpler fragmentation diagnostics
```

Memory types that are buffer-only are used only for compatible pools.

## 16. Upload path

Large assets:

```text
disk/page cache
    ->
host-cached staging
    ->
family-2 transfer queue
    ->
device-local destination
    ->
ReadyToken
```

Small dynamic data may write directly to mapped device-local coherent memory.

## 17. Frame reset

A FrameContext's linear arenas reset only after all recorded queue completion values for that context have completed.

No transient offset reuse before GPU completion.

## 18. Deferred destruction

Every destruction becomes a retirement record:

```cpp
struct RetiredAllocation {
    Allocation allocation;

    uint64_t graphicsDone;
    uint64_t transferDone;
    uint64_t computeDone;
};
```

An allocation returns to its pool only when every relevant queue timeline has reached the recorded value.

## 19. Allocation handle

Conceptual renderer-facing handle:

```cpp
struct GpuAllocation {
    uint32_t blockId;
    uint32_t memoryTypeIndex;

    VkDeviceSize offset;
    VkDeviceSize size;

    void* mapped;
    VkDeviceAddress baseAddress;

    uint32_t flags;
};
```

Exact public encapsulation may hide Vulkan details further.

## 20. Telemetry

Track per pool:

```text
reserved bytes
used bytes
free bytes
largest free range
internal fragmentation
allocation count
block count
peak used
dedicated allocation bytes
priority class
```

Track heap:

```text
budget
driver-reported usage
allocator-owned usage
pressure state
```

## 21. Failure policy

Allocation failure:

```text
1. refresh memory budget
2. trim explicitly disposable cache if allowed
3. retry once where appropriate
4. report exact pool/resource failure
```

Do not silently drop required geometry, RT structures or G-buffer resources.

Presentation failure must not alter canonical game state.

## Lazy commitment authority

Architecture 074 is the exact commitment/residency authority.

The block sizes in this document are:

```text
first/growth allocation units
```

not an instruction to eagerly allocate every pool and every FrameContext arena at renderer startup.

Unused logical pools commit zero backing `VkDeviceMemory` unless a specifically documented bootstrap resource requires memory.

Frame/transient/scratch/upload/readback storage grows on first demand and may retain safely retired blocks for reuse subject to pressure trimming.

## Baseline texture-pressure restriction

A live published persistent sampled-image heap content texture is not mip-stripped or view-rewritten by memory pressure.

Pressure behavior follows architecture 074:

```text
whole unreferenced asset eviction
prefetch reduction
optional upload deferral
safe allocator-cache trimming
```

True partial/sparse mip residency requires a later explicit architecture contract.
