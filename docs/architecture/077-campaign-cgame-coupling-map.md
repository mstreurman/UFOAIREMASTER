# Campaign / Cgame Coupling Map

**Status:** Source-grounded migration inventory  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Primary authorities:** ADR-001, ADR-026, architecture 001, 043–046, 054

## 1. Purpose

This document closes the inventory portion of `B029-001` and `M029-002` by making the campaign/cgame presentation coupling explicit before migration.

The campaign remains canonical strategic game logic. Presentation modernization must not turn renderer/UI/audio systems into owners of campaign state.

## 2. Existing cgame boundary

At the audited revision, `src/client/cgame/cgame.h` defines:

```text
cgame_export_t
cgame_import_t
```

The source itself contains a TODO immediately above `cgame_import_t` stating that the import interface should be defined. The current table is therefore a historical coupling surface, not a clean architectural boundary.

Campaign mode is implemented under:

```text
src/client/cgame/campaign/
```

and obtains engine/client services through the shared `cgi` pointer.

## 3. Existing exports that cross into presentation

`cgame_export_t` includes presentation-facing callbacks such as:

```text
RunFrame
DrawBaseLayout
DrawBaseLayoutTooltip
EndRoundAnnounce
InitMissionBriefing
NotifyEvent
AddChatMessage
MapDraw
MapDrawMarkers
MapClick
```

The last three are direct Geoscape presentation/input coupling.

These are preserved during migration through adapters, then replaced by typed strategic view-model publication, scene extraction and intents.

## 4. Direct UI-coupled campaign files

A source search for `cgi->UI_` at the audited revision identifies direct campaign UI coupling in at least the following production files:

```text
cp_popup.cpp
cp_statistics.cpp
cp_team_callbacks.cpp
cp_save_callbacks.cpp
cp_cgame_callbacks.cpp
cp_market_callbacks.cpp
cp_hospital_callbacks.cpp
cp_research_callbacks.cpp
cp_aircraft_callbacks.cpp
cp_employee_callbacks.cpp
cp_aliencont_callbacks.cpp
cp_mission_callbacks.cpp
cp_uforecovery_callbacks.cpp
cp_base_callbacks.cpp
cp_installation_callbacks.cpp
cp_messageoptions_callbacks.cpp
cp_basedefence_callbacks.cpp
cp_campaign.cpp
missions/cp_mission_ufocarrier.cpp
cp_ufopedia.cpp
cp_produce_callbacks.cpp
cp_nation.cpp
cp_fightequip_callbacks.cpp
cp_transfer_callbacks.cpp
cp_team.cpp
cp_messages.cpp
cp_event_callbacks.cpp
cp_geoscape.cpp
cp_save.cpp
cp_aircraft.cpp
cp_auto_mission.cpp
missions/cp_mission_baseattack.cpp
cp_messageoptions.cpp
```

This is the migration inventory for direct legacy UI calls. It does not imply those files are presentation-owned; most contain canonical campaign logic that must remain authoritative.

## 5. Direct renderer-coupled campaign files

Confirmed direct renderer coupling includes:

```text
cp_geoscape.cpp
    immediate line/color/marker rendering

cp_overlay.cpp
    direct access to r_xviAlpha / r_radarPic / r_radarSourcePic
```

These are replaced by strategic presentation data and rendering, not by moving campaign logic into the Vulkan renderer.

## 6. Direct sound-coupled campaign files

Confirmed direct sound coupling includes:

```text
cp_messages.cpp
cp_airfight.cpp
cp_base_callbacks.cpp
```

These become semantic strategic audio requests.

## 7. Coupling classification

Every campaign/client crossing must be classified as one of:

```text
CanonicalMutation
CanonicalQuery
PresentationProjection
PresentationIntent
PresentationAudioRequest
PresentationSceneExtraction
LegacyCompatibilityOnly
```

### CanonicalMutation

Changes campaign-authoritative state.

Examples conceptually include:

```text
hire/fire
buy/sell
assign research/production
build/destroy base facilities
launch/redirect aircraft
start mission
save/load
```

The final presentation layer may request these actions, but campaign code validates and applies them.

### CanonicalQuery

Reads authoritative campaign state for canonical logic or validation.

It remains inside campaign/canonical service code.

### PresentationProjection

Converts canonical state into immutable/typed display data.

Examples:

```text
base summaries
research lists
market rows
employee rows
aircraft status
mission markers
nation/funding state
message list
```

### PresentationIntent

User action produced by retained UI/Geoscape presentation.

It contains IDs/parameters, not raw pointers into campaign memory.

### PresentationAudioRequest

Semantic one-shot/music/environment request derived from campaign outcome/state.

### PresentationSceneExtraction

Immutable strategic/Geoscape scene data for the renderer.

## 8. Forbidden final-state coupling

The final remaster boundary forbids:

```text
campaign code issuing immediate Vulkan/OpenGL drawing
campaign code owning UI nodes
campaign code writing renderer image buffers
UI code mutating campaign structs directly
renderer code reading campaign globals directly
audio thread reading campaign globals directly
view models exposing raw campaign pointers
```

## 9. Save/load boundary

Existing campaign save/load remains canonical.

Presentation state may persist only when it is explicitly presentation preference/state, for example:

```text
camera/view preference
UI layout preference
non-authoritative presentation setting
```

No required canonical campaign state may exist only in a retained UI node, renderer object, audio object or Presentation World component.

Loading a campaign rebuilds/publishes presentation projections from canonical state.

## 10. Migration strategy by callsite

For each file in the direct-coupling inventory:

```text
1. identify the canonical mutation/query portion
2. leave authoritative state ownership in campaign code
3. replace UI writes with typed view-model publication
4. replace UI callback strings/direct calls with UiIntent dispatch
5. replace R_* calls with strategic scene/UI extraction
6. replace S_* calls with semantic AudioCommand publication
7. retain an adapter only while the legacy screen remains active
8. add regression coverage before deleting the adapter
```

## 11. Required completion evidence

Campaign presentation migration is not complete until source search proves:

```text
no production campaign cgi->UI_* immediate UI calls remain
no production campaign cgi->R_* calls/raw r_* presentation buffers remain
no direct campaign OpenAL/renderer ownership exists
all strategic user mutations enter through typed intents/canonical validation
all strategic presentation reads come from immutable snapshots/view models
save/load reconstructs presentation state correctly
```

Architecture 078 defines the target strategic/Geoscape runtime boundary that replaces this coupling.

## Source references

- cgame interface: https://github.com/ufoaiorg/ufoai/blob/763173ed036ebbee32c2a7bf6aefa19748df89ff/src/client/cgame/cgame.h
- campaign tree: https://github.com/ufoaiorg/ufoai/tree/763173ed036ebbee32c2a7bf6aefa19748df89ff/src/client/cgame/campaign
