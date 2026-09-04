# ADR-014 — Canonical Map Semantic Compatibility Contract

**Status:** Accepted  
**Decision type:** Canonical map preservation / presentation-map migration  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`

## Context

The map/BSP source audit shows that canonical map meaning is distributed across more than collision polygons.

Current tactical behavior depends on:

- compiled routing;
- BSP content masks;
- canonical trace results;
- canonical surface texture identity;
- selected surface flags;
- terrain definitions;
- inline brush-model state;
- map entity definitions;
- random-map-assembly remapping;
- tactical level/floor structure;
- mission/spawn/trigger entities.

The client separately consumes some of the same map entity data for purely visual/audio environment setup.

## Decision

The remaster presentation-map pipeline may replace visual representation, but must preserve a stable mapping to all current canonical map semantics.

The compatibility contract is:

1. The canonical BSP/common map runtime remains authoritative.
2. The presentation map is always derived from and hash-matched to a specific canonical BSP.
3. Canonical surface identity is retained even when a different PBR material is rendered.
4. Canonical content masks are never inferred from presentation geometry.
5. Canonical terrain lookup remains keyed from the canonical trace/surface identity.
6. Canonical inline brush-model identity remains stable across RMA assembly.
7. Door/breakable/rotating presentation follows canonical inline-model events and state.
8. Dynamic routing changes remain driven by canonical brush-model state, not Jolt.
9. Map entity classes with gameplay semantics remain parsed by the canonical game path.
10. Client-only map entities may migrate to Presentation World only after preserving the existing final merged entity-string semantics.
11. Radar/tile identity and tactical-level presentation dependencies remain valid until the UI/radar implementation is deliberately replaced.
12. Presentation-only geometry and materials may not become sources for canonical pathfinding, LOS, cover, projectile collision, grenade bounce, burnability, mission triggers, rescue zones or spawn logic.

## Important source findings

At the audited source commit:

- the game-side spawn table recognizes 27 map entity class names;
- the client-side presentation parser handles five of those names directly;
- the game field parser recognizes 33 keys, including `light`, `maxteams` and `maxlevel` as intentionally ignored game-side fields;
- the client field table contains 31 unique parsed keys;
- `maxteams` is parsed into a client member that is not the `maxMultiplayerTeams` member consumed by `SP_worldspawn`, while `maxMultiplayerTeams` is initialized to `TEAM_MAX_HUMAN`;
- `SURF_BURN` has a direct canonical combat consumer;
- `SURF_FOOTSTEP` is an authoring/compiler marker; runtime footsteps are looked up by canonical surface texture name through terrain definitions;
- `SURF_SLICK` has no direct runtime gameplay consumer in the audited tree despite its comment;
- `CONTENTS_WATER`, `CONTENTS_PASSABLE`, clipping masks and canonical collision masks have runtime/common/game effects;
- campaign tactical startup performs a quicksave before entering the battlescape;
- campaign mission persistence stores a map-definition ID, while no tactical map-entity save/load path was found in `src/game` at this commit.

## Consequence

The future remaster map compiler must emit a semantic mapping table, not only GPU mesh data.

Presentation-map validation should be capable of answering:

```text
Which canonical BSP/tile/model/surface/entity produced this presentation object?
```

for all structurally important map objects.
