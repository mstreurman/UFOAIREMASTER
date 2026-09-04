# Exact Frame Graph API

**Status:** Implementation specification baseline  
**Related ADR:** ADR-016  
**Target:** Vulkan 1.4 / Intel Arc B580

## 1. Namespace

```cpp
namespace ufo::render::fg {
    // Frame Graph API
}
```

## 2. Typed logical handles

Logical Frame Graph resources are small opaque typed IDs.

```cpp
struct ImageHandle {
    uint32_t id = UINT32_MAX;
};

struct BufferHandle {
    uint32_t id = UINT32_MAX;
};

struct AccelHandle {
    uint32_t id = UINT32_MAX;
};

struct PassHandle {
    uint32_t id = UINT32_MAX;
};
```

No implicit conversion exists among handle types.

These handles identify logical graph resources, not Vulkan objects.

## 3. Queue and pass classes

```cpp
enum class QueueClass : uint8_t {
    Graphics,
    Transfer,
    AsyncCompute
};

enum class PassClass : uint8_t {
    Raster,
    Compute,
    RayTracing,
    AccelBuild,
    Transfer
};
```

`AsyncCompute` exists in the API but is disabled by default on the B580 baseline.

## 4. Shader-stage mask

```cpp
enum class ShaderStage : uint32_t {
    None       = 0,
    Vertex     = 1u << 0,
    Fragment   = 1u << 1,
    Compute    = 1u << 2,
    RayTracing = 1u << 3,
    Task       = 1u << 4,
    Mesh       = 1u << 5
};
```

`RayTracing` represents the RT pipeline shader-stage synchronization domain.

## 5. Resource descriptions

### Images

```cpp
struct ImageDesc {
    VkFormat format;

    VkExtent3D extent;

    uint32_t mipLevels = 1;
    uint32_t arrayLayers = 1;

    VkSampleCountFlagBits samples = VK_SAMPLE_COUNT_1_BIT;

    VkImageCreateFlags createFlags = 0;
};
```

The graph infers required `VkImageUsageFlags` from declared accesses.

### Buffers

```cpp
enum class BufferFlags : uint32_t {
    None          = 0,
    DeviceAddress = 1u << 0
};

struct BufferDesc {
    VkDeviceSize size;
    VkDeviceSize alignment = 1;

    BufferFlags flags = BufferFlags::None;
};
```

The graph infers required `VkBufferUsageFlags` from declared accesses.

### Acceleration structures

```cpp
enum class AccelType : uint8_t {
    BottomLevel,
    TopLevel
};

struct AccelDesc {
    AccelType type;
    VkDeviceSize storageSize;
};
```

Build geometry/range information remains pass-owned command data; the graph owns only resource dependencies and state.

## 6. Resource ranges

### Image range

```cpp
struct ImageRange {
    VkImageAspectFlags aspects;

    uint32_t baseMipLevel;
    uint32_t levelCount;

    uint32_t baseArrayLayer;
    uint32_t layerCount;

    static ImageRange allColor();
    static ImageRange allDepth();
};
```

### Buffer range

```cpp
struct BufferRange {
    VkDeviceSize offset;
    VkDeviceSize size;

    static BufferRange whole();
};
```

The compiler creates dependencies only when ranges overlap.

## 7. Image access vocabulary

```cpp
enum class ImageAccess : uint8_t {
    SampledRead,

    StorageRead,
    StorageWrite,
    StorageReadWrite,

    ColorAttachment,

    DepthStencilRead,
    DepthStencilWrite,

    TransferSrc,
    TransferDst,

    Present
};
```

## 8. Buffer access vocabulary

```cpp
enum class BufferAccess : uint8_t {
    VertexRead,
    IndexRead,
    IndirectRead,
    UniformRead,

    StorageRead,
    StorageWrite,
    StorageReadWrite,

    TransferSrc,
    TransferDst,

    AccelBuildInputRead,
    AccelScratchReadWrite,

    ShaderBindingTableRead
};
```

## 9. Acceleration-structure access vocabulary

```cpp
enum class AccelAccess : uint8_t {
    BuildRead,
    BuildWrite,

    ShaderRead,

    CopyRead,
    CopyWrite
};
```

`ShaderRead` also specifies the invoking shader stage mask so exceptional RayQuery consumers can be represented without changing the model.

## 10. Attachment declarations

```cpp
enum class LoadOp : uint8_t {
    Load,
    Clear,
    DontCare
};

enum class StoreOp : uint8_t {
    Store,
    DontCare
};

struct ColorAttachmentDesc {
    LoadOp loadOp;
    StoreOp storeOp;
    VkClearColorValue clearValue;
};

struct DepthAttachmentDesc {
    LoadOp loadOp;
    StoreOp storeOp;
    VkClearDepthStencilValue clearValue;
    bool readOnly = false;
};
```

## 11. Graph construction

```cpp
class FrameGraphBuilder {
public:
    ImageHandle createImage(
        std::string_view name,
        const ImageDesc& desc);

    BufferHandle createBuffer(
        std::string_view name,
        const BufferDesc& desc);

    AccelHandle createAccel(
        std::string_view name,
        const AccelDesc& desc);

    ImageHandle importImage(
        std::string_view name,
        const ImportedImage& image);

    BufferHandle importBuffer(
        std::string_view name,
        const ImportedBuffer& buffer);

    AccelHandle importAccel(
        std::string_view name,
        const ImportedAccel& accel);

    template<typename PassData, typename SetupFn, typename ExecuteFn>
    PassHandle addPass(
        std::string_view name,
        PassClass passClass,
        QueueClass queue,
        SetupFn&& setup,
        ExecuteFn&& execute);

    void present(ImageHandle swapchainImage);
};
```

## 12. Pass builder

The setup callback receives:

```cpp
class PassBuilder {
public:
    void read(
        ImageHandle image,
        ImageAccess access,
        ShaderStage stages = ShaderStage::None,
        ImageRange range = defaultRange);

    void write(
        ImageHandle image,
        ImageAccess access,
        ShaderStage stages = ShaderStage::None,
        ImageRange range = defaultRange);

    void readWrite(
        ImageHandle image,
        ImageAccess access,
        ShaderStage stages,
        ImageRange range = defaultRange);

    void read(
        BufferHandle buffer,
        BufferAccess access,
        ShaderStage stages = ShaderStage::None,
        BufferRange range = BufferRange::whole());

    void write(
        BufferHandle buffer,
        BufferAccess access,
        ShaderStage stages = ShaderStage::None,
        BufferRange range = BufferRange::whole());

    void readWrite(
        BufferHandle buffer,
        BufferAccess access,
        ShaderStage stages,
        BufferRange range = BufferRange::whole());

    void read(
        AccelHandle accel,
        AccelAccess access,
        ShaderStage stages = ShaderStage::None);

    void write(
        AccelHandle accel,
        AccelAccess access);

    void colorAttachment(
        uint32_t slot,
        ImageHandle image,
        const ColorAttachmentDesc& desc,
        ImageRange range = defaultColorRange);

    void depthAttachment(
        ImageHandle image,
        const DepthAttachmentDesc& desc,
        ImageRange range = defaultDepthRange);

    void dependsOn(PassHandle pass);
};
```

The `read`/`write` form must agree with the semantic access type.

Examples:

```text
ImageAccess::SampledRead      -> read
ImageAccess::StorageWrite     -> write
ImageAccess::StorageReadWrite -> readWrite

BufferAccess::AccelBuildInputRead -> read
BufferAccess::AccelScratchReadWrite -> readWrite

AccelAccess::BuildWrite -> write
AccelAccess::ShaderRead -> read
```

Invalid combinations are compile-time graph-validation errors.

## 13. Raster attachment behavior

`colorAttachment()` declares:

```text
ImageAccess::ColorAttachment
```

and records Dynamic Rendering attachment metadata.

`depthAttachment()` declares either:

```text
DepthStencilWrite
```

or:

```text
DepthStencilRead
```

depending on `readOnly`.

The Frame Graph automatically performs:

```text
vkCmdBeginRendering
execute callback
vkCmdEndRendering
```

for a Raster pass.

The callback records draws and dynamic state only.

## 14. Pass callback

Conceptual:

```cpp
template<typename PassData>
using Execute = void (*)(
    const PassData&,
    PassContext&);
```

`PassContext` exposes resolved physical resources:

```cpp
class PassContext {
public:
    VkCommandBuffer commandBuffer() const;

    const ResolvedImage& image(ImageHandle) const;
    const ResolvedBuffer& buffer(BufferHandle) const;
    const ResolvedAccel& accel(AccelHandle) const;

    PassHeapWriter& heap();

    const FrameContext& frame() const;
    const GpuSceneRoot& scene() const;

    void intraPassBarrier(const VkDependencyInfo&);
};
```

`intraPassBarrier` is only for dependencies inside the pass that stay compatible with the pass's declared final resource state.

## 15. Descriptor-heap publication

`ResolvedImage` contains the layout assigned to that image range for the current pass.

```cpp
struct ResolvedImage {
    VkImage image;
    VkImageView view;
    VkImageLayout layout;
    VkExtent3D extent;
    VkFormat format;
};
```

A pass that needs a transient sampled-image handle obtains it through the active FrameContext heap writer:

```cpp
const uint32_t inputHeapIndex =
    ctx.heap().publishSampledImage(ctx.image(data.input));
```

The heap writer creates descriptor bytes with the exact graph-derived `VkImageLayout` and publishes them into the FrameContext resource-heap arena under architecture 089.

There is no Set-2 descriptor region. Pass-local heap entries are lifetime-scoped to the active FrameContext.

## 16. Example — compute skinning

```cpp
struct SkinningPassData {
    BufferHandle bindVertices;
    BufferHandle palettes;
    BufferHandle skinnedVertices;
};

graph.addPass<SkinningPassData>(
    "Skinning",
    PassClass::Compute,
    QueueClass::Graphics,

    [&](PassBuilder& b, SkinningPassData& d) {
        d.bindVertices = bindVertices;
        d.palettes = bonePalettes;
        d.skinnedVertices = skinnedVertices;

        b.read(
            d.bindVertices,
            BufferAccess::StorageRead,
            ShaderStage::Compute);

        b.read(
            d.palettes,
            BufferAccess::StorageRead,
            ShaderStage::Compute);

        b.write(
            d.skinnedVertices,
            BufferAccess::StorageWrite,
            ShaderStage::Compute);
    },

    [&](const SkinningPassData& d, PassContext& ctx) {
        // bind descriptor-heap pipeline; heaps are already bound for the command buffer
        // publish/pass any transient heap handles needed, push root data, dispatch skinning
    });
```

## 17. Example — dynamic BLAS build

```cpp
struct BlasPassData {
    BufferHandle skinnedVertices;
    BufferHandle scratch;
    AccelHandle blas;
};

graph.addPass<BlasPassData>(
    "Actor BLAS",
    PassClass::AccelBuild,
    QueueClass::Graphics,

    [&](PassBuilder& b, BlasPassData& d) {
        d.skinnedVertices = skinnedVertices;
        d.scratch = blasScratch;
        d.blas = actorBlas;

        b.read(
            d.skinnedVertices,
            BufferAccess::AccelBuildInputRead);

        b.readWrite(
            d.scratch,
            BufferAccess::AccelScratchReadWrite);

        b.write(
            d.blas,
            AccelAccess::BuildWrite);
    },

    [&](const BlasPassData& d, PassContext& ctx) {
        // vkCmdBuildAccelerationStructuresKHR
    });
```

The compiler generates:

```text
COMPUTE_SHADER / SHADER_STORAGE_WRITE
        ->
ACCELERATION_STRUCTURE_BUILD / SHADER_READ
```

for the skinned vertex buffer.

## 18. Example — RT shadows

```cpp
struct ShadowPassData {
    ImageHandle depth;
    ImageHandle normal;
    ImageHandle shadowMask;
    AccelHandle tlas;
};

graph.addPass<ShadowPassData>(
    "RT Shadows",
    PassClass::RayTracing,
    QueueClass::Graphics,

    [&](PassBuilder& b, ShadowPassData& d) {
        d.depth = depth;
        d.normal = normal;
        d.shadowMask = shadowMask;
        d.tlas = tlas;

        b.read(
            d.depth,
            ImageAccess::SampledRead,
            ShaderStage::RayTracing);

        b.read(
            d.normal,
            ImageAccess::SampledRead,
            ShaderStage::RayTracing);

        b.read(
            d.tlas,
            AccelAccess::ShaderRead,
            ShaderStage::RayTracing);

        b.write(
            d.shadowMask,
            ImageAccess::StorageWrite,
            ShaderStage::RayTracing);
    },

    [&](const ShadowPassData& d, PassContext& ctx) {
        // bind RT pipeline/SBT
        // vkCmdTraceRaysKHR
    });
```

## 19. Same-pass incompatible use

The following is rejected in the baseline API for one image range:

```text
ColorAttachment + SampledRead
DepthAttachmentWrite + SampledRead
TransferDst + SampledRead
```

Split into two passes.

Sampled/storage shader use in one pass may be merged only when the compiler can represent the range in `GENERAL` with a single shader-stage/access union.

## 20. No automatic pass culling initially

Every declared pass executes.

Pass culling can be added later.

This makes initial validation/profiling deterministic and keeps graph behavior obvious during renderer bring-up.
