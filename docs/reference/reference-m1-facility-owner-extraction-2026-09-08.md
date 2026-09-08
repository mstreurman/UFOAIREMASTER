# Reference — M1 Base facility canonical-owner extraction

**Date:** 2026-09-08
**Artifact baseline:** `e02dc60d8ab8321431d8a9b1dfc525c1d0b6a05f`
**Scope:** third strategic canonical-owner extraction slice

## Result

This slice extracts two additional strategic facility actions into canonical campaign ownership:

```text
BuildFacility
DestroyFacility
```

Expected authoritative bridge accounting after qualification:

```text
strategic authoritative semantics: 57 / 57 typed
strategic canonical-applied:        15 / 57
strategic fail-closed pending:      42 / 57

tactical authoritative semantics:  15 / 15 typed
tactical server-forwarded:          13 / 15
tactical fail-closed pending:        2 / 15
```

No command-string or cvar fallback is introduced in the strategic intent adapter.

## BuildFacility owner

`B_TryBuildFacility(base, definition, column, row, out)` owns the mutation callback's source-derived checks and delegates construction to `B_BuildBuilding`:

```text
base pointer exists
facility definition resolves to a building template
column/row are inside the 5x5 base grid
facility footprint fits the grid
existing CP_CheckCredits(fixCosts) gate passes
B_BuildBuilding accepts occupancy/coherency and performs the canonical construction mutation
```

The owner deliberately does **not** invent research or max-count mutation gates. The legacy source currently applies those when listing/selecting build options (`B_ListBuildings_f` / `B_FillBuildingInfo_f`), not in the final `B_BuildBuilding_f` mutation callback. A future rule-normalization slice may decide to promote them, but M1 owner extraction preserves current mutation semantics.

The legacy callback keeps presentation effects: invalid-input diagnostics, insufficient-credit popup, placement sound, and return to the Bases UI.

## DestroyFacility owner

The existing typed contract already carries `(BaseId, facilityIndex)`. In canonical base storage, `building_t::idx` is a base-scoped compact index, so this slice makes that mapping explicit with `B_GetBuildingByIDXSafe`.

Important identity rule:

```text
facilityIndex is current-snapshot and base-scoped
facilityIndex is compacted when another facility is removed
facilityIndex is not a persistent/stable presentation identity
```

`B_CheckDestroyFacility` owns the actual preflight gates formerly in `B_BuildingDestroy_f`:

```text
base/facility resolve
base is not under attack
facility is not the base entrance
removal does not break base-building connectivity
```

`B_TryDestroyFacility` represents an **already-confirmed** destructive request. It re-runs the canonical preflight and then delegates to `B_BuildingDestroy`, which retains liquidation, capacity/status updates, onDisable/onDestroy event processing, overflow cleanup and the actual mutation.

Capacity-sensitive warning choice remains presentation policy. The legacy callback still chooses the Alien Containment / Hangar / Quarters / Storage warning and confirmation UI before it sends the confirmed request. New presentation must likewise submit `DestroyFacility` only after its own confirmation flow.

## Removing low-level presentation refresh coupling

Before this slice, both low-level canonical mutations executed:

```text
Cmd_ExecuteString("base_init ...")
```

`B_BuildBuilding` and `B_BuildingDestroy` no longer do that. The equivalent refresh is retained only in the legacy callbacks after successful interactive build/destroy. This prevents typed canonical execution from implicitly invoking legacy Bases UI refresh while preserving legacy presentation behavior.

Canonical script events fired by `B_FireEvent` remain canonical campaign behavior during M1; this slice does not rewrite the campaign script/event system.

## DestroyAntimatterFacility remains fail-closed

The inventory row named `DestroyAntimatterFacility` maps to `B_Destroy_AntimaterStorage_f`, but that function is the internal probabilistic `onDestroy` breach event. It consumes a probability/base/type callback payload, removes excess antimatter, and can destroy the entire base. It is not equivalent to the typed `(BaseId, facilityIndex)` presentation contract.

This slice therefore leaves `DestroyAntimatterFacility` fail-closed and records the mismatch explicitly for later inventory reclassification or contract correction. Normal user destruction of an antimatter-storage building already flows through `DestroyFacility` -> `B_BuildingDestroy` -> canonical `B_FireEvent`.

`StartMission` remains fail-closed in its dedicated later extraction scope.

## Qualification expectations

Focused M1 lanes:

```bash
python3 tools/remaster/test-m1-aircraft-geoscape-owner-extraction.py
python3 tools/remaster/test-m1-base-installation-owner-extraction.py
python3 tools/remaster/test-m1-facility-owner-extraction.py
python3 tools/remaster/test-m1-authoritative-intent-surface.py
```

Canonical preservation gate:

```bash
python3 tools/remaster/run-m0-canonical-regression.py --verify
```

Expected unchanged digest:

```text
33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2
```

Fresh legacy and remaster production builds remain required before qualification.
