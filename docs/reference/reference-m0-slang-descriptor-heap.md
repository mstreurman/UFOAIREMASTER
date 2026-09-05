# M0.7 R3 Slang descriptor-heap ABI/reflection/package reference

**Status:** qualification mechanism; reference evidence is generated only by a successful Fedora 44 gate

This fixture qualifies the pinned Slang v2026.17 compiler API path required before production shader packaging depends on `SPV_EXT_descriptor_heap`.

## Scope

R3 proves, without changing production/canonical source:

- the fixture links the Slang compiler API from the project-local pinned v2026.17 distribution rather than shelling out to `slangc` for authoritative reflection;
- SPIR-V 1.6 with Vulkan 1.4 validation;
- the fixture's explicit `spirv_1_6` target is closed over all Slang capability atoms required by this shader, with no implicit-profile-upgrade warning accepted;
- `spvDescriptorHeapEXT` capability;
- `SPIRVResourceHeapStride = 0`;
- `SPIRVSamplerHeapStride = 0`;
- unified image/buffer resource-heap stride mode;
- scalar block layout;
- Vulkan memory model;
- explicit column-major default matrix layout (Slang/HLSL column-major is represented by SPIR-V `RowMajor` member decoration);
- direct `ResourceDescriptorHeap[]` / `SamplerDescriptorHeap[]` source use;
- sampled image, storage image, constant buffer, structured buffer and RW storage buffer handle recovery;
- source-level divergent heap indices are marked explicitly;
- authoritative `IBindlessResourceMetadata::usesBindlessResourceHeap()` target metadata reports heap use;
- `GpuShaderRoot` remains 32 bytes with offsets `0,8,16,24`;
- matrix reflection remains column-major;
- final SPIR-V has descriptor-heap builtins and no `DescriptorSet`/`Binding` decorations for direct-heap resources;
- `spirv-val --target-env vulkan1.4` passes;
- a deterministic `.rshader` qualification package uses the accepted `RSHD` common container, canonical `META,ENTR,SPV0,REFL,DEPS,NAME` order, META v2, CRC32C, common content/source hashes and exact `ShaderBindingAbiHash256` v2;
- two package builds from identical inputs are byte-identical.

## Deliberate boundary

This is the architecture-091 R3 compiler/package gate. Native sampler/resource execution is already proven by R2. Acceleration-structure 8-byte direct-address lowering and B580 TraceRay/ray-query execution remain R4 and are intentionally rejected if they appear in this fixture.

The `ENTR`, `REFL` and `DEPS` payloads in this qualification package are deterministic normalized fixture records. The common container ABI and META v2 fields are exact; future production `ufo-shaderc` may extend normalized record schemas only under their owning architecture/version rules.

## Authoritative run

```bash
python3 tools/remaster/run-m0-slang-descriptor-heap-fixture.py --capture
python3 tools/remaster/run-m0-slang-descriptor-heap-fixture.py --verify
```

A successful capture writes:

```text
docs/reference/reference-m0-slang-descriptor-heap.txt
docs/reference/reference-m0-slang-descriptor-heap.b3
```

Do not create or edit those files by hand. A failed gate must not be converted into reference evidence.
