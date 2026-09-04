# Current Audio State — 2026-09-04 10:47:54+02:00

**Status:** Authoritative latest active-audio observation for this documentation baseline  
**Input archive:** `ufoai-audio-baseline-20260904-104754.tar.gz`  
**Archive SHA-256:** `ae67fe026c77c4566c64e15698128e72f82e0beb5384f58ac3f632f75f44452f`  
**Scope:** PipeWire/WirePlumber/BlueZ routing, OpenAL enumeration, active Bluetooth profile/codec, playback/capture defaults

## Audio software

```text
PipeWire     1.6.8
WirePlumber  0.5.14
BlueZ        5.87
Pulse compat 17.0
OpenAL Soft  1.24.2
```

`pipewire-codec-aptx` is installed (`1.6.7-1.fc44.x86_64`).

## Active playback route

At capture time the configured/default output was:

```text
LG-PK5(56)
backend: BlueZ/PipeWire
profile: A2DP Sink
active codec profile: aptX HD
sink sample specification: 24-bit stereo / 48 kHz
PipeWire volume: 0.83 (~ -4.96 dB)
connected: yes
```

The sink was suspended at the instant of capture, consistent with an idle PipeWire endpoint; the Bluetooth device itself remained connected and selected as default.

## Other local playback routes

```text
Sound Blaster AE-7 / CA0132 Analog Stereo
HD559 AE-7 Parametric EQ PipeWire filter sink
```

The AE-7 remains physical installed hardware, but it was not the active default playback route in this snapshot.

## OpenAL view

OpenAL Soft enumerated:

```text
LG-PK5(56)
HD559 AE-7 Parametric EQ
Sound Blaster AE-7 Analog Stereo
```

and reported `ALC_ENUMERATE_ALL_EXT`, `ALC_SOFT_HRTF`, `ALC_SOFT_reopen_device` and other OpenAL Soft device-management capabilities. Current state:

```text
default playback device = LG-PK5(56)
HRTF capability = available
HRTF profiles = Default HRTF, Built-In HRTF
actual HRTF state on LG-PK5(56) = disabled
```

This proves that OpenAL Soft follows/selects PipeWire endpoints on the development platform. It does **not** establish LG-PK5 or HRTF-off as engine defaults.

## Capture source

Default capture input at this instant:

```text
C920 PRO HD Webcam Analog Stereo
```

The remaster currently specifies playback/spatial-audio architecture; capture-device policy is not made gameplay-authoritative by this observation.

## Architecture consequence

Production audio settings must expose a system-default/named OpenAL device selector and independent HRTF selection. Current Bluetooth/AE-7 routing is a local test fixture only. See ADR-046 and architecture 035/037/090.
