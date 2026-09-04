# ADR-004 — OpenAL Soft + EFX Audio

**Status:** Accepted  
**Decision type:** Audio architecture baseline

## Context

The remaster targets a substantially modernized presentation layer while keeping canonical gameplay unchanged.

The reference Fedora 44 system exposes OpenAL Soft 1.24.2 with EFX 1.0.

The tested device reports support for:

- 3D OpenAL playback;
- EFX;
- two auxiliary sends;
- low-pass, high-pass, and band-pass filters;
- EAX Reverb and Reverb;
- additional effects including chorus, distortion, echo, flanger, frequency shifting, pitch shifting, compression, and equalization;
- OpenAL Soft HRTF capability.

## Decision

OpenAL Soft is the remaster's audio implementation target.

EFX is required for environmental-audio presentation.

The audio architecture should support:

- spatialized 3D sources;
- environmental reverberation;
- filtering;
- acoustic-zone presentation;
- occlusion-style audio presentation;
- environmental transitions;
- configurable/device-dependent HRTF.

## Gameplay boundary

Audio is presentation-only.

Audio propagation, EFX filters, acoustic occlusion, or HRTF results must not modify gameplay detection, AI awareness, or any other canonical game state.

## HRTF policy

HRTF support is a capability, not a mandatory always-on output mode.

The selected playback device, user configuration, speaker/headphone arrangement, and OpenAL Soft capabilities determine whether HRTF is enabled.

## Current status and remaining work

ADR-024 and architecture 035–038 now resolve the runtime architecture for:

```text
source/logical-voice pools
bus architecture
EFX send/slot policy
environment zones/portals
streaming
HRTF/device controls
```

Resolved by later architecture:

- reference-v1 acoustic zone/portal/BVH records and `.rmap` ownership are fixed by architecture 031/085.

Still content/performance-tunable rather than architecture blockers:

- final environment preset library;
- authored loudness/mix/ducking values;
- final source-priority scoring weights;
- runtime BVH construction/optimization strategy consistent with the persisted semantics;
- an optional future dedicated remaster audio asset container, which would require a separately versioned format if ever adopted.

## Baseline 030 persisted-acoustic closure

Architecture 085 fixes reference-v1 acoustic zone/portal/BVH records. Environment preset/mix values remain content/tuning rather than architecture blockers.
