# Frame Graph Resource-State and Synchronization Model

**Status:** Implementation specification baseline  
**Related ADR:** ADR-016  
**Synchronization API:** Vulkan Synchronization2

## 1. Internal state types

### Image state

```cpp
struct ImageState {
    VkPipelineStageFlags2 stages;
    VkAccessFlags2 access;
    VkImageLayout layout;

    uint32_t queueFamily;

    bool initialized;
};
```

### Buffer state

```cpp
struct BufferState {
    VkPipelineStageFlags2 stages;
    VkAccessFlags2 access;

    uint32_t queueFamily;

    bool initialized;
};
```

### Acceleration-structure state

```cpp
struct AccelState {
    VkPipelineStageFlags2 stages;
    VkAccessFlags2 access;

    uint32_t queueFamily;

    bool initialized;
};
```

`initialized` means meaningful prior contents exist.

## 2. Image access mapping

| Frame Graph access | Vulkan stage | Vulkan access | Vulkan layout |
|---|---|---|---|
| `SampledRead` | declared shader stages | `VK_ACCESS_2_SHADER_SAMPLED_READ_BIT` | `VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL` |
| `StorageRead` | declared shader stages | `VK_ACCESS_2_SHADER_STORAGE_READ_BIT` | `VK_IMAGE_LAYOUT_GENERAL` |
| `StorageWrite` | declared shader stages | `VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT` | `VK_IMAGE_LAYOUT_GENERAL` |
| `StorageReadWrite` | declared shader stages | `VK_ACCESS_2_SHADER_STORAGE_READ_BIT \| VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT` | `VK_IMAGE_LAYOUT_GENERAL` |
| `ColorAttachment` | `VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT` | `VK_ACCESS_2_COLOR_ATTACHMENT_READ_BIT \| VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT` | `VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL` |
| `DepthStencilRead` | early + late fragment tests | `VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT` | `VK_IMAGE_LAYOUT_DEPTH_STENCIL_READ_ONLY_OPTIMAL` |
| `DepthStencilWrite` | early + late fragment tests | `VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT \| VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT` | `VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL` |
| `TransferSrc` | `VK_PIPELINE_STAGE_2_TRANSFER_BIT` | `VK_ACCESS_2_TRANSFER_READ_BIT` | `VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL` |
| `TransferDst` | `VK_PIPELINE_STAGE_2_TRANSFER_BIT` | `VK_ACCESS_2_TRANSFER_WRITE_BIT` | `VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL` |
| `Present` | `VK_PIPELINE_STAGE_2_NONE` | `VK_ACCESS_2_NONE` | `VK_IMAGE_LAYOUT_PRESENT_SRC_KHR` |

Shader-stage translation:

```text
Vertex     -> VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT
Fragment   -> VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT
Compute    -> VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT
RayTracing -> VK_PIPELINE_STAGE_2_RAY_TRACING_SHADER_BIT_KHR
Task       -> VK_PIPELINE_STAGE_2_TASK_SHADER_BIT_EXT
Mesh       -> VK_PIPELINE_STAGE_2_MESH_SHADER_BIT_EXT
```

Task/Mesh are not baseline rendering paths but the mapping is defined.

## 3. Buffer access mapping

| Frame Graph access | Vulkan stage | Vulkan access |
|---|---|---|
| `VertexRead` | `VK_PIPELINE_STAGE_2_VERTEX_ATTRIBUTE_INPUT_BIT` | `VK_ACCESS_2_VERTEX_ATTRIBUTE_READ_BIT` |
| `IndexRead` | `VK_PIPELINE_STAGE_2_INDEX_INPUT_BIT` | `VK_ACCESS_2_INDEX_READ_BIT` |
| `IndirectRead` | `VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT` | `VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT` |
| `UniformRead` | declared shader stages | `VK_ACCESS_2_UNIFORM_READ_BIT` |
| `StorageRead` | declared shader stages | `VK_ACCESS_2_SHADER_STORAGE_READ_BIT` |
| `StorageWrite` | declared shader stages | `VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT` |
| `StorageReadWrite` | declared shader stages | storage read + write |
| `TransferSrc` | `VK_PIPELINE_STAGE_2_TRANSFER_BIT` | `VK_ACCESS_2_TRANSFER_READ_BIT` |
| `TransferDst` | `VK_PIPELINE_STAGE_2_TRANSFER_BIT` | `VK_ACCESS_2_TRANSFER_WRITE_BIT` |
| `AccelBuildInputRead` | `VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_BUILD_BIT_KHR` | `VK_ACCESS_2_SHADER_READ_BIT` |
| `AccelScratchReadWrite` | `VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_BUILD_BIT_KHR` | `VK_ACCESS_2_ACCELERATION_STRUCTURE_READ_BIT_KHR \| VK_ACCESS_2_ACCELERATION_STRUCTURE_WRITE_BIT_KHR` |
| `ShaderBindingTableRead` | `VK_PIPELINE_STAGE_2_RAY_TRACING_SHADER_BIT_KHR` | `VK_ACCESS_2_SHADER_BINDING_TABLE_READ_BIT_KHR` |

The acceleration-structure build-input mapping follows Vulkan's RT synchronization rules: vertex/index/instance/transform build buffers are synchronized at the AS-build stage with shader-read access.

## 4. Acceleration-structure access mapping

| Frame Graph access | Vulkan stage | Vulkan access |
|---|---|---|
| `BuildRead` | `VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_BUILD_BIT_KHR` | `VK_ACCESS_2_ACCELERATION_STRUCTURE_READ_BIT_KHR` |
| `BuildWrite` | `VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_BUILD_BIT_KHR` | `VK_ACCESS_2_ACCELERATION_STRUCTURE_WRITE_BIT_KHR` |
| `ShaderRead` | declared shader stages | `VK_ACCESS_2_ACCELERATION_STRUCTURE_READ_BIT_KHR` |
| `CopyRead` | `VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_COPY_BIT_KHR` | `VK_ACCESS_2_ACCELERATION_STRUCTURE_READ_BIT_KHR` |
| `CopyWrite` | `VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_COPY_BIT_KHR` | `VK_ACCESS_2_ACCELERATION_STRUCTURE_WRITE_BIT_KHR` |

`VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_COPY_BIT_KHR` is available because the B580 baseline requires RT maintenance1.

## 5. Defined-content tracking

Transient resources start:

```text
initialized = false
```

A compile error is generated for a read before a defining write.

### Attachments

First use:

```text
LoadOp::Load
```

requires initialized content.

First use:

```text
LoadOp::Clear
LoadOp::DontCare
```

does not.

After an attachment pass:

```text
StoreOp::Store
    -> initialized = true

StoreOp::DontCare
    -> initialized = false
```

A later read from discarded contents is a graph compile error.

Imported resources specify whether their initial contents are defined.

## 6. Dependency construction

For each overlapping resource range the compiler tracks:

```text
last writer
active readers
```

### New read

Dependency:

```text
last writer -> reader
```

Then add reader to active-reader set.

### New write/read-write

Dependencies:

```text
last writer -> writer
all active readers -> writer
```

Then clear active readers and set the new last writer.

This produces RAW, WAR and WAW ordering.

Independent resource ranges do not create edges.

## 7. Stable topological order

The compiler topologically sorts the pass DAG.

When passes are independent, declaration order is used as the stable tie-breaker.

Graph cycles are compile errors and report the participating passes/resources.

## 8. Same-queue barrier rule

For overlapping ranges on the same queue:

### Read -> read

No barrier if:

```text
same layout
no write access involved
```

The tracked read state may union stage/access masks.

### Anything involving a prior or next write

Generate a barrier.

### Image layout change

Generate an image barrier even for read -> read.

### First transient image use

Old layout:

```text
VK_IMAGE_LAYOUT_UNDEFINED
```

Source:

```text
VK_PIPELINE_STAGE_2_NONE
VK_ACCESS_2_NONE
```

The transition does not preserve contents.

## 9. Barrier representation

Use only Synchronization2 barrier types:

```text
VkMemoryBarrier2
VkBufferMemoryBarrier2
VkImageMemoryBarrier2
VkDependencyInfo
```

Normal inter-pass barriers are emitted with:

```text
vkCmdPipelineBarrier2
```

The compiler combines all compatible pass-prologue barriers into one dependency call where practical.

Queue-release barriers are emitted in producer epilogues.

Queue-acquire barriers are emitted in consumer prologues.

## 10. Queue ownership transfer

Resources are created `VK_SHARING_MODE_EXCLUSIVE` by default.

Cross-family dependency:

```text
producer queue
    release barrier
    signal producer timeline value
          |
          v
consumer queue
    wait producer timeline value
    acquire barrier
```

For images, release and acquire barriers use the same:

```text
srcQueueFamilyIndex
dstQueueFamilyIndex
oldLayout
newLayout
subresourceRange
```

The layout transition is part of the ownership transfer.

Release side uses producer stage/access.

Acquire side uses consumer stage/access.

`VK_PIPELINE_STAGE_2_NONE` / no-access scopes are used on the unused side of the release/acquire operation as appropriate under Synchronization2.

## 11. Queue-local timeline semaphores

```cpp
struct QueueTimeline {
    VkSemaphore semaphore;
    uint64_t nextSignalValue;
};
```

One per active queue:

```text
graphicsTimeline
transferTimeline
optional computeTimeline
```

A submission batch records:

```cpp
struct SubmissionWait {
    QueueClass producerQueue;
    uint64_t value;
    VkPipelineStageFlags2 dstStages;
};

struct SubmissionSignal {
    QueueClass queue;
    uint64_t value;
};
```

`vkQueueSubmit2` carries timeline waits/signals.

FrameContext reuse waits on all queue timeline values to which that context's transient resources were submitted.

## 12. External/imported readiness

Imported resources carry:

```cpp
struct ReadyToken {
    QueueClass queue;
    uint64_t timelineValue;
};

struct ExternalState {
    ResourceState state;
    ReadyToken ready;
};
```

Example:

```text
texture upload on transfer queue
      |
signal transfer value 37
      |
Frame Graph import
      |
graphics first use waits transfer 37
      |
queue ownership acquire
```

If an imported resource is already graphics-owned and ordered by the graphics queue, the token can be empty.

## 13. Swapchain

The swapchain image is imported with the state tracked by the swapchain manager.

The final graph operation:

```cpp
graph.present(swapchainImage);
```

creates:

```text
last writer
   ->
PRESENT_SRC_KHR
```

and the render-finished WSI synchronization required by presentation.

The WSI acquire/present binary semaphores remain outside timeline replacement.

## 14. No hidden global barriers

The compiler may not solve uncertainty by emitting:

```text
ALL_COMMANDS
MEMORY_READ | MEMORY_WRITE
```

global barriers.

If an access cannot be mapped precisely, graph compilation fails in development builds until a real access type is added.

This is required to keep B580 synchronization measurable and auditable.
