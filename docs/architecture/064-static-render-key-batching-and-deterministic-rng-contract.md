# Static Render Key, Identity Batching and Deterministic RNG Contract

**Status:** Exact implementation specification  
**Related ADR:** ADR-030  
**Related architecture:** 048, 058, 059

## 1. StaticRenderKey type

```cpp
struct StaticRenderKey {
    uint8_t bytes[32];
};

static_assert(sizeof(StaticRenderKey) == 32);
```

Ordering is unsigned lexicographic byte order.

## 2. Source tuple serialization

`remaster-mapc` constructs a versioned little-endian byte tuple:

```text
u32 keyFormatVersion = 1
u64 tilePlacementSequence
u32 tacticalLevel
u32 canonicalIdentityKind
u64 canonicalIdentityValue
u8  presentationMeshAssetId[16]
u32 sectionIdentityGroupOrdinal
```

Exact identity kinds:

```cpp
enum StaticCanonicalIdentityKind : uint32_t {
    BspSurface             = 0,
    InlineModelSurface     = 1,
    PresentationOnlyGroup  = 2
};
```

`canonicalIdentityValue` is the deterministic compiler ordinal/key inside the selected identity-kind namespace.

For a non-RMA/monolithic map:

```text
tilePlacementSequence = 0
```

No native struct padding is hashed.

## 3. Key derivation

```text
StaticRenderKey =
    BLAKE3-256(serializedTuple)
```

The compiler retains the unhashed tuple in validation/debug metadata where useful.

If two distinct tuples produce the same 256-bit key:

```text
fatal asset compiler collision error
```

No collision fallback changes ordering silently.

## 4. Tile placement sequence

`tilePlacementSequence` is assigned by the deterministic final RMA/static presentation assembly order.

It is not pointer/address order and not filesystem enumeration order.

Identical canonical map assembly/content produces identical sequence values.

## 5. Static registration

Runtime:

```text
read static identity groups
sort by StaticRenderKey bytes
allocate RenderObjectId monotonically
```

This occurs before dynamic render-object allocation.

## 6. Raster batching boundary

One `GpuDrawData` carries one `renderObjectId`.

Therefore a raster draw may contain geometry from exactly one stable render-identity group.

Batching must split when `RenderObjectId` changes even if:

```text
material matches
mesh buffer matches
pipeline matches
```

Performance batching may still combine command generation/indirect submission without merging identity semantics.

## 7. RT geometry boundary

An RT geometry entry may carry one:

```text
renderObjectIdOverride
```

It must not merge triangles belonging to different static render-identity groups into one identity-bearing geometry entry.

A BLAS may still contain many RT geometries/IDs.

## 8. Raster/RT parity validation

Offline/runtime debug validation samples identity groups and verifies:

```text
raster G4 ID
RT hit resolved ID
StaticRenderKey mapping
```

agree for the same static presentation surface/group.

## 9. Stochastic RNG algorithm

Presentation stochastic GPU work uses:

```text
Philox4x32-10
```

as a counter-based generator.

No effect consumes a shared mutable RNG stream.

## 10. Global presentation stochastic seed

Replay/session metadata provides:

```text
uint64 presentationRandomSeed
```

FrameConstants contains the low/high 32-bit halves of this seed.

The seed does not advance by mutation.

## 11. RNG domain IDs

ABI v1:

```cpp
enum PresentationRngDomain : uint32_t {
    RestirCandidate      = 1,
    RestirSpatial        = 2,
    ReflectionPrimary    = 3,
    ReflectionFilter     = 4,
    DdgiProbeRay         = 5,
    VolumetricSample     = 6,
    VfxParticle          = 7,
    DebugDiagnostic      = 8
};
```

Zero is invalid/reserved.

## 12. Counter/key construction

Inputs:

```text
uint64 presentationRandomSeed
uint32 frameIndex
uint32 domainId
uint64 stableElement
uint32 sampleOrdinal
uint32 substream
```

Counter:

```text
c0 = frameIndex
c1 = domainId
c2 = low32(stableElement)
c3 = sampleOrdinal
```

Key:

```text
k0 = seedLo ^ Mix32(high32(stableElement))
k1 = seedHi ^ Mix32(substream)
```

`stableElement` is effect-specific:

```text
screen pixel linear index
DDGI probe ID
stable light lifetime identity packed as:
    (uint64(lightGeneration) << 32) | lightId
RenderObjectId
stable emitter/particle spawn ID
```

The effect document specifies which stable element it uses.

## 13. Exact `Mix32`

```cpp
uint32_t Mix32(uint32_t x) {
    x ^= x >> 16;
    x *= 0x7feb352dU;
    x ^= x >> 15;
    x *= 0x846ca68bU;
    x ^= x >> 16;
    return x;
}
```

C++ and Slang use identical modulo-2^32 integer arithmetic.

## 14. Exact Philox4x32-10 constants

```text
M0 = 0xD2511F53
M1 = 0xCD9E8D57
W0 = 0x9E3779B9
W1 = 0xBB67AE85
```

One round for counter `(c0,c1,c2,c3)` and key `(k0,k1)`:

```text
hi0, lo0 = mulHiLo(M0, c0)
hi1, lo1 = mulHiLo(M1, c2)

next.c0 = hi1 ^ c1 ^ k0
next.c1 = lo1
next.c2 = hi0 ^ c3 ^ k1
next.c3 = lo0

nextKey.k0 = k0 + W0
nextKey.k1 = k1 + W1
```

Apply exactly ten rounds.

All operations are unsigned 32-bit modulo arithmetic.

## 15. Required known-answer tests

Before renderer stochastic code is accepted, C++ and Slang tests contain identical known-answer vectors for:

```text
Mix32
one Philox round
Philox4x32-10
counter/key construction for every domain
```

A C++/Slang mismatch is a build/test failure.

## 16. Scheduling independence

Changing:

```text
worker
wave/subgroup
dispatch order
pass chunking
async overlap
```

must not change a sample's random sequence when its semantic counter/key inputs are unchanged.

## 17. Replay

Presentation replay records:

```text
presentationRandomSeed
```

and the configuration/content/shader identities.

It does not need to record every random sample.

## Effect stream assignment authority

Architecture 068 owns exact production domain/stableElement/sampleOrdinal/substream/output-word mappings.

## ReSTIR codec authority

Architecture 067 owns the exact ReSTIR estimator and sample codecs.
