# Third-Party Toolchain / Dependency Manifest

**Status:** Accepted reproducibility baseline  
**Platform:** Fedora 44 x86_64  
**Current workstation evidence:** 2026-09-04T10:41:03+02:00 broad machine capture; 2026-09-04T10:47:54+02:00 audio capture; 2026-09-04T12:02:48+02:00 build-environment readiness run  
**Current dependency audit:** Baseline 040

## 1. Policy

This manifest distinguishes three states that must never be conflated:

```text
accepted project dependency identity
observed local installation state
implementation/qualification state
```

A dependency may be accepted and reproducible without already being installed/downloaded locally. Conversely, an RPM with a similar name does not satisfy a project dependency unless it provides the required implementation/API.

## 2. Slang shader compiler

```text
name: shader-slang / Slang
role: build-time/offline shader compiler + reflection
runtime game dependency: no
accepted release: v2026.17
accepted release commit: 5bcb1c031b7873444f745b757a35e25567bbe043
accepted artifact: slang-2026.17-linux-x86_64-glibc-2.28.tar.gz
artifact SHA-256: a5a48530e7218d79e10b633c216ef04cbe778450b8c0a7579125e630c088ca75
source/release: https://github.com/shader-slang/slang/releases/tag/v2026.17
repository-local tool-cache location: tools/slang/v2026.17/ (local-only; ignored by repository policy and not committed)
source-build fallback: same v2026.17 source release only
license: Apache-2.0 WITH LLVM-exception
patch list: none at Baseline 041
```

The v2026.17 release was published on 2026-09-04 and reports no breaking changes. It contains the descriptor-heap compiler facilities required by architectures 029/056/087/089, including `spvDescriptorHeapEXT`, direct resource/sampler heap syntax and unified image/buffer heap stride support.

Bootstrap behavior:

```text
1. use an already verified local cache if present
2. otherwise the explicit bootstrap step downloads the accepted artifact
3. verify SHA-256 before extraction/use
4. record slangc and compiler-library identity in the build manifest
5. never require Slang shared libraries in the shipped game runtime
```

Current workstation state after explicit provisioning:

```text
project tool cache: tools/slang/v2026.17/
slangc: tools/slang/v2026.17/bin/slangc
reported version: 2026.17
artifact SHA-256: VERIFIED
DescriptorHeapEXT compile smoke: PASS
spirv-val Vulkan 1.4 smoke: PASS
```

The earlier 10:41 broad capture predates provisioning and remains historically correct for that timestamp.

The installed RPM `slang-2.3.3-9.fc44.x86_64` is the unrelated **S-Lang terminal/programming library**. It is not `shader-slang/slang`, does not provide `slangc`, and does not satisfy this dependency.

## 3. Jolt Physics

```text
name: Jolt Physics
role: CPU-side presentation-only physics
runtime linkage: static into project binary/library
canonical gameplay authority: none
accepted release: v5.6.0
accepted commit: e77f175595e64cb44218cc9d9d56fc365ad0e36a
license: MIT
source: https://github.com/jrouwe/JoltPhysics
vendor location: third_party/JoltPhysics/
vendor method: immutable source snapshot of accepted commit; no git submodule
patch list: none at Baseline 041
```

The vendor snapshot carries `third_party/JoltPhysics/UFOAI_VENDOR_MANIFEST.txt` with:

```text
upstream URL
release tag
commit SHA
license identifier
sorted-file-manifest BLAKE3-256
local patch list
```

The sorted-file-manifest hash is BLAKE3-256 over each non-manifest regular file in bytewise UTF-8 path order, feeding `path`, one NUL byte, the unsigned decimal file length, one NUL byte, the exact file bytes, then one NUL byte. This makes the project identity independent of GitHub tarball compression metadata.

Reference CMake switches are fixed by architecture 082. Jolt DX12/Vulkan/Metal/CPU-compute interfaces are disabled because this project uses Jolt only for CPU presentation rigid-body/ragdoll simulation.

Current reference-workstation state after the 2026-09-04 12:15 provisioning run:

```text
Jolt source/vendor tree: PRESENT at third_party/JoltPhysics/
Jolt release:            v5.6.0
Jolt commit:             e77f175595e64cb44218cc9d9d56fc365ad0e36a
Jolt vendor BLAKE3-256:  ffe175b315e20631eea26419b65ef225b73e37e3788dd93b66407fb3f37a9df2
local patches:           none
standalone build:        build-jolt-f44/libJolt.a PRESENT
upstream HelloWorld:     PASS
upstream UnitTests:      PASS (1/1)
production qualification: PENDING architecture-082 stress gate
```

The earlier broad machine snapshots that reported Jolt absent remain historical evidence for their timestamps and do not override this later provisioning record.

Qualification caveat: Jolt 5.6.0 remains the current accepted development pin and current upstream release at the Baseline-039 audit. Architecture 082 still requires the finite-transform sleep/wake stress test before production qualification. Upstream issue #2092 reported non-finite transforms around sleep transitions on this same v5.6.0 commit and a passing comparison on v5.5.0; the issue is closed/completed, so it remains a qualification signal rather than proof that the project workload is affected. If the reference test reproduces the failure, v5.5.0 commit `23dadd0e603f1b321142d4c74df07fce85064989` is the authorized fallback candidate subject to the same vendor manifest and qualification process.

## 4. FFmpeg / libav

Project role:

```text
name: FFmpeg libraries
role: cinematic demux/decode/resample/optional pixel conversion
required APIs: libavformat, libavcodec, libavutil, libswresample; libswscale when needed
runtime linkage: matching system shared libraries on Fedora
```

Fresh workstation RPM evidence:

```text
ffmpeg-8.1.2-3.fc44.x86_64
ffmpeg-libs-8.1.2-3.fc44.x86_64
libavdevice-8.1.2-3.fc44.x86_64
```

The 10:41 broad capture did **not** expose the libav development `pkg-config` modules; that observation remains historical for the pre-provisioning state. The later readiness run supersedes it for current installation state.

Current state:

```text
FFmpeg runtime: PRESENT
FFmpeg development headers/pkg-config metadata: PROVISIONED / VERIFIED
cinematic backend compile dependency readiness: READY
```

The later explicit provisioning run installed matching Fedora 44 RPM Fusion `ffmpeg-devel-8.1.2-3.fc44.x86_64`, matching the installed `ffmpeg`/`ffmpeg-libs` 8.1.2-3.fc44 family. The readiness smoke verifies `pkg-config` modules `libavcodec 62.28.102`, `libavformat 62.12.102`, `libavutil 60.26.102`, `libswresample 6.3.102`, and `libswscale 9.5.102`.

Fedora and third-party repositories can provide different FFmpeg package families. M0 must select **one coherent runtime/development package family** and let DNF resolve the transaction; do not mix a `-free` development package with incompatible runtime libraries merely because the API version number looks similar. After provisioning, record exact NEVRA values and require all needed libav `pkg-config` modules to resolve before enabling the cinematic backend build.

Dependency installation alone is not sufficient for decoder retirement: architecture 083 still requires a shipped-cinematic corpus test before legacy decoders can be removed.

## 5. SDL3 / OpenAL / Vulkan

Fresh workstation evidence confirms:

```text
SDL3-3.4.14-1.fc44.x86_64
SDL3-devel-3.4.14-1.fc44.x86_64
openal-soft-1.24.2-6.fc44.x86_64
openal-soft-devel-1.24.2-6.fc44.x86_64
vulkan-headers-1.4.341.0-1.fc44.noarch
vulkan-loader-1.4.341.0-1.fc44.x86_64
vulkan-loader-devel-1.4.341.0-1.fc44.x86_64
vulkan-tools-1.4.341.0-1.fc44.x86_64
vulkan-validation-layers-1.4.341.0-2.fc44.x86_64
```

The current Arc B580 driver is supplied by locally built Mesa 26.2.2 RPMs, including:

```text
mesa-vulkan-drivers-26.2.2-0.1.local.fc44.x86_64
```

The current Vulkan capture proves the B580 device API is Vulkan 1.4.354 and exposes the descriptor-heap/RT feature set required by the renderer architecture. Runtime display/audio endpoint selection remains user-configurable; the captured display and Bluetooth routes are qualification evidence, not hardcoded defaults.

## 6. Reference workstation toolchain

Fresh snapshot includes:

```text
GCC 16.2.1
Clang 22.1.8
CMake 4.3.0
Ninja 1.13.2
Meson 1.11.2
Git 2.55.0
Python 3.14.7
pkg-config 2.5.1
ccache 4.12.3
shaderc/glslc 2026.1
glslang 16.2.0
SPIR-V Tools 2026.1
OpenAL Soft 1.24.2 + devel
SDL3 3.4.14 + devel
Intel oneAPI / Level Zero / IGC / ocloc stack
```

The compiler commands resolve through `/usr/lib64/ccache/` in the fresh capture. Reproducible benchmark manifests record both the real compiler identity and ccache enabled/disabled state.

The raw exact RPM inventory belongs to the fresh machine-capture archive summarized by `reference-current-development-machine-2026-09-04-104103.md`; the older `reference-local-development-state-2026-09-04.md` remains historical evidence only.

## 7. Offline/reproducible build rule

A fully prepared source checkout may build without network access once:

```text
Jolt accepted source snapshot is vendored for milestones that build it
Slang accepted artifact is verified and present in the tool cache
matching FFmpeg development packages are installed for milestones that build the cinematic backend
other Fedora RPM build dependencies are installed
```

Ordinary compilation must not fetch arbitrary moving branches/releases.

## 8. Build-manifest and release-license capture

M0 records exact installed RPM NEVRA values and tool versions used for the reference build rather than relying only on Fedora package names. The build manifest includes at least compiler, linker, ccache state, CMake, Ninja, Vulkan headers/loader/driver identity, SDL3, OpenAL Soft and FFmpeg/libav package identities plus the pinned Slang/Jolt identities. Benchmark/replay qualification artifacts reference the manifest hash.

Vendored/tool-cache dependencies also record SPDX/license identity and upstream license source. Current accepted identities include Jolt `MIT` and Slang `Apache-2.0 WITH LLVM-exception`. System-library distribution licensing remains an RPM/release-packaging audit item; this document does not substitute for the final package license review.
