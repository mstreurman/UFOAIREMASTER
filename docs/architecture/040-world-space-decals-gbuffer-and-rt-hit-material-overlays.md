# World-Space Decals, G-Buffer Application and RT-Hit Material Overlays

**Status:** Implementation specification baseline  
**Related ADR:** ADR-025

## 1. Decal types

Persistent world decals include:

```text
blood
bullet/impact marks
scorch
alien fluid
burn marks
floor/wall stains
presentation-only structural damage markings
```

## 2. Baseline capacities

```text
world decals:
    4096

attached/moving decals:
    1024
```

These are renderer starting capacities.

## 3. Decal record

Conceptual:

```cpp
struct GpuDecal {
    float worldToDecal[12];

    uint32_t materialIndex;
    uint32_t stableDecalId;
    uint32_t packedLayerPriority;
    uint32_t flags;

    uint32_t ownerRenderObjectId;
    uint32_t tacticalLevel;
    float age;
    float lifetime;
};
```

Exact runtime packing remains shader-ABI work.

## 4. Decal flags

At minimum:

```text
AffectsBaseColor
AffectsNormal
AffectsRoughness
AffectsMetalness
AffectsAO
Emissive
Attached
RtVisible
Persistent
```

## 5. G-buffer order

Material decals execute immediately after opaque/alpha-mask G-buffer construction:

```text
GBuffer
    ->
MaterialDecals
    ->
RT shadows / local direct / DDGI
    ->
DeferredLighting
```

This allows direct lighting to use the decal-modified material state for primary visible surfaces.

## 6. Projector volume

Render an oriented unit box around each decal.

Per fragment:

```text
sample primary depth
    ->
reconstruct world position
    ->
transform to decal-local space
    ->
inside projector?
    ->
evaluate decal material
```

## 7. G-buffer modifications

Allowed:

```text
G0:
    base color
    metalness

G1:
    final shading normal

G2:
    roughness
    AO
```

Not modified:

```text
Depth
G3 motion
G4 object ID
```

A decal is material appearance on existing geometry, not new canonical/renderer object identity.

## 8. Normal blending

Use a defined normal-overlay method appropriate to tangent/world-space decal projection.

Do not linearly interpolate decoded normals without normalization/appropriate compositing.

Exact method is finalized with shader implementation/visual tests.

## 9. Decal ordering

Deterministic order:

```text
layer
priority
stableDecalId
```

Do not let CPU job completion or GPU append order define overlapping decal appearance.

## 10. Decal spatial index

Persistent significant decals are inserted into a bounded world-space decal lookup structure.

Exploit tactical spatial organization:

```text
tactical cell
+
tactical level
    ->
compact candidate decal range/list
```

A decal overlapping multiple cells may appear in each affected bucket.

## 11. RT-hit decal evaluation

At reflection/DDGI material reconstruction:

```text
world hit position
    ->
tactical cell/level
    ->
candidate decals
    ->
projector containment test
    ->
ordered material overlay
```

This keeps significant decal appearance consistent when seen in RT reflections or used at GI hits.

## 12. RT bounds

Starting limits:

```text
maximum RtVisible candidates/cell:
    8

maximum applied overlays/hit:
    4
```

If a cell exceeds the candidate cap, retain highest-priority/significant decals deterministically.

Tiny low-value impact marks need not be `RtVisible`.

## 13. RT-visible selection

Good candidates:

```text
large blood pools
major scorch/burn marks
large alien fluid stains
high-contrast persistent story/environment decal
```

Often excluded:

```text
tiny bullet marks
small cosmetic dirt
short-lived low-value marks
```

This bounds reflection/DDGI shader cost.

## 14. Emissive decals

Emissive material overlay is split:

```text
material component:
    G-buffer modification

emissive radiance:
    separate SceneColor contribution
```

No full-screen emissive G-buffer is introduced.

Emissive contribution remains linear ACEScg.

For an `RtVisible` emissive decal, RT-hit decal evaluation returns the same overlay emissive radiance term as part of reconstructed hit material state.

Reflections/DDGI therefore do not see an otherwise glowing persistent decal as non-emissive merely because the hit is secondary.

## 15. Attached decals

A decal attached to a rigid moving presentation object stores:

```text
owner RenderObjectId
owner-local projector transform
```

Its current world projector derives from the owner's presentation transform.

No canonical state changes.

Skinned-surface attached decals are not part of the first baseline unless a robust skin attachment representation is implemented.

## 16. Lifetime/eviction

Decals may be:

```text
persistent for mission
timed
fade-out
priority-evictable
```

When pool pressure occurs:

```text
old low-priority decals
    evict before important fresh/high-priority decals
```

Stable IDs prevent ordering changes during compaction.

## 17. Cutaway

Decal presentation visibility follows the underlying tactical-level/world geometry.

Hidden level:

```text
decal is not rasterized
```

When visible again:

```text
remaining-lifetime decal appears at correct world location
```

Timed decals continue ageing while hidden.

## 18. Debug

Required:

```text
decal projector volumes
layer/priority
RtVisible flag
cell candidate lists
candidate overflow
applied RT overlays
owner/attached state
lifetime/age
```
