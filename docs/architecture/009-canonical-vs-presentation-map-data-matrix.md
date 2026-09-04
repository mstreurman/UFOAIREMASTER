# Canonical vs Presentation Map Data Matrix

**Status:** Source-complete audit baseline  
**Source commit:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Related ADRs:** ADR-013, ADR-014

## 1. Scope and meaning of source-complete

This audit accounts for the current map data paths relevant to the remaster boundary:

- BSP lump categories;
- game-side map entity class registry;
- client-side map entity class registry;
- all recognized game-side map key names;
- all recognized client-side map key names;
- `SURF_*` definitions and observed consumers;
- `CONTENTS_*` definitions and observed consumers;
- terrain runtime fields and consumers;
- inline model / dynamic routing behavior;
- RMA entity remapping behavior;
- radar/tile dependencies;
- campaign save/start dependencies found by source inspection.

"Source-complete" means these current code paths are accounted for at the stated commit.

It does not mean runtime regression tests already exist.

## 2. Top-level data ownership matrix

| Data | Current source owner/consumer | Canonical authority | Presentation replacement policy |
|---|---|---:|---|
| BSP brushes/planes/nodes/leaves | common collision/tracing | Yes | Keep canonical; do not replace with Vulkan/Jolt geometry |
| Routing lump / `Routing` | common/server/grid | Yes | Keep canonical |
| Inline BSP model collision | common/server/game | Yes | Keep canonical |
| Dynamic door/breakable routing | game + common/server | Yes | Keep canonical |
| BSP surface texture name | common trace result; terrain/game lookups | Yes where consumed | Preserve semantic ID/mapping |
| BSP surface flags | common trace result; selected game use | Yes where consumed | Preserve semantic flags |
| BSP visible faces/vertices/normals | legacy renderer | No | Replace with presentation-map meshes |
| BSP day/night lightmaps | legacy renderer; common loads selected data | No current gameplay effect from `CM_GetVisibility` at this commit | May be superseded visually; retain canonical data path |
| Map entity string | common assembly -> game + client | Mixed | Canonical game parser remains; client presentation parser may migrate |
| Worldspawn gameplay temp keys | game | Yes | Keep canonical |
| Worldspawn lighting keys | client renderer setup | No | Migrate to HDR environment data |
| `misc_model` non-solid | client | No | Presentation World |
| `misc_model` solid | game collision + client visual model | Mixed | Preserve game BBOX; replace presentation mesh |
| `misc_particle` | client only | No | Presentation World VFX |
| `misc_sound` | client only | No | OpenAL presentation |
| `light` | client only | No | Vulkan presentation light |
| actor/player spawnpoints | game | Yes | Never bake away as visual-only data |
| mission/rescue/hurt/touch/nextmap triggers | game | Yes | Preserve canonical trigger volumes/logic |
| door/breakable/rotating brush entities | game + client events | Yes for state/collision | Rich presentation allowed; canonical brush state wins |
| radar images and RMA tile placement | UI | Presentation dependency | Preserve until radar replaced |
| map definition / map theme selection | campaign | Yes for mission launch | Keep strategic/canonical selection |
| PBR materials | remaster | No | Presentation-only |
| Jolt static collision | remaster | No | Presentation-only |
| RT BLAS/TLAS | remaster | No | Presentation-only |

## 3. BSP lump matrix

The BSP header contains 17 lump categories.

| Lump | Canonical/common use | Legacy renderer use | Remaster treatment |
|---|---|---|---|
| `LUMP_ENTITIES` | Yes; assembled into final entity string | indirect client entity parser | Keep canonical; presentation consumes final merged string initially |
| `LUMP_PLANES` | Yes; tracing/collision | Yes | Keep canonical; presentation compiler may reconstruct geometry |
| `LUMP_VERTEXES` | No canonical loader use | Yes | Presentation compiler input |
| `LUMP_ROUTING` | Yes | No | Canonical only |
| `LUMP_NODES` | Yes; tracing | Yes | Keep canonical; no need for Vulkan runtime BSP traversal |
| `LUMP_TEXINFO` | Yes; surface names/flags | Yes; UV/material identity | Split semantic vs render-material mapping |
| `LUMP_FACES` | No canonical collision loader use | Yes | Presentation compiler input |
| `LUMP_LIGHTING_NIGHT` | common loads selected data; current visibility function still returns 1 | Yes | Preserve BSP; modern renderer may ignore as primary light source |
| `LUMP_LIGHTING_DAY` | same | Yes | same |
| `LUMP_LEAFS` | Yes | Yes | Canonical collision/tracing; presentation need not preserve runtime BSP leaf traversal |
| `LUMP_LEAFBRUSHES` | Yes | not primary render input | Canonical |
| `LUMP_EDGES` | No canonical loader use | Yes | Presentation compiler input |
| `LUMP_SURFEDGES` | No canonical loader use | Yes | Presentation compiler input |
| `LUMP_MODELS` | Yes; inline models | Yes | Canonical IDs preserved; emit separate presentation model meshes |
| `LUMP_BRUSHES` | Yes | No primary visual path | Canonical |
| `LUMP_BRUSHSIDES` | Yes | No primary visual path | Canonical |
| `LUMP_NORMALS` | No canonical loader use | Yes | Presentation compiler input |

## 4. Map assembly / RMA contract

The current common loader rewrites assembled entity data.

Observed transforms include:

- origin values are shifted by the tile placement;
- inline `model "*N"` references are renumbered by previously loaded inline model count;
- `target` and `targetname` are suffixed with tile identity to prevent collisions;
- inline model bounds/origin handling accounts for tile shifts.

Therefore the presentation runtime must use the same assembled tile placement and the same canonical inline-model identity mapping.

A presentation compiler may work per tile, but the runtime assembly description is canonical input.

## 5. Inline model and routing contract

Canonical inline brush models include doors, breakables, rotating entities and trigger brush geometry.

Canonical code:

- assigns `SOLID_BSP`;
- links brush entities into the server world;
- obtains inline-model AABBs;
- updates inline-model orientation;
- recalculates routing when doors move;
- recalculates routing after breakables are removed;
- recalculates visibility around door changes.

Presentation code may animate richer geometry, but cannot substitute Jolt or RT geometry for these operations.

## 6. Tactical-level / cutaway contract

Legacy rendering uses tactical world-level filtering.

Presentation geometry must retain enough level membership metadata to ensure a hidden upper level is consistently hidden from:

- raster primary visibility;
- RT instance visibility;
- shadow rays where presentation requires;
- reflections;
- GI;
- presentation occlusion.

This does not change canonical LOS/pathfinding.

## 7. Lighting contract

The BSP carries day and night lightmaps.

The common path loads the selected lighting lump, and `GetVisibility` is exposed to the game.

At this exact commit, `CM_GetVisibility` returns `1.0f` and contains a TODO rather than computing a darkness-based gameplay modifier.

Therefore modern HDR/RT lighting may diverge significantly from legacy lightmaps without currently changing the returned gameplay visibility value.

The canonical/common lightdata path should still be preserved unless a separate canonical gameplay change is intentionally approved.

## 8. Map-zone terrain texture substitution

Campaign battle startup sets `sv_mapzone`.

The legacy render loader substitutes `tex_terrain/dummy` with a map-zone-specific presentation texture.

This substitution is renderer-side.

Canonical trace surfaces retain their canonical BSP surface identity.

The remaster should treat map-zone substitution as a presentation material binding, not rewrite canonical surface semantics.

## 9. Radar/UI dependency

The current radar:

- consumes `CS_TILES`;
- consumes `CS_POSITIONS`;
- uses `cl.mapData->mapBox`;
- retains per-RMA-tile grid placement;
- loads level-specific images named approximately `pics/radars/<tile>_<level>.<ext>`;
- supports multiple tactical levels;
- derives map-space placement from tile/grid dimensions.

Presentation-map work must preserve canonical tile names/positions and radar compatibility until the radar implementation is deliberately replaced.

## 10. Campaign/save boundary

Campaign battle startup performs `game_quicksave` before the tactical map command.

Campaign mission save data includes a `mapDefId` reference and strategic mission state.

No tactical map-entity/BSP-state save/load serializer was found in the audited `src/game` path.

Therefore:

```text
campaign save
    !=
serialized Presentation World
    !=
serialized tactical BSP entity runtime
```

The remaster Presentation World must remain outside canonical campaign save data.

## 11. Required runtime mapping table

A future compiled presentation map should preserve at least:

```cpp
struct CanonicalMapBinding {
    TileId canonicalTile;
    InlineModelId canonicalInlineModel;   // optional
    SurfaceId canonicalSurface;           // optional
    MapEntityNumber canonicalMapEntity;   // optional
};
```

Exact types are not locked.

The key requirement is traceability from structural presentation assets back to canonical source identity.

## 12. Validation invariants

1. A presentation map cannot load against the wrong BSP hash.
2. A presentation door cannot exist without a canonical inline-model binding.
3. A PBR material change cannot modify canonical bounce/burn/footstep semantics.
4. A Jolt collision mesh cannot be queried for canonical gameplay.
5. RMA tile transforms cannot be independently invented by presentation code.
6. Presentation-only detail cannot alter routing or map triggers.
7. Tactical-level hiding must not mutate canonical map geometry/state.
8. Radar compatibility must be preserved until intentionally replaced.
