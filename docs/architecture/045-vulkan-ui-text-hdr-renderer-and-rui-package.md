# Vulkan UI/Text/HDR Renderer and `.rui` Package

**Status:** Implementation specification baseline  
**Related ADR:** ADR-026

## 1. Offline UI package

Add runtime asset:

```text
.rui
```

Magic:

```text
RUI0
```

using the common remaster chunked asset container.

## 2. `ufo-uic`

Create offline tool:

```text
tools/ufo-uic
```

Responsibilities:

```text
parse legacy/new UI authoring definitions
resolve includes/inheritance
validate node/property/action schemas
resolve style references
resolve AssetIds/string IDs
compile layout/binding/action metadata
emit `.rui`
```

Production runtime eventually does not parse legacy `.ufo` UI source.

## 3. `.rui` chunks

Initial logical chunks:

```text
META
TREE
STYL
LAYO
BIND
ACTN
TEXT
IMAG
ANIM
DEPS
```

Optional compatibility:

```text
LEGC
```

## 4. TREE

Stores:

```text
node type
parent/child/sibling relationship
stable compiled node ID/path ID
payload index
style ID
binding ID
flags
```

No raw process pointers.

## 5. STYL

Resolved/compiled semantic UI styles.

Contains renderer-neutral properties such as:

```text
padding
margin
background style
border style
text style
icon sizing
corner radius
state colors
transition IDs
```

## 6. BIND

Compiled binding records map node properties to typed view-model fields/compatibility data.

Production binding execution does not evaluate arbitrary C++ pointer expressions.

## 7. ACTN

Compiled local UI actions and typed intent emission definitions.

During legacy compatibility, symbolic `LegacyActionId` references may exist only in `LEGC` according to architecture 054.

Do not serialize arbitrary function pointers, Lua VM pointers or Lua registry handles.

## 8. Vulkan UI primitives

Baseline GPU primitives:

```text
SolidRect
RoundedRect
Image
NineSlice
Glyph
Line
Icon
```

Prefer instance rendering from compact buffers.

## 9. Draw instance

Conceptual:

```cpp
struct UiDrawInstance {
    float rect[4];

    uint32_t textureIndex;
    uint32_t packedColor;
    uint32_t packedParams;
    uint32_t clipIndex;
};
```

Exact size/layout is finalized through Slang ABI/reflection.

## 10. Bindless textures

UI images/icons use the existing global persistent sampled-image descriptor-heap registry.

No per-widget descriptor allocations; widgets reference persistent or FrameContext heap handles.

`AssetId` -> loaded texture -> descriptor index occurs through normal asset loading.

## 11. Clip rectangles

Baseline clipping:

```text
nested axis-aligned clip rectangles
```

Renderer uses:

```text
scissor state
and/or
clip index data
```

depending on batching.

Rounded-rectangle geometry performs analytical edge clipping.

Do not add stencil-based arbitrary masks unless real UI content needs them.

## 12. Batching order

Build deterministic draw ordering by:

```text
UI layer
clip
pipeline/primitive class
stable tree/render order
```

Bindless textures avoid texture-based reorder requirements.

## 13. Text shaping

Use HarfBuzz for shaping.

Inputs include:

```text
UTF-8/string
font face
font size
language
script
direction
OpenType features
max width/wrapping constraints
```

Output:

```text
glyph IDs
positions
clusters
advances
bounds
```

## 14. Font rasterization

Use FreeType.

Baseline glyph representation:

```text
coverage bitmap
R8_UNORM
```

Use hinting/configuration appropriate for UI text.

No MSDF dependency for normal text.

## 15. Glyph atlas

Starting atlas pages:

```text
2048 × 2048 R8_UNORM
```

Size buckets come from theme typography.

Example starting set:

```text
14
16
18
20
24
28
32
40
48
64
```

Actual content/theme may use fewer/more.

## 16. Glyph atlas lifetime

Maintain:

```text
font face
size
glyph ID
render mode
atlas page/rect
last use
```

Atlas eviction/repack must not invalidate glyph instances already referenced by an in-flight frame.

Use FrameContext/timeline-safe retirement.

## 17. Text shaping cache

Cache key includes:

```text
font face
size
language
script/direction
feature set
text hash
maximum width
```

Cached output:

```text
UiGlyphRun
```

Measurement/layout and rendering use the same shaped run.

## 18. Premultiplied alpha

All UI color output is premultiplied.

Composite:

```text
out.rgb = ui.rgb + background.rgb * (1 - ui.a)
out.a   = ui.a + background.a * (1 - ui.a)
```

UI textures are imported/converted consistently with this convention or multiplied in shader at a defined point.

## 19. HDR pipeline

UI authoring:

```text
sRGB / semantic UI colors
```

HDR conversion:

```text
sRGB decode
    ->
linear Rec.709
    ->
linear Rec.2020
    ->
scale so nominal white = 203 nits
```

Composite after ACES scene rendering into display-linear Rec.2020.

Then:

```text
ST2084/PQ
```

for HDR output.

UI bypasses scene exposure and bloom.

## 20. HDR limits

Baseline nominal white:

```text
203 nits
```

HDR qualification/mastering target:

```text
DisplayHDR-600-class / nominal 600-nit qualification peak
```

Runtime peak luminance follows the active output descriptor. Do not map ordinary UI white to the qualification peak or to an arbitrary display maximum.

Exceptional authored UI highlights above reference white require explicit style/token intent.

## 21. SDR

Same authored UI.

SDR path:

```text
sRGB authoring
    ->
linear Rec.709
    ->
100-nit reference presentation
    ->
composite
    ->
sRGB output
```

No separate UI content/layout system.

## 22. UI render snapshot

Conceptual:

```cpp
struct UiRenderSnapshot {
    uint64_t frameIndex;

    Span<const UiDrawInstance> draws;
    Span<const UiClipRect> clips;
    Span<const UiEmbeddedViewRequest> embeddedViews;
    Span<const UiGlyphRunRef> glyphRuns;

    UiOutputTransform output;
};
```

Snapshot is immutable after publication.

## 23. Render-thread responsibilities

Render thread:

```text
consume UiRenderSnapshot
ensure glyph/image resources
render embedded views
upload UI instance data
record UI pass
composite into display-linear output
```

Main does not call Vulkan.

## 24. UI frame-graph pass

Logical order:

```text
RenderExtent Scene HDR
    ->
ACES/display transform to display-linear output
    ->
SceneOutputScale to OutputExtent
    ->
Embedded view resolves as needed
    ->
UiComposite at UiRasterExtent = OutputExtent
    ->
PQ encode / SDR encode at OutputExtent
    ->
Present
```

Architecture 072 owns the render/output/UI extent and scaling contract.

Ordinary UI is rasterized at OutputExtent rather than being scene-upscaled from RenderExtent.

If some HUD elements intentionally interact with pre-display scene content, they must be explicitly classified as Presentation Overlay rather than ordinary UI.

## 25. GPU targets

Engineering targets, not measured results:

```text
UI upload/batch CPU on Render:
    <= 0.15 ms

UI GPU standard HUD/menu:
    <= 0.30 ms

UI GPU heavy menu:
    <= 0.50 ms
```
