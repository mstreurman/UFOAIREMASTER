# ADR-004 — OpenAL Soft + EFX Audio

**Status:** Accepted  
**Decision type:** Audio architecture baseline

## Context

The remaster targets a substantially modernized presentation layer while keeping canonical gameplay unchanged.

The 2026-09-04 Fedora 44 workstation capture exposed OpenAL Soft 1.24.2 with EFX 1.0. That capture remains historical capability evidence. The reference workstation was subsequently rotated to OpenAL Soft 1.25.2 on 2026-09-07, matching the accepted >=1.25.2 implementation-version baseline for the future production audio runtime.

The tested device reports support for:

- 3D OpenAL playback;
- EFX;
- two auxiliary sends;
- low-pass, high-pass, and band-pass filters;
- EAX Reverb and Reverb;
- additional effects including chorus, distortion, echo, flanger, frequency shifting, pitch shifting, compression, and equalization;
- OpenAL Soft HRTF capability.

## Decision

OpenAL Soft **>=1.25.2** is the remaster's reference audio implementation target for production qualification. The core API contract remains stable **OpenAL 1.1** rather than a fictitious newer OpenAL core version.

`ALC_EXT_EFX` is required for environmental-audio presentation. `ALC_SOFT_HRTF` and at least two auxiliary sends/source are also required reference capabilities. Additional OpenAL Soft extensions remain runtime capability-probed unless explicitly promoted by later architecture.

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

The reference workstation is now on OpenAL Soft 1.25.2 and the M0.3/M0.5 environment evidence was resealed after that rotation. M8 production-audio closure still requires its dedicated device/EFX/HRTF runtime qualification and production-audio soak; the version upgrade alone does not close M8.

Still content/performance-tunable rather than architecture blockers:

- final environment preset library;
- authored loudness/mix/ducking values;
- final source-priority scoring weights;
- runtime BVH construction/optimization strategy consistent with the persisted semantics;
- an optional future dedicated remaster audio asset container, which would require a separately versioned format if ever adopted.

## Baseline 030 persisted-acoustic closure

Architecture 085 fixes reference-v1 acoustic zone/portal/BVH records. Environment preset/mix values remain content/tuning rather than architecture blockers.
