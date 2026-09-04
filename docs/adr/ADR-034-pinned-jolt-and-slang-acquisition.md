# ADR-034 — Pinned Jolt and Slang Acquisition

**Status:** Accepted  
**Decisions:** `DEPS-JOLT-001`, `DEPS-SLANG-001`

**Slang pin update:** ADR-047 / Baseline 039 supersedes ADR-041 and the original v2026.14 Slang artifact identity while preserving this ADR's acquisition policy.

## Jolt

Pin:

```text
Jolt Physics v5.6.0
commit e77f175595e64cb44218cc9d9d56fc365ad0e36a
license MIT
```

Vendor an immutable source snapshot in the project, build it statically, and disable Jolt compute backends. Do not use a git submodule and do not depend on a system Jolt package.

The reference build enables the i9-9900K-supported x86 feature set through Jolt's documented CMake switches: SSE4.1, SSE4.2, AVX, AVX2, LZCNT, TZCNT, F16C and FMADD on; AVX-512 off. Jolt remains presentation-only, so cross-platform deterministic simulation is not required for canonical gameplay.

Production qualification requires architecture-082 stress testing. v5.5.0 is the pre-authorized fallback candidate if 5.6.0 fails the reference-machine qualification gate.

## Slang

Current pin (superseded from ADR-041 by ADR-047):

```text
release: v2026.17
artifact: slang-2026.17-linux-x86_64-glibc-2.27.tar.gz
SHA-256: e8162da376858faf7d00dc9a94be52a8ff014d14c35c5f8e49c97688ec57bb7b
runtime game dependency: NO
```

The build/bootstrap layer verifies the digest before extraction. Building Slang from the same pinned source release is fallback-only.

The update is motivated in part by Slang's `SPV_EXT_descriptor_heap` support and direct `ResourceDescriptorHeap[]` / `SamplerDescriptorHeap[]` syntax. ADR-045 / Baseline 036 subsequently accepts that heap path as the production renderer binding model from initial implementation.

## Authority

Exact acquisition and integration metadata lives in `../reference/reference-third-party-toolchain-manifest.md` and architecture 082/029.
