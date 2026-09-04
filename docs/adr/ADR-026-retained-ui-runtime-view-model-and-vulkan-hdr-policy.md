# ADR-026 — Retained UI Runtime, View-Model and Vulkan HDR Policy

**Status:** Accepted  
**Decision type:** UI runtime / presentation integration  
**Primary qualification target:** Fedora 44 / Vulkan 1.4 / 1920×1080 / DisplayHDR 600-class; runtime output mode remains selectable  
**Related:** ADR-001, ADR-018, ADR-022, ADR-023

## Context

The existing UFO:AI UI is already a retained hierarchical node/window system with:

```text
parent/child node hierarchy
node behaviors and inheritance
properties
focus/hover/input state
window stack
Lua/event callbacks
drag-and-drop
shared UI data
specialized nodes
```

The main architectural problem is not that it is retained-mode.

The problem is the coupling around it:

```text
raw uiNode_t pointers
UI data publication
window-stack mutation
direct UI drawing
direct renderer drawing
game/campaign logic
```

are mixed across client/cgame interfaces.

The remaster must modernize UI presentation without rewriting gameplay rules or forcing a complete content rewrite before the renderer exists.

## Decision

Build a new retained UI runtime with:

```text
UiNodeId-based hierarchy
typed view models
UiIntent commands
retained layout/input/animation state
immutable UiRenderSnapshot
Vulkan UI renderer
display-linear HDR composition
```

Legacy UI definitions remain a migration source/compatibility input.

`uiNode_t` is not the long-term renderer/runtime ABI.

## Data flow

State to presentation:

```text
Canonical / Campaign / Tactical
            |
            v
       typed UiViewModels
            |
            v
        retained UiRuntime
            |
            v
       UiRenderSnapshot
            |
            v
         Render thread
            |
            v
        Vulkan UI pass
```

Input to authority:

```text
platform input event
    |
    v
UiInputRouter
    |
    v
UiIntent
    |
    v
Main thread
    |
    v
canonical/campaign validation
```

UI describes user intent.

Gameplay/campaign systems decide legality and mutate authoritative state.

The concrete Fedora window/input API is owned by ADR-008. This UI ADR intentionally does not adopt SDL3 or any alternative platform layer by itself.

## Legacy migration

Do not replace every existing UFO:AI screen in one milestone.

Initial migration path:

```text
legacy UI definitions
    ->
compatibility parser/compiler
    ->
new retained UiNode tree
```

Long-term offline path:

```text
legacy/new UI source
    ->
ufo-uic
    ->
.rui
```

Production runtime eventually loads `.rui` and does not parse legacy UI source.

## Layout

Do not implement a browser/CSS engine.

Baseline layout primitives:

```text
Absolute
Row
Column
Stack
Grid
Scroll
Overlay
```

with:

```text
min/max/preferred size
padding
margin
gap
alignment
flex weight
aspect ratio
```

## UI coordinate system

Reference design space:

```text
1920 × 1080 logical units
```

At native target:

```text
1 logical unit = 1 pixel
```

User UI scaling is layered on top.

## Rendering

UI is rendered by the Vulkan renderer.

Baseline primitives:

```text
SolidRect
RoundedRect
Image
NineSlice
Glyph
Line
Icon
```

All use premultiplied alpha.

UI images use the global persistent sampled-image descriptor-heap registry.

## Text

Use:

```text
HarfBuzz
+
FreeType
+
Vulkan glyph atlas renderer
```

Baseline glyph atlas uses high-quality coverage glyphs, not an MSDF-first text system.

## HDR

UI bypasses:

```text
scene exposure
bloom
creative scene grading
```

HDR UI pipeline:

```text
sRGB UI authoring
    ->
linear Rec.709
    ->
linear Rec.2020
    ->
203-nit graphics/reference white
    ->
composite into display-linear Rec.2020
    ->
PQ
```

UI white is nominally 203 nits, not 600 nits.

## Embedded presentation views

Specialized views such as:

```text
model preview
geoscape view
radar view
video view
```

are represented by `UiEmbeddedViewRequest`.

UI does not directly invoke arbitrary renderer functions.

## World overlay boundary

World-space presentation overlays remain outside the 2D UI tree.

Examples:

```text
selection outlines
movement paths
target lines
world labels
world-space interaction markers
geoscape world markers
```

They may contribute screen-space overlay primitives during final composition but remain Presentation World data.

## Consequences

- existing UI content can be migrated gradually;
- direct renderer/game coupling is removed;
- modern HDR/text/input behavior can be implemented cleanly;
- UI does not become gameplay authority;
- production UI remains renderer-owned rather than embedding a browser/framework stack.
