# Static-Key Source Values, GPU Time and ABI Authority Cleanup

**Status:** Exact supporting specification  
**Related ADR:** ADR-031

## 1. StaticRenderKey tilePlacementSequence

For RMA:

```text
tilePlacementSequence =
    zero-based index in canonical assembled CS_TILES / CS_POSITIONS placement-list order
```

Not filesystem, pointer, parallel-completion or independently sorted order.

Monolithic map: zero.

## 2. BspSurface identity value

```text
canonicalIdentityValue =
    uint64(canonical BSP SURFACES-lump surface index)
```

## 3. InlineModelSurface identity value

```text
canonicalIdentityValue =
    (uint64(inlineModelIndex) << 32) |
    uint64(surfaceOrdinalWithinInlineModel)
```

## 4. PresentationOnlyGroup identity value

```text
canonicalIdentityValue =
    (uint64(sourceRecordOrdinal) << 32) |
    uint64(localGroupOrdinal)
```

Source records sort by normalized asset path unsigned UTF-8 bytes, then source record byte offset, then source record type numeric ID.

## 5. Static-key mesh AssetId bytes

Use architecture-066 raw AssetId bytes `digest[0..15]`.

## 6. GpuInstance draw ownership

`GpuInstance` does not own one implicit draw record.

The former `drawDataIndex` word becomes `reserved0 = 0`.

Raster work uses `GpuRasterDrawPassData.drawDataIndex -> GpuSceneRoot.drawData[]`.

One instance may participate in zero, one or many draws.

## 7. Transform lookup

`GpuRtInstanceData.gpuInstanceIndex` references `GpuInstance`.

Current/previous transforms come from `currentWorldFromObject` and `previousWorldFromObject`.

There is no separate transform-index array.

## 8. QueueCompletionValues authority

Architecture 052 is exact owner.

## 9. GpuRtInstanceData authority

Architecture 059 is exact byte-layout owner; architecture 027 owns RT semantics.

## 10. GpuLight authority

Architecture 059 owns exact byte layout; architecture 062 owns field/sample semantics.

## 11. AudioVoiceId authority

Architecture 065 owns exact layout/reuse policy.

## 12. CPU presentation time

Main keeps monotonic `double presentationTimeSeconds`.

## 13. GPU split presentation time

FrameConstants uses:

```text
presentationTimeHighSeconds
presentationTimeLowSeconds
```

CPU generation:

```text
highD =
    floor(cpuPresentationTimeSeconds / 1024.0) * 1024.0

high = float(highD)
low  = float(cpuPresentationTimeSeconds - highD)
```

`0 <= low < 1024`.

## 14. Shader time helpers

Periodic effect period `P`:

```text
phaseTime =
    fmod(
        fmod(presentationTimeHighSeconds, P) +
        presentationTimeLowSeconds,
        P)
```

Non-periodic continuous effects use per-effect local epochs.

Do not use a wrapped global float as a non-periodic absolute clock.

## 15. RNG/identity clocks

Presentation time is not RNG identity, entity/light identity, replay order or canonical time.

## 16. Baseline skin influence status

ABI-v1 baseline:

```text
maximum stored/processed influences = 8
GpuSkinFormat::EightInfluenceU16F32 = 0
```

Only later optimized/compressed representation remains open.

## 17. Map-entity bake status

Architecture 054 already fixes:

```text
audited presentation-only/presentation-readable data may bake
canonical entity behavior remains canonical
```

Only representation/packing optimization remains open.
