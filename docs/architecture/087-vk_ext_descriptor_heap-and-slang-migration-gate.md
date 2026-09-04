# `VK_EXT_descriptor_heap` and Slang Qualification Contract

**Status:** Accepted implementation qualification contract  
**Related ADR:** ADR-045, ADR-047  
**Decision:** `DESCRIPTOR-HEAP-001` accepted in Baseline 036

## 1. Accepted architecture

`VK_EXT_descriptor_heap` is the binding model from the first renderer implementation.

This document no longer gates adoption and no longer requires a descriptor-buffer comparator. Architecture 089 owns the exact production heap ABI.

## 2. Verified capability basis

The developer-provided Mesa 26.2.2 Arc B580 capture reports:

```text
VK_EXT_descriptor_heap revision 1

descriptorHeap              = true
descriptorHeapCaptureReplay = true

samplerHeapAlignment        = 64 B
resourceHeapAlignment       = 64 B
maxSamplerHeapSize          = 2 GiB
maxResourceHeapSize         = 2 GiB
samplerDescriptorSize       = 32 B
imageDescriptorSize         = 64 B
bufferDescriptorSize        = 64 B
samplerDescriptorAlignment  = 32 B
imageDescriptorAlignment    = 64 B
bufferDescriptorAlignment   = 64 B
maxPushDataSize             = 256 B
sparseDescriptorHeaps       = true
protectedDescriptorHeaps    = false

bufferDeviceAddress         = true
shaderUntypedPointers       = true
```

Every runtime check is scoped to vendorID `0x8086` / deviceID `0xe20b`; llvmpipe values are never substituted.

## 3. Slang conformance gate

Pinned Slang v2026.17 must compile SPIR-V 1.6 / Vulkan 1.4 fixtures with `spvDescriptorHeapEXT` and validate:

```text
ResourceDescriptorHeap[] direct indexing
SamplerDescriptorHeap[] direct indexing
sampled image recovery
storage image recovery
sampler recovery
uniform/structured/storage buffer recovery
RT acceleration-structure access
combined texture/sampler handle behavior where used
source-level non-uniform resource indexing semantics
unified image/buffer resource-heap stride mode
8-byte direct acceleration-structure address-element lowering
reflection metadata identifies heap use
no DescriptorSet/Binding decorations for direct-heap resources
column-major ABI invariants unchanged
```

`DescriptorHeapEXT` changes SPIR-V non-uniform rules: heap accesses are non-uniform by default and final SPIR-V does not need a `NonUniform` decoration. The source fixture must still mark divergent Slang/HLSL indices appropriately; validation checks correct behavior and absence of an incorrect uniform assumption rather than requiring a particular decoration token.

The Fedora 44 reference installation currently uses SPIR-V Tools 2026.1. Its executed DescriptorHeapEXT fixture passes `spirv-val --target-env vulkan1.4`, but this packaged validator does not expose the newer explicit `--buffer-descriptor-layout`, `--image-descriptor-layout`, and `--sampler-descriptor-layout` command-line switches. Therefore those switches are optional supplemental validation when a newer validator providing them is used; they are not an M0 prerequisite.

The measured B580 values remain authoritative inputs to the native heap qualification:

```text
buffer descriptor size/alignment: 64:64
image descriptor size/alignment:  64:64
sampler descriptor size/alignment: 32:32
```

These values come from the Mesa 26.2.2 B580 capability capture. A future qualified device uses its own queried size/alignment values. The native Vulkan fixture must prove descriptor writes/reads against the queried runtime layout. The selected Slang direct-AS path uses a raw 64-bit address element, so its 8-byte typed array stride is validated by the emitted module/RT fixture and must not be confused with Vulkan's opaque acceleration-structure descriptor layout parameter.

Known compiler/driver edge cases are treated as bring-up defects to isolate and resolve. Architecture 089 fixes the acceleration-structure heap ABI; the fixture verifies rather than selects it. Failures do not authorize silent descriptor-buffer fallback.

## 4. Vulkan execution/validation gate

Before large renderer subsystems depend on the heaps, pass a minimal native test that:

```text
creates sampler/resource heap buffers
uses VK_BUFFER_USAGE_DESCRIPTOR_HEAP_BIT_EXT
uses VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT
writes sampler descriptors with vkWriteSamplerDescriptorsEXT
writes resource descriptors with vkWriteResourceDescriptorsEXT
binds sampler heap with vkCmdBindSamplerHeapEXT
binds resource heap with vkCmdBindResourceHeapEXT
pushes GpuShaderRoot-compatible data with vkCmdPushDataEXT
executes sampled/storage/buffer reads and writes
runs clean under VK_LAYER_KHRONOS_validation
survives repeated descriptor publication/retirement churn
```

The RT fixture additionally proves the exact Slang/Vulkan acceleration-structure heap representation used by architecture 089 before the production TLAS handle is enabled.

## 5. Benchmarking role

Benchmarking now tunes the heap implementation rather than deciding whether to adopt it.

Measure at least:

```text
CPU descriptor generation/publication cost
command recording cost
GPU frame time
RT shadow/reflection/DDGI timings
raster material-heavy scenes
streaming churn
resource-heap locality
validation overhead
1% / 0.1% frame-time tails
```

Possible tuning changes include heap allocation size, region placement, publication batching and host-write strategy. None of those measurements require a second production descriptor-buffer renderer.

## 6. Cache/ABI rule

Descriptor-heap shader/package identity is distinct from every historical descriptor-buffer package.

No descriptor-buffer `.rshader` package, pipeline binary, binding hash or descriptor serialization is reusable merely because source-level resource declarations look similar.
