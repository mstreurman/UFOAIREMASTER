# GPU Memory, Queues, Frame Context and Pipeline Persistence

**Status:** Architecture baseline  
**Related ADR:** ADR-015

## 1. Reference memory heaps

The reference B580 exposes two heaps.

### Heap 0 — device local

Approximately:

```text
11.93 GiB physical
8.38 GiB current Vulkan budget in the captured dump
```

The current budget is dynamic and must be queried through `VK_EXT_memory_budget`.

### Heap 1 — host/system

Approximately:

```text
23.36 GiB physical
21.02 GiB budget in the captured dump
```

## 2. Relevant memory classes

Reference memory types include:

### Device-local only

Use for:

```text
static map geometry
textures
persistent GPU scene
BLAS/TLAS storage
large long-lived images
```

### Device-local + host-visible + host-coherent

Use selectively for:

```text
descriptor heaps
small dynamic constants
small scene-table updates
possibly bone palettes
```

This is a B580-specific fast path and should still be benchmarked against staging for larger transfers.

### Host-visible + host-coherent + host-cached

Use for:

```text
staging
readback
CPU-visible telemetry
large upload source buffers
```

## 3. Allocator classes

The renderer owns a centralized allocator with logical pools:

```text
PersistentDeviceLocal
MappedDeviceLocal
UploadStaging
Readback
FrameTransient
AccelerationStructureStorage
AccelerationStructureScratch
```

Avoid `vkAllocateMemory` at fine object granularity.

## 4. Memory-budget policy

The asset/streaming system reads current budget and usage.

Budget thresholds should trigger:

```text
streaming pressure reduction
texture residency reduction
deferred uploads
transient-budget reduction
diagnostic telemetry
```

The renderer does not assume all 12 GiB is always available.

Exact high/critical watermark percentages remain tunable.

## 5. Upload paths

### Small/direct dynamic path

```text
CPU
  |
mapped device-local coherent memory
  |
GPU reads directly
```

Candidates:

- descriptor heaps;
- frame constants;
- small scene roots;
- compact bone-palette updates.

### Large staged path

```text
CPU
  |
host-cached staging
  |
dedicated transfer queue
  |
device-local destination
```

Candidates:

- textures;
- static meshes;
- map tile geometry;
- large streaming assets.

## 6. Queue families

Reference B580:

```text
family 0:
    GRAPHICS | COMPUTE | TRANSFER | SPARSE
    count 1
    present supported

family 1:
    COMPUTE | TRANSFER | SPARSE
    count 1
    present supported

family 2:
    TRANSFER
    count 1
    present supported
```

All expose 64 timestamp bits.

## 7. Queue assignment

Baseline:

```text
GraphicsQueue = family 0
TransferQueue = family 2
```

Reserved benchmark path:

```text
AsyncComputeQueue = family 1
```

The renderer must function with no async-compute overlap.

## 8. Queue ownership

Large asset uploads use the transfer family and perform explicit ownership transfer when resources become graphics/RT inputs.

Small directly mapped dynamic resources do not require transfer-queue copies.

Frame-graph ownership transitions should be explicit and measurable.

## 9. FrameContext

Two frames in flight.

Conceptual ownership is exact at the queue-completion level:

```cpp
struct FrameContext {
    uint32_t frameIndex;
    QueueCompletionValues completion;

    VkCommandPool graphicsCommandPool;
    VkCommandBuffer graphicsCommandBuffer;

    VkCommandPool transferCommandPool;
    VkCommandBuffer transferCommandBuffer;

    DescriptorArena frameDescriptors;
    LinearGpuArena transientGpu;
    UploadArena upload;
    QueryArena timestamps;

    DynamicSceneRegion dynamicScene;
    SkinnedVertexRegion skinnedVertices;

    // per-FrameContext TLAS storage/descriptor
};
```

Exact subsystem fields may be split, but per-queue completion values and per-frame TLAS ownership must not collapse into one scalar.

See architecture 052.

## 10. Timeline synchronization

Internal synchronization uses **one monotonically increasing timeline semaphore per active queue**:

```text
graphics timeline
transfer timeline
optional async-compute timeline
```

Cross-queue dependencies are expressed with timeline waits/signals through `vkQueueSubmit2`.

A single independently-signaled global timeline is not used for concurrent queue completion because a higher value from one queue must not falsely imply completion of unrelated work on another queue.

Binary semaphores remain for swapchain acquire/present where WSI requires them.

FrameContext reuse waits on every queue completion value that used that context's transient resources.

## 11. Dynamic Rendering

Graphics passes use Vulkan Dynamic Rendering.

Traditional long-lived render-pass/framebuffer objects are not architectural dependencies.

## 12. Frame graph

The frame graph owns:

```text
image layout transitions
buffer/image access state
Synchronization2 barriers
queue ownership transitions
transient lifetime
transient aliasing later
pass debug labels
GPU timestamps
descriptor generation for transient images
```

Passes declare logical intent such as:

```text
SampledRead
StorageRead
StorageWrite
ColorAttachment
DepthAttachment
TransferSrc
TransferDst
AccelerationStructureBuildInput
AccelerationStructureWrite
Present
```

## 13. AS scratch

Reference minimum scratch alignment:

```text
64 bytes
```

Maintain a reusable suballocated AS scratch arena.

Avoid one allocation per BLAS/TLAS build.

## 14. Skinned geometry

At least two frame-visible regions are maintained for GPU compute-skinned vertex output.

The skinned output is used by:

```text
raster
motion/temporal data
dynamic actor BLAS
```

The exact buffer-ring layout remains benchmark-driven.

## 15. Pipeline binary persistence

Reference device supports `VK_KHR_pipeline_binary` and reports internal/precompiled cache capability.

Preferred disk path:

```text
$XDG_CACHE_HOME/ufoai-remaster/vulkan/
```

fallback:

```text
~/.cache/ufoai-remaster/vulkan/
```

Cache identity includes:

```text
pipeline global key
device UUID
driver UUID
renderer build ID
shader ABI version
ShaderBindingAbiHash256
shader source/compiled hash
Slang compiler version
pipeline description hash
```

Invalid or mismatched binaries are discarded.

## 16. Conventional pipeline objects remain baseline

Even though the reference B580 supports shader objects and graphics pipeline libraries, the first renderer uses ordinary Vulkan pipeline objects created for descriptor-heap use (`VK_PIPELINE_CREATE_2_DESCRIPTOR_HEAP_BIT_EXT`) with a null pipeline layout.

Reasons:

- fewer runtime state combinations;
- clear pipeline ownership;
- easier RT/raster debugging;
- strong pipeline-binary persistence support.

## 17. Present/HDR

Native Wayland surface baseline:

```text
FIFO present mode first
MAILBOX optional
IMMEDIATE diagnostic/developer option
```

Reference Wayland surface supports present timing and present-wait capabilities.

Use these for frame-pacing telemetry before implementing ad-hoc sleep-based pacing.

Preferred HDR surface pair:

```text
VK_FORMAT_A2B10G10R10_UNORM_PACK32
VK_COLOR_SPACE_HDR10_ST2084_EXT
```

with SDR fallback handled separately.
