# Pass Data, Bindless Heap Registries and Shader-Binding ABI

**Status:** Exact implementation specification  
**Related ADR:** ADR-030, ADR-045  
**Related architecture:** 029, 052, 056, 059, 070, 089

## 1. Exact shader root

Architecture 056 owns the exact 32-byte `GpuShaderRoot`:

```text
sceneRootAddress
frameConstantsAddress
viewConstantsAddress
passDataAddress
```

The root is sent with descriptor-heap push data.

## 2. Root address sentinel

```text
0 = absent/unused BDA record
```

Production passes that require a record treat zero as validation failure.

## 3. Pass-data ABI

Each shader entry point declares exactly one statically known pass-data type.

`passDataAddress` points directly to that immutable record.

Optional validation header:

```cpp
struct GpuPassDataHeader {
    uint32_t abiTag;
    uint32_t sizeBytes;
    uint32_t flags;
    uint32_t reserved0;
};
static_assert(sizeof(GpuPassDataHeader) == 16);
```

## 4. Raster draw pass data

```cpp
struct GpuRasterDrawPassData {
    uint32_t drawDataIndex;
    uint32_t reserved0;
    uint32_t reserved1;
    uint32_t reserved2;
};
static_assert(sizeof(GpuRasterDrawPassData) == 16);
```

`drawDataIndex` indexes `GpuSceneRoot.drawData[]`.

## 5. Descriptor-heap handles in pass data

A pass that needs transient image/buffer resources stores typed heap indices in its pass-data record.

Rules:

```text
resource image/buffer handle != sampler handle
handle type is known statically by the consuming shader field
global persistent handles are never substituted with frame-local handles
frame-local handles are invalid after FrameContext retirement
0xffffffff is the generic invalid 32-bit heap-index sentinel where a field permits absence
```

Acceleration-structure handles follow architecture 089's exact 8-byte device-address-element handle contract and mandatory B580 conformance verification.

Resource-heap indices are **typed views of one byte-address heap**, not one interchangeable integer-slot namespace. Architecture 089 owns byte-range allocation and derives each typed index as `byteOffset / typedStride`, preventing image/buffer and acceleration-structure publications from overlapping despite their different strides.

## 6. Pass-data lifetime

Pass records are allocated from active FrameContext device-local/mapped upload-backed structured storage and remain valid until all queue work referencing that FrameContext retires.

## 7. BDA alignment

Minimum project ABI alignment:

```text
GpuShaderRoot-referenced record     16 bytes
structured-array base               16 bytes
GpuAffine3x4Rows array              16 bytes
FrameConstants                      16 bytes
ViewConstants                       16 bytes
GpuSceneRoot                        16 bytes
pass-data record                    16 bytes
```

Allocator uses the strongest applicable project/device/type requirement.

## 8. Global sampled-image capacity

ABI v1:

```text
sampledImages[65536]
```

Slots:

```text
0  white 1x1
1  black 1x1
2  flat tangent normal
3  default ORM
4..65535 streamed/content images
```

Invalid material texture index:

```text
0xffffffff
```

The material loader resolves missing optional textures to an appropriate fallback slot before GPU upload.

## 9. Global sampler capacity

ABI v1:

```text
samplers[256]
```

Sampler allocation is description-deduplicated. Sampler slots are process-lifetime stable and are not reordered/reused until renderer shutdown.

Invalid sampler index is forbidden in a GPU-visible material.

## 10. Sampled-image handle registry

Render owns the sampled-image heap registry.

A content image slot may be retired only after:

```text
asset strong references reach zero
all GpuMaterial references are removed/rebuilt
all FrameContexts that could reference the old slot retire
all upload/transfer ownership affecting the image retires
```

Only then may the numeric slot be reused.

## 11. Persistent publication rule

Architecture 070 is exact authority.

A content texture reaches `VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL` before persistent heap publication.

While live, asset/view identity, descriptor bytes and layout remain immutable.

Replacement uses a new slot plus retirement of old references/FrameContexts.

Layout-changing images use FrameContext resource-heap handles instead.

## 12. Frame/pass resource arena

Each FrameContext owns transient resource-heap allocation state under architecture 089.

The previous Set-1/Set-2 descriptor counts are no longer Vulkan layout ABI. Implementations still track per-pass/per-frame descriptor usage and enforce configured arena capacity with telemetry.

## 13. Overflow policy

Development:

```text
validation failure
capture requested bytes/type/pass/asset
fail affected pass/frame
```

Release:

```text
fatal presentation renderer capacity error
preserve canonical game state
```

Heap allocation size may be tuned between builds without changing the shader ABI when published indices remain valid.

## 14. ShaderBindingAbiHash256

Architecture 070 owns exact v2 serialization.

It covers the shader-visible binding contract rather than a Vulkan pipeline layout, because descriptor-heap pipelines use no pipeline layout object.

The hash includes at least:

```text
binding ABI version
descriptor-heap model identifier
Slang heap capability/stride mode
GpuShaderRoot size/version
global sampled-image capacity
global sampler capacity
handle sentinel/type conventions
TLAS heap-handle semantic version
```

## 15. Cache/package identity

`ShaderBindingAbiHash256` participates in:

```text
.rshader META
shader package content identity
pipeline description hash
VK_KHR_pipeline_binary cache key
debug capture build identity
RDGI cache identity where shader binding compatibility matters
```

Historical `PipelineLayoutAbiHash256` is superseded and never matches the descriptor-heap v2 binding domain.
