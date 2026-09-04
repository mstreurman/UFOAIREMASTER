# Presentation World and Tactical Event Bridge

**Status:** Accepted architecture baseline  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Platform:** Fedora Linux 44  
**CPU target:** Intel Core i9-9900K  
**GPU target:** Intel Arc B580 / Xe2

## 1. Purpose

This document defines the one-way boundary between canonical UFO: Alien Invasion tactical gameplay and the remaster presentation runtime.

The existing tactical game already emits typed `EV_*` events through the server. The remaster preserves that protocol initially and splits client handling into explicit canonical-mirror and presentation stages.

```text
Canonical game.so
      |
      | authoritative EV_* events
      v
Server/event transport
      |
      v
Tactical Client Mirror
      |
      | typed read-only presentation projection
      v
Presentation Event Bridge
      |
      v
Presentation World
      |
      +-- Vulkan 1.4 / B580 renderer
      +-- animation
      +-- Jolt Physics
      +-- OpenAL Soft + EFX
      +-- VFX/particles
      +-- UI presentation

NO FEEDBACK INTO CANONICAL GAMEPLAY
```

## 2. Authority rule

The canonical game decides what happened. Presentation systems decide how that result is shown and heard.

Vulkan RT, Jolt, OpenAL, animation, particles, and UI presentation may consume canonical results but may not write gameplay-authoritative state.

## 3. Split legacy `le_t` responsibilities

The legacy `le_t` combines mirrored tactical state, interaction state, animation, models, particles, lighting, sound, interpolation and callbacks. It must not become the new renderer's scene model.

The remaster separates three logical domains.

### 3.1 Tactical Client Mirror

Conceptual shape:

```cpp
using CanonicalEntityId = uint32_t;

struct TacticalActorMirror {
    CanonicalEntityId id;
    GridPosition gridPosition;
    GridPosition previousGridPosition;

    int team;
    int playerNumber;
    int characterUcn;

    int timeUnits;
    int maxTimeUnits;
    int hitPoints;
    int maxHitPoints;
    int stun;
    int morale;
    int maxMorale;

    uint16_t stateFlags;
    ActorSize fieldSize;
    InventoryMirror inventory;
};
```

This is illustrative, not final code.

The mirror contains canonical values needed by the client. It contains no Vulkan handles, Jolt bodies, OpenAL sources, particle objects, renderer model pointers, or animation-runtime objects.

### 3.2 Tactical Interaction State

Local player/UI intent remains separate from both canonical state and rendering:

```cpp
struct TacticalInteractionState {
    CanonicalEntityId selectedActor;
    ActionMode selectedMode;
    GridPosition pendingMove;
    FireModeSelection selectedFireMode;
    MovePreview movePreview;
};
```

### 3.3 Presentation World

Conceptual presentation entity:

```cpp
using PresentationEntityId = uint64_t;

struct PresentationEntity {
    PresentationEntityId id;
    OptionalCanonicalEntityId canonicalSource;

    TransformHandle transform;
    RenderableHandle renderable;
    SkeletonHandle skeleton;
    PhysicsHandle physics;
    AudioEmitterHandle audio;
    ParticleEmitterHandle particles;
    PresentationFlags flags;
};
```

The storage decision is now owned by ADR-011 and architecture 006: a custom component-based Presentation World with generational IDs, dense component storage, sparse entity-to-component lookup, controlled structural mutation and immutable renderer extraction.

## 4. Canonical-to-presentation mapping

A canonical entity may map to one presentation entity or several.

```text
Canonical actor 37
   |
   +-- body render entity
   +-- weapon render entity
   +-- audio emitter
   +-- temporary muzzle-flash light
   +-- temporary particle emitter
```

Presentation-only entities need no canonical source:

- debris;
- shell casings;
- smoke;
- sparks;
- ragdoll helper bodies;
- temporary lights;
- blood/VFX particles.

## 5. Two-stage event handling

Every migrated legacy event callback is conceptually split into:

```text
Stage A: decode + canonical client-mirror mutation
Stage B: emit typed presentation event(s)
```

Example:

```text
EV_ACTOR_STATS
      |
      +--> mirror: TU / HP / STUN / morale
      |
      +--> UI presentation notification
```

Vulkan, Jolt and OpenAL do not parse legacy network events directly.

## 6. Presentation event envelope

Internal presentation events should carry common ordering/timing metadata.

```cpp
struct PresentationEventHeader {
    uint64_t sequence;
    uint64_t scheduledPresentationTime;
    PresentationEventType type;
    OptionalCanonicalEntityId source;
    OptionalCanonicalEntityId target;
};
```

`sequence` preserves canonical event order. `scheduledPresentationTime` preserves the legacy client's intentional movement/projectile/impact sequencing.

## 7. Representative typed events

### Actor moved

```cpp
struct ActorMovedEvent {
    CanonicalEntityId actor;
    Span<const CanonicalMoveStep> path;
    GridPosition finalPosition;
};
```

Animation and transform interpolation may make movement look natural. Jolt may not change the canonical path or final position.

### Actor shot

```cpp
struct ActorShotEvent {
    CanonicalEntityId shooter;
    OptionalCanonicalEntityId victim;
    WeaponDefinitionId weapon;
    FireDefinitionId fireDefinition;
    ShootType shootType;
    Vec3 canonicalFrom;
    Vec3 canonicalImpact;
    Vec3 canonicalImpactNormal;
    uint32_t canonicalFlags;
    uint32_t surfaceFlags;
};
```

Presentation may generate muzzle flash, tracer/projectile visuals, decals, impact VFX, temporary lighting and audio. The canonical impact is never recomputed by Vulkan RT or Jolt.

### Actor died

```cpp
struct ActorDiedEvent {
    CanonicalEntityId actor;
    uint16_t canonicalState;
    int playerNumber;
    bool attackerAttributed;
};
```

After the mirror records the canonical death, presentation may trigger animation, Jolt ragdoll, audio and VFX.

### Sound requested

```cpp
struct SoundRequestedEvent {
    OptionalCanonicalEntityId entity;
    Vec3 canonicalOrigin;
    SoundAssetId sound;
    int movementStep;
};
```

OpenAL Soft may apply attenuation, HRTF and EFX. Audio calculations remain presentation-only.

### Model exploded

```cpp
struct ModelExplodedEvent {
    CanonicalEntityId entity;
    SoundAssetId sound;
};
```

Canonical destruction/mirror updates happen first. Jolt debris and VFX are aftermath only.

## 8. Timing semantics

The current client intentionally schedules events based on movement duration, shot timing, projectile travel, impact time and actor locks.

The remaster preserves the ordering model:

```text
start shot
   -> projectile/tracer presentation
   -> canonical impact time
   -> explosion/death presentation
```

It must never reorder dependent events into a visually or logically impossible sequence.

## 9. Presentation event queue requirements

The bridge queue must:

- preserve event order;
- support scheduled presentation time;
- preserve required entity dependencies/locks during migration;
- expose event IDs/names for debugging;
- support capture/replay later;
- support multiple presentation consumers;
- allow a consumer to be disabled without changing gameplay;
- never require Vulkan/Jolt/OpenAL completion for canonical simulation correctness.

## 10. Presentation consumers

```text
Presentation Event
      |
      +--> Presentation World mutation
      +--> Animation sink
      +--> Jolt sink
      +--> OpenAL sink
      +--> VFX sink
      +--> UI presentation sink
```

Not every event is broadcast to every sink.

## 11. Renderer boundary

The renderer primarily consumes an immutable per-frame snapshot, not the event stream itself.

```text
Events -> Presentation World -> RenderSnapshot -> Vulkan
```

The exact semantic contents of the renderer snapshot are owned by architecture 006 and later subsystem extraction specifications.

This overview intentionally does not define a competing `RenderSnapshot` struct.

The snapshot remains the clean CPU/GPU handoff.

## 12. Jolt boundary

Jolt receives presentation commands such as:

```text
ActivateRagdoll
SpawnDebris
ApplyPresentationImpulse
DestroyPresentationBody
```

Jolt writes presentation transforms only.

Preferred flow:

```text
Jolt -> Presentation World -> skeleton/transform extraction -> Vulkan
```

Never:

```text
Jolt -> canonical actor/grid state
```

## 13. Animation boundary

Animation consumes canonical presentation events and mirror state, but animation root motion is not canonical movement.

Canonical paths and positions remain authoritative.

## 14. OpenAL boundary

OpenAL Soft consumes sound events, listener state, emitter transforms and environmental presentation state.

EFX/HRTF/occlusion processing cannot modify AI detection or gameplay visibility.

## 15. Threading direction

Canonical event decoding/mirror mutation remains ordered.

Presentation work may fan out afterward:

```text
ordered decode/mirror
       |
ordered presentation-event creation
       |
       +-- animation jobs
       +-- Jolt jobs
       +-- audio preparation
       +-- render-scene extraction
       |
frame synchronization point
       |
immutable RenderSnapshot
```

Do not parallelize canonical event mutation merely to use all 16 hardware threads.

## 16. i9-9900K data-oriented direction

Presentation storage should be designed for the reference CPU's cache hierarchy and AVX2 capability:

- compact component arrays;
- stable integer handles;
- minimal pointer chasing;
- batched transform updates;
- batched animation updates;
- batched renderer extraction;
- AVX2 transform kernels where benchmarks justify them.

## 17. Legacy migration pattern

Each event is migrated safely:

```text
legacy callback
    |
    +-- retain legacy decode/mirror mutation
    +-- emit typed presentation event
    +-- temporarily retain old presentation implementation
```

After the new consumer is validated:

```text
old presentation implementation -> remove
```

The network protocol and canonical outcome stay unchanged.

## 18. Required invariants

1. Vulkan cannot mutate canonical tactical state.
2. Jolt cannot mutate canonical tactical state.
3. OpenAL cannot mutate canonical tactical state.
4. Animation cannot mutate canonical tactical state.
5. Presentation transform is not canonical transform.
6. Presentation physics collision is not canonical collision.
7. RT visibility is not canonical LOS.
8. Audio occlusion is not AI detection.
9. Root motion is not canonical movement.
10. Visual projectile trajectory cannot change a canonical projectile result.
11. Dropping a presentation event consumer cannot change canonical outcomes.
12. Presentation subsystem failure may degrade presentation, never redefine gameplay.

## 19. Capture/replay goal

A future debug capture should record normalized presentation input so that graphics/audio/physics can be replayed without rerunning tactical simulation.

Use cases:

- B580 repeatable GPU benchmarks;
- animation regression tests;
- Jolt stress tests;
- OpenAL tests;
- renderer regression tests;
- preservation debugging.

This is not a replacement for save games.

## 20. Prototype presentation integration subset

The following events remain a useful early **presentation integration prototype**:

```text
EV_ACTOR_APPEAR
EV_ACTOR_MOVE
EV_ACTOR_TURN
EV_ACTOR_SHOOT
EV_ACTOR_DIE
EV_MODEL_EXPLODE
EV_SOUND
EV_DOOR_OPEN
EV_DOOR_CLOSE
```

This group is **not a standalone tactical bridge**.

It is valid only while every unported legacy tactical-event handler remains active.

The source-complete audit in `004-tactical-event-catalog.md` and `005-tactical-event-dependency-matrix.md` establishes that a replacement must preserve all 46 executable event semantics, plus `EV_NULL` stream termination and `EV_INV_TRANSFER` serialization-helper behavior.

The prototype is useful because it exercises entity presentation, motion, animation, weapon VFX, canonical impact consumption, Jolt ragdolls/debris, positional audio and moving world geometry.

## 21. Prototype completion criteria

The bridge is successful when:

- legacy tactical simulation is unchanged;
- events arrive in the same canonical order;
- mirror values match legacy client behavior;
- Presentation World exists independently of `le_t` renderer state;
- selected events emit typed presentation events;
- all unported events continue through the legacy callback path;
- presentation consumers can be disabled without affecting gameplay;
- presentation-only entities may exist without canonical counterparts;
- Jolt may move visual bodies without altering canonical state;
- Vulkan extraction no longer requires renderer pointers inside canonical mirror structures.

## 22. Baseline 034 tactical presentation-fidelity closures

Two source-observed presentation details are now explicit bridge policy:

```text
EV_SOUND queued movement step:
    preserve legacy closest-friendly-actor source-start spatialization
    carry the compatibility reference to AudioControl
    do not mutate the global OpenAL listener

EV_CAMERA_APPEAR:
    consume transmitted dir for presentation yaw
    classify the difference from the legacy callback as an approved presentation-only bug fix
```

ADR-042 owns the audio compatibility decision. ADR-043 owns the camera-direction fix. Neither changes the canonical tactical event stream or moves presentation state into gameplay authority.

