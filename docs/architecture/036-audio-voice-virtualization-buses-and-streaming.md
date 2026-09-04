# Audio Voice Virtualization, Buses and Streaming

**Status:** Implementation specification baseline  
**Related ADR:** ADR-024

## 1. Logical voice pool

Starting maximum:

```text
512 logical voices
```

A logical voice contains:

```text
AudioVoiceId
sound asset/reference
owner/emitter ID
bus
priority class
flags
logical playback cursor/time
gain/pitch
spatial parameters
loop state
environment/occlusion state
physical source assignment or none
```

Logical voices do not own OpenAL source IDs.

## 2. Physical source pool

Starting OpenAL source pool:

```text
96 sources
```

Allocate at audio initialization.

Do not generate/delete ordinary sources for every one-shot.

The exact pool size is benchmark-tunable.

## 3. Source classes

Physical pool is shared, but priority reservations protect:

```text
UI
Dialogue
Music/stream control
critical feedback
```

from being starved by low-value world ambience.

Reservations are minimum guarantees, not permanently partitioned source arrays.

## 4. Voice priority

Each logical voice computes a deterministic score from:

```text
authored priority class
bus importance
estimated post-attenuation audibility
distance
loop/one-shot state
age
critical-feedback flag
dialogue/UI reservation
```

Tie break:

```text
AudioVoiceId
```

not scheduler/completion order.

Exact scoring weights remain mix-tuning constants.

## 5. Physical assignment

At each relevant audio update:

```text
rank eligible logical voices
    ->
retain currently assigned sources where competitive
    ->
promote highest-value virtual voices
    ->
virtualize/steal lowest-value physical voices
```

Use hysteresis to avoid source thrashing near the 96-source boundary.

## 6. Virtual playback clock

Virtual voices continue advancing in logical time.

When promoted:

```text
restore playback offset
apply current gain/spatial state
start physical source from current logical position
```

If a virtual non-looping voice reaches its end:

```text
retire it without ever consuming a physical source
```

Do not restart virtualized sounds from the beginning.

## 7. Source stealing

When a physical source is reassigned:

```text
short release/fade where practical
stop
detach buffer/queue
clear direct filter
clear aux sends
reset source properties
assign new logical voice
```

Avoid filter/send state leaking between voices.

## 8. Logical buses

Baseline buses:

```cpp
enum class AudioBus : uint8_t {
    Master,
    Sfx,
    Dialogue,
    Ambience,
    Music,
    UI
};
```

`Master` is global.

Individual voices belong to one non-Master bus.

## 9. Bus gain

Final dry source gain includes:

```text
asset gain
voice/event gain
distance model
occlusion gain
voice fade
bus gain
master gain
```

Implement:

```text
Master:
    listener/global gain where practical

other buses:
    source gain multiplier
```

Bus values are smoothed to prevent zippering.

## 10. Ducking

Architecture supports deterministic bus ducking envelopes.

Do not lock artistic dB values in the engine architecture.

Content/mix configuration may define relationships such as:

```text
Dialogue -> Music
Dialogue -> Ambience
UI critical -> selected Sfx
```

Ducking affects presentation only.

## 11. Spatial source format

Baseline positional world sound:

```text
mono
3D positioned
```

Stereo/multichannel sources are reserved mainly for:

```text
music
UI
non-positional ambience beds
```

and explicitly disable spatialization where supported.

## 12. Distance model

Use one renderer-owned attenuation policy translated into OpenAL source/reference parameters.

Do not let individual legacy code directly mutate arbitrary OpenAL distance-model global state.

Baseline OpenAL global distance model:

```text
inverse-distance-clamped
```

Per-sound metadata controls:

```text
reference distance
maximum distance
rolloff
```

Presentation World distances convert to audio meters using architecture 051:

```text
32 presentation units = 1 meter
```

## 13. Doppler

Set:

```text
alDopplerFactor(0)
```

baseline.

Camera panning/zoom is not physical listener movement.

If a future sound explicitly needs Doppler, implement it as authored presentation pitch logic or revise this policy.

## 14. Static-buffer sounds

Short/common SFX are decoded into OpenAL buffers and cached.

Buffer cache tracks:

```text
asset ID
format
channels
sample rate
sample frames
OpenAL buffer
memory bytes
last use
ref count
```

Eviction never deletes a buffer still referenced by an active physical source.

## 15. Streaming

Use queued OpenAL buffers for baseline long-form streaming.

Do not require `AL_SOFT_callback_buffer`.

Typical use:

```text
music
long ambience
long dialogue if needed
```

Starting stream queue:

```text
4 OpenAL buffers
1024 sample frames/buffer
48 kHz target
```

Nominal queued PCM time:

```text
~85 ms
```

for 4 x 1024 frames.

The exact queue size is benchmark/underrun tunable.

## 16. Stream decoding

Background/SmtFriendly jobs may decode compressed data into CPU PCM rings.

AudioControl owns:

```text
alBufferData
alSourceQueueBuffers
alSourceUnqueueBuffers
stream source start/stop
```

Decoded blocks move through a bounded CPU queue.

Do not perform large file decompression on AudioControl.

## 17. Runtime encoded audio

Initial migration baseline may continue to use existing project audio compression/containers such as Ogg Vorbis for runtime stream data.

Short clips may also be sourced from existing project sound assets and decoded to PCM at load.

A dedicated remaster audio container can be added later without changing OpenAL runtime architecture.

## 18. Stream underrun

If a stream source stops because its queue starved:

```text
record underrun
refill available buffers
restart only when safe queue depth exists
```

Music logical time remains renderer-controlled rather than treating an underrun as canonical timing.

## 19. Latency telemetry

If available, use:

```text
AL_SOFT_source_latency
ALC_SOFT_device_clock
```

for diagnostics of:

```text
source playback position
estimated device/output latency
stream timing
```

Do not make gameplay timing depend on those values.
