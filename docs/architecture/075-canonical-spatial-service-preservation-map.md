# Canonical Spatial-Service Preservation Map

**Status:** Source-grounded implementation contract  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Primary authorities:** ADR-001, ADR-014, architecture 001, architecture 008–011

## 1. Purpose

This document closes the source-boundary gap identified as `M029-001` in the Baseline 029 completeness audit.

The remaster may replace presentation technology, but it must not accidentally replace gameplay-authoritative spatial behavior with Vulkan RT, Jolt, GPU visibility, presentation navigation or other rendering/physics data.

This map identifies the canonical spatial service boundary at the audited UFO:AI source revision and defines the migration rule for every service exposed through `game_import_t`.

## 2. Source authority

At the audited source revision, `src/game/game.h` defines `game_import_t`. The host/server populates that interface in `src/server/sv_game.cpp::SV_InitGameProgs()`.

The important architectural consequence is:

```text
src/game canonical rules
    -> game_import_t spatial request
    -> server/common canonical spatial implementation
    -> canonical answer returned to game
```

The physical source directory containing a function does not decide authority. A service is canonical when the game rules consume it to determine movement, LOS/visibility, collision, trajectory, reachability or other gameplay outcomes.

## 3. Exact host wiring at the audited revision

`SV_InitGameProgs()` wires the spatial portion of `game_import_t` as follows:

| `game_import_t` member | Audited host implementation | Canonical responsibility |
|---|---|---|
| `Trace` | `SV_Trace` | swept/line collision against canonical map/entity state |
| `LinkEdict` | `SV_LinkEdict` | publish canonical entity collision/spatial state |
| `UnlinkEdict` | `SV_UnlinkEdict` | remove canonical entity collision/spatial state |
| `TestLine` | `SV_TestLine` -> `TR_TestLine` | canonical map line test |
| `TestLineWithEnt` | `SV_TestLineWithEnt` -> `CM_EntTestLine` | canonical line test including entities |
| `GrenadeTarget` | `Com_GrenadeTarget` | canonical grenade/throw trajectory solution |
| `GridCalcPathing` | `SV_GridCalcPathing` -> `Grid_CalcPathing` | canonical reachable-path field calculation |
| `GridFindPath` | `SV_GridFindPath` -> `Grid_FindPath` | canonical path search |
| `MoveStore` | `Grid_MoveStore` | canonical path/movement-state storage |
| `MoveLength` | `Grid_MoveLength` | canonical movement cost/path length |
| `MoveNext` | `Grid_MoveNext` | canonical path traversal step |
| `GetTUsForDirection` | `Grid_GetTUsForDirection` | canonical TU movement cost |
| `GridFall` | `SV_GridFall` -> `Grid_Fall` | canonical grid-floor/fall result |
| `GridPosToVec` | `SV_GridPosToVec` -> `Grid_PosToVec` | canonical grid/world conversion |
| `isOnMap` | `SV_GridIsOnMap` | canonical map bounds test |
| `GridRecalcRouting` | `SV_RecalcRouting` -> `Grid_RecalcRouting` | canonical dynamic routing update |
| `CanActorStandHere` | `SV_CanActorStandHere` -> `RT_CanActorStandHere` | canonical standability |
| `GridShouldUseAutostand` | `Grid_ShouldUseAutostand` | canonical movement posture helper |
| `GetVisibility` | `SV_GetVisibility` | canonical tactical visibility metric |
| `PointContents` | `SV_PointContents` | canonical point/content classification |
| `SetInlineModelOrientation` | `SV_SetInlineModelOrientation` | canonical dynamic inline-model spatial orientation |
| `GetInlineModelAABB` | `SV_GetInlineModelAABB` | canonical inline-model bounds |
| `LoadModelAABB` | `SV_LoadModelAABB` | canonical model bounds used by game/server logic |

This table is the migration checklist. A remaster implementation must preserve each function's semantic result unless a separately accepted gameplay ADR explicitly changes it.

## 4. Confirmed canonical consumers

The audited source contains direct game-side consumers including:

| Service | Representative canonical consumers at `763173ed...` |
|---|---|
| `Trace` | `src/game/g_utils.cpp` trace wrapper used by game logic |
| `PointContents` | `src/game/g_actor.cpp` actor content/position logic |
| `TestLine`, `TestLineWithEnt` | `src/game/g_utils.cpp` canonical visibility/line-test helpers |
| `GrenadeTarget` | `src/game/g_ai.cpp`, `src/game/g_combat.cpp` |
| `GridCalcPathing`, `GridFindPath` | `src/game/g_move.cpp` |
| `MoveStore` | `src/game/g_ai.cpp`, `src/game/g_ai_lua.cpp` |
| `MoveLength` | `src/game/g_move.cpp`, `src/game/g_ai.cpp`, `src/game/g_ai_lua.cpp` |
| `MoveNext` | `src/game/g_move.cpp`, `src/game/g_ai.cpp`, `src/game/g_ai_lua.cpp` |
| `GetTUsForDirection` | `src/game/g_move.cpp` |
| `GridFall` | `src/game/g_spawn.cpp`, `src/game/g_move.cpp` |

The list above is intentionally representative of direct `gi.*` consumers rather than a claim that only those files are semantically affected. Higher-level game functions transitively depend on them.

## 5. Preservation classes

### 5.1 Exact-result services

The following are treated as exact canonical behavior for a given canonical state/input:

```text
PointContents
TestLine
TestLineWithEnt
GridCalcPathing
GridFindPath
MoveStore
MoveLength
MoveNext
GetTUsForDirection
GridFall
GridPosToVec
isOnMap
GridRecalcRouting
CanActorStandHere
GridShouldUseAutostand
GetVisibility
```

Optimization may change implementation, data layout or threading, but not gameplay-visible results.

### 5.2 Geometric-query services

```text
Trace
SetInlineModelOrientation
GetInlineModelAABB
LoadModelAABB
LinkEdict
UnlinkEdict
```

These remain tied to canonical BSP/entity collision semantics. Presentation BVHs/TLAS/Jolt bodies may mirror them but cannot substitute for them.

### 5.3 Canonical trajectory service

`GrenadeTarget` remains the authoritative throw/launch calculation used by AI and combat. A Jolt projectile, GPU trajectory preview or presentation spline may visualize the result but cannot determine the canonical outcome.

The audited `Com_GrenadeTarget` source contains an old TODO questioning the naming/meaning of its `speed`/`fireDef.range` parameter. That TODO is **not** permission to fix behavior during presentation migration. Any gameplay correction requires its own canonical-gameplay change decision and regression tests.

## 6. Required remaster layering

```text
CanonicalSpatial
    owns:
        BSP collision/content
        entity linking
        routing/pathfinding
        gameplay visibility
        canonical trajectory queries

PresentationSpatial
    may own:
        render BVH/TLAS
        acoustic BVH
        Jolt bodies
        particle/debris collision proxies
        GPU culling structures
        UI/world picking helpers
```

One-way synchronization is allowed:

```text
CanonicalSpatial -> PresentationSpatial
```

The reverse direction is forbidden for authoritative decisions.

## 7. Dynamic inline models and doors

Dynamic inline-model state is a particularly important parity point.

Canonical door/breakable/mover state may trigger:

```text
canonical inline-model transform/routing update
    +
presentation render transform/TLAS update
    +
presentation acoustic portal/occluder update
    +
optional Jolt presentation proxy update
```

These updates share the same canonical event/state source but remain separate data structures.

A render/acoustic/Jolt update must never become the source that tells canonical routing that a door is open or closed.

## 8. Parallelism and CPU optimization rule

The i9-9900K target permits AVX2/FMA/cache-aware optimization and job-system integration for canonical spatial services only when semantic equivalence is demonstrated.

For deterministic or order-sensitive operations:

```text
parallelize internal work
    -> deterministic merge/publication
    -> compare against canonical regression corpus
```

No optimization is accepted merely because it is faster on the target CPU.

## 9. Required regression coverage

Before replacing/refactoring any canonical spatial implementation, capture source-revision reference cases for:

```text
line/box traces through representative BSP geometry
content queries at floor/wall/water/special-volume boundaries
door open/closed line tests
routing before/after dynamic inline-model changes
actor-size pathfinding
crouch/autostand transitions
TU movement costs
falls/level transitions
AI path selection inputs
grenade reachable/unreachable trajectories
visibility edge cases
entity link/unlink interactions
```

Tests compare semantic outputs, not implementation internals.

## 10. Migration completion criterion

`M029-001` is closed at the documentation level when implementation work can answer, for every canonical spatial call:

```text
where is the original authority?
what exact semantic result must remain stable?
what new presentation structure may mirror it?
how is parity tested?
```

This document supplies that contract. Implementation still requires the regression corpus and measured optimized code.

## Source references

- Audited UFO:AI source revision: https://github.com/ufoaiorg/ufoai/tree/763173ed036ebbee32c2a7bf6aefa19748df89ff
- `game_import_t`: https://github.com/ufoaiorg/ufoai/blob/763173ed036ebbee32c2a7bf6aefa19748df89ff/src/game/game.h
- host wiring: https://github.com/ufoaiorg/ufoai/blob/763173ed036ebbee32c2a7bf6aefa19748df89ff/src/server/sv_game.cpp
