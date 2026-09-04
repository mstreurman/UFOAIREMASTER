# RDGI DDGI User-Cache Container

**Status:** Exact implementation specification  
**Related ADR:** ADR-044  
**Outer-container authority:** architecture 066  
**DDGI record authority:** architecture 085  
**Shader-visible DDGI ABI:** architecture 057

## 1. Role

`RDGI` stores **disposable mutable DDGI warm-start history**. It is never canonical game data and never replaces `.rmap` static presentation content.

One `RDGI` file stores one DDGI volume. Multiple volumes for a map therefore produce independent cache files and can be invalidated independently.

## 2. Location

Use the platform cache-directory service. On the Fedora reference platform:

```text
if XDG_CACHE_HOME is non-empty:
    $XDG_CACHE_HOME/ufoai-remaster/ddgi/
else:
    $HOME/.cache/ufoai-remaster/ddgi/
```

Failure to create/read/write this directory is non-fatal and simply disables disk warm-start caching for that run.

Cache files are not installed into the game data tree and must not be committed to source control.

## 3. Outer container

Use `RemasterAssetHeaderV1` and `RemasterAssetChunkV1` from architecture 066.

```text
magic:         RDGI
majorVersion:  1
minorVersion:  0
flags:         0
```

All architecture-066 rules remain in force, including little-endian serialization, CRC-32C, `ContentHash256`, chunk bounds, canonical chunk ordering and top-level payload alignment of `max(64, chunk.alignment)`.

For `RDGI`, outer `sourceHash` stores the exact `SourceHash256` of the compatible `.rmap` source set. It is an early rejection key, not the complete cache identity.

## 4. Canonical chunk order

Exactly these five chunks occur once each, in this order:

```text
META
VOLM
PROB
IRAD
DIST
```

Unknown additional chunks are rejected by v1. Duplicate chunks are rejected.

All five chunks are `Uncompressed` in reference-v1. A later compressed representation requires an explicitly versioned format change; compression must not be inferred from size.

## 5. META v1

```text
uint32 cacheFormatVersion     = 1
uint32 rendererAbiVersion     = 1
uint32 ddgiEncodingVersion    = 1
uint32 volumeId
uint8  bspSourceHash256[32]
uint8  rmapContentHash256[32]
uint8  volumeDescriptorHash256[32]
uint8  ddgiShaderAbiHash256[32]
uint8  cacheKey256[32]
uint32 flags                  = 0
uint32 reserved[3]            = 0
```

All integer fields are little-endian. Hash fields are raw 32-byte BLAKE3 digests in byte order.

`bspSourceHash256` is the canonical BSP/source identity used by the map presentation compiler. `rmapContentHash256` is the accepted `.rmap` outer `ContentHash256`.

## 6. Volume descriptor hash

`volumeDescriptorHash256` is:

```text
BLAKE3-256(
    "UFOAIREMASTER:DDGIVolumeDescriptor:v1\0" ||
    exact serialized DDGI/VOLM reference-v1 record bytes
)
```

The `DDGI/VOLM` bytes are those defined by architecture 085.

## 7. DDGI shader ABI hash

`ddgiShaderAbiHash256` is:

```text
BLAKE3-256(
    "UFOAIREMASTER:DDGIShaderABI:v1\0" ||
    ShaderBindingAbiHash256 ||
    u32 shaderPackageCount ||
    sorted relevant .rshader ContentHash256 values
)
```

`shaderPackageCount` is little-endian. The `.rshader` content hashes are sorted lexicographically by raw 32-byte value before hashing. Relevant packages are exactly those used by DDGI trace/update/relocation/classification/gather for the current renderer build.

Changing any participating shader package invalidates the cache.

## 8. Cache key

```text
cacheKey256 = BLAKE3-256(
    "UFOAIREMASTER:DDGICacheKey:v1\0" ||
    bspSourceHash256 ||
    rmapContentHash256 ||
    volumeDescriptorHash256 ||
    ddgiShaderAbiHash256 ||
    LE32(rendererAbiVersion) ||
    LE32(ddgiEncodingVersion)
)
```

The cache filename is lowercase hexadecimal `cacheKey256` followed by `.rdgi`. The filename is a lookup convenience; the embedded META key must still be verified.

## 9. VOLM chunk

`VOLM` contains exactly one serialized `DDGI/VOLM` reference-v1 record from architecture 085. Its `volumeId` must equal `META.volumeId`.

## 10. PROB chunk

`PROB` contains exactly `probeCount.x * probeCount.y * probeCount.z` consecutive `DDGI/PROB` reference-v1 records from architecture 085, sorted by ascending `probeIndex`.

The first record must have `probeIndex = 0`; the last must have `probeIndex = probeCountTotal - 1`; no duplicate or missing index is valid.

## 11. IRAD and DIST chunks

`IRAD` contains exactly one architecture-085 `DDGI/TEXD` descriptor followed by its raw row-major payload and zero padding. It must declare:

```text
payloadKind = 1
texelFormat = RGBA16_SFLOAT
```

`DIST` contains exactly one `DDGI/TEXD` descriptor followed by payload and padding. It must declare:

```text
payloadKind = 2
texelFormat = RG16_SFLOAT
```

Dimensions/layers must agree with the current volume/atlas allocation expected by the DDGI loader. `rowPitchBytes`, `dataBytes` and all bounds are validated before allocation/copy.

## 12. Load validation

Validation order:

```text
1. outer architecture-066 header/table/bounds/CRC/content-hash validation
2. magic/version/chunk topology
3. META reserved/flags/version checks
4. bspSourceHash256 match
5. rmapContentHash256 match
6. current VOLM bytes -> volumeDescriptorHash256 match
7. current DDGI shader packages -> ddgiShaderAbiHash256 match
8. recompute cacheKey256 and compare META + filename key
9. VOLM semantic validation
10. PROB count/order/range validation
11. IRAD/DIST descriptor and payload-size validation
12. upload/seed runtime DDGI history
```

Any failure means:

```text
ignore cache
optionally delete/replace it
start DDGI from normal empty/reset state
continue map load
```

Cache rejection is not a fatal content error.

## 13. Write policy

Only write a cache after the volume has reached a valid presentation state and all probe/payload values intended for persistence are finite.

Write to a sibling temporary file, finish all payloads/table/header/hashes/CRCs, flush/close it, then atomically rename it over the final cache path. A crash or partial write must never make a malformed file authoritative.

The renderer may rate-limit writes. Write cadence is presentation/IO tuning, not gameplay behavior.

## 14. Security and robustness

Before allocating from cache-controlled sizes, validate multiplication overflow, file bounds, probe-count limits and payload byte limits against current renderer limits. Never trust cached counts merely because CRC/content hash passes.

## 15. Runtime behavior

Warm-start cache use is enabled when the cache directory is available. A developer/user diagnostic option may disable reading/writing caches, but disabling it must only affect DDGI convergence/performance and never gameplay.

Runtime DDGI history remains mutable GPU/presentation state. `RDGI` is merely a seed for that state.
