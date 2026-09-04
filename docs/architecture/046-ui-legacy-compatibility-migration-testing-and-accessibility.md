# UI Legacy Compatibility, Migration, Testing and Accessibility

**Status:** Architecture baseline  
**Related ADR:** ADR-026

## 1. Source audit basis

The legacy system already provides useful migration concepts:

```text
retained hierarchical uiNode_t
behavior registration/inheritance
properties
window stack
shared UI data
focus/mouse capture
drag/drop
Lua callbacks
specialized nodes
```

The migration should preserve user-facing behavior where appropriate while replacing runtime coupling.

## 2. Legacy compatibility backend

First implementation milestone:

```text
legacy UI runtime/content
    ->
LegacyUiAdapter
    ->
new UiDrawList / UiRenderSnapshot
    ->
Vulkan UI renderer
```

Goal:

```text
existing menus remain usable
legacy OpenGL/direct renderer UI path becomes unnecessary
```

## 3. Compatibility data store

Implement transitional store for:

```text
legacy registered text
legacy list text
legacy options
legacy window/layer operations
legacy notices/popups
```

This allows existing campaign/cgame code to keep functioning during migration.

## 4. No new legacy dependencies

From the start of remaster UI implementation:

```text
do not add new UI_Draw* calls
do not add new R_Draw* calls from cgame UI paths
do not add new raw uiNode_t dependencies in remaster systems
```

Existing dependencies are migration debt.

## 5. Migration stages

### Stage 1 — Vulkan compatibility rendering

Render existing legacy UI through new Vulkan UI primitives.

### Stage 2 — text replacement

Route legacy text through:

```text
HarfBuzz
FreeType
glyph atlas
```

### Stage 3 — compatibility data bridge

Move:

```text
UI_RegisterText
UI_RegisterLinkedListText
UI_RegisterOption
window stack operations
```

onto the new retained runtime bridge.

### Stage 4 — direct-draw removal

Replace direct UI/renderer imports with:

```text
UiViewModels
UiIntents
UiEmbeddedViewRequest
PresentationOverlaySnapshot
```

### Stage 5 — offline compile

Introduce:

```text
ufo-uic
.rui
```

Legacy screens may compile symbolic `LegacyActionId` references into `LEGC` and dispatch through `LegacyUiBridge` on Main.

Newly modernized screens may not add new Lua UI callbacks.

Stop parsing legacy UI authoring source in production runtime while retaining compatibility dispatch for remaining legacy screens.

### Stage 6 — screen modernization

Recommended order:

```text
main menu
settings
save/load
modal/popup framework

tactical HUD
inventory
team/equipment

base screens
research
production
aircraft
geoscape
```

## 6. Visual modernization rule

Modernization may change:

```text
layout density
typography
color/style
animation
icons
information hierarchy
responsive scaling
```

It may not change canonical rules or omit information required for gameplay.

## 7. Accessibility baseline

Support from first modernized screens:

```text
UI scale
keyboard-only navigation
visible focus
reduced motion
high-contrast theme hooks
text scaling
color-independent state indicators
```

Controller navigation remains planned.

## 8. Localization

All user-facing UI text uses localization/string identity rather than hard-coded English in compiled UI packages.

Text shaping must support:

```text
Unicode
complex scripts
RTL shaping
ligatures/kerning
```

where translation content requires it.

## 9. Stable input tests

Automated UI-runtime tests should cover:

```text
focus traversal
modal focus trapping
pointer capture
drag/drop intent emission
scroll behavior
keyboard activation
text entry/IME state machine
visibility/enabled changes
```

Tests operate on node IDs/view models/intents, not pixel coordinates where avoidable.

## 10. Layout tests

For important screens, test at:

```text
1920x1080 / 100%
1920x1080 / 150%
1920x1080 / 200%
```

and future supported window sizes.

Verify:

```text
no overlapping mandatory controls
no clipped primary labels
scrolling where expected
stable focus ordering
```

## 11. Visual regression

Capture deterministic UI render snapshots or rendered images for representative states.

Compare:

```text
layout boxes
draw instance counts
glyph runs
clip rects
embedded-view rectangles
optional image regression
```

Do not depend solely on image diff when semantic snapshot checks can identify the real issue.

## 12. UI performance telemetry

Track:

```text
active node count
dirty node count
layout count/time
text-shape requests/cache hits
glyph atlas pages/evictions
draw instance count
clip count
embedded view count
Main UI update time
Render UI upload time
GPU UI pass time
```

## 13. CPU targets

Engineering targets:

```text
UI input/update/model:
    <= 0.20 ms

dirty layout:
    <= 0.20 ms

text/layout snapshot:
    <= 0.30 ms
```

Not measured results.

## 14. Embedded-view testing

Verify UI/runtime remains correct when:

```text
model preview missing/not ready
geoscape renderer unavailable
video asset missing
embedded render target reallocates
HDR/SDR mode changes
```

UI should display controlled fallback state rather than dereference renderer internals.

## 15. World-overlay separation tests

Ensure these remain Presentation World/overlay data rather than 2D UI authority:

```text
movement paths
world target lines
selection outlines
actor world labels
world interaction markers
```

UI may control their visibility/options by intent, but does not calculate canonical geometry/LOS.

## 16. Legacy removal criterion

Legacy runtime node/data APIs can be removed only when:

```text
all production screens use new retained runtime
all authoritative actions use UiIntent
all UI data uses typed view models or final compatibility-free binding
all direct cgame UI/renderer drawing imports are removed
production UI loads .rui or equivalent compiled data
```

## 17. Open details

Still intentionally content/tooling/quality-tunable rather than architecture blockers:

```text
exact .rui authoring syntax after legacy phase
exact theme visual design
final typeface/font asset selection
exact glyph atlas eviction algorithm
final responsive art/layout tuning outside native 1080p
```

Controller navigation normalization and IME ownership are now fixed by architecture 081.

## Legacy Lua compatibility authority

Architecture 054 is the exact legacy UI Lua/`.rui` migration authority.

The intended eventual removal is the legacy **UI** Lua bridge, not an architectural ban on Lua elsewhere.

## Budget-accounting authority

Architecture 055 owns parent/child timing accounting.

UI work performed before Main publication is attribution within the parent snapshot-ready path.

## Baseline 031 platform binding

Architecture 081 binds controller navigation and UTF-8 text/IME composition to normalized SDL3-backed platform events. The retained-UI ownership model above is unchanged.
