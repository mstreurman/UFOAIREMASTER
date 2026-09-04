# ADR-010 — Preserve the Complete Legacy Tactical Event Protocol During Migration

**Status:** Accepted  
**Decision type:** Compatibility / tactical client migration  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`

## Context

UFO: Alien Invasion already has an explicit tactical event protocol between the authoritative tactical game/server and the battlescape client.

The protocol is defined by `event_t` in:

```text
src/game/q_shared.h
```

and registered on the client in:

```text
src/client/battlescape/events/e_main.cpp
```

The remaster presentation runtime will be introduced incrementally.

A subset of events is useful for early Vulkan/Jolt/OpenAL integration, but such a subset is not sufficient to replace the legacy tactical client event system.

## Verified protocol shape

At the source baseline commit there are **48 enum entries before `EV_NUM_EVENTS`**, including `EV_NULL`.

Two entries are special:

- `EV_NULL` is the event-list terminator/null marker and is not dispatched as a normal event.
- `EV_INV_TRANSFER` has a registered wire-format string but deliberately has no client callback; its format is reused for item serialization/deserialization.

Therefore the current client registry contains **46 executable event types** in addition to those two special protocol entries.

## Decision

The remaster will preserve the complete current tactical event protocol during migration.

Specifically:

1. Existing `event_t` numeric ordering is preserved.
2. Existing wire formats are preserved initially.
3. Existing event ordering and scheduling semantics are preserved.
4. Existing immediate-event (`EVENT_INSTANTLY`) behavior is preserved.
5. Existing entity-lock/check semantics are preserved until their replacement is proven equivalent.
6. Every currently executable event continues to have valid handling during migration.
7. Events not yet migrated to the new Presentation World keep their legacy client callback path.
8. A new presentation consumer may be disabled without changing canonical outcomes.
9. No event may be deleted merely because the new renderer does not use it.
10. A protocol change requires a separate versioned compatibility decision.

## Migration model

The allowed incremental pattern is:

```text
legacy EV_* decode
      |
      +--> preserve existing mirror/control behavior
      |
      +--> emit new typed PresentationEvent where implemented
      |
      +--> legacy presentation fallback where still required
```

Later:

```text
legacy EV_* decode
      |
      +--> canonical client mirror/control projection
      |
      +--> typed PresentationEvent
             |
             +-- Vulkan
             +-- animation
             +-- Jolt
             +-- OpenAL
             +-- UI/VFX
```

Only after parity is demonstrated may a legacy presentation callback be removed.

## Important verified dependencies

The source audit identified several dependencies that prohibit treating a small visual-event subset as standalone:

- `EV_ACTOR_ADD` creates hidden actors before later visibility events.
- `EV_ACTOR_APPEAR` may also create an actor directly when one does not already exist, such as at mission start.
- `EV_ADD_BRUSH_MODEL` establishes doors/breakables before open/close/explosion events can operate on them.
- `EV_ACTOR_START_SHOOT`, shot events, impact timing, death, particles, inventory drops, sounds, and `EV_ACTOR_END_SHOOT` share scheduler state.
- `EV_ENT_APPEAR` precedes later data for some entity types, including particle entities and dropped items.
- `EV_PARTICLE_APPEAR` requires the referenced local entity to already exist.
- `EV_CLIENT_ACTION` requires both actor and actionable entity to already exist.
- `EV_SOUND` can be synchronized to an actor movement step.
- `EV_ACTOR_STATECHANGE` can itself transition a living actor to a dead state without an `EV_ACTOR_DIE` animation event.
- `EV_RESULTS` is a mission-to-game-mode/campaign result bridge and is not presentation-only.
- inventory/reload events update client inventory/equipment state in addition to audiovisual presentation.

## Consequence

The first remaster integration slice may still focus on visually important events, but it must run alongside the complete legacy event handling until the full bridge is implemented.

The initial visual subset is a **prototype/migration subset**, not the definition of the complete tactical bridge.

## Validation requirement

Before the legacy battlescape event callbacks can be considered replaceable, the remaster must demonstrate:

- all 48 protocol entries accounted for;
- all 46 executable events decoded correctly;
- `EV_NULL` termination preserved;
- `EV_INV_TRANSFER` helper-format behavior preserved;
- equivalent mirror/control mutations;
- equivalent dependency ordering;
- equivalent event scheduling;
- equivalent interaction-state effects;
- equivalent mission-result handoff;
- presentation consumers isolated from canonical authority.
