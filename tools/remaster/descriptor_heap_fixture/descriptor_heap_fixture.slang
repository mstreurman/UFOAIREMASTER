// M0.7 R2 native VK_EXT_descriptor_heap execution fixture.
// This shader intentionally uses the legacy Vulkan DescriptorSet/Binding SPIR-V
// interface. The native fixture maps those declarations into descriptor heaps
// with VkShaderDescriptorSetAndBindingMappingInfoEXT. Direct
// SPV_EXT_descriptor_heap lowering is qualified separately by M0.7 R3.

struct GpuShaderRoot
{
    uint64_t sceneRootAddress;
    uint64_t frameConstantsAddress;
    uint64_t viewConstantsAddress;
    uint64_t passDataAddress;
};

[[vk::push_constant]]
ConstantBuffer<GpuShaderRoot> gRoot;

[[vk::binding(0, 0)]]
Texture2D<float4> gSource;

[[vk::binding(1, 0)]]
SamplerState gSampler;

[[vk::binding(2, 0)]]
[vk::image_format("r32ui")]
RWTexture2D<uint> gOutput;

[[vk::binding(3, 0)]]
RWStructuredBuffer<uint> gWords;

[shader("compute")]
[numthreads(1, 1, 1)]
void computeMain(uint3 tid : SV_DispatchThreadID)
{
    if (any(tid != uint3(0, 0, 0)))
        return;

    float4 sampled = gSource.SampleLevel(gSampler, float2(0.5, 0.5), 0.0);
    uint4 sourceBytes = uint4(round(saturate(sampled) * 255.0));
    uint delta = uint(gRoot.passDataAddress & uint64_t(0xff));
    uint4 result = sourceBytes + uint4(delta, delta * 2u, delta * 3u, delta * 4u);

    gOutput[uint2(0, 0)] = result.x;

    uint previous = gWords[0];
    gWords[0] = previous + result.x;
    gWords[1] = result.y;
    gWords[2] = result.z;
    gWords[3] = result.w;
}
