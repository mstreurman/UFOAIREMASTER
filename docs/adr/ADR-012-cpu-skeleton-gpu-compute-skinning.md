# ADR-012 — CPU Skeleton Evaluation + B580 GPU Compute Skinning

**Status:** Accepted  
**Decision type:** Animation/rendering architecture  
**Primary targets:** Intel Core i9-9900K + Intel Arc B580

## Context

The current UFO:AI model stack already contains skeletal/bone data, per-frame bone matrices, bone influences and model attachment tags, while the legacy runtime animation path is largely based on frame ranges, `frame`/`oldframe` and interpolation.

The remaster needs:

- higher-quality blended animation;
- attachments and sockets;
- Jolt ragdoll integration;
- bone-linked VFX/audio;
- temporal rendering data;
- raster rendering;
- ray-traced acceleration structures for animated actors.

Vertex-shader-only skinning does not naturally expose the final deformed geometry needed for dynamic RT acceleration-structure builds.

## Decision

Skeleton and animation pose evaluation will run on the CPU.

Vertex skinning will run in a Vulkan compute pass on the Arc B580.

The split is:

```text
i9-9900K
    animation state
    clip sampling
    blending
    local joint pose
    hierarchy evaluation
    Jolt pose integration
    sockets/attachments
        |
        v
current + previous skin palettes
================================ CPU/GPU boundary
        |
        v
Arc B580 compute skinning
        |
        +--> raster geometry
        +--> previous-position/motion data
        +--> RT actor geometry / dynamic BLAS
```

## Skeleton asset layout

Skeleton assets are immutable and index-based.

They contain at minimum:

- joint count;
- parent indices;
- bind/local transforms;
- inverse-bind transforms;
- a topological evaluation order;
- joint/socket identifiers for tooling and attachment lookup.

Runtime hierarchy traversal is non-recursive and pointer-free.

Where practical, asset compilation orders parents before children.

## Pose representation

Local animation poses use translation + quaternion rotation + scale.

FP32 3x4 affine matrices are used for evaluated joint/world transforms and skin transforms.

The hot CPU pose path is designed to permit AVX2 processing in eight-float blocks.

An AoSoA block-of-8 layout is the preferred benchmark baseline for sampling/blending operations, but exact packing remains performance-testable.

## Current and previous data

The renderer retains current and previous presentation transforms and current/previous skin palettes for:

- motion vectors;
- temporal AA;
- RT denoising;
- reflection/GI reconstruction;
- temporal history rejection.

## Attachments

Weapons, headgear and other detachable objects remain separate presentation entities.

Attachments use numeric joint/socket indices at runtime.

String/tag lookup is an asset-import/tooling concern and is not repeated in hot per-frame code.

## Root motion

Animation root motion is non-authoritative.

Canonical movement events/pathing determine actor displacement.

Animation playback and pose are fitted to the canonical presentation timing; they never move the canonical actor.

## Jolt ragdolls

Jolt ragdolls initialize from the current animation pose.

Jolt may then drive presentation skeleton joints or blended joint weights.

Ragdoll state never changes canonical actor position, collision, cover, LOS or mission state.

## Legacy import

Legacy animation ranges, tag data and supported skeletal information are converted by the remaster asset pipeline into the new runtime representation.

The Vulkan renderer is not required to understand legacy `.anm` semantics directly.

## Remaining decisions / later authorities

Resolved by later accepted architecture:

```text
maximum influences per vertex = 8           architecture 063
dynamic deforming BLAS granularity          ADR-021 / architecture 026
    one dynamic BLAS per deforming render object per FrameContext
    full BUILD on rendered frames
```

Later accepted authorities now lock:

```text
clip reference-v1 storage       ADR-039 / architecture 085
maximum skeleton joints         ADR-038 = 256
joint IDs                       uint16_t
active/partial ragdoll          not a v1 baseline; ADR-037
```

Final AoSoA block format, authored ragdoll blend duration and skinning workgroup size are implementation/benchmark tuning and do not block the ABI.
