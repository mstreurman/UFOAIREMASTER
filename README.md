# UFO: Alien Invasion Remaster

A preservation-first technical remaster of **UFO: Alien Invasion**.

The goal is not to redesign the game. The goal is to keep canonical UFO:AI gameplay, campaign logic, tactical rules, event semantics and content identity intact while replacing aging presentation/runtime technology with a modern, testable implementation.

This repository is based on the upstream UFO:AI source tree at:

```text
763173ed036ebbee32c2a7bf6aefa19748df89ff
```

The remaster architecture and implementation strategy currently live in **Design Baseline 042** under [`docs/`](docs/README.md).

## Vision

Preserve the game. Modernize the engine around it.

The remaster targets:

- canonical UFO:AI gameplay preservation;
- Vulkan 1.4 rendering;
- `VK_EXT_descriptor_heap` as the production binding model from the first renderer implementation;
- Slang v2026.17 for the shader toolchain;
- hybrid deferred rasterization with dedicated hardware ray tracing;
- HDR output with runtime-selectable display, resolution, refresh rate and HDR mode;
- SDL3 platform/window/input integration;
- OpenAL Soft + EFX with runtime-selectable output device and HRTF policy;
- Jolt v5.6.0 for **presentation-only** physics;
- FFmpeg for cinematic/video migration;
- deterministic offline runtime-asset generation;
- aggressive optimization for the Intel Core i9-9900K + Intel Arc B580 reference workstation;
- runtime configurability that remains separate from hardware-specific optimization.

The reference performance profile is **1920x1080, 60 Hz, sustained close to 60 FPS, DisplayHDR-600-class output when HDR is enabled and correctly qualified**. That is an optimization and qualification target, not a hardcoded runtime configuration.

## Non-negotiable rules

1. **Canonical gameplay stays authoritative.** Presentation systems do not decide game outcomes.
2. **Migration is incremental.** Risky new paths are proved before they replace legacy paths.
3. **New default and legacy deletion are separate steps.** We do not make a risky replacement the default and delete its rollback path in the same change.
4. **Measured evidence beats assumptions.** B580/i9-specific decisions must be supported by validation, benchmarks or captured runtime capability data.
5. **Builds stay bisectable.** Mergeable implementation units must remain buildable and testable.
6. **Runtime settings stay runtime settings.** Display, resolution, refresh, HDR, audio device and HRTF are selectable rather than baked into the engine.

See [`docs/architecture/091-implementation-execution-strategy.md`](docs/architecture/091-implementation-execution-strategy.md) for the execution contract.

## Current implementation plan

The accepted migration roadmap is [`docs/architecture/080-implementation-migration-roadmap.md`](docs/architecture/080-implementation-migration-roadmap.md).

| Milestone | Goal |
| --- | --- |
| **M0** | Reproducible bootstrap and preservation harness |
| **M1** | Canonical boundary shims |
| **M2** | Vulkan device/platform foundation |
| **M3** | Offline content/runtime asset foundation |
| **M4** | Presentation World + basic raster scene |
| **M5** | Tactical presentation parity |
| **M6** | Strategic/campaign/Geoscape migration |
| **M7** | Retained UI and input completion |
| **M8** | OpenAL/EFX production audio |
| **M9** | VFX + Jolt presentation physics |
| **M10** | Hardware RT lighting and reconstruction |
| **M11** | Cinematic/video migration |
| **M12** | Performance specialization |
| **M13** | Legacy removal and release packaging |

### Immediate execution order

The first implementation queue is deliberately risk-first:

1. repository ownership and ignore hygiene;
2. CMake presets/options and dependency discovery;
3. exact tool/RPM/vendor manifest capture;
4. clean canonical legacy build + launch smoke;
5. canonical regression/replay/reference harness;
6. feature-selection/compatibility scaffolding without behavior replacement;
7. native `VK_EXT_descriptor_heap` execution fixture;
8. Slang descriptor-heap ABI/package fixture;
9. Jolt `>=256` body, `>=10` minute sleep/wake finite-transform stress qualification;
10. SDL3/Vulkan production bootstrap;
11. frame contexts, allocator and descriptor-heap runtime;
12. Frame Graph + swapchain diagnostic frame;
13. representative `.rshader` / `.r*` asset-pipeline slice;
14. Presentation World -> first real Vulkan tactical scene.

## Readiness checklist

### Design and preservation

- [x] Canonical source revision pinned.
- [x] Tactical event protocol inventoried and preserved.
- [x] Presentation/canonical authority boundary documented.
- [x] Renderer, RT, UI, audio, asset, replay/cache and platform architectures documented.
- [x] Runtime display/HDR/audio configurability separated from target-machine optimization.
- [x] M0-M13 migration roadmap defined.
- [x] Risk-first implementation execution strategy defined.

### Local development environment

- [x] Fedora 44 KDE/Wayland reference workstation captured.
- [x] GCC 16.2.1 / Clang 22.1.8 available.
- [x] CMake 4.3.0 / Ninja 1.13.2 / ccache 4.12.3 available.
- [x] Vulkan headers/loader/tools and validation layer available.
- [x] Intel Arc B580 / Mesa 26.2.2 exposes `VK_EXT_descriptor_heap`.
- [x] SDL3 3.4.14 development environment available.
- [x] OpenAL Soft 1.24.2 development environment available.
- [x] FFmpeg 8.1.2 development modules available.
- [x] Slang v2026.17 provisioned and hash-verified.
- [x] Slang emits `SPV_EXT_descriptor_heap` and Fedora SPIR-V Tools validates it for Vulkan 1.4.
- [x] Jolt v5.6.0 vendored at exact commit `e77f175595e64cb44218cc9d9d56fc365ad0e36a`.
- [x] Jolt static library, HelloWorld and upstream UnitTests pass on the reference workstation.

### M0 / high-risk qualification

- [ ] Commit repository ownership/ignore rules.
- [ ] Add CMake presets and explicit remaster build options.
- [ ] Generate reproducible machine/tool/vendor manifest from a clean checkout.
- [ ] Add canonical legacy clean-build + launch smoke harness.
- [ ] Add canonical regression/replay/reference harness.
- [ ] Add migration feature-selection scaffolding.
- [ ] Execute native B580 `VK_EXT_descriptor_heap` write/bind/read fixture.
- [ ] Execute acceleration-structure heap fixture with the documented 8-byte AS element representation.
- [ ] Run Jolt `>=256` dynamic-body, contact-heavy, sleep/wake stress for `>=10` minutes with finite-transform checks.
- [ ] Reproduce M0 from a clean checkout without undocumented workstation state.

### Renderer and presentation

- [ ] SDL3 + Vulkan production window/surface/device bootstrap.
- [ ] Runtime display/resolution/refresh/HDR selection.
- [ ] Frame contexts and two-frames-in-flight infrastructure.
- [ ] GPU allocator and resource lifetime model.
- [ ] Production ResourceHeap + SamplerHeap runtime.
- [ ] Frame Graph.
- [ ] Diagnostic swapchain frame.
- [ ] Runtime shader/package pipeline.
- [ ] Runtime asset family and deterministic content conversion.
- [ ] Presentation World.
- [ ] Basic raster tactical scene.
- [ ] Tactical presentation parity.
- [ ] Geoscape/campaign presentation migration.
- [ ] Retained UI/input migration.
- [ ] OpenAL/EFX production audio migration.
- [ ] VFX + Jolt presentation physics integration.
- [ ] Hardware RT lighting/reconstruction.
- [ ] FFmpeg cinematic/video migration.
- [ ] B580/i9-9900K performance specialization.
- [ ] Legacy presentation-code removal after parity/default/rollback gates pass.

## Current target workstation

Primary optimization and qualification target:

```text
CPU:       Intel Core i9-9900K, 8C/16T, AVX2/FMA
GPU:       Intel Arc B580 / Battlemage G21 / Xe2
Driver:    Mesa 26.2.2, xe kernel driver
Desktop:   Fedora 44 KDE Plasma, Wayland
Target:    1920x1080 @ 60 Hz
Frame ref: 16.667 ms
HDR:       DisplayHDR-600-class qualification profile
```

Runtime configuration is not restricted to that profile. The renderer is explicitly designed to select output display, output resolution, refresh rate where supported, HDR Auto/Off/On, render resolution mode, OpenAL playback device and HRTF mode at runtime.

## Key implementation technologies

```text
Platform/window/input   SDL3
Graphics                Vulkan 1.4
Shader language/tool    Slang v2026.17
Binding model           VK_EXT_descriptor_heap
Primary GPU             Intel Arc B580 / Xe2
Primary CPU             Intel Core i9-9900K
Audio                   OpenAL Soft + EFX
Presentation physics    Jolt Physics v5.6.0
Video/cinematics        FFmpeg 8.1.x API family
Build                    CMake + Ninja + ccache
```

The renderer intentionally has **no production descriptor-set fallback** for its heap-based binding architecture.

## Repository layout

Important remaster-owned paths as implementation begins:

```text
docs/                       accepted design/architecture/reference baseline
third_party/JoltPhysics/    vendored Jolt v5.6.0 source snapshot
tools/slang/                local provisioned Slang binary cache; not committed
build-f44/                  local legacy build; not committed
build-jolt-f44/             local standalone Jolt verification build; not committed
```

The legacy UFO:AI source tree remains in its existing upstream layout until individual migration seams are introduced.

## Implementation gates

Every mergeable implementation unit is evaluated against the applicable gates from Architecture 091:

- **G0 — Build**: required targets compile and link.
- **G1 — Component**: focused unit/fixture test passes.
- **G2 — Canonical preservation**: no unauthorized gameplay-state change.
- **G3 — Presentation regression**: affected visible/audible behavior is checked.
- **G4 — API/validation**: Vulkan/SDL/OpenAL/etc. validation is clean where applicable.
- **G5 — Stress/sanitizer**: high-risk paths survive required stress and sanitizer coverage.
- **G6 — Performance**: target-machine claims have benchmark evidence.
- **G7 — Clean bootstrap**: behavior can be reproduced from a clean checkout.

Not every commit needs every gate, but no milestone is complete until all gates applicable to that milestone have passed.

## Documentation

Start here:

- [`docs/README.md`](docs/README.md) — complete design-document index.
- [`docs/architecture/080-implementation-migration-roadmap.md`](docs/architecture/080-implementation-migration-roadmap.md) — M0-M13 roadmap.
- [`docs/architecture/091-implementation-execution-strategy.md`](docs/architecture/091-implementation-execution-strategy.md) — day-to-day implementation method and gates.
- [`docs/reference/reference-current-build-environment-readiness-2026-09-04-120248.md`](docs/reference/reference-current-build-environment-readiness-2026-09-04-120248.md) — local build-environment readiness evidence.
- [`docs/reference/reference-current-jolt-provisioning-2026-09-04-121547.md`](docs/reference/reference-current-jolt-provisioning-2026-09-04-121547.md) — exact Jolt provisioning/build evidence.

## Build status

The original UFO:AI source currently still builds in the existing local `build-f44/` tree. The new remaster runtime is **not implemented yet**; the project is at the start of M0.

Do not interpret checked design/provisioning items above as implemented renderer features.

## Upstream lineage and licensing

This remaster is derived from the UFO:AI source project and intentionally retains upstream Git history. The original project's licensing and attribution remain governed by the repository's existing [`COPYING`](COPYING) and [`LICENSES`](LICENSES) files.

Vendored Jolt Physics is retained under its MIT license and carries its upstream license in `third_party/JoltPhysics/LICENSE`.

The project-local Slang binary cache under `tools/slang/` is a development dependency and is intentionally not committed as part of this repository publication.

## Status

**Current phase: M0 — reproducible bootstrap and preservation harness.**

The architecture is considered implementation-ready. The next work is code, fixtures, reproducibility and qualification—not another broad design rewrite.
