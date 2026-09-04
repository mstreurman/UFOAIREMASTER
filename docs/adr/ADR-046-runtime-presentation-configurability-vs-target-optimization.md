# ADR-046 — Runtime Presentation Configurability Is Separate from B580/i9-9900K Optimization

**Status:** Accepted  
**Decision type:** Runtime configuration / performance-target boundary  
**Primary target:** Intel Arc B580 + Intel Core i9-9900K  
**Related:** ADR-002, ADR-006, ADR-018, ADR-024, ADR-026, ADR-032, ADR-033, architecture 035/037/072/073/081/090

## Context

The development workstation is intentionally the primary optimization and qualification machine. Its current display/audio choices, however, are transient user configuration rather than engine requirements.

For example, the fresh 2026-09-04 captures observe:

```text
Arc B580 + i9-9900K
primary HDR-capable 3840x2160@60 display currently in HDR/WCG mode
second SDR display
Bluetooth LG-PK5(56) currently selected for playback via A2DP/aptX HD
Sound Blaster AE-7 also available
OpenAL HRTF capability available, actual HRTF disabled at capture time
```

Hardcoding those transient choices would confuse **performance target** with **runtime configuration**.

## Decision

The renderer/audio engine is optimized first and most aggressively for the Arc B580 + i9-9900K reference machine, including target-specific Vulkan, RT, shader, SIMD, cache, threading and scheduling work.

Separately, the player must be able to select supported presentation configuration at runtime.

Required display controls:

```text
output display/monitor
windowed / borderless-fullscreen / fullscreen-mode request
output resolution
refresh rate where the platform exposes selectable modes
HDR Off / On / Auto
render resolution mode: NativeOutput or Explicit internal resolution
```

Required audio controls:

```text
SystemDefault or named OpenAL playback device
HRTF Auto / Off / On / NamedProfile
```

Requested and actual state are tracked separately. Unsupported or asynchronously rejected display/audio requests must not be misreported as active.

## Performance qualification profile

The mandatory primary performance profile remains:

```text
CPU              Intel Core i9-9900K
GPU              Intel Arc B580 / Xe2
RenderExtent     1920x1080
target refresh   60 Hz
target frame rate sustained close to 60 FPS
frame reference  16.667 ms
HDR quality      DisplayHDR 600-class when HDR is enabled
```

This profile is a benchmark/acceptance target, not the only legal runtime mode. Higher resolutions, different refresh rates, SDR, other displays, other OpenAL endpoints and HRTF choices remain supported runtime configurations but are not required to hit the same 1080p60 number.

## Hardware-specific optimization policy

Target-specific fast paths are allowed and preferred when they materially improve the B580/i9-9900K qualification workload. This includes:

```text
B580-specific Vulkan/RT scheduling and shader specialization
VK_EXT_descriptor_heap-first binding
Xe2 subgroup/work-group tuning
B580 memory/residency tuning
i9-9900K AVX2/FMA kernels
cache/topology-aware job placement
CPU/GPU pipeline decisions selected by target-machine benchmarks
```

Runtime configurability does not require a lowest-common-denominator implementation.

## Non-hardcoding rule

The following development-machine observations are never compiled into production defaults/requirements merely because they were observed locally:

```text
current KDE display ID or connector
current 4K desktop mode/scaling
current HDR toggle/brightness override
LG-PK5(56) Bluetooth endpoint
AE-7 endpoint
current HRTF disabled state
current PipeWire default route
```

They are test fixtures/capability evidence only.

## Consequences

- the renderer can be fully tuned around B580/i9-9900K without freezing user settings;
- benchmark reports have an unambiguous 1080p60/HDR600 qualification profile;
- display/audio settings report requested and actual state separately;
- development-machine observations remain references rather than hidden runtime contracts.
