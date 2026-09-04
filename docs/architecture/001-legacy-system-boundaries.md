# Legacy System Boundaries

**Status:** Initial source-grounded architecture baseline  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Upstream:** `ufoaiorg/ufoai`  
**Purpose:** Identify the current UFO: Alien Invasion boundaries that must be preserved, wrapped, split, or replaced to implement the remaster without changing canonical gameplay.

## 1. Executive conclusion

The legacy source already contains a useful architectural seam for the remaster.

The tactical game is implemented as a separate shared library named `game`, with an explicit engine/game import-export API. The server supplies collision, tracing, pathfinding, routing, filesystem, event-writing, configuration, memory, and other services to that library.

The tactical game emits typed events to clients. The client battlescape layer receives, schedules, and executes those events through a registry of presentation handlers.

This means the remaster does **not** need to make the Vulkan renderer, OpenAL Soft, or presentation physics aware of tactical game internals.

The preferred migration direction is:

```text
Canonical Tactical Game
        |
        | authoritative state changes
        | typed tactical events
        v
Server / event transport
        |
        v
Client canonical mirror / event projection
        |
        | read-only presentation events + snapshots
        v
Modern Presentation Runtime
        |
        +-- Vulkan 1.4 / Arc B580 RT renderer
        +-- animation
        +-- presentation-only physics
        +-- OpenAL Soft + EFX
        +-- modern UI presentation
```

The current event system is therefore the most promising tactical presentation boundary.

The campaign/Geoscape side is less clean. Campaign logic is compiled directly into the main client and its cgame interface imports UI and renderer functions. Campaign modernization will require a deliberate separation layer.

## 2. Source-tree baseline

The examined tree is based on commit:

```text
763173ed036ebbee32c2a7bf6aefa19748df89ff
```

Important source areas include:

```text
src/game/                 tactical gameplay shared library
src/server/               server and tactical-game host
src/common/               collision, grid, routing, network, filesystem, etc.
src/client/battlescape/   tactical client and presentation
src/client/cgame/         campaign/skirmish/multiplayer client-game modes
src/client/renderer/      legacy OpenGL renderer
src/client/sound/         legacy sound implementation
src/client/ui/            legacy UI system
src/shared/               shared low-level utilities/types
src/tools/                content/map/editor tools
base/                     game data and presentation assets
```

The captured source-size snapshot shows approximately:

```text
src/client     6.2 MiB
src/common     980 KiB
src/game       816 KiB
src/server     232 KiB

base/maps      179 MiB
base/music     203 MiB
base/models    245 MiB
base/textures  326 MiB
base/ufos      2.2 MiB
```

The exact byte sizes are not architectural requirements, but they show that presentation assets dominate the data footprint while the tactical gameplay library itself is comparatively compact.

## 3. Current build/runtime topology

### 3.1 Tactical game library

`src/game/CMakeLists.txt` defines:

```text
project(game DESCRIPTION "Tactical battle library of UFO:AI.")
add_library(game SHARED ...)
```

The library contains:

- actor logic;
- tactical AI;
- combat;
- health;
- inventory;
- morale;
- movement;
- reaction fire;
- rounds;
- spawning;
- missions;
- tactical visibility;
- tactical events;
- tactical statistics.

This is the strongest canonical tactical boundary in the existing code.

### 3.2 Main client

The `ufo` executable compiles a large set of systems together:

- battlescape client;
- campaign;
- skirmish;
- multiplayer client game;
- renderer;
- sound;
- UI;
- input;
- common engine code;
- server code;
- shared game helpers.

The build defines `HARD_LINKED_CGAME`.

The main client therefore contains both gameplay-facing and presentation-facing responsibilities.

### 3.3 Dedicated server

`ufoded` contains:

- common collision/grid/routing infrastructure;
- server implementation;
- selected shared game helpers;
- networking;
- the host side of the `game` shared-library API.

It depends on the same `game` shared library.

### 3.4 Important implication

The current tactical split is approximately:

```text
               +-----------------------+
               |       game.so         |
               | Tactical game rules   |
               +-----------+-----------+
                           |
                 game_import_t /
                 game_export_t
                           |
               +-----------v-----------+
               |       server          |
               | collision / routing   |
               | event transport       |
               +-----------+-----------+
                           |
                     server events
                           |
               +-----------v-----------+
               | battlescape client    |
               | local mirror +        |
               | presentation          |
               +-----------------------+
```

This structure should be preserved and strengthened rather than discarded.

## 4. Tactical canonical authority

### 4.1 `game` is the tactical rules owner

The `game_export_t` API exports gameplay operations such as:

- initialization/shutdown;
- entity spawning;
- client connection and match start;
- player actions;
- end-round handling;
- active-team handling;
- per-frame tactical simulation.

The tactical library also owns its edict and player arrays.

This makes `src/game` canonical by default.

### 4.2 Server-provided canonical spatial services

The game library does not calculate every spatial operation internally. Through `game_import_t`, the server provides:

- `Trace`;
- `PointContents`;
- `TestLine`;
- `TestLineWithEnt`;
- grenade-target calculation;
- grid path calculation;
- grid path finding;
- movement cost/step services;
- grid fall;
- grid-to-world conversion;
- routing recalculation;
- standability checks;
- visibility;
- model AABBs;
- entity link/unlink.

`SV_InitGameProgs` wires these imports to the server/common implementation.

Therefore these server/common spatial systems are part of the canonical gameplay authority even though they are not located under `src/game`.

### 4.3 Remaster rule

The following must not be replaced by presentation technology:

```text
canonical tracing       != Vulkan ray tracing
canonical collision     != presentation physics
canonical visibility    != GPU visibility
canonical pathfinding   != physics navigation
canonical grenade logic != rigid-body trajectory
```

They may be optimized on the i9-9900K, but behavior must remain canonical.

## 5. Tactical event boundary

### 5.1 Game-side event publication

`src/game/g_events.cpp` emits explicit events including:

- actor turn;
- actor movement;
- actor shooting;
- hidden shooting;
- actor death;
- actor state;
- inventory changes;
- entity destruction;
- model explosions;
- particle appearance/spawn;
- sounds;
- reaction-fire changes.

Events serialize canonical outcomes and relevant presentation data through the server event-writing functions.

A shooting event, for example, serializes data including:

- shooter entity;
- potential victim entity;
- fire definition;
- shoot type;
- flags;
- surface/content information;
- muzzle/from position;
- canonical impact position;
- hit-plane normal.

The presentation layer therefore does not need to perform an authoritative ray trace to decide where the shot landed.

### 5.2 Client-side event registry

`src/client/battlescape/events/e_main.cpp` defines a table mapping event IDs to:

- message format;
- callback;
- timing callback;
- optional execution check.

The event set includes direct presentation opportunities for the remaster:

```text
EV_ACTOR_MOVE
EV_ACTOR_START_SHOOT
EV_ACTOR_SHOOT
EV_ACTOR_THROW
EV_ACTOR_END_SHOOT
EV_ACTOR_DIE
EV_ACTOR_WOUND
EV_MODEL_EXPLODE
EV_PARTICLE_APPEAR
EV_PARTICLE_SPAWN
EV_SOUND
EV_DOOR_OPEN
EV_DOOR_CLOSE
```

### 5.3 Client-side event timing

`e_parse.cpp`:

1. receives an event;
2. looks up its registered handler;
3. calculates presentation execution time;
4. schedules it;
5. executes it later when locks/timing permit.

The existing client already separates **canonical event arrival** from **presentation-time execution**.

This is highly valuable.

The remaster can preserve canonical event ordering and data while replacing the presentation implementation.

## 6. The key mixed structure: `le_t`

`src/client/battlescape/cl_localentity.h` defines the local client entity.

It currently combines several responsibilities.

### 6.1 Canonical/mirrored state

Examples:

- grid/world position;
- Time Units;
- morale;
- HP;
- stun;
- actor state;
- wounds;
- team;
- player number;
- inventory;
- held-item indices;
- fire definitions.

### 6.2 Client interaction state

Examples:

- selected actor;
- selected fire mode;
- pending action;
- cursor/move destination;
- locally calculated move length;
- client action target.

### 6.3 Presentation state

Examples:

- renderer model pointers;
- animation state;
- alpha;
- render flags;
- particles;
- lighting;
- local movement interpolation;
- movement timing;
- sound index/attenuation/volume;
- think callbacks.

### 6.4 Architectural conclusion

`le_t` must **not** become the data model of the new renderer.

The remaster should eventually split the current role conceptually into at least:

```text
TacticalClientMirror
    canonical values received/derived from server events

TacticalInteractionState
    selection, cursor intent, move previews, local UI state

PresentationEntity
    transforms, render assets, animation, VFX, audio emitters,
    presentation physics handles, interpolation state
```

The exact C++ types remain to be designed.

The principle is the important part: presentation state must stop being structurally entangled with canonical mirrored state.

## 7. Example: actor death

The current actor-death client event demonstrates why this split is needed.

The callback currently performs several unrelated operations:

1. reads canonical death/state values from the event;
2. updates local mirrored state;
3. updates UI-visible enemy counts;
4. invokes renderer animation functions;
5. displays HUD text;
6. plays death sound;
7. modifies local collision/content representation;
8. removes particles;
9. updates local movement/path preview state.

For the remaster, the desired conceptual flow is:

```text
EV_ACTOR_DIE
      |
      v
Canonical client mirror update
      |
      +--> UI notification projection
      +--> animation event
      +--> OpenAL death/audio event
      +--> ragdoll/presentation-physics event
      +--> VFX event
```

The ragdoll result remains completely outside canonical state.

## 8. Example: actor shooting

The current shooting callback already receives the canonical impact position produced by tactical simulation.

It then performs presentation work:

- determines a visual muzzle position from model tags;
- creates a client projectile effect;
- plays weapon audio;
- triggers shooting animation;
- changes presentation flags.

This is almost exactly the boundary the remaster needs.

The future renderer should treat the canonical event's impact information as input and use it to create:

- muzzle flash;
- animated weapon recoil;
- tracer/projectile presentation;
- RT-aware emissive lighting;
- surface VFX;
- decals;
- debris;
- OpenAL weapon/impact audio;
- presentation physics.

None of those systems may change the canonical hit.

## 9. Campaign/Geoscape boundary

The campaign is significantly more coupled to the client presentation architecture.

Campaign code lives under:

```text
src/client/cgame/campaign/
```

The cgame interface exposes direct UI and renderer imports.

Examples include imported functions for:

- pushing/popping UI windows;
- registering UI text/options;
- HUD messages;
- drawing text, images, rectangles, fills, and tooltips;
- drawing Geoscape markers;
- drawing lines;
- renderer image operations;
- local sound playback.

Campaign code therefore cannot simply be declared a presentation-independent library today.

### 9.1 Classification

Campaign files must be treated as **mixed canonical + presentation** until analyzed function-by-function.

### 9.2 Migration rule

Do not rewrite campaign rules merely to modernize their UI.

Instead introduce adapters/interfaces so that:

```text
campaign rule/state code
        |
        v
campaign presentation model / commands
        |
        v
new UI + renderer
```

The initial modernization can preserve existing campaign callbacks while replacing their imported presentation implementation behind compatible wrappers.

## 10. Legacy renderer

Current renderer sources are concentrated under:

```text
src/client/renderer/
```

They include:

- OpenGL state;
- arrays/drawing;
- BSP rendering;
- lighting/lightmaps;
- models;
- MD2/MD3/OBJ loaders;
- materials;
- particles;
- framebuffer;
- weather;
- Geoscape rendering;
- font rendering;
- animation helpers.

### Classification

**Presentation — replaceable**, with caveats.

Some renderer-side model/animation utilities are currently called directly by battlescape event code and UI/campaign code.

Therefore removal must happen after adapters are introduced.

### Target

```text
legacy OpenGL renderer
        |
        X  replaced
        |
Vulkan 1.4 Arc-B580 renderer
```

Canonical collision/BSP/routing data must not disappear merely because the rendering representation changes.

## 11. Legacy sound

The main client currently links SDL_mixer and contains sound code under:

```text
src/client/sound/
```

### Classification

**Presentation — replaceable.**

### Target

OpenAL Soft + EFX.

The tactical event protocol already carries spatial sound events, which provides a natural input path for the replacement audio runtime.

UI/campaign sound calls need adapter coverage.

## 12. Legacy UI

The existing UI subsystem lives under:

```text
src/client/ui/
```

It is extensive and tightly integrated with campaign/cgame callbacks.

### Classification

**Presentation, but highly coupled.**

### Migration rule

Do not remove it first.

A safer sequence is:

1. introduce presentation interfaces;
2. route legacy UI through them;
3. add replacement UI implementation;
4. migrate screens incrementally;
5. remove legacy UI only after campaign behavior is proven unchanged.

## 13. `src/common` and `src/shared`

These directories are not automatically "engine code that can be replaced."

They include infrastructure used by canonical gameplay, such as:

- BSP/collision model;
- grid;
- routing;
- tracing;
- networking/message serialization;
- parsing;
- shared mathematics/types.

### Classification

**Mixed infrastructure / canonical dependency.**

Any replacement or optimization must be analyzed by behavior, not directory name.

In particular, canonical pathing, collision, tracing, and routing must retain their outputs.

## 14. `base/` data classification

The base directory mixes gameplay data and presentation assets.

### Canonical-sensitive data

Likely includes significant portions of:

```text
base/ufos/
base/ai/
map gameplay/routing definitions
weapon/item/team/campaign definitions
```

These must be reviewed before modification.

### Presentation-oriented data

Large portions of:

```text
base/textures/
base/models/
base/music/
base/sound/
base/pics/
base/shaders/
base/materials/
```

are primary remaster targets.

### Mixed data

Maps are inherently mixed:

- canonical geometry/routing/collision/mission layout;
- visual geometry/materials/lighting.

The new renderer must be able to create richer presentation geometry/materials without silently changing canonical map behavior.

## 15. Boundary classification matrix

| Area | Current classification | Remaster treatment |
|---|---|---|
| `src/game` tactical rules | Canonical | Preserve behavior |
| server game host | Canonical infrastructure | Preserve behavior, wrap |
| common tracing/collision/grid/routing | Canonical infrastructure | Preserve outputs |
| tactical event serialization | Canonical-to-client boundary | Preserve and exploit |
| battlescape event scheduling | Mixed / presentation timing | Preserve semantics, refactor |
| battlescape event callbacks | Mixed | Split mirror updates from presentation |
| `le_t` | Strongly mixed | Split responsibilities |
| OpenGL renderer | Presentation | Replace |
| SDL_mixer sound | Presentation | Replace with OpenAL Soft + EFX |
| animation helpers | Presentation/mixed | Replace behind presentation model |
| particles/VFX | Presentation | Replace |
| client UI | Presentation/mixed | Incremental replacement |
| campaign logic | Canonical/mixed | Preserve rules; decouple presentation |
| Geoscape drawing | Presentation inside campaign layer | Route through new presentation API |
| presentation physics | New presentation system | Add; zero authority |
| Vulkan RT | New presentation system | Add; zero gameplay authority |
| `base/ufos` | Primarily canonical data | Preserve unless explicitly approved |
| textures/models/music/sound | Presentation | Remaster target |
| maps | Mixed | Preserve canonical spatial behavior; enrich presentation |

## 16. Proposed tactical presentation bridge

The preferred future tactical architecture is:

```text
game.so
  Canonical tactical simulation
          |
          | game events
          v
server
  Canonical collision/routing +
  event transport
          |
          v
Tactical Event Decoder
          |
          +----------------------+
          |                      |
          v                      v
Canonical Client Mirror    Presentation Event Stream
          |                      |
          |                      +--> Animation
          |                      +--> Visual Physics
          |                      +--> Vulkan/VFX
          |                      +--> OpenAL/EFX
          |                      +--> UI notifications
          |
          v
Tactical Interaction/UI Model
```

The exact implementation may remain in-process initially.

The boundary is logical first; process or DLL separation is not required.

## 17. Presentation event requirements

A future typed presentation-event layer should:

- preserve canonical event ordering;
- carry canonical entity IDs;
- carry canonical positions and state transitions;
- distinguish authoritative data from purely visual parameters;
- allow presentation events to be replayed/debugged;
- avoid pointers into legacy renderer structures;
- avoid presentation callbacks inside canonical gameplay;
- allow multiple consumers (renderer, audio, animation, physics, UI);
- allow consumers to ignore events safely;
- prohibit consumers from writing canonical game state.

## 18. Migration priorities

### Phase A — Preserve and observe

- keep existing game/server behavior;
- add regression tests where available;
- document event semantics;
- identify canonical client-mirror updates inside event callbacks.

### Phase B — Split tactical event handlers

For each event callback:

```text
legacy callback
   |
   +--> canonical mirror projection
   +--> presentation event emission
```

Keep the legacy presentation path temporarily.

### Phase C — Introduce modern presentation world

Build:

- modern entity handles;
- transform hierarchy;
- animation presentation state;
- Vulkan render entities;
- OpenAL emitters;
- presentation-physics handles.

### Phase D — Replace legacy tactical presentation

Migrate event consumers to:

- Vulkan renderer;
- modern animation;
- presentation physics;
- OpenAL Soft + EFX.

### Phase E — Campaign presentation separation

Introduce adapters around the cgame UI/renderer imports, then incrementally replace Geoscape and campaign UI presentation without changing campaign rules.

## 19. Source-grounded investigation status

The investigations originally requested by this document now have explicit follow-on authorities:

1. **Tactical event catalog — COMPLETE at documentation level**
   - architecture 004: complete tactical event catalog;
   - architecture 005: dependency/authority matrix.

2. **Canonical spatial-service map — COMPLETE at documentation level**
   - architecture 075 maps `game_import_t` spatial services to audited host implementations, representative canonical consumers, preservation classes and regression requirements.

3. **Legacy renderer dependency/migration map — COMPLETE at design level**
   - architecture 076 inventories the renderer families, cgame renderer import surface, known external consumers, adapter disposition and removal gates.
   - implementation still requires a final source scan before deleting the old renderer.

4. **Legacy sound dependency/migration map — COMPLETE at design level**
   - architecture 076 inventories sound families, exact cgame sound imports, campaign consumers, target OpenAL command path and removal gates.

5. **Campaign/cgame coupling map — COMPLETE at documentation level**
   - architecture 077 inventories direct UI/renderer/sound coupling at source baseline `763173ed...`;
   - architecture 078 defines the typed strategic snapshot/intent/Geoscape presentation boundary.

## 20. Architecture rule established by this analysis

The remaster should not begin by rewriting `src/game`.

The highest-value first implementation work is to strengthen the boundary that already exists between canonical tactical events and client presentation.

That allows the renderer, animation, physics, sound, and eventually UI to be replaced while retaining the tactical game's existing authority.

## 21. Follow-on specifications

The proposed split is refined in:

- `003-presentation-world-and-event-bridge.md`;
- `004-tactical-event-catalog.md`;
- `005-tactical-event-dependency-matrix.md`;
- `075-canonical-spatial-service-preservation-map.md`;
- `076-legacy-renderer-and-sound-migration-map.md`;
- `077-campaign-cgame-coupling-map.md`;
- `078-strategic-geoscape-presentation-separation-contract.md`;
- `080-implementation-migration-roadmap.md`.

These later documents make the tactical/canonical, strategic/campaign, renderer, audio and migration boundaries explicit.
