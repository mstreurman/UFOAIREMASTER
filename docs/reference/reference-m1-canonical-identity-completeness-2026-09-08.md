# Reference — M1 Canonical Identity Completeness Pass

**Date:** 2026-09-08
**Artifact baseline:** `0af7d502ea9b3b866b91dd98ffe7150391d88005`
**Status:** local qualification required

## Purpose

Audit every currently known presentation-facing strategic/tactical reference and make the identity rules explicit before more owner extraction hardens raw indices into public contracts.

This is a boundary/contract slice. It does **not** change canonical game rules, production rules, facility rules, transfer rules, defence rules, save data, balance, or simulation outcomes.

## Strong ID domains after this pass

The C++11 canonical identity header contains 17 distinct 32-bit domains including the generic tactical protocol `EntityId`:

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

New strong domains introduced here:

```text
FacilityId
TransferId
DefenceSlotId
```

These names reserve safe public identity domains. They do not claim that a stable legacy mapping already exists.

## Identity taxonomy

### Runtime direct
Use an existing canonical value whose lifetime already matches the runtime object.

### Runtime sidecar required
Legacy storage has no stable per-logical-object value, or its current index compacts. The canonical boundary owns the stable mapping. Presentation never derives one from a pointer, array offset, or mutable ordinal.

### Structural reference
A coordinate inside a stable owner is not automatically a runtime object. Examples: aircraft equipment slots, facility placement cells, and strategic positions.

### Static definition key
Script/content definitions are not mutable runtime entities.

### Submission/context token
`TransferManifestId` is not an active transfer identity. Legacy transfer construction uses temporary staging state; active transfers are separate `transfer_t` objects in `ccs.transfers`.

```text
TransferManifestId = request/staging context
TransferId         = active canonical transfer
```

## Hazards found

### Production queue index
`queueIndex` is location/order metadata only. Queue move/delete can make the same index refer to another logical production. Production mutations remain fail-closed until a stable `ProductionId` mapping exists.

### Facility index
`building_t::idx` is base-local and facility removal can compact/renumber entries. `DestroyFacility` is already qualified through the current legacy-index bridge, so this pass records explicit migration debt rather than changing gameplay behavior. New presentation must not treat that integer as a persistent facility identity.

### Defence slot index
Base/installation defence batteries are addressed through mutable array ordinals. `DefenceSlotId` is reserved now; defence mutation stays pending until its stable mapping is implemented.

### Message sidecar
The current `MessageId` adapter uses a legacy message-node pointer sidecar. This pass does not assert that pointer reuse is a bug; it records a focused lifetime audit before declaring the mapping generation-safe for an entire campaign/load lifetime.

## Existing ID contract gap repaired

The standalone C++11 identity contract previously covered only 11 domains. It did not include the later-added:

```text
StoredUfoId
UfoSaleOfferId
TransferManifestId
```

The contract now covers all 17 domains, including the three new ones, for distinctness, 32-bit shape, explicit integer construction, cross-domain non-constructibility, invalid/default semantics and equality.

## Publication documentation correction

Architecture 078's conceptual snapshot is updated to include the already-implemented technology and production categories.

## Authority accounting

This pass changes no intent disposition:

```text
strategic: 15 canonical-applied / 42 fail-closed
tactical:  13 server-forwarded / 2 fail-closed
```

## Follow-on ordering

1. wire/publish direct identities needed by the next screen family;
2. extract clean Research owners using published `TechnologyId`;
3. implement stable `ProductionId` before production queue mutation;
4. migrate facility destruction to `FacilityId` before new presentation originates it;
5. add `TransferId` with active transfer publication;
6. add `DefenceSlotId` mapping before air-defence mutation bridging;
7. audit/harden `MessageId` lifetime semantics.
