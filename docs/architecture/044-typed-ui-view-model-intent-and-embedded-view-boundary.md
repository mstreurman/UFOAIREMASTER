# Typed UI View Models, Intents and Embedded View Boundary

**Status:** Implementation specification baseline  
**Related ADR:** ADR-026

## 1. Principle

The new UI does not receive arbitrary game/campaign pointers.

It receives typed presentation data.

It emits typed user intent.

## 2. View-model rules

A view model may contain:

```text
plain values
stable IDs
localized/string IDs
AssetIds
enabled/visible flags
presentation labels
presentation timing
read-only list/span views valid for the publication lifetime
```

It must not contain:

```text
character_t*
base_t*
aircraft_t*
raw inventory pointers
uiNode_t*
Vulkan handles
OpenAL handles
Jolt handles
```

## 3. Example tactical HUD model

Conceptual:

```cpp
struct TacticalHudModel {
    TacticalActorUiId selectedActor;

    int currentTU;
    int maxTU;

    int health;
    int maxHealth;

    TacticalWeaponUiModel leftWeapon;
    TacticalWeaponUiModel rightWeapon;

    Span<const TacticalActionUiModel> actions;

    bool reactionFireEnabled;
    bool canEndTurn;
};
```

This is presentation data only.

## 4. Example research model

Conceptual:

```cpp
struct ResearchScreenModel {
    ResearchProjectUiId selected;

    Span<const ResearchProjectUiModel> projects;

    int scientistsAvailable;
    int scientistsAssigned;

    bool canStartSelected;
    bool canStopSelected;
};
```

The campaign system remains authoritative.

## 5. Intent ABI

Conceptual:

```cpp
enum class UiIntentType : uint16_t {
    OpenScreen,
    CloseScreen,
    ConfirmModal,
    CancelModal,

    SelectActor,
    EndTurn,
    ChangeStance,
    ToggleReactionFire,

    MoveInventoryItem,
    EquipItem,

    SelectResearchProject,
    StartResearch,
    StopResearch,

    SelectAircraft,
    SelectBase,

    ChangeTimeScale,
    ChangeSetting
};

struct UiIntent {
    UiIntentType type;
    UiIntentPayload payload;
};
```

Exact union/variant packing is implementation work.

## 6. Intent processing

Flow:

```text
UiRuntime
    ->
ordered UiIntent queue
    ->
Main
    ->
domain-specific validator/command
    ->
authoritative state mutation
    ->
next UiViewModel publication
```

UI never assumes an intent succeeded until authoritative state reflects it.

## 7. Intent ordering

Ordering is Main-thread deterministic.

Do not define intent order from worker completion.

Multiple pointer/key events in one frame preserve input event order.

## 8. Compatibility bridge

Provide:

```text
LegacyUiBridge
```

mapping old interfaces into compatibility data/layer operations.

Examples:

```text
UI_RegisterText
    -> LegacyUiDataStore::setText

UI_RegisterLinkedListText
    -> LegacyUiDataStore::setList

UI_RegisterOption
    -> LegacyUiDataStore::setOptions

UI_PushWindow
    -> UiLayerStack::push

UI_PopWindow
    -> UiLayerStack::pop
```

This bridge is transitional.

New screens should prefer typed models.

## 9. Legacy raw-node compatibility

Where old code still requests:

```text
UI_GetNodeByPath
uiNode_t*
```

contain that behavior inside the compatibility layer.

Do not add new remaster code that depends on legacy node pointers.

## 10. Removing direct UI draw imports

Replace old cgame usage of:

```text
UI_DrawString
UI_DrawFill
UI_DrawTooltip
R_DrawLine
R_DrawRect
R_DrawFill
R_Draw2DMapMarkers
R_Draw3DMapMarkers
R_DrawImageCentered
```

with one of:

```text
typed UiViewModel
UiIntent
UiEmbeddedViewRequest
PresentationOverlaySnapshot
```

No new direct renderer drawing calls from campaign/cgame UI code.

## 11. Embedded view request

Conceptual:

```cpp
enum class UiEmbeddedViewType : uint8_t {
    ModelPreview,
    Radar,
    Video,
    GeoscapeSubview
};

struct UiEmbeddedViewRequest {
    UiEmbeddedViewType type;
    UiNodeId ownerNode;
    UiRect viewport;
    UiEmbeddedViewPayload payload;
};
```

Payload contains stable renderer-facing IDs/parameters only.

## 12. Model preview

UI:

```text
model preview node
    ->
UiEmbeddedViewRequest
```

Render:

```text
offscreen HDR preview
    ->
resolved image/texture
    ->
UI composite
```

UI does not invoke model rendering directly.

## 13. Geoscape split

Campaign state publishes:

```text
GeoscapeSceneSnapshot
GeoscapeUiModel
```

Renderer owns:

```text
globe/world presentation
3D/2D world markers
world-space movement presentation
```

UI owns:

```text
buttons
selection panels
timers
base/aircraft lists
notifications
modals
```

## 14. Tactical split

Tactical state publishes:

```text
TacticalHudModel
TacticalInteractionState
```

UI owns:

```text
TU/health
weapon controls
stance controls
reaction-fire controls
messages
turn controls
inventory panels
```

Presentation/world overlay owns:

```text
actor outlines
movement path
target line
world labels
world interaction circles
world targeting visualization
```

## 15. Inventory authority

Inventory UI may calculate local visual preview for:

```text
drag location
hover highlight
candidate destination
```

but only canonical inventory logic determines:

```text
valid placement
TU cost
weight/load legality
actual item ownership/location
```

## 16. Settings

Presentation/runtime settings may apply through typed intents.

Examples:

```text
UI scale
ReducedMotion
HDR mode
HRTF mode
volume
graphics quality
```

Settings that cause device/runtime reset are processed by owning subsystems after Main validates/persists the change.

## 17. Notifications

Use typed notification model:

```text
severity
localized text
icon
duration/sticky state
optional action intent
```

Do not call arbitrary popup draw functions from gameplay code.

## 18. Migration rule

Any newly modernized screen:

```text
must use typed view-model input
must emit typed intents
must not call direct renderer drawing
must not introduce new raw uiNode_t dependencies
```
