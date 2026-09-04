# Legacy Renderer and Sound Migration Map

**Status:** Source-grounded migration contract  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Primary authorities:** ADR-024–027, architecture 002, 035–050, 054

## 1. Purpose

This document closes the design-level migration-map gap identified as `M029-002`.

It does not preserve OpenGL or the old mixer as architecture. It preserves the **behavioral call-in surfaces and consumers** that must be accounted for while those implementations are replaced.

## 2. Renderer source families at the audited revision

The legacy renderer is concentrated under `src/client/renderer/` and is exposed to the rest of the client through renderer headers plus `src/client/cl_renderer.h`.

Audited source families include:

```text
r_main                 lifecycle/frame entry
r_sdl                  legacy SDL video/context mode integration
r_state/r_array        OpenGL state/array management
r_program              GLSL program management
r_framebuffer          framebuffer/postprocess targets
r_image                 image loading/cache/upload
r_model*                model loading/drawing/legacy MD2/MD3/OBJ/brush
r_mesh/r_mesh_anim      mesh and animation rendering helpers
r_bsp/r_surface         world/BSP surface rendering
r_material              legacy material behavior
r_light/r_lightmap      lighting/lightmap behavior
r_particle              legacy particles
r_weather               weather presentation
r_flare/r_corona/grass  auxiliary world effects
r_geoscape              Geoscape rendering helpers
r_font/r_draw           2D/font drawing helpers
r_thread                legacy renderer threading
r_matrix/r_misc         transform/matrix helpers
```

The Vulkan remaster replaces implementation, not every high-level behavior at once.

## 3. Non-renderer client consumers that require migration accounting

At the audited revision, renderer-facing behavior is also used by client systems outside `src/client/renderer/`, including:

```text
src/client/cl_screen.cpp
src/client/cl_video.cpp
src/client/cl_team.cpp
src/client/cl_console.cpp
src/client/cl_language.cpp
src/client/ui/*
src/client/cgame/* through cgame_import_t
```

The exact implementation may be replaced behind adapters during staged migration.

## 4. Exact cgame renderer import surface

`src/client/cgame/cgame.h` exposes these renderer imports to cgame code:

```text
R_SoftenTexture
R_LoadImage
R_ImageExists
R_Color
R_DrawLineStrip
R_DrawLine
R_DrawRect
R_DrawFill
R_Draw2DMapMarkers
R_Draw3DMapMarkers
R_DrawBloom
R_UploadAlpha
R_DrawImageCentered
```

It additionally exposes renderer-owned Geoscape image data through:

```text
r_xviAlpha
r_radarPic
r_radarSourcePic
```

These imports/raw pointers are legacy coupling and are not part of the final remaster API.

## 5. Confirmed direct cgame renderer consumers

The audited source has direct renderer coupling including:

```text
campaign/cp_geoscape.cpp
    R_Color
    R_DrawLineStrip
    other Geoscape drawing helpers

campaign/cp_overlay.cpp
    raw r_xviAlpha/r_radarPic/r_radarSourcePic access

multiplayer/mp_serverlist.cpp
    R_ImageExists for map-shot selection
```

`src/client/cgame/cl_game.cpp` wires the renderer imports and raw Geoscape buffers into `cgame_import_t`.

## 6. Renderer migration disposition

Each legacy renderer use falls into one of these target classes:

| Legacy responsibility | Target remaster owner |
|---|---|
| scene/world rendering | Vulkan renderer + Frame Graph |
| model/image asset loading | offline/runtime asset system |
| font/text/2D UI drawing | retained UI renderer |
| Geoscape lines/markers/globe visuals | strategic presentation scene + retained UI embedded view |
| map screenshots/image existence | asset registry/content lookup, not renderer query |
| bloom/postprocess | Vulkan postprocess/color pipeline |
| particles/weather/flares | VFX runtime |
| renderer thread/state | new Render thread + frame contexts |
| OpenGL/SDL GL context state | removed |

No final cgame API may require an OpenGL-style immediate draw/state call.

## 7. Sound implementation families at the audited revision

Legacy sound implementation is concentrated under `src/client/sound/`:

```text
s_main             public lifecycle/source entry
s_sample           sample cache/loading
s_mix              source/mix update
s_music            music playback/control
s_mumble           Mumble positional integration
s_local            internal state/types
```

The remaster audio target is already fixed by ADR-024 and architecture 035–038: OpenAL Soft with the accepted audio-control/thread/voice/environment model.

## 8. Exact cgame sound import surface

`cgame_import_t` exposes:

```text
S_StartLocalSample
S_SetSampleRepeatRate
```

Confirmed campaign consumers include:

```text
campaign/cp_messages.cpp
    local notification sounds
    sample repeat-rate behavior

campaign/cp_airfight.cpp
    Geoscape air-combat presentation sounds

campaign/cp_base_callbacks.cpp
    base-building placement sound
```

`src/client/cgame/cl_game.cpp` wires these functions into the cgame import table.

## 9. Sound migration disposition

| Legacy responsibility | Target remaster owner |
|---|---|
| local/UI one-shot | typed presentation audio command |
| tactical world sound | event-derived world audio command |
| Geoscape/campaign sound | strategic presentation audio adapter |
| music | remaster music/stream control preserving campaign intent |
| sample repeat/throttle | audio command policy or semantic notification throttle |
| positional/environment processing | OpenAL Soft/EFX runtime |
| old mixer/source internals | removed after parity |

Campaign code may request a semantic sound, but must not own OpenAL sources, buffers, EFX objects or audio-thread state.

## 10. Migration adapter rule

During staged migration, adapters may retain old call signatures temporarily, but they must route into the new owner:

```text
legacy R_* call
    -> compatibility adapter
    -> retained UI / strategic scene / Vulkan renderer service

legacy S_* call
    -> compatibility adapter
    -> typed AudioCommand
    -> AudioControl/OpenAL runtime
```

Compatibility adapters are migration tools, not the final API.

## 11. Removal gates

### Renderer legacy removal

The old renderer implementation can be removed only when:

```text
world/battlescape rendering migrated
strategic/Geoscape rendering migrated
UI/text/2D drawing migrated
cinematic/video upload/display migrated
asset image/model ownership migrated
all cgame R_* imports/raw renderer pointers removed or compatibility-only and unused
OpenGL context/state dependencies removed
```

### Sound legacy removal

The old sound implementation can be removed only when:

```text
world/local/UI/campaign/music behaviors have OpenAL-backed replacements
cgame sound imports route through typed audio commands or are removed
save/gameplay code has no dependency on mixer internals
regression capture confirms expected logical sound command sequences
```

## 12. Verification

A source-boundary audit before deleting the old systems must search at minimum for:

```text
R_*
r_* renderer globals exposed outside renderer
S_*
AL*/alc* direct calls outside the new audio runtime
OpenGL symbols / GL context creation
legacy renderer/sound headers included by cgame/UI/client code
```

The implementation milestone is not complete while an unclassified production callsite remains.
