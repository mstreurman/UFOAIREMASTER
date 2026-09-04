# Reference Development Platform

**Status:** Recorded baseline, locally revalidated 2026-09-04  
**Purpose:** Capture the machine and software stack against which the remaster architecture is designed and validated. Exact observed installation/repository state is separated into the dated local-state record.

## Current local-state provenance

The latest broad developer-supplied workstation/source snapshot is:

```text
reference/reference-current-development-machine-2026-09-04-104103.md
```

The latest dedicated audio-routing snapshot is:

```text
reference/reference-current-audio-state-2026-09-04-104754.md
```

The latest build-environment provisioning/readiness verification is:

```text
reference/reference-current-build-environment-readiness-2026-09-04-120248.md
```

The Mesa 26.2.2 Vulkan-detail record is:

```text
reference/reference-local-vulkan-state-2026-09-04-mesa-26_2_2.md
```

The older `reference-local-development-state-2026-09-04.md` remains historical. Use the newest source that actually re-probed a subsystem; do not merge stale values forward as though they were re-observed.

## Operating system

- Fedora Linux 44
- KDE Plasma Desktop Edition
- Wayland session
- Linux kernel: 7.1.12-200.fc44.x86_64

## CPU

- Intel Core i9-9900K
- 8 physical cores
- 16 hardware threads
- x86_64
- up to 5.0 GHz reported maximum frequency
- AVX2-capable

## Memory

- approximately 31 GiB system RAM
- 8 GiB zram swap

## Primary GPU

- Intel Arc B580
- Battlemage BMG-G21
- kernel driver: `xe`
- approximately 12 GiB dedicated video memory reported by Mesa

## Graphics software

Current Vulkan runtime observation:

- Mesa 26.2.2
- Vulkan instance version reported: 1.4.341
- Arc device API version reported: 1.4.354
- Intel open-source Mesa Vulkan driver
- `VK_EXT_descriptor_heap` revision 1 on the Arc B580
- `descriptorHeap = true`
- `descriptorHeapCaptureReplay = true`

The earlier broad workstation snapshot recorded Mesa 26.1.8. That remains a historical observation, not the current Vulkan driver state.

## Validated RT extensions/features

Extensions observed:

- `VK_KHR_acceleration_structure`
- `VK_KHR_ray_tracing_pipeline`
- `VK_KHR_ray_query`

Features observed:

- `accelerationStructure = true`
- `rayTracingPipeline = true`
- `rayQuery = true`

## Arc B580 RT properties observed

- shader group handle size: 32 bytes
- shader group handle alignment: 16 bytes
- shader group base alignment: 16 bytes
- max hit attribute size: 32 bytes
- max ray recursion depth: 31
- max ray dispatch invocation count: 1,073,741,824
- max geometry count: 16,777,215
- max instance count: 16,777,215
- max primitive count: 536,870,911
- acceleration-structure scratch offset alignment: 64 bytes
- default subgroup size: 32
- minimum subgroup size: 16
- maximum subgroup size: 32

`vulkaninfo` also exposed a software llvmpipe Vulkan device. Values recorded above are the hardware Arc B580 values.

## Audio

The latest audio capture observes PipeWire 1.6.8 / WirePlumber 0.5.14 / BlueZ 5.87 with `LG-PK5(56)` selected as the current system/default playback route over A2DP/aptX HD at 48 kHz. The physical Sound Blaster AE-7 and an AE-7 EQ filter sink remain available. This routing is runtime state, not a hardcoded project default.

OpenAL information observed:

- OpenAL renderer: OpenAL Soft
- OpenAL Soft version: 1.24.2
- EFX version: 1.0
- maximum auxiliary sends: 2
- HRTF capability exposed
- supported filters include low-pass, high-pass, and band-pass
- supported effects include EAX Reverb, Reverb, Chorus, Distortion, Echo, Flanger, Frequency Shifter, Vocal Morpher, Pitch Shifter, Ring Modulator, Autowah, Compressor, Equalizer, Dedicated Dialog, and Dedicated LFE

## Toolchain

Confirmed by the 2026-09-04 snapshot:

- GCC/G++ 16.2.1;
- Clang/Clang++ 22.1.8;
- CMake 4.3.0;
- Ninja 1.13.2;
- Meson 1.11.2;
- Git 2.55.0;
- shaderc/glslc 2026.1;
- glslang 16.2.0;
- SPIR-V Tools 2026.1.

The same snapshot confirms Vulkan development/validation packages, OpenAL Soft development files, SDL3 development files, and a substantial Intel oneAPI/Level Zero/IGC/ocloc tool stack.

The 10:41 broad snapshot correctly recorded Slang, FFmpeg-development and Jolt state before provisioning. The later 12:02:48 build-environment readiness run supersedes the Slang/FFmpeg installation-state fields: the exact hash-pinned Slang v2026.17 artifact is provisioned at `tools/slang/v2026.17/`, and matching `ffmpeg-devel-8.1.2-3.fc44.x86_64` is installed with all required libav `pkg-config` modules. The subsequent 12:15 Jolt provisioning run supersedes the Jolt-absence field: v5.6.0 commit `e77f175595e64cb44218cc9d9d56fc365ad0e36a` is now vendored at `third_party/JoltPhysics/`, builds as `build-jolt-f44/libJolt.a`, and passes upstream HelloWorld/UnitTests. Production stress qualification remains pending.

## SDL compatibility baseline

Observed pkg-config versions:

- SDL2 API: 2.32.70
- SDL2_mixer: 2.8.1
- SDL2_ttf: 2.24.0

On Fedora 44, the SDL2 API may be provided through the SDL2 compatibility layer over the current SDL stack.

## CPU optimization role

The Intel Core i9-9900K is not merely a reference CPU. It is the primary CPU optimization target.

The remaster may use i9-9900K/Coffee Lake-specific instructions, SIMD, cache-aware layouts, threading strategies, and hand-tuned kernels where benchmarking shows a material benefit.

The primary local optimized build may use `-march=native -mtune=native` on this reference machine.

Global `-ffast-math` is prohibited because canonical gameplay behavior must not be changed by unsafe floating-point transformations.

## Platform role

Fedora Linux 44 is now the explicitly accepted primary and specifically supported platform for the remaster.

KDE Plasma/Wayland is the reference desktop/session environment.

Cross-platform parity with Windows or macOS is not a current architectural requirement.

## Physics runtime role

Jolt Physics is the accepted presentation-only physics runtime.

It is intended to be built and profiled specifically for the i9-9900K reference CPU and integrated through the Presentation World boundary.

The earlier 2026-09-04 local-state snapshot found no Jolt source. That observation is now superseded for current state by `reference-current-jolt-provisioning-2026-09-04-121547.md`: Jolt v5.6.0 is vendored at the accepted commit, has the recorded BLAKE3 vendor identity, builds successfully as a static library with the reference i9-9900K options, and passes upstream HelloWorld/UnitTests. Remaster integration and architecture-082 production stress qualification remain pending.

## Mesa 26.2.2 upgrade runtime-confirmed

The post-upgrade `vulkaninfo` capture now confirms the Arc B580 is loaded through Mesa 26.2.2 / Intel open-source Mesa Vulkan with device API 1.4.354.

The same B580 section confirms `VK_EXT_descriptor_heap`, both descriptor-heap feature booleans, and the full heap size/alignment/descriptor-size property block. See `reference-local-vulkan-state-2026-09-04-mesa-26_2_2.md` and `reference-arc-b580-vulkan-capabilities.md`.

A device-scoped correction was also required: the B580 does **not** advertise `VK_EXT_memory_priority` or `VK_EXT_pageable_device_local_memory` in this capture. Those capabilities appear under the separate llvmpipe device. Current allocator requirements therefore use `VK_EXT_memory_budget` plus explicit project-owned residency/eviction policy instead of assuming driver pageable-local-memory support.

## Purpose of this reference platform

This machine is the initial development, optimization and performance-qualification reference for:

- Arc B580 / Xe2 RT architecture decisions and target-specific fast paths;
- i9-9900K AVX2/FMA/cache/topology optimization;
- Vulkan 1.4 renderer bring-up;
- 1920x1080 / 60 Hz / near-60-FPS performance work;
- DisplayHDR 600-class presentation qualification;
- OpenAL Soft + EFX/HRTF integration;
- presentation-physics integration.

It is **not** a statement of minimum requirements or a source of hardcoded runtime display/audio settings. Resolution, refresh, display, HDR, playback device and HRTF are selectable according to ADR-046/architecture 090.

## Arc B580 microarchitecture reference

Static B580/Xe2 hardware facts used to motivate renderer benchmarks are recorded in:

```text
reference/reference-arc-b580-xe2-microarchitecture.md
```

Runtime Vulkan facts remain in:

```text
reference/reference-arc-b580-vulkan-capabilities.md
```

Project-measured performance remains a separate benchmark artifact class.


## Existing local checkout/build state

The 2026-09-04 snapshot records the remaster checkout on branch `master` at:

```text
763173ed036ebbee32c2a7bf6aefa19748df89ff
```

with `origin` pointing to the remaster fork and `upstream` to `ufoaiorg/ufoai`.

A configured `build-f44/` tree already exists and contains `ufo`, `ufoded`, and `base/game.so`. The legacy Fedora CMake/Ninja build therefore has already produced principal binaries on the reference workstation. This is distinct from implementation of the remaster architecture.
