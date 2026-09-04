# Surface, Content and Terrain Semantics Matrix

**Status:** Source-complete definition/consumer audit baseline  
**Source commit:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`

## 1. Rule

A rendering material and a canonical BSP surface are not the same thing.

The remaster must preserve:

```text
canonical surface name
canonical surface flags
canonical content flags
terrain lookup identity
```

separately from:

```text
PBR base color
normal
roughness
metalness
emissive
opacity
RT classification
```

## 2. `SURF_*` matrix

| Flag | Current source meaning / observed consumer | Canonical status | Remaster policy |
|---|---|---:|---|
| `SURF_LIGHT` | ufo2map/lightmap surface-emission authoring | No direct runtime gameplay consumer found | Presentation/compiler semantic |
| `SURF_SLICK` | defined as affecting game physics, but audit found only definition/map-check handling | **No direct runtime gameplay consumer found at this commit** | Preserve bit for compatibility; do not invent new canonical behavior |
| `SURF_WARP` | legacy renderer/ufo2map water/warp handling | Presentation | Map to modern water/warp material class |
| `SURF_BLEND33` | legacy alpha blending/lightmap treatment; compiler marks translucent/detail | Presentation/compile | Modern transparency class |
| `SURF_BLEND66` | legacy alpha blending/lightmap treatment | Presentation/compile | Modern transparency class |
| `SURF_FLOWING` | legacy animated/scrolling surface semantics | Presentation | Preserve as material animation input |
| `SURF_NODRAW` | compiler/authoring visibility semantic | Compile/presentation | Do not emit normal visible surface |
| `SURF_HINT` | BSP splitter/compiler semantic | Compiler | No runtime PBR meaning required |
| `SURF_SKIP` | compiler ignores/permits non-closed brush behavior | Compiler | No runtime PBR meaning |
| `SURF_PHONG` | compile-time/render normal smoothing behavior | Presentation/compiler | Convert to modern normal/smoothing data |
| `SURF_BURN` | directly checked by canonical combat for persistent fire eligibility | **Canonical** | Preserve canonical bit independently of material |
| `SURF_FOOTSTEP` | ufo2map authoring marker used to generate footstep-related texture lists; runtime footstep lookup uses surface name -> terrain definition | Compiler feeding runtime semantic validation/data | Preserve source semantic; runtime gameplay remains texture/terrain keyed |
| `SURF_ORIGIN` | RMA/inline-model renderer-origin behavior | Structural presentation/compiler | Preserve during presentation compile/import |
| `SURF_FOLIAGE` | renderer/compiler foliage generation/placement | Presentation | Modern foliage metadata |
| `SURF_ALPHATEST` | legacy alpha-test; compiler also classifies translucent/detail | Presentation with RT performance consequences | Separate alpha-test RT geometry from opaque where useful |

## 3. Important `SURF_SLICK` finding

The comment says:

```text
SURF_SLICK — effects game physics
```

but the source audit at this commit found no runtime game/common/server consumer beyond the definition and map tooling/checking.

Therefore the remaster should preserve the flag, but must not create new canonical slip/physics behavior in the name of "preserving" something the current game is not executing.

## 4. Important `SURF_BURN` finding

Canonical combat checks the trace surface's `surfaceFlags` and requires `SURF_BURN` for supported fire/incendiary/blast behavior to leave burning effects.

This is a direct gameplay dependency.

A PBR material cannot redefine it.

## 5. `CONTENTS_*` matrix

| Content | Current observed role | Canonical status | Remaster policy |
|---|---|---:|---|
| `CONTENTS_SOLID` | core collision/tracing; masks; BSP structural semantics | Canonical | Keep common BSP |
| `CONTENTS_WINDOW` | included in solid/shot masks; visible/translucent collision | Canonical | Preserve collision; render material may be glass |
| `CONTENTS_LADDER` | map authoring/compiler/check semantic; no direct runtime flag consumer found | Compiler-derived canonical routing input | Preserve canonical compiled routing; do not depend on presentation ladder collision |
| `CONTENTS_WATER` | passable mask; game movement water state/sounds; smoke/fire trace rejection; visibility mask | Canonical | Preserve BSP content; modern water visuals separate |
| `CONTENTS_LEVEL_1..8` / `CONTENTS_LEVEL_ALL` | level-specific BSP structure/masks | Canonical structural + presentation cutaway | Keep canonical; map to presentation level masks |
| `CONTENTS_ACTORCLIP` | actor-impassable mask / clip BSP | Canonical | Keep |
| `CONTENTS_PASSABLE` | changes tracing-node blocking classification and passable masks | Canonical | Keep |
| `CONTENTS_TERRAIN` | ufo2map terrain material generation/UV behavior; no direct runtime gameplay flag consumer found | Compiler/presentation input | Preserve source mapping; canonical runtime behavior still surface-name/terrain based |
| `CONTENTS_LIGHTCLIP` | special compile/light clipping and clip masks | Canonical/common trace mask may include it; mostly compile/light semantic | Preserve BSP |
| `CONTENTS_ACTOR` | dynamic actor content, included in `MASK_SHOT` | Canonical dynamic entity semantic | Keep canonical server/client mirror semantics |
| `CONTENTS_ORIGIN` | removed/consumed during BSP compilation for inline entity origins | Compiler structural | Preserve import result, not runtime material |
| `CONTENTS_WEAPONCLIP` | explicitly stops shots; included in shot/smoke-fire masks; common box hull uses it | Canonical | Keep |
| `CONTENTS_DEADACTOR` | client local-entity dead-actor content classification | Tactical client mirror/spatial presentation legacy | Preserve event/mirror behavior where required; not a map authoring material |
| `CONTENTS_DETAIL` | compiler/detail and legacy debug/render semantics | Compiler/presentation | No canonical replacement behavior needed |
| `CONTENTS_TRANSLUCENT` | compiler auto classification for alpha surfaces | Compiler/presentation | Modern transparency metadata |

## 6. Masks

Several canonical masks combine content semantics.

Examples:

```text
MASK_SOLID
    CONTENTS_SOLID | CONTENTS_WINDOW

MASK_IMPASSABLE
    MASK_SOLID | CONTENTS_ACTORCLIP

MASK_PASSABLE
    CONTENTS_PASSABLE | CONTENTS_WATER

MASK_SHOT
    CONTENTS_SOLID
    | CONTENTS_ACTOR
    | CONTENTS_WEAPONCLIP
    | CONTENTS_WINDOW

MASK_SMOKE_AND_FIRE
    MASK_SOLID
    | CONTENTS_WATER
    | CONTENTS_WEAPONCLIP

MASK_VISIBILILITY
    CONTENTS_SOLID
    | CONTENTS_WATER
```

The presentation map must never substitute its own material/geometry classifications for these masks.

## 7. Terrain definition

Runtime terrain definitions contain:

```text
texture          canonical lookup key
footstepSound
particle
bounceFraction
footstepVolume
```

Script parser keys include:

```text
footstepsound
particle
footstepvolume
bouncefraction
```

## 8. Canonical terrain consumers

### Footsteps

Canonical movement traces downward with `MASK_SOLID`.

If a trace has a surface, the game asks:

```text
GetFootstepSound(trace.surface->name)
```

The server implementation looks up the terrain definition by the canonical surface texture name.

Therefore a presentation material rename must not alter the canonical surface-name lookup.

### Grenade bounce

Canonical grenade simulation uses the trace surface name to obtain:

```text
bounceFraction
```

from the terrain definition.

This directly affects canonical projectile behavior.

### Client footstep presentation

Legacy client presentation also looks up terrain by texture name and uses:

- footstep particle;
- footstep sound;
- footstep volume.

The remaster OpenAL/VFX systems may replace presentation behavior, but canonical movement timing/surface identity remains the input.

## 9. `SURF_FOOTSTEP` versus runtime terrain lookup

`SURF_FOOTSTEP` itself is not what the runtime asks when an actor steps.

ufo2map uses the flag while generating/validating texture lists.

Runtime code uses the canonical trace surface texture name and terrain definition.

This distinction matters for the remaster asset compiler:

```text
authoring flag
    !=
runtime canonical terrain lookup key
```

## 10. PBR mapping requirement

A presentation material binding should therefore resemble:

```cpp
struct RenderMaterialBinding {
    CanonicalSurfaceId source;
    RenderMaterialId material;
};
```

The `RenderMaterialId` is free to point to high-resolution replacement PBR assets.

It must not overwrite canonical:

```text
surface name
surface flags
content masks
terrain identity
```

## 11. RT classification

Presentation compile may derive RT classes such as:

```text
Opaque
AlphaTest
Transparent
Water
NoRT
```

These are renderer-only.

They cannot replace canonical `MASK_*`, `CONTENTS_*` or `SURF_BURN` decisions.
