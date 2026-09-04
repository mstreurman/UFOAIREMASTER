# Reference — Intel Arc B580 Vulkan Capabilities

**Source:** Developer-provided full `vulkaninfo` capture  
**Reference date:** 2026-09-04  
**GPU:** Intel Arc B580 / BMG G21  
**Mesa:** 26.2.2  
**Vulkan device API:** 1.4.354

## Provenance and device scoping

The current runtime evidence is the post-upgrade capture summarized in:

```text
reference/reference-local-vulkan-state-2026-09-04-mesa-26_2_2.md
```

All capability claims in this document are scoped specifically to:

```text
GPU0
vendorID 0x8086
deviceID 0xe20b
deviceName Intel(R) Arc(tm) B580 Graphics (BMG G21)
driverID DRIVER_ID_INTEL_OPEN_SOURCE_MESA
driverInfo Mesa 26.2.2
```

The same `vulkaninfo` output also contains a separate llvmpipe CPU device. Never infer B580 support from a whole-file extension/feature grep without first isolating the B580 device section.

## Identity

```text
vendorID          0x8086
deviceID          0xe20b
device type       discrete GPU
device API        Vulkan 1.4.354
driver version    26.2.2
driver ID         Intel open-source Mesa
pipelineCacheUUID 6b072dd5-3d62-8b32-8168-722fd60c1fb8
deviceUUID        86800be2-0000-0000-0300-000000000000
driverUUID        ffe06a92-7a02-f0b9-be4b-cdf916b0cba1
```

The Mesa upgrade changed the driver/pipeline-cache identity relative to the earlier 26.1.8 capture. Driver-dependent pipeline binaries and caches must therefore be treated as a different compatibility domain.

## WSI

Native Wayland exposes, among many combinations:

```text
VK_COLOR_SPACE_HDR10_ST2084_EXT
VK_COLOR_SPACE_BT2020_LINEAR_EXT
VK_FORMAT_A2B10G10R10_UNORM_PACK32
VK_FORMAT_A2R10G10B10_UNORM_PACK32
VK_FORMAT_R16G16B16A16_SFLOAT
```

Wayland present modes:

```text
MAILBOX
FIFO
IMMEDIATE
```

Wayland present timing is reported supported.

XCB/Xlib surfaces in the capture expose only SRGB-nonlinear SDR formats.

## Descriptor heap — Mesa 26.2.2 B580 observation

`VK_EXT_descriptor_heap` revision 1 is advertised by the B580 device.

Features:

```text
descriptorHeap              = true
descriptorHeapCaptureReplay = true
```

Properties:

```text
samplerHeapAlignment                    = 64
resourceHeapAlignment                   = 64
maxSamplerHeapSize                      = 2147483648 bytes (2 GiB)
maxResourceHeapSize                     = 2147483648 bytes (2 GiB)
minSamplerHeapReservedRange             = 0
minSamplerHeapReservedRangeWithEmbedded = 0
minResourceHeapReservedRange            = 0
samplerDescriptorSize                   = 32
imageDescriptorSize                     = 64
bufferDescriptorSize                    = 64
samplerDescriptorAlignment              = 32
imageDescriptorAlignment                = 64
bufferDescriptorAlignment               = 64
maxPushDataSize                         = 256
imageCaptureReplayOpaqueDataSize        = 8
maxDescriptorHeapEmbeddedSamplers       = 2048
samplerYcbcrConversionCount             = 3
sparseDescriptorHeaps                   = true
protectedDescriptorHeaps                = false
```

These values satisfy the device-side runtime portion of architecture 087. ADR-045 / Baseline 036 accepts descriptor heap as the production binding model from first implementation. Slang conformance and validation-layer execution tests remain mandatory qualification work.

The Vulkan extension defines exactly one sampler heap and one resource heap. Architecture 089 therefore designs directly around those two heaps rather than emulating the old multi-buffer descriptor topology.

## Descriptor buffer

The existing binding path remains available concurrently:

```text
descriptorBuffer = true
descriptorBufferCaptureReplay = true
descriptorBufferPushDescriptors = true
descriptorBufferImageLayoutIgnored = false

descriptorBufferOffsetAlignment = 64

samplerDescriptorSize = 32
sampledImageDescriptorSize = 64
storageImageDescriptorSize = 64
uniformBufferDescriptorSize = 64
storageBufferDescriptorSize = 64
accelerationStructureDescriptorSize = 16
```

This support is recorded as device capability evidence only. The production renderer does not require a descriptor-buffer fallback or A/B implementation.

## Descriptor indexing

Descriptor-indexing capabilities are also present on the B580:

```text
descriptorIndexing
runtimeDescriptorArray
descriptorBindingPartiallyBound
descriptorBindingVariableDescriptorCount
descriptorBindingUpdateUnusedWhilePending
sampled-image update-after-bind
storage-image update-after-bind
storage-buffer update-after-bind
non-uniform sampled/storage image indexing
non-uniform storage buffer indexing
```

## Buffer addressing

```text
bufferDeviceAddress = true
scalarBlockLayout = true
shaderUntypedPointers = true
```

`shaderUntypedPointers = true` is relevant because `VK_EXT_descriptor_heap` depends on `VK_KHR_shader_untyped_pointers` in addition to Vulkan 1.2/BDA-class addressing support.

## Ray tracing

```text
accelerationStructure = true
rayTracingPipeline = true
rayQuery = true
rayTracingMaintenance1 = true
rayTracingPositionFetch = true
rayTraversalPrimitiveCulling = true
```

Selected properties:

```text
maxRayRecursionDepth = 31
shaderGroupHandleSize = 32
shaderGroupHandleAlignment = 16
shaderGroupBaseAlignment = 16
maxRayHitAttributeSize = 32
AS scratch alignment = 64
```

Important limitation:

```text
accelerationStructureIndirectBuild = false
```

## Queues

```text
0: graphics + compute + transfer
1: compute + transfer
2: transfer only
```

Each has one queue and 64 timestamp bits.

## Memory

Device-local heap:

```text
~11.93 GiB
captured budget ~9.33 GiB
```

Host/system heap:

```text
~23.36 GiB
captured budget ~21.02 GiB
```

A device-local + host-visible + host-coherent memory type is available.

### Important B580 capability correction

The **B580/ANV device section does not advertise**:

```text
VK_EXT_memory_priority
VK_EXT_pageable_device_local_memory
```

and consequently has no B580 `memoryPriority` / `pageableDeviceLocalMemory` feature block in this capture.

Those extensions/features occur later in the same full output under the **llvmpipe CPU device**. Previous live architecture text that attributed them to the B580 is superseded by Baseline 035. The B580 allocator must use `VK_EXT_memory_budget` plus project-owned residency/eviction policy and must not require driver-controlled pageable-local-memory behavior.

## Subgroups

```text
default = 32
minimum = 16
maximum = 32
required subgroup size supported for compute/task/mesh
```

## Supported-but-not-baseline features

```text
mesh shaders
shader objects
graphics pipeline libraries
cooperative matrices
fragment shading rate
pipeline binaries
present timing/wait
descriptor buffer (available but non-baseline)
```

`VK_KHR_pipeline_binary` remains the accepted pipeline-persistence mechanism. Descriptor heap is the accepted production binding model under ADR-045; descriptor buffer is non-baseline capability telemetry.

## Static microarchitecture authority

This document records runtime Vulkan observations.

Static Arc B580/Xe2 execution-resource facts are recorded separately in:

```text
reference/reference-arc-b580-xe2-microarchitecture.md
```

Do not infer static Xe2 execution-resource topology from Vulkan properties alone.
