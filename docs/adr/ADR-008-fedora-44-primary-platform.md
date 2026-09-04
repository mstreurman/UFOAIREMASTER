# ADR-008 — Fedora Linux 44 as Primary Platform

**Status:** Accepted  
**Decision type:** Platform / operating system target

## Context

The reference development and runtime machine uses Fedora Linux 44 KDE Plasma Desktop Edition under Wayland.

The project does not currently need to preserve Windows, macOS, or generic cross-platform parity.

The project prioritizes a highly optimized remaster for a known CPU/GPU/software stack.

## Decision

**Fedora Linux 44** is the primary and specifically supported platform for the remaster.

The reference desktop/session environment is:

- Fedora Linux 44;
- KDE Plasma;
- Wayland;
- Linux kernel 7.1.x-class reference;
- Mesa Intel graphics stack;
- Intel `xe` kernel driver for Arc B580.

## Consequences

The remaster may use Fedora/Linux-specific capabilities and assumptions where they materially improve implementation quality, performance, observability, or maintainability.

The architecture does not need to be restricted by Windows/macOS portability requirements.

## Graphics stack

The primary graphics environment is:

```text
Fedora 44
  |
  +-- Wayland
  +-- Mesa
  +-- Intel ANV Vulkan driver
  +-- Intel xe kernel driver
  +-- Intel Arc B580
```

Vulkan 1.4 is the renderer API.

## Platform/window/input layer

A platform abstraction may still be used for:

- window creation;
- Wayland integration;
- keyboard/mouse/controller input;
- Vulkan surface creation;
- clipboard and basic desktop integration.

If SDL3 is adopted for these functions, it is an implementation convenience inside a Fedora-specific engine, not a cross-platform architectural constraint.

Until a bootstrap/platform decision explicitly adopts SDL3 or an alternative, higher-level subsystems such as UI must depend on normalized platform events rather than naming SDL3 as an accepted architectural dependency.

The renderer will use Vulkan directly rather than a higher-level SDL GPU abstraction.

## Audio

OpenAL Soft + EFX is the primary audio runtime on Fedora 44.

## Observed local build state — latest 2026-09-04 capture

The authoritative current workstation snapshot is `reference/reference-current-development-machine-2026-09-04-104103.md`, captured at 10:41:03+02:00 after the Mesa 26.2.2 update. It confirms Fedora 44, kernel 7.1.12, KDE Plasma/KWin 6.7.4 Wayland, GCC 16.2.1, Clang 22.1.8, CMake 4.3.0, Ninja 1.13.2, Meson 1.11.2, Git 2.55.0, SDL3 3.4.14, OpenAL Soft 1.24.2, FFmpeg 8.1.2 runtime libraries and the locally built Mesa 26.2.2 RPM stack.

The checkout remains at `763173ed036ebbee32c2a7bf6aefa19748df89ff` with the existing `build-f44/` CMake/Ninja outputs. A later 2026-09-04 build-environment readiness run provisions the exact pinned Slang v2026.17 tool cache and installs matching RPM Fusion `ffmpeg-devel-8.1.2-3.fc44.x86_64`; the complete isolated environment smoke passes. A subsequent Jolt provisioning run vendors Jolt v5.6.0 commit `e77f175595e64cb44218cc9d9d56fc365ad0e36a` into `third_party/JoltPhysics/`, verifies the project vendor hash, builds static `libJolt.a`, and passes upstream HelloWorld/UnitTests. Project-specific Jolt stress qualification remains pending.

The earlier `reference/reference-local-development-state-2026-09-04.md` remains a historical snapshot and must not override newer observations.

## Build and packaging

Fedora-native build tooling is preferred:

- GCC/G++;
- CMake;
- Ninja;
- pkg-config;
- Fedora development packages.

RPM packaging may be considered later, but is not required by this ADR.

## Portability

Other operating systems are out of scope unless a future project decision explicitly adds them.

Any future portability layer must preserve the Fedora 44 primary path and may not force it into a lowest-common-denominator design.

## Baseline 031 platform closure

The Fedora platform closure is now owned by ADR-033 and architecture 081/086. SDL3 is the accepted window/input/text/IME/Vulkan-surface layer; Vulkan retains swapchain/HDR ownership. The reference install layout, capability probing, local crash-symbol policy and dependency checks are no longer open architecture choices. Desktop/RPM metadata details may be completed during packaging without changing this platform boundary.
