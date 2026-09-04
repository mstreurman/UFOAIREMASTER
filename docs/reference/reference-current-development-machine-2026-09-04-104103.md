# Current Development Machine — 2026-09-04 10:41:03+02:00

**Status:** Authoritative latest broad workstation observation for this documentation baseline  
**Input archive:** `ufoai-machine-baseline-20260904-104103.tar.gz`  
**Archive SHA-256:** `548682081cbf1a4deb98c07060e5041d52f0f5ed4f5ac469f786e57387a3b85c`  
**Scope:** local hardware, OS/session, toolchain, installed RPMs, display state, graphics driver layout, repository/build state

## Authority rule

For facts re-probed by this snapshot, this document supersedes the older `reference-local-development-state-2026-09-04.md`. The older file remains historical evidence and is not rewritten.

The later dedicated audio snapshot `reference-current-audio-state-2026-09-04-104754.md` is newer and therefore authoritative for active audio routing/device/profile state.

## OS/session

```text
Fedora Linux 44 (KDE Plasma Desktop Edition)
kernel 7.1.12-200.fc44.x86_64
XDG session = Wayland
KDE Plasma 6.7.4
KWin 6.7.4
```

## Board/CPU/memory

```text
board: ASRock Z390 Extreme4
BIOS: American Megatrends P4.30F, 2022-09-06
CPU: Intel Core i9-9900K, 8C/16T, max reported 5.0 GHz
RAM: approximately 31 GiB usable
zram swap: 8 GiB, lzo-rle
```

Observed CPU capabilities continue to include AVX2/FMA/F16C/BMI1/BMI2/AES/PCLMUL/ADX-class facilities and no AVX-512.

## GPU/Vulkan/Mesa

```text
GPU: Intel Arc B580 / BMG G21 [8086:e20b]
kernel driver: xe
Vulkan device API: 1.4.354
Mesa driverInfo: Mesa 26.2.2
conformance: 1.4.0.0
```

The locally built Mesa stack is installed as `26.2.2-0.1.local.fc44` RPMs, including `mesa-vulkan-drivers` for x86_64/i686.

The active Intel Vulkan driver file is RPM-owned rather than selected through an environment override. The snapshot reports:

```text
VK_DRIVER_FILES=unset
VK_ICD_FILENAMES=unset
LD_LIBRARY_PATH=unset
/usr/lib64/libvulkan_intel.so
owner: mesa-vulkan-drivers-26.2.2-0.1.local.fc44.x86_64
SHA-256: bcce8446d98b01a0dd2d970d3908552821f500571f05208fd0efa82a2c8966e6
```

The complete device capability details remain in `reference-local-vulkan-state-2026-09-04-mesa-26_2_2.md` and `reference-arc-b580-vulkan-capabilities.md`.

## Current displays at capture time

KDE reported two enabled displays. These are **runtime state, not hardcoded engine targets**.

### HDMI-A-3

```text
selected mode: 1920x1080 @ 60.00 Hz
HDR: incapable
wide color gamut: incapable
color resolution: 8 bpc active, device range reported 8..12 bpc
KDE scale: 0.75
ICC: ${HOME}/Documents/2270W.icm
```

### DP-2, priority 1 / primary

```text
selected mode: 3840x2160 @ 60.00 Hz
HDR: enabled
wide color gamut: enabled
color resolution: 10 bpc active, device range reported 6..12 bpc
reported peak brightness: 644 nits
current KDE peak override: 370 nits
max average brightness: 400 nits
min brightness: 0.0524 nits
HDR profile source: EDID
KDE scale: 1.5
ICC: ${HOME}/Documents/326M6V.icm
```

The primary monitor also enumerates 1920x1080@60 among its supported modes. The project performance target remains a 1920x1080/60/DisplayHDR-600-class qualification profile, not the captured 4K desktop configuration.

## Toolchain

```text
GCC/G++       16.2.1
Clang/Clang++ 22.1.8
CMake         4.3.0
Ninja         1.13.2
Meson         1.11.2
Make          4.4.1
Git           2.55.0
Python        3.14.7
pkg-config    2.5.1
ccache        4.12.3
```

`gcc`, `g++`, `clang`, and `clang++` resolve through `/usr/lib64/ccache/` in this capture. Reproducible benchmark manifests therefore record ccache state rather than assuming direct compiler executable paths.

## Shader tooling

```text
glslc/shaderc       2026.1
glslangValidator    16.2.0
SPIR-V Tools        2026.1
slangc               NOT PRESENT
```

Slang v2026.17 is now the selected/pinned project tool under Baseline 039. This capture predates that pin update and proves only the local installation fact: shader-compiler `slangc` was not present in `PATH` at capture time.

The RPM inventory contains `slang-2.3.3-9.fc44.x86_64`; that package is the unrelated **S-Lang terminal/programming library**, not the `shader-slang/slang` shader compiler and does not satisfy the project Slang dependency.

## SDL / OpenAL / FFmpeg

```text
SDL3              3.4.14
SDL3-devel        3.4.14
OpenAL Soft       1.24.2
OpenAL Soft devel 1.24.2
FFmpeg            8.1.2
ffmpeg-libs       8.1.2
```

The capture did not report `pkg-config` modules for `libavcodec`, `libavformat`, `libavutil`, `libswresample`, or `libswscale`. Treat FFmpeg development headers/libraries as **not yet proven provisioned** even though FFmpeg runtime/libraries are installed.

## Intel developer/compute stack

Observed packages continue to include:

```text
intel-compute-runtime 26.22.38646.6
intel-level-zero 26.22.38646.6
intel-level-zero-gpu-raytracing 1.2.3
intel-igc 2.36.3
intel-ocloc 26.22.38646.6
Intel oneAPI DPC++/C++ 2026.1.1
```

Their presence does not replace the Vulkan renderer architecture.

## Source/build state

```text
repository: ~/Projects/ufoai-remaster/upstream-ufoai
branch: master...upstream/master
HEAD: 763173ed036ebbee32c2a7bf6aefa19748df89ff
origin:   https://github.com/mstreurman/UFOAIREMASTER.git
upstream: https://github.com/ufoaiorg/ufoai.git
untracked: build-f44/, docs/
```

Existing build artifacts remain present:

```text
build-f44/ufo
build-f44/ufoded
build-f44/base/game.so
CMAKE_BUILD_TYPE=RelWithDebInfo
generator=Ninja
```

## Jolt/Slang provision state

```text
Jolt vendor/source tree: not present
slangc: not present in PATH
```

This is intentional current state; architecture selection does not imply local installation.
