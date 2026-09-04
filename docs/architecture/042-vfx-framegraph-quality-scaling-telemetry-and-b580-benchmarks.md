# VFX Frame Graph, Quality Scaling, Telemetry and B580 Benchmarks

**Status:** Architecture baseline  
**Related ADR:** ADR-025

## 1. Relevant GPU order

Baseline sequence:

```text
GBuffer
MaterialDecals

RTDirectionalShadow
ReSTIR local direct
DDGI
DeferredLighting

EmissiveDecals

VolumeInject
VolumeDirectionalVisibility
VolumeLight
VolumeIntegrate
VolumeComposite

Transparent world surfaces

ParticleSpawn
ParticleSimulateCompact
ParticleClassify
ParticleAlphaSort
ParticleIndirectBuild
ParticleRender

Ribbon/BeamRender

HDR post
UI
```

Particle simulation may be scheduled earlier if resource dependencies allow; the listed order represents logical consumption/composition.

## 2. Particle Frame Graph resources

Persistent:

```text
ParticleStateA
ParticleStateB
ParticleMaterialTable
```

Per-frame/transient:

```text
SpawnCommands
Alive/visible counters
AdditiveVisibleIndices
AlphaVisibleIndices
AlphaSortKeys
IndirectDrawArgs
```

Frame Graph owns synchronization.

## 3. Particle compute baseline

Starting workgroup:

```text
256 threads
```

for large simple particle simulation/compaction kernels, subject to B580 benchmarking.

Benchmark:

```text
128
256
```

threads/workgroup and subgroup:

```text
16
32
```

Do not assume 8x8 workgroups for one-dimensional particle kernels.

## 4. Sorting benchmark

Compare GPU radix-sort implementations/configurations for:

```text
16k
32k
65k
```

visible alpha particles.

Measure:

```text
sort time
temporary memory
cache behavior
render overdraw
```

Baseline cap remains 65,536 until measured otherwise.

## 5. VFX GPU budget targets

Starting engineering targets, not measured claims:

```text
particle simulation/compaction:
    <= 0.35 ms

particle classify/sort/indirect:
    <= 0.30 ms

particle/ribbon raster normal scene:
    <= 0.60 ms

decals:
    <= 0.30 ms

volume injection:
    <= 0.25 ms

volume lighting/integration:
    <= 0.75 ms

normal VFX total:
    target ~2.0 ms
    provisional ceiling ~2.5 ms
```

Overdraw may dominate particle cost in stress scenes.

## 6. Quality priority classes

At least:

```text
CriticalFeedback
CombatHigh
EnvironmentNormal
AmbientLow
Disposable
```

Examples:

```text
CriticalFeedback:
    primary hit/impact feedback
    essential weapon flash
    critical UI-linked world feedback

CombatHigh:
    explosion core
    blood spray
    plasma discharge

EnvironmentNormal:
    smoke
    ordinary debris
    persistent scorch

AmbientLow:
    drifting dust
    tiny sparks
    ambient motes
```

## 7. Particle quality scaling

When VFX budget is exceeded:

```text
1. reduce AmbientLow spawn multiplicity
2. reduce Disposable/AmbientLow visible cap
3. reduce ordinary particle emitter rates
4. shorten low-value particle lifetimes
5. reduce expensive alpha-render population
```

Protect CriticalFeedback before cosmetic density.

## 8. Volumetric scaling

Baseline:

```text
froxel:
    160x90x64

directional visibility lattice:
    40x23x32
```

Scaling order:

```text
1. reduce temporal update frequency for low-value volumes
2. reduce directional visibility lattice density
3. reduce froxel XY
4. reduce froxel Z only after visual evaluation
5. reduce low-priority volume emitter contribution
```

Do not replace world-space volume truth with purely screen-space smoke behavior.

## 9. Decal scaling

Under pool/budget pressure:

```text
expire/evict oldest low-priority decals
reduce RtVisible classification for minor decals
reduce decal raster population outside relevant presentation region
```

Do not change canonical surface state.

## 10. RT decal scaling

If RT-hit overlay cost is too high:

```text
1. reduce RtVisible designation of minor decals
2. lower candidate cap/cell
3. lower overlays applied/hit
```

Do not introduce raster/RT inconsistency for the highest-priority decals without explicit quality policy.

## 11. VFX-light scaling

At transient-light cap:

```text
rank by:
    importance
    expected screen/world contribution
    distance
    intensity/radius
    critical event class
```

Low-value lights may be omitted while their sprite/particle VFX remain.

No omitted VFX light changes canonical visibility/damage.

## 12. Jolt debris scaling

Starting cap:

```text
256
```

Pressure:

```text
sleep/retire old low-priority debris
downgrade new low-value pieces to GPU particles
```

Ragdolls retain separate priority/cap rules.

## 13. Benchmark scenes

Include:

```text
automatic weapon fire into wall
multiple simultaneous explosions
blood-heavy close combat
dense smoke room
plasma/laser-heavy alien firefight
many bullet/scorch decals
RMA multi-level cutaway
large outdoor dust/smoke
256 rigid-debris stress
```

## 14. VFX telemetry

Track:

```text
live/spawned/killed particles
particles dropped by priority
visible additive
visible alpha
alpha sort count/time

decal count
attached decal count
decal evictions
RtVisible decals
RT candidate overflows

volume emitter count
active froxels
volume-grid GPU time
volume RT visibility ray count

VFX light count
VFX light drops

Jolt debris active/sleeping
debris downgrades
```

## 15. Debug reproducibility

Record stable seeds/IDs for:

```text
spawn command
particle stable ID
decal stable ID
VFX light generation
beam/ribbon ID
```

Capture/replay should reproduce event-level VFX decisions.

Exact floating-point particle trajectories need not be canonical/bit-exact across future renderer revisions.

## 16. Failure policy

VFX resource exhaustion:

```text
degrade/drop presentation work according to priority
log telemetry in developer mode
continue game
```

Never:

```text
modify canonical damage
change canonical visibility
stall canonical state waiting for cosmetic capacity
```

## Global budget-accounting authority

Architecture 055 defines how VFX timing relates to core RT/reconstruction and UI targets.

Volumetric RT traversals count in the global ray ceiling while volumetric GPU time remains in the VFX budget, avoiding double-counting.
