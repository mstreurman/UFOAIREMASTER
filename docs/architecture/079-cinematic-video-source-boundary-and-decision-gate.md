# Cinematic / Video Source Boundary and Backend Closure

**Status:** Source-grounded boundary; backend resolved by ADR-035 / architecture 083  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Related:** architecture 045, 046, 076

## 1. Why this document exists

Baseline 029 identified cinematic/video as a real source subsystem with no corresponding remaster specification (`M029-003`).

This document records what must be preserved and the source boundary that remains in force after ADR-035 selected FFmpeg as the production decoder backend.

## 2. Audited legacy source

The source tree contains:

```text
src/client/cinematic/cl_cinematic_ogm.cpp/.h
src/client/cinematic/cl_cinematic_roq.cpp/.h
src/client/cl_video.cpp/.h
```

The OGM decoder source describes the supported historical container/codec combination as:

```text
Ogg wrapper
Vorbis audio
Xvid video or Theora video
```

and explicitly contrasts it with the older RoQ cinematic format.

The legacy build also links/uses Ogg/Theora/Vorbis-era dependencies.

## 3. Preservation requirements

The remaster must preserve production content behavior for existing cinematics/sequences unless content is intentionally transcoded as a separate project decision.

Required semantic behavior:

```text
play named cinematic/sequence asset
video frame timing
associated audio timing
skip/abort input semantics
end-of-stream/end-of-sequence callback behavior
aspect-ratio/presentation policy compatible with existing content
failure handling for missing/unsupported media
UI/sequence integration
```

Canonical gameplay must never depend on a decoded video frame.

## 4. Target ownership

The final boundary is:

```text
CinematicController
    owns playback state/timing/skip/end semantics

DecoderBackend
    produces decoded video frames + audio packets/PCM

VulkanVideoPresentation
    owns GPU image upload/conversion/composition

AudioRuntime
    owns playback/mix of cinematic audio

RetainedUI / Sequence layer
    owns placement/overlay/subtitle/control presentation
```

Decoder code must not issue immediate renderer draw calls.

## 5. Video frame contract

The decoder backend should publish frames with explicit metadata:

```text
presentation timestamp
duration
coded width/height
display aspect ratio
pixel format / color metadata
frame serial
end/discontinuity flags
```

The Vulkan presentation layer converts/imports to the renderer's defined color/output pipeline without treating legacy encoded pixel values as scene-linear lighting.

## 6. Audio synchronization

Cinematic audio uses the same master playback timeline as the video controller.

The exact decoder backend may deliver compressed packets or decoded PCM, but the final audio path must route through the remaster audio runtime rather than a second unmanaged audio device/context.

## 7. Threading

Decode may run asynchronously, but publication is bounded:

```text
decode worker
    -> bounded frame/audio queues
    -> playback controller
    -> Render / AudioControl consumers
```

Skipping/stopping must cancel/drain work cleanly and must not stall the canonical game loop waiting on arbitrary decoder work.

## 8. Content compatibility test corpus

Before deleting the legacy decoder path, build a corpus containing every shipped cinematic/sequence media asset and verify:

```text
opens successfully
correct dimensions/aspect
A/V duration and sync
first/last frame behavior
skip behavior
sequence transition behavior
no unbounded decode queue growth
no renderer/audio resource leaks
```

## 9. Backend decision — resolved

ADR-035 accepts FFmpeg/libavformat/libavcodec as the primary production decoder backend while preserving all shipped-format behavior through compatibility testing. Architecture 083 is the exact decode/queue/presentation contract. The legacy RoQ/OGM decoders remain only until the corpus gate passes.

## Source references

- cinematic source tree: https://github.com/ufoaiorg/ufoai/tree/763173ed036ebbee32c2a7bf6aefa19748df89ff/src/client/cinematic
- client video path: https://github.com/ufoaiorg/ufoai/blob/763173ed036ebbee32c2a7bf6aefa19748df89ff/src/client/cl_video.cpp
