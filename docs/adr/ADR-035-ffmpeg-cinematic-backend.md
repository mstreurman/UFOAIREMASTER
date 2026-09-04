# ADR-035 — FFmpeg Cinematic Backend

**Status:** Accepted  
**Decision:** `VIDEO-001`

## Decision

Use FFmpeg libraries as the production cinematic demux/decode backend:

```text
libavformat
libavcodec
libavutil
libswresample where audio conversion is required
libswscale only when pixel-format/color conversion cannot be expressed directly
```

The compatibility contract is behavioral, not decoder-implementation compatibility. Existing shipped RoQ and OGM/Ogg/Vorbis/Xvid/Theora-era assets must pass corpus tests for dimensions, duration, A/V sync, skip semantics and sequence transitions before legacy decoders are removed.

Decoded video is uploaded through the Vulkan presentation path; decoded PCM is submitted through the OpenAL presentation path. FFmpeg never owns renderer or audio-device lifetime.

Architecture 083 is the implementation authority.
