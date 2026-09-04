# OpenAL Device, Context, Audio Thread and Snapshot Runtime

**Status:** Implementation specification baseline  
**Related ADR:** ADR-024

## 1. AudioControl thread

Create one fixed engine thread:

```text
AudioControl
```

Affinity:

```text
one SMT sibling belonging to a worker physical core
```

This replaces one of the six baseline SMT helper workers.

Result:

```text
Main                1
Render              1
Primary workers     6
SMT helpers         5
AudioControl        1
---------------------
engine fixed threads 14
```

OpenAL Soft may create its own backend/mixer threads outside this count.

## 2. OpenAL ownership rule

Only AudioControl may call:

```text
alc*
al*
EFX APIs
HRTF/device-reset APIs
```

No OpenAL object handle is exposed to Main/worker/render subsystems.

Renderer/presentation audio handles are renderer-owned generational IDs.

## 3. Device startup

AudioControl startup:

```text
enumerate OpenAL playback devices
resolve user preference: SystemDefault or NamedOpenALDevice
    ->
alcOpenDevice(resolved specifier or NULL for system default)
    ->
query ALC extensions/capabilities
    ->
create context
    ->
make current
    ->
query AL extensions
    ->
create source pool
    ->
create EFX objects
    ->
apply output/HRTF settings
    ->
publish AudioReady
```

Reference output rate target:

```text
48,000 Hz
```

Request 48 kHz but report actual context/device rate.


## 3.1 Requested versus actual playback device

Runtime configuration never hardcodes the development machine's AE-7, Bluetooth speaker, or any other endpoint. Settings persist either:

```text
SystemDefault
or
NamedOpenALDevice(specifier)
```

Use `ALC_ENUMERATE_ALL_EXT` when available to populate the device chooser. The exact OpenAL specifier string is the runtime open request; a human-readable UI label may be derived separately.

On a user device change:

```text
prefer ALC_SOFT_reopen_device when supported and suitable
otherwise rebuild device/context using the logical-state-preservation path
```

If a preferred named device disappears, enter recovery/fallback without overwriting the saved preference. The actual opened device is always reported independently from the requested preference.

The 2026-09-04 10:47 audio capture observed `LG-PK5(56)` as the system/default OpenAL playback route over Bluetooth A2DP/aptX HD; this is evidence that the Fedora/OpenAL path can route dynamically and is **not** a production default.

## 4. Required target capabilities

For the reference target require:

```text
ALC_EXT_EFX
ALC_SOFT_HRTF
at least 2 auxiliary sends
```

Strongly preferred/probed:

```text
AL_SOFT_deferred_updates
AL_SOFT_source_latency
ALC_SOFT_device_clock
AL_SOFT_source_spatialize
AL_SOFT_source_resampler
ALC_EXT_disconnect
AL_EXT_debug / ALC_EXT_debug where available
```

Optional extensions must be feature-probed at runtime.

## 5. Deferred update batch

If `AL_SOFT_deferred_updates` is present:

```text
alDeferUpdatesSOFT()

apply:
    listener
    source transforms
    gains/pitches
    filters
    sends
    starts/stops where semantics permit

alProcessUpdatesSOFT()
```

Use one batch for a normal snapshot/control update.

If unavailable, execute the same update sequence normally.

Runtime behavior must not require the extension for correctness.

## 6. Audio service loop

AudioControl is event-driven with a bounded periodic wake.

Baseline maximum sleep:

```text
5 ms
```

Wake sources:

```text
new AudioCommand
new AudioStateSnapshot
stream refill deadline
device-state change
shutdown
```

The thread normally sleeps/futex-waits.

It is not a busy mixer thread; OpenAL Soft owns actual mixing.

## 7. Continuous state

Use double-buffer/latest-wins publication:

```cpp
struct AudioStateSnapshot {
    uint64_t frameIndex;

    AudioListenerState listener;
    AudioBusState buses;

    span<AudioEmitterState> emitters;
    span<AudioEnvironmentState> environments;

    uint32_t cutawayRevision;
};
```

Published state is immutable.

If AudioControl sees several snapshots queued, it may skip obsolete continuous snapshots and consume the newest.

## 8. Discrete command queue

Separate SPSC ring:

```text
Main -> AudioControl
```

Starting capacity:

```text
4096 commands
```

Commands include:

```text
PlayOneShot
StartLoop
StopVoice
StopObjectVoices
StartStream
StopStream
SetMusicState
DeviceSettingChanged
PausePresentationAudio
ResumePresentationAudio
```

Discrete commands remain ordered.

A newer continuous snapshot does not replace them.

## 9. Command overflow

Development:

```text
assert/log exact command producer/type
```

Release policy:

```text
never drop:
    UI critical
    dialogue
    music state
    explicit stop commands

may coalesce/drop only explicitly LowPriorityRepeatable SFX
```

Dropping an audio presentation command never changes canonical gameplay.

## 10. Audio handle

Architecture 065 is the exact `AudioVoiceId` layout/reuse/wrap authority.

No raw `ALuint` escapes AudioControl.

Stable audio owner IDs:

```text
AudioEmitterId
AudioVoiceId
```

are separate from OpenAL source IDs.

`PresentationEntityId`/`RenderObjectId` may be attached as debug/correlation metadata, but ordered asynchronous commands do not use `RenderObjectId` as their lifetime key.

`AudioEmitterId` exact generation semantics are defined by architecture 060.

## 11. Device/HRTF reset

On device reset/reopen:

```text
stop API mutation
capture logical voice/stream state
reset/recreate device/context
recreate AL objects/buffers as needed
reapply listener/bus settings
recreate EFX objects
reassign physical voices
resume logical timelines
```

A device reset may cause an audible discontinuity.

It must not corrupt logical voice state.

## 12. Disconnect recovery

If `ALC_EXT_disconnect` indicates device loss:

```text
enter SilentDevice state
continue logical voice clocks
keep consuming commands/snapshots
periodically attempt output-device recovery
```

After successful reopen:

```text
rebuild OpenAL state
promote currently relevant logical voices
```

No canonical state waits for audio recovery.

## 13. Debug context

Development builds request/use OpenAL debug facilities when supported.

Label/diagnose:

```text
sources
buffers
effects
effect slots
filters
```

where OpenAL support permits.

OpenAL errors are checked at subsystem boundaries rather than after every individual hot-path call in release.

## Spatial-unit hardening

Architecture 051 owns spatial scale.

OpenAL listener/emitter coordinates use:

```text
meters = presentationUnits / 32
```

## Audio ID wrap authority

Architecture 065 owns the exact invalid/start/reuse/wrap rules for `AudioVoiceId` and `AudioEmitterId`.

Generation wrap retires the slot rather than aliasing a stale asynchronous command.

## Legacy queued-footstep start-spatialization compatibility

ADR-042 preserves the audited v1 behavior of queued movement-step `EV_SOUND` events without making the global OpenAL listener unstable.

Extend the discrete one-shot command with an optional compatibility record conceptually equivalent to:

```cpp
struct LegacyStepSpatializationRef {
    float sourceOriginPu[3];
    float closestFriendlyOriginPu[3];
    int32_t movementStep;
};
```

The exact in-memory packing may follow the command ABI, but the semantics are fixed:

```text
ordinary one-shot:
    spatialize against AudioStateSnapshot.listener

queued movement-step one-shot with closest friendly actor:
    source-start spatialization position reference = closest friendly actor
    orientation reference = normal tactical listener orientation
    next normal continuous update = ordinary tactical listener

queued movement-step one-shot without closest friendly actor:
    do not start the sample
```

Do not implement this by publishing a transient global listener snapshot or by issuing process-wide listener mutations around `alSourcePlay`; that would introduce ordering/race behavior absent from the single-threaded legacy call path.

