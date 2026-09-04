# FFmpeg Cinematic Decode and Presentation Contract

**Status:** Implementation specification baseline  
**Authority:** ADR-035, architecture 079

## 1. Backend

Production cinematics use FFmpeg libraries. The old custom RoQ/OGM decoder code remains only until compatibility corpus parity is proven.

## 2. Ownership

`CinematicController` owns logical playback state. A decode worker owns FFmpeg contexts. Renderer/audio systems own their resources.

```text
asset/VFS reader -> AVIOContext -> libavformat -> libavcodec
                                      | video -> bounded decoded-video queue -> Vulkan upload/composite
                                      | audio -> bounded decoded-audio queue -> resample if required -> OpenAL stream
```

FFmpeg callbacks use project VFS reads/seeks; the decoder is not permitted to bypass project asset identity/file policy for shipped content.

## 3. Video frame contract

A decoded frame publication contains:

```text
playback generation
frame sequence
PTS in common playback timebase
width/height
pixel format / color metadata
plane pointers or owned staging payload
line strides
end-of-stream/discontinuity flags
```

Conversion target for baseline upload is a renderer-supported 8-bit SDR format unless source metadata and accepted output path justify a higher-fidelity path. Cinematics are presentation content and are composed through the same output/HDR transform as UI/video surfaces.

## 4. Audio contract

Decode to a project-owned PCM stream representation accepted by the OpenAL streaming layer. Resample/channel-remap with libswresample only when source and output formats differ.

Audio clock is the preferred master clock when an audio stream is present and healthy. Otherwise playback uses monotonic presentation time. Video frames may be dropped to catch up; audio samples are not stretched by an ad-hoc renderer clock.

## 5. Queueing

Both decoded queues are bounded. Decoder work must stop/backpressure rather than grow memory without limit.

Seek/skip increments playback generation and invalidates old queued frames/samples.

## 6. Compatibility corpus gate

Before removing legacy decoders, enumerate every shipped cinematic and verify:

```text
open/demux/decode success
expected video dimensions and aspect
expected stream duration within tolerance
A/V sync and monotonic PTS handling
first/last frame behavior
skip input behavior
sequence/campaign transition behavior
bounded memory
no leaked Vulkan/OpenAL/FFmpeg resources
```

If Fedora's default FFmpeg build lacks a decoder required by shipped content, the project must not silently drop compatibility. The resolution must be documented as a dependency/content decision before legacy removal.
