# Reference-v1 Persisted and Runtime Record ABIs

**Status:** Exact v1 serialization authority  
**Authority:** ADR-039, ADR-038

## 1. Global serialization rules

All reference-v1 persisted records use:

```text
little-endian integers
IEEE-754 binary32/binary64 floats as explicitly declared
UTF-8 strings without implicit normalization beyond the owning asset-ID rules
no native-struct dumps
no compiler padding
no pointer values
no implicit enum size
zero-filled reserved fields on write; reject nonzero reserved fields unless a later version defines them
8-byte alignment for subrecords/non-.r* envelopes where this document explicitly requires it; alignment bytes are zero
top-level `.r*` chunk payloads obey architecture 066 and are therefore aligned to max(64, chunk.alignment)
CRC/content/source hash rules from architecture 066 where the enclosing .r* container applies
```

Writers serialize fields individually in listed order. Readers bounds-check all counts/offsets before allocation.

Reference-v1 means **no quantization or bit packing unless explicitly shown below**.

## 2. `.ranim` v1

The first `.ranim` clip representation is dense sampled local-joint transforms.

Within the `.ranim` `RANM` container, `META`:

```text
uint32 jointCount            <= 256
uint32 frameCount
float32 sampleRateHz         > 0
float32 durationSeconds      >= 0
uint32 flags                 = 0 for v1
uint32 reserved              = 0
```

`TRAK` contains exactly `frameCount * jointCount` records in frame-major, joint-minor order:

```text
float32 translation[3]
float32 rotationQuaternion[4]    normalized xyzw
float32 scale[3]
```

No joint index is stored per record because array position is normative. The skeleton asset supplies hierarchy/rest pose. Optional animation events remain in their own versioned chunk and use explicit time + stable event ID/payload references.

A future compressed track chunk must use a different chunk/version and decode to the same semantic transforms.

## 3. DDGI persisted v1

Persisted DDGI is an optimization/cache, never canonical state.

`DDGI/VOLM` record:

```text
uint32 volumeId
uint32 flags
float32 origin[3]
float32 probeSpacing[3]
uint32 probeCount[3]
uint32 raysPerProbe
float32 hysteresis
float32 normalBias
float32 viewBias
uint32 irradianceTexelsPerProbe
uint32 distanceTexelsPerProbe
uint32 reserved[2] = 0
```

`DDGI/PROB` record per probe:

```text
uint32 probeIndex
uint32 state
float32 relocationOffset[3]
float32 classificationConfidence
```

Persisted irradiance/distance texel payloads use one `DDGI/TEXD` descriptor followed by raw row-major texel bytes:

```text
uint32 payloadKind          1 = irradiance, 2 = distance
uint32 texelFormat          1 = RGBA16_SFLOAT, 2 = RG16_SFLOAT
uint32 widthTexels
uint32 heightTexels
uint32 layerCount
uint32 rowPitchBytes
uint64 dataBytes
uint32 flags                = 0 for v1
uint32 reserved             = 0
rawData[dataBytes]
8-byte zero padding
```

For Baseline-v1 DDGI, irradiance payloads must declare `RGBA16_SFLOAT` and distance payloads must declare `RG16_SFLOAT`, matching architecture 024. `rowPitchBytes` is explicit and must be at least the tightly packed row size; readers must not infer padding. v1 does not BC-compress or quantize these payloads. Cache invalidation keys include source/content identity, volume descriptor bytes, renderer build/shader layout identity and required color/encoding version.

## 4. Particle runtime reference-v1

The first semantic particle state is **not** the old ambiguous 48-byte manually packed target. Reference-v1 is explicit:

```text
struct ParticleStateRefV1 serialized fields:
    float32 position[3]
    float32 age
    float32 velocity[3]
    float32 lifetime
    float32 size[2]
    float32 rotation
    float32 angularVelocity
    float32 color[4]
    uint32 materialId
    uint32 flags
    uint32 stableId
    uint32 priority
```

Serialized size = 80 bytes.

`ParticleMaterialRefV1`:

```text
uint32 materialId
uint32 textureIndex
uint32 samplerIndex
uint32 blendMode
uint32 orientationMode
uint32 flags
float32 softness
float32 gravityFactor
float32 drag
float32 emissiveScale
float32 sizeOverLife[4]
float32 colorOverLifeStart[4]
float32 colorOverLifeEnd[4]
```

A later packed GPU format may replace the hot runtime representation after architecture-073 measurement, but it must have an explicit format ID and conversion path from these semantics. No anonymous packed bits are permitted.

## 5. Trace v1

Each trace file starts with an explicit header:

```text
magic[8] = "UFOATR01"
uint32 formatVersion = 1
uint32 headerBytes            = 112 for trace v1
uint32 sourceHashBytes         = 20 for current Git SHA-1 checkout identity
uint32 buildIdBytes            <= 32
uint8  sourceCommitHash[32]    first sourceHashBytes significant, remaining bytes zero
uint8  buildId[32]             first buildIdBytes significant, remaining bytes zero
uint64 monotonicStartNs
uint32 eventTypeTableVersion
uint32 flags
uint32 reserved[2]             = 0
```

Each event record:

```text
uint32 type
uint32 payloadBytes
uint64 timestampNsFromStart
uint32 threadId
uint32 flags
payload[payloadBytes]
padding to next 8-byte boundary
```

`sourceHashBytes` and `buildIdBytes` prevent the file format from assuming one permanent Git-object or ELF-build-ID width. Baseline 031 uses the current checkout's 20-byte Git SHA-1 identity. `sourceCommitHash[0..19]` contains the raw 20 digest bytes decoded from the 40 hexadecimal commit ID, not the ASCII hex characters; ELF GNU build IDs are copied verbatim up to the 32-byte field limit, and a longer identifier requires a new trace-header version rather than truncation. Payload schema is selected by `type` and versioned by the event-type table. Unknown event types can be skipped by `payloadBytes`.

## 6. Replay v1

`.uforeplay` keeps the logical chunks already defined by architecture 048. Reference-v1 chunk envelope:

```text
uint32 fourcc
uint16 major
uint16 minor
uint32 flags
uint32 recordCount
uint64 payloadBytes
uint32 payloadCrc32c
uint32 reserved = 0
payload
8-byte zero padding
```

`payloadCrc32c` is CRC-32C Castagnoli with the exact polynomial/initial/final-XOR parameters from architecture 066 and covers exactly the `payloadBytes` bytes, excluding envelope fields and alignment padding. FourCC serialization follows architecture 066.

Canonical input/event payloads use the existing network/canonical serialization where that is the preservation authority; presentation-only chunks use explicit fields from their owning documents. Replay readers reject incompatible required-major versions and may skip unknown optional chunks.

## 7. Probe/debug capture v1

Probe records use the same replay chunk envelope and carry explicit IDs/coordinates/material/ray/temporal values described by architectures 049–050. Images are stored as separately typed payloads with explicit width, height, row pitch and format enum; no implicit PNG/JPEG requirement is part of the binary ABI.

## 8. Acoustic `ACOU` v1

`AcousticZoneRefV1`:

```text
uint32 zoneId
uint32 environmentPresetId
float32 aabbMin[3]
float32 aabbMax[3]
float32 wetGain
float32 transitionDistance
uint32 priority
uint32 flags
```

`AcousticBvhNodeRefV1`:

```text
float32 aabbMin[3]
float32 aabbMax[3]
uint32 leftChildOrFirstZone
uint32 rightChildOrZoneCount
uint32 flags             bit0 = leaf
uint32 reserved = 0
```

Leaves reference a separate contiguous `uint32 zoneId[]` table.

## 9. Acoustic `APRT` v1

`AcousticPortalRefV1`:

```text
uint32 portalId
uint32 zoneA
uint32 zoneB
uint32 controllingEntityId
float32 center[3]
float32 halfExtents[3]
float32 openTransmission
float32 closedTransmission
float32 highFrequencyTransmission
uint32 flags
uint32 reserved = 0
```

A missing/noninteractive controlling entity uses `0xffffffff` and leaves presentation state authored/static.

## 10. Version evolution

Any compression/quantization/packing change that changes bytes gets a new chunk/format version. Readers must never infer a compact encoding from payload length alone.

## 11. Baseline 034 DDGI enclosure closure

The DDGI records above are the semantic reference-v1 payload records. Baseline 034 accepts `DDGI-CACHE-001` choice B. `RMAP/DDGI` remains static presentation-map placement metadata and must never become mutable runtime history.

The mutable disk envelope is the disposable `RDGI` user-cache container defined by ADR-044 and architecture 088. `RDGI` reuses the common outer container rules from architecture 066 and contains exactly `META`, `VOLM`, `PROB`, `IRAD`, and `DIST` chunks in v1. Missing, stale, mismatched or corrupt cache data is discarded and rebuilt rather than failing canonical content load.
