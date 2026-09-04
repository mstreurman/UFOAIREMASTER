# Legacy UI Lua and Audited Map-Entity Migration Policy

**Status:** Exact migration specification  
**Related ADR:** ADR-013, ADR-026, ADR-028

## 1. UI principle

Legacy screens must remain migratable without making Lua callbacks part of the permanent new UI ABI.

## 2. `LegacyActionId`

During compatibility migration, `.rui` `LEGC` may contain symbolic/interned:

```text
LegacyActionId
```

It identifies a legacy authored action/callback.

It is not a function pointer, VM pointer or Lua registry handle.

## 3. Dispatch

```text
UiRuntime
    ->
LegacyActionId
    ->
LegacyUiBridge on Main
    ->
existing legacy UI/Lua dispatch
```

Gameplay/campaign legality remains outside the UI.

## 4. Modernized screens

Once modernized:

```text
no new Lua UI callbacks
no new raw uiNode_t dependencies
no new direct UI_Draw*/R_Draw* calls
```

Use typed view models, `BIND`, `ACTN`, `UiIntent`, embedded views and presentation overlays.

## 5. Compatibility lifetime

The legacy UI Lua bridge remains only while production screens reference `LegacyActionId`.

Removing the last compatibility reference permits later removal of that UI bridge.

Lua outside this legacy UI path is not redefined here.

## 6. `ufo-uic`

Compatibility compiler:

```text
parses legacy hierarchy/properties
resolves includes/inheritance
compiles layout/style
emits LegacyActionId for untranslated legacy callbacks
emits typed ACTN/UiIntent for modernized behavior
```

Unsupported dynamic behavior is a migration error, not silently serialized arbitrary scripting.

## 7. Map entity authority

The final merged canonical entity string remains consumed by the canonical/legacy runtime.

`.rmap` remains presentation-only.

## 8. Audited presentation baking

Because architecture 010 is source-complete, `remaster-mapc` may bake fields classified presentation-only or presentation-readable.

Examples:

```text
presentation light metadata
audio/acoustic preset links
presentation model/decal/VFX references
static presentation labels/markers
```

Architecture 010's field matrix remains authority.

## 9. Forbidden bake

Never replace canonical behavior for:

```text
doors/breakables/triggers
damage
mission logic
routing/pathfinding
collision
LOS
spawn/gameplay state
```

## 10. Strong coupling

Baked metadata records the canonical BSP/content/source identity required to reject stale presentation assets.

## 11. Dynamic state

Baked data is only initial/static presentation metadata.

Dynamic state arrives one-way from canonical events/mirror state into Presentation World.
