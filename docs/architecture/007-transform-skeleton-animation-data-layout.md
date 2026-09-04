# Transform, Skeleton and Animation Data Layout

**Status:** Architecture baseline  
**Related ADR:** `ADR-012-cpu-skeleton-gpu-compute-skinning.md`  
**Primary targets:** Intel Core i9-9900K + Intel Arc B580

## 1. Existing compatibility seam

The current model system already exposes concepts that can be imported:

- bones with parent relationships;
- bone/skin matrices;
- vertex bone influences;
- frame-based animation ranges;
- model tags used for attachments.

The remaster keeps compatibility at the asset-import boundary but does not retain the legacy frame/backlerp runtime as the new animation architecture.

## 2. Asset versus instance

Immutable:

```text
SkeletonAsset
AnimationClipAsset
AnimationGraphAsset
RagdollBindingAsset
MeshSkinBinding
SocketTable
```

Mutable per entity:

```text
AnimationComponent
PoseHandle
SkeletonInstance
PoseSource
```

## 3. Skeleton asset

Conceptual shape:

```cpp
struct SkeletonAsset {
    uint16_t jointCount;

    std::span<const uint16_t> parentIndex;
    std::span<const LocalTRS> bindLocal;
    std::span<const Mat3x4> inverseBind;

    std::span<const uint16_t> evaluationOrder;

    std::span<const JointNameHash> jointNames;
};
```

No parent pointers.

No recursive bone objects.

Asset compilation should order parents before children where possible.

## 4. Local pose

Animation blending uses TRS, not matrices.

Logical joint transform:

```cpp
struct JointTRS {
    Vec4 translation;
    Quat rotation;
    Vec4 scale;
};
```

## 5. Hot pose storage

The preferred benchmark baseline is AoSoA in blocks of 8 joints to match AVX2 eight-wide FP32 operations.

Concept:

```cpp
struct alignas(32) JointPoseBlock8 {
    float tx[8], ty[8], tz[8];

    float qx[8], qy[8], qz[8], qw[8];

    float sx[8], sy[8], sz[8];
};
```

Strong SIMD candidates:

- clip interpolation;
- pose blend;
- additive layers;
- masks;
- pose copy;
- selected matrix construction.

Hierarchy propagation remains dependency-driven and is not forced into SIMD.

## 6. Pose arena

Large pose data is stored contiguously.

Conceptual handle:

```cpp
struct PoseHandle {
    uint32_t offset;
    uint16_t jointCount;
};
```

Avoid actor -> skeleton -> bone pointer chains.

## 7. Evaluated matrices

Use FP32 affine 3x4 matrices:

```cpp
struct alignas(16) Mat3x4 {
    float row0[4];
    float row1[4];
    float row2[4];
};
```

Maintain two conceptual matrix sets:

```text
worldJoint[j]
skinMatrix[j]
```

with:

```text
worldJoint = parentWorld * localPose
skinMatrix = worldJoint * inverseBind
```

## 8. CPU animation responsibilities

The i9-9900K performs:

```text
animation state transitions
clip sampling
pose blending
additive layers
joint hierarchy evaluation
Jolt/ragdoll integration
socket resolution
bone-linked VFX/audio transform generation
```

## 9. GPU skinning responsibilities

The B580 compute pass consumes:

```text
bind vertices
bone indices/weights
current skin palette
previous skin palette
```

and produces deformed GPU vertex data suitable for both raster and ray tracing.

Conceptually:

```text
compute skinning
   |
   +--> current position -> raster + BLAS
   +--> normal/tangent   -> raster
   +--> previous position -> velocity/motion
```

Avoid CPU vertex skinning as the primary path.

## 10. Temporal state

Retain:

```text
entity current world transform
entity previous world transform

current skin palette
previous skin palette
```

This is required for temporal AA and RT reconstruction/denoising.

## 11. Palette bandwidth baseline

Use uncompressed FP32 3x4 palettes initially.

Compression is not justified until profiling demonstrates pressure.

The expected palette upload size is small relative to B580 memory bandwidth.

## 12. Attachments and sockets

Weapons/headgear remain separate rigid presentation entities.

Runtime attachment:

```cpp
struct SkeletonAttachment {
    presentation::EntityId parent;
    uint16_t jointIndex;
    LocalTRS offset;
};
```

Legacy tag names are resolved to integer sockets during asset import/compilation.

## 13. Muzzle presentation

Recommended hierarchy:

```text
actor skeleton
    |
hand socket
    |
weapon presentation entity
    |
weapon muzzle socket
    |
    +--> muzzle flash
    +--> temporary light
    +--> smoke
    +--> audio origin
```

Canonical hit/impact data remains server/event data and is never recomputed from visual muzzle rays.

## 14. Root motion

Actor displacement follows canonical movement/event timing.

Locomotion animation is fitted to that movement.

Animation root motion may influence visual pose internally but cannot move the canonical actor.

## 15. Animation graph baseline

A compact layered graph is sufficient.

Example layers:

```text
BASE
  idle
  walk
  crouch
  injured
  stunned
  death

UPPER BODY
  aim
  fire
  reload
  throw
  use

ADDITIVE
  recoil
  breathing
  hit reaction
  procedural aim
```

The exact state graph remains content/design work.

## 16. Bone masks

Upper-body and partial overlays use precompiled per-joint masks.

A compact `uint8_t` weight table is a suitable initial representation.

## 17. Ragdoll transition

Jolt initializes bodies from the current evaluated pose.

Conceptual flow:

```text
animation pose
    |
world joints
    |
initialize Jolt ragdoll
    |
Jolt simulation
    |
ragdoll joint transforms
    |
final skeleton pose
    |
skin palette
    |
GPU compute skinning
```

The precise animation-to-ragdoll blend time remains tunable.

## 18. Asset import

Legacy data is converted offline into runtime assets.

The runtime renderer should not parse legacy animation range files or search tag strings in hot paths.

## 19. Remaining animation decisions / benchmark gates

Resolved architecture decisions:

```text
maximum skeleton joints = 256                 ADR-038
joint ID storage = uint16_t                   ADR-038
maximum vertex influences = 8                 architecture 063
reference-v1 dense clip storage               ADR-039 / architecture 085
active/partial ragdoll baseline = NO          ADR-037
dynamic deforming BLAS = one per render object per FrameContext
                                                ADR-021 / architecture 026
```

Exact AoSoA packing, sampling implementation, skinning workgroup shape and CPU job chunk size are benchmark-tuned implementation values, not unresolved architecture. Authored ragdoll blend duration is presentation content tuning.

## Transform convention authority

Architecture 051 owns axes, handedness, units, matrices, quaternions and tangent handedness.

Animation/skeleton importers convert source assets offline into that convention.

GPU skin transforms use `GpuAffine3x4Rows` where serialized.

## GPU skinning binding authority

Architecture 059 owns the exact GPU-side `GpuSkinningJob` binding/output ABI.

The job binds:

```text
position/normal/tangent bind streams
joint-index/weight streams
current/previous bone palette
FrameContext-owned current/previous skinned output
```

Exact compressed JNT0/WGT0 authoring/runtime-expanded format selection remains a later animation/content packing decision and does not change these GPU addresses/strides.

## Baseline influence-count status

Architecture 063 fixes ABI-v1 maximum stored/processed influences = 8.

Only later optimized/compressed representations remain open.

## Compact production skin-format benchmark

Architecture 073 requires the B580 production path to compare the executable 48-byte/influence reference format against compact candidates such as:

```text
8 x U16 joints + 8 x UNORM16 weights
qualifying assets:
    4 x U16 joints + 4 x UNORM16 weights
```

Selection is per measured animation error, skinning/BLAS timing and bandwidth/VRAM benefit.

The reference format remains valid even if a compact production format wins.
