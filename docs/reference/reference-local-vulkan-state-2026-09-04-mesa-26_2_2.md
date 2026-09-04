# Local Vulkan State — 2026-09-04 — Mesa 26.2.2

**Status:** Developer-provided runtime observation  
**Scope:** Vulkan runtime only; does not replace the broader workstation/source snapshot  
**Input:** `ufoai-vulkaninfo-mesa-26.2.2.txt`

## Purpose

Record the first post-upgrade Arc B580 Vulkan capture after the developer built/installed Mesa 26.2.2.

This document is authoritative for the Vulkan runtime facts below. The later 10:41:03+02:00 broad workstation capture (`reference-current-development-machine-2026-09-04-104103.md`) independently revalidates Mesa 26.2.2 as the installed/active B580 driver and supersedes the older broad local-state record for current OS/package/source-tree facts.

## Device identity

```text
GPU index:          0
vendorID:           0x8086
deviceID:           0xe20b
deviceType:         PHYSICAL_DEVICE_TYPE_DISCRETE_GPU
deviceName:         Intel(R) Arc(tm) B580 Graphics (BMG G21)
apiVersion:         1.4.354
driverVersion:      26.2.2
driverID:           DRIVER_ID_INTEL_OPEN_SOURCE_MESA
driverName:         Intel open-source Mesa driver
driverInfo:         Mesa 26.2.2
conformanceVersion: 1.4.0.0
pipelineCacheUUID:  6b072dd5-3d62-8b32-8168-722fd60c1fb8
deviceUUID:         86800be2-0000-0000-0300-000000000000
driverUUID:         ffe06a92-7a02-f0b9-be4b-cdf916b0cba1
```

The capture also contains GPU1 llvmpipe. Capability extraction must remain device-scoped.

## Descriptor heap

B580 advertises:

```text
VK_EXT_descriptor_heap : extension revision 1
```

Features:

```text
descriptorHeap              = true
descriptorHeapCaptureReplay = true
```

Properties:

```text
samplerHeapAlignment                    64 B
resourceHeapAlignment                   64 B
maxSamplerHeapSize                      2 GiB
maxResourceHeapSize                     2 GiB
minSamplerHeapReservedRange             0 B
minSamplerHeapReservedRangeWithEmbedded 0 B
minResourceHeapReservedRange            0 B
samplerDescriptorSize                   32 B
imageDescriptorSize                     64 B
bufferDescriptorSize                    64 B
samplerDescriptorAlignment              32 B
imageDescriptorAlignment                64 B
bufferDescriptorAlignment               64 B
maxPushDataSize                         256 B
imageCaptureReplayOpaqueDataSize        8 B
maxDescriptorHeapEmbeddedSamplers       2048
samplerYcbcrConversionCount             3
sparseDescriptorHeaps                   true
protectedDescriptorHeaps                false
```

This closes the hardware-enumeration half of the descriptor-heap runtime gate.

## Existing descriptor-buffer support

B580 still reports:

```text
VK_EXT_descriptor_buffer
descriptorBuffer                   = true
descriptorBufferCaptureReplay      = true
descriptorBufferPushDescriptors    = true
descriptorBufferImageLayoutIgnored = false
descriptorBufferOffsetAlignment    = 64 B
```

This remains useful capability evidence, but ADR-045 / Baseline 036 does not require a descriptor-buffer implementation or comparator path.

## Required descriptor-heap dependencies observed

```text
bufferDeviceAddress  = true
shaderUntypedPointers = true
```

## Memory capability correction

Within the **GPU0 B580** device-extension/feature section, the capture does not advertise:

```text
VK_EXT_memory_priority
VK_EXT_pageable_device_local_memory
```

Those names/features occur only in the later llvmpipe GPU1 section of the same file.

Therefore B580 code must not require or enable those two extensions on this reference driver. Memory pressure behavior is based on:

```text
VK_EXT_memory_budget
project-owned residency classes
project-owned eviction/defer policy
```

## HDR/Wayland observation

Native Wayland still exposes HDR-capable color-space/format combinations including:

```text
VK_COLOR_SPACE_HDR10_ST2084_EXT
VK_FORMAT_A2R10G10B10_UNORM_PACK32
VK_FORMAT_A2B10G10R10_UNORM_PACK32
VK_FORMAT_R16G16B16A16_SFLOAT
```

Wayland reports MAILBOX, FIFO and IMMEDIATE present modes.

## Cache compatibility consequence

Mesa 26.2.2 reports a different driver/pipeline-cache identity from the prior 26.1.8 capture. Renderer cache keys must continue to include the driver/pipeline identity; no 26.1.8 pipeline binary/cache should be assumed reusable under 26.2.2.

## What this capture does not prove

It does not prove:

```text
Slang v2026.17 is installed
SPV_EXT_descriptor_heap shaders compile correctly in the project pipeline
validation-clean descriptor heap bind/write/read behavior in UFO:AI
descriptor-heap whole-frame performance/tuning under project workloads
```

Those remain architecture-087 qualification work.
