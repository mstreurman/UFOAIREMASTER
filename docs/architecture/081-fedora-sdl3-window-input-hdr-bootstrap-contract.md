# Fedora SDL3 Window, Input, HDR and Bootstrap Contract

**Status:** Implementation specification baseline  
**Authority:** ADR-008, ADR-033

## 1. Layering

```text
Fedora/Wayland
    -> SDL3 window + event + controller + text/IME layer
        -> PlatformWindow / PlatformInput normalized interface
            -> Vulkan surface creation
            -> retained UI input stream
            -> canonical input command layer

Vulkan renderer owns swapchain/HDR/present/resource lifetime.
```

No renderer code may depend on raw Wayland objects in the baseline path.

## 2. SDL3 responsibilities

Use SDL3 for:

```text
SDL_Init / shutdown of required subsystems
window lifecycle and resize notifications
display enumeration / DPI information
fullscreen display-mode enumeration (resolution + refresh)
target-display hinting at window creation/recreation
keyboard/mouse events
controller/gamepad hot-plug and normalized input
text input start/stop and UTF-8 commit events
IME composition/edit events exposed by SDL3
focus/minimize/restore events
Vulkan surface creation
```

The platform layer translates SDL events into project-owned immutable event structs before higher layers consume them.

## 3. Runtime display selection

The settings/UI layer exposes display selection, resolution, refresh rate, window/fullscreen mode and HDR preference. SDL3 is the platform authority for enumerating displays/fullscreen modes and applying the requested window/fullscreen display mode; Vulkan WSI remains the authority for the actual swapchain extent/format/color space.

Use SDL3 display modes as capability data, not hardcoded mode tables. On window systems where a fullscreen-mode request is asynchronous, the renderer waits for/consumes the resulting window pixel-size events and then rebuilds the swapchain from actual surface capabilities.

Native Wayland does not allow an ordinary toplevel window to reposition itself arbitrarily. Therefore target-display selection must **not** depend on `SDL_SetWindowPosition` succeeding. Use display-specific creation/recreation hints (`SDL_WINDOWPOS_UNDEFINED_DISPLAY` / `SDL_WINDOWPOS_CENTERED_DISPLAY`) for windowed/borderless placement and a fullscreen mode belonging to the chosen `SDL_DisplayID` for fullscreen-mode requests. If changing the target display cannot be applied to the existing Wayland toplevel, recreate the SDL window + Vulkan surface while preserving canonical/presentation state.

Windowed/borderless modes may otherwise be compositor-controlled; requested refresh is never reported as actual unless the platform confirms it. Architecture 090 owns the requested-vs-actual state model.

## 4. Vulkan/HDR responsibilities

SDL is not a swapchain abstraction. Renderer code:

```text
queries VkSurfaceKHR capabilities
chooses present mode
chooses SDR/HDR format + color space from actual surface support
recreates swapchain on resize/out-of-date/suboptimal transitions
publishes OutputExtent separately from RenderExtent
owns HDR metadata/output transform where supported
falls back to SDR without changing internal scene color architecture
```

Wayland compositor HDR support is runtime capability, never assumed from Fedora version alone.

## 5. Input ownership

`PlatformInputEventV1` carries normalized physical input only:

```text
monotonic timestamp
window/focus identity
device class + stable session device ID
key/scancode/button/axis identifier
pressed/released/repeat state
float axis value when applicable
modifier mask
UTF-8 committed text or composition payload for text events
```

Canonical gameplay converts these events into existing commands/intents. SDL state may not become gameplay authority.

## 6. Controller navigation

Retained UI consumes project-normalized actions:

```text
NavigateUp/Down/Left/Right
Accept
Cancel
PagePrev/PageNext
TabPrev/TabNext
```

Default binding maps SDL gamepad d-pad/left-stick and south/east/shoulder buttons. User bindings remain data/configuration. UI focus movement is deterministic for a fixed node tree and action sequence.

## 7. Text/IME

Text widgets:

```text
start SDL text input only while an editable widget owns text focus
preserve UTF-8 committed text exactly
keep composition text/range presentation-only until commit
never synthesize gameplay commands from composition events
stop text input when focus leaves editable content
```

## 8. Fedora dependency baseline

The 2026-09-04 10:41 workstation capture confirms `SDL3-devel`, Vulkan headers/loader/tools/validation, CMake and Ninja. The bootstrap must probe with RPM metadata rather than invoking missing-command auto-install behavior.

The broad 10:41 workstation capture initially found FFmpeg 8.1.2 runtime libraries without the libav development `pkg-config` modules. A later explicit provisioning/readiness run installs matching RPM Fusion `ffmpeg-devel-8.1.2-3.fc44.x86_64` and confirms `libavcodec`, `libavformat`, `libavutil`, `libswresample`, and `libswscale` through `pkg-config`. Development provisioning is therefore ready. Runtime codec compatibility still requires the shipped cinematic corpus; development-package presence is not proof of complete legacy-bitstream coverage.

## 9. Install layout

Reference native install layout:

```text
/usr/bin/ufoai-remaster                 executable
/usr/lib64/ufoai-remaster/              project private runtime libraries if any
/usr/share/ufoai-remaster/              base data / compiled remaster assets
/usr/share/applications/                 desktop entry
/usr/share/icons/hicolor/...             application icons
/usr/lib/debug/.build-id/...             distribution/debug-package symbols, not normal runtime payload
```

A developer build continues to run from the build/source tree without requiring installation.

## 10. Bootstrap gates

M0 must fail clearly when any required item is absent. It must not silently install packages.

Minimum checks include:

```text
Fedora release = 44 for reference-support mode
x86_64
CMake >= project minimum
Ninja
C++ compiler
SDL3 pkg-config/CMake package
Vulkan loader + headers
OpenAL Soft development package
FFmpeg libavformat/libavcodec development packages
Slang v2026.17 pinned tool available in project tool cache
Jolt vendored source at accepted commit
```
