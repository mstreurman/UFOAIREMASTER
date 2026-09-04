# ADR-013 — Preserve Canonical BSP; Compile Separate Presentation Map Assets

**Status:** Accepted  
**Decision type:** Map/runtime asset architecture  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`

## Context

The current BSP is not merely visible geometry.

At the audited source baseline, BSP/map infrastructure provides or carries data used for:

- collision and line/box tracing;
- point contents;
- canonical surface identity and flags;
- routing/pathfinding;
- inline brush models;
- doors/breakables and moving brush geometry;
- random map assembly;
- map entity definitions;
- terrain-dependent gameplay behavior;
- render geometry and legacy lightmaps.

The engine already separates collision loading (`CM_LoadMap`/common BSP) from renderer-side brush-model loading (`R_ModBeginLoading`).

## Decision

The existing UFO:AI BSP/common spatial path remains the canonical tactical map representation.

The remaster replaces the renderer-side map representation, not the canonical collision/routing representation.

A separate offline presentation-map compiler will generate GPU/Jolt-oriented runtime assets from the canonical compiled BSP.

Conceptually:

```text
.map
  |
ufo2map
  |
canonical .bsp
  |------------------------------> canonical common/server path
  |                                  collision
  |                                  routing
  |                                  entity semantics
  |                                  canonical surface behavior
  |
  +--> remaster map compiler
          |
          v
      presentation runtime map asset
          |
          +--> Vulkan geometry/material metadata
          +--> RT geometry metadata
          +--> Jolt presentation collision
```

The later runtime-asset contract resolves this as `.rmap` using the common remaster chunked container defined by architecture 031. This ADR remains authoritative for the canonical-BSP/presentation-map semantic split.

## Source matching

Every compiled presentation-map asset must identify the exact source BSP from which it was generated.

A strong content hash/checksum is required.

A presentation map generated from a different BSP must not be silently paired with the canonical map.

## Random map assembly

Presentation assets are compiled per canonical map tile.

Runtime RMA presentation assembly uses the same tile placement/shift information as the canonical assembly.

Inline model identity must remain traceable across tile assembly and canonical model renumbering.

## Canonical surface semantics

PBR materials do not replace canonical surface semantics.

The canonical path retains:

- BSP texture/surface identity;
- surface/content flags;
- terrain lookup semantics;
- bounce behavior;
- burn behavior;
- any other game-consumed surface property.

Modern render materials are presentation-only mappings from canonical surfaces/material identity.

## Inline brush models

Doors, breakables, rotating entities and other inline brush models remain canonical spatial objects.

Presentation equivalents may use richer meshes/materials, but follow canonical event/state changes.

Jolt is not used to replace canonical brush collision.

## Level/cutaway behavior

Presentation geometry retains tactical-level metadata so raster and RT visibility can honor the current floor/cutaway presentation.

Invisible upper levels must not continue to contribute unwanted RT shadow/reflection/GI visibility.

## Presentation collision

The presentation compiler may generate a separate simplified static collision mesh for Jolt.

It is used only by presentation physics such as ragdolls, debris and loose props.

It is never authoritative for actor movement, projectile results, LOS, cover, routing or pathfinding.

## Entity data

The canonical runtime continues to consume the existing final merged map entity string.

The canonical-vs-presentation entity audit is now source-complete (architecture 010).

Accordingly, `.rmap` may bake only the audited presentation-only/presentation-readable metadata defined by architecture 054.

Canonical entity behavior is never replaced by the bake.

## Consequences

The remaster can radically modernize map rendering without risking canonical routing, traces, collision or map assembly.

It also permits independent GPU optimization of geometry while retaining a provable link to the exact canonical BSP.
