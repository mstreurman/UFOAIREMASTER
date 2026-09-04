# Deterministic Presentation Commit and Static Render Identity

**Status:** Exact implementation specification  
**Related ADR:** ADR-011, ADR-021, ADR-028, ADR-029

## 1. Goal

Exact presentation regression requires stable identity/order that does not depend on worker completion timing.

## 2. Structural command stamp

Every deferred structural command carries:

```cpp
struct PresentationMutationStamp {
    uint64_t sourceSequence;
    uint32_t sourceEntityKey;
    uint16_t phase;
    uint16_t ordinal;
};

static_assert(sizeof(PresentationMutationStamp) == 16);
```

## 3. `sourceSequence`

For canonical-derived work:

```text
sourceSequence = monotonically increasing PresentationEvent sequence
```

assigned on Main during event decode.

For deterministic presentation-only scheduled work:

```text
sourceSequence
```

is assigned on Main before jobs are dispatched from a deterministic subsystem/frame sequence.

Workers never invent a global sequence from completion order.

## 4. `sourceEntityKey`

Use the stable canonical/presentation source entity key when one exists.

For global commands use zero.

## 5. `phase`

Baseline:

```text
0 Destroy/retire
1 Create
2 Add/remove structural component
3 Relationship/attachment
4 Post-create presentation registration
```

Within one logical source event, producer code assigns deterministic `ordinal`.

## 6. Merge/commit

Main:

```text
collect per-worker command buffers
stable-sort lexicographically by:
    sourceSequence
    sourceEntityKey
    phase
    ordinal
apply commands
allocate stable presentation identities
```

Duplicate complete stamps are a developer error unless the command type explicitly permits a deterministic secondary key.

## 7. Identity allocation after ordering

The sorted commit order controls allocation of:

```text
Presentation EntityId slots
RenderObjectId
LightId slots when new slots are required
AudioEmitterId slots where created through presentation structure
```

Worker completion order is irrelevant.

## 8. Static map identity

Static `.rmap` geometry is registered before ordinary dynamic Presentation World render objects for a tactical presentation world.

`remaster-mapc` emits one deterministic `StaticRenderKey` per raster/RT identity group.

The exact key type, versioned little-endian source tuple, BLAKE3-256 derivation and collision policy are owned by architecture 064.

The serialized key is stable for identical canonical/presentation content.

## 9. Static identity granularity

A static identity group must not merge geometry that needs independent temporal/object identity.

Default:

```text
one RenderObjectId per emitted static raster/RT identity group
```

The compiler may group triangles only when they share:

```text
same stable canonical/presentation identity
same tactical-level/cutaway lifetime
same static transform lifetime
```

Material equality alone is not sufficient to merge identity.

## 10. Static runtime allocation

Main sorts static identity groups by serialized `StaticRenderKey`, then allocates monotonic `RenderObjectId`s.

This occurs before dynamic render-object allocation.

## 11. Raster identity

Every raster draw carries an explicit:

```text
GpuDrawData.renderObjectId
```

G-buffer G4 writes that value.

Dynamic/rigid draws normally copy the owning instance's `RenderObjectId`.

Static draws use the static identity-group ID.

## 12. RT identity override

`GpuRtGeometryData.renderObjectIdOverride`:

```text
0xffffffff
    use GpuRtInstanceData.renderObjectId

valid ID
    use this geometry-level identity
```

Static map RT geometries use the override.

Rigid/dynamic object geometries normally use invalid override and inherit the instance ID.

## 13. Static TLAS instance identity

A static BLAS/TLAS partition may contain multiple geometry-level render IDs.

Therefore:

```text
GpuRtInstanceData.renderObjectId
```

for such a partition may be invalid if every emitted geometry supplies a valid override.

Temporal hit identity uses the resolved geometry/instance value, not the BLAS chunk identity.

## 14. Reflection history

Secondary-hit history records the resolved hit `RenderObjectId`.

A sharp-reflection history match therefore means the same static identity group or same dynamic object lifetime, not merely the same BLAS partition.

## 15. Replay regression

Presentation structural regression hashes:

```text
sorted structural command sequence
allocated IDs
stable static identity mapping
RenderSnapshot semantic identities
```

The same replay/build/content must produce the same ordering and IDs on the reference platform.

## Identity batching boundary

Architecture 064 makes the batching implication explicit:

```text
one raster GpuDrawData = one RenderObjectId identity group
one RT geometry identity override = one RenderObjectId identity group
```

Material/pipeline equality may not merge different temporal/object identities into one identity-bearing draw/RT geometry entry.
