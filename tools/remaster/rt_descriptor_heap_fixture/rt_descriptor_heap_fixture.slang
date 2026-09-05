// M0.7 R4: 8-byte direct acceleration-structure heap + TraceRay fixture.
// The TLAS handle is a typed ResourceDescriptorHeap index whose element is an
// exact uint64_t acceleration-structure device address at byte offset index*8.

struct GpuShaderRoot
{
    uint64_t sceneRootAddress;        // AS typed heap index (8-byte units)
    uint64_t frameConstantsAddress;   // reserved by the v1 root contract
    uint64_t viewConstantsAddress;    // reserved by the v1 root contract
    uint64_t passDataAddress;         // storage-buffer typed heap index (unified units)
};

[[vk::push_constant]]
ConstantBuffer<GpuShaderRoot> gRoot;

[raypayload]
struct R4Payload
{
    uint value : read(caller) : write(caller, closesthit, miss);
    float hitT : read(caller) : write(caller, closesthit, miss);
};

[shader("raygeneration")]
void rayGenMain()
{
    uint asIndex = uint(gRoot.sceneRootAddress);
    uint outputIndex = uint(gRoot.passDataAddress);

    RaytracingAccelerationStructure scene = ResourceDescriptorHeap[asIndex];
    RWStructuredBuffer<uint> output = ResourceDescriptorHeap[outputIndex];

    RayDesc ray;
    ray.Origin = float3(0.0, 0.0, 0.0);
    ray.TMin = 0.001f;
    ray.Direction = float3(0.0, 0.0, 1.0);
    ray.TMax = 100.0f;

    R4Payload payload = { 0u, -1.0f };
    TraceRay(scene, RAY_FLAG_NONE, 0xff, 0, 0, 0, ray, payload);

    output[0] = payload.value;
    output[1] = asIndex;
    output[2] = asuint(payload.hitT);
}

[shader("miss")]
void missMain(inout R4Payload payload)
{
    payload.value = 0x0BADF00Du;
    payload.hitT = -2.0f;
}

[shader("closesthit")]
void closestHitMain(inout R4Payload payload, in BuiltInTriangleIntersectionAttributes attributes)
{
    // Force the hit shader to consume both the fixed triangle and the payload.
    payload.value = 0xC0FFEE42u ^ asuint(attributes.barycentrics.x * 0.0f);
    payload.hitT = RayTCurrent();
}
