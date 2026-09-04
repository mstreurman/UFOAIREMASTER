# ADR-033 — SDL3 Fedora Window/Input Platform Layer

**Status:** Accepted  
**Decision:** `PLATFORM-001`

## Context

Fedora 44 is the primary platform. The renderer owns Vulkan device, swapchain, HDR, synchronization and frame lifetime, but the project still requires a window/input/text integration layer.

## Decision

Use **SDL3** for:

```text
window creation/destruction
Wayland-facing event integration
keyboard and mouse normalization
gamepad/controller discovery and events
text input and IME composition events
DPI/display/window state events
VkSurfaceKHR creation support
```

SDL3 does **not** own:

```text
Vulkan instance/device selection
swapchain format/present mode/HDR policy
frame graph
queue synchronization
renderer resource lifetime
canonical gameplay input interpretation
```

Architecture 081 owns the exact platform contract.

## Consequences

A native Wayland/libdecor/xkbcommon platform backend is not part of v1. Platform-specific escape hatches may be added only for a capability that SDL3 cannot expose, and must stay behind the same platform interface.
