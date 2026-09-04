# Presentation World — C++ API and Data Layout

**Status:** Architecture baseline  
**Related ADR:** `ADR-011-custom-presentation-world-data-model.md`

## 1. Purpose

This document translates the Presentation World concept into an implementable C++ shape.

It is a design target, not committed source code.

## 2. Typed IDs

Conceptual types:

```cpp
namespace ufo::canonical {
struct EntityId {
    uint32_t value;
};
}

namespace ufo::presentation {
struct EntityId {
    uint32_t index;
    uint32_t generation;
};
}
```

`canonical::EntityId` is the project-side presentation-bridge identity and is exactly `uint32_t`, matching architecture 003. The audited legacy runtime stores `entnum` in `int`, while tactical event format code `s` serializes a signed 16-bit value and `MAX_EDICTS` is 1024. Legacy wire adapters validate/decode that preserved protocol domain into the 32-bit project type; changing the wire protocol is not implied.

Other subsystem identities remain distinct:

```cpp
struct RenderInstanceId;
struct PhysicsBodyHandle;
struct AudioEmitterHandle;
struct MeshHandle;
struct MaterialHandle;
```

No implicit conversion should exist between these identity domains.

## 3. Entity record

Keep the record compact:

```cpp
using ComponentMask = uint64_t;

struct EntityRecord {
    uint32_t generation;
    ComponentMask components;

    canonical::EntityId canonicalSource;
    uint32_t flags;
};
```

A separate flag indicates whether `canonicalSource` is valid.

## 4. Component-store baseline

Each component family uses dense storage plus sparse lookup.

Conceptual interface:

```cpp
template<typename T>
class DenseComponentStore {
public:
    bool has(EntityId id) const noexcept;

    T& get(EntityId id);
    const T& get(EntityId id) const;

    T& add(EntityId id, const T& value);
    void remove(EntityId id);

    std::span<const EntityId> entities() const noexcept;
    std::span<T> values() noexcept;
};
```

The exact generic/template implementation is not locked.

The important invariants are:

- dense iteration;
- stable generational validation at the world level;
- no per-component heap object;
- no pointer graph between components;
- no structural mutation during parallel read/update phases.

## 5. Initial component families

```text
Transform
Renderable
Skeleton
Animation
PhysicsProxy
AudioEmitter
Light
ParticleEmitter
Attachment
Lifetime
```

Additional components are added only when a clear runtime need exists.

## 6. Transform component

Logical shape:

```cpp
struct LocalTRS {
    Vec4 translation;
    Quat rotation;
    Vec4 scale;
};

struct TransformComponent {
    LocalTRS local;

    EntityId parent;

    Mat3x4 world;
    Mat3x4 previousWorld;

    uint32_t flags;
};
```

Actual storage may later become SoA/AoSoA.

`previousWorld` is first-class state for temporal rendering.

## 7. Canonical binding

The Presentation World maintains fast lookup from canonical entities to presentation entities.

Conceptually:

```cpp
class CanonicalPresentationMap {
public:
    EntityId primary(canonical::EntityId source) const noexcept;

    std::span<const EntityId>
    all(canonical::EntityId source) const noexcept;
};
```

One canonical actor may map to:

- primary actor presentation entity;
- equipped weapon entities;
- headgear;
- attached presentation effects.

Presentation-only debris and VFX have no canonical binding.

## 8. Renderer-facing component

```cpp
struct RenderableComponent {
    MeshHandle mesh;
    MaterialSetHandle materials;

    Bounds localBounds;

    RenderInstanceId rendererInstance;

    uint32_t renderFlags;
    uint32_t layerMask;
};
```

Do not store raw Vulkan objects here.

## 9. Physics-facing component

```cpp
enum class PhysicsMode : uint8_t {
    None,
    KinematicPresentation,
    DynamicPresentation,
    RagdollRoot
};

struct PhysicsComponent {
    PhysicsBodyHandle body;
    PhysicsMode mode;
};
```

`PhysicsBodyHandle` is owned by the remaster integration layer, not a leaked `JPH::BodyID`.

## 10. Animation/skeleton components

Keep state small:

```cpp
struct AnimationComponent {
    AnimationGraphHandle graph;

    AnimationStateId baseState;
    AnimationStateId overlayState;

    ClipHandle baseClip;
    ClipHandle overlayClip;

    float baseTime;
    float overlayTime;
    float playbackRate;
    float overlayWeight;

    PoseSource poseSource;

    uint32_t flags;
};
```

Large pose data lives in a dedicated pose arena/store.

## 11. Attachments

```cpp
struct AttachmentComponent {
    EntityId parent;
    uint16_t jointOrSocketIndex;
    LocalTRS offset;
    AttachmentTargetType targetType;
};
```

Hot runtime attachment resolution is integer-indexed.

## 12. Lifetime

```cpp
struct LifetimeComponent {
    float remainingSeconds;
};
```

This supports transient lights, casings, debris, particles and other presentation-only entities without bespoke lifetime callbacks.

## 13. World API

Conceptual API:

```cpp
class PresentationWorld {
public:
    EntityId create();
    void destroy(EntityId id);

    bool alive(EntityId id) const noexcept;

    void bindCanonical(EntityId id, canonical::EntityId source);
    EntityId findPrimary(canonical::EntityId source) const noexcept;

    void process(std::span<const PresentationEvent> events);

    void update(const PresentationUpdateContext& context);

    void buildRenderSnapshot(RenderSnapshotBuilder& builder) const;

private:
    EntityPool entities;

    TransformStore transforms;
    RenderableStore renderables;
    SkeletonStore skeletons;
    AnimationStore animations;
    PhysicsStore physics;
    AudioEmitterStore audio;
    LightStore lights;
    ParticleStore particles;
    AttachmentStore attachments;
    LifetimeStore lifetimes;
};
```

Systems should remain separate from a monolithic world class.

## 14. Systems

Initial system families:

```text
PresentationEventSystem
AnimationSystem
SkeletonSystem
PhysicsIntegrationSystem
AttachmentSystem
TransformSystem
LifetimeSystem
RenderExtractionSystem
AudioExtractionSystem
```

## 15. Structural command buffer

Parallel systems may request structural changes through a deferred command buffer.

Typical commands:

```text
CreateEntity
DestroyEntity
AddComponent
RemoveComponent
```

The world applies these at a known structural synchronization point.

## 16. Update phase baseline

```text
1. consume scheduled PresentationEvents
2. apply Presentation World state requests
3. animation state update
4. animation sampling/blending
5. skeleton evaluation
6. Jolt step
7. ragdoll/physics pose integration
8. attachments
9. world-transform propagation
10. lights/audio/VFX update
11. lifetime/destruction processing
12. structural command commit
13. freeze presentation state
14. build RenderSnapshot
15. build audio extraction data
```

The exact job split may evolve, but ordering dependencies must be explicit.

## 17. Frame arena

Transient per-frame allocations should use linear arenas.

Typical consumers:

- variable-size event payloads;
- temporary sort arrays;
- renderer extraction;
- visible lists;
- upload metadata.

Reset occurs only when the corresponding frame lifetime is complete.

## 18. Immutable render snapshot

This document is the semantic authority for renderer extraction.

A sealed `RenderSnapshot` contains, as applicable:

```text
frame number
CameraSnapshot
atmosphere/environment snapshot
cutaway/tactical-level state

contiguous RenderInstance array
contiguous RenderLight array
contiguous SkeletonSnapshot array

particle-emitter data
volume-emitter data
ribbon/beam presentation data
world-presentation overlay data
```

Transient VFX lights are folded into renderer light extraction.

Audio uses the separate `AudioStateSnapshot` + `AudioCommandQueue`.

2D UI uses the separate `UiRenderSnapshot`.

Exact subsystem arrays may be split into typed spans/blocks, but higher-level documents must not define another incompatible `RenderSnapshot` shape.

The Vulkan renderer consumes immutable contiguous extraction data and does not walk the mutable world.

## 19. CPU/GPU layout split

Do not force Presentation World component layout to match shader/GPU layout.

Extraction is an explicit conversion step:

```text
CPU Presentation World
       |
       v
immutable RenderSnapshot
       |
       v
GPU scene / upload packing
```

That allows each side to be independently optimized.

## 20. 9900K direction

Hot arrays should support at least 32-byte alignment where useful.

64-byte cache-line isolation is reserved for concurrently modified control state/counters, not blindly applied to all entity data.

SIMD layout and worker chunk sizes are benchmark decisions.

## Deterministic structural command ordering

Architecture 058 owns the exact deferred-command ordering contract.

Workers emit commands carrying a Main-issued `PresentationMutationStamp`.

Main stable-sorts/merges commands by that stamp before:

```text
structural mutation
entity-slot allocation
RenderObjectId allocation
LightId allocation
other stable presentation identity allocation
```

Worker completion order is never a structural-order input.

This ordering is part of presentation structural replay/regression semantics.
