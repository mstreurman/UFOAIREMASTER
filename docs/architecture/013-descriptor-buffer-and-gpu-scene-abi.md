# Descriptor-Buffer GPU Scene ABI — Superseded Reference

**Status:** Superseded for production binding by ADR-045 / architecture 089  
**Related ADR:** ADR-015, ADR-045

## Purpose

This filename is retained so historical audit links remain valid.

Earlier baselines designed the renderer around `VK_EXT_descriptor_buffer`. Baseline 036 explicitly replaces that production binding model with `VK_EXT_descriptor_heap` from the first renderer implementation.

The following principles survive the superseded descriptor-buffer design:

```text
bindless resource indexing
Buffer Device Address for large structured scene arrays
one common GPU scene representation for raster/compute/RT
fixed v1 sampled-image capacity of 65536
fixed v1 sampler capacity of 256
reflection-verified Slang/SPIR-V ABI
FrameContext lifetime separation
descriptor publication only after resource state is valid
no silent capacity/layout ABI mutation
```

They are now implemented through the exact heap contract in:

```text
architecture/056-exact-shader-root-descriptor-and-slang-compile-contract.md
architecture/061-pass-data-bindless-registry-and-pipeline-layout-abi.md
architecture/070-rshader-layout-hash-material-and-set0-publication-abi.md
architecture/089-exact-descriptor-heap-gpu-binding-abi.md
```

## Non-authoritative historical model

The old Set-0/Set-1/Set-2 descriptor-buffer layout, descriptor-buffer offset rules, mapped descriptor-buffer regions and `PipelineLayoutAbiHash256` are historical only.

Production code must not recreate them as an initial implementation or fallback.

`VK_EXT_descriptor_buffer` may still appear in the measured B580 capability reference because the driver exposes it. Capability availability does not make it part of the renderer ABI.
