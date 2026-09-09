# M1 second-pass canonical identity audit — save/wire lifetime qualification

**Baseline:** `d10c58e4d6e826db89c4a4c7c7bfcbaf8c3dd903`  
**Date:** 2026-09-09

## Scope

This is a source-derived second pass over canonical presentation identities and identity-shaped values. It classifies each value independently across:

1. canonical runtime lifetime;
2. save/load lifetime;
3. tactical wire lifetime;
4. presentation encoding/resolution lifetime.

It deliberately makes **no canonical gameplay change, no save-format change, no wire-format change, and no new strong-ID type**.

## Result

The existing strong-ID set remains **17 distinct 32-bit domains**:

```text
EntityId
MissionId
AircraftId
BaseId
InstallationId
NationId
EmployeeId
TechnologyId
ProductionId
FacilityId
TransferId
DefenceSlotId
MessageId
ItemId
StoredUfoId
UfoSaleOfferId
TransferManifestId
```

Authority accounting remains unchanged:

```text
strategic: 24 canonical-applied / 34 fail-closed
tactical:  13 server-forwarded / 2 fail-closed
```

## Main findings

### 1. `CharacterUcn` is a correlation key, not tactical entity identity

The examined source establishes these facts:

```text
CL_GenerateCharacter
    -> chr->ucn = cls.nextUniqueCharacterNumber++

GAME_SaveCharacter / GAME_LoadCharacter
    -> UCN persisted in character save data

E_GetEmployeeFromChrUCN
    -> campaign employee lookup by UCN

tactical actor/result traffic
    -> UCN written/read as a short

TacticalActorView
    -> characterUcn exposed read-only
```

Therefore UCN is a persistent/network **correlation key**. Tactical mutation identity remains `EntityId` / server entity number.

`EmployeeId` is **not** promoted to qualified in this pass. Before using UCN as a long-lived typed mutation key, M1 still needs a dedicated qualification proving:

- allocator restoration/reconciliation and non-reuse across campaign/team load;
- the inherited 16-bit wire representation is sufficient for the supported lifetime/epoch.

This second-pass audit records that work as debt. It does not claim that allocator reconciliation is absent everywhere in the tree, and it does not claim an observed collision.

### 2. `ItemId` is content-definition identity, not item-instance identity

Save/inventory paths use item script IDs. Tactical reaction-fire selection passes an `objDef_t::idx` ordinal, and the server resolves it with:

```text
INVSH_GetItemByIDX(objIdx)
```

That means the relevant identity is the static/content definition. `ItemId` remains pending until M1 explicitly qualifies the runtime definition ordinal together with the stable script/content key.

This also means compatible multiplayer depends on the same qualified canonical content revision when protocol fields carry definition ordinals.

### 3. `FacilityId` remains real debt

`building_t::idx` is base-local and may compact. It is not a safe long-lived facility identity.

A generation-safe runtime mapping is still required before long-lived facility mutation can rely on `FacilityId`.

### 4. `TransferId` remains real debt

`transfer_t` has no native identity. The inherited transfer save format stores endpoints/timing/contents but not an active-transfer identity.

The preferred M1 direction is a runtime identity rebuilt after load, rather than extending the inherited save schema merely for presentation/bridge convenience.

### 5. `DefenceSlotId` remains real debt

`baseWeapon_t` lives in base/installation arrays without a native logical identity. Slot ordinals are currently structural/location values.

M1 must either prove a stable structural tuple is sufficient or introduce a generation-safe runtime identity.

### 6. `MessageId` remains runtime-only/read-only debt

Current `MessageId` is a pointer-keyed sidecar owned by the strategic snapshot adapter and reset with that adapter.

That is sufficient for current read-only publication, but pointer-address reuse must be proven harmless or removed before any mutation/campaign-lifetime semantics use `MessageId`.

### 7. `AircraftId` UFO high bit is presentation encoding only

The high-bit namespace used to distinguish PHALANX aircraft from UFOs is a presentation encoding. It is **not** a save-field or tactical-wire representation and must not silently leak into either compatibility boundary.

## Explicit non-entity/reference categories

These values cross or influence the presentation boundary but should not be silently promoted into entity IDs:

```text
ProductionQueueIndex
AircraftEquipmentSlot
FacilityPlacementCell
StrategicPosition
AircraftDefinitionKey
FacilityDefinitionKey
InstallationDefinitionKey
UgvDefinitionKey
UfoDefinitionKey
SaveSlotKey
ContainedAlienSpecies
CharacterUcn
InventoryContainerRef
InventoryCell
TacticalItemDefinitionIndex
TacticalGridCell
TacticalPlayerNumber
TacticalTeamNumber
```

## Compatibility rule derived by this pass

Within the current save/wire compatibility epoch:

- runtime-only bridge/presentation IDs should normally regenerate after load;
- presentation namespace encodings do not become save/wire ABI;
- content-definition ordinals on the wire are valid only for the same qualified canonical content revision;
- mutable ordinals/coordinates remain structural values unless a separate lifetime proof establishes object identity;
- stale IDs reject against current canonical state rather than rebinding to whatever currently occupies an old ordinal.

## Remaining M1 identity work

Recommended order:

1. qualify UCN allocator restoration/non-reuse and the 16-bit wire bound;
2. qualify/publish `ItemId` plus aircraft production-definition subjects;
3. complete production-subject publication;
4. extract canonical `CreateProduction`;
5. continue stored-UFO/recovery owner work;
6. implement Facility/Transfer/Defence runtime identity mappings;
7. qualify Message/UFO-sale-offer generation lifetimes.
