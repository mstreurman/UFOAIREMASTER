# Retained UI Runtime: Node, Layout, Input and Animation

**Status:** Implementation specification baseline  
**Related ADR:** ADR-026

## 1. Runtime node identity

Use generational handles:

```cpp
struct UiNodeId {
    uint32_t index;
    uint32_t generation;
};
```

Invalid:

```text
0xffffffff / generation 0
```

or equivalent explicit sentinel.

Do not expose raw node pointers across subsystem boundaries.

## 2. Runtime node

Conceptual:

```cpp
struct UiNode {
    UiNodeId parent;
    UiNodeId firstChild;
    UiNodeId nextSibling;

    UiNodeType type;
    UiNodeFlags flags;

    UiStyleId style;
    UiLayoutBox layout;

    UiBindingId binding;
    UiPayloadId payload;
};
```

Behavior-specific payloads are stored in typed side arrays/pools.

Do not reproduce legacy "extra bytes after uiNode_t" as the new ABI.

## 3. Hierarchy storage

Use dense/sparse generational storage.

Requirements:

```text
stable UiNodeId until destruction
dense iteration for layout/render
parent/child navigation
deterministic child order
safe stale-handle detection
```

Structural mutation is Main-thread-owned.

## 4. Node types

Initial general-purpose types:

```text
Root
Panel
Text
Image
Button
Toggle
Slider
Progress
List
Grid
ScrollView
TextInput
Tooltip
Modal
EmbeddedView
Spacer
```

Inventory and other domain-specific experiences should primarily compose general nodes plus typed models/intents.

Add specialized nodes only when semantics genuinely require them.

## 5. Layout modes

```cpp
enum class UiLayoutMode : uint8_t {
    Absolute,
    Row,
    Column,
    Stack,
    Grid,
    Scroll,
    Overlay
};
```

Each node may specify:

```text
preferred size
minimum size
maximum size
padding
margin
gap
alignment
flex weight
aspect ratio
```

## 6. Reference coordinate system

Design reference:

```text
1920 × 1080 logical units
```

Scale:

```text
fit-to-output scale
×
user UI scale
```

Starting user scale choices:

```text
75%
100%
125%
150%
175%
200%
```

Exact settings UI may use a slider rather than fixed enumerants.

## 7. Pixel snapping

Use pixel snapping for:

```text
text baselines
thin borders
1-pixel separators
small icons where authored for pixel alignment
```

Do not globally snap animated/transformed panels in ways that create visible judder.

## 8. Dirty layout

Each node tracks relevant dirty state:

```text
StructureDirty
StyleDirty
MeasureDirty
LayoutDirty
RenderDirty
TextDirty
```

Changing child structure propagates measure/layout dirtiness upward as required.

Changing only opacity/color need not recompute layout.

## 9. Layout phases

Baseline:

```text
1. update local state/bindings
2. measure dirty subtree
3. arrange dirty subtree
4. update clip rectangles
5. update render primitives
```

Avoid full-tree layout every frame when only a small HUD value changed.

## 10. Input ownership

Input runs on Main.

Flow:

```text
platform input event
    ->
UiInputRouter
    ->
hit testing/focus routing
    ->
local UI state change
    ->
UiIntent if authoritative action requested
```

Render thread never interprets mouse/keyboard events.

The platform layer supplies normalized input events. ADR-033 and architecture 081 fix SDL3 as the Fedora window/input/text/IME and Vulkan-surface layer; UI code still consumes only project-normalized events.

## 11. Input event model

Support:

```text
pointer move
pointer down/up
wheel
keyboard press/release
text input
IME/composition
focus traversal
mouse capture
drag/drop
```

Controller navigation is planned and should use the same focus/action model.

## 12. Event routing

Baseline event phases:

```text
Capture
Target
Bubble
```

A node may:

```text
handle
stop propagation
capture pointer
request focus
emit local UI action
emit UiIntent
```

## 13. Focus

Maintain one focused UiNodeId per active focus scope.

Focus scopes include:

```text
root window
modal
popup
embedded input surface where needed
```

A modal traps navigation/input appropriately.

## 14. Drag and drop

Use UI-local drag state:

```cpp
struct UiDragState {
    UiNodeId source;
    UiDragPayload payload;
    UiNodeId hoverTarget;
};
```

Drop emits a typed intent.

Example:

```text
drag inventory item
    ->
visual preview
    ->
drop
    ->
UiIntent::MoveInventoryItem
    ->
canonical inventory validation
```

UI never declares the move authoritative.

## 15. Local UI animation

Retained properties may animate:

```text
opacity
position
scale
selection indicator
panel expand/collapse
progress interpolation
scroll offset
highlight
```

Animation uses presentation real time.

Not canonical game time.

## 16. Reduced motion

Global accessibility setting:

```text
ReducedMotion
```

reduces or disables nonessential:

```text
sliding
zooming
parallax
large eased transitions
```

while preserving critical state feedback.

## 17. Theme/style IDs

Nodes reference semantic style IDs.

Examples:

```text
Button.Primary
Button.Secondary
Panel.Standard
Panel.Modal
Text.Heading
Text.Body
Text.Caption
Hud.Health
Hud.TU
```

Do not embed arbitrary styling constants in gameplay/campaign code.

## 18. UI runtime ownership

Writer table:

```text
retained tree             Main
window/layer stack        Main
focus/hover/capture       Main
local animation state     Main
view-model binding state  Main
layout state              Main
UiRenderSnapshot          Main then sealed
```

Workers may later assist text shaping/layout only through explicit immutable work batches.

## UI raster extent authority

Architecture 072 owns physical UI raster sizing:

```text
UiLogicalExtent = 1920x1080 logical units
UiRasterExtent  = OutputExtent
```

Existing fit-to-output scaling maps retained layout coordinates into the current output pixel extent before user UI scale is applied.
