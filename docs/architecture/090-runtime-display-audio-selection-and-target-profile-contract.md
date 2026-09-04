# Runtime Display, Audio Selection and Target-Profile Contract

**Status:** Exact implementation specification  
**Authority:** ADR-046  
**Related:** architecture 035, 037, 072, 073, 081

## 1. Principle

```text
reference workstation = optimization + qualification target
reference workstation != hardcoded runtime configuration
```

All presentation configuration is resolved from user preference + current runtime capabilities.

## 2. Display requested-state model

Conceptual persistent configuration:

```cpp
enum class WindowMode : uint8_t { Windowed, BorderlessFullscreen, FullscreenMode };
enum class HdrPreference : uint8_t { Auto, Off, On };
enum class RenderResolutionMode : uint8_t { NativeOutput, Explicit };

struct DisplayPreferenceV1 {
    string preferredDisplaySelector;
    WindowMode windowMode;
    uint32_t requestedWidth;
    uint32_t requestedHeight;
    uint32_t requestedRefreshMilliHz;
    HdrPreference hdr;
    RenderResolutionMode renderResolutionMode;
    uint32_t explicitRenderWidth;
    uint32_t explicitRenderHeight;
};
```

The exact settings-file serialization may differ; these semantics are mandatory.

## 3. Display enumeration and mode selection

On Fedora/SDL3:

```text
SDL_GetDisplays
    -> enumerate current displays
SDL_GetFullscreenDisplayModes(display)
    -> enumerate supported fullscreen resolution/refresh tuples
SDL_SetWindowFullscreenMode
    -> request a selected fullscreen mode when FullscreenMode is chosen
```

No compiled mode table is authoritative. Only currently enumerated modes are offered as exact fullscreen-mode choices.

On native Wayland, do not assume an existing ordinary toplevel can be moved with `SDL_SetWindowPosition`; Wayland may deny that operation. Target-display selection uses display-specific window creation/recreation hints (`SDL_WINDOWPOS_UNDEFINED_DISPLAY(displayID)` or `SDL_WINDOWPOS_CENTERED_DISPLAY(displayID)`) and, for an explicit fullscreen mode, an `SDL_DisplayMode` obtained from that target display. When necessary, changing display recreates the SDL window/Vulkan surface while preserving canonical and presentation state.

`SDL_DisplayID` is a session runtime identifier, not a durable content/gameplay ID. Persistence stores a best-effort display selector and resolves it again at startup; if it cannot be resolved, use the platform primary/default display and report the fallback.

## 4. Requested versus actual display state

Publish an immutable runtime state containing at least:

```text
requested display selector
actual SDL display identity/name
requested window mode
actual window/fullscreen state
requested resolution
actual OutputExtent
requested refresh rate
actual/observed refresh rate when available
requested HDR preference
actual HDR active state
actual swapchain format/color space
active output luminance descriptor
RenderExtent
```

A successful settings write does not prove that the compositor/display accepted the request. Actual state is authoritative for rendering and diagnostics.

## 5. RenderExtent policy

```text
NativeOutput:
    RenderExtent = OutputExtent

Explicit:
    RenderExtent = explicitRenderWidth x explicitRenderHeight
    final scene output scales to OutputExtent using architecture 072
```

The 1920x1080 value is mandatory for the primary performance qualification profile but is not globally hardcoded.

Changing RenderExtent invalidates/recreates the histories/resources owned by architecture 072. Changing only OutputExtent rebuilds output/UI resources as specified there.

## 6. Refresh-rate semantics

Refresh rate is a display-mode request, not the Vulkan present mode.

Fullscreen-mode selection may request a specific enumerated refresh rate. Windowed/borderless behavior may be compositor-controlled. The UI shows requested and actual/observed refresh independently and must not claim that a requested rate is active when the platform cannot confirm it.

Present mode/VSync remains a separate renderer/presentation policy.

## 7. HDR semantics

```text
Off:
    select SDR output even if HDR is available

On:
    request an HDR-capable output path; if unavailable, actual state reports SDR + reason

Auto:
    use HDR when the selected display/surface path is HDR-capable according to platform policy
```

The HDR output transform and metadata use the actual selected output descriptor. DisplayHDR 600 is the qualification target, not a universal runtime luminance constant.

## 8. Audio requested-state model

Conceptual persistent configuration:

```cpp
enum class AudioDeviceMode : uint8_t { SystemDefault, NamedDevice };

struct AudioOutputPreferenceV1 {
    AudioDeviceMode deviceMode;
    string openalDeviceSpecifier;
    HrtfMode hrtfMode;
    string namedHrtfProfile;
};
```

`HrtfMode` is defined by architecture 037.

## 9. Audio device enumeration/selection

When supported, use `ALC_ENUMERATE_ALL_EXT` / `ALC_ALL_DEVICES_SPECIFIER` to populate named playback devices.

```text
SystemDefault:
    alcOpenDevice(NULL)

NamedDevice:
    alcOpenDevice(selected exact OpenAL specifier)
```

The current development machine's Bluetooth or AE-7 endpoint names are never special-cased.

On a runtime device change, prefer `ALC_SOFT_reopen_device` where supported and appropriate; otherwise rebuild the device/context while preserving logical audio state per architecture 035.

## 10. HRTF selection

The UI exposes architecture-037 modes:

```text
Auto
Off
On
NamedProfile
```

After apply/reset, query and publish actual HRTF status/profile. Requested `On` does not imply actual-on.

## 11. Device loss/fallback

If a named audio device disappears:

```text
retain saved preferred device
enter recovery/silent state as needed
optionally open SystemDefault as a temporary fallback
report requested device != actual device
retry preferred device according to normal recovery policy
```

Never overwrite the user's stored choice merely because a device is temporarily absent.

## 12. Primary qualification profile

Target-machine acceptance runs use:

```text
CPU: Intel Core i9-9900K
GPU: Intel Arc B580 / Mesa ANV
RenderExtent: 1920x1080
output target: 60 Hz
frame target: sustained close to 60 FPS
HDR quality profile: DisplayHDR 600-class when enabled
```

The exact selected physical display and audio endpoint are recorded in each benchmark artifact; they are not implied by this profile.

For an HDR run to be labeled the **DisplayHDR-600-class qualification profile**, the benchmark manifest must also record the resolved active HDR luminance descriptor/target and verify that the active output policy is actually configured for the intended 600-class target. A display capability alone is insufficient. For example, the fresh workstation capture reports a 644-nit display capability but a current KDE peak override of 370 nits; that captured 370-nit active state is a valid runtime test case but must not be mislabeled as the 600-class HDR qualification run.

## 13. Validation matrix

Display regression must include at least:

```text
two distinct displays when available
SDR Off/On capability transition where supported
1920x1080 qualification mode
one non-1080 mode
windowed and fullscreen/borderless path
refresh-rate mode change where supported
RenderExtent NativeOutput and Explicit
```

Audio regression must include at least:

```text
SystemDefault endpoint
explicit named endpoint
HRTF Off
HRTF On/Auto when supported
device reopen/change
selected-device disconnect/recovery
```

The current workstation's DP HDR display + HDMI SDR display and Bluetooth + AE-7 routes are useful local fixtures for this matrix, not required hardware for players.

## 14. SDL/OpenAL API basis

The display contract relies on SDL3 APIs documented for SDL 3.2+ and present in the installed SDL3 3.4.14 runtime:

```text
SDL_GetDisplays
SDL_GetFullscreenDisplayModes
SDL_SetWindowFullscreenMode
SDL_SetWindowFullscreen
SDL_GetDisplayForWindow
SDL_WINDOWPOS_UNDEFINED_DISPLAY / SDL_WINDOWPOS_CENTERED_DISPLAY
```

Relevant SDL documentation:

- https://wiki.libsdl.org/SDL3/SDL_GetFullscreenDisplayModes
- https://wiki.libsdl.org/SDL3/SDL_SetWindowFullscreenMode
- https://wiki.libsdl.org/SDL3/SDL_SetWindowFullscreen
- https://wiki.libsdl.org/SDL3/README-wayland

The audio contract relies on standard ALC device enumeration plus OpenAL Soft extensions already observed in the fresh audio capture, including `ALC_ENUMERATE_ALL_EXT`, `ALC_SOFT_HRTF` and `ALC_SOFT_reopen_device`.
