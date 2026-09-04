# Texture Orientation, Output Debug and Audio Identity Contract

**Status:** Exact implementation specification  
**Related ADR:** ADR-024, ADR-027, ADR-029

## 1. Runtime UV orientation

All runtime `.rmesh`/material texture coordinates are normalized to:

```text
UV (0,0) = top-left texel
+U       = right
+V       = down
```

The runtime renderer does no hidden source-format-dependent V flip.

## 2. Offline normalization

Import/conversion tools inspect source-format conventions and convert:

```text
vertex UVs
image orientation
KTX2 orientation metadata/content
```

into the runtime convention.

The generated runtime asset must sample correctly without a runtime orientation branch.

## 3. Tangent-space normal map

Runtime tangent-space normal vector:

```text
+X = +T
+Y = +B
+Z = +N
```

with:

```text
B = tangentSign * cross(N, T)
```

A source normal map using `-Y` green convention is converted offline by flipping the green component.

BC5 runtime decode produces the normalized +Y convention above.

## 4. Raster/RT material agreement

Raster and RT hit material reconstruction use identical:

```text
UV orientation
normal-map channel convention
tangent basis
texture LOD policy for their respective derivative/ray context
```

No RT-only V/green flip exists.

## 5. Output-reference semantics

`FrameConstants` uses mode-neutral:

```text
outputReferenceWhiteNits
outputPeakNits
```

Runtime rule:

```text
HDR:
    outputReferenceWhiteNits = 203
    outputPeakNits           = resolved active output/renderer peak target

SDR:
    outputReferenceWhiteNits = 100
    outputPeakNits           = 100
```

The accepted HDR graphics/reference white remains `203` nits and the SDR target remains `100` nits. The B580/i9-9900K qualification profile uses a `600`-nit HDR peak, but that peak is not a universal runtime constant. `outputPeakNits` must reflect the actual selected output descriptor and active user/output policy from architecture 072/090.

## 6. RT Isolation red

“Pure red” means zero green/blue and red at output reference white:

```text
nonRtDisplayLinear =
    (outputReferenceWhiteNits, 0, 0)
```

Therefore:

```text
HDR = (203, 0, 0) nits
SDR = (100, 0, 0) nits
```

before output transfer encoding.

This is intentionally obvious rather than approximately 1 nit.

Other diagnostic hues are likewise normalized hues scaled by the chosen diagnostic/reference intensity.

## 7. Diagnostic compositing order

RT diagnostic scene-data capture/resolve occurs before developer UI/crosshair composition.

The `+` overlay:

```text
does not write G-buffer identity/material data
does not change the pixel being probed
does not enter RT Isolation classification
```

The developer panel/crosshair is composited afterward.

## 8. Jolt gravity baseline

Presentation Jolt world:

```text
up       = +Z
gravity  = (0, 0, -9.81) m/s^2
```

The magnitude is a presentation baseline and may be artistically tuned only through an explicit presentation setting/preset.

It remains non-authoritative.

## 9. AudioEmitterId

```cpp
struct AudioEmitterId {
    uint32_t slot;
    uint32_t generation;
};

static_assert(sizeof(AudioEmitterId) == 8);
```

Generation zero is invalid.

Slot `0xffffffff` is invalid.

## 10. Audio identity policy

Ordered asynchronous `AudioCommandQueue` commands identify long-lived emitters/voices with:

```text
AudioEmitterId
AudioVoiceId
```

They do not use `RenderObjectId` as their lifetime key.

Continuous `AudioStateSnapshot` may carry a `RenderObjectId` for debug/correlation only.

## 11. Audio emitter reuse

Main-owned emitter-slot reuse increments generation.

A stale command with an old generation is rejected/ignored by AudioControl and surfaced in debug telemetry if unexpected.

This decouples audio command lifetime from Presentation World renderer-ID namespace reset.

## AudioVoiceId exact reuse policy

Architecture 065 owns exact `AudioVoiceId` layout/reuse/wrap semantics.

`AudioEmitterId` follows the same invalid/generation/wrap policy.

A stale generation is never redirected to a newly allocated voice/emitter.

## Screen-space projection authority

Architecture 063 owns the final Vulkan viewport, clip/NDC->render-UV and jitter-sign convention.

Texture UV orientation in this document and rendered screen UV now share a top-left/+V-down convention, but they remain semantically distinct coordinate domains.
