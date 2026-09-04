# Tactical Event Dependency Matrix

**Status:** Source-complete dependency baseline  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`

## 1. Purpose

This document records the dependency relationships that matter when moving the current battlescape client from legacy `le_t`-centric callbacks toward:

```text
Tactical Client Mirror
        |
Presentation Event Bridge
        |
Presentation World
```

The matrix distinguishes protocol correctness from optional modern presentation consumers.

## 2. Dependency matrix

| Event | Required existing state / prerequisite | Current client-side mutation/effect | New bridge requirement |
|---|---|---|---|
| `EV_NULL` | none | ends event sequence | protocol terminator only |
| `EV_RESET` | match/player initialized | resets selection, sets team/active team, completes routing recalc | mandatory control/mirror |
| `EV_START` | initial actors/team data may already exist | initializes camera/client active state, starts battlescape game mode | mandatory control + camera presentation |
| `EV_ENDROUND` | active match | updates active team, round presentation, particles/HUD/audio | mandatory control/mirror |
| `EV_ENDROUNDANNOUNCE` | player/team known | forwards to game-mode handler | mandatory game-mode/UI bridge |
| `EV_RESULTS` | match ending | parses winner/spawn/alive/kills/stuns and forwards remainder to game mode | mandatory canonical game-mode bridge |
| `EV_CENTERVIEW` | map/camera initialized | centers view at grid position | presentation |
| `EV_MOVECAMERA` | map/camera initialized | moves camera along route | presentation |
| `EV_ENT_APPEAR` | map routing available | creates/reactivates generic LE, type/position; particle types start hidden | mandatory mirror/lifetime |
| `EV_ENT_PERISH` | referenced LE normally exists | type-specific inventory/animation/particle cleanup; marks invisible | mandatory mirror/lifetime |
| `EV_ENT_DESTROY` | optional existing LE | marks entity unused | mandatory lifetime |
| `EV_ADD_BRUSH_MODEL` | inline BSP/model data available | creates door/breakable/trigger representation; AABB/model/routing | mandatory world mirror |
| `EV_ADD_EDICT` | none | creates display/debug bounding-box entity with offset ID | preserve current behavior; presentation/debug |
| `EV_ACTOR_APPEAR` | actor may or may not already exist | fully populates/reveals actor, models/state/team data, spotted/UI/path preview | mandatory actor mirror + presentation spawn |
| `EV_ACTOR_ADD` | none | creates hidden actor identity/state/position | mandatory hidden-actor mirror |
| `EV_ACTOR_TURN` | actor exists | updates canonical-facing mirror and visual yaw | mandatory mirror + animation |
| `EV_ACTOR_MOVE` | actor exists; may interleave visibility events | stores authoritative step path/final position and starts timed local move | mandatory mirror + presentation timing |
| `EV_ACTOR_REACTIONFIRECHANGE` | actor/character exists | updates character reaction-fire mode | mandatory tactical UI/mirror |
| `EV_ACTOR_REACTIONFIREADDTARGET` | shooter + target exist; target movement step may exist | HUD target entry; camera center; step timing | mandatory UI/timing |
| `EV_ACTOR_REACTIONFIREREMOVETARGET` | target exists | removes HUD target; step timing | mandatory UI/timing |
| `EV_ACTOR_REACTIONFIRETARGETUPDATE` | shooter + target exist | updates reaction target status/range; step timing | mandatory UI/timing |
| `EV_ACTOR_REACTIONFIREABORTSHOT` | shooter + target exist | abort HUD notification; step timing | mandatory UI/timing / presentation cancellation |
| `EV_ACTOR_START_SHOOT` | shooter may be hidden | marks shot timing state, optional camera/animation | mandatory timing sequence |
| `EV_ACTOR_SHOOT` | shot sequence/fire definitions; target optional | consumes authoritative impact/from/normal/flags; projectile visual, sound, animation | mandatory combat presentation from canonical result |
| `EV_ACTOR_SHOOT_HIDDEN` | fire definition, optional target | hidden-shooter sound/impact presentation and timing | mandatory hidden-combat presentation |
| `EV_ACTOR_THROW` | fire definition | consumes server duration/muzzle/velocity; visual thrown object + sound | mandatory combat presentation; Jolt non-authoritative |
| `EV_ACTOR_END_SHOOT` | shot timing may be active | clears shot/death timing and returns actor to idle | mandatory timing sequence |
| `EV_ACTOR_DIE` | actor exists | updates state, team list, AABB, UI/audio/animation/path preview | mandatory mirror + death presentation |
| `EV_ACTOR_REVITALISED` | actor exists and is stunned/dead | restores actor state/team list/AABB/floor link/path preview | mandatory mirror + presentation transition |
| `EV_ACTOR_STATS` | own controlled actor expected | updates TU/HP/STUN/morale/max values and UI/move preview | mandatory mirror |
| `EV_ACTOR_STATECHANGE` | actor exists | updates state; may itself kill actor; updates reservation/character/path preview/UI | mandatory mirror; lifecycle transition source |
| `EV_ACTOR_RESERVATIONCHANGE` | actor/character exists | updates reserved reaction/shot/crouch TU | mandatory mirror/UI |
| `EV_ACTOR_WOUND` | actor exists/body template valid | updates wound/treatment levels and bleeding UI | mandatory mirror/UI |
| `EV_INV_ADD` | entity exists; often timed after shot/death/drop | deserializes item data into inventory; weapon slots/floor rendering/UI | mandatory inventory mirror + timing |
| `EV_INV_DEL` | entity exists | removes item/slot state; floor/UI update | mandatory inventory mirror + timing |
| `EV_INV_AMMO` | actor/inventory item may exist | updates ammo count/type for own team | mandatory inventory mirror |
| `EV_INV_RELOAD` | actor/inventory item may exist | reload sound, loose-clip equipment accounting, ammo update, UI | mandatory gameplay-client state + presentation |
| `EV_INV_TRANSFER` | not dispatched | serialization format only | keep helper format; never treat as executable presentation event |
| `EV_MODEL_EXPLODE` | brush/breakable LE exists | delayed destruction, removes clip model, sound, routing recalculation | mandatory world mirror first; then Jolt/VFX/audio |
| `EV_MODEL_EXPLODE_TRIGGERED` | brush/breakable LE exists | same callback without impact-delay timing | mandatory world mirror first; then presentation |
| `EV_PARTICLE_APPEAR` | referenced particle LE already exists | stores particle ID/flags and spawns attached particle | presentation with hard entity-lifetime dependency |
| `EV_PARTICLE_SPAWN` | none | spawns free particle using start/velocity/acceleration | presentation with shot/death timing |
| `EV_SOUND` | referenced LE needed for timed step behavior | movement/impact-synchronized spatial sound; queued step start spatialization uses closest friendly actor reference | OpenAL presentation with scheduler dependency; preserve ADR-042 compatibility rule |
| `EV_DOOR_OPEN` | door LE from `EV_ADD_BRUSH_MODEL` | starts rotating/sliding door behavior and associated client spatial state | mandatory world-state presentation |
| `EV_DOOR_CLOSE` | door LE from `EV_ADD_BRUSH_MODEL` | inverse door behavior | mandatory world-state presentation |
| `EV_CLIENT_ACTION` | actor and action entity both exist | sets actor's actionable entity; enables UI | mandatory interaction mirror/UI |
| `EV_RESET_CLIENT_ACTION` | actor exists | clears actionable entity; disables UI | mandatory interaction mirror/UI |
| `EV_CAMERA_APPEAR` | camera model assets | creates camera LE/model/team/level flags/animation; legacy callback ignores transmitted `dir` for yaw | presentation/world mirror; ADR-043 requires yaw from transmitted `dir` |

## 3. Hard ordering chains

### Battlescape bootstrap

```text
EV_RESET (instant)
   |
initial entity/actor information
   |
EV_START (instant)
   |
normal scheduled events
```

The exact network stream can include initial events around this sequence, but both reset and start are immediate-event semantics and must not simply become ordinary queued presentation messages.

### Hidden actor visibility

```text
EV_ACTOR_ADD
    |
ET_ACTORHIDDEN mirror exists
    |
...movement/state may occur...
    |
EV_ACTOR_APPEAR
```

`EV_ACTOR_APPEAR` can also create an actor directly if no hidden mirror exists.

### Actor movement and visibility

```text
EV_ACTOR_MOVE
   |
step timing / actor lock
   |
EV_ENT_PERISH / EV_ACTOR_APPEAR and related visibility changes may interleave
   |
movement completes / actor unlocks
```

Do not isolate movement and visibility onto independently reordered queues.

### Normal shot sequence

Conceptually:

```text
EV_ACTOR_START_SHOOT
       |
EV_ACTOR_SHOOT [possibly repeated/bounced]
       |
impact-time-dependent events:
    EV_MODEL_EXPLODE
    EV_ACTOR_DIE
    EV_PARTICLE_*
    EV_ENT_APPEAR
    EV_INV_DEL / EV_INV_ADD
    EV_SOUND
       |
EV_ACTOR_END_SHOOT
```

Not every shot emits every event, but these events share the scheduler state.

### Hidden shot sequence

```text
EV_ACTOR_SHOOT_HIDDEN
       |
impact/audio timing
       |
related damage/death/world events
```

A visible shooter is not required.

### Throw sequence

```text
EV_ACTOR_THROW
       |
server-provided travel duration
       |
impactTime
       |
impact/death/particle/inventory/world events
```

Jolt may render the thrown object, but the canonical duration/result remains the event input.

### Breakable/door lifecycle

```text
EV_ADD_BRUSH_MODEL
      |
      +--> EV_CLIENT_ACTION references
      +--> EV_DOOR_OPEN
      +--> EV_DOOR_CLOSE
      +--> EV_MODEL_EXPLODE(_TRIGGERED)
```

### Particle entity lifecycle

```text
EV_ENT_APPEAR (ET_PARTICLE)
       |
EV_PARTICLE_APPEAR
       |
EV_ENT_PERISH / destruction
```

### Actor death alternatives

Normal explicit path:

```text
EV_ACTOR_DIE
```

But also:

```text
EV_ACTOR_STATECHANGE
    with STATE_DEAD
```

which performs a distinct no-normal-death-animation transition.

The Presentation World must model the resulting state transition, not assume one event ID equals one universal death behavior.

## 4. Bridge architecture implication

The correct bridge is not:

```text
EV_* -> renderer
```

It is:

```text
EV_*
 |
 +--> ordered legacy-protocol decoder
 |
 +--> Tactical Client Mirror / interaction-state mutation
 |
 +--> lifecycle/timing derivation
 |
 +--> typed PresentationEvents
 |
 +--> Presentation World
       |
       +-- Vulkan
       +-- animation
       +-- Jolt
       +-- OpenAL
       +-- VFX/UI
```

Some protocol events produce no modern renderer event at all, yet remain mandatory for correctness.

## 5. Prototype subset clarification

The previously listed nine events:

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

remain useful as a **visual integration prototype** only when the unported legacy handlers remain active.

They are not a standalone replacement set.

A more useful modern integration test can add:

```text
EV_ACTOR_ADD
EV_ADD_BRUSH_MODEL
EV_ACTOR_START_SHOOT
EV_ACTOR_SHOOT_HIDDEN
EV_ACTOR_THROW
EV_ACTOR_END_SHOOT
EV_ENT_APPEAR
EV_ENT_PERISH
EV_PARTICLE_APPEAR
EV_PARTICLE_SPAWN
```

but even that is still not permission to remove the remaining legacy event handlers.

The replacement target is all 46 executable event semantics.
