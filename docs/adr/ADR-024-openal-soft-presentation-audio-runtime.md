# ADR-024 — OpenAL Soft Presentation Audio Runtime

**Status:** Accepted  
**Decision type:** Presentation audio architecture  
**Primary platform:** Fedora 44 / OpenAL Soft  
**Reference audio environment:** PipeWire/WirePlumber with runtime-selectable OpenAL playback device  
**Related:** ADR-001, ADR-007, ADR-023

## Context

Audio is part of the remaster presentation layer.

It may represent:

```text
weapon fire
impacts
movement
UI
dialogue
ambient sound
music
environmental acoustics
presentation-only physics/debris
```

but it has no authority over canonical gameplay.

The reference Fedora 44 system has confirmed:

```text
OpenAL Soft 1.24.x
48 kHz
ALC_EXT_EFX
ALC_SOFT_HRTF
2 auxiliary sends/source
EAX Reverb / Reverb and other EFX effects
low/high/band-pass filters
```

HRTF support exists on the reference OpenAL Soft runtime, but whether it is active is a user/runtime choice. The fresh 10:47:54+02:00 audio snapshot happened to use the Bluetooth `LG-PK5(56)` route with HRTF disabled; that observation is not a default-device or default-HRTF requirement.

## Decision

Use OpenAL Soft as the production audio runtime.

Use:

```text
3D positional mono sources
EFX environmental effects
HRTF when enabled/available
source virtualization
logical bus gains
streamed music/long ambience
presentation-only acoustic occlusion
```

All OpenAL API calls are owned by one dedicated engine AudioControl thread.

OpenAL Soft's internal backend/mixer threads remain library-owned.

## Thread ownership

The scheduler baseline is refined:

```text
Main physical core:
    Main thread

Render physical core:
    Render thread

6 worker physical cores:
    PrimaryWorker[0..5]

5 worker SMT siblings:
    SmtWorker[0..4]

1 worker SMT sibling:
    AudioControl
```

Main/Render SMT siblings remain unused by the engine.

The exact worker core whose sibling hosts AudioControl is benchmark-selectable.

AudioControl uses:

```text
SCHED_OTHER
fixed CPU affinity
```

and normally sleeps between work.

## OpenAL context ownership

AudioControl:

```text
opens ALC device
creates ALC context
makes context current
owns all AL/ALC object mutation
destroys context/device
```

Main, Render and job workers never call OpenAL directly.

## Audio data flow

Use two one-way channels from game/presentation code:

```text
AudioStateSnapshot
    continuous/latest state

AudioCommandQueue
    ordered discrete events
```

Continuous state may be replaced by a newer snapshot.

Discrete commands are never silently lost merely because a newer snapshot exists.

## Physical/logical voices

Baseline:

```text
512 logical voices
96 physical OpenAL sources
```

Logical voices preserve timing/state even when virtual.

Physical source assignment is recalculated deterministically from audibility/priority.

These counts are benchmark constants, not gameplay semantics.

## HRTF

Expose user modes:

```text
Auto
Off
On
NamedProfile
```

Use `ALC_SOFT_HRTF` and device reset where supported.

After every HRTF/device reset, query actual HRTF status.

Never assume requested HRTF mode became active.

## Playback-device selection

The runtime must expose:

```text
SystemDefault
NamedOpenALDevice
```

The selected named device is opened explicitly when available. `SystemDefault` follows the platform/OpenAL default route. Device selection is independent of the physical PCI audio hardware installed in the development workstation.

If a named device disappears, audio may temporarily fall back to the current system default while retaining the user's preferred named device for later recovery. Requested and actual devices are both surfaced in settings/diagnostics. Architecture 035/090 owns reopen/failover details.

## EFX

Require two auxiliary sends on the reference target.

Baseline send meaning:

```text
Send 0:
    primary environmental room/reverb

Send 1:
    secondary transition/local/special environment
```

Direct filters provide occlusion/obstruction shaping.

OpenAL EFX does not define canonical gameplay acoustics.

## Tactical listener

The tactical listener is not the camera eye.

Baseline:

```text
position:
    tactical camera focus/pivot world position

forward:
    camera yaw direction projected to tactical horizontal plane

up:
    presentation world up

velocity:
    zero
```

This avoids exaggerated attenuation and Doppler caused by the elevated/rapidly moving tactical camera.

### Legacy queued-footstep compatibility exception

ADR-042 is the sole v1 exception to ordinary listener-position semantics. A queued movement-step `EV_SOUND` initially evaluates spatialization against the closest friendly actor origin, matching the audited legacy client behavior.

This **does not move the global OpenAL listener**. The exception is carried as per-event compatibility data and applies to the source-start spatialization update only; a surviving voice returns to ordinary continuous spatialization on the next normal audio update. If the legacy closest-friendly lookup produces no actor, no step sample is started, matching the source behavior.

## Doppler

Baseline:

```text
global Doppler disabled
```

The tactical camera is not a physical listener moving through the game world.

Individual authored pitch effects remain possible.

## Acoustic visibility

Audio occlusion is presentation-only.

It uses a dedicated read-only acoustic scene derived from presentation/map data.

Do not use Jolt contacts as acoustic authority.

Do not feed acoustic results into:

```text
AI
LOS
damage
cover
canonical visibility
```

## Consequences

- all OpenAL calls are serialized and easy to debug;
- audio does not stall Main on ordinary API work;
- HRTF is configurable without being falsely assumed active;
- limited EFX sends are used intentionally;
- tactical camera movement does not create artificial Doppler;
- audio virtualization prevents source count from becoming content authority.
