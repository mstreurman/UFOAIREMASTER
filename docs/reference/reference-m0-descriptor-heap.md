# M0.7 R2 native `VK_EXT_descriptor_heap` qualification fixture

**Status:** implementation fixture; native B580 execution evidence pending
**Baseline:** landed M0.6 revision `f34679f8f5674a2a272595870b9ff55de7e13035`
**Risk fixture:** R2 from architecture 091

## Purpose

This fixture proves the native Vulkan sampler/resource descriptor-heap API on the reference Intel Arc B580 before production renderer code depends on it.

It is deliberately standalone. It does not modify `src/`, does not enable a remaster production backend, and does not change canonical gameplay or presentation defaults.

## Scope boundary

R2 isolates the driver/API heap mechanism from the later shader ABI gates.

The compute shader intentionally emits conventional Vulkan `DescriptorSet` / `Binding` decorations. `VkShaderDescriptorSetAndBindingMappingInfoEXT` maps those declarations to native descriptor-heap offsets at pipeline creation. This is the compatibility binding interface defined by `VK_EXT_descriptor_heap`.

The following remain separate M0.7 fixtures:

- R3: pinned Slang direct `SPV_EXT_descriptor_heap` lowering, reflection and package/ABI checks;
- R4: the architecture-089 8-byte acceleration-structure heap representation and RT execution.

A successful R2 result therefore does not claim R3 or R4 are qualified.

## Device qualification

The executable selects only the architecture-012 reference device identity:

```text
vendorID = 0x8086
deviceID = 0xe20b
deviceType = DISCRETE_GPU
```

`llvmpipe` is never accepted as a substitute.

The fixture requires Vulkan API 1.4 and `VK_EXT_descriptor_heap` revision 1. It verifies `VK_KHR_shader_untyped_pointers` and `shaderUntypedPointers` support because that is part of the accepted device contract, but does not enable the untyped-pointer feature in R2 because the compatibility binding interface does not need it.

## B580 property gate

The queried device must reproduce the accepted Mesa 26.2.2 B580 values:

```text
samplerHeapAlignment        = 64 B
resourceHeapAlignment       = 64 B
maxSamplerHeapSize          = 2 GiB
maxResourceHeapSize         = 2 GiB
samplerDescriptorSize       = 32 B
imageDescriptorSize         = 64 B
bufferDescriptorSize        = 64 B
samplerDescriptorAlignment  = 32 B
imageDescriptorAlignment    = 64 B
bufferDescriptorAlignment   = 64 B
minSamplerHeapReservedRange = 0 B
minResourceHeapReservedRange= 0 B
sparseDescriptorHeaps       = true
protectedDescriptorHeaps    = false
maxPushDataSize             >= 32 B
```

The fixture also cross-checks descriptor sizes through `vkGetPhysicalDeviceDescriptorSizeEXT`.

## Heap construction proof

Both heap buffers use:

```text
VK_BUFFER_USAGE_DESCRIPTOR_HEAP_BIT_EXT
VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT
```

Host-visible + host-coherent memory is required for this B580 qualification fixture and device-local memory is preferred and reported.

The implementation does not assume the raw buffer device address satisfies heap alignment. Each backing buffer is deliberately over-allocated and the bound heap address is computed as:

```text
rawBase       = vkGetBufferDeviceAddress(...)
heapBase      = align_up(rawBase, requiredHeapAlignment)
heapBaseDelta = heapBase - rawBase
```

The selected heap range is checked to remain inside the backing buffer. Mapped descriptor writes use `mappedBase + heapBaseDelta`. Any implementation reservation is placed at the tail of the bound range.

## C++ Vulkan structure initialization

All Vulkan structures carrying `sType` are fully zero-initialized before `sType` is assigned. The fixture uses one typed helper for that pattern instead of partial aggregate initialization. This keeps every unspecified member deterministically zero and remains warning-clean under the Fedora 44 GCC 16 `-Wmissing-field-initializers` diagnostic while preserving `-Werror`.

## Execution proof

One compute pipeline is created with:

```text
VK_PIPELINE_CREATE_2_DESCRIPTOR_HEAP_BIT_EXT
pipeline layout = VK_NULL_HANDLE
```

The fixture writes and consumes:

- a sampler descriptor through `vkWriteSamplerDescriptorsEXT`;
- a sampled-image resource descriptor through `vkWriteResourceDescriptorsEXT`;
- a storage-image resource descriptor through `vkWriteResourceDescriptorsEXT`;
- a storage-buffer resource descriptor through `vkWriteResourceDescriptorsEXT`;
- sampler and resource heap bindings through `vkCmdBindSamplerHeapEXT` and `vkCmdBindResourceHeapEXT`;
- a 32-byte `GpuShaderRoot`-compatible push-data block through `vkCmdPushDataEXT`.

The compute dispatch samples one of two 1x1 RGBA images, derives deterministic values from the 32-byte root data, writes one value through an `R32_UINT` storage image for transfer/readback verification, and writes the complete four-value result through an `RWStructuredBuffer<uint>` for host verification.

## Publication/retirement churn

The executable runs 256 iterations. Each iteration rewrites the live sampler/resource descriptor bytes, alternates the sampled image, dispatches, verifies both output paths, and waits for a fence before descriptor bytes are republished.

This is a small lifetime/publication churn qualification, not a renderer-scale performance benchmark.

## Validation contract

`VK_LAYER_KHRONOS_validation` is mandatory. Warning and error messages are counted through `VK_EXT_debug_utils`; the result fails unless both counts are zero.

The runner also:

1. validates the generated SPIR-V for Vulkan 1.4 with `spirv-val`;
2. disassembles it and requires legacy `DescriptorSet`, `Binding`, and `PushConstant` declarations;
3. rejects direct `SPV_EXT_descriptor_heap` / `DescriptorHeapEXT` in R2 so the R2/R3 risk boundary cannot silently collapse;
4. clears inherited Vulkan device/ICD/layer override variables only in the fixture subprocess;
5. discovers the installed system Intel ANV ICD manifest that identifies `libvulkan_intel.so`, prefers the native `x86_64` manifest, and forces that single absolute manifest with scoped `VK_DRIVER_FILES`;
6. isolates HOME/XDG state, locale and timezone for execution;
7. fingerprints the selected Intel ICD manifest plus fixture inputs and built shader/executable in captured evidence.

## Vulkan ICD isolation

The zero-warning gate applies to the driver under qualification, not to unrelated installed Vulkan ICDs. The Fedora workstation can contain Mesa `dzn`, lavapipe and other manifests. Loader probing of an unrelated ICD may emit warnings before physical-device selection, which would make a strict validation count nondeterministic without actually testing the B580 path.

The runner therefore clears inherited loader-selection variables in its child environment, discovers the system Intel ANV manifest whose `ICD.library_path` identifies `libvulkan_intel.so`, requires a unique native `x86_64` choice when multiple architectures are installed, and sets:

```text
VK_DRIVER_FILES=/absolute/path/to/intel_icd.x86_64.json
```

for the fixture subprocess only. It does not export or persist this setting in the user's shell. The manifest path, manifest SHA-256 and declared driver library are captured in R2 evidence. This excludes unrelated ICD probe noise without filtering validation messages from the Intel driver being qualified.

## Evidence files

Successful capture creates:

```text
docs/reference/reference-m0-descriptor-heap.txt
docs/reference/reference-m0-descriptor-heap.b3
```

`--verify` rebuilds and reruns the fixture, byte-compares newly generated evidence to the stored evidence, and verifies the BLAKE3 sidecar.

## Acceptance

R2 is accepted only when all of the following pass on the reference workstation:

```text
clean standalone CMake/Ninja build
pinned Slang v2026.17 shader compile
spirv-val --target-env vulkan1.4
exact Arc B580 device/property selection
explicitly aligned sampler/resource heap ranges
sampler/resource descriptor writes
sampler/resource heap binds
32-byte push data
sampled-image read
storage-image write + readback
storage-buffer read/write
256 publish/retire iterations
zero validation warnings
zero validation errors
capture followed by byte-identical immediate verify
```

Failure blocks descriptor-heap production bring-up for diagnosis. It does not authorize a descriptor-buffer or descriptor-set production fallback.
