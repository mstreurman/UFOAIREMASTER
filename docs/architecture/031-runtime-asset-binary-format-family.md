# Runtime Asset Binary Format Family

**Status:** Implementation specification baseline  
**Related ADR:** ADR-022  
**Runtime platform:** Fedora 44 x86-64, little endian

## 1. Runtime file family

```text
.rshader
.rmesh
.rskel
.ranim
.rmat
.rmap
.rui
.ktx2
```

Future packaging may add:

```text
.rpak
```

without changing the individual asset payload formats.

## 2. No custom texture container

Textures use KTX2.

Baseline GPU texture payloads:

```text
base color:
    BC7 SRGB

emissive:
    BC7 SRGB

normal:
    BC5 UNORM

ORM:
    BC7 UNORM
```

KTX2 owns:

```text
mip hierarchy
compressed image payload
texture dimensions/layers/faces
```

Engine metadata referring to textures remains in `.rmat` or other engine assets.

## 3. Common `.r*` container

Architecture 066 is the exact v1 authority for:

```text
RemasterAssetHeaderV1
RemasterAssetChunkV1
chunk flags/storage encoding
container alignment/bounds
CRC32C
NormalizeAssetPathV1 / AssetId128
ContentHash256 / SourceHash256
```

This document defines asset-family/chunk semantics built on that common container.

## 4. Common identity summary

All cross-asset references use architecture-066 exact identities.

No runtime descriptor index, CPU pointer or Vulkan handle is serialized.

## 5. Compression

Individual chunks may be:

```text
Uncompressed
Zstd
```

starting baseline.

GPU-native BC image data remains in KTX2 and is not wrapped in generic `.r*` chunk compression.

Small chunks may remain uncompressed.

Exact Zstd level is a build-time performance/size choice.

## 6. Runtime parsing rule

Loader validates before exposing data:

```text
magic
major version
file size
chunk table bounds
chunk bounds
chunk alignment
integer overflow
CRC where enabled
content hash according to validation mode
```

Never trust offsets from an asset file without bounds validation.

## 7. `.rmesh`

Magic:

```text
RMSH
```

Required/typical chunks:

```text
META
SECT
POS0
NRM0
TAN0
TEX0
IDX0
BBOX
RTMD
DEPS
```

Skinned optional:

```text
JNT0
WGT0
SKEL
```

Additional UV/color streams may be added through new optional chunks.

## 8. Mesh stream policy

Prefer structure-of-arrays streams.

RT can consume:

```text
POS0
IDX0
```

without fetching unrelated tangent/UV/skin streams.

Baseline positions:

```text
float32 XYZ
```

Indices:

```text
uint16 when legal
uint32 otherwise
```

The stream metadata explicitly records type/stride/count.

## 9. Mesh sections

`SECT` records:

```text
index range
vertex/base references
material AssetId
material slot
bounds
opacity class
render flags
RT participation flags
```

A section is the primary material/RT metadata unit.

## 10. RT metadata

`RTMD` records enough information for offline/runtime BLAS partitioning and `GpuRtGeometryData` construction.

At minimum:

```text
geometry section index
opacity class
position stream/index stream references
primitive range
material dependency
tactical-level membership where relevant
```

Map-level partitioning may additionally live in `.rmap`.

## 11. `.rskel`

Magic:

```text
RSKL
```

Chunks:

```text
META
JONT
REST
IBND
SOCK
NAME
DEPS
```

Contains:

```text
joint parent hierarchy
stable joint IDs
rest local TRS
inverse-bind matrices
numeric socket IDs
optional debug/source names
```

Runtime animation output remains FP32 3x4 skin matrices as already specified.

## 12. `.ranim`

Magic:

```text
RANM
```

Chunks:

```text
META
CLIP
TRAK
ROTA
TRAN
SCAL
EVNT
DEPS
```

Semantic format is locked.

Reference-v1 is the dense unquantized format fixed by ADR-039 / architecture 085. A future compact version may benchmark quantized encodings such as:

```text
rotation:
    smallest-three quaternion encoding

translation:
    per-track quantized bounds

scale:
    per-track quantized bounds

time:
    quantized normalized/sample times
```

Decoder layout should remain friendly to the i9-9900K AVX2 8-joint processing baseline.

## 13. `.rmat`

Magic:

```text
RMAT
```

Disk material is not `GpuMaterial`.

It stores stable asset references and authoring-independent runtime properties:

```text
baseColorTexture AssetId
normalTexture AssetId
ormTexture AssetId
emissiveTexture AssetId

sampler definition/ID
material class
material flags

baseColorFactor
emissiveFactor
emissiveStrength
roughnessFactor
metallicFactor
normalScale
occlusionStrength
alphaCutoff
IOR
specularFactor
```

## 14. Material runtime patching

Load:

```text
.rmat
    |
resolve KTX2 dependencies
    |
allocate/lookup global descriptor-table entries
    |
construct 96-byte GpuMaterial
    |
upload GpuMaterial
```

Runtime descriptor indices never appear in `.rmat`.

## 15. `.rmap`

Magic:

```text
RMAP
```

`.rmap` is a presentation companion to canonical BSP.

Required identity includes:

```text
source/canonical BSP strong hash
map compiler version
runtime format version
```

Typical chunks:

```text
META
BSPH
TILE
LEVL
SURF
MATB
GEOM
RTPT
INLN
LITE
DDGI
CUTW
ACOU
APRT
VFXP
DEPS
```

## 16. `.rmap` semantics

Contains presentation-only:

```text
surface -> PBR material binding
render geometry
tactical-level presentation grouping
RT BLAS partition metadata
cutaway presentation grouping
inline-model render metadata
presentation static lights
DDGI volume/probe placement descriptors
acoustic zones/environment presets
acoustic portal relationships
presentation VFX placement/preset references where map-authored
canonical surface semantic references
```

Does not contain authoritative replacements for:

```text
collision
routing
pathfinding
LOS
damage
canonical entity state
```

## 17. RMA reuse

Tile `.rmap` data is tile-local.

Repeated RMA placements use:

```text
same .rmap tile asset
same tile-local static BLAS data/build
different placement transform
```

matching ADR-021.

## 18. `.rshader`

Magic:

```text
RSHD
```

Detailed by architecture document 029.

It uses the same common asset container.


## 19. `.rui`

Magic:

```text
RUI0
```

Compiled retained UI package.

Detailed by architecture documents 043-046.

Typical chunks:

```text
META
TREE
STYL
LAYO
BIND
ACTN
TEXT
IMAG
ANIM
DEPS
```

Optional compatibility:

```text
LEGC
```

Contains renderer-neutral UI hierarchy/layout/style/binding/action metadata.

Does not contain:

```text
raw game pointers
uiNode_t pointers
Vulkan handles
OpenAL handles
```


## 20. Versioning

Major version change means incompatible parser/layout semantics.

Minor version may add:

```text
optional chunks
optional flags
new metadata ignored safely by older compatible readers
```

A runtime never guesses compatibility after an unknown major version.

## 21. Build dependency graph

Offline tools compute:

```text
source paths
dependency AssetIds
dependency content/source hashes
compiler/tool version
build options
```

and use them for incremental rebuilds.

## 22. Runtime asset states

Conceptual:

```text
Unloaded
LoadingCpu
ReadyCpu
UploadingGpu
ReadyGpu
Failed
Retiring
```

GPU readiness includes queue timeline `ReadyToken`.

## 23. File I/O baseline

Start with conventional Linux file/page-cache access:

```text
open
mmap or pread/read
validate
decompress needed chunks
stage/upload
```

Do not require `io_uring` or direct I/O in the architecture.

They may be benchmarked later.

## 24. Optional package layer

Future `.rpak` may bundle individual runtime assets for distribution/locality.

It must preserve:

```text
AssetId
individual content hashes
individual asset-version semantics
```

The first implementation may load loose compiled assets.

## 25. Migration tools

Legacy UFO:AI formats and modern interchange formats may be parsed by:

```text
offline importers
conversion utilities
asset compiler plugins
```

not by the production renderer/runtime loader.

## 26. Remaining tuning, not ABI blockers

Architecture 085 now fixes reference-v1 `.ranim` and DDGI persisted representations. Still benchmark/distribution-tunable:

```text
final Zstd compression levels
optional .rpak format
some future mesh/animation compact encodings
```

Any compact successor must use a new explicit format/chunk version.

## Runtime texture orientation

Architecture 060 owns the canonical runtime texture convention:

```text
UV (0,0) top-left
+U right
+V down
normal-map +Y along tangent-space B
```

Offline tools normalize source images/UVs/normal-map green channels into this convention.

Runtime KTX2 sampling performs no hidden source-format flip.

## Static render identity metadata

For map/static presentation geometry, `RTMD`/`.rmap` also carries the deterministic static render-identity grouping/key required by architecture 058.

Material equality alone is not a sufficient identity grouping condition.

## Skin-stream GPU binding

`.rmesh` `JNT0`/`WGT0` resolve into the joint-index/weight addresses and strides consumed by architecture-059 `GpuMesh`/`GpuSkinningJob`.

ABI-v1 supports exactly eight stored/processed influences per vertex as fixed by architecture 063. Only a future, separately versioned compression/packing representation remains a content-pipeline decision; the GPU binding is exact.

## Exact static identity key

Architecture 064 owns the exact 32-byte `StaticRenderKey` BLAKE3-256 derivation.

`.rmap` static identity metadata stores that exact key for deterministic runtime sort/RenderObjectId allocation.

## Baseline runtime skin format

Architecture 063 locks the first runtime-expanded skin format:

```text
GpuSkinFormat::EightInfluenceU16F32 = 0

joint stream:
    8 x uint16 = 16 bytes/vertex

weight stream:
    8 x float32 = 32 bytes/vertex
```

Later compressed formats may be added without changing the existing value zero.

## Asset identity/hash open-status

Asset path case/Unicode normalization, AssetId mapping, common container layout, CRC coverage, ContentHash and SourceHash are no longer open.

Architecture 066 is exact authority.

## Baseline runtime texture residency

Architecture 074 owns first-version runtime texture residency.

A texture publishes one immutable live persistent sampled-image heap view containing its baseline required mip set.

The first implementation does not promise live per-mip eviction/streaming.

Future partial/sparse mip residency requires an explicit new contract rather than being implied by the common `.r*` asset container.

## Baseline 031 reference-format closure

ADR-039 and architecture 085 define dense unquantized `.ranim` v1 and explicit DDGI reference-v1 persisted records. Later compression is versioned and benchmark-gated.
