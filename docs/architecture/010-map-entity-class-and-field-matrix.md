# Map Entity Class and Field Matrix

**Status:** Source-complete registry/field audit  
**Source commit:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`

## 1. Registries

The game-side map spawn table recognizes **27 class names**.

The client-side map presentation parser handles **5** class names directly:

```text
worldspawn
misc_model
misc_particle
misc_sound
light
```

Those five names are part of the same merged map entity namespace, but the game intentionally frees/ignores some of them when they are client-only.

Unknown game-side class names are marked unused by the current spawn dispatcher.

Unknown client-side class names are ignored by the current client presentation dispatcher.

## 2. Complete class matrix

| Map classname | Game-side current role | Client-side direct map parser | Authority classification | Remaster treatment |
|---|---|---|---|---|
| `worldspawn` | initializes world; applies `noequipment`/`norandomspawn`; multiplayer configstrings | max-level/team validation intent; sun/ambient setup | Mixed | Keep game parser; migrate visual environment parsing carefully |
| `light` | freed as client-only | static renderer light | Presentation | Presentation World/Vulkan light |
| `misc_item` | adds canonical item to floor container, frees source edict | none | Canonical | Keep canonical |
| `misc_sound` | freed as client-only | ambient sound | Presentation | OpenAL map emitter |
| `misc_model` | only solid variant becomes canonical BBOX/blocking entity; otherwise freed | always creates client local model | Mixed | Preserve solid-game path; Presentation World model |
| `misc_particle` | freed as client-only | map particle | Presentation | Presentation World VFX |
| `misc_mission` | mission/zone objective trigger | none | Canonical | Keep canonical |
| `info_player_start` | multiplayer actor spawnpoint | none | Canonical | Keep |
| `info_human_start` | single-player PHALANX spawnpoint | none | Canonical | Keep |
| `info_alien_start` | alien spawnpoint | none | Canonical | Keep |
| `info_civilian_start` | civilian spawnpoint | none | Canonical | Keep |
| `info_civilian_target` | civilian waypoint | none | Canonical | Keep |
| `info_2x2_start` | 2x2 unit spawnpoint | none | Canonical | Keep |
| `info_null` | dummy/freed | none | No runtime object | Preserve parser compatibility |
| `func_breakable` | solid inline BSP, destroyable, routing update on destruction | visual arrives via brush-model/event path | Canonical state + presentation | Keep brush authority; modern debris/VFX only after event |
| `func_door` | solid inline BSP, trigger/client action, routing/visibility update | visual arrives via brush-model/event path | Canonical state + presentation | Keep brush authority; modern animation |
| `func_door_sliding` | solid inline BSP; canonical movement/routing behavior via common door use | event-driven visual | Canonical state + presentation | same |
| `func_rotating` | solid inline BSP, optionally destroyable | brush-model presentation | Canonical state + presentation | keep canonical transform/collision |
| `trigger_nextmap` | single-player map transition trigger | none | Canonical | Keep |
| `trigger_hurt` | canonical damage/stun trigger | none | Canonical | Keep |
| `trigger_touch` | canonical target/use/client-action trigger | none | Canonical | Keep |
| `trigger_rescue` | canonical rescue-zone state | none | Canonical | Keep |
| `misc_message` | canonical trigger/use HUD message | none | Canonical/UI bridge | Keep semantics; UI presentation may modernize |
| `misc_smoke` | canonical smoke field + stun-gas touch + visibility effect | particle representation is event-driven | Canonical state + presentation | Keep canonical field; modern VFX |
| `misc_fire` | canonical fire field + incendiary hurt | event-driven presentation | Canonical state + presentation | Keep canonical field |
| `misc_smokestun` | canonical stun-smoke field | event-driven presentation | Canonical state + presentation | Keep canonical field |
| `misc_camera` | single-player canonical camera/visibility entity | later camera event/model presentation | Canonical state + presentation | Keep canonical camera semantics |

## 3. Game-side recognized fields

The game entity parser recognizes 33 key names:

```text
classname
model
spawnflags
speed
dir
active
target
targetname
item
noise
particle
nextmap
frame
team
group
size
count
time
health
radius
sounds
material
light
maxteams
maxlevel
dmg
origin
angles
angle
message
desc
norandomspawn
noequipment
```

Special current behavior:

```text
light     -> explicitly ignored game-side
maxteams  -> explicitly ignored game-side
maxlevel  -> explicitly ignored game-side
```

Keys beginning with `_` are discarded before field parsing as utility/comment keys.

## 4. Client-side recognized fields

The client local-entity parser table contains 31 unique key names:

```text
skin
maxteams
spawnflags
maxlevel
attenuation
volume
frame
angle
wait
angles
origin
color
_color
modelscale_vec
classname
model
anim
particle
noise
tag
target
targetname
light
ambient_day
light_day
angles_day
color_day
ambient_night
light_night
angles_night
color_night
```

`wait` appears twice in the table but maps to the same field.

## 5. Per-class field semantics

### `worldspawn`

Game-consumed:

```text
norandomspawn
noequipment
```

Game parser also accepts but currently ignores:

```text
light
maxteams
maxlevel
```

Client-consumed:

```text
maxlevel

ambient_day
light_day
angles_day
color_day

ambient_night
light_night
angles_night
color_night
```

The client also intends to validate multiplayer team count.

### Legacy `maxteams` discrepancy

The client parse table maps:

```text
"maxteams" -> localEntityParse_t::maxteams
```

but `SP_worldspawn` reads:

```text
localEntityParse_t::maxMultiplayerTeams
```

and that member is initialized to `TEAM_MAX_HUMAN`.

No assignment from parsed `maxteams` into `maxMultiplayerTeams` was found.

Therefore the current source behavior does **not** actually apply the parsed `maxteams` field to the value used by this validation path.

Do not silently "fix" this while claiming exact compatibility.

### `misc_model`

Game-side solid behavior depends on:

```text
spawnflags bit 8 (MISC_MODEL_SOLID)
model
frame
origin
```

When solid, the server loads model AABB, creates `ET_SOLID`, sets `SOLID_BBOX`, links it and builds a forbidden-position list.

Non-solid instances are game-freed and client-only.

Client presentation consumes:

```text
model
origin
angles
modelscale_vec
spawnflags
targetname
target
tag
skin
frame
anim
```

Client presentation uses a glow/pulse spawnflag and low spawnflag bits.

### `misc_particle`

Client presentation consumes:

```text
particle
origin
wait
spawnflags
```

A no-day spawnflag controls daylight suppression.

The game frees this entity as client-only.

### `misc_sound`

Client presentation consumes:

```text
noise
origin
spawnflags
volume
attenuation
```

The game frees this entity as client-only.

### `light`

Client presentation consumes:

```text
origin
light
color/_color
spawnflags
```

The game frees this entity as client-only.

### Spawnpoints

Canonical placement relies primarily on:

```text
origin
angle
team (where applicable)
```

Spawn processing converts world origin to grid position, falls it to canonical routing/grid ground and establishes actor-size-specific occupancy.

`info_2x2_start` adjusts the grid position to the lower-left cell required by routing/pathfinding.

### `misc_item`

Canonical field:

```text
item
origin
```

The entity deposits the item into the floor inventory at its grid position, then is freed.

### `misc_mission`

Relevant fields include:

```text
team
time
target
targetname
item
radius
desc
message
particle
spawnflags
group
origin
```

The mission logic supports:

- zone occupation;
- timed occupation;
- item delivery;
- triggering/using another target;
- grouped objective zones;
- victory-condition description;
- mission HUD messages;
- objective marker particle.

This is canonical mission logic, not presentation map metadata.

### `misc_message`

Relevant fields:

```text
message
spawnflags
```

The use callback prints HUD text to an actor's player; spawnflag bit 0 frees the message entity after use.

### `misc_smoke`, `misc_fire`, `misc_smokestun`

Relevant fields include:

```text
origin
particle
spawnflags
```

The shared field-spawn path creates canonical trigger-volume entities, links them into the world, tracks round timing/team and spawns a presentation particle.

Smoke/stun-smoke use stun-gas damage type; fire uses incendiary.

Smoke also triggers a visibility recheck.

### `misc_camera`

Relevant fields:

```text
origin
angle
spawnflags
```

Single-player only.

A rotation spawnflag changes canonical camera behavior.

### `func_breakable`

Relevant canonical fields include:

```text
model
health
material
particle
spawnflags
```

Canonical destruction:

- emits model-explode event;
- selects break sound from material;
- may spawn particle;
- frees trigger/edict;
- removes canonical inline model;
- recalculates routing;
- makes actors standing above it fall.

### `func_door`

Relevant canonical fields include:

```text
model
health
noise
speed
spawnflags
```

Canonical behavior includes:

- solid BSP;
- generated action trigger;
- TU cost;
- open/closed state;
- optional reverse/start-open behavior;
- inline-model orientation update;
- routing recalculation old and new bounds;
- visibility recalculation;
- door events and sound.

### `func_door_sliding`

Relevant fields:

```text
model
health
noise
speed
dir
spawnflags
```

Shares canonical door state/use routing behavior.

### `func_rotating`

Relevant fields:

```text
model
health
speed
```

Creates a solid inline rotating entity and may be destroyable.

### `trigger_nextmap`

Relevant fields:

```text
model
particle
nextmap
team
spawnflags
```

Single-player only.

Eventually enables a transition trigger, spawns marker presentation, centers view and ends the current match when activated.

### `trigger_hurt`

Relevant fields:

```text
model
dmg
```

Creates a canonical solid trigger; default damage is 5 and damage type is fire in this map class.

### `trigger_touch`

Relevant fields:

```text
model
target
spawnflags
```

Canonical touch resolves the target entity and either:

- exposes a client action;
- calls target `use`;
- optionally supports once/on-leave behavior.

### `trigger_rescue`

Relevant fields:

```text
model
team
spawnflags
```

Single-player only.

Marks matching actors as inside/outside the rescue zone, affecting mission-abort survival semantics.

## 6. RMA entity-key transforms

When map tiles are assembled, common map loading transforms entity text before game/client parsing:

```text
origin      -> shifted by tile placement
model "*N"  -> renumbered by accumulated inline-model count
target      -> tile-specific suffix
targetname  -> tile-specific suffix
```

Worldspawn may also receive externally supplied assembly entity text.

The remaster must consume the final assembled semantics rather than independently reconstructing them from raw tile source.
