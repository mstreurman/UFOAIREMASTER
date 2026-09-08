# Reference — M1 Base + Installation lifecycle canonical-owner extraction

**Date:** 2026-09-08  
**Artifact baseline:** `4be6dcda5e0a3f9de09a5abc294fd5c35a28478a`  
**Scope:** second strategic canonical-owner extraction slice

## Result

This slice extracts five additional strategic lifecycle actions into canonical campaign owners:

```text
BuildBase
RenameBase
BuildInstallation
RenameInstallation
DestroyInstallation
```

After this slice the authoritative strategic bridge ledger is expected to be:

```text
strategic authoritative semantics: 57 / 57 typed
strategic canonical-applied:        13 / 57
strategic fail-closed pending:      44 / 57
```

Tactical accounting remains `13 forwarded / 2 fail-closed`. No presentation command-string or cvar fallback is introduced.

## Shared placement rule

`GEO_IsValidLandPosition` centralizes the existing geoscape placement rule used by both legacy click handling and the new campaign owners. It validates finite longitude/latitude, enforces geoscape bounds, and rejects water using the canonical terrain mask. `GEO_Click` consumes the helper instead of duplicating the land test.

## Base lifecycle owner rules

`B_TryBuildBase` owns the source-derived construction rules that were split between geoscape and `B_BuildBase_f`: active campaign, base-count/slot limit, valid land position, the existing strict credit check (`credits - basecost > 0`), legacy invalid-name fallback, `B_Build`, credit mutation, canonical construction message, and first-base setup. The legacy callback retains interaction-only state, legacy cvar synchronization and presentation selection/popups.

`B_TrySetName` owns the existing `Com_IsValidName` gate and `B_SetName` mutation. The legacy callback retains only its invalid-name cvar restoration.

## Installation lifecycle owner rules

`INS_TryBuildInstallation` unifies the already-existing source gates from installation type selection, geoscape placement, and the build callback: installation-count limit, researched technology, once-only template restriction, valid land position, strict credit check, `INS_Build`, credit mutation and canonical construction message.

`INS_TrySetName` owns the existing bounded `Q_strncpyz` installation-name mutation without inventing a new validation rule.

`INS_TryDestroyInstallation` represents an **already-confirmed** destructive intent and delegates canonical removal to `INS_DestroyInstallation`. Legacy UI keeps the confirmation dialog; new presentation must only submit `DestroyInstallation` after its own confirmation flow.

## Deliberately deferred facility internals

The following remain fail-closed in this slice:

```text
BuildFacility
DestroyFacility
DestroyAntimatterFacility
```

Reasons:

- `BuildFacility` still has source rules split between UI listing/selection (research/max-count visibility) and `B_BuildBuilding`; the lower-level path also still executes a legacy `base_init` command as migration-era UI synchronization.
- `DestroyFacility` is not yet identity-clean: the typed contract carries `facilityIndex`, while the legacy callback resolves a building by base-grid `(column,row)` and contains capacity-sensitive confirmation branches for alien containment, hangars, quarters and storage.
- `DestroyAntimatterFacility` is currently mapped to an antimatter-storage **breach onDestroy callback** whose inputs/semantics include probability and can destroy the whole base. That is not equivalent to the current typed `(BaseId, facilityIndex)` contract and must not be guessed.

`StartMission` also remains fail-closed and retains its dedicated later extraction scope.

## Existing migration debt retained intentionally

Two pre-existing low-level functions still contain legacy presentation synchronization:

```text
B_Build                    -> B_SetCurrentSelectedBase -> legacy selection cvars
INS_DestroyInstallation    -> mn_installation_count cvar update
```

This slice does not expand or copy those side effects into the presentation adapter. They remain explicit cleanup debt for later canonical/presentation decoupling. The strict adapter guard still rejects direct `Cmd_ExecuteString`, `Cbuf_AddText`, `Cvar_Set` and `Cvar_SetValue` use.

## Qualification expectations

```bash
python3 tools/remaster/test-m1-aircraft-geoscape-owner-extraction.py
python3 tools/remaster/test-m1-base-installation-owner-extraction.py
python3 tools/remaster/test-m1-authoritative-intent-surface.py
python3 tools/remaster/run-m0-canonical-regression.py --verify
```

The canonical regression digest is expected to remain:

```text
33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2
```

Fresh legacy and remaster production builds remain required before qualification.
