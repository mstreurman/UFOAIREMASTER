# Presentation Action Authority, Scope, and Intent Completeness Contract

**Status:** M1 implementation contract — v3 classification sealed; owner extraction in progress
**Accepted:** 2026-09-07  
**Qualified source baseline:** `1dd974017f25d5bda5cc5b82b48d2590e574e50f`  
**Current implementation baseline:** `46c6c3ca9fb808f7c5bdb8c665b79ef378a3cabf` plus qualified LoadLastSave explicit-context normalization
**Supersedes:** v1 command-only inventory interpretation of this document

## 1. Purpose

The remaster must classify presentation-originated actions by authority before defining the remaining strategic/tactical typed intent surface.

The v1 capture proved command tables are useful, but also exposed that command registration is both over-inclusive and incomplete. v2 therefore separates **scope** from **authority** and adds direct-entry/protocol discovery.

## 2. Scope before authority

Every discovered entry point receives a scope:

```text
PRESENTATION_ACTION
PRESENTATION_PROJECTION
SESSION_CONTROL
APPLICATION_PERSISTENCE
CANONICAL_LIFECYCLE
CANONICAL_MAINTENANCE
SCRIPTED_CANONICAL_EVENT
MULTIPLAYER_SESSION
SKIRMISH_SESSION
DEBUG_TOOLING
INTERNAL_PROTOCOL
UNCLASSIFIED_SCOPE
```

Only `PRESENTATION_ACTION` participates in the five-way presentation authority model.

`UNCLASSIFIED_SCOPE` is a completeness blocker.

## 3. Five presentation authority classes

For `PRESENTATION_ACTION`, exactly one final semantic authority class must apply:

```text
PRESENTATION_ONLY
PRESENTATION_CONTEXT
READ_ONLY
STRATEGIC_CANONICAL
TACTICAL_SERVER
```

Analysis-only states:

```text
SPLIT_REQUIRED
UNCLASSIFIED
```

`SPLIT_REQUIRED` means one legacy entry point contains multiple semantic actions and must be decomposed before the typed API is sealed.

## 4. Presentation-only

Window navigation, tabs, camera/focus/zoom, UFOPedia, tooltips, sorting/filtering, confirmation UI and notification preferences remain inside presentation.

They do not become gameplay intents.

## 5. Presentation context

Viewed/selected base, mission, aircraft, actor, fire mode, move mode, pending confirmations and placement staging may carry typed IDs but are not authority.

Gameplay intents should carry explicit authority-bearing IDs rather than infer them from hidden selection globals.

## 6. Read-only

Legacy callbacks that project canonical/mirror state into UI become immutable snapshots or typed view models.

They are not intents.

Incidental maintenance inside a read callback must be split before deletion.

## 7. Strategic canonical

```text
presentation
 -> StrategicIntent(explicit typed payload)
 -> Main/campaign adapter
 -> canonical validation
 -> mutation or rejection
 -> StrategicIntentResult
 -> immutable strategic publication
```

Results remain `Applied` / `RejectedByCanonical`.

## 8. Tactical server

```text
presentation
 -> TacticalIntent(explicit typed payload)
 -> client Main adapter
 -> existing client/server request protocol
 -> game server
 -> server validation/mutation
 -> EV_* events
 -> tactical mirror/publication
```

Client transport results remain `ForwardedToServer` / `RejectedByClientBoundary`, never `Applied`.

## 9. Direct-entry requirement

Command registration is not a complete presentation input inventory.

The source-proven example is:

```text
MapClick -> GEO_Click
```

`GEO_Click` handles presentation selection/placement and also contains the legacy aircraft-route mutation.

At v2 discovery time it remained `SPLIT_REQUIRED`; the v3 decomposition registry subsequently split it into:

```text
presentation selection/focus
base/installation placement staging
SetAircraftDestination(AircraftId, GeoPosition)
```

## 10. Protocol requirement

Tactical completeness must cover both `MSG_Write_PA(PA_*)` and non-PA requests that represent player actions.

Known non-PA examples:

```text
clc_endround -> EndTurn
sv win       -> AbortMission
```

Packet/request opcodes are authority evidence, not public intent names.

## 11. Comment-aware discovery

The scanner ignores:

```text
// comments
/* block comments */
#if 0 ... #endif
```

while preserving line numbers.

This fixes the v1 false-positive from a commented `ui_aircraft_changename` registration in `cl_map_callbacks.cpp`.

## 12. Function-body evidence

v2 records:

```text
PA_* kinds
UI/popup/sound signals
hidden current/selected-state dependencies
canonical mutation hints
preprocessor guard
handler body SHA-256
```

This fixes v1's broken body-analysis totals.

## 13. Mixed and split legacy functions

A canonical action with popup/sound side effects remains `STRATEGIC_CANONICAL`; those side effects move to presentation reaction.

Legacy umbrellas that contain distinct semantic actions are `SPLIT_REQUIRED`.

Known examples:

```text
hud_executeaction
hud_shotreservationpopup
actor_confirmaction
ships_click
ui_market_buy
MapClick/GEO_Click
```

There must never be public intents named after those umbrella callbacks merely to preserve legacy structure.

## 14. Scope examples

These stay inventoried without automatically becoming gameplay intents:

```text
debug_*                    DEBUG_TOOLING
multiplayer lobby commands MULTIPLAYER_SESSION
skirmish setup commands    SKIRMISH_SESSION
game_setmode/game_exit     SESSION_CONTROL
saved team slot commands   APPLICATION_PERSISTENCE
capacity/derived counters  CANONICAL_MAINTENANCE
script-triggered mutations SCRIPTED_CANONICAL_EVENT
```

## 15. Selection policy

Qualified compatibility `SelectMission` / `SelectAircraft` intents may remain while legacy consumers require canonical selection globals.

Retained presentation should prefer local typed context plus explicit gameplay payloads:

```text
SendAircraftToMission(AircraftId, MissionId)
BuildFacility(BaseId, FacilityTypeId, Cell)
SetAircraftDestination(AircraftId, GeoPosition)
StartMission(MissionId, AircraftId)
```

## 16. Authority-leak review

Classification must detect presentation-supplied values that canonical code should own.

A recovered-UFO sale should not trust a price round-tripped through presentation. Prefer canonical offer publication plus `AcceptUfoSaleOffer(OfferId)` with canonical revalidation.

## 17. Presentation source guard

Outside `*_legacy_adapter.cpp`, new `src/client/presentation` code must not:

```text
include campaign/cgame implementation headers
dereference ccs
send MSG_Write_PA directly
call canonical mutation owners directly
```

## 18. v2 outputs

```text
.build/m1-presentation-authority/inventory.tsv
.build/m1-presentation-authority/unresolved.tsv
.build/m1-presentation-authority/summary.md
.build/m1-presentation-authority/review-pack.md
```

The review pack contains unresolved handler evidence.

## 19. Strict completion

`--strict` passes only when:

```text
no active discovered entry has UNCLASSIFIED_SCOPE
every PRESENTATION_ACTION has a final five-way authority
no PRESENTATION_ACTION remains SPLIT_REQUIRED/UNCLASSIFIED
all direct tactical protocol callsites have semantic mappings
all direct presentation input hooks are classified
presentation source guard has zero violations
```

Out-of-scope commands do not have to become presentation intents.

## 20. Intent-completeness phase

After strict classification:

```text
STRATEGIC_CANONICAL -> complete StrategicIntent catalog
TACTICAL_SERVER     -> complete TacticalIntent catalog
PRESENTATION_ONLY / PRESENTATION_CONTEXT -> retained presentation state/actions
READ_ONLY -> immutable snapshots/view models
```

Consumer replacement happens later.

## 21. Exit rule

M1 gameplay-action boundary completion requires:

```text
scope inventory sealed
presentation authority classification strict-clean
all strategic canonical semantic actions have typed routes
all tactical server semantic actions have typed routes
canonical/server ownership unchanged
canonical preservation green
legacy consumers still functional behind adapters
```


## 22. Semantic decomposition closure

A legacy `SPLIT_REQUIRED` entry is classification-complete only when a tracked decomposition maps it into two or more semantic components, each with one of the five final authority classes.

Registry:

```text
tools/remaster/m1-presentation-authority-decomposition.tsv
```

Tracked decompositions:

```text
actor_confirmaction
    MoveActor                  TACTICAL_SERVER
    Shoot                      TACTICAL_SERVER

hud_executeaction
    SelectFireMode             PRESENTATION_CONTEXT
    Reload                     TACTICAL_SERVER

hud_shotreservationpopup
    OpenShotReservationPopup   PRESENTATION_ONLY
    ClearShotReservation       TACTICAL_SERVER

MapClick / GEO_Click
    StageBasePlacement         PRESENTATION_CONTEXT
    StageInstallationPlacement PRESENTATION_CONTEXT
    OpenGeoscapeSelection      PRESENTATION_ONLY
    ResetGeoscapeAction        PRESENTATION_CONTEXT
    SetAircraftDestination     STRATEGIC_CANONICAL

ui_market_buy
    BuyItem / SellItem
    BuyAircraft / SellAircraft
    BuyUGV / SellUGV           STRATEGIC_CANONICAL

ships_click
    SendAircraftToMission      STRATEGIC_CANONICAL
    PursueUfo                  STRATEGIC_CANONICAL

game_continue
    ResumeCurrentPresentation  PRESENTATION_ONLY
    LoadLastSave               STRATEGIC_CANONICAL
```

The umbrella callback names are not public remaster intents.

## 23. Derived semantic inventories

A v3 capture writes:

```text
.build/m1-presentation-authority/semantic-actions.tsv
.build/m1-presentation-authority/intent-candidates.tsv
```

`semantic-actions.tsv` is the classified five-way presentation action surface after decomposition.

`intent-candidates.tsv` is the authoritative subset:

```text
STRATEGIC_CANONICAL
TACTICAL_SERVER
```

with `api_relevance=yes`.

That file is the source inventory for the complete typed-intent implementation pass.

## 24. v3 observed-surface closure

The v3 registry resolves every entry reported by the local v2 capture:

```text
v2 unresolved entries: 119
v3 registry/decomposition/protocol coverage: 119/119
```

The v3 registry/decomposition result is the sealed classification basis for the typed-intent catalog. Reproducibility remains guarded by running the strict capture on the exact local tree:

```bash
python3 tools/remaster/capture-m1-presentation-authority-inventory.py --strict
```

which must continue to report zero unresolved entries and zero presentation source-guard violations.
## 25. Authoritative intent surface v1 qualification — 2026-09-08

The classification contract described by this document has now produced and qualified the complete typed authoritative surface:

```text
strategic authoritative semantics: 57/57
tactical authoritative semantics:  15/15
```

Qualification preserves fail-closed migration behavior:

```text
strategic canonical-applied:        3/57
strategic owner-extraction pending: 54/57
tactical server-forwarded:          13/15
tactical helper-extraction pending: 2/15
```

The qualification includes strict C++11 public-header coexistence, bounded C++26 transport checks, historical M1 integration lanes, two canonical 104/104 regression passes with trace repeatability, digest verification, and fresh legacy/remaster production builds.

The next authority milestone is not additional classification. It is reducing the fail-closed counts to zero by extracting canonical campaign owners and the remaining tactical request helpers.

This section is retained as dated 2026-09-08 qualification evidence. A subsequent semantic split of legacy `prod_inc` introduced distinct `CreateProduction`, temporarily expanding the strict strategic inventory from 57 to 58. The 2026-09-11 full authority re-audit then proved `building_amdestroy` / `DestroyAntimatterFacility` is an internal probabilistic scripted canonical event rather than a presentation request, correcting the presentation-authoritative strategic surface back to 57 without changing the tactical total.

## 26. Current M1 authority implementation status — 2026-09-13

At implementation baseline `46c6c3ca9fb808f7c5bdb8c665b79ef378a3cabf` plus the qualified LoadLastSave explicit-context normalization:

```text
strategic presentation-authoritative semantics: 57
  canonical-applied:                            55
  owner-extraction pending:                     2

tactical authoritative semantics:               15
  forwarded to server authority:                13
  helper-extraction pending:                     2
```

The current strategic-applied set includes the previously qualified Aircraft/Geoscape, Base/Installation, Facility, Research and Production owners, canonical `CreateProduction`, the six Employee/Team actions, and all seven Market actions:

```text
AssignEmployeeToAircraft
DeequipEmployee
DeleteEmployee
HireOrFireEmployee
RenameEmployee
SetEmployeeSkin
BuyAircraft
BuyItem
BuyUGV
SellAircraft
SellItem
SellUGV
SetAutoSellPolicy
```

Market item owners preserve inherited partial-fill normalization before the strict low-level mutation helpers. Market purchase/sale subjects reuse qualified `BaseId`, `AircraftId`, `EmployeeId`, `ItemId` or static aircraft/UGV definition keys re-resolved at execution; no new persistent identity domain is introduced. Autosell carries an explicit desired state rather than a canonical toggle.

Persisted `EmployeeId` is published from `character_t::ucn`; stable runtime `ProductionId` and persisted `StoredUfoId` remain qualified. Runtime-only `FacilityId` is now canonical metadata on `building_t`, freshly reconstructed after load, preserved across facility-array compaction, published through immutable facility views and re-resolved at typed destruction execution. BuildFacility, StopAircraft, PursueUfo, SendAircraftToMission, BuyAircraft and BuyUGV also recheck the inherited eligibility boundaries identified by the full authority audit.

`building_amdestroy` is `SCRIPTED_CANONICAL_EVENT`; `DestroyAntimatterFacility = 20` is retained only as a deprecated numeric tombstone and exposes no public submit helper. Recovered/stored-UFO authority now uses a one-shot process-monotonic `UfoRecoveryId` minted from the canonical won-mission recovery trigger, generation-safe `UfoSaleOfferId` values bound to canonical nation/price offers generated at the recovery handoff before the inherited sell-tab projection, and persisted `StoredUfoId` for destroy/transfer. This closes AcceptUfoSaleOffer, StoreRecoveredUfo, DestroyStoredUfo and TransferStoredUfo without trusting UI-round-tripped price/UFO condition and without changing save v4. `KillContainedAlien` and `KillContainedAliens` now resolve `BaseId`/`TechnologyId` at execution and delegate to UI-free `cp_aliencont.cpp` owners. Single-species killing preserves the inherited behavior of converting one live alien for every team definition mapped to the requested technology; kill-all converts each positive live count to dead through `AlienContainment::add`, so capacity/research side effects and underflow protection remain canonical. No individual `AlienId` is introduced. `EquipAircraftItem` and `RemoveAircraftItem` now re-resolve the fixed aircraft structural slot coordinate and current `ItemId`, preserve inherited replacement/install/ammo/storage/stat semantics in `cp_mapfightequip.cpp`, and `RenameAircraft` delegates printable/default-name validation to `AIR_TrySetName`; no aircraft-slot runtime identity is minted. Defence authority is now extracted without changing defence gameplay: `baseWeapon_t::runtimeId` provides runtime-only `DefenceSlotId`, array compaction carries the ID with the logical battery, vacated tails receive fresh IDs, load reconstructs fresh IDs without save-format changes, immutable snapshots publish the IDs, equip/remove re-resolve them at execution, and autofire/target retain inherited all-battery aggregate behavior. StartTransfer now stages a bounded value-only `StrategicTransferManifest` in a one-shot runtime registry identified by `TransferManifestId`; the Main adapter consumes it exactly once and lowers it to `TR_TryStartTransfer`, which re-resolves every current canonical reference and validates all cargo quantities before entering the inherited pointer-rich transfer mutation/scheduling path. `TransferManifestId` remains submission context only and is never reused as the still-unmapped active `TransferId`. SaveGame now converges from both legacy and typed presentation paths directly on the existing `SAV_GameSave` canonical serializer; no wrapper, new identity, schema fork, or save-version change is introduced. `LoadGame` is now qualified without changing the save format: `SAV_GameLoad` remains the single owner, but every failure after its initial campaign-mode reload now releases transient XML where necessary and directly reloads campaign mode again before returning rejection. The typed adapter therefore converges on the same owner without command/cvar fallback. Campaign shutdown clears stale intent/result queues while the monotonic intent sequence survives the lifecycle reset, allowing the in-flight LoadGame result to be published afterward. The legacy `game_load` wrapper remains unchanged because its command-based session behavior on pre-reload failures is presentation/session policy, not canonical load authority. `LoadLastSave` is now qualified as a boundary normalization rather than a second persistence owner. Archived `cl_lastsave` remains application/presentation context; the typed API requires that context to be resolved before submission and carries only the bounded slot value. The adapter preserves the decomposed `game_continue` contract by rejecting the authoritative semantic while on Battlescape or while a campaign is already running, leaving those resume/pop branches presentation-owned; only the no-running-campaign branch delegates to the already-qualified `SAV_GameLoad`. No cvar lookup, command dispatch, canonical last-save identity, serializer fork, or save-version change is introduced. The remaining 2 true strategic presentation actions stay fail-closed until their campaign-owned contracts are audited and extracted.

These implementation counts and runtime-only FacilityId do not alter campaign persistence or tactical transport: save format v4 and protocol 18 remain the active compatibility epoch.
