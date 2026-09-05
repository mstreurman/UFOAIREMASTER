# M0.7 R4 acceleration-structure descriptor-heap + TraceRay reference

**Status:** qualification mechanism; evidence is generated only by a successful Fedora 44 B580 gate

R4 closes the remaining descriptor-heap/ray-tracing migration risk after accepted R2 native sampler/resource execution and R3 Slang ABI/package qualification.

## Scope

The fixture proves, without modifying `src/` or replacing production behavior:

- pinned Slang v2026.17 compiler API compilation, not authoritative CLI/reflection scraping;
- SPIR-V 1.6, Vulkan 1.4, `SPV_EXT_descriptor_heap`, and `RayTracingKHR`;
- exact acceleration-structure heap lowering as a runtime array of `uint64` with `ArrayStride 8`;
- `OpConvertUToAccelerationStructureKHR` between the 64-bit heap load and ray traversal;
- `OpTraceRayKHR` on the production-facing `VK_KHR_ray_tracing_pipeline` path;
- no descriptor-set/binding decorations for the direct-heap resources;
- the v1 32-byte `GpuShaderRoot` with offsets `0,8,16,24`;
- exact Intel Arc B580 selection (`0x8086:0xe20b`) under a forced Intel ANV ICD manifest;
- mandatory descriptor-heap, untyped-pointer, acceleration-structure, ray-tracing-pipeline, and RT-maintenance feature checks;
- one known triangle BLAS and one TLAS built with device-address-backed Vulkan buffers;
- `vkGetAccelerationStructureDeviceAddressKHR(TLAS)` returns a non-zero 64-bit address;
- that exact 64-bit TLAS address is raw-published into the resource heap at an 8-byte typed AS slot;
- the AS publication deliberately does **not** call `vkWriteResourceDescriptorsEXT`, because architecture 089 defines the selected Slang direct-AS path as a raw device-address element rather than Vulkan's opaque AS descriptor representation;
- a separate storage-buffer descriptor is generated with `vkWriteResourceDescriptorsEXT` at the B580 unified image/buffer descriptor stride;
- the AS and image/buffer typed views share one byte domain without sharing one universal slot namespace;
- a descriptor-heap ray-tracing pipeline is created with `VK_PIPELINE_CREATE_2_DESCRIPTOR_HEAP_BIT_EXT` and `layout = VK_NULL_HANDLE`;
- shader binding table addresses/strides honor queried B580 handle/base alignment properties;
- `vkCmdBindResourceHeapEXT`, `vkCmdPushDataEXT`, and `vkCmdTraceRaysKHR` execute a 1x1x1 known-triangle smoke;
- the closest-hit shader returns the required magic value and a finite hit distance near 1.0;
- Vulkan validation reports zero warnings and zero errors;
- immediate `--verify` regenerates byte-identical normalized evidence even though process-local GPU virtual addresses themselves may differ between runs.

## Deliberate representation boundary

Do not substitute the opaque `VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR` descriptor produced by `vkWriteResourceDescriptorsEXT` for this R4 path. The accepted Slang v2026.17 direct descriptor-heap lowering consumes an 8-byte `uint64` acceleration-structure device-address element and converts it with `OpConvertUToAccelerationStructureKHR`.

The runtime evidence therefore records address equality semantically (`tlas.address_match=PASS`) rather than pinning an address value that may legitimately vary between executions. The raw run log still prints both values for audit.

## Authoritative run

```bash
python3 tools/remaster/run-m0-rt-descriptor-heap-fixture.py --capture
python3 tools/remaster/run-m0-rt-descriptor-heap-fixture.py --verify
```

A successful capture writes:

```text
docs/reference/reference-m0-rt-descriptor-heap.txt
docs/reference/reference-m0-rt-descriptor-heap.b3
```

Do not create or edit those files by hand. A failed build, compile, SPIR-V semantic check, native TraceRay execution, or validation-layer check must not be converted into reference evidence.
