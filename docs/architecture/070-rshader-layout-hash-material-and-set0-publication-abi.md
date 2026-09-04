# `.rshader` Binding Hash, Material ABI and Persistent-Heap Publication Contract

**Status:** Exact implementation specification  
**Related ADR:** ADR-022, ADR-030, ADR-031, ADR-045  
**Related architecture:** 018, 029, 056, 061, 066, 089

## 1. ShaderBindingAbiHash v2 domain

```text
UFOAIREMASTER:ShaderBindingABI:v2\0
```

The historical `PipelineLayoutAbiHash256` v1 domain is superseded by descriptor-heap binding ABI v2.

## 2. Canonical binding serialization

All integers are little-endian `uint32` unless stated otherwise.

```text
domainPrefix

u32 bindingAbiVersion = 2
u32 bindingModel = 1              # 1 = VK_EXT_descriptor_heap
u32 rootSizeBytes = 32
u32 rootVersion = 1

u32 sampledImageCapacity = 65536
u32 samplerCapacity = 256
u32 invalidHandle = 0xffffffff
u32 tlasHandleSemanticVersion = 1

u32 slangSpvDescriptorHeapEXT = 1
u32 unifiedResourceHeapStride = 1
u32 explicitResourceStrideBytes = 0
u32 explicitSamplerStrideBytes = 0

u32 reserved[8] = {0}
```

No native padding participates.

The descriptor byte sizes reported by one driver are **not** serialized into this cross-build shader ABI hash because the production Slang mode uses descriptor-heap size/stride semantics rather than hard-coded B580 descriptor bytes. Device/driver identity remains a separate pipeline-binary compatibility input.

## 3. Hash

```text
ShaderBindingAbiHash256 =
    BLAKE3-256(canonicalBindingStream)
```

## 4. `.rshader` META v2 record

String fields are indices into the package `NAME` string table.

```cpp
struct RshaderMetaV2 {
    uint32_t shaderPackageVersion;
    uint32_t rendererShaderAbiVersion;
    uint32_t metaVersion;
    uint32_t slangVersionStringIndex;

    uint32_t shadercBuildIdStringIndex;
    uint32_t spirvTargetStringIndex;
    uint32_t vulkanTargetStringIndex;
    uint32_t reserved0;

    uint8_t shaderBindingAbiHash[32];

    uint64_t requiredCapabilityBits;

    uint8_t reserved[24];
};
static_assert(sizeof(RshaderMetaV2) == 96);
```

```text
metaVersion = 2
reserved0 = 0
reserved[] = 0
```

Capability bits v2:

```text
0 DescriptorHeap
1 BufferDeviceAddress
2 DynamicRendering
3 Synchronization2
4 ScalarBlockLayout
5 VulkanMemoryModel
6 AccelerationStructure
7 RayTracingPipeline
8 RayQuery
9 SubgroupSizeControl
10 PipelineBinary
11 ShaderUntypedPointers
12..63 reserved
```

The outer `.r*` `ContentHash256` remains package content identity.

## 5. Pipeline binary identity

Includes:

```text
outer .rshader ContentHash256
ShaderBindingAbiHash256
pipeline description hash
device/driver identity
pipeline global key
renderer build ID
```

A historical descriptor-buffer pipeline binary is incompatible.

## 6. MaterialClass ABI v1

```cpp
enum class MaterialClass : uint32_t {
    StandardPbr = 0,
    Unlit       = 1,
    Glass       = 2,
    Water       = 3,
    Decal       = 4
};
```

Other values are reserved/invalid.

## 7. MaterialFlags ABI v1

```cpp
enum MaterialFlags : uint32_t {
    Material_AlphaMask          = 1u << 0,
    Material_AlphaBlend         = 1u << 1,
    Material_DoubleSided        = 1u << 2,
    Material_CastsShadow        = 1u << 3,
    Material_RtVisible          = 1u << 4,
    Material_ReflectionEligible = 1u << 5,
    Material_GiEligible         = 1u << 6,
    Material_Emissive           = 1u << 7,
    Material_ReceivesDecals     = 1u << 8
};
```

Bits 9..31 are reserved zero. AlphaMask and AlphaBlend are mutually exclusive.

## 8. Persistent sampled-image publication

Publication:

```text
create image/view
upload baseline mips
perform transfer/layout transitions
reach VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
create descriptor bytes with vkWriteResourceDescriptorsEXT
copy/write descriptor to persistent sampled-image heap slot
publish numeric handle
```

While live:

```text
image remains SHADER_READ_ONLY_OPTIMAL
asset/view identity is unchanged
published descriptor bytes are unchanged
```

## 9. Replacement/retirement

To replace identity/view:

```text
allocate new heap slot
publish new references
retire old references
wait all referencing FrameContexts
retire old descriptor/image
optionally reuse numeric slot
```

Do not rewrite a live persistent slot while an older frame may consume it.

## 10. Layout-changing images

Images changing layout during ordinary frame operation use FrameContext transient resource-heap handles generated from the exact Frame Graph-derived access layout.

## 11. Baseline mip streaming

Baseline resident mip set exists before persistent publication.

Future sparse/partial residency requires a separate architecture change.

## 12. Memory-pressure publication rule

Architecture 074 owns texture-residency pressure behavior.

A live persistent texture keeps the same asset/view identity and stable descriptor publication until established retirement conditions are satisfied.
