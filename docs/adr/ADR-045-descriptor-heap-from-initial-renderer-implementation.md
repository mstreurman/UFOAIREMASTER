# ADR-045 — Descriptor Heap from Initial Renderer Implementation

**Status:** Accepted  
**Date:** 2026-09-04  
**Decision:** `DESCRIPTOR-HEAP-001`  
**Supersedes:** descriptor-buffer-first production policy in ADR-015 and architectures 013/056/061/070  
**Related:** ADR-047, architecture 087, architecture 089

## Decision

The remaster renderer uses `VK_EXT_descriptor_heap` from the first Vulkan renderer implementation.

There is no descriptor-buffer-first bring-up phase and no requirement to implement `VK_EXT_descriptor_buffer` as an A/B or fallback renderer path.

The B580 renderer therefore requires:

```text
VK_EXT_descriptor_heap
VkPhysicalDeviceDescriptorHeapFeaturesEXT::descriptorHeap = true
VK_KHR_shader_untyped_pointers
VkPhysicalDeviceShaderUntypedPointersFeaturesKHR::shaderUntypedPointers = true
Buffer Device Address / Vulkan 1.2+
Slang v2026.17 with spvDescriptorHeapEXT
```

The reference Arc B580 / Mesa 26.2.2 runtime satisfies the device-side feature gate.

## Binding model

Production shaders use the descriptor-heap model directly:

```text
one sampler heap
one resource heap
ResourceDescriptorHeap[index]
SamplerDescriptorHeap[index]
```

Production heap pipelines use no Vulkan descriptor-set layouts and no Vulkan pipeline layout object. Pipelines are created for descriptor-heap use and pass root data through the descriptor-heap push-data interface.

The existing four-address `GpuShaderRoot` remains the v1 root payload, but it is sent through `vkCmdPushDataEXT` rather than `vkCmdPushConstants`.

Large structured GPU arrays continue to use Buffer Device Address instead of consuming resource-heap descriptors unnecessarily.

## No descriptor-buffer fallback

`VK_EXT_descriptor_buffer` may still be:

```text
reported in capability diagnostics
used by external experiments/tools
mentioned in historical audits
```

It is not:

```text
a renderer requirement
a production binding path
a bring-up fallback
a compatibility path that must be maintained
```

If descriptor-heap conformance fails on the reference B580/driver/compiler stack, the failure blocks renderer bring-up and is diagnosed/fixed. The project does not silently switch to descriptor buffers.

## Qualification remains mandatory

Starting with descriptor heaps does not waive validation. Before content-scale rendering, implementation must pass:

```text
Slang SPV_EXT_descriptor_heap compile fixtures
spirv-val validation
minimal sampler/resource heap bind-write-read test
non-uniform indexing tests
sampled/storage image tests
buffer tests
RT acceleration-structure heap test
validation-layer clean execution
descriptor churn stress
capture/replay smoke test where practical
```

Performance measurement remains required for tuning, but no descriptor-buffer implementation is required merely to provide a comparator.

## Consequences

- shader/package ABI identity changes from descriptor-buffer layout identity to descriptor-heap binding identity;
- descriptor sets and pipeline layouts are removed from the production binding architecture;
- `vkCmdPushDataEXT` becomes the root-data command;
- frame/pass descriptor writers allocate typed slots from the bound heaps;
- all live documentation that still presents descriptor buffers as normative is superseded by architecture 089 and the Baseline-036 normalization.
