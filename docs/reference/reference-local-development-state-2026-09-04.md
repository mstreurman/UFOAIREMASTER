# Local Development State — 2026-09-04

**Historical status:** Superseded for current-state facts by `reference-current-development-machine-2026-09-04-104103.md`; retained unchanged as the earlier 2026-09-04 capture.  

**Status:** Observed workstation snapshot  
**Captured:** 2026-09-04T02:37:57+02:00  
**Purpose:** Separate the actually observed Fedora workstation/repository state from accepted design intent and from dependencies that are selected but not yet present.

## Interpretation rule

This file is an observation record, not a new architecture decision.

Use the following state classes when planning implementation work:

```text
CONFIRMED INSTALLED
    directly observed in the 2026-09-04 workstation snapshot

CONFIRMED IN REPOSITORY
    directly observed in the checked-out source tree/build tree

SELECTED / DOCUMENTED, NOT CONFIRMED PRESENT
    accepted by design, but no implementation/source/tool installation was found
    in this snapshot

NOT REVALIDATED BY THIS SNAPSHOT
    information retained elsewhere in the design baseline but not queried by
    the local-state capture command
```

Do not turn an accepted design dependency into an "installed" dependency without an observed local artifact.

## Operating system and kernel — CONFIRMED INSTALLED

```text
Fedora release 44 (Forty Four)
Linux kernel 7.1.8-200.fc44.x86_64
architecture x86_64
```

The snapshot did not directly query the active KDE/Wayland session. Fedora 44 KDE/Wayland remains the accepted reference desktop/session under ADR-008, but that session detail is **not revalidated by this particular capture**.

## CPU — CONFIRMED INSTALLED

```text
Intel Core i9-9900K @ 3.60 GHz
Coffee Lake Refresh family/model 6/158 stepping 12
8 physical cores
16 hardware threads
max frequency reported 5.0 GHz
16 MiB shared L3
2 MiB total L2
256 KiB total L1d
256 KiB total L1i
1 NUMA node
```

Observed relevant ISA facilities include:

```text
SSE / SSE2 / SSE3 / SSSE3 / SSE4.1 / SSE4.2
AVX / AVX2
FMA
F16C
BMI1 / BMI2
POPCNT
AES
PCLMULQDQ
ADX
RDRAND / RDSEED
FSGSBASE
CLFLUSHOPT
ERMS
INVPCID
```

No AVX-512 capability was reported. ADR-006 remains the normative CPU-optimization policy.

## GPU and Linux driver — CONFIRMED INSTALLED

```text
Intel Arc B580
Battlemage G21 / BMG G21
PCI vendor/device 8086:e20b
kernel driver in use: xe
```

The snapshot also sees a software `llvmpipe` Vulkan device. The Arc B580 is the intended hardware target and must be selected for renderer measurements.

## Vulkan/Mesa — CONFIRMED INSTALLED

```text
vulkaninfo: /usr/bin/vulkaninfo
Vulkan instance version: 1.4.341
Arc device API version: 1.4.354
Mesa driver version: 26.1.8
Vulkan driver: Intel open-source Mesa driver
Arc device type: discrete GPU
```

Installed Vulkan components observed in RPM inventory include:

```text
vulkan-headers 1.4.341.0
vulkan-loader / vulkan-loader-devel 1.4.341.0
vulkan-tools 1.4.341.0
vulkan-validation-layers 1.4.341.0
mesa-vulkan-drivers 26.1.8
```

The snapshot command used `vulkaninfo --summary`; therefore the detailed RT feature/property set is **not revalidated here**. The dedicated runtime capability record remains:

```text
reference/reference-arc-b580-vulkan-capabilities.md
```

## Compiler/build toolchain — CONFIRMED INSTALLED

```text
GCC/G++ 16.2.1
Clang/Clang++ 22.1.8
CMake 4.3.0
Ninja 1.13.2
Meson 1.11.2
Git 2.55.0
```

The local-state probe triggered Fedora's command-not-found/package flow for Meson; the final package inventory confirms Meson is installed at the end of the capture. Future diagnostics should avoid probes that can implicitly install packages.

## Shader/SPIR-V tooling — CONFIRMED INSTALLED

Observed tools/packages include:

```text
glslc / shaderc 2026.1
glslang 16.2.0
SPIRV-Tools 2026.1
spirv-llvm-translator 22.1.2
```

The local-state probe also triggered Fedora package installation for `glslang`; the final RPM inventory confirms it is installed.

### Slang implementation state

The architecture selects Slang and defines `.rshader`/shader-package contracts in architecture 029/056/061/070.

However, this snapshot did **not** show `slangc`, a Slang package, or a vendored Slang source tree.

Classify Slang as:

```text
SELECTED / DOCUMENTED, NOT CONFIRMED PRESENT
```

until a later workstation/source snapshot proves otherwise.

## Intel compute/developer tooling — CONFIRMED INSTALLED

Observed Intel packages include:

```text
intel-compute-runtime 26.22.38646.6
intel-level-zero 26.22.38646.6
intel-level-zero-devel 26.22.38646.6
intel-level-zero-gpu-raytracing 1.2.3
intel-igc 2.36.3
intel-ocloc 26.22.38646.6
intel-opencl 26.22.38646.6
Intel oneAPI DPC++/C++ 2026.1.x
Intel oneAPI debugger/developer utilities
Intel oneAPI TBB + TBB development package
```

These tools are available for profiling/experimentation where useful, but their presence does not override the Vulkan renderer architecture or benchmark-gated optimization policy.

## Audio stack — CONFIRMED INSTALLED

Observed packages include:

```text
openal-soft 1.24.2
openal-soft-devel 1.24.2
openal-soft-examples 1.24.2
```

This confirms that the accepted OpenAL Soft implementation has development headers/libraries available on the reference machine.

Detailed EFX/HRTF runtime capability observations remain recorded in `reference-development-platform.md` and were not re-probed by this snapshot.

## SDL stack — CONFIRMED INSTALLED

Observed packages include:

```text
SDL3 3.4.14
SDL3-devel 3.4.14
SDL3_image 3.4.4
SDL3_ttf 3.2.2
SDL2 compatibility 2.32.70
SDL2_mixer 2.8.1 + devel
SDL2_ttf 2.24.0 + devel
SDL 1.2 compatibility packages
```

At the time of this workstation snapshot, this confirmed only that SDL3 development files were available; the then-current ADR-008 had not yet selected it. Baseline 031 subsequently accepts SDL3 via ADR-033, as recorded below.

## Other observed development dependencies — CONFIRMED INSTALLED

The snapshot confirms development/runtime packages for at least:

```text
libcurl
libjpeg-turbo
libpng
SQLite
zlib-ng compatibility
Mesa OpenGL
```

Package presence is not, by itself, an architecture dependency declaration.

## Git/source state — CONFIRMED IN REPOSITORY

Observed repository state:

```text
branch: master
HEAD: 763173ed036ebbee32c2a7bf6aefa19748df89ff
origin:   https://github.com/mstreurman/UFOAIREMASTER.git
upstream: https://github.com/ufoaiorg/ufoai.git
submodules: none reported
```

Observed untracked paths:

```text
?? build-f44/
?? docs/
```

The documentation package therefore currently lives in an untracked `docs/` tree unless the developer intentionally adds/commits it.

## Existing build state — CONFIRMED IN REPOSITORY

The Fedora build directory already exists:

```text
build-f44/
```

Observed configured/generated build artifacts include:

```text
build-f44/build.ninja
build-f44/CMakeCache.txt
build-f44/CMakeFiles/
build-f44/ufo
build-f44/ufoded
build-f44/base/game.so
```

Therefore:

```text
legacy Fedora/CMake/Ninja build bring-up = already demonstrated locally
```

Do not describe the project as requiring its first successful Fedora build unless a later clean-build validation says otherwise.

This observation does not prove that the remaster architecture itself is implemented; it proves the current upstream-derived game checkout has an existing configured Fedora build that produced principal binaries.

## Jolt Physics implementation state

Jolt is accepted by ADR-007 and is referenced by the CPU-frame/VFX architecture.

The snapshot found:

```text
docs/adr/ADR-007-jolt-presentation-physics.md
docs/architecture/033-exact-cpu-frame-schedule-and-jolt-integration.md
docs/architecture/041-volumetrics-vfx-lights-ribbons-beams-and-jolt-debris.md
```

It did **not** expose:

```text
Jolt source checkout
Jolt vendor/third-party directory
Jolt git submodule
Jolt RPM/package
obvious Jolt build artifact
```

Therefore classify Jolt as:

```text
SELECTED / DOCUMENTED, NOT YET CONFIRMED DOWNLOADED OR INTEGRATED
```

This is an implementation-state statement only; it does not reopen ADR-007.

## Memory/session information not revalidated

The capture command did not query RAM/zram or the active desktop/session.

The existing reference-development-platform values for memory and KDE/Wayland remain prior recorded baseline information, but are **NOT REVALIDATED BY THIS SNAPSHOT**.

## Planning consequence

Before asking the developer to install or download a dependency, check this observation record first.

Current planning categories include:

```text
Already present:
    GCC / Clang / CMake / Ninja / Meson / Git
    Vulkan loader/headers/tools/validation
    Mesa Arc B580 Vulkan stack
    shaderc/glslc, glslang, SPIR-V Tools
    OpenAL Soft development stack
    SDL3 development stack
    Intel oneAPI / Level Zero / IGC / ocloc tooling
    common image/network/database/zlib development packages
    configured build-f44 with existing ufo/ufoded/game.so outputs

Selected but not confirmed present at snapshot time:
    Jolt implementation/source
    Slang compiler/source

Architecture state at snapshot time:
    SDL3 versus another Fedora/Wayland bootstrap/window/input layer was not yet decided
```

**Subsequent closure:** Baseline 031 / ADR-033 accepts SDL3 for the Fedora platform/window/input/text/IME and Vulkan-surface layer. This note does not alter the historical package snapshot; it only prevents the old observation from being mistaken for a current open decision.

## Provenance

Source: developer-supplied `ufoai-remaster-local-state.txt`, captured on the reference machine at `2026-09-04T02:37:57+02:00`.
