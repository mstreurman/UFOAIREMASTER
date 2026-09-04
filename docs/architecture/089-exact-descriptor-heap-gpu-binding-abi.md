# Exact Descriptor-Heap GPU Binding ABI

**Status:** Exact implementation specification  
**Related ADR:** ADR-015, ADR-045, ADR-047  
**Supersedes:** production descriptor-buffer binding details in architecture 013  
**Related architecture:** 012, 029, 052, 056, 059, 061, 070, 087

## 1. Production rule

The renderer is descriptor-heap-native from its first implementation.

Exactly two descriptor-heap address ranges are bound for production graphics/compute/RT work:

```text
SamplerHeap
ResourceHeap
```

There are no production Vulkan descriptor sets and no production Vulkan pipeline layout object for heap pipelines.

## 2. Required device/compiler features

Require on the selected Arc B580 device:

```text
VK_EXT_descriptor_heap revision >= 1
descriptorHeap = true
VK_KHR_shader_untyped_pointers
shaderUntypedPointers = true
bufferDeviceAddress = true
Vulkan device API >= 1.4
```

Shaders are compiled by pinned Slang v2026.17 with:

```text
SPIR-V 1.6
Vulkan 1.4
spvDescriptorHeapEXT
SPIRVResourceHeapStride = 0
SPIRVSamplerHeapStride = 0
SPIRVUnifiedDescriptorHeapStride = true
column-major matrices
scalar block layout
Vulkan memory model
```

The unified-resource-stride mode applies to image/buffer resource handles. Acceleration-structure handles use Slang's distinct `spvDescriptorHeapEXT` lowering: the heap element is a 64-bit acceleration-structure device address, the default SPIR-V `ArrayStride` is 8 bytes, and dereference converts that address with `OpConvertUToAccelerationStructureKHR`. `SPIRVUnifiedDescriptorHeapStride` does not alter acceleration-structure entries.

## 3. Reference B580 heap properties

Measured Mesa 26.2.2 values:

```text
samplerHeapAlignment       = 64 B
resourceHeapAlignment      = 64 B
maxSamplerHeapSize         = 2 GiB
maxResourceHeapSize        = 2 GiB
samplerDescriptorSize      = 32 B
imageDescriptorSize        = 64 B
bufferDescriptorSize       = 64 B
samplerDescriptorAlignment = 32 B
imageDescriptorAlignment   = 64 B
bufferDescriptorAlignment  = 64 B
maxPushDataSize            = 256 B
sparseDescriptorHeaps      = true
```

For ordinary image/buffer heap indexing on the reference GPU:

```text
UnifiedResourceStride = max(imageDescriptorSize, bufferDescriptorSize) = 64 B
SamplerStride         = samplerDescriptorSize = 32 B
```

Production code queries and validates the properties instead of blindly assuming the reference values.

## 4. Heap buffers

Each heap is backed by a Vulkan buffer created with at least:

```text
VK_BUFFER_USAGE_DESCRIPTOR_HEAP_BIT_EXT
VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT
```

On the reference B580, prefer the device-local + host-visible + host-coherent memory type so descriptor publication can write mapped heap memory directly.

The heap manager still supports staging/copy internally if a future qualified device requires it, but the B580 path is direct mapped publication.

Heap buffer addresses and sizes satisfy the queried sampler/resource heap alignment and maximum-size rules.

Do **not** assume the base device address returned for a descriptor-heap buffer is automatically aligned to the heap-address requirement. The allocator over-allocates enough addressable buffer range to select an aligned `VkBindHeapInfoEXT.heapRange.address` explicitly:

```text
rawBase       = vkGetBufferDeviceAddress(...)
heapBase      = align_up(rawBase, requiredHeapAlignment)
heapBaseDelta = heapBase - rawBase
```

The selected `[heapBase, heapBase + heapRange.size)` must remain wholly inside the descriptor-heap buffer device-address range. Direct mapped host writes add `heapBaseDelta` to the mapped base pointer. This avoids depending on stronger implicit buffer-device-address alignment than the Vulkan contract guarantees.

Implementation-reserved ranges passed in `VkBindHeapInfoEXT` are never allocated by the application. To preserve stable heap index zero semantics, any required implementation reservation is placed at the **tail** of the bound heap range:

```text
application range: [0, reservedRangeOffset)
reserved range:    [reservedRangeOffset, reservedRangeOffset + reservedRangeSize)
```

The runtime obeys the queried minimum reservation requirements. On the measured B580 all reported minimum reserved ranges are zero, so the baseline bind may use a zero-sized reserved tail.

## 5. Command-buffer binding

At the start of each primary graphics/compute command buffer that uses heap pipelines:

```text
vkCmdBindSamplerHeapEXT
vkCmdBindResourceHeapEXT
```

The renderer does not issue non-heap descriptor binding commands afterward. Recording a non-heap binding command is a developer validation failure because it can invalidate heap state.

Secondary command-buffer policy must preserve the same bound-heap contract and is validated before broad parallel command recording is enabled.

## 6. Root data

The existing v1 root remains:

```cpp
struct GpuShaderRoot {
    uint64_t sceneRootAddress;
    uint64_t frameConstantsAddress;
    uint64_t viewConstantsAddress;
    uint64_t passDataAddress;
};
static_assert(sizeof(GpuShaderRoot) == 32);
```

It is sent at push-data offset zero using:

```text
vkCmdPushDataEXT
```

not `vkCmdPushConstants`.

The 32-byte root fits within the B580 `maxPushDataSize = 256` limit and leaves the remaining push-data space available for future explicitly versioned root additions without changing the v1 root struct.

## 7. Persistent sampler heap registry

ABI-v1 logical sampler capacity remains:

```text
samplers[256]
```

For the reference B580, slot `i` begins at:

```text
samplerByteOffset = i * 32
```

The application-visible heap begins at byte offset zero; any implementation reservation is at the heap tail. Therefore logical sampler index 0 is always the first application sampler slot.

Slots are description-deduplicated and process-lifetime stable. Slots are not reordered/reused until renderer shutdown.

Sampler descriptor bytes are produced with `vkWriteSamplerDescriptorsEXT`.

## 8. Persistent sampled-image registry

ABI-v1 global sampled-image capacity remains:

```text
sampledImages[65536]
```

The registry occupies a stable image/buffer-unified-stride region of the resource heap.

For the B580:

```text
resource image slot stride = 64 B
resourceByteOffset(i)      = i * 64
slot 0..65535              = persistent sampled-image registry
registry bytes             = 4,194,304 B (4 MiB)
```

Fallback meanings remain:

```text
0 white 1x1
1 black 1x1
2 flat tangent normal
3 default ORM
4..65535 streamed/content images
```

A texture is published only after it has reached its stable shader-read layout. The live slot is immutable until retirement.

Image descriptor bytes are generated with `vkWriteResourceDescriptorsEXT` using the exact image layout that the shader will access.

## 9. Frame/pass resource heap arena

Resources that can change layout or identity per frame/pass are not placed in the persistent sampled-image registry.

Each FrameContext owns a resource-heap arena allocator over application-owned resource-heap bytes outside persistent ranges.

The arena creates typed handles for:

```text
frame sampled images
frame storage images
frame buffer descriptors when BDA is not the better representation
pass sampled images
pass storage images
pass buffer descriptors when required
FrameContext TLAS typed heap handle
```

Image/buffer handles use the unified Slang resource-heap stride mode. Large structured scene arrays continue to use BDA through `GpuSceneRoot` and do not consume heap slots merely for convenience.

### 9.1 One byte-address allocation domain, typed index views

The resource heap is one application-owned **byte-address allocation domain**. It is not a single universal integer-slot namespace because different statically typed Slang heap views may have different strides. In particular, image/buffer handles use the unified image/buffer stride while the selected direct acceleration-structure path uses 8-byte `uint64_t` elements.

Every resource-heap publication first reserves a non-overlapping byte range:

```text
[byteOffset, byteOffset + allocationBytes)
```

Then the typed shader index is derived from that byte offset:

```text
require byteOffset % typedStride == 0
typedHeapIndex = byteOffset / typedStride
```

For the reference B580:

```text
image/buffer typedStride = 64 B
AS direct-address typedStride = 8 B
```

The persistent sampled-image registry therefore reserves resource-heap bytes `[0, 4 MiB)`. Frame/pass allocation begins outside all persistent ranges and outside any implementation-reserved tail. An AS entry cannot overlap those bytes merely because its numeric typed index is computed in 8-byte units.

Rules:

```text
no universal resource-slot counter across image/buffer/AS types
byte ranges never overlap while either publication can be referenced
allocation alignment >= the static typed view stride/alignment requirement
numeric heap indices are interpreted only with their shader-static resource type
retirement/reuse follows the owning persistent or FrameContext lifetime
```

This byte-domain rule is runtime allocation policy, not a driver-specific cross-build ABI constant. Descriptor sizes/alignments remain queried device properties; the B580 values above are the qualification profile.

Per-pass arenas are reset only after the owning FrameContext retires.

## 10. TLAS handle

`GpuSceneRoot.reserved0` is promoted to:

```text
frameTlasHeapIndex
```

without changing the 160-byte `GpuSceneRoot` size.

It is a typed Slang descriptor-heap index for `RaytracingAccelerationStructure`, valid only for the active FrameContext.

For pinned Slang v2026.17 with `spvDescriptorHeapEXT`, acceleration structures use a distinct address-element representation. The shader heap element is a 64-bit acceleration-structure device address, the default SPIR-V array stride is 8 bytes, and dereference converts it with `OpConvertUToAccelerationStructureKHR`. `SPIRVUnifiedDescriptorHeapStride` does not change this AS stride.

Therefore the v1 handle unit is exact:

```text
asByteOffset = uint64(frameTlasHeapIndex) * 8
```

The published 64-bit value is the address returned by `vkGetAccelerationStructureDeviceAddressKHR` for the active FrameContext TLAS.

Before RT production code is enabled, architecture 087 requires a compile/runtime fixture that verifies this accepted representation:

```text
Slang emits SPV_EXT_descriptor_heap with 8-byte AS ArrayStride
OpConvertUToAccelerationStructureKHR is present on dereference
spirv-val passes for Vulkan 1.4
published value equals vkGetAccelerationStructureDeviceAddressKHR(TLAS)
B580 TraceRay/ray-query known-triangle smoke test succeeds
validation layers remain clean
```

The fixture verifies the implementation helper; it no longer chooses the ABI. If the pinned compiler/driver fails this contract, RT heap bring-up is blocked for diagnosis/fix. There is no descriptor-buffer fallback.

## 11. Descriptor publication API

The renderer exposes typed publication operations rather than exposing raw heap byte writes to arbitrary systems:

```text
publishSampler(...)
publishSampledImage(...)
publishStorageImage(...)
publishUniformBuffer(...)
publishStorageBuffer(...)
publishAccelerationStructure(...)
retireHandle(...)
```

Sampler descriptors are created with `vkWriteSamplerDescriptorsEXT`.

Image/buffer/resource descriptors use `vkWriteResourceDescriptorsEXT`. The Slang direct-AS heap path is the explicit exception: it publishes the 64-bit acceleration-structure device address at the architecture-089 AS byte offset and validates that lowering with the mandatory fixture.

All publication is owned by the Render thread/heap manager and obeys FrameContext retirement.

## 12. Handle lifetime

Persistent content handles are stable while any GPU-visible material/object can reference them.

A handle may be reused only after:

```text
asset references are gone
all GPU scene/material references are rebuilt or retired
all FrameContexts that could consume the old handle retire
all transfer/upload ownership affecting the resource retires
```

Frame/pass handles have FrameContext lifetime and are never exposed as process-lifetime asset IDs.

## 13. Overflow

No heap grows or changes binding ABI silently during a frame.

Development overflow:

```text
validation failure
record requested bytes/type/pass/asset
fail affected pass/frame
```

Release overflow:

```text
fatal presentation-renderer capacity error
canonical game state remains intact
```

Physical heap allocation size is an implementation/tuning parameter and may increase between builds without changing shader ABI as long as all published indices and reserved regions remain valid.

## 14. Pipeline creation

Every production Vulkan pipeline that consumes heap resources is created with `VK_PIPELINE_CREATE_2_DESCRIPTOR_HEAP_BIT_EXT` and uses a null pipeline layout.

The renderer does not construct descriptor-set layouts solely for production heap shaders.

## 15. ABI/cache identity

Architecture 070 defines `ShaderBindingAbiHash256` v2.

The hash identifies at least:

```text
descriptor-heap binding model
spvDescriptorHeapEXT requirement
unified image/buffer resource stride mode
sampler/resource handle ABI version
persistent sampled-image capacity 65536
persistent sampler capacity 256
GpuShaderRoot size/version
TLAS heap-handle semantic version
```

A historical descriptor-buffer package is incompatible by definition.
