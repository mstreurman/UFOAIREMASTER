# Asset ID, Container, Content Hash and Source Hash v1 ABI

**Status:** Exact implementation specification  
**Related ADR:** ADR-022, ADR-031  
**Runtime:** Fedora 44 x86-64, little endian

## 1. Unicode normalization version

Asset-path ABI v1 pins:

```text
Unicode Standard 17.0.0
Normalization Form C (NFC)
```

A future Unicode normalization upgrade requires an asset-ID ABI version change.

## 2. NormalizeAssetPathV1

Input must be valid UTF-8.

```text
1. reject U+0000
2. replace ASCII '\' (U+005C) with '/'
3. reject if converted path begins with '/'
4. reject if converted path ends with '/'
5. split on '/'
6. discard empty interior components from repeated separators
7. discard component "."
8. reject component ".."
9. join remaining components with one '/'
10. reject empty final path
11. normalize complete joined UTF-8 string to Unicode-17 NFC
12. revalidate: no leading/trailing '/', no empty component, no "."/".." component
13. emit NFC UTF-8 bytes exactly
```

Identity is case-sensitive, case-preserving and locale-independent.

No case fold is applied for AssetId generation.

## 3. Case-collision diagnostic

For portability, compilers additionally compute Unicode-17 full default case fold followed by NFC.

Two distinct normalized asset paths with the same folded diagnostic key are a content-build error.

This diagnostic does not change AssetId bytes.

## 4. AssetId128 v1

Exact domain prefix, including terminating NUL:

```text
UFOAIREMASTER:AssetId:v1\0
```

```text
digest32 =
    BLAKE3-256(
        domainPrefix ||
        NormalizeAssetPathV1(path)
    )
```

```cpp
struct AssetId128 {
    uint64_t lo;
    uint64_t hi;
};
static_assert(sizeof(AssetId128) == 16);
```

Mapping:

```text
lo = LE64(digest32[0..7])
hi = LE64(digest32[8..15])
```

Raw 16-byte serialization is `digest32[0..15]`.

## 5. Exact common header v1

```cpp
struct RemasterAssetHeaderV1 {
    char     magic[4];          // 0
    uint16_t majorVersion;      // 4
    uint16_t minorVersion;      // 6
    uint32_t flags;             // 8
    uint32_t chunkCount;        // 12
    uint64_t fileSize;          // 16
    uint64_t chunkTableOffset;  // 24
    uint8_t  contentHash[32];   // 32
    uint8_t  sourceHash[32];    // 64
    uint8_t  reserved[32];      // 96
};
static_assert(sizeof(RemasterAssetHeaderV1) == 128);
```

All integers are little-endian. ABI-v1 header flags are zero. Reserved bytes are written zero.

The C++ declarations document field offsets and sizes; readers/writers serialize fields explicitly and never `fwrite`/`memcpy` native structs as the file ABI.

FourCC/chunk type values use literal ASCII bytes in file order. Equivalently:

```cpp
constexpr uint32_t FourCC(char a, char b, char c, char d) {
    return uint32_t(uint8_t(a))
         | (uint32_t(uint8_t(b)) << 8)
         | (uint32_t(uint8_t(c)) << 16)
         | (uint32_t(uint8_t(d)) << 24);
}
```

Thus chunk name `META` is stored as bytes `4d 45 54 41`.

## 6. Exact common chunk descriptor v1

```cpp
struct RemasterAssetChunkV1 {
    uint32_t type;              // 0
    uint32_t flags;             // 4
    uint64_t fileOffset;        // 8
    uint64_t storedSize;        // 16
    uint64_t uncompressedSize;  // 24
    uint32_t alignment;         // 32
    uint32_t crc32c;            // 36
    uint64_t reserved;          // 40
};
static_assert(sizeof(RemasterAssetChunkV1) == 48);
```

`reserved = 0`.

## 7. Chunk flags v1

```text
bits 0..3 StorageEncoding
0 = Uncompressed
1 = Zstd
2..15 reserved

bits 4..31 type-specific semantic flags
```

```text
semanticFlags = flags & 0xfffffff0
storageEncoding = flags & 0x0000000f
```

Unknown storage encoding is rejected.

## 8. Container placement

```text
header:
    offset 0
    size 128

chunk table:
    offset >= 128
    16-byte aligned
    chunkCount * 48 bytes
    entirely within fileSize

top-level payload:
    aligned to max(64, chunk.alignment)
```

`alignment` is power-of-two and >=1.

Stored payload ranges may not overlap header, table or another payload.

Padding bytes are written zero and are not semantic.

## 9. CRC32C v1

CRC covers exactly:

```text
[fileOffset, fileOffset + storedSize)
```

and excludes padding/table/other chunks.

CRC-32C Castagnoli:

```text
reflected polynomial = 0x82F63B78
initial value        = 0xffffffff
final xor            = 0xffffffff
```

CRC is over stored bytes, before decompression.

## 10. Canonical chunk order

Chunk-table order is semantic compiled content.

Each asset-format specification defines canonical chunk order.

Duplicate chunk types are forbidden unless the owning format explicitly defines duplicate occurrence order.

## 11. ContentHash256 v1

Domain:

```text
UFOAIREMASTER:ContentHash:v1\0
```

Canonical stream, integers little-endian:

```text
domainPrefix

magic[4]
u16 majorVersion
u16 minorVersion
u32 semanticHeaderFlags
u32 chunkCount

for each chunk in canonical table order:
    u32 type
    u32 semanticFlags
    u64 uncompressedSize
    u8  uncompressedCanonicalPayload[uncompressedSize]
```

For ABI v1, `semanticHeaderFlags = 0`.

Excluded:

```text
fileSize
chunkTableOffset
contentHash
sourceHash
reserved bytes
fileOffset
storedSize
alignment
crc32c
StorageEncoding bits
padding
compressed representation
```

Recompressing identical canonical chunk data does not change `ContentHash256`.

## 12. Canonical payload bytes

Uncompressed chunk: payload bytes are the canonical payload.

Zstd chunk: canonical payload is exact decompressed bytes.

The owning chunk spec must serialize its uncompressed payload deterministically.

## 13. RawSourceHash256

```text
RawSourceHash256 =
    BLAKE3-256(exact file bytes)
```

No newline normalization, UTF-8 normalization, case folding, comment stripping or filesystem metadata.

## 14. ToolchainConfigHash256

Domain:

```text
UFOAIREMASTER:ToolchainConfig:v1\0
```

Canonical manifest records sorted by unsigned UTF-8 key bytes:

```text
u32 keyByteCount
u8 key[keyByteCount]
u32 valueByteCount
u8 value[valueByteCount]
```

Keys are unique.

Required keys include applicable tool/compiler/config/target/ABI identities.

## 15. SourceHash256 v1

Domain:

```text
UFOAIREMASTER:SourceHash:v1\0
```

Canonical stream:

```text
domainPrefix
u32 manifestVersion = 1

u32 primaryPathByteCount
u8 NormalizeAssetPathV1(primaryPath)

u8 ToolchainConfigHash256[32]

u32 sourceRecordCount

source records sorted by unsigned normalized-path UTF-8 bytes:
    u32 pathByteCount
    u8 normalizedPath[pathByteCount]
    u8 RawSourceHash256[32]
```

A dependency path appears once.

## 16. Loader validation order

```text
magic/version/flags
file/table bounds
chunk bounds/alignment/overlap
stored CRC32C
decompression
ContentHash validation per load policy
asset-type semantic validation
dependency/hash coupling
```

Hash failure never triggers runtime recompilation.

## 17. `.rshader` ownership

`.rshader` uses the common outer `ContentHash256` as package content identity.

It does not embed a second self-referential package-content hash inside META.

Pipeline-layout identity is separate and owned by architecture 070.
