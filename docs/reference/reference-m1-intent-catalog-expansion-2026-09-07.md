# Reference — M1 Strategic + Tactical Intent Catalog Expansion Qualification

**Date:** 2026-09-07  
**Status:** PASS  
**Scope:** first breadth expansion of the qualified M1 typed-intent mechanism  
**Reference compiler:** GCC 16.2.1  
**Canonical evidence:** `33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2`

## Qualified catalog

### Strategic

The strategic catalog now contains five typed presentation intents:

```text
SetCampaignTimeLapse
SelectMission
SelectAircraft
SendAircraftToMission
ReturnAircraftToBase
```

The first entry was already qualified by the foundational typed-intent lane. The four new entries extend the same bounded transport and Main/campaign adapter.

Canonical owner mapping:

```text
SelectMission(MissionId)
    -> MIS_GetByIdx
    -> GEO_SelectMission

SelectAircraft(AircraftId)
    -> AIR_AircraftGetFromIDX
    -> GEO_SelectAircraft

SendAircraftToMission(AircraftId, MissionId)
    -> AIR_AircraftGetFromIDX
    -> MIS_GetByIdx
    -> AIR_SendAircraftToMission

ReturnAircraftToBase(AircraftId)
    -> AIR_AircraftGetFromIDX
    -> AIR_IsAircraftOnGeoscape
    -> AIR_AircraftReturnToBase
```

Typed IDs are resolved to legacy pointers only inside the retained C++11 adapter. No raw campaign pointer enters the shared public contract.

## Tactical catalog

The first tactical typed-intent catalog contains:

```text
SetReactionFire(EntityId, bool)
SetReservedTimeUnits(EntityId, shotTus, crouchTus)
```

These do **not** mutate tactical canonical state in the client adapter.

Qualified flow:

```text
presentation
    -> bounded strict-C++26 tactical intent transport
    -> retained C++11 client-Main adapter
    -> existing PA_* tactical request protocol
    -> game server
    -> authoritative server validation/mutation
    -> existing EV_* response/event path
    -> tactical publication/presentation
```

Protocol mapping:

```text
SetReactionFire
    -> PA_STATE
    -> G_ClientStateChange(..., true)

SetReservedTimeUnits
    -> PA_RESERVE_STATE
    -> G_ActorReserveTUs(...)
```

## Tactical result semantics

The tactical result vocabulary is intentionally:

```text
ForwardedToServer
RejectedByClientBoundary
```

and intentionally does **not** contain:

```text
Applied
```

`ForwardedToServer` means only that the retained client boundary successfully translated the typed intent into the existing tactical protocol.

It is not canonical acceptance.

The authoritative tactical result remains the server decision and resulting event/publication stream.

## Client-boundary validation

The tactical adapter rejects before network forwarding unless:

```text
client state == ca_active
network stream exists
battlescape is running
EntityId is valid and inside the edict domain
matching local entity is in use
entity is an actor
actor belongs to the local team/player
```

Negative shot/crouch reservation values are rejected locally.

These checks protect the client/protocol boundary. They do not replace server validation.

## Runtime ownership

The strict-C++26 intent runtime target now owns both:

```text
strategic_intent_dispatch.cpp
tactical_intent_dispatch.cpp
```

Both use:

```text
pending queue capacity: 256
result queue capacity: 256
process-monotonic sequence IDs
bounded FIFO semantics
lifetime reset without sequence reuse
```

The retained legacy/Main adapters remain C++11.

## Focused qualification

Command:

```bash
python3 tools/remaster/test-m1-intent-catalog-expansion.py
```

Result:

```text
M1 intent catalog expansion lane: PASS
  strategic catalog: 5 typed intents
  tactical catalog: 2 typed server-forwarded intents
  strict C++11 public contracts: PASS
  strict C++26 bounded runtimes: PASS
  FIFO/capacity/reset/sequence contracts: PASS
  strategic canonical-owner mappings: PASS
  tactical PA_STATE/PA_RESERVE_STATE server-authority mapping: PASS
  integration GoogleTests: 3/3
  sealed src/tests/CMakeLists.txt: unchanged
```

Integration tests:

```text
SelectMissionUsesTypedIdentityAndPublishesSelection
InvalidStrategicIdentitiesAreRejectedInOrder
TacticalIntentNeverClaimsCanonicalApplicationAtClientBoundary
```

The positive tactical server mutation is intentionally not faked in this client-only integration fixture; source/ownership audits verify the real PA_* to server-handler path.

## Preservation evidence

After this source slice, the canonical preservation corpus remained:

```text
104/104 PASS
104/104 PASS
two-run trace repeatability: PASS
```

Current M0.5 evidence identity remained:

```text
33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2
```

Therefore this catalog expansion introduced no canonical evidence drift.

## Fresh production builds

Legacy:

```text
[391/391] Linking CXX executable ufo
PASS
```

Remaster:

```text
M0 dependency discovery: PASS
OpenAL: 1.25.2
[5/5] Linking CXX executable ufo
PASS
```

## M1 conclusion

The project now has qualified strategic and tactical typed-intent **seed catalogs** behind the already-qualified transport architecture.

This closes the initial catalog-expansion checklist item.

It does not mean the eventual presentation command surface is complete.

Future catalog growth must remain tied to real owning presentation migrations and existing canonical/server authority.

Likely next strategic actions:

```text
SetAircraftDestination
OpenBase
BuildFacility
AssignResearch
BuyItem / SellItem
StartMission
SaveGame / LoadGame
```

Likely later tactical actions:

```text
MoveActor
TurnActor
Shoot
Use
InventoryMove
ReactionFireSettings
```

Richer tactical actions should be added with matching server-authority fixtures rather than merely enlarging the enum.
