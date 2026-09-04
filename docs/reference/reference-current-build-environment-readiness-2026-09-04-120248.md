# Current Build-Environment Readiness — 2026-09-04 12:02:48 +02:00

**Status:** Current implementation-bootstrap evidence  
**Scope:** project-local Slang provisioning, Vulkan descriptor-heap header/link compatibility, Slang/SPIR-V descriptor-heap smoke, development dependency availability, toolchain identity, canonical checkout/build presence  
**Supersedes for provisioning/readiness state:** the pre-provisioning fields in `reference-current-development-machine-2026-09-04-104103.md`  
**Does not supersede:** hardware/OS/display/audio facts in the broad and audio captures

## Result

The isolated final environment smoke completed with:

```text
FINAL LOCAL BUILD-ENVIRONMENT SMOKE: PASS
```

This establishes that the reference workstation is ready to begin Baseline-039/040 M0 implementation work. It does **not** claim that native descriptor-heap execution, RT acceleration-structure heap access, Jolt qualification, cinematic corpus qualification, or final B580/i9 performance targets have already passed; those are implementation-stage gates.

## Vulkan headers and loader link

A C++20 smoke program compiled with:

```text
-Wall -Wextra -Werror
-lvulkan
```

and referenced:

```text
VkPhysicalDeviceDescriptorHeapFeaturesEXT
VkPhysicalDeviceDescriptorHeapPropertiesEXT
PFN_vkWriteResourceDescriptorsEXT
PFN_vkWriteSamplerDescriptorsEXT
PFN_vkCmdBindResourceHeapEXT
PFN_vkCmdBindSamplerHeapEXT
PFN_vkCmdPushDataEXT
VK_BUFFER_USAGE_DESCRIPTOR_HEAP_BIT_EXT
VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT
```

Result:

```text
PASS: Vulkan headers compile and link
```

Therefore the installed Vulkan headers/loader development environment exposes the API surface needed to start the heap-first renderer implementation.

## Slang v2026.17 provisioning

The exact accepted artifact was downloaded and verified before extraction:

```text
artifact: slang-2026.17-linux-x86_64-glibc-2.27.tar.gz
SHA-256: e8162da376858faf7d00dc9a94be52a8ff014d14c35c5f8e49c97688ec57bb7b
verification: PASS
```

Provisioned location:

```text
tools/slang/v2026.17/
tools/slang/v2026.17/bin/slangc
tools/slang/v2026.17/include/slang.h
tools/slang/v2026.17/lib/libslang.so
```

Reported compiler version:

```text
2026.17
```

The project invokes the explicit tool-cache path; the unrelated Fedora `slang` RPM remains irrelevant to shader compilation.

## DescriptorHeapEXT compiler/SPIR-V smoke

Pinned Slang v2026.17 successfully compiled a compute fixture using:

```text
ResourceDescriptorHeap[]
SamplerDescriptorHeap[]
-capability spvDescriptorHeapEXT
-spirv-unified-descriptor-heap-stride
-matrix-layout-column-major
-emit-spirv-directly
-target spirv
-profile spirv_1_6
```

The emitted module passed:

```text
spirv-val --target-env vulkan1.4
```

Disassembly contained:

```text
OpCapability DescriptorHeapEXT
BuiltIn ResourceHeapEXT
BuiltIn SamplerHeapEXT
```

and the smoke found no conventional `DescriptorSet` / `Binding` decorations for the heap resources.

Result:

```text
PASS: Slang emitted SPIR-V
PASS: spirv-val Vulkan 1.4
PASS: DescriptorHeapEXT resource/sampler heaps present
PASS: no conventional DescriptorSet/Binding decorations
```

## SPIR-V Tools qualifier

The reference workstation reports:

```text
SPIRV-Tools v2026.1
```

This installed build accepts and validates the DescriptorHeapEXT module for Vulkan 1.4. It does not expose the newer explicit descriptor-layout CLI switches that were added upstream after this Fedora package generation. Those switches are therefore optional supplemental checks when available, not an M0 prerequisite. Exact B580 descriptor-size/alignment conformance remains owned by the native Vulkan heap fixture using queried runtime properties.

## Development libraries

Verified with `pkg-config`:

```text
SDL3          3.4.14
OpenAL        1.24.2
libavcodec    62.28.102
libavformat   62.12.102
libavutil     60.26.102
libswresample 6.3.102
libswscale    9.5.102
```

The matching Fedora 44 RPM Fusion package installed during provisioning is:

```text
ffmpeg-devel-8.1.2-3.fc44.x86_64
```

This closes the previously recorded FFmpeg-development provisioning gap. It does not waive the architecture-083 shipped-cinematic corpus qualification.

## Toolchain identity rechecked

```text
GCC/G++       16.2.1
Clang         22.1.8
CMake         4.3.0
Ninja         1.13.2
Git           2.55.0
ccache        4.12.3
SPIR-V Tools  2026.1
```

## Canonical checkout and existing build

```text
HEAD = 763173ed036ebbee32c2a7bf6aefa19748df89ff
build-f44/ufo     PRESENT
build-f44/ufoded  PRESENT
build-f44/base/game.so PRESENT
```

Observed working-tree state:

```text
?? build-f44/
?? docs/
?? tools/
```

`tools/` is currently untracked rather than ignored. This does not block compilation, but the repository should add an explicit ignore policy for the binary Slang tool cache before the first remaster commit if the cache is intended to remain local-only.

## Readiness classification

```text
C/C++ compiler environment:          READY
CMake/Ninja/ccache:                  READY
Vulkan loader/headers:               READY
Arc B580 / Mesa 26.2.2 runtime:      READY
VK_EXT_descriptor_heap capability:   READY
Slang v2026.17 provisioning:         READY
Slang DescriptorHeapEXT compilation: READY
SPIR-V Vulkan-1.4 validation:        READY
SDL3 development:                    READY
OpenAL development:                  READY
FFmpeg development:                  READY
canonical source/build baseline:     READY
Jolt source:                         INTENTIONALLY DEFERRED

native descriptor-heap execution:   IMPLEMENTATION QUALIFICATION
AS heap TraceRay/ray-query fixture:  IMPLEMENTATION QUALIFICATION
cinematic corpus:                    IMPLEMENTATION QUALIFICATION
B580/i9 performance gates:           IMPLEMENTATION QUALIFICATION
```

## Later Jolt provisioning supersession

This record is authoritative for the 12:02:48 environment smoke. Its `Jolt source: INTENTIONALLY DEFERRED` line was correct at that time but is no longer current workstation state. See `reference-current-jolt-provisioning-2026-09-04-121547.md`: Jolt v5.6.0 is now vendored/build-ready and passes upstream HelloWorld/UnitTests; production stress qualification remains pending.
