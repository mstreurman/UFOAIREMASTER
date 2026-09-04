# Frame Graph Compilation and Execution

**Status:** Implementation specification baseline  
**Related:** `015-exact-frame-graph-api.md`, `016-resource-state-and-synchronization-model.md`

## 1. Frame lifetime

A new logical graph is built each rendered frame from a FrameContext-owned CPU arena.

The graph description is transient.

Persistent Vulkan resources are imported.

Frame-local logical images/buffers/AS objects are created by the graph.

## 2. Compile phases

Compilation occurs in this order.

### Phase 1 — Validate declarations

Check:

- handles are valid;
- ranges are in bounds;
- pass class and queue are compatible;
- shader-stage declarations are legal;
- read/write API agrees with access semantics;
- attachment formats/aspects are compatible;
- imported states are valid.

### Phase 2 — Infer Vulkan creation usage

Collect all uses for every transient resource.

Examples:

```text
SampledRead     -> VK_IMAGE_USAGE_SAMPLED_BIT
StorageWrite    -> VK_IMAGE_USAGE_STORAGE_BIT
ColorAttachment -> VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT
TransferDst     -> VK_IMAGE_USAGE_TRANSFER_DST_BIT
```

Buffers similarly infer:

```text
VERTEX_BUFFER
INDEX_BUFFER
INDIRECT_BUFFER
UNIFORM_BUFFER
STORAGE_BUFFER
TRANSFER_SRC/DST
ACCELERATION_STRUCTURE_BUILD_INPUT_READ_ONLY
SHADER_BINDING_TABLE
SHADER_DEVICE_ADDRESS
```

`BufferFlags::DeviceAddress` forces:

```text
VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT
```

AS scratch buffers include:

```text
VK_BUFFER_USAGE_STORAGE_BUFFER_BIT
VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT
```

### Phase 3 — Defined-content validation

Reject:

- transient read-before-write;
- attachment `Load` from undefined contents;
- read after `StoreOp::DontCare` without intervening defining write.

### Phase 4 — Build hazard DAG

Use overlapping image/buffer ranges and whole-AS state.

Create:

```text
RAW
WAR
WAW
explicit dependsOn
```

edges.

### Phase 5 — Topological sort

Stable declaration order is used for independent passes.

Cycles are fatal graph errors.

### Phase 6 — Determine resource lifetimes

For every transient logical resource record:

```text
first pass use
last pass use
queue set
```

Baseline does not intra-frame alias resources.

Lifetime information is still retained for diagnostics and future aliasing.

### Phase 7 — Allocate/resolve physical resources

Transient resources are acquired from FrameContext/device pools.

Imported logical handles resolve to external Vulkan resources.

All required debug names are applied.

### Phase 8 — Derive per-use states

Map each declared access to:

```text
pipeline stages
access flags
image layout
queue family
```

using architecture document 016.

### Phase 9 — Synthesize barriers

Generate:

```text
same-queue prologue barriers
producer release barriers
consumer acquire barriers
final present transition
```

Track state at declared range granularity.

### Phase 10 — Build submission batches

Passes are grouped per queue.

A batch is split when necessary to express a cross-queue wait/signal without unnecessarily stalling earlier independent work.

Each batch receives:

```text
command buffer
wait list
signal value
pass range
```

Baseline queue set:

```text
graphics
transfer
```

Async compute participates only when explicitly enabled for a benchmark path.

### Phase 11 — Allocate GPU timestamp queries

Every pass receives:

```text
begin timestamp
end timestamp
```

from its FrameContext query arena.

Additional submission-boundary timestamps may be allocated for queue-overlap analysis.

### Phase 12 — Prepare Dynamic Rendering metadata

Raster passes compile:

```text
VkRenderingAttachmentInfo[]
VkRenderingInfo
```

from attachment declarations and resolved image views/layouts.

### Phase 13 — Prepare pass heap publications

FrameContext resource-heap space is allocated for each pass that requests transient descriptors.

The per-pass resolved image layout is made available to the heap writer, which produces typed resource-heap handles under architecture 089.

## 3. Execution

Execution records command buffers by submission batch.

For each pass:

```text
debug label begin
timestamp begin
prologue barriers

if Raster:
    vkCmdBeginRendering

execute callback

if Raster:
    vkCmdEndRendering

epilogue release barriers
timestamp end
debug label end
```

No pass manually emits graph-owned inter-pass transitions.

## 4. Submission

Use:

```text
vkQueueSubmit2
```

with:

```text
VkCommandBufferSubmitInfo
VkSemaphoreSubmitInfo waits
VkSemaphoreSubmitInfo signals
```

Queue-local timeline values are monotonically increasing.

WSI binary semaphore waits/signals are added to the graphics submission that consumes/acquires and presents the swapchain image.

## 5. Completion tracking

After submission:

```cpp
frame.graphicsCompletion = lastGraphicsSignal;
frame.transferCompletion = lastTransferSignalUsedByFrame;
frame.computeCompletion = optionalComputeSignal;
```

Before reusing the FrameContext, wait until all non-zero completion values for that context have completed.

## 6. External state publication

After graph submission, imported persistent resources have a known planned final state/owner.

The resource registry records:

```text
final ResourceState
owning queue family
completion ReadyToken
```

The next frame or streaming system imports those values.

This avoids pretending an external resource is immediately complete while work is still in flight.

## 7. Upload manager integration

Large streaming uploads normally originate outside render-pass construction.

The Upload Manager:

```text
allocates staging
records transfer command
submits transfer queue
signals transfer timeline
publishes ReadyToken
```

The Frame Graph imports the destination resource with that token and creates the graphics wait/ownership acquire only when the resource is actually consumed.

## 8. Descriptor-heap integration

At command-buffer recording start:

```text
bind the one sampler heap
bind the one resource heap
```

Persistent content uses stable heap registries. Frame/pass resources use the active FrameContext resource-heap arena. Pass-data records carry the typed heap indices they consume.

Transient image descriptors are generated using the exact layout derived for that pass.

The renderer does not issue non-heap descriptor binding commands after heap binding, and no duplicated independent image-layout state is maintained by the heap subsystem.

## 9. Dynamic BLAS/TLAS ordering example

Typical actor path:

```text
Skinning
    Buffer StorageWrite

        |
        | barrier:
        | COMPUTE_SHADER / SHADER_STORAGE_WRITE
        | ->
        | AS_BUILD / SHADER_READ
        v

Dynamic BLAS Build
    skinned buffer = AccelBuildInputRead
    BLAS = BuildWrite

        |
        | AS_BUILD / AS_WRITE
        | ->
        | AS_BUILD / AS_READ
        v

TLAS Build
    BLAS = BuildRead
    instance buffer = AccelBuildInputRead
    TLAS = BuildWrite

        |
        | AS_BUILD / AS_WRITE
        | ->
        | RAY_TRACING_SHADER / AS_READ
        v

RT Shadows / Reflections / GI
    TLAS = ShaderRead
```

This dependency chain is generated from declarations rather than handwritten barriers.

## 10. G-buffer -> RT -> denoiser example

```text
G-buffer
    DepthStencilWrite
    ColorAttachment

        |
        v

RT Shadows
    depth/normal SampledRead
    shadow StorageWrite

        |
        v

Denoiser
    shadow StorageRead
    history SampledRead
    output StorageWrite

        |
        v

Deferred Lighting
    G-buffer SampledRead
    denoised shadow SampledRead
```

Image layouts and barriers derive mechanically from the state table.

## 11. Diagnostics

A compiled graph can dump:

```text
pass DAG
topological order
resource lifetime table
physical resource resolution
per-pass input/output states
generated barriers
queue ownership transfers
timeline waits/signals
descriptor arena offsets
timestamp indices
```

Development command target concept:

```text
r_dumpFrameGraph 1
```

Exact console command naming can be chosen during implementation.

## 12. Validation requirements

Development builds should assert:

- no use of undeclared resource in `PassContext`;
- no raw inter-pass barrier from ordinary pass code;
- no descriptor write for an image not declared for that pass;
- no transient read-before-write;
- no stale imported readiness token;
- no queue ownership use without acquire;
- no present without a valid swapchain-image writer/transition.

## 13. Initial non-features

Not in the first implementation:

```text
automatic dead-pass culling
intra-frame transient memory aliasing
automatic async-compute scheduling
automatic pass merging
render-pass/subpass synthesis
attachment feedback loops
device-generated command scheduling
```

Their absence is deliberate.

Correctness, deterministic diagnostics and measurable B580 behavior come first.

## Instrumentation and diagnostic integration

ADR-027 makes Frame Graph pass boundaries the primary GPU instrumentation boundary.

Every significant production pass may carry:

```text
semantic pass NameId
VK_EXT_debug_utils command label
GPU timestamp begin/end query indices
effect-specific counters where useful
```

Timestamp results are consumed asynchronously after the relevant FrameContext/timeline completion.

Diagnostic configurations may append explicit passes such as:

```text
RT visualization resolve
RenderProbeCapture
diagnostic readback copy
```

These passes obey the same declared resource-access/state rules as production passes.

The profiler/debug UI must never introduce a queue-idle stall merely to display current results.

## Transient aliasing benchmark trigger

Baseline still performs no intra-frame transient aliasing.

Architecture 073 permits an aliasing experiment only after measured B580 memory high-water/pressure makes the additional complexity worthwhile.

The default implementation remains non-aliased for clarity/debuggability.
