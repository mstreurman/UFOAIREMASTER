# Exact Presentation RNG Stream Assignments

**Status:** Exact implementation specification  
**Related ADR:** ADR-027, ADR-031  
**Related architecture:** 048, 064, 067

## 1. Primitive

Use architecture-064 Philox4x32-10/Mix32 with:

```text
presentationRandomSeed
frameIndex
domainId
stableElement
sampleOrdinal
substream
```

No mutable global RNG.

## 2. U01

```cpp
float U01(uint32_t word) {
    return float(word >> 8) * (1.0f / 16777216.0f);
}
```

Range [0,1).

## 3. ReSTIR candidate domain

```text
RestirCandidate = 1
stableElement = uint64(pixelY*960 + pixelX)
```

Fresh proposal candidate `i=0..7`:

```text
sampleOrdinal=i
substream=0

word0 alias-table column
word1 alias threshold
word2 shape param 0
word3 shape param 1
```

Fresh weighted-reservoir update:

```text
sampleOrdinal=i
substream=1
word0 -> U01 reservoir selection
word1..3 reserved
```

Temporal reservoir update:

```text
sampleOrdinal=8
substream=1
word0 -> U01 reservoir selection
```

This ordinal is reserved even with no temporal history.

Rect/Disk use word2 low/high U16. Line uses word2 low U16.

Finite Point/Spot sphere:

```text
u=U01(word2)
v=U01(word3)
z=1-2*u
phi=2*pi*v
r=sqrt(max(0,1-z*z))
dir=(r*cos(phi),r*sin(phi),z)
```

Reservoir storage uses architecture-067 oct codec.

## 4. ReSTIR spatial domain

```text
RestirSpatial = 2
stableElement = uint64(pixelY*960 + pixelX)
```

Pattern rotation:

```text
sampleOrdinal=0
substream=0
rotation=word0 & 7
```

Spatial combine neighbor ordinal k=0..3:

```text
sampleOrdinal=k
substream=1
word0 -> U01 reservoir selection
```

Skipped neighbors do not renumber later ordinals.

## 5. ReflectionPrimary

```text
ReflectionPrimary = 3
stableElement = uint64(pixelY*renderWidth + pixelX)
sampleOrdinal = 0
substream = 0
```

ABI-v1:

```text
word0 GGX/VNDF sample X
word1 GGX/VNDF sample Y
word2/3 reserved
```

## 6. ReflectionFilter

```text
ReflectionFilter = 4
```

Reserved in ABI v1. Production temporal/variance/à-trous filtering is deterministic and consumes no RNG here.

## 7. DdgiProbeRay

```text
DdgiProbeRay = 5
stableElement = uint64(volume.firstProbeIndex + localProbeIndex)
sampleOrdinal = rayIndex 0..127
substream = 0
```

```text
word0/1 -> equal-area sphere

z=1-2*U01(word0)
phi=2*pi*U01(word1)
r=sqrt(max(0,1-z*z))
dir=(r*cos(phi),r*sin(phi),z)

word2/3 reserved
```

No mutable/scheduling-dependent probe rotation state.

## 8. VolumetricSample

```text
VolumetricSample = 6
```

Froxel integration:

```text
stableElement = uint64((z*froxelHeight+y)*froxelWidth+x)
sampleOrdinal=0
substream=0

word0/1/2 within-froxel X/Y/Z jitter
word3 phase/sample jitter
```

Coarse directional RT lattice:

```text
stableElement = uint64((z*coarseHeight+y)*coarseWidth+x)
sampleOrdinal=0
substream=1

word0/1/2 within-cell X/Y/Z jitter
word3 reserved
```

## 9. VfxParticle

```text
VfxParticle = 7
```

Continuous emitter:

```text
stableElement = raw 64-bit PresentationEntityId
sampleOrdinal = emitter-local monotonic spawnSequence
substream=0
```

Main assigns spawnSequence deterministically before GPU expansion.

One-shot event:

```text
stableElement = PresentationEvent.sourceSequence
sampleOrdinal = particle ordinal in event
substream=1
```

Particle template consumes words in fixed declared parameter order; changing random-parameter order requires template ABI/version change.

## 10. DebugDiagnostic

```text
DebugDiagnostic = 8
stableElement = requestId
sampleOrdinal = diagnostic ordinal
substream = tool-defined non-production value
```

Must not mutate production history or accepted regression output.

## 11. Stable light lifetime

When needed:

```text
stableElement =
    (uint64(lightGeneration)<<32) |
    uint64(lightId)
```

## 12. Frame index

Use deterministic Presentation/Render frame index recorded/reconstructed by PresentationReplay, not wall-clock/present/completion/job count.

## 13. Quality changes

Changing candidate/ray counts or sample/substream allocation changes replay/settings identity.

## 14. Known-answer tests

Each production domain pins at least one full input tuple and expected Philox words/U01/sample decode results.
