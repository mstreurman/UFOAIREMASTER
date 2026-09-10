# UFO: Alien Invasion Remaster

A preservation-first technical remaster of **UFO: Alien Invasion**.

The goal is not to redesign the game. The goal is to keep canonical UFO:AI gameplay, campaign logic, tactical rules, event semantics and content identity intact while replacing aging presentation/runtime technology with a modern, testable implementation.

This repository is based on the upstream UFO:AI source tree at:

```text
763173ed036ebbee32c2a7bf6aefa19748df89ff
```

The remaster architecture and implementation strategy live in the current accepted design baseline under [`docs/`](docs/README.md).

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
- C++26 for new remaster runtime code, with retained canonical/legacy code kept C++11 initially behind a narrow C++11-compatible value boundary;
- OpenAL Soft >=1.25.2 as the reference audio implementation, using the stable OpenAL 1.1 API with required EFX/HRTF capability checks, runtime-selectable output device and HRTF policy;
- Jolt v5.6.0 for **presentation-only** physics;
- FFmpeg for cinematic/video migration;
- deterministic offline runtime-asset generation;
- legacy source-content import for supported maps, models, textures and audio without preserving the old mod/UI/renderer ABI;
- aggressive optimization for the Intel Core i9-9900K + Intel Arc B580 reference workstation;
- runtime configurability that remains separate from hardware-specific optimization.

The reference performance profile is **1920x1080, 60 Hz, sustained close to 60 FPS, DisplayHDR-600-class output when HDR is enabled and correctly qualified**. That is an optimization and qualification target, not a hardcoded runtime configuration.

The accepted toolchain hardening baseline is equally explicit: new remaster runtime targets use strict **C++26** on the GCC 16.2.x reference compiler family, retained canonical/legacy targets stay C++11 initially, and shared bridge headers remain C++11-compatible. Vulkan requires core **1.4+** while development headers/registry/validation track an accepted current 1.4.x revision rather than hard-pinning a patch number. Slang remains exactly pinned to **v2026.17**. OpenAL keeps the stable **OpenAL 1.1** API contract while the new production audio runtime targets **OpenAL Soft >=1.25.2** with required EFX/HRTF capability checks. Architecture 092 is the normative language/toolchain authority.

## Non-negotiable rules

1. **Canonical gameplay stays authoritative.** Presentation systems do not decide game outcomes.
2. **Migration is incremental.** Risky new paths are proved before they replace legacy paths.
3. **New default and legacy deletion are separate steps.** We do not make a risky replacement the default and delete its rollback path in the same change.
4. **Measured evidence beats assumptions.** B580/i9-specific decisions must be supported by validation, benchmarks or captured runtime capability data.
5. **Builds stay bisectable.** Mergeable implementation units must remain buildable and testable.
6. **Runtime settings stay runtime settings.** Display, resolution, refresh, HDR, audio device and HRTF are selectable rather than baked into the engine.
7. **Legacy backends are migration tools, not permanent products.** OpenGL and the old mixer are removed once their modern replacements have been defaulted, soaked and separately decommissioned.
8. **Legacy source-content import is not legacy mod compatibility.** Supported maps/models/textures/audio may be imported or converted; old gameplay mods, GUI/Lua ABI, renderer internals and source-patch total conversions are not compatibility constraints.
9. **Language standard follows architectural ownership.** Retained canonical/legacy targets stay C++11 initially; new remaster runtime targets use strict C++26; shared canonical/remaster headers stay C++11-compatible until the lower side is deliberately migrated.
10. **Canonical saves and gameplay wire semantics are compatibility boundaries.** Within the current compatibility epoch, remaster-only presentation/runtime state must not fork the inherited campaign save format or tactical client/server protocol; intentional incompatibility requires an explicit version/epoch decision and qualification plan.

See [`docs/architecture/091-implementation-execution-strategy.md`](docs/architecture/091-implementation-execution-strategy.md) for the execution contract.

## Current implementation plan

The accepted migration roadmap is [`docs/architecture/080-implementation-migration-roadmap.md`](docs/architecture/080-implementation-migration-roadmap.md).

| Milestone | Goal |
| --- | --- |
| **M0** | Reproducible bootstrap and preservation harness — **complete** |
| **M1** | Canonical boundary shims |
| **M2** | Vulkan device/platform foundation |
| **M3** | Offline content/runtime asset foundation + legacy source-content import |
| **M4** | Presentation World + basic raster scene |
| **M5** | Tactical presentation parity + tactical OpenGL retirement |
| **M6** | Strategic/campaign/Geoscape migration + strategic OpenGL retirement |
| **M7** | Retained UI/input + complete OpenGL decommission |
| **M8** | OpenAL/EFX production audio + legacy mixer decommission |
| **M9** | VFX + Jolt presentation physics |
| **M10** | Hardware RT lighting and reconstruction |
| **M11** | Cinematic/video completion |
| **M12** | Performance specialization |
| **M13** | Release hardening and packaging |

### Immediate execution order

M0 is sealed. M1 is actively extracting presentation-facing authority without replacing canonical game rules. The current boundary state is mechanically inventoried and qualified:

```text
strategic authoritative semantics: 58 total
  canonical-applied:               25
  fail-closed pending owners:      33

tactical authoritative semantics:  15 total
  forwarded to server authority:   13
  fail-closed pending helpers:      2

canonical regression:               104/104 twice
canonical verification digest:      33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2
```

The active execution order is:

1. formalize canonical spatial wrappers and tests — **complete**;
2. introduce immutable tactical/strategic publication seams — **complete**;
3. establish C++11-compatible strong presentation identities and C++26 remaster consumers — **complete foundation**;
4. complete the source-derived presentation action inventory and five-way authority classification — **complete, with one later semantic split: 58 strategic + 15 tactical authoritative semantics**;
5. introduce typed intent dispatch without changing canonical rules — **complete contract/catalog foundation**;
6. extract canonical strategic owners from legacy callbacks — **25 strategic semantics qualified so far**, covering campaign time lapse, aircraft/geoscape operations, base/installation lifecycle, facility build/destroy, Research assign/max/stop, and all existing-job Production amount/move/stop operations;
7. publish Research + Production immutable state — **complete**, including `TechnologyId`, stable runtime `ProductionId`, and snapshot-local queue order/state;
8. complete the canonical identity audit — **complete contract pass**, with 17 strong 32-bit domains; stable Production and persisted StoredUfo identity are now implemented/published while Facility, Transfer, Defence and other runtime mappings remain explicit debt;
9. Research owner extraction, all existing-job Production owners, and `CreateProduction` are **complete**; ItemId / aircraft-definition / StoredUfo production subjects are qualified and the legacy/remaster create paths converge on the campaign owner;
10. migrate the remaining employee/team, market, stored-UFO/recovery, transfer, defence, save/load and mission-start authority families behind typed IDs and canonical owners;
11. keep ambiguous or misclassified semantics fail-closed until their canonical contract is proven;
12. once M1 boundary exit criteria are satisfied, bring up the SDL3/Vulkan production platform path;
13. implement frame contexts, allocator and production descriptor-heap runtime;
14. implement Frame Graph + swapchain/output diagnostic frame;
15. build Presentation World and reach tactical Vulkan presentation parity before retiring tactical OpenGL;
16. migrate strategic/Geoscape presentation and retire strategic OpenGL;
17. complete retained UI/text/2D, OpenAL/EFX, VFX/Jolt, RT, FFmpeg cinematic completion, performance specialization and release hardening.

## Readiness checklist

### Design and preservation

- [x] Canonical source revision pinned.
- [x] Tactical event protocol inventoried and preserved.
- [x] Legacy/remaster save-format and tactical-wire compatibility contract made explicit with static ABI guards.
- [ ] Complete bidirectional classic/remaster cross-binary save and multiplayer interoperability qualification before release claims.
- [x] Presentation/canonical authority boundary documented.
- [x] Renderer, RT, UI, audio, asset, replay/cache and platform architectures documented.
- [x] Runtime display/HDR/audio configurability separated from target-machine optimization.
- [x] M0-M13 migration roadmap defined.
- [x] Risk-first implementation execution strategy defined.
- [x] Progressive OpenGL/legacy-mixer decommission policy defined.
- [x] Legacy compatibility narrowed to supported source-content import rather than old mod/runtime ABI preservation.

### Local development environment

- [x] Fedora 44 KDE/Wayland reference workstation captured.
- [x] GCC 16.2.1 / Clang 22.1.8 available; GCC 16.2.x accepted as the initial strict-C++26 reference compiler family.
- [x] CMake 4.3.0 / Ninja 1.13.2 / ccache 4.12.3 available.
- [x] Vulkan headers/loader/tools and validation layer available.
- [x] Intel Arc B580 / Mesa 26.2.2 exposes `VK_EXT_descriptor_heap`.
- [x] SDL3 3.4.14 development environment available.
- [x] OpenAL Soft 1.25.2 is installed on the Fedora 44 reference workstation and the deterministic M0.3 environment manifest has been recaptured/verified at `aa42dc88f980845c94fab1d6ff992657f935f25c13ac418c16aa25f3baa5d305`; M8 still requires the dedicated EFX/HRTF/device-runtime qualification before audio closure.
- [x] FFmpeg 8.1.2 development modules available.
- [x] Slang v2026.17 provisioned and hash-verified.
- [x] Slang emits `SPV_EXT_descriptor_heap` and Fedora SPIR-V Tools validates it for Vulkan 1.4.
- [x] Jolt v5.6.0 vendored at exact commit `e77f175595e64cb44218cc9d9d56fc365ad0e36a`.
- [x] Jolt static library, HelloWorld and upstream UnitTests pass on the reference workstation.

### M0 / high-risk qualification

- [x] Commit repository ownership/ignore rules.
- [x] Add CMake presets and explicit remaster build options.
- [x] Generate reproducible machine/tool/vendor manifest from a clean checkout.
- [x] Add canonical legacy clean-build + launch smoke harness.
- [x] Add canonical regression/replay/reference harness.
- [x] Add migration feature-selection scaffolding.
- [x] Execute native B580 `VK_EXT_descriptor_heap` write/bind/read fixture.
- [x] Execute acceleration-structure heap fixture with the documented 8-byte AS element representation.
- [x] Run Jolt `>=256` dynamic-body, contact-heavy, sleep/wake stress for `>=10` minutes with finite-transform checks.
- [x] Reproduce M0 from a clean checkout without undocumented workstation state.

### M1 / canonical boundary shims

- [x] Canonical spatial-service boundary and preservation tests.
  - [x] Centralize and qualify all 23 canonical spatial bindings.
  - [x] Establish and audit M1 semantic sentinels over the sealed M0 corpus.
  - [x] Add direct executable fixtures for map bounds and core grid/path result semantics.
  - [x] Qualify the remaining stateful routing/world/model/trajectory services; final evidence partition is 7 sentinel + 16 direct = 23/23.
- [x] Introduce typed presentation IDs where required.
  - [x] Introduce the strong canonical `EntityId` used by tactical publication.
  - [x] Define and compile-qualify 17 mutually distinct 32-bit canonical identity domains, including Mission, Aircraft, Base, Installation, Nation, Employee, Technology, Production, Facility, Transfer, DefenceSlot, Message, Item, StoredUfo, UfoSaleOffer and TransferManifest identities.
  - [x] Complete the M1 identity taxonomy/registry so runtime-direct IDs, sidecar-required IDs, structural references, static definition keys, aggregate keys and submission-context tokens cannot be conflated.
  - [x] Reserve `FacilityId`, `TransferId` and `DefenceSlotId` while keeping their legacy mappings explicitly pending rather than fabricating stable identity from mutable indices.
  - [x] Implement runtime-only `ProductionId` in canonical production state so logical jobs retain identity across queue reorder/compaction and loaded jobs receive fresh non-persisted IDs.
  - [x] Qualify persisted `StoredUfoId` directly from `storedUFO_t::idx`, including duplicate-load rejection and allocator reconciliation so removed/stale IDs are never reused.
  - [x] Keep canonical identity domains value-only, C++11-compatible and free of implicit integer or cross-domain conversions.
- [x] Publish immutable tactical snapshots/events without raw canonical pointers.
  - [x] Publish only after canonical client-mirror event mutation, with one monotonic sequence and scheduled presentation time.
  - [x] Confine legacy local-entity access to the adapter; public tactical snapshot/event contracts are value-only.
  - [x] Qualify canonical value projection, ordered publication and immutable/copyable public value types in the dedicated 3-test M1 lane.
- [x] Publish immutable strategic snapshots/view data without raw canonical pointers.
  - [x] Publish one immutable generation after canonical Geoscape frame updates on Main.
  - [x] Project campaign time/credits/selection plus missions, aircraft/UFOs, bases, installations, nations, technologies, production queue state and messages as owning value data.
  - [x] Publish `TechnologyId` directly from canonical technology identity.
  - [x] Publish stable runtime `ProductionId` for each logical production job while retaining `queueIndex` strictly as current location/order metadata.
  - [x] Publish persisted `StoredUfoId` with immutable UFO-yard/status/condition/disassembly/definition state and no raw canonical pointers.
  - [x] Confine campaign/message pointers and message identity mapping to the legacy adapter; reset mapping on new game/load/shutdown.
  - [x] Qualify public pointer isolation, publication ordering, canonical preservation and both production client builds.
- [x] Establish the split C++ language/toolchain boundary before expanding the new runtime.
  - [x] Document C++11 retained canonical/bridge ownership and strict C++26 remaster ownership in Architecture 092.
  - [x] Remove inherited global C++0x standard forcing and assign language modes per target.
  - [x] Move modern publication/runtime ownership into a strict C++26 target while keeping legacy adapters C++11.
  - [x] Replace tactical deprecated `shared_ptr` atomic free functions with `std::atomic<std::shared_ptr<...>>`.
  - [x] Add and qualify a strict C++11 + strict C++26 mixed compile/link/run lane on GCC 16.2.1 / libstdc++.
- [x] Introduce typed intent dispatch without changing canonical rules.
  - [x] Establish the C++11-compatible strategic intent/result value contract.
  - [x] Establish the bounded strict-C++26 intent/result transport with monotonic sequence IDs.
  - [x] Complete the source-derived presentation-action scope and five-way authority classification.
  - [x] Seal typed catalog coverage, then correct one discovered context-dependent conflation: **58 strategic authoritative semantics + 15 tactical semantics** (`CreateProduction` split from legacy `prod_inc`).
  - [x] Preserve the presentation authority guard: no command/cvar fallback in strategic/tactical intent adapters.
  - [x] Forward **13/15 tactical semantics** through the existing server protocol; keep AbortMission and Reload fail-closed until request helpers prove protocol emission.
  - [x] Qualify **25/58 strategic semantics** through campaign-owned canonical owners: campaign time lapse; aircraft mission/return/start/stop/destination/pursuit/homebase; base build/rename; installation build/rename/destroy; facility build/destroy; Research assign/max/stop; all existing-job Production decrease/increase/set-amount/move/stop operations.
  - [x] Keep the remaining **33 strategic semantics fail-closed** until their campaign-owned validation/mutation contracts are extracted or corrected.
  - [x] Complete ItemId + aircraft + StoredUfo production-subject qualification and bridge `CreateProduction` through the canonical campaign owner; facility/defence long-lived mutation still requires stable identity.
- [ ] Keep legacy consumers behind temporary adapters until each owning presentation path migrates.

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
- [ ] Legacy source-content import path for supported maps/models/textures/audio.
- [ ] Presentation World.
- [ ] Basic raster tactical scene.
- [ ] Tactical presentation parity; default Vulkan tactical presentation; retire tactical-only OpenGL ownership.
- [ ] Geoscape/campaign presentation migration; retire strategic OpenGL ownership.
- [ ] Retained UI/input + Vulkan cinematic frame display; complete OpenGL decommission in M7.
- [ ] OpenAL/EFX production audio; remove the legacy mixer in M8 after default/soak evidence.
- [ ] VFX + Jolt presentation physics integration.
- [ ] Hardware RT lighting/reconstruction.
- [ ] FFmpeg cinematic/video completion on the Vulkan/OpenAL presentation stack.
- [ ] B580/i9-9900K performance specialization.
- [ ] Release hardening/packaging after legacy renderer/audio decommission has already completed.

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
Language/runtime        C++26 new remaster runtime; C++11 retained canonical/bridge initially
Reference compiler      GCC 16.2.x / libstdc++
Platform/window/input   SDL3
Graphics                Vulkan >=1.4; accepted current 1.4.x tooling/registry
Shader language/tool    Slang v2026.17 exact pin
Binding model           VK_EXT_descriptor_heap
Primary GPU             Intel Arc B580 / Xe2
Primary CPU             Intel Core i9-9900K
Audio                   OpenAL Soft >=1.25.2 / OpenAL 1.1 + EFX + HRTF
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
- [`docs/architecture/092-cpp26-language-toolchain-and-boundary-contract.md`](docs/architecture/092-cpp26-language-toolchain-and-boundary-contract.md) — C++11/C++26 ownership, compiler/ABI and dependency-version hardening contract.
- [`docs/reference/reference-cpp26-toolchain-audio-hardening-2026-09-07.md`](docs/reference/reference-cpp26-toolchain-audio-hardening-2026-09-07.md) — adoption-time GCC/Vulkan/Slang/OpenAL and canonical-regression evidence.
- [`docs/reference/reference-current-build-environment-readiness-2026-09-04-120248.md`](docs/reference/reference-current-build-environment-readiness-2026-09-04-120248.md) — local build-environment readiness evidence.
- [`docs/reference/reference-current-jolt-provisioning-2026-09-04-121547.md`](docs/reference/reference-current-jolt-provisioning-2026-09-04-121547.md) — exact Jolt provisioning/build evidence.
- [`docs/reference/reference-m1-tactical-publication-2026-09-06.txt`](docs/reference/reference-m1-tactical-publication-2026-09-06.txt) — M1.2 tactical publication qualification evidence.
- [`docs/reference/reference-m1-typed-identity-2026-09-07.txt`](docs/reference/reference-m1-typed-identity-2026-09-07.txt) — M1 typed canonical presentation identity qualification evidence.
- [`docs/reference/reference-m1-strategic-publication-2026-09-07.txt`](docs/reference/reference-m1-strategic-publication-2026-09-07.txt) — M1 immutable strategic publication qualification evidence.

## Build status

M0 is qualified and sealed: the original UFO:AI source, preservation harness and high-risk dependency fixtures reproduce from a clean checkout. The full remaster presentation runtime is **not implemented yet**; the active production phase is M1.

M1 canonical spatial-service work is qualified. Commit `041cf2297426f259dd38df901927cbd715aed261` centralized the 23 import bindings; `85e3c218eb2e84de8d99ba34b77de48e63479dc4` established the M1 semantic sentinel lane; `9e52c5fd286273830d6dd7e2bdd735a00ee4a4e0` added direct map-bounds coverage; and `4ad13451e20b66293d3eb788cdae3150e0f61754` added the core grid/path exact-result bundle.

The closure audit corrected an earlier over-count: `GameTest.Shooting` is currently a placeholder and does not execute `Trace`, while `GameTest.VisFlags` directly supports the entity-aware `TestLineWithEnt` path rather than plain `TestLine`/`GetVisibility`. A dedicated M1-only stateful integration lane now executes the corrected remaining routing/world/model/trajectory services against live canonical map/server state without changing the sealed `src/tests/CMakeLists.txt`. The final evidence partition is 7 sentinel services plus 16 directly qualified services, covering all 23 Architecture-075 spatial services. G0 legacy/remaster builds pass and the sealed M0 canonical regression remains 104/104 tests in both repeatability passes with evidence identity `b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e`.

M1.2 tactical publication is qualified. The tactical client now exposes a strong canonical entity identity and immutable, value-only snapshot/event publication after canonical mirror mutation, with legacy local-entity access confined to an adapter. The dedicated M1 lane passes 3/3 tests; the sealed canonical regression remains 104/104 in both repeatability passes with the same evidence identity; and both legacy and remaster production client builds pass. The qualification transcript is summarized in `docs/reference/reference-m1-tactical-publication-2026-09-06.txt`.

The M1 typed presentation identity contract is also qualified. Tactical `EntityId` remains unchanged, while the strategic/view/intent bridge now defines distinct 32-bit `MissionId`, `AircraftId`, `BaseId`, `InstallationId`, `NationId`, `EmployeeId`, `TechnologyId`, `ProductionId`, `MessageId` and `ItemId` domains. The strict C++11 contract proves domain separation and value semantics, and both qualified production client configurations rebuild successfully.

The M1 strategic publication boundary is qualified. Campaign/Geoscape presentation can now consume an immutable owning snapshot containing typed mission, aircraft/UFO, base, installation, nation and message views plus campaign time/credits and typed selection state. Publication occurs after canonical campaign frame updates; raw campaign/message pointers remain confined to the legacy adapter, and campaign/load reset clears transient message identity mapping.

A post-M1 hardening audit and fresh local validation confirmed 104/104 canonical tests twice with trace repeatability and the same evidence identity, while GCC 16.2.1 reproduced the expected deprecation of the tactical `shared_ptr` atomic free functions. The project has therefore accepted strict C++26 for new remaster runtime targets, retained C++11 for canonical/legacy targets initially, OpenAL Soft >=1.25.2 for eventual production-audio qualification, Vulkan >=1.4 without a patch-level runtime pin, and the existing exact Slang v2026.17 pin. These decisions are documentation-complete; the corresponding build-target split and atomic modernization remain implementation work.

Do not interpret checked design/provisioning/qualification items above as implemented Vulkan/OpenAL presentation features.

## Upstream lineage and licensing

This remaster is derived from the UFO:AI source project and intentionally retains upstream Git history. The original project's licensing and attribution remain governed by the repository's existing [`COPYING`](COPYING) and [`LICENSES`](LICENSES) files.

Vendored Jolt Physics is retained under its MIT license and carries its upstream license in `third_party/JoltPhysics/LICENSE`.

The project-local Slang binary cache under `tools/slang/` is a development dependency and is intentionally not committed as part of this repository publication.

## Status

**Current phase: M1 — canonical boundary shims.**

M0 is complete; the M1 canonical spatial-service workstream, tactical publication, typed presentation identity contract and immutable strategic publication boundary are qualified. The C++11/C++26 target boundary and mixed-standard qualification are now implemented and qualified on GCC 16.2.1 / libstdc++; active M1 implementation continues with typed intent dispatch and temporary legacy-consumer adapters.
