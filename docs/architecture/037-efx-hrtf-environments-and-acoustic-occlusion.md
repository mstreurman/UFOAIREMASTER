# EFX, HRTF, Environments and Acoustic Occlusion

**Status:** Implementation specification baseline  
**Related ADR:** ADR-024

## 1. EFX capability

Require on the reference target:

```text
ALC_EXT_EFX
```

Query:

```text
ALC_MAX_AUXILIARY_SENDS
```

Reference target:

```text
2 sends/source
```

Baseline runtime is designed explicitly around two sends.

## 2. EFX objects

Maintain pools for:

```text
Effects
AuxiliaryEffectSlots
Filters
```

Do not create/delete EFX objects per source update.

Starting active effect-slot budget:

```text
8 slots allocated
up to 4 expensive wet effects active in normal play
```

Exact CPU budget is benchmark-tunable.

## 3. Send ABI

Per physical source:

```text
Send 0:
    PrimaryEnvironment

Send 1:
    SecondaryEnvironment
```

Typical meaning:

```text
Primary:
    current room/zone reverb

Secondary:
    adjacent-room transition
    special local environment
    temporary crossfade
```

During a two-zone crossfade, both sends may be consumed by room environments.

## 4. Environment effects

Primary baseline effects:

```text
EAX Reverb when supported
Reverb fallback
```

Other confirmed OpenAL Soft EFX effects such as:

```text
chorus
echo
flanger
distortion
frequency shifter
pitch shifter
ring modulator
autowah
compressor
equalizer
```

are available for authored presentation effects but are not the default room model.

## 5. Acoustic environment asset data

Extend presentation `.rmap` semantics with acoustic data.

Conceptual chunks:

```text
ACOU:
    acoustic zones/volumes
    environment preset IDs
    room parameters

APRT:
    acoustic portals
    door/connection relationships
```

This data is presentation-only.

Architecture 085 fixes the reference-v1 persisted `ACOU` zone/BVH and `APRT` portal records. The semantic ownership defined here is unchanged.

## 6. Acoustic zone

Conceptual:

```cpp
struct AcousticZone {
    uint32_t zoneId;
    uint32_t environmentPresetId;

    Bounds bounds;

    float wetGain;
    float transitionDistance;
    uint32_t priority;
};
```

A listener may blend between nearby/overlapping zones.

## 7. Portals

Acoustic portals model:

```text
doors
open arches
windows
level connections
```

Portal openness is driven one-way by canonical/presentation events.

The acoustic portal graph never determines whether canonical movement/LOS is possible.

## 8. Environment selection

At each audio-state update:

```text
listener position
    ->
active acoustic zone(s)
    ->
primary/secondary EFX slots
```

Transition values are smoothed.

Do not switch reverb parameters instantaneously on ordinary zone boundaries.

## 9. Occlusion scene

Maintain a presentation-only CPU acoustic scene.

Sources:

```text
static `.rmap` acoustic/occluder geometry
dynamic door/breakable acoustic state from canonical events
```

Do not query Jolt as authoritative occlusion geometry.

The implementation may share immutable geometry data/build tooling with presentation map data, but its runtime query representation is CPU-side.

## 10. Occlusion query

Baseline source-to-listener query:

```text
one world-space acoustic visibility ray
```

Inputs:

```text
tactical acoustic listener position
source position
acoustic surface/portal state
```

Output:

```text
occlusion 0..1
obstruction/HF attenuation metadata
```

No screen-space audio occlusion.

## 11. Occlusion update rate

Do not ray-test every active voice every frame.

Starting policy:

```text
critical/near physical voices:
    up to 20 Hz

ordinary physical world voices:
    up to 10 Hz

virtual/inaudible voices:
    no regular occlusion query
```

Stagger queries across frames.

Exact query budget is CPU benchmark-tunable.

## 12. Occlusion filter

Use EFX low-pass filtering on the direct path.

Starting tuning range:

```text
unoccluded:
    direct gain 1.0
    HF gain 1.0

fully occluded:
    direct gain approximately 0.35
    HF gain approximately 0.15
```

Interpolate/smooth between values.

These are mix starting constants, not architectural invariants.

## 13. Reverb under occlusion

Occlusion does not simply mute the wet path.

A source behind geometry may retain or increase relative room contribution.

Use per-send filters/gains to shape:

```text
direct path
primary wet path
secondary wet path
```

independently.

## 14. HRTF modes

User-selectable audio setting:

```cpp
enum class HrtfMode {
    Auto,
    Off,
    On,
    NamedProfile
};
```

### Auto

Request:

```text
ALC_DONT_CARE_SOFT
```

and let OpenAL Soft/output conditions select behavior.

### Off

Request disabled HRTF.

### On

Request enabled HRTF.

### NamedProfile

Enumerate:

```text
ALC_NUM_HRTF_SPECIFIERS_SOFT
ALC_HRTF_SPECIFIER_SOFT
```

and request selected ID/profile where supported.

## 15. HRTF apply

Use:

```text
alcResetDeviceSOFT
```

when the extension permits runtime reconfiguration.

After reset query:

```text
ALC_HRTF_STATUS_SOFT
active HRTF specifier/name
output mode if available
```

UI/debug output reports actual state, not just requested state.

## 16. HRTF target use

HRTF is intended for headphone spatialization and remains explicitly user-selectable. The fact that the latest development-machine Bluetooth route reported HRTF disabled does not establish the game's default or force HRTF off.

World mono sources receive normal 3D spatialization.

Music/UI/non-positional stereo sources explicitly avoid world spatialization.

## 17. Tactical acoustic listener

Position:

```text
camera tactical focus/pivot
```

Orientation:

```text
forward:
    camera yaw projected onto horizontal tactical plane

up:
    world up
```

Velocity:

```text
zero
```

This decouples acoustic perspective from camera height and fast pan velocity.

## 18. Multiple tactical floors

World-space source height remains meaningful.

The listener orientation is horizontally stable, so sounds from upper/lower floors can retain vertical spatial cues under HRTF.

Cutaway visibility does not automatically silence a sound.

Audio audibility follows acoustic/world state, not whether geometry is currently rendered.

Specific UI/design rules may intentionally suppress sounds from hidden/non-relevant tactical content, but cutaway is not acoustic occlusion truth.

## 19. Air absorption

`AL_AIR_ABSORPTION_FACTOR` may be used per authored source class.

Do not enable aggressive global air absorption by default until map scale and mix are benchmarked.

## 20. Source cones

Directional sources may use:

```text
cone inner angle
cone outer angle
outer gain
AL_CONE_OUTER_GAINHF where supported
```

Examples:

```text
alarms/speakers
directed machinery
engines
```

Ordinary weapon impacts/footsteps remain omnidirectional unless authored otherwise.

## Baseline 031 acoustic-format closure

Architecture 085 is the exact reference-v1 serialization authority for `ACOU` zones/BVH and `APRT` portals. Future compact layouts require a new version.
