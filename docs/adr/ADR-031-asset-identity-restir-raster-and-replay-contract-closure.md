# ADR-031 — Asset Identity, ReSTIR, Raster and Replay Contract Closure

**Status:** Accepted  
**Decision type:** Pre-implementation identity/math contract closure  
**Primary target:** Fedora 44 / i9-9900K / Intel Arc B580  
**Related:** ADR-013, ADR-017, ADR-020, ADR-022, ADR-029, ADR-030

## Context

The Baseline-024 full deep scan found no gameplay/presentation authority regression, but it found five contracts that still permitted incompatible implementations:

```text
raster front-face validation under the accepted Vulkan screen convention
AssetId128 path normalization / digest mapping
ContentHash256 / SourceHash256 byte coverage
ReSTIR DI estimator math
effect-to-Philox stream assignment
```

## Decision 1 — raster convention remains CCW

Keep:

```text
runtime geometry: counter-clockwise outside-facing
Vulkan viewport: positive height
projection: explicit Vulkan Y correction
raster state:
    VK_FRONT_FACE_COUNTER_CLOCKWISE
    VK_CULL_MODE_BACK_BIT
```

A required reference-triangle/cube test proves that the accepted projection/viewport path preserves the intended semantic outside face.

## Decision 2 — AssetId128 v1

Asset identity uses:

```text
case-sensitive
case-preserving
UTF-8
Unicode 17.0.0 NFC
root-relative virtual paths
```

Normalization converts `\` to `/`, collapses repeated interior separators, removes `.` components, rejects `..`, and rejects leading/trailing `/`.

ID derivation:

```text
digest =
    BLAKE3-256(
        "UFOAIREMASTER:AssetId:v1\0" ||
        normalizedPathUtf8
    )

AssetId128.lo = LE64(digest bytes 0..7)
AssetId128.hi = LE64(digest bytes 8..15)
```

Different normalized path bytes, including different case, produce different IDs.

The compiler also rejects Unicode-17 full-case-fold collisions as a portability/content error; that check does not alter the case-sensitive ID.

## Decision 3 — semantic ContentHash256

`ContentHash256` is independent of:

```text
compression level
stored offsets
padding
CRC values
container placement
```

It hashes a versioned canonical semantic stream of asset/chunk metadata and exact uncompressed canonical chunk bytes.

## Decision 4 — SourceHash256

`SourceHash256` hashes a versioned canonical build-source manifest containing:

```text
normalized primary asset path
toolchain/config manifest hash
sorted normalized source/dependency paths
BLAKE3-256 of exact raw source-file bytes
```

No newline/text normalization is applied to raw source bytes.

## Decision 5 — exact ReSTIR DI baseline

Use classic weighted-reservoir ReSTIR DI:

```text
8 fresh candidates
deterministic per-frame local-light alias proposal
exact shape proposal
scalar target = ACEScg luminance of unshadowed RGB direct integrand
visibility excluded from target
weighted reservoir sampling
temporal reuse with M clamp
4 deterministic spatial reservoir candidates
one final RT visibility ray
final RGB estimator = selected unshadowed RGB integrand * reservoir W * visibility
```

## Decision 6 — exact stochastic stream ownership

Philox4x32-10 remains the primitive.

Architecture 068 assigns exact:

```text
domain
stableElement
sampleOrdinal
substream
output-word usage
```

for every production stochastic effect.

## Decision 7 — common binary/cache exactness

The common `.r*` header/chunk structures are fixed byte ABIs.

`ShaderBindingAbiHash256` v2 receives exact serialization and is stored in `.rshader` META.

Persistent sampled-image heap entries are published only after upload/layout stabilization and remain immutable while live. ADR-045 supersedes the historical descriptor-set/layout terminology.

## Decision 8 — remaining ABI cleanup

- `GpuInstance` no longer contains an ambiguous instance-to-draw index.
- `MaterialClass` and `MaterialFlags` numeric values are exact ABI-v1 values.
- `StaticRenderKey` source ordinals/identity values are exact.
- long-session GPU presentation time uses split high/low representation.
- duplicate exact struct ownership is reduced.
- stale open-list items are normalized.

## Consequence

Later Baseline 031 authorities close ray-origin/alpha-test behavior and reference-v1 trace/replay/probe packing. Remaining work under this ADR is implementation sequencing, measured tuning, optional later compact/compressed formats and UI/content quality work.
