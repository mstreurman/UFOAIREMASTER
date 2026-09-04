# GPU Particle Runtime, Simulation, Compaction and Rendering

**Status:** Implementation specification baseline  
**Related ADR:** ADR-025

## 1. CPU/GPU ownership

CPU creates only spawn commands and high-level emitter state.

After spawn, ordinary particle state remains GPU-resident.

Flow:

```text
PresentationEvent
    ->
VfxSpawnCommand[]
    ->
mapped frame upload
    ->
ParticleSpawn
    ->
ParticleSimulateCompact
    ->
ParticleClassify
    ->
ParticleSort
    ->
ParticleIndirectBuild
    ->
ParticleRender
```

## 2. Baseline capacities

```text
live particles:
    262,144

new spawns/frame:
    32,768

sorted alpha-visible:
    65,536

additive-visible:
    131,072
```

Overflow uses deterministic priority/degradation rules.

## 3. Particle state ABI

Reference-v1 is the explicit 80-byte semantic state defined by architecture 085 (`ParticleStateRefV1`). It contains uncompressed size, rotation, angular velocity and color fields plus material/flags/stable-ID/priority values.

The former ambiguous 48-byte manually packed target is **not** the v1 ABI. It may return only as a separately identified benchmarked compact format with an explicit converter and format ID. Slang reflection verifies the selected runtime layout.

## 4. Particle material ABI

Per-material data should hold common behavior rather than duplicating it per particle.

Conceptual:

```text
texture index
sampler index
blend mode
softness/fade mode
gravity factor
drag
size-over-life parameters
color-over-life parameters
emissive scale
orientation mode
flags
```

## 5. Ping-pong state

Use two persistent device-local buffers:

```text
ParticleStateA
ParticleStateB
```

Current frame reads one and compacts survivors into the other.

Swap roles after completion.

## 6. Spawn integration

Spawn commands are appended into the next-state output during simulation/compaction.

Spawn command contains:

```text
emitter/event ID
stable spawn seed
position/orientation
base velocity
material
count
lifetime range
size/color parameters
```

Randomness derives from stable event/frame/sample data.

Never derive visible randomness from GPU invocation order.

## 7. Simulation

Ordinary simulation includes:

```text
position integration
velocity integration
gravity
drag
age/lifetime
size/color curve evaluation inputs
optional simple analytic constraints
```

No canonical collision.

## 8. No screen-depth collision

Baseline explicitly excludes depth-buffer collision.

Reason:

```text
camera-dependent result
off-screen geometry missing
view changes alter particle behavior
```

This would violate the world-space presentation policy.

## 9. Subgroup compaction

Starting B580 algorithm:

```text
one invocation/live particle
    ->
alive predicate
    ->
subgroup ballot
    ->
subgroup alive count
    ->
one atomic reservation/subgroup
    ->
lane-local compacted offset
```

Benchmark required subgroup sizes:

```text
16
32
```

Do not hard-code a subgroup width without the B580 measurement.

## 10. Particle classes

At minimum:

```text
Additive
PremultipliedAlpha
OpaqueCutout
```

### Additive

Examples:

```text
sparks
energy glows
fire highlights
muzzle-flash particles
```

No depth sorting required.

### Premultiplied alpha

Examples:

```text
smoke sprites
dust
blood mist
debris clouds
```

Depth sorted when included in the capped sorted-visible set.

## 11. Visibility/classification

For every live particle:

```text
cutaway/tactical-level test
lifetime test
frustum test
projected-size test
material class
```

Build compact visible lists.

Particles outside current presentation visibility continue ageing/simulating unless explicitly killed by their lifetime/emitter policy.

## 12. Alpha sorting

Use GPU back-to-front sort.

Starting key:

```text
32-bit quantized view-space depth
```

Use radix sort.

Stable ID may be incorporated into the key/tie break where deterministic ordering is useful.

Do not sort additive particles.

## 13. Geometry expansion

Baseline particle geometry:

```text
static unit quad
4 vertices
6 indices
instanced rendering
```

Vertex shader constructs world-space/camera-facing billboard geometry.

Mesh shaders are benchmark-only, not foundational.

## 14. Orientation modes

Support at least:

```text
CameraFacing
CameraFacingYLocked
VelocityAligned
WorldOriented
```

Orientation is presentation-only.

## 15. Indirect rendering

GPU generates indirect draw counts/arguments after classification/sort.

CPU does not read back visible particle counts.

## 16. Soft-particle policy

Do not use depth to change particle physics.

Depth may be used only at raster time to soften an intersection with the current primary surface.

This is reconstruction/compositing, not particle world truth.

## 17. HDR/color

Particle colors and emission are converted/evaluated in:

```text
linear ACEScg
```

before compositing into SceneColor.

Texture color spaces follow asset metadata.

## 18. Cutaway

Each particle/emitter carries presentation tactical-level/cutaway classification when relevant.

Hidden particles:

```text
do not render
continue lifetime/simulation
```

They do not freeze and reappear at an old age/state later.

## 19. Debug views

Required:

```text
live count
spawn count
visible additive count
visible alpha count
dropped count
particle material
particle priority
particle age/lifetime
particle tactical level
compaction occupancy
sort cost
```

## Baseline 031 particle-ABI closure

Architecture 085 defines `ParticleStateRefV1` (80 bytes serialized) and `ParticleMaterialRefV1`. Compact bit-packed runtime variants are optional future benchmark candidates and cannot silently reuse the v1 format identity.
