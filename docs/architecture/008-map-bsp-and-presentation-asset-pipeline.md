# Map/BSP Architecture and Presentation Asset Pipeline

**Status:** Source-grounded architecture baseline  
**Related ADR:** `ADR-013-canonical-bsp-presentation-map-split.md`  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`

## 1. Purpose

Define how the remaster modernizes map rendering without changing canonical UFO:AI collision, routing, pathfinding, visibility/tracing or map entity behavior.

This document records the currently verified architectural split.

A complete function-by-function map entity and surface-semantic audit remains planned.

## 2. Existing BSP responsibilities

BSP version 79 currently defines 17 lump categories:

```text
ENTITIES
PLANES
VERTEXES
ROUTING
NODES
TEXINFO
FACES
LIGHTING_NIGHT
LIGHTING_DAY
LEAFS
LEAFBRUSHES
EDGES
SURFEDGES
MODELS
BRUSHES
BRUSHSIDES
NORMALS
```

The container therefore mixes canonical spatial data and presentation data.

## 3. Existing loader split

The current engine already has separate conceptual consumers.

### Canonical/common path

`CM_LoadMap` / `CM_LoadBsp` consume collision/spatial data such as:

```text
TEXINFO
LEAFS
LEAFBRUSHES
PLANES
BRUSHES
BRUSHSIDES
MODELS
NODES
ROUTING
ENTITIES
```

The server/game interface exposes traces, contents, routing and pathfinding based on this data.

### Legacy renderer path

`R_ModBeginLoading` / `r_model_brush.cpp` consume render-oriented data such as:

```text
VERTEXES
NORMALS
EDGES
SURFEDGES
LIGHTING
PLANES
TEXINFO
FACES
LEAFS
NODES
MODELS
```

This existing split is the seam the remaster will strengthen.

## 4. Target architecture

```text
source .map
    |
    v
ufo2map
    |
    v
canonical .bsp
    |
    +------------------------------+
    |                              |
    v                              v
CanonicalMapRuntime          RemasterMapCompiler
common/server                       |
    |                               v
    |                       PresentationMapAsset
    |                               |
    +--> game.so                    +--> Vulkan
                                    +--> RT metadata
                                    +--> Jolt presentation collision
```

There is no presentation-to-canonical feedback path.

## 5. Canonical BSP remains authoritative

Keep the canonical/common map path for:

- line and box traces;
- contents tests;
- grenade canonical collision/trajectory helpers;
- routing/pathfinding;
- actor standability;
- inline model bounds/orientation;
- dynamic routing changes;
- server entity collision;
- canonical surface identity and flags;
- canonical map entity definitions.

## 6. Canonical surface semantics

Do not replace canonical surface identity with PBR material properties.

Verified examples include canonical use of:

- surface flags such as `SURF_BURN`;
- trace-returned texture/surface names;
- terrain lookup;
- grenade bounce fraction.

Architecture:

```text
CanonicalSurfaceSemantics
    |
    +--> gameplay

canonical surface/material mapping
    |
    v
RenderMaterial
    |
    +--> Vulkan/PBR/RT
```

A high-resolution replacement material may look completely different internally while preserving the canonical surface mapping.

## 7. Presentation map asset

The runtime presentation-map asset is now:

```text
.rmap
```

using the common remaster chunked container defined by architecture 031.

Conceptually the compiled runtime asset contains:

```text
header/version/source-BSP hash
tile bounds
static mesh clusters
inline-model presentation meshes
material bindings
surface/source mapping
tactical level masks
RT classification metadata
presentation collision
asset dependencies
```

Do not serialize device-specific Vulkan acceleration structures initially.

Build runtime BLAS/TLAS from optimized RT-ready geometry.

## 8. Source BSP hash

Every presentation asset must record a strong hash of the exact canonical BSP input.

Runtime validation should prevent accidental use of mismatched canonical and presentation map revisions.

Development mode may fall back to legacy presentation, but mismatch must never be silent.

## 9. Random map assembly

The canonical runtime supports map assemblies made from multiple shifted tiles.

The presentation compiler therefore works per tile.

At runtime:

```text
canonical assembly description
        |
        +--> canonical BSP tile shifts
        |
        +--> presentation tile instances using the same shifts
```

Do not invent an independent presentation RMA layout.

## 10. Entity-string behavior

Canonical map loading rewrites/merges entity data for assemblies, including shifted origins, inline-model renumbering and tile-specific target/targetname handling.

For the first remaster implementation, continue consuming this final merged entity string for presentation-side map entities/environment metadata.

Do not independently reconstruct RMA entity semantics in the presentation compiler until the full map-entity audit is complete.

## 11. Entity classes already observed

The game-side map parser includes canonical or gameplay-relevant classes such as:

```text
worldspawn
misc_item
misc_mission
info_* spawn points
func_breakable
func_door
func_door_sliding
func_rotating
trigger_nextmap
trigger_hurt
trigger_touch
trigger_rescue
misc_smoke
misc_fire
misc_smokestun
misc_camera
```

The client-side map parser separately uses presentation classes including:

```text
worldspawn
misc_model
misc_particle
misc_sound
light
```

This is a mixed-authority entity namespace and must be audited before baking it into a new runtime map format.

## 12. Inline brush models

Inline BSP models are preserved as canonical objects for doors, breakables and related entities.

Presentation map compilation emits corresponding separable presentation geometry.

Typical flow:

```text
canonical inline brush model
       |
EV_ADD_BRUSH_MODEL
       |
PresentationEntity
       |
Vulkan mesh
```

Door/breakable presentation follows canonical events.

Jolt never replaces canonical inline-model collision or routing.

## 13. Static geometry replacement policy

### Structural tactical geometry

Walls, floors, stairs, major cover and similar tactical silhouettes should initially preserve BSP geometry closely.

Modernization may add:

- PBR materials;
- high-resolution textures;
- normal/detail maps;
- decals;
- improved shading;
- RT lighting;
- non-authoritative small bevel/detail geometry.

### Rich visual replacement

Some canonical objects may use richer presentation meshes while preserving their canonical anchor and tactical meaning.

### Presentation-only detail

Purely visual detail may include:

- pipes;
- cables;
- trash;
- bolts;
- decals;
- clutter;
- foliage;
- debris.

Presentation-only additions should not visually imply major canonical cover or create deceptive large opaque blockers.

## 14. Tactical levels/cutaway

The legacy renderer filters surfaces by tactical world level.

The presentation asset therefore retains level/cutaway metadata per geometry cluster.

When a level is hidden for presentation, the renderer must apply that state consistently to:

- raster visibility;
- RT instances/masks;
- shadows;
- reflections;
- GI where appropriate.

Canonical LOS/pathfinding is unchanged.

## 15. RT geometry organization

ADR-021 now locks the baseline partition:

```text
tile asset
    × tactical level
    × opacity class
    × spatial chunk when required
```

Static BLAS are tile-local and shared across repeated RMA placements.

Starting static chunk sizing:

```text
target ~65,536 triangles
ceiling ~131,072 triangles
```

with spatial recursive subdivision when the ceiling is exceeded.

Opaque and alpha-tested static geometry remain separate RT classes.

Inline/rigid models use reusable compacted asset BLAS; their movement occurs through TLAS transforms.

Only truly deforming/skinned geometry uses dynamic per-frame BLAS.

## 16. Jolt presentation collision

The presentation compiler may emit simplified static triangle/convex collision for:

- ragdolls;
- shell casings;
- debris;
- loose visual props.

Canonical actor/projectile/LOS/pathfinding systems never query this Jolt world.

## 17. Legacy day/night lightmaps

The current BSP includes day and night lighting data used by the legacy renderer.

The common loader also reads selected light data.

At the audited source commit, `CM_GetVisibility` currently returns `1.0f` and contains a TODO rather than deriving a gameplay visibility factor from the lightmap.

The remaster should still preserve the canonical/common data path.

Vulkan is free to use modern HDR/PBR/RT lighting instead of treating the legacy lightmaps as its primary illumination solution.

## 18. Environment metadata

The current client-side `worldspawn` parser supplies day/night ambient and sun direction/color/intensity inputs.

Initially treat those as presentation environment seed data.

The HDR renderer may reinterpret them into modern physical/presentation lighting without changing canonical tactical rules.

## 19. Offline compiler stages

Conceptual pipeline:

```text
1. verify BSP version/checksum
2. read canonical tile/model/surface identities
3. reconstruct renderable polygons
4. triangulate/optimize
5. preserve source surface mapping
6. partition opaque/alpha/transparent/warp classes
7. preserve tactical level masks
8. split inline models
9. map legacy material identity -> PBR material IDs
10. build GPU-friendly mesh clusters
11. generate RT metadata
12. generate simplified Jolt collision
13. emit dependency table
14. write source-BSP hash
```

## 20. Current open implementation details

Already resolved elsewhere:

```text
presentation-map extension/container -> `.rmap`, architecture 031
PBR material ABI                    -> ADR-017 / architecture 018
BLAS partition contract             -> ADR-021 / architecture 026
```

Still implementation/benchmark-tunable here:

- final mesh attribute/compression choices consistent with architecture 031;
- whether meshlets materially help the accepted renderer;
- benchmark tuning around the accepted static-BLAS chunk thresholds;
- exact non-authoritative Jolt presentation-collision simplifier.

Static map-entity baking authority is already fixed by architecture 010/054: only audited presentation-only or presentation-readable fields may bake, and canonical behavior remains canonical. Source `.map` data may be used only as optional offline presentation/compiler input when bound to the same canonical source identity; runtime correctness may not depend on unbound source-map metadata.

## 21. Historical source-audit requirement — completed

The earlier baseline required a canonical-vs-presentation matrix for:

- all `func_*`;
- all `trigger_*`;
- all `info_*`;
- all `misc_*`;
- worldspawn keys;
- surface/content flags;
- terrain/material definitions;
- dynamic routing effects;
- save/load references to map entities;
- client UI/radar dependencies;
- map-zone/terrain substitutions.

That requirement was the map equivalent of the source-complete tactical event catalog and is now satisfied by the follow-on documents below.

## 22. Source-complete follow-on audit

Baseline 008 adds the source-complete map semantic audit:

- `009-canonical-vs-presentation-map-data-matrix.md`
- `010-map-entity-class-and-field-matrix.md`
- `011-surface-content-terrain-semantics-matrix.md`

Those documents supersede the earlier "required next source audit" as the current source-grounded compatibility baseline.

## Coordinate/scale authority

Architecture 051 owns the presentation coordinate/scale contract.

`remaster-mapc` preserves canonical BSP XYZ numerically in presentation units:

```text
right-handed
+Z up
32 presentation units = 1 meter
```

Jolt/audio conversions occur only after canonical/presentation separation.

## Static entity baking status

Architecture 054 already fixes the authority policy: audited presentation-only/presentation-readable metadata may bake, while canonical entity behavior remains canonical.

Only representation/packing optimization remains open.
