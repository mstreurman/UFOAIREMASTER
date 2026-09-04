# Tactical Event Catalog — Source-Complete Protocol Audit

**Status:** Source-complete for the stated commit  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Scope:** Current tactical `event_t` protocol, client registry, callbacks, timing callbacks, and event-role classification.

## 1. Verification scope

This revision replaces the earlier prototype-level classification.

The audit checked:

```text
src/game/q_shared.h
src/game/g_events.cpp
src/game/g_move.cpp
src/game/g_match.cpp
src/client/battlescape/events/e_main.cpp
src/client/battlescape/events/e_parse.cpp
src/client/battlescape/events/event/actor/*.cpp
src/client/battlescape/events/event/inventory/*.cpp
src/client/battlescape/events/event/player/*.cpp
src/client/battlescape/events/event/world/*.cpp
src/client/battlescape/cl_localentity.cpp
```

The purpose is not to redesign the protocol. It is to record what the current game actually requires.

## 2. Protocol count

`event_t` contains **48 entries before `EV_NUM_EVENTS`**:

- 1 null/terminator entry: `EV_NULL`
- 1 non-executable format-helper entry: `EV_INV_TRANSFER`
- 46 executable client event entries

`EVENT_INSTANTLY` is bit `0x80` and is removed by the client parser before event lookup.

## 3. Special entries

### `EV_NULL`

Purpose:

- terminates an event stream/list;
- causes `CL_ParseEvent` to return immediately;
- has no callback.

It is protocol structure, not a Presentation World event.

### `EV_INV_TRANSFER`

Registry:

```text
format: "sbsbbbbs"
callback: none
timing: none
check: none
```

It is used as the shared item serialization layout by inventory send/receive code.

If it arrived as an independently dispatched event, the client parser would reject it because it has no callback.

It must therefore be preserved as a **wire-format helper ID**, not treated as one of the 46 executable event handlers.

## 4. Complete client registry

| Event | Wire format | Client callback | Timing callback | Entity check |
|---|---|---|---|---|
| `EV_NULL` | `""` | none | none | none |
| `EV_RESET` | `bb` | `CL_Reset` | none | none |
| `EV_START` | `b` | `CL_StartGame` | none | none |
| `EV_ENDROUND` | `b` | `CL_DoEndRound` | none | none |
| `EV_ENDROUNDANNOUNCE` | `bb` | `CL_EndRoundAnnounce` | none | none |
| `EV_RESULTS` | manual | `CL_ParseResults` | `CL_ParseResultsTime` | none |
| `EV_CENTERVIEW` | `g` | `CL_CenterView` | none | none |
| `EV_MOVECAMERA` | `g` | `CL_MoveView` | none | none |
| `EV_ENT_APPEAR` | `sbg` | `CL_EntAppear` | `CL_EntAppearTime` | none |
| `EV_ENT_PERISH` | `sb` | `CL_EntPerish` | none | none |
| `EV_ENT_DESTROY` | `s` | `CL_EntDestroy` | none | none |
| `EV_ADD_BRUSH_MODEL` | `sbsbppsbb` | `CL_AddBrushModel` | none | none |
| `EV_ADD_EDICT` | `sbpp` | `CL_AddEdict` | none | none |
| `EV_ACTOR_APPEAR` | `!s!sbbbsbgbssssbbsbbbs` | `CL_ActorAppear` | `CL_ActorAppearTime` | `CL_CheckDefault` |
| `EV_ACTOR_ADD` | `!sbbbbgsb` | `CL_ActorAdd` | none | none |
| `EV_ACTOR_TURN` | `sb` | `CL_ActorDoTurn` | none | none |
| `EV_ACTOR_MOVE` | manual (`sbsss!lg` registry hint) | `CL_ActorDoMove` | `CL_ActorDoMoveTime` | `CL_CheckDefault` |
| `EV_ACTOR_REACTIONFIRECHANGE` | `sbbs` | `CL_ActorReactionFireChange` | none | none |
| `EV_ACTOR_REACTIONFIREADDTARGET` | `ssbb` | `CL_ActorReactionFireAddTarget` | `CL_ActorReactionFireAddTargetTime` | none |
| `EV_ACTOR_REACTIONFIREREMOVETARGET` | `ssb` | `CL_ActorReactionFireRemoveTarget` | `CL_ActorReactionFireRemoveTargetTime` | none |
| `EV_ACTOR_REACTIONFIRETARGETUPDATE` | `ssbb` | `CL_ActorReactionFireTargetUpdate` | `CL_ActorReactionFireTargetUpdateTime` | none |
| `EV_ACTOR_REACTIONFIREABORTSHOT` | `ssb` | `CL_ActorReactionFireAbortShot` | `CL_ActorReactionFireAbortShotTime` | none |
| `EV_ACTOR_START_SHOOT` | `sbgg` | `CL_ActorStartShoot` | `CL_ActorStartShootTime` | none |
| `EV_ACTOR_SHOOT` | `ssbsbbbbbppb` | `CL_ActorDoShoot` | `CL_ActorDoShootTime` | none |
| `EV_ACTOR_SHOOT_HIDDEN` | `sbsbbpb` | `CL_ActorShootHidden` | `CL_ActorShootHiddenTime` | none |
| `EV_ACTOR_THROW` | `ssbbbpp` | `CL_ActorDoThrow` | `CL_ActorDoThrowTime` | none |
| `EV_ACTOR_END_SHOOT` | `s` | `CL_ActorEndShoot` | `CL_ActorEndShootTime` | `CL_CheckDefault` |
| `EV_ACTOR_DIE` | `ssbb` | `CL_ActorDie` | `CL_ActorDieTime` | `CL_CheckDefault` |
| `EV_ACTOR_REVITALISED` | `ss` | `CL_ActorRevitalised` | none | `CL_CheckDefault` |
| `EV_ACTOR_STATS` | `!sbsbb` | `CL_ActorStats` | none | none |
| `EV_ACTOR_STATECHANGE` | `ss` | `CL_ActorStateChange` | none | `CL_CheckDefault` |
| `EV_ACTOR_RESERVATIONCHANGE` | `ssss` | `CL_ActorReservationChange` | none | none |
| `EV_ACTOR_WOUND` | `sbbb` | `CL_ActorWound` | none | none |
| `EV_INV_ADD` | `s*` | `CL_InvAdd` | `CL_InvAddTime` | `CL_CheckDefault` |
| `EV_INV_DEL` | `sbbb` | `CL_InvDel` | `CL_InvDelTime` | `CL_CheckDefault` |
| `EV_INV_AMMO` | `sbbbbb` | `CL_InvAmmo` | none | none |
| `EV_INV_RELOAD` | `sbbbbb` | `CL_InvReload` | `CL_InvReloadTime` | none |
| `EV_INV_TRANSFER` | `sbsbbbbs` | none | none | none |
| `EV_MODEL_EXPLODE` | `s&` | `CL_Explode` | `CL_ExplodeTime` | none |
| `EV_MODEL_EXPLODE_TRIGGERED` | `s&` | `CL_Explode` | none | none |
| `EV_PARTICLE_APPEAR` | `ssp&` | `CL_ParticleAppear` | `CL_ParticleAppearTime` | none |
| `EV_PARTICLE_SPAWN` | `bppp&` | `CL_ParticleSpawnEvent` | `CL_ParticleSpawnEventTime` | none |
| `EV_SOUND` | `spb&` | `CL_SoundEvent` | `CL_SoundEventTime` | none |
| `EV_DOOR_OPEN` | `s` | `CL_DoorOpen` | none | none |
| `EV_DOOR_CLOSE` | `s` | `CL_DoorClose` | none | none |
| `EV_CLIENT_ACTION` | `ss` | `CL_ActorClientAction` | none | none |
| `EV_RESET_CLIENT_ACTION` | `s` | `CL_ActorResetClientAction` | none | none |
| `EV_CAMERA_APPEAR` | `spbbbbb` | `CL_CameraAppear` | none | none |

Format codes are the legacy network format codes documented by `e_parse.cpp`; events marked manual are parsed explicitly rather than relying solely on the format string.

## 5. Authority classification

### Session/control and game-mode bridge

These must remain functional even if they never produce a Vulkan/Jolt event:

```text
EV_RESET
EV_START
EV_ENDROUND
EV_ENDROUNDANNOUNCE
EV_RESULTS
```

Notably:

- `EV_RESET` sets the player's team and active team, resets actor selection, completes client routing recalculation, and initializes round UI state.
- `EV_START` initializes battlescape camera/client state and calls `GAME_StartBattlescape`.
- `EV_ENDROUND` changes `cl.actTeam` and performs round-transition client work.
- `EV_RESULTS` transfers mission results into `GAME_HandleResults`; campaign/skirmish/multiplayer logic may consume the remainder of the result payload.

`EV_RESULTS` is therefore a critical gameplay/game-mode handoff, not a renderer event.

### Camera presentation

```text
EV_CENTERVIEW
EV_MOVECAMERA
```

These are presentation commands, but their current behavior should remain available.

### World/entity lifetime

```text
EV_ENT_APPEAR
EV_ENT_PERISH
EV_ENT_DESTROY
EV_ADD_BRUSH_MODEL
EV_ADD_EDICT
EV_MODEL_EXPLODE
EV_MODEL_EXPLODE_TRIGGERED
EV_PARTICLE_APPEAR
EV_PARTICLE_SPAWN
EV_SOUND
EV_DOOR_OPEN
EV_DOOR_CLOSE
EV_CAMERA_APPEAR
```

These range from strong mirror/client-routing events to pure presentation requests.

### Actor lifecycle and state

```text
EV_ACTOR_APPEAR
EV_ACTOR_ADD
EV_ACTOR_TURN
EV_ACTOR_MOVE
EV_ACTOR_DIE
EV_ACTOR_REVITALISED
EV_ACTOR_STATS
EV_ACTOR_STATECHANGE
EV_ACTOR_RESERVATIONCHANGE
EV_ACTOR_WOUND
```

These establish or mutate the tactical client mirror and must not be bypassed by the renderer.

### Shooting / throwing

```text
EV_ACTOR_START_SHOOT
EV_ACTOR_SHOOT
EV_ACTOR_SHOOT_HIDDEN
EV_ACTOR_THROW
EV_ACTOR_END_SHOOT
```

These form a presentation-timing sequence around authoritative combat results.

### Reaction fire

```text
EV_ACTOR_REACTIONFIRECHANGE
EV_ACTOR_REACTIONFIREADDTARGET
EV_ACTOR_REACTIONFIREREMOVETARGET
EV_ACTOR_REACTIONFIRETARGETUPDATE
EV_ACTOR_REACTIONFIREABORTSHOT
```

These are primarily tactical client/UI state plus movement-step-dependent timing.

### Inventory

```text
EV_INV_ADD
EV_INV_DEL
EV_INV_AMMO
EV_INV_RELOAD
```

These update client inventory state. `EV_INV_RELOAD` also has audio/UI behavior and updates the equipment definition's loose-clip accounting when appropriate.

They cannot be reduced to presentation-only notifications.

### Interaction state

```text
EV_CLIENT_ACTION
EV_RESET_CLIENT_ACTION
```

These establish/clear the actionable world entity associated with an actor and drive interaction UI.

## 6. Verified producer locations

Most executable events are emitted by helpers in:

```text
src/game/g_events.cpp
```

Exceptions/special cases include:

- `EV_ACTOR_MOVE`: step serialization is primarily produced by `src/game/g_move.cpp`; falling also uses the same event through `G_EventActorFall`.
- `EV_RESULTS`: produced in `src/game/g_match.cpp`.
- `EV_INV_TRANSFER`: not emitted as a normal executable event; used as a serialization format.
- `EV_NULL`: appended/used as an event-list terminator by the event transport.

## 7. Immediate-event behavior

Verified current uses include:

```text
EV_START | EVENT_INSTANTLY
EV_RESET | EVENT_INSTANTLY
```

`G_EventActorAdd` can also request `EVENT_INSTANTLY`.

The client strips the bit before validating the event number.

When set, the callback is executed immediately rather than placed on the normal presentation scheduler.

This behavior is part of compatibility.

## 8. Entity-lock scheduling

`CL_CheckDefault` checks whether the entity number at the front of the event message is currently locked by a prior event.

The following registry entries use it:

```text
EV_ACTOR_APPEAR
EV_ACTOR_MOVE
EV_ACTOR_END_SHOOT
EV_ACTOR_DIE
EV_ACTOR_REVITALISED
EV_ACTOR_STATECHANGE
EV_INV_ADD
EV_INV_DEL
```

If the entity is locked, the event is delayed.

This is an ordering dependency and must not be removed casually when the new Presentation World is introduced.

## 9. Shot/death timing state

The scheduler maintains shared timing state including:

```text
nextTime
impactTime
shootTime
parsedShot
parsedDeath
```

Important current behavior:

- `EV_ACTOR_START_SHOOT` marks a shot sequence and advances the initial presentation time.
- `EV_ACTOR_SHOOT` calculates impact time from canonical muzzle/impact distance and the fire definition's projectile speed.
- repeated shots advance `shootTime` according to `delayBetweenShots`.
- bounced shots use prior impact timing.
- `EV_ACTOR_SHOOT_HIDDEN` has its own hidden-shooter timing.
- `EV_ACTOR_THROW` receives a server-encoded duration and sets impact/shoot time from that.
- `EV_ACTOR_DIE` can be scheduled at the shot impact time.
- `EV_MODEL_EXPLODE` can be scheduled at impact time.
- `EV_ENT_APPEAR`, `EV_INV_ADD`, `EV_INV_DEL`, `EV_PARTICLE_APPEAR`, and `EV_PARTICLE_SPAWN` explicitly examine shot/death timing.
- `EV_ACTOR_END_SHOOT` clears shot/death timing flags and consumes/reset impact timing.

This shared scheduler state is a hard compatibility requirement for initial migration.

## 10. Verified legacy timing quirks that must be documented before changing

### Inventory-after-death marker

`CL_InvAddTime` treats inventory add messages as the final events sent after a death and clears `parsedDeath`.

The legacy source itself contains a TODO noting that if a dying actor has no inventory event, a later unrelated `EV_INV_ADD` could be scheduled incorrectly.

This is a known legacy timing quirk.

The remaster should not silently change it while claiming protocol parity. A fix, if desired, should be a deliberate separate compatibility change with a regression case.

### Visibility during movement

The movement callback explicitly notes that hidden movement relies on visibility events interrupting the `EV_ACTOR_MOVE` sequence.

Therefore actor visibility/lifetime events cannot be moved to an unrelated asynchronous channel without preserving this ordering relationship.

## 11. Critical state-transition finding: death is not only `EV_ACTOR_DIE`

`CL_ActorStateChange` contains a path where a living actor receiving `STATE_DEAD` is transitioned to dead client state without the normal death-animation event path.

That path:

- may play a death sound depending on stun-state transition;
- updates actor state;
- clears floor association;
- stops the think function;
- reduces the actor AABB to the dead size;
- removes the actor from the team list;
- returns without the normal `EV_ACTOR_DIE` animation path.

Therefore:

```text
PresentationEvent::ActorDied
```

must not be emitted solely by translating `EV_ACTOR_DIE`.

The bridge must derive presentation lifecycle transitions from the actual mirror-state transition semantics as well as explicit death events.

## 12. Hidden actor lifecycle

`EV_ACTOR_ADD` creates an actor as `ET_ACTORHIDDEN` with basic tactical identity/state and position.

`EV_ACTOR_APPEAR` later reveals/fully populates actors.

However, `EV_ACTOR_APPEAR` can also create the local entity directly if it does not already exist, which occurs during initial mission population.

Therefore the dependency is:

```text
hidden actor case:
EV_ACTOR_ADD -> later EV_ACTOR_APPEAR

mission-start/direct-visible case:
EV_ACTOR_APPEAR may create the actor itself
```

`EV_ACTOR_ADD` is required by the full protocol but is not an unconditional prerequisite for every actor appearance.

## 13. Brush model / door / breakable lifecycle

`EV_ADD_BRUSH_MODEL` establishes local entities for:

- breakables;
- rotating doors;
- sliding doors;
- rotating entities;
- rescue/next-map triggers.

It stores data including:

- entity type;
- model index;
- level flags;
- origin;
- angles;
- speed;
- angle;
- direction;
- AABB/size;
- inline model identity.

It also participates in client collision/routing representation.

Thus:

```text
EV_ADD_BRUSH_MODEL
      |
      +--> EV_DOOR_OPEN / EV_DOOR_CLOSE
      +--> EV_MODEL_EXPLODE / EV_MODEL_EXPLODE_TRIGGERED
      +--> EV_CLIENT_ACTION references where applicable
```

The new Jolt representation is not a replacement for this canonical/client-routing representation.

## 14. Generic entity and particle lifecycle

`EV_ENT_APPEAR` creates or reactivates generic local entities.

For `ET_PARTICLE`, the entity is initially made invisible because a later particle event supplies the particle presentation.

`EV_PARTICLE_APPEAR` requires the referenced local entity to already exist.

Thus a current dependency is:

```text
EV_ENT_APPEAR (ET_PARTICLE)
        ->
EV_PARTICLE_APPEAR
```

`EV_ENT_PERISH` has type-specific cleanup, including:

- floor-item inventory unlinking;
- actor inventory destruction/animation clearing;
- particle destruction;
- visibility changes.

It is not merely a visual hide command.

## 15. Sound semantics

`EV_SOUND` carries:

- entity number;
- world origin;
- movement step byte;
- sound asset string.

The server uses two important forms:

- ordinary sound: step byte `0xFF`;
- queued footstep/movement sound: actual actor move-step index.

`CL_SoundEventTime` uses the actor movement step timing when applicable.

Current footstep spatialization also contains a legacy client behavior that temporarily evaluates the sound relative to the closest friendly actor rather than simply using the camera listener position.

Baseline 034 accepts `AUDIO-FIDELITY-001` choice A: preserve that behavior for v1. ADR-042/architecture 035 own the remaster implementation rule. The compatibility behavior is applied as a per-event start-spatialization reference; it does not mutate the stable process-wide OpenAL listener.

It must not affect canonical AI/sound detection because none of this client audio logic is canonical.

## 16. Camera entity note

`EV_CAMERA_APPEAR` transmits a direction value.

The current callback decodes that value into a local variable but sets yaw using `le->angle`, without assigning the transmitted `dir` to `le->angle` in that callback.

This appears to be a legacy presentation discrepancy.

Baseline 034 accepts `CAMERA-FIDELITY-001` choice B: use the transmitted `dir` for the remaster camera-model yaw. ADR-043 owns this intentional presentation-only legacy bug fix; the tactical protocol and canonical gameplay remain unchanged.

## 17. Complete compatibility conclusion

A complete remaster bridge cannot be defined as a short list of visually interesting events.

The correct compatibility target is:

```text
all 48 event_t protocol entries accounted for
all 46 executable callbacks preserved or replaced
EV_NULL termination preserved
EV_INV_TRANSFER helper-format behavior preserved
all timing/order dependencies preserved
all client mirror/control mutations preserved
```

A smaller subset remains valid only as an incremental integration slice while the rest of the legacy path remains active.

## Baseline 034 fidelity decision closure

The two presentation-only discrepancies identified in sections 15–16 are resolved:

```text
AUDIO-FIDELITY-001   ACCEPTED A — preserve closest-friendly start spatialization for v1
CAMERA-FIDELITY-001  ACCEPTED B — consume transmitted dir and fix camera-model yaw
```

See ADR-042, ADR-043 and `../design/002-baseline-031-deep-audit-decision-gates.md`.
