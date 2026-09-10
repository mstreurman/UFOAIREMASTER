# M1 ItemId and production-subject qualification

**Baseline:** `128b8a8a95531e5d5a53b1e4b91efc71b425c9ca`

**Date:** 2026-09-09

## Purpose

This slice closes the identity/publication prerequisites that keep `CreateProduction`
fail-closed. It does not extract or enable the `CreateProduction` owner.

The three production subject forms remain distinct:

```text
item production        -> ItemId + item script-ID definition catalog
aircraft production    -> AircraftDefinitionKey (script ID)
stored-UFO disassembly -> StoredUfoId
```

No per-storage-item instance identity and no aircraft-template runtime entity ID are introduced.

## ItemId qualification

`objDef_t` carries both a current-content ordinal (`idx`) and stable script key (`id`).
`Com_ParseItem` assigns `idx` from canonical parse order, inherited tactical definition
fields resolve that ordinal with `INVSH_GetItemByIDX`, while campaign production saves
persist the script ID and reconstruct the definition on load.

Therefore `ItemId` is qualified as a current-canonical-content identity, not a
cross-content-version database ID.

## Aircraft production identity

Aircraft production jobs already save/load the aircraft template by `aircraft_t::id`.
That remains a static definition key. `AircraftId` remains reserved for runtime aircraft/UFO
instances.

## Publication

The strategic snapshot gains immutable value-only item and aircraft definition catalogs.
`StrategicProductionView` gains typed `item`, `storedUfo`, and `aircraftDefinition`
subject fields. Exactly the field matching the production type is populated.

## Compatibility and authority

No save or wire schema changes are made. `SAVE_FILE_VERSION` remains 4 and
`PROTOCOL_VERSION` remains 18.

`CreateProduction` remains fail-closed, so authority remains:

```text
strategic: 24 canonical-applied / 34 fail-closed
tactical:  13 server-forwarded / 2 fail-closed
```

## Next step

After this slice qualifies and lands, extract a canonical `CreateProduction` owner that
re-resolves and validates the published typed subject against current canonical state.
