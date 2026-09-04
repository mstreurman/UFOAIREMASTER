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
    Span<const StrategicMessageView> messages;

    StrategicSelectionView selection;
    StrategicEnvironmentView environment;
};
```

Exact packed ABI may evolve internally; the semantic ownership above is locked.

Snapshot memory is immutable to UI/render/audio consumers for its lifetime.

## 4. Stable identities

Every presentation-visible canonical object is projected using a stable typed ID, never a raw canonical pointer.

Required classes include:

```text
MissionId
AircraftId
BaseId
InstallationId
NationId
EmployeeId
TechnologyId
ProductionId
MessageId
```

Where legacy code lacks a naturally persistent ID, the canonical adapter owns a generation-safe mapping for the current campaign/load lifetime.

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
