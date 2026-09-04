# ADR-016 — Frame Graph Owns Resource State and Inter-Pass Synchronization

**Status:** Accepted  
**Decision type:** Vulkan frame execution / synchronization  
**Related:** ADR-015  
**Primary target:** Intel Arc B580 / Mesa ANV / Vulkan 1.4

## Context

The remaster renderer contains raster, compute, acceleration-structure build, ray-tracing, transfer and presentation work.

Manual image-layout transitions and barriers distributed across individual rendering passes would make the following difficult to prove correct:

- G-buffer -> RT reads;
- compute skinning -> dynamic BLAS build;
- BLAS -> TLAS build;
- TLAS -> RT trace;
- RT output -> denoiser;
- transfer queue -> graphics queue ownership;
- HDR post -> swapchain present;
- transient descriptor-heap image publication/layouts.

The B580 reference target supports Vulkan Synchronization2 and `vkQueueSubmit2`.

## Decision

A renderer-specific Frame Graph is the single owner of:

```text
inter-pass dependency construction
resource hazard ordering
image layout transitions
buffer/image memory barriers
acceleration-structure memory barriers
queue-family ownership transfer
cross-queue timeline waits/signals
transient resource lifetime
automatic pass timestamps
dynamic-rendering attachment setup
transient image descriptor layout information
```

Individual passes declare intent rather than raw inter-pass Vulkan synchronization.

## Pass atomicity

A pass is the Frame Graph synchronization unit.

Normal passes may not manually perform inter-pass resource transitions.

If multiple operations inside one pass need an intra-pass memory dependency while remaining in the same declared resource state, the callback may issue a local Synchronization2 barrier.

If an image needs a different layout or a resource needs a semantically different final access state, split the work into separate passes.

## Queue timelines

Each active Vulkan queue owns its own monotonically increasing timeline semaphore/value space.

Baseline queues:

```text
graphics timeline
transfer timeline
optional async-compute timeline when enabled
```

Do not use one independently-signaled global timeline for concurrent queues.

Cross-queue dependencies use `VkSemaphoreSubmitInfo` waits/signals in `vkQueueSubmit2`.

## Resource tracking granularity

Images are tracked by overlapping:

```text
aspect
mip range
array-layer range
```

Buffers are tracked by overlapping byte ranges.

Acceleration structures are tracked as whole logical objects.

Non-overlapping ranges do not create false hazards.

## Initial aliasing policy

The first implementation does not perform intra-frame memory aliasing between transient images/buffers.

The compiler still calculates first/last use.

Transient allocation may be reused across completed FrameContexts, but two logical resources in the same compiled frame receive distinct physical storage.

Aliasing may be added later without changing the public pass/resource API.

## Consequences

- pass code contains less Vulkan synchronization boilerplate;
- descriptor-heap image-layout correctness is derived from the same state model as barriers;
- compute-skinning/RT dependencies are explicit;
- transfer queue ownership becomes auditable;
- validation failures can identify the declaring pass/resource rather than a distant raw barrier call.
