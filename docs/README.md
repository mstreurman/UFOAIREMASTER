# UFO: Alien Invasion Remaster — Design & Architecture

This directory contains the initial design and architecture baseline for the UFO: Alien Invasion remaster.

## Current non-negotiable decisions

- The canonical UFO: Alien Invasion game state, rules, balance, AI, progression, tactical outcomes, strategic outcomes, and other gameplay-authoritative behavior remain unchanged unless a future decision explicitly changes project scope.
- Presentation systems are consumers of canonical game state. They do not become authoritative sources of gameplay state.
- Presentation physics is allowed and encouraged, but it is strictly non-authoritative.
- Intel Arc B580 / Battlemage / Xe2 is the primary graphics target.
- The primary **performance qualification profile** is Arc B580 + i9-9900K at RenderExtent 1920×1080, 60 Hz / sustained close to 60 FPS, with DisplayHDR 600-class HDR quality when enabled. Resolution, refresh, display selection and HDR state are runtime-selectable and are not hardcoded to the development workstation.
- Vulkan 1.4 is the graphics API.
- `VK_EXT_descriptor_heap` is the production resource-binding model from the first renderer implementation; no descriptor-buffer fallback is required.
- Hardware ray tracing is a first-class renderer feature.
- `VK_KHR_ray_tracing_pipeline` is the preferred RT mechanism.
- `VK_KHR_ray_query` is exceptional and requires benchmark-backed justification.
- OpenAL Soft is the audio implementation target. Playback device (system default or named endpoint) and HRTF mode/profile are runtime-selectable; the currently connected Bluetooth/AE-7 routes are test fixtures, not hardcoded defaults.
- EFX is required for environmental audio processing.
- Fedora 44 KDE/Wayland is the initial reference development environment.
- Intel Core i9-9900K / Coffee Lake Refresh is the primary CPU optimization target; CPU-specific SIMD/intrinsics and cache-aware optimizations are permitted when benchmarked.
- Jolt Physics is the accepted presentation-only physics engine.
- Fedora Linux 44 is the specifically supported primary platform.
- The renderer baseline is hybrid deferred raster + dedicated RT pipelines, with rasterized primary visibility.
- The tactical client is specified as separate canonical mirror, interaction state, and Presentation World layers.
- The Presentation World is a custom component-based runtime with generational presentation IDs, dense component stores, controlled structural mutation and immutable renderer extraction.
- Animation/skeleton evaluation runs on the i9-9900K; skinned vertex generation runs in Vulkan compute on the Arc B580 and feeds both raster and RT geometry.
- The canonical UFO:AI BSP/common spatial path remains authoritative; modern map presentation is compiled into a separate source-hash-matched runtime asset per map/RMA tile.
- The map semantic inventory accounts for all current game/client map entity classes and parser keys, all defined `SURF_*`/`CONTENTS_*` semantics, terrain lookup dependencies, dynamic inline-model routing, radar/RMA dependencies, and the observed campaign save boundary.
- The complete existing tactical `EV_*` protocol remains preserved during migration; prototype presentation subsets require legacy fallback.

## Normative authority map

Where an earlier overview conflicts with a later accepted specification, use these current authorities:

```text
Canonical gameplay authority       ADR-001, ADR-010, ADR-014
Canonical spatial preservation     architecture 075
Presentation World/storage         ADR-011, architecture 006
Frame Graph/resource state         ADR-016, architecture 015–017
GpuMaterial/PBR ABI                ADR-017, architecture 018, generated Slang ABI
HDR/color/output                   ADR-018, architecture 018
RT effects/reconstruction          ADR-019/020, architecture 019–025
BLAS/TLAS                          ADR-021, architecture 026–028
Shader/package ABI                 architecture 029, 056, 061, 070
Shader temporal/light/DDGI ABI     architecture 057, 062, 067, 068
DDGI warm-start cache              ADR-044, architecture 085/088
Deterministic/static identity      architecture 058, 064, 068, 071
Runtime asset-family registry      architecture 031
CPU topology/job/Jolt scheduling   ADR-023/024, architecture 032–038
Audio runtime                      ADR-024/042, architecture 035–038
VFX                                ADR-025, architecture 039–042
UI                                 ADR-026, architecture 043–046
Instrumentation/replay/RT debug    ADR-027, architecture 047–050, 055, 060
World units/matrix/winding         ADR-028, architecture 051
Render identity/TLAS/frame life    ADR-028, architecture 052
Core GPU scene v1 ABI              architecture 059, 063, 071
Legacy UI/map migration policy     architecture 054
Legacy renderer/sound migration    architecture 076
Campaign/cgame coupling            architecture 077
Strategic/Geoscape separation      architecture 078
Cinematic/video boundary           architecture 079
Implementation sequencing          architecture 080
Budget/debug provenance            architecture 055
Texture/output/audio identity      ADR-029/030/031, architecture 060, 063, 065, 071
Render/output/UI extents           ADR-032/046, architecture 072/090
Runtime display/audio selection     ADR-046, architecture 035/037/081/090
Target optimization benchmarks     ADR-032, architecture 073
GPU memory commitment/residency    ADR-032, architecture 030, 070, 074
B580/Xe2 static hardware facts     reference-arc-b580-xe2-microarchitecture.md
Current local workstation state    reference-current-development-machine-2026-09-04-104103.md
Current local audio/routing state   reference-current-audio-state-2026-09-04-104754.md
Current Jolt provisioning state       reference-current-jolt-provisioning-2026-09-04-121547.md
Historical workstation snapshot     reference-local-development-state-2026-09-04.md
Current B580 Vulkan runtime          reference-local-vulkan-state-2026-09-04-mesa-26_2_2.md
Third-party dependency manifest    reference-third-party-toolchain-manifest.md
Resolved decision register         design/001-decisions-required-for-implementation-complete-baseline.md
Fedora SDL3 platform/input         ADR-033, architecture 081
Pinned Jolt acquisition            ADR-034, architecture 082
Pinned Slang/compiler identity      ADR-047, ADR-034, architecture 029
Descriptor-heap production binding  ADR-045, architecture 087/089
Tactical fidelity exceptions        ADR-042/043, architecture 004/005
FFmpeg cinematic backend           ADR-035, architecture 079/083
Transparency/RT edge policy        ADR-036, architecture 084
Jolt ragdoll v1 policy             ADR-037, architecture 082
Skeleton joint limit               ADR-038, architecture 007/085
Reference-v1 binary ABIs           ADR-039, architecture 085
Local crash/privacy                ADR-040, architecture 086
```

Earlier documents remain useful for rationale/history but must not redefine an ABI or ownership rule that a later authority above has explicitly locked.

## Documents

### Design

- `design/000-remaster-scope-and-preservation.md`
- `design/001-decisions-required-for-implementation-complete-baseline.md`
- `design/002-baseline-031-deep-audit-decision-gates.md`
- `design/003-descriptor-heap-adoption-decision-gate.md`

### Architecture

- `architecture/000-presentation-architecture-principles.md`
- `architecture/001-legacy-system-boundaries.md`
- `architecture/002-renderer-frame-architecture.md`
- `architecture/003-presentation-world-and-event-bridge.md`
- `architecture/004-tactical-event-catalog.md`
- `architecture/005-tactical-event-dependency-matrix.md`
- `architecture/006-presentation-world-cpp-api-and-data-layout.md`
- `architecture/007-transform-skeleton-animation-data-layout.md`
- `architecture/008-map-bsp-and-presentation-asset-pipeline.md`
- `architecture/009-canonical-vs-presentation-map-data-matrix.md`
- `architecture/010-map-entity-class-and-field-matrix.md`
- `architecture/011-surface-content-terrain-semantics-matrix.md`
- `architecture/012-vulkan-device-contract-and-feature-chain.md`
- `architecture/013-descriptor-buffer-and-gpu-scene-abi.md`
- `architecture/014-gpu-memory-queues-frame-context-and-pipeline-persistence.md`
- `architecture/015-exact-frame-graph-api.md`
- `architecture/016-resource-state-and-synchronization-model.md`
- `architecture/017-frame-graph-compilation-and-execution.md`
- `architecture/018-gbuffer-material-and-color-implementation-spec.md`
- `architecture/019-world-space-rt-shadows-reflections-ddgi.md`
- `architecture/020-rt-quality-scaling-and-reconstruction-policy.md`
- `architecture/021-shared-temporal-validation-and-shadow-reconstruction.md`
- `architecture/022-restir-di-history-and-local-direct-reconstruction.md`
- `architecture/023-reflection-temporal-variance-and-atrous-reconstruction.md`
- `architecture/024-ddgi-probe-history-relocation-and-gather.md`
- `architecture/025-denoiser-framegraph-passes-and-b580-benchmarks.md`
- `architecture/026-exact-blas-partitioning-build-and-lifetime-policy.md`
- `architecture/027-exact-tlas-instance-abi-mask-and-visibility-policy.md`
- `architecture/028-acceleration-structure-framegraph-lifecycle-and-b580-benchmarks.md`
- `architecture/029-slang-shader-compiler-and-rshader-package-spec.md`
- `architecture/030-exact-b580-gpu-memory-allocator.md`
- `architecture/031-runtime-asset-binary-format-family.md`
- `architecture/032-exact-i9-9900k-job-system-api-and-topology.md`
- `architecture/033-exact-cpu-frame-schedule-and-jolt-integration.md`
- `architecture/034-cpu-ownership-determinism-budgets-and-9900k-benchmarks.md`
- `architecture/035-openal-device-context-audio-thread-and-snapshot.md`
- `architecture/036-audio-voice-virtualization-buses-and-streaming.md`
- `architecture/037-efx-hrtf-environments-and-acoustic-occlusion.md`
- `architecture/038-audio-frame-schedule-telemetry-and-benchmarks.md`
- `architecture/039-gpu-particle-runtime-simulation-compaction-and-rendering.md`
- `architecture/040-world-space-decals-gbuffer-and-rt-hit-material-overlays.md`
- `architecture/041-volumetrics-vfx-lights-ribbons-beams-and-jolt-debris.md`
- `architecture/042-vfx-framegraph-quality-scaling-telemetry-and-b580-benchmarks.md`
- `architecture/043-retained-ui-runtime-node-layout-input-and-animation.md`
- `architecture/044-typed-ui-view-model-intent-and-embedded-view-boundary.md`
- `architecture/045-vulkan-ui-text-hdr-renderer-and-rui-package.md`
- `architecture/046-ui-legacy-compatibility-migration-testing-and-accessibility.md`
- `architecture/047-telemetry-tracing-frame-timing-and-developer-hud.md`
- `architecture/048-canonical-presentation-replay-and-regression-harness.md`
- `architecture/049-rt-false-color-visualizer-and-frame-wide-debug-modes.md`
- `architecture/050-render-probe-crosshair-material-ray-and-temporal-inspector.md`
- `architecture/051-world-space-units-transform-and-matrix-abi.md`
- `architecture/052-render-object-id-framecontext-and-per-frame-tlas-binding.md`
- `architecture/053-exact-core-gpu-scene-v1-abi.md`
- `architecture/054-legacy-ui-lua-and-audited-map-entity-migration-policy.md`
- `architecture/055-frame-budget-hierarchy-and-rt-debug-provenance.md`
- `architecture/056-exact-shader-root-descriptor-and-slang-compile-contract.md`
- `architecture/057-light-restir-ddgi-and-temporal-history-v1-abi.md`
- `architecture/058-deterministic-presentation-commit-and-static-render-identity.md`
- `architecture/059-core-gpu-scene-v1-semantic-and-skinning-abi.md`
- `architecture/060-texture-orientation-output-debug-and-audio-identity-contract.md`
- `architecture/061-pass-data-bindless-registry-and-pipeline-layout-abi.md`
- `architecture/062-local-light-shape-orientation-intensity-and-restir-sampling.md`
- `architecture/063-vulkan-screen-space-index-and-skin-format-contract.md`
- `architecture/064-static-render-key-batching-and-deterministic-rng-contract.md`
- `architecture/065-pipeline-cache-overflow-time-and-audio-id-cleanup.md`
- `architecture/066-asset-id-container-content-and-source-hash-v1-abi.md`
- `architecture/067-exact-restir-di-estimator-and-sample-codec.md`
- `architecture/068-exact-presentation-rng-stream-assignments.md`
- `architecture/069-raster-front-face-projection-and-rt-parity-validation.md`
- `architecture/070-rshader-layout-hash-material-and-set0-publication-abi.md`
- `architecture/071-static-key-source-values-gpu-time-and-abi-authority-cleanup.md`
- `architecture/072-render-output-ui-extent-and-swapchain-contract.md`
- `architecture/073-b580-9900k-optimization-benchmark-gates.md`
- `architecture/074-b580-memory-commit-and-texture-residency-policy.md`
- `architecture/075-canonical-spatial-service-preservation-map.md`
- `architecture/076-legacy-renderer-and-sound-migration-map.md`
- `architecture/077-campaign-cgame-coupling-map.md`
- `architecture/078-strategic-geoscape-presentation-separation-contract.md`
- `architecture/079-cinematic-video-source-boundary-and-decision-gate.md`
- `architecture/080-implementation-migration-roadmap.md`
- `architecture/081-fedora-sdl3-window-input-hdr-bootstrap-contract.md`
- `architecture/082-jolt-v5_6-presentation-physics-integration-contract.md`
- `architecture/083-ffmpeg-cinematic-decode-and-presentation-contract.md`
- `architecture/084-transparency-glass-water-alpha-test-and-ray-offset-contract.md`
- `architecture/085-reference-v1-persisted-and-runtime-record-abis.md`
- `architecture/086-local-crash-diagnostics-symbol-and-bundle-contract.md`
- `architecture/087-vk_ext_descriptor_heap-and-slang-migration-gate.md`
- `architecture/088-rdgi-ddgi-user-cache-container.md`
- `architecture/089-exact-descriptor-heap-gpu-binding-abi.md`
- `architecture/090-runtime-display-audio-selection-and-target-profile-contract.md`
- `architecture/091-implementation-execution-strategy.md`

### Architecture Decision Records

- `adr/ADR-001-canonical-gameplay-preservation.md`
- `adr/ADR-002-arc-b580-primary-gpu-target.md`
- `adr/ADR-003-vulkan-1.4-rt-pipeline-policy.md`
- `adr/ADR-004-openal-soft-efx-audio.md`
- `adr/ADR-005-non-authoritative-presentation-physics.md`
- `adr/ADR-006-intel-i9-9900k-primary-cpu-target.md`
- `adr/ADR-007-jolt-presentation-physics.md`
- `adr/ADR-008-fedora-44-primary-platform.md`
- `adr/ADR-009-hybrid-deferred-rt-frame-architecture.md`
- `adr/ADR-010-preserve-complete-tactical-event-protocol.md`
- `adr/ADR-011-custom-presentation-world-data-model.md`
- `adr/ADR-012-cpu-skeleton-gpu-compute-skinning.md`
- `adr/ADR-013-canonical-bsp-presentation-map-split.md`
- `adr/ADR-014-map-semantic-compatibility-contract.md`
- `adr/ADR-015-arc-b580-vulkan-gpu-foundation.md`
- `adr/ADR-016-frame-graph-owns-resource-state-and-inter-pass-synchronization.md`
- `adr/ADR-017-gbuffer-and-pbr-material-abi.md`
- `adr/ADR-018-acescg-aces2-hdr-color-pipeline.md`
- `adr/ADR-019-world-space-ray-traced-lighting-policy.md`
- `adr/ADR-020-effect-specific-rt-denoising-and-reconstruction.md`
- `adr/ADR-021-blas-partitioning-and-single-frame-tlas-policy.md`
- `adr/ADR-022-offline-content-to-gpu-contract.md`
- `adr/ADR-023-i9-9900k-job-system-and-cpu-frame-schedule.md`
- `adr/ADR-024-openal-soft-presentation-audio-runtime.md`
- `adr/ADR-025-world-space-vfx-particles-decals-and-volumetrics.md`
- `adr/ADR-026-retained-ui-runtime-view-model-and-vulkan-hdr-policy.md`
- `adr/ADR-027-instrumentation-profiling-replay-regression-and-rt-inspection.md`
- `adr/ADR-028-implementation-contract-hardening.md`
- `adr/ADR-029-shader-identity-temporal-contract-closure.md`
- `adr/ADR-030-final-shader-descriptor-screen-space-contract-closure.md`
- `adr/ADR-031-asset-identity-restir-raster-and-replay-contract-closure.md`
- `adr/ADR-032-target-hardware-optimization-normalization.md`
- `adr/ADR-033-sdl3-fedora-window-input-platform-layer.md`
- `adr/ADR-034-pinned-jolt-and-slang-acquisition.md`
- `adr/ADR-035-ffmpeg-cinematic-backend.md`
- `adr/ADR-036-transparent-glass-water-and-rt-edge-policy.md`
- `adr/ADR-037-post-death-full-body-ragdoll-v1.md`
- `adr/ADR-038-maximum-256-joint-skeleton-v1.md`
- `adr/ADR-039-reference-first-binary-abi-policy.md`
- `adr/ADR-040-local-only-crash-diagnostics-and-privacy.md`
- `adr/ADR-041-slang-2026_16_1-and-descriptor-heap-evaluation.md`
- `adr/ADR-042-preserve-legacy-footstep-spatialization-v1.md`
- `adr/ADR-043-use-transmitted-security-camera-direction.md`
- `adr/ADR-044-disposable-rdgi-ddgi-warm-start-cache.md`
- `adr/ADR-045-descriptor-heap-from-initial-renderer-implementation.md`
- `adr/ADR-046-runtime-presentation-configurability-vs-target-optimization.md`
- `adr/ADR-047-slang-2026_17-current-shader-compiler-pin.md`

### Reference

- `reference/reference-development-platform.md`
- `reference/reference-current-development-machine-2026-09-04-104103.md`
- `reference/reference-current-audio-state-2026-09-04-104754.md`
- `reference/reference-current-build-environment-readiness-2026-09-04-120248.md`
- `reference/reference-current-jolt-provisioning-2026-09-04-121547.md`
- `reference/reference-local-development-state-2026-09-04.md`
- `reference/reference-local-vulkan-state-2026-09-04-mesa-26_2_2.md`
- `reference/reference-arc-b580-vulkan-capabilities.md`
- `reference/reference-arc-b580-xe2-microarchitecture.md`
- `reference/reference-third-party-toolchain-manifest.md`

### Public documentation scope


Cross-cutting contracts are explicit for:

```text
per-FrameContext TLAS binding
RenderObjectId lifetime/static hit identity
deterministic presentation structural commit
world units/scale/matrices/winding
explicit Slang column-major compilation
exact four-address shader root
exact pass-data BDA path
persistent bindless texture/sampler lifetime
fixed persistent heap capacities + shader-binding ABI hash
per-queue FrameContext completion
core GPU scene semantic/layout ABI
exact local-light shapes/orientation/sampling
light ID + generation / ReSTIR packed ABI
DDGI shader metadata
positive-height Vulkan viewport / NDC->UV convention
jitter-inclusive temporal motion
shared raster/RT index enum
baseline eight-influence skin format
GPU skinning input/output binding
exact StaticRenderKey serialization
RenderObjectId batching boundaries
counter-based deterministic Philox RNG
runtime UV/normal-map convention
legacy UI Lua compatibility
presentation-only entity baking
budget hierarchy
RT diagnostic provenance/output luminance
audio asynchronous identity + voice/emitter generation
```

Baseline 031 decision closure is complete:

```text
PLATFORM-001      ACCEPTED
DEPS-JOLT-001     ACCEPTED
DEPS-SLANG-001    ACCEPTED
VIDEO-001         ACCEPTED
RENDER-EDGE-001   ACCEPTED
JOLT-POLICY-001   ACCEPTED
ANIM-001          ACCEPTED
ABI-REF-001       ACCEPTED
CRASH-001         ACCEPTED
```

The Baseline 032 fidelity/cache decisions and Baseline 033 descriptor-heap decision are now closed. Remaining work is implementation, conformance testing, measurement, content tuning and release qualification.

## Historical Baseline 025 closure summary (superseded by later baselines)

The current baseline additionally fixes:

```text
NormalizeAssetPathV1 / AssetId128V1
exact common .r* header/chunk/CRC ABI
semantic ContentHash256
canonical SourceHash256
exact ReSTIR DI estimator/sample codecs
exact Philox production stream assignments
validated CCW raster/front-face parity
historical PipelineLayoutAbiHash/.rshader META (superseded by ShaderBindingAbiHash256 v2)
exact MaterialClass/MaterialFlags values
historical Set-0 publication rule (now persistent sampled-image heap publication)
exact StaticRenderKey source identities
GpuInstance draw-index cleanup
split high/low GPU presentation time
```

Remaining work is primarily implementation sequencing, optimized compression, ray-origin/alpha-test details, DDGI allocator/tuning, particle ABI, UI visual details, platform bootstrap, benchmark tuning, and higher-level trace/replay/probe packing.

## Historical Baseline 026 target-hardware normalization summary (superseded by later baselines)

Baseline 026 additionally fixes:

```text
RenderExtent 1920x1080 is distinct from OutputExtent swapchain pixels
UiLogicalExtent 1920x1080 is distinct from UiRasterExtent = OutputExtent
scene scaling occurs before output-resolution UI and transfer encoding
fixed B580 bindless ABI is 65,536 sampled images + 256 samplers
old 16K->1K descriptor fallback is removed
allocator block sizes are lazy growth units rather than eager startup commitments
memory pressure evicts whole unreferenced textures, not live mips
static B580/Xe2 hardware facts are documented separately from Vulkan/runtime measurements
CPU compiler/LTO/PGO optimization is benchmark-gated
GPU-driven indirect submission is a mandatory post-bring-up benchmark
compact skin formats are benchmark-gated
RT position fetch is benchmark-gated
transient aliasing/XMX/extra spirv-opt remain measured-only
```

Static B580/Xe2 hardware reference now records Intel-published:

```text
20 Xe-cores
5 render slices
160 Vector Engines
160 XMX engines
20 RT units
8 hardware threads / Vector Engine
1280 hardware threads
18 MB L3
256 KB L1 / Xe-core
128 KB SLM / Xe-core
subgroups 16 and 32
12 GB GDDR6
192-bit memory interface
456 GB/s memory bandwidth
Xe2 RTU:
    3 traversal pipelines
    18 box intersections
    2 triangle intersections
```

Remaining work is primarily implementation/migration/bootstrap sequencing and the benchmark artifacts that determine which optional target optimizations become measured wins.

## Historical Baseline 027 Intel RT guidance hardening summary

Baseline 027 adds direct Intel-source traceability for the already accepted RT-pipeline-first policy without changing renderer scope or gameplay behavior.

```text
Intel Arc RTRT developer guide is now an explicit hardware-reference source
Xe2 TSU presence is explicitly recorded from Intel's Xe2 architecture material
Ray Query synchronous/TSU-bypass rationale is documented with scope caveat
RT pipeline remains the substantial-workload default
Ray Query remains a narrow benchmark-only exception
Ray Query comparison now charges software sorting/classification and whole-frame cost
SLM/groupshared interaction with RT is an explicit B580 benchmark hypothesis
```

The Xe-HPG-era Intel guide is not treated as a direct B580 performance measurement. Xe2 documentation establishes TSU presence; actual Vulkan crossover behavior remains measured on the Arc B580.



## Historical Baseline 028 local development-state normalization summary

Baseline 028 records the actual 2026-09-04 Fedora workstation/source state separately from accepted architecture intent.

```text
confirmed workstation:
    Fedora 44 / kernel 7.1.8-200.fc44.x86_64
    i9-9900K 8C/16T with AVX2/FMA/BMI1/BMI2/AES/PCLMUL/ADX-class ISA
    Arc B580 BMG G21 / xe kernel driver
    Mesa 26.1.8 / Arc Vulkan API 1.4.354

confirmed toolchain:
    GCC 16.2.1
    Clang 22.1.8
    CMake 4.3.0
    Ninja 1.13.2
    Meson 1.11.2
    Git 2.55.0
    shaderc/glslc 2026.1
    glslang 16.2.0
    SPIR-V Tools 2026.1
    Vulkan development + validation packages
    OpenAL Soft development packages
    SDL3 development packages
    Intel oneAPI / Level Zero / IGC / ocloc stack

confirmed checkout/build:
    master @ 763173ed036ebbee32c2a7bf6aefa19748df89ff
    origin = remaster fork
    upstream = ufoaiorg/ufoai
    no submodules reported
    build-f44 configured
    build-f44/ufo present
    build-f44/ufoded present
    build-f44/base/game.so present

selected/documented at the time but not confirmed present:
    Jolt source/integration
    Slang compiler/source

installed and, as of Baseline 031, now accepted architecturally:
    SDL3 as the Fedora platform/window/input bootstrap
```

The dated local-state record remains the authority for what was physically present at capture time. Later ADRs may close architecture choices without retroactively claiming that a dependency was installed. Baseline 031 closes SDL3/Jolt/Slang policy while Jolt and Slang remain unconfirmed as locally provisioned.

## Historical Baseline 030 source-boundary remediation summary

Baseline 030 fixes every Baseline 029 finding that can be resolved from accepted architecture and the exact canonical source revision without inventing a new project preference.

Added/normalized:

```text
canonical game_import_t spatial preservation map
legacy renderer/sound migration map
campaign/cgame direct-coupling inventory
typed StrategicSnapshot/StrategicIntent/Geoscape separation contract
cinematic/video source and preservation boundary
executable M0-M13 migration roadmap
third-party reproducibility manifest
central explicit decision register with recommendations
stale animation 8-influence and dynamic-BLAS wording removed
architecture-status wording no longer overclaims whole-project completeness
```


## Baseline 031 decision/ABI closure summary

Baseline 031 adds ADR-033–040 and architecture 081–086. It locks SDL3 platform integration, exact Jolt/Slang acquisition policy, FFmpeg cinematics, transparency/glass/water/RT edge behavior, post-death-only full ragdolls, the 256-joint ceiling, reference-v1 persisted/runtime records, and local-only crash diagnostics. All Baseline 029/030 architecture blockers are resolved; future changes to these decisions require explicit ADR/version updates.


## Baseline 033 Slang / descriptor-heap update summary

Baseline 033 updates the accepted offline shader compiler from Slang v2026.14 to **v2026.16.1**, pins the official Linux x86-64 glibc-2.27 artifact and SHA-256, and records Slang's `SPV_EXT_descriptor_heap` / direct descriptor-heap syntax. Mesa 26.2.x/ANV makes the same Vulkan extension relevant to the Arc B580 target.

Baseline 035 records the post-install proof that the Arc B580 is running Mesa 26.2.2 and exposes `VK_EXT_descriptor_heap`, both heap feature booleans, and the full B580 heap property block. Baseline 036 then resolves `DESCRIPTOR-HEAP-001` in favor of descriptor heap from initial implementation; descriptor buffer is no longer a required renderer path.

## Baseline 036 descriptor-heap-first closure summary

Baseline 036 accepts `DESCRIPTOR-HEAP-001` exactly as directed by the project owner: the Vulkan renderer starts on `VK_EXT_descriptor_heap` rather than implementing descriptor buffers first. ADR-045 and architecture 089 are the production authorities. Heap pipelines use one sampler heap plus one resource heap, null Vulkan pipeline layouts, and `vkCmdPushDataEXT` for the unchanged 32-byte `GpuShaderRoot`. `ShaderBindingAbiHash256` v2 replaces the historical pipeline-layout hash. Descriptor-buffer support remains capability telemetry only.

## Baseline 035 Mesa 26.2.2 runtime-verification summary

Baseline 035 replaces the *current Vulkan runtime* reference from Mesa 26.1.8 to the developer-provided Mesa 26.2.2 B580 capture while preserving the earlier workstation snapshot as historical evidence. The B580 reports 2 GiB sampler/resource descriptor heaps, 64-byte heap alignment, heap capture/replay support and sparse heaps. It also reveals that `VK_EXT_memory_priority` and `VK_EXT_pageable_device_local_memory` are not B580/ANV capabilities in this capture; previous live requirements for those extensions were corrected to project-owned residency policy driven by `VK_EXT_memory_budget`.

Capability extraction must be device-scoped because the same `vulkaninfo` includes llvmpipe with a different extension set.




## Baseline 040 local build-environment readiness closure

Baseline 040 records the successful isolated M0 environment smoke after provisioning. The exact hash-pinned Slang v2026.17 tool cache is present and emits/validates `SPV_EXT_descriptor_heap`; matching `ffmpeg-devel-8.1.2-3.fc44.x86_64` is installed and all required libav pkg-config modules resolve; strict Vulkan DescriptorHeapEXT header/link compilation passes; canonical source/build identity remains unchanged. Fedora SPIR-V Tools 2026.1 validates the heap module under Vulkan 1.4 but lacks newer explicit descriptor-layout CLI switches, so those switches are supplemental when available rather than an M0 prerequisite. Native B580 heap execution remains the authority for queried descriptor layout.

## Baseline 041 Jolt provisioning readiness closure

Baseline 041 records Jolt v5.6.0 commit `e77f175595e64cb44218cc9d9d56fc365ad0e36a` as physically vendored at `third_party/JoltPhysics/` with project sorted-file-manifest BLAKE3-256 `ffe175b315e20631eea26419b65ef225b73e37e3788dd93b66407fb3f37a9df2`. The architecture-082 i9-9900K configuration is verified, static `libJolt.a` builds, and upstream HelloWorld plus UnitTests pass. Jolt is now dependency-ready, but its >=256-body >=10-minute sleep/wake finite-transform stress qualification remains an implementation gate.

Baseline 042 adds the implementation execution strategy in architecture 091. The existing M0-M13 roadmap remains the sequencing authority; the new strategy defines risk-first vertical slices, G0-G7 gates, rollback/default-switch discipline, dependency ownership, early high-risk fixtures, performance evidence rules, and explicit definitions of done for milestones and legacy removal.

## Baseline 038 current-machine / runtime-configurability normalization summary

Baseline 038 uses the fresh 10:41 broad workstation capture and 10:47 audio capture as current local-state authority. It records kernel 7.1.12, KDE 6.7.4 Wayland, locally installed Mesa 26.2.2 RPMs, SDL3 3.4.14, OpenAL Soft 1.24.2, FFmpeg 8.1.2 runtime, current display/HDR state and the Bluetooth A2DP/aptX-HD default audio route. Jolt and Slang remain unprovisioned; FFmpeg development pkg-config modules remain unconfirmed.

ADR-046/architecture 090 make the policy explicit: B580+i9-9900K is the aggressive optimization and 1920x1080/60/DisplayHDR-600-class performance target, **not a hardcoded runtime configuration**. Users can choose display, resolution, refresh, HDR, render-resolution mode, playback device and HRTF; requested and actual state are reported separately.
