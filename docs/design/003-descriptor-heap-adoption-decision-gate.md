# Descriptor-Heap Adoption Decision

**Status:** Accepted  
**Decision baseline:** 036  
**Decision ID:** `DESCRIPTOR-HEAP-001`  
**Accepted choice:** descriptor heap from initial renderer implementation

## Decision

The owner explicitly selected `VK_EXT_descriptor_heap` as the production binding model **from the first renderer implementation**.

The previously recommended transitional choice—descriptor heap first while retaining descriptor buffer for A/B/fallback qualification—is superseded. The project will not spend implementation effort on a descriptor-buffer fallback solely for migration safety.

## Measured B580 basis

The developer-provided Arc B580 / Mesa 26.2.2 capture confirms:

```text
VK_EXT_descriptor_heap revision 1
descriptorHeap              = true
descriptorHeapCaptureReplay = true
max sampler heap            = 2 GiB
max resource heap           = 2 GiB
heap address alignment      = 64 B
sampler descriptor          = 32 B / 32 B alignment
image descriptor            = 64 B / 64 B alignment
buffer descriptor           = 64 B / 64 B alignment
max push data               = 256 B
sparse descriptor heaps     = true
shaderUntypedPointers       = true
bufferDeviceAddress         = true
```

## Result

```text
DESCRIPTOR-HEAP-001: ACCEPTED
production model:    VK_EXT_descriptor_heap
first implementation: descriptor heap
VK_EXT_descriptor_buffer fallback: NOT REQUIRED
```

Architecture 089 is the exact production binding authority. Architecture 087 now defines qualification rather than an adoption choice.
