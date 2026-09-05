// M0.7 R3: direct SPV_EXT_descriptor_heap compile/reflection fixture.
// This is compile/ABI qualification only. Native Vulkan execution is R2;
// acceleration-structure 8-byte lowering and TraceRay/ray-query are R4.

struct GpuShaderRoot
{
    uint64_t sceneRootAddress;
    uint64_t frameConstantsAddress;
    uint64_t viewConstantsAddress;
    uint64_t passDataAddress;
};

struct MatrixAbiProbe
{
    float4x4 objectToWorld;
    float3 bias;
    float scale;
};

struct StructuredItem
{
    float4 value;
    uint tag;
};

[[vk::push_constant]]
ConstantBuffer<GpuShaderRoot> gRoot;

[numthreads(64, 1, 1)]
void computeMain(uint3 tid : SV_DispatchThreadID)
{
    uint lane = tid.x;

    // The divergent source-level indices are marked explicitly even though
    // SPV_EXT_descriptor_heap makes final NonUniform decorations unnecessary.
    uint sampledIndex = NonUniformResourceIndex(uint(gRoot.sceneRootAddress) + lane);
    uint samplerIndex = NonUniformResourceIndex(uint(gRoot.frameConstantsAddress) + lane);
    uint storageImageIndex = NonUniformResourceIndex(uint(gRoot.viewConstantsAddress) + lane);
    uint bufferBase = uint(gRoot.passDataAddress);

    Texture2D<float4> sampledImage = ResourceDescriptorHeap[sampledIndex];
    SamplerState samplerState = SamplerDescriptorHeap[samplerIndex];
    RWTexture2D<float4> storageImage = ResourceDescriptorHeap[storageImageIndex];

    ConstantBuffer<MatrixAbiProbe> constants =
        ResourceDescriptorHeap[NonUniformResourceIndex(bufferBase + lane * 3 + 0)];
    StructuredBuffer<StructuredItem> structuredInput =
        ResourceDescriptorHeap[NonUniformResourceIndex(bufferBase + lane * 3 + 1)];
    RWStructuredBuffer<float4> storageOutput =
        ResourceDescriptorHeap[NonUniformResourceIndex(bufferBase + lane * 3 + 2)];

    float4 sampled = sampledImage.SampleLevel(samplerState, float2(0.5, 0.5), 0.0);
    float4 transformed = mul(constants.objectToWorld, structuredInput[0].value);
    float4 result = sampled + transformed + float4(constants.bias, constants.scale);

    storageImage[uint2(lane, 0)] = result;
    storageOutput[lane] = result;
}
