# ADR-018 — ACEScg Working Space + ACES 2 HDR/SDR Output Pipeline

**Status:** Accepted  
**Decision type:** Color management / HDR output  
**Primary display target:** VESA DisplayHDR 600-class presentation  
**Primary WSI target:** Fedora 44 KDE native Wayland

## Context

The remaster requires a 1920x1080/60 FPS/DisplayHDR-600-class **qualification profile** together with runtime-selectable resolution, refresh and HDR state. The color pipeline itself must support:

```text
HDR presentation when selected and supported
SDR presentation when selected or required
PBR lighting
ray-traced reflections/GI
bright emissive effects
stable UI brightness
runtime output-target luminance metadata
```

The B580 reference Vulkan capture exposes native Wayland HDR10/ST2084 swapchain color spaces.

## Decision

The renderer working color space is:

```text
ACEScg
AP1 primaries
scene-linear
FP16/FP32 arithmetic/storage as appropriate
```

The main HDR scene target is:

```text
VK_FORMAT_R16G16B16A16_SFLOAT
linear ACEScg/AP1
scene-referred
```

## Source texture decode

Base-color/emissive source assets remain conventional sRGB-authored images.

Processing:

```text
sRGB texture
    ->
hardware sRGB decode
    ->
linear Rec.709/sRGB RGB
    ->
apply linear material factors
    ->
3x3 conversion
    ->
linear ACEScg/AP1
```

Normal, ORM and other data textures remain non-color data and are not color transformed.

## HDR scene pipeline

Baseline:

```text
PBR + RT lighting
linear ACEScg
    |
forward transparency
    |
exposure
    |
bloom
    |
creative grade
    |
ACEScg/AP1 -> ACES2065-1/AP0
    |
ACES 2 Rendering Transform
target = active output descriptor (Rec.2020/D65 for HDR; peak from selected/display target)
    |
display-linear Rec.2020
    |
HDR-aware UI composition
    |
ST.2084 / PQ encoding
    |
10-bit HDR swapchain
```

## Display targets

The B580 performance/quality qualification profile uses:

```text
Rec.2020
D65
600 nit peak target
203 nit reference/graphics white
```

At runtime, HDR peak/min/average metadata and output-transform parameters come from the selected output target/capability path rather than a hardcoded 600-nit constant. A user's HDR-off choice uses the SDR path even on an HDR-capable display.

SDR target:

```text
Rec.709 / sRGB
D65
100 nit display target
```

The same scene rendering and artistic grade feed both output transforms.

Do not create separate HDR and SDR lighting models.

## UI

UI does not pass through scene exposure or bloom.

UI pipeline:

```text
sRGB UI artwork
    ->
linear Rec.709
    ->
Rec.2020 conversion
    ->
scale graphics white to 203 nits
    ->
composite into display-linear HDR scene
    ->
PQ encode
```

This makes UI brightness stable independently of tactical-scene exposure.

## HDR swapchain

Preferred native Wayland HDR swapchain:

```text
VK_FORMAT_A2B10G10R10_UNORM_PACK32
VK_COLOR_SPACE_HDR10_ST2084_EXT
```

Alternative ten-bit channel ordering may be accepted only if the surface/platform path requires it and the encode path is verified.

## HDR metadata

HDR metadata is built from the actual selected output path and the renderer's active output descriptor. For the 1080p60 DisplayHDR-600 qualification profile the nominal peak target is 600 nits, but runtime metadata is not hardcoded to that value.

Required fields include:

```text
display primaries / white point
maxLuminance
minLuminance when known
maxContentLightLevel when authored/measured
maxFrameAverageLightLevel when authored/measured
```

Unknown values use the platform/API-defined unknown representation where permitted. User HDR selection, actual surface capability and actual output metadata remain observable separately.

## Native Wayland requirement

HDR mode is supported only when the actual Vulkan surface exposes the required HDR10/ST2084 color space.

On the reference machine this occurs on native Wayland.

XCB/Xlib/XWayland must not silently be treated as an HDR-capable path merely because the qualification target is DisplayHDR 600-class.

## Pre-exposure

No renderer-wide pre-exposure is required initially.

Use stable scene-linear FP16 values first.

Pre-exposure may be added later only if profiling/quality analysis demonstrates a concrete need.

## Consequences

- all renderer lighting operates in one wide-gamut scene-linear space;
- SDR/HDR appearance is derived from one scene;
- UI luminance remains predictable;
- emissive/RT radiance naturally exceeds SDR range;
- output color management becomes explicit and testable.
