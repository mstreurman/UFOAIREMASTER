# ADR-015 — Arc B580 Vulkan GPU Foundation

**Status:** Accepted  
**Decision type:** GPU/runtime foundation  
**Primary GPU:** Intel Arc B580 / Battlemage BMG G21  
**Reference driver:** Mesa Intel ANV 26.2.2  
**Reference Vulkan device API:** 1.4.354

## Context

The remaster targets one concrete GPU architecture first:

```text
Intel Arc B580
vendorID 0x8086
deviceID 0xe20b
Battlemage BMG G21
Mesa Intel open-source Vulkan driver
```

A complete `vulkaninfo` dump from the reference Fedora 44 system confirms the exact feature/extension set used by this ADR.

## Decision

The renderer foundation is:

```text
Vulkan 1.4
native Wayland WSI
Dynamic Rendering
Synchronization2
Queue-local timeline semaphores
Buffer Device Address
Scalar block layout
VK_EXT_descriptor_heap
VK_KHR_shader_untyped_pointers
VK_EXT_memory_budget
VK_KHR_pipeline_binary
VK_KHR_acceleration_structure
VK_KHR_ray_tracing_pipeline
VK_KHR_ray_query available but non-preferred
VK_KHR_ray_tracing_maintenance1
VK_KHR_ray_tracing_position_fetch available
VK_EXT_hdr_metadata
VK_EXT_swapchain_colorspace
```

## Resource binding

ADR-045 accepts `VK_EXT_descriptor_heap` as the production binding architecture from the first renderer implementation.

The reference B580 / Mesa 26.2.2 exposes both `descriptorHeap` and `descriptorHeapCaptureReplay`, 2 GiB sampler/resource heap limits, 64-byte heap alignment and `shaderUntypedPointers = true`.

Production heap pipelines use one sampler heap plus one resource heap, no descriptor-set layouts, a null pipeline layout, and `vkCmdPushDataEXT` for the 32-byte `GpuShaderRoot`.

`VK_EXT_descriptor_buffer` is no longer a renderer requirement or fallback. It may remain visible in diagnostics because the driver supports it.

Large structured GPU data continues to use Buffer Device Address where appropriate.

## Pipeline persistence

`VK_KHR_pipeline_binary` is the preferred persistent compiled-pipeline cache mechanism for the B580 reference target.

Traditional `VkPipelineCache` may still be used internally or as a compatibility mechanism, but it is not the architectural persistence primitive.

## HDR

The supported HDR path requires a native Wayland surface.

Preferred output baseline:

```text
VK_FORMAT_A2B10G10R10_UNORM_PACK32
VK_COLOR_SPACE_HDR10_ST2084_EXT
```

with `VK_EXT_hdr_metadata`.

XCB/Xlib surfaces are not considered the supported HDR600 path because the audited surface list only exposes SDR color spaces there.

## Queues

Reference queue-family assignment:

```text
family 0:
    graphics + compute + transfer
    primary render/RT queue

family 2:
    transfer only
    asynchronous asset upload queue

family 1:
    compute + transfer
    reserved for measured async-compute experiments
```

Async compute is not required for baseline correctness or performance.

## Memory

The B580 exposes:

- ordinary device-local VRAM;
- device-local + host-visible + host-coherent memory;
- host-visible + host-coherent + host-cached system memory;
- `VK_EXT_memory_budget`.

The allocator therefore distinguishes:

```text
Persistent device-local
Mapped device-local dynamic
Host staging/readback
Transient frame memory
Acceleration-structure scratch
```

The runtime respects the current Vulkan budget, not only physical VRAM size.

The Mesa 26.2.2 B580 device section does **not** expose `VK_EXT_memory_priority` or `VK_EXT_pageable_device_local_memory`. They are therefore not B580 requirements. The renderer uses `VK_EXT_memory_budget` plus its own residency/eviction classes; any future use of memory-priority/pageable-local-memory extensions is optional and device-gated.

## Ray tracing

RT pipeline remains the default hardware-tracing mechanism.

RayQuery remains available only for measured exceptions.

Baseline RT rules remain:

- raster primary visibility;
- recursion depth 1;
- dedicated RT pipelines;
- compact payloads;
- opaque geometry aggressively;
- avoid any-hit where possible;
- direct AS build commands;
- B580-specific benchmarking.

## Explicitly not mandatory

The following are supported by the reference GPU but are not baseline requirements:

```text
VK_EXT_mesh_shader
VK_EXT_shader_object
VK_EXT_graphics_pipeline_library
VK_KHR_cooperative_matrix
async compute
fragment shading rate
device-generated commands
```

They may be benchmarked later.

## Consequences

This ADR intentionally reduces portability.

A device that does not satisfy the mandatory feature contract is not considered equivalent to the B580 reference renderer target.
