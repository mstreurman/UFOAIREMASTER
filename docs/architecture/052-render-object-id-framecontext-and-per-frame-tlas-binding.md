# RenderObjectId, FrameContext Lifetime and Per-Frame TLAS Binding

**Status:** Exact implementation specification  
**Related ADR:** ADR-028

## 1. RenderObjectId

```cpp
using RenderObjectId = uint32_t;
constexpr RenderObjectId kInvalidRenderObjectId = 0xffffffffu;
```

Valid range:

```text
0x00000000 .. 0xfffffffe
```

## 2. Allocation

Allocation occurs through the Main-owned renderer-identity registry.

Static `.rmap` identity groups are allocated first in the deterministic order defined by architecture 058.

Dynamic/presentation structural allocations then occur only after deferred commands are sorted by the architecture-058 mutation stamp.

Worker completion order never assigns IDs or determines allocation order.

## 3. Lifetime/reuse

Within one Presentation World:

```text
monotonic allocation
stable across frames
never reused
```

Destroyed IDs remain tombstoned/unmapped.

## 4. Namespace reset

Reset only after:

```text
Presentation World destroyed
RenderSnapshot queue drained
all GPU FrameContexts retired
all temporal histories invalidated
attached-decal owner mappings destroyed
probe/debug mappings released
```

Then the next world may start again at zero.

## 5. Exhaustion

Attempting to allocate `0xffffffff` is a fatal presentation-capacity error.

Canonical state must remain uncorrupted.

## 6. CPU registry

CPU lookup may map:

```text
RenderObjectId
    ->
Presentation EntityId
renderer component/generation
debug name
asset identity
```

CPU internals may use generations; the GPU temporal key remains the stable 32-bit ID.

## 7. Temporal-history contract

Within a Presentation World:

```text
same RenderObjectId => same renderer-object lifetime
```

A world reset invalidates temporal histories before the ID namespace resets.

## 8. Decals/debug

Attached decals and debug/probe mappings never resolve a destroyed ID to a newly created object.

## 9. Descriptor-heap ownership

Production binding uses the one sampler heap + one resource heap model from architecture 089.

Persistent content images/samplers use the process-lifetime registries. Frame/pass resources use the active FrameContext's transient resource-heap arena.

`FrameConstants` and `ViewConstants` remain BDA-rooted through architecture-056 `GpuShaderRoot`.

## 10. TLAS heap handle

Each FrameContext owns:

```text
TLAS storage/handle
typed descriptor-heap publication for that TLAS
GpuSceneRoot.frameTlasHeapIndex
```

After that FrameContext retires, its TLAS can be rebuilt and its transient heap publication reused. The other in-flight FrameContext's TLAS handle/storage is never overwritten early.

Architecture 089 fixes the Slang acceleration-structure heap representation to 8-byte device-address-element units; architecture 087 requires that exact representation to pass a dedicated B580 conformance fixture before production RT use.

## 11. Queue completion values

```cpp
struct QueueCompletionValues {
    uint64_t graphics;
    uint64_t transfer;
    uint64_t compute;
};
```

A FrameContext carries these values rather than one ambiguous completion scalar.

Inactive optional queues use zero/an explicit inactive sentinel.

## 12. Reuse

FrameContext reuse waits for every queue completion value that references resources owned by that context.

## 13. Deferred destruction

Retirement records carry all relevant queue completion values.

Free/destroy only after all required queues pass them.

## 14. Telemetry

Report:

```text
FrameContext index
per-queue completion target/current value
TLAS handle/instance count
Set-1 descriptor region
next RenderObjectId
live/tombstoned object count
```

## Asynchronous audio is not a RenderObjectId owner

Ordered AudioCommandQueue commands use `AudioEmitterId`/`AudioVoiceId` according to architecture 060.

`RenderObjectId` may be carried only as debug/correlation metadata in continuous audio state.

Therefore RenderObjectId namespace reset does not depend on stale asynchronous audio commands.
