# Vulkan Device Contract and Feature Chain

**Status:** Architecture baseline  
**Related ADR:** ADR-015  
**Reference GPU:** Intel Arc B580 / BMG G21  
**Reference driver:** Mesa 26.2.2

## 1. Device selection

The renderer should explicitly prefer and validate:

```text
vendorID = 0x8086
deviceID = 0xe20b
deviceType = DISCRETE_GPU
deviceName contains Arc B580 / BMG G21
```

The llvmpipe CPU device exposed by Mesa must never be selected as the remaster target.

Device selection should log:

```text
deviceName
vendorID
deviceID
driverID
driverName
driverInfo
apiVersion
driverVersion
deviceUUID
driverUUID
pipelineCacheUUID
```

Capability validation is **device-scoped**. A multi-device `vulkaninfo`/runtime enumeration may also contain llvmpipe; extension/feature names found only on that CPU device must never satisfy a B580 requirement.

The Mesa 26.2.2 B580 capture explicitly does not expose `VK_EXT_memory_priority` or `VK_EXT_pageable_device_local_memory`, so neither is a mandatory device extension.

`VK_EXT_descriptor_heap` is mandatory under accepted ADR-045. The reference device reports `descriptorHeap = true` and `descriptorHeapCaptureReplay = true`.

## 2. Mandatory API baseline

Require:

```text
Vulkan device API >= 1.4
```

The reference B580 reports Vulkan 1.4.354.

## 3. Mandatory instance capabilities

Required for normal Fedora 44 KDE Wayland operation:

```text
VK_KHR_surface
VK_KHR_wayland_surface
VK_EXT_debug_utils              development builds
VK_EXT_swapchain_colorspace     HDR/color-space enumeration
```

The renderer may enumerate XCB/Xlib surfaces for diagnostics/SDR fallback, but the HDR path is native Wayland.

## 4. Mandatory device extensions

The B580 renderer contract requires:

```text
VK_KHR_swapchain

VK_KHR_acceleration_structure
VK_KHR_deferred_host_operations
VK_KHR_ray_tracing_pipeline
VK_KHR_ray_tracing_maintenance1

VK_EXT_descriptor_heap
VK_KHR_shader_untyped_pointers
VK_EXT_memory_budget
VK_EXT_hdr_metadata

VK_KHR_pipeline_binary
```

`VK_KHR_ray_query` is required as a capability only if the renderer retains its exceptional comparator path; it is not the default tracing mechanism.

## 5. Core feature chain

Use Vulkan 1.2/1.3/1.4 feature structs for core functionality.

Required Vulkan 1.2 features:

```text
scalarBlockLayout = true
timelineSemaphore = true
bufferDeviceAddress = true
```

Descriptor-indexing/update-after-bind features remain useful capability telemetry but are not production binding requirements under the descriptor-heap ABI.

Required Vulkan 1.3 features:

```text
synchronization2 = true
dynamicRendering = true
subgroupSizeControl = true
computeFullSubgroups = true
```

Required Vulkan 1.4 features:

```text
dynamicRenderingLocalRead = true
```

`hostImageCopy` and `pushDescriptor` are available on the reference GPU but are not renderer-binding requirements. Descriptor-heap pipelines use `vkCmdPushDataEXT`, not push descriptors.

## 6. Required extension feature structs

### Descriptor heap

Require:

```text
descriptorHeap = true
shaderUntypedPointers = true
```

Reference B580 properties:

```text
descriptorHeapCaptureReplay = true
samplerHeapAlignment = 64
resourceHeapAlignment = 64
maxSamplerHeapSize = 2 GiB
maxResourceHeapSize = 2 GiB
samplerDescriptorSize = 32
imageDescriptorSize = 64
bufferDescriptorSize = 64
maxPushDataSize = 256
sparseDescriptorHeaps = true
```

Architecture 089 owns exact heap construction, binding, publication and root push-data behavior.

`VK_EXT_descriptor_buffer` may be logged as an available device capability but is not required or used as a renderer fallback.

### Acceleration structures

Require:

```text
accelerationStructure = true
```

Reference limitation:

```text
accelerationStructureIndirectBuild = false
```

Do not design around indirect AS build commands.

### Ray tracing pipeline

Require:

```text
rayTracingPipeline = true
rayTracingPipelineTraceRaysIndirect = true
rayTraversalPrimitiveCulling = true
```

### RT maintenance

Require:

```text
rayTracingMaintenance1 = true
rayTracingPipelineTraceRaysIndirect2 = true
```

### Memory priority / pageable device-local memory

Not required and not exposed by the Mesa 26.2.2 B580 device:

```text
VK_EXT_memory_priority                 absent on B580
VK_EXT_pageable_device_local_memory    absent on B580
```

The allocator remains correct using `VK_EXT_memory_budget` plus project-owned residency/eviction policy. Do not populate these feature structs unless the selected physical device explicitly advertises the corresponding extension.

### Pipeline binary

Require:

```text
pipelineBinaries = true
```

### Optional position fetch

Available:

```text
rayTracingPositionFetch = true
```

Architecture 073 requires a B580 benchmark against the existing BDA reconstruction path before making shader code depend on position fetch universally.

## 7. Optional feature groups

### Async compute group

Reference GPU supports a separate compute+transfer family.

Not required.

### Mesh shader group

Available:

```text
taskShader = true
meshShader = true
```

Not baseline.

### Shader object group

Available:

```text
shaderObject = true
```

Not baseline.

### Graphics pipeline library

Available:

```text
graphicsPipelineLibrary = true
```

Not baseline.

### Cooperative matrix

Available:

```text
cooperativeMatrix = true
```

Compute only on the reference GPU.

Not baseline.

## 8. Subgroup policy

Reference properties:

```text
default subgroup size = 32
minimum subgroup size = 16
maximum subgroup size = 32

required subgroup size supported for:
    compute
    task
    mesh
```

Baseline:

```text
subgroup32 default
```

Benchmark:

```text
subgroup16 versus subgroup32
```

for skinning, denoising and other RT-adjacent compute.

## 9. RT properties recorded

Reference B580:

```text
shaderGroupHandleSize = 32
shaderGroupHandleAlignment = 16
shaderGroupBaseAlignment = 16
shaderGroupHandleCaptureReplaySize = 32
maxRayHitAttributeSize = 32
maxRayRecursionDepth = 31
```

Engine baseline still clamps effective recursion to 1.

Acceleration-structure scratch offset alignment:

```text
64 bytes
```

## 10. Startup rejection

Startup should fail the remaster Vulkan renderer with a precise capability report if a mandatory feature is missing.

It should not silently:

- select llvmpipe;
- downgrade to a non-RT renderer;
- switch away from the accepted descriptor-heap binding path;
- fall back from native HDR Wayland to XWayland while claiming HDR mode.
