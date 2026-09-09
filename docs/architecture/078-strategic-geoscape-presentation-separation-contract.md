# Strategic / Geoscape Presentation Separation Contract

**Status:** Implementation contract  
**Related:** ADR-001, ADR-026, architecture 043–046, 054, 077

## 1. Goal

Strategic/campaign gameplay remains canonical while the Geoscape and campaign UI become modern presentation clients of that state.

Target split:

```text
Campaign Canonical State
    |
    +--> StrategicSnapshot / typed view models
    |       |
    |       +--> retained UI
    |       +--> Geoscape presentation scene
    |       +--> strategic audio adapter
    |
    <--- StrategicIntent / UiIntent
             |
             +--> canonical validation + mutation
```

## 2. Ownership

### Campaign/canonical owns

```text
campaign clock/date
missions and mission lifecycle
bases/installations
aircraft and interceptions
research/production
market/inventory/personnel
nations/funding
campaign messages/events
save/load data
all strategic outcomes/rules
```

### Strategic presentation owns

```text
Geoscape camera
visual interpolation
marker layout/decluttering
visual trails/ribbons
non-authoritative animation
retained UI node/layout state
hover/focus/selection presentation state
presentation-only audio state
```

A presentation selection may refer to a canonical object ID but does not become that object's authority.

## 3. Strategic snapshot publication

Publish immutable snapshot generations from Main after canonical campaign updates that affect presentation.

Conceptual root:

```cpp
struct StrategicSnapshot {
    uint64_t publicationSerial;
    CanonicalTime campaignTime;

    Span<const StrategicMissionView> missions;
    Span<const StrategicAircraftView> aircraft;
    Span<const StrategicBaseView> bases;
    Span<const StrategicInstallationView> installations;
    Span<const StrategicNationView> nations;
    Span<const StrategicTechnologyView> technologies;
    Span<const StrategicProductionView> productions;
    Span<const StrategicMessageView> messages;

    StrategicSelectionView selection;
    StrategicEnvironmentView environment;
};
```

Exact packed ABI may evolve internally; the semantic ownership above is locked.

Snapshot memory is immutable to UI/render/audio consumers for its lifetime.

## 4. Stable identities

Every presentation-visible canonical object is projected using a stable typed ID, never a raw canonical pointer.

Required strong identity domains include:

```text
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

Where legacy code lacks a naturally persistent ID, the canonical adapter owns a generation-safe mapping for the current campaign/load lifetime.

A declared strong ID type does not by itself prove that a safe legacy mapping already exists. The identity registry tracks type existence, mapping, publication and mutation readiness separately.

Mutable array/list ordinals are not stable IDs. Production `queueIndex`, base-local `facilityIndex`, and defence `slotIndex` are location metadata rather than persistent identity.

`ProductionId` is implemented as canonical runtime-only metadata on each logical production job. It survives production queue reorder/compaction because the ID moves with the copied queue record; loaded productions receive fresh runtime IDs and the save schema does not persist them. `queueIndex` remains display/order metadata only.

Production mutation owners resolve `(BaseId, ProductionId)` against the current canonical queue at execution time. A missing/stale ID rejects; it is never reinterpreted as the object currently occupying an old `queueIndex`. Decrease/MoveUp/MoveDown/Stop/Increase/SetAmount use this contract.

Legacy `prod_inc` was found to contain two context-dependent authoritative semantics. The typed contract therefore splits existing-job `IncreaseProduction` from `CreateProduction`; the latter is a distinct fail-closed action until production-subject identity/publication is qualified.

`StoredUfoId` maps directly to persisted `storedUFO_t::idx`. Stored UFOs are linked-list objects, removal does not renumber survivors, the ID and its monotonic allocator state are saved, duplicate IDs are rejected on load, and the allocator is reconciled after load before new recovery can allocate another identity. Immutable strategic publication exposes `StoredUfoId` plus value-only UFO-yard/status/condition/definition state. This qualifies the stored-UFO subject identity but does not by itself authorize `CreateProduction`.

`FacilityId` and `DefenceSlotId` still require their generation-safe mappings before new presentation relies on those mutable ordinals for long-lived mutation.

`TransferManifestId` and `TransferId` have different lifetimes: the former identifies transfer submission/staging context; the latter identifies an active canonical transfer.

Structural coordinates (aircraft equipment slots, facility placement cells, positions) and static script/content definition keys do not become runtime entity IDs merely because they cross the presentation boundary.

## 5. Geoscape scene extraction

The renderer consumes a strategic presentation scene built from `StrategicSnapshot`.

Minimum scene categories:

```text
Earth/globe surface and day/night presentation
mission markers
UFO markers
PHALANX aircraft markers
aircraft/UFO routes
bases
installations
radar coverage presentation
selection/hover markers
projectile/air-combat presentation effects
strategic labels/icons through UI overlay
```

Canonical radar detection, mission availability, interception state and aircraft movement are projected into this scene; visual geometry does not calculate those outcomes.

## 6. Marker ABI semantics

Conceptual marker record:

```cpp
struct StrategicMarker {
    StrategicObjectId objectId;
    StrategicMarkerKind kind;
    double longitudeRadians;
    double latitudeRadians;
    float altitudePresentation;
    float headingRadians;
    uint32_t visualClass;
    uint32_t flags;
};
```

Important rule:

```text
longitude/latitude/time/state = canonical projection
screen position/occlusion/decluttering/animation = presentation
```

## 7. Radar/overlay data

Legacy direct arrays such as:

```text
r_xviAlpha
r_radarPic
r_radarSourcePic
```

must not remain shared mutable renderer/campaign memory.

Replace them with one of:

```text
immutable strategic overlay texture/data snapshot
or
renderer-owned derived resource generated from immutable canonical radar/overlay inputs
```

The campaign publishes semantic radar/overlay input/state; the renderer owns GPU resources.

## 8. Strategic intents

All presentation-originated strategic actions use typed intents.

Examples:

```text
SelectMission(MissionId)
SelectAircraft(AircraftId)
SetAircraftDestination(AircraftId, target)
OpenBase(BaseId)
BuildFacility(BaseId, FacilityType, cell)
AssignResearch(TechnologyId, BaseId, count)
BuyItem(BaseId, ItemId, count)
StartMission(MissionId, AircraftId)
PauseCampaignTime
SetCampaignTimeScale
SaveGame(slot/name)
LoadGame(slot/name)
```

These names illustrate the semantic contract; exact C++ enum/function naming may differ.

Intent handling sequence:

```text
UI/Geoscape input
    -> typed intent
    -> Main/campaign adapter
    -> canonical validation
    -> canonical mutation or rejection
    -> next snapshot publication
```

No optimistic UI mutation is allowed for state that affects gameplay authority; the UI may show pending feedback but the canonical result wins.

## 9. Read-only projection model

Legacy UI callback code often pushes strings/options directly into UI nodes. Replace that with typed view models.

Examples:

```text
MarketViewModel
ResearchViewModel
ProductionViewModel
EmployeesViewModel
BaseViewModel
AircraftViewModel
MissionViewModel
MessagesViewModel
UfopediaViewModel
```

View-model generation may cache and diff presentation data but reads canonical state only on Main at the defined publication boundary.

## 10. Threading

Baseline ownership:

```text
Main:
    campaign mutation
    strategic snapshot/view-model build
    intent validation/dispatch

Render:
    consume immutable strategic scene snapshot

UI presentation:
    consume immutable view-model snapshot
    produce intents

AudioControl:
    consume strategic audio commands/snapshot
```

No worker/render/audio thread dereferences live mutable campaign structures.

## 11. Strategic audio adapter

Campaign code publishes semantic requests such as:

```text
NotificationSound(id/class)
AirCombatShot(class, position/state)
AirCombatExplosion(position/state)
BasePlacementConfirmation
MusicState(campaignContext)
```

The audio runtime maps them to assets/voices/mix behavior.

Legacy `S_StartLocalSample`/repeat-rate calls remain compatibility shims only during migration.

## 12. Legacy screen fallback

Migration is screen/subsystem incremental.

A not-yet-migrated campaign screen may continue through the old cgame/UI compatibility path provided:

```text
canonical state ownership is unchanged
new presentation code does not depend on legacy node internals
migrated screens do not call back into old immediate renderer APIs
fallback is feature-gated and regression-tested
```

## 13. Save/load and restart

After load/restart:

```text
canonical campaign state restored
    ->
stable ID mapping rebuilt/validated
    ->
StrategicSnapshot regenerated
    ->
view models regenerated
    ->
Geoscape presentation resources rebuilt as needed
```

Renderer/UI/audio transient state is never required to reconstruct canonical campaign state.

## 14. Replay/regression

Extend presentation regression coverage with strategic sequences:

```text
campaign time advance
mission spawn/expire
aircraft launch/route/interception
base build action
research/production changes
market transaction
message publication
save -> load -> snapshot regeneration
```

Capture/compare:

```text
canonical strategic hashes where available
StrategicIntent sequence
StrategicSnapshot semantic hashes
strategic audio command sequence
selected visual regression frames
```

## 14.1. M1 typed-intent mechanism qualification

The first production typed strategic intent path was implemented and qualified on 2026-09-07.

Representative action:

```text
SetCampaignTimeLapse(int32 lapseIndex)
```

Qualified flow:

```text
presentation
    -> bounded C++26 intent runtime
    -> C++11 Main/campaign adapter
    -> CP_TrySetGameTimeLapse()
    -> canonical acceptance/rejection
    -> typed result feedback
    -> next StrategicSnapshot publication
```

Properties proven by the focused lane:

```text
public intent/result contract strict C++11: PASS
bounded C++26 FIFO/capacity/reset/sequence contract: PASS
submission does not optimistically mutate canonical state: PASS
canonical invalid-lapse rejection: PASS
campaign reset drops pending presentation intent state: PASS
Main intent resolution before campaign run: PASS
campaign run before strategic publication: PASS
integration GoogleTests: 3/3 PASS
sealed src/tests/CMakeLists.txt: unchanged
```

This qualifies the dispatch mechanism required by section 8.

It does **not** imply that every example intent listed in section 8 has already been implemented. New strategic actions should extend this typed value/dispatch path as screens and Geoscape consumers migrate. Tactical player actions may use a separate server/canonical authority adapter while preserving the same presentation-is-not-authority rule.

Permanent evidence:

```text
docs/reference/reference-m1-strategic-intent-dispatch-2026-09-07.md
```

## 14.2. M1 strategic catalog expansion qualification

The first strategic breadth expansion was qualified on 2026-09-07.

Qualified catalog:

```text
SetCampaignTimeLapse
SelectMission
SelectAircraft
SendAircraftToMission
ReturnAircraftToBase
```

The new identity-bearing actions resolve typed `MissionId` / `AircraftId` values only inside the retained C++11 campaign adapter.

Canonical owner mapping:

```text
SelectMission             -> GEO_SelectMission
SelectAircraft            -> GEO_SelectAircraft
SendAircraftToMission     -> AIR_SendAircraftToMission
ReturnAircraftToBase      -> AIR_AircraftReturnToBase
```

The adapter does not reproduce legacy popup/UI behavior as part of the typed contract.

Qualification:

```text
strict C++11 public contract: PASS
strict C++26 bounded runtime: PASS
FIFO/capacity/reset/sequence: PASS
canonical-owner mapping audit: PASS
typed mission selection -> StrategicSnapshot: PASS
invalid typed identities rejected: PASS
integration GoogleTests: 3/3 PASS
canonical regression: 104/104 x2 + repeatable trace
```

Permanent evidence:

```text
docs/reference/reference-m1-intent-catalog-expansion-2026-09-07.md
```

This is a seed catalog, not the final strategic command surface. Further actions are added when their owning presentation consumers migrate.

## 15. Removal criterion

`B029-001` is documentation-closed when the project has:

```text
source coupling inventory                 architecture 077
typed one-way target boundary             this document
UI migration authority                    architecture 043–046/054
renderer/sound migration mapping          architecture 076
save/load/replay boundary                 this document
thread/publication ownership              this document
```

Implementation remains incomplete until the old direct cgame presentation imports are actually eliminated from production paths.
