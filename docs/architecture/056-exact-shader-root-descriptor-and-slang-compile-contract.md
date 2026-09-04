# Exact Shader Root, Descriptor-Heap and Slang Compile Contract

**Status:** Exact implementation specification  
**Related ADR:** ADR-022, ADR-029, ADR-045, ADR-047  
**Related architecture:** 029, 059, 061, 087, 089

## 1. Compiler pin

Production shader packages are compiled with pinned:

```text
Slang v2026.17
```

Builds never follow an unpinned moving tag.

## 2. Required compile/session settings

`ufo-shaderc` configures:

```text
target                              SPIR-V
profile                             spirv_1_6
Vulkan target                       1.4
capability                          spvDescriptorHeapEXT
scalar block layout                 enabled
Vulkan memory model                 enabled
matrix layout                       COLUMN_MAJOR
SPIRVResourceHeapStride             0
SPIRVSamplerHeapStride              0
SPIRVUnifiedDescriptorHeapStride    enabled
optimization                        release package enabled
```

API path must explicitly set column-major matrix layout. Do not rely on the Slang default.

The unified resource stride mode is required for ordinary image/buffer heap handles. Architecture 087 owns compiler fixtures for acceleration-structure and non-uniform cases.

## 3. Matrix validation

A build test compiles a known matrix ABI fixture and verifies:

```text
column-major reflected layout
expected member offsets
CPU transform == Slang transform
```

Failure stops the shader/content build.

## 4. Exact push-data root

```cpp
struct GpuShaderRoot {
    uint64_t sceneRootAddress;
    uint64_t frameConstantsAddress;
    uint64_t viewConstantsAddress;
    uint64_t passDataAddress;
};

static_assert(sizeof(GpuShaderRoot) == 32);
```

Address sentinel:

```text
0 = absent/unused BDA record
```

The root is written at push-data offset zero with `vkCmdPushDataEXT`.

Do not use `vkCmdPushConstants` for production descriptor-heap pipelines.

## 5. Root semantics

```text
sceneRootAddress
    -> active FrameContext GpuSceneRoot

frameConstantsAddress
    -> active FrameContext FrameConstants

viewConstantsAddress
    -> selected ViewConstants for this pass/view

passDataAddress
    -> entry-point-specific immutable pass/draw record
```

Architecture 061 owns pass-data lifetime/typing.

## 6. Root lifetime

For FrameContext `N`:

```text
GpuSceneRoot[N]
FrameConstants[N]
ViewConstants[N][...]
pass records[N][...]
```

remain immutable until all queue uses of FrameContext `N` retire.

## 7. Descriptor heaps

Production shader resource access uses:

```text
ResourceDescriptorHeap[index]
SamplerDescriptorHeap[index]
```

There are no production descriptor-set numbers or binding numbers for direct-heap resources.

The command buffer binds one resource heap and one sampler heap under architecture 089.

## 8. Persistent capacities

ABI-v1 capacities remain:

```text
sampledImages[65536]
samplers[256]
```

These are logical registry capacities, not Vulkan descriptor-set array sizes.

A device that cannot support the fixed remaster heap ABI fails the renderer capability contract; ABI v1 is not silently shrunk.

## 9. Frame/pass resources

Frame- and pass-local image/buffer descriptors are allocated from the active FrameContext's resource-heap arena.

The old fixed Set-1/Set-2 binding numbers are not part of the descriptor-heap ABI.

Pass-data structs carry typed heap indices when a shader needs transient descriptors. Large structured data should remain BDA-rooted when that is the simpler/faster representation.

## 10. TLAS

The active FrameContext TLAS is addressed by the typed heap index stored in:

```text
GpuSceneRoot.frameTlasHeapIndex
```

Architecture 059 owns the exact root field; architecture 089 fixes acceleration-structure heap handles to 8-byte device-address-element units and architecture 087 requires conformance verification before RT production use.

## 11. Image layouts

Heap image descriptor creation includes the exact `VkImageLayout` used for access.

Persistent material textures normally remain:

```text
VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
```

Transient image descriptors are regenerated/published according to the Frame Graph's resolved pass layout.

## 12. BDA arrays

Large structured scene arrays are reached through `GpuSceneRoot` device addresses.

Do not allocate a heap descriptor for an array merely because a shader consumes it.

## 13. SBT

SBT records remain minimal and do not embed:

```text
materials
object structs
frame constants
large pass payloads
```

Raygen/miss/hit shaders use the same push-data root and heap ABI.

## 14. Reflection / SPIR-V validation

Normalized shader metadata validates:

```text
uses descriptor heap when expected
required SPV_EXT_descriptor_heap / untyped-pointer capabilities
32-byte push-data root contract
matrix layout
shader-visible struct sizes/offsets
resource handle family/type
source-level non-uniform indexing semantics where required by Slang/HLSL
absence of unintended DescriptorSet/Binding decorations on direct-heap resources
```

With `DescriptorHeapEXT` declared in SPIR-V, Vulkan treats heap resource access as non-uniform by default, so the final SPIR-V is **not required** to carry a `NonUniform` decoration. High-level Slang/HLSL semantics are unchanged: divergent heap indices must still be expressed with the appropriate source-level non-uniform construct (for example `NonUniformResourceIndex`) so the compiler does not assume uniform access or add `Uniform`/`UniformId` semantics incorrectly. Validation tests therefore check behavior and emitted heap semantics, not the mere presence of a `NonUniform` decoration.

Any mismatch with architecture 057/059/061/070/089 is a build error.

## 15. Persistent handle authority

Architecture 061 owns sampled-image/sampler handle allocation, retirement, reuse, overflow and `ShaderBindingAbiHash256`.

Global material texture/sampler handles may not be reused using ordinary FrameContext transient-heap rules.
