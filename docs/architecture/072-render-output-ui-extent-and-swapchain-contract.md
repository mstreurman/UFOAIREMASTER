# Render, Output, UI Extent and Swapchain Contract

**Status:** Exact implementation specification  
**Related ADR:** ADR-032  
**Primary qualification profile:** native Wayland, RenderExtent 1920x1080, 60 Hz / near-60 FPS; runtime output/render mode selectable

## 1. Three distinct coordinate/resolution domains

```text
RenderExtent
    scene/rendering pixel extent

OutputExtent
    current Vulkan swapchain pixel extent

UiLogicalExtent
    retained-UI design coordinate extent

UiRasterExtent
    physical UI raster/composite pixel extent
```

They are never aliases by assumption.

## 2. RenderExtent

`RenderExtent` is runtime-configurable. Supported policy modes are:

```text
NativeOutput:
    RenderExtent = OutputExtent

Explicit:
    RenderExtent = user-selected internal render width/height
```

The mandatory B580/i9-9900K qualification profile is:

```text
RenderExtent.width  = 1920
RenderExtent.height = 1080
```

No shader, dispatch, history allocation or CPU-side renderer constant may assume that 1920x1080 is the only runtime value.

RenderExtent owns:

```text
G-buffer
primary raster visibility
SceneColor HDR
depth
motion vectors
object IDs
directional shadow launch/reconstruction grids
ReSTIR half-resolution grid
reflection launch/reconstruction
DDGI screen gather
scene-space VFX raster targets
scene post-processing before output scaling
```

Existing 1920x1080 renderer budgets/ray counts describe the **qualification RenderExtent** unless a document explicitly says OutputExtent. Runtime dimensions are always read from the active RenderExtent.

## 3. OutputExtent

OutputExtent is the exact current swapchain image extent accepted through Vulkan WSI/surface capabilities.

The renderer:

```text
queries WSI
chooses/creates swapchain
records actual chosen extent
uses that exact extent for final output
```

It does not infer OutputExtent from:

```text
monitor marketing/native mode
RenderExtent
UI logical resolution
legacy SDL window size
```

A user-selected output resolution/display mode is a **request**. SDL/display-mode selection and Vulkan WSI determine the actual resulting `OutputExtent`, which must be reported back to settings/telemetry.

On Wayland, compositor/surface behavior is authoritative through Vulkan WSI.

## 4. UiLogicalExtent

Fixed design space:

```text
UiLogicalExtent = 1920x1080 logical units
```

Existing UI scale remains:

```text
fit-to-output scale
*
user UI scale
```

## 5. UiRasterExtent

Baseline:

```text
UiRasterExtent = OutputExtent
```

This keeps:

```text
text
glyph edges
lines
icons
HUD geometry
developer overlays
```

crisp at the actual swapchain resolution rather than first rasterizing UI at RenderExtent.

## 6. Frame composition order

Baseline HDR order:

```text
RenderExtent scene HDR
    ->
scene post
    ->
ACES/display transform to display-linear Rec.2020 at RenderExtent
    ->
SceneOutputScale to OutputExtent in display-linear linear-light space
    ->
UiComposite at OutputExtent
    ->
developer output-space overlays at OutputExtent
    ->
PQ encode at OutputExtent
    ->
swapchain
    ->
present
```

SDR:

```text
RenderExtent scene
    ->
scene post/display transform
    ->
SceneOutputScale to OutputExtent in display-linear space
    ->
UiComposite at OutputExtent
    ->
SDR transfer encode at OutputExtent
    ->
present
```

Ordinary UI is not scene-upscaled.

## 7. Identity-scale case

If:

```text
RenderExtent == OutputExtent
```

SceneOutputScale is an identity/no-op.

Frame Graph may elide the copy only when the resource/format/lifetime contract permits it without changing observable output ordering.

## 8. Baseline output scaler

The first implementation uses:

```text
linear-light bilinear filtering
```

for scene-to-output scaling.

This is a deterministic presentation scaler, not a temporal reconstruction/upscaling dependency.

Benchmark alternatives may include:

```text
sharpened bilinear
Catmull-Rom/bicubic
other deterministic spatial filters
```

They require visual/performance comparison before replacing the baseline.

The 1080p60 target must stand without XeSS/FSR/DLSS-style performance dependence.

## 9. Screen-space shader coordinates

Architecture 063 `renderUV` remains a **RenderExtent** coordinate.

Define separate output coordinate:

```text
outputUV.x = (outputPixelX + 0.5) / OutputExtent.width
outputUV.y = (outputPixelY + 0.5) / OutputExtent.height
```

Do not use renderUV to address OutputExtent images or outputUV to index G-buffer histories.

## 10. Temporal histories

Scene temporal histories are RenderExtent histories.

Changing RenderExtent invalidates/recreates:

```text
motion-dependent histories
shadow histories
ReSTIR histories
reflection histories
other screen-grid histories
```

Changing only OutputExtent does not alter world/scene temporal sample identity, but output/UI resources are recreated.

## 11. Swapchain recreation

On OutputExtent/surface changes:

```text
wait only for required affected in-flight swapchain ownership/lifetimes
recreate swapchain/output-resolution resources
keep canonical state intact
keep Presentation World intact
retain RenderExtent histories when still compatible
```

Do not globally `vkDeviceWaitIdle` as an ordinary resize policy unless required for a specific recovery path.

## 12. HDR metadata

HDR metadata describes the active output/swapchain/display presentation path.

It does not redefine RenderExtent.

The DisplayHDR-600-class qualification profile remains:

```text
nominal qualification peak target  600 nit
ordinary UI reference               203 nit
```

Runtime HDR may be Off/On/Auto per ADR-046/architecture 090. The actual selected display capability/output descriptor determines runtime peak/min/average metadata; 600 nits is not a hardcoded output ceiling.

## 13. Output-dependent GPU accounting

OutputExtent-dependent work is measured separately:

```text
SceneOutputScale
UiComposite
developer output overlays
PQ/SDR encode
swapchain output
```

The 1920x1080 qualification scene GPU budget does not pretend output-dependent passes are free when OutputExtent differs or is larger.

## 14. Regression cases

At minimum visual/presentation regression includes:

```text
qualification-identity:
    RenderExtent 1920x1080
    OutputExtent 1920x1080

scaled-output:
    RenderExtent 1920x1080
    fixed larger OutputExtent supported by the test environment

native-non1080:
    RenderExtent = OutputExtent
    a non-1920x1080 mode supported by the test environment
```

The exact output/render extents and refresh/HDR state are recorded in the replay/regression manifest.

## 15. Legacy renderer independence

This contract applies to the new Vulkan renderer.

It does not require fixing or preserving legacy SDL/OpenGL fullscreen sizing behavior.
