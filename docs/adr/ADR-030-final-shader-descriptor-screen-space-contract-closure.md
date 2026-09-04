# ADR-030 — Final Shader, Descriptor and Screen-Space Contract Closure

**Status:** Accepted  
**Decision type:** Final pre-roadmap implementation-contract closure  
**Primary target:** Fedora 44 / i9-9900K / Intel Arc B580  
**Related:** ADR-015, ADR-017, ADR-020, ADR-022, ADR-028, ADR-029, ADR-045

**Descriptor-binding update:** ADR-045 / architecture 089 supersede the historical descriptor-set/layout representation while preserving the fixed logical sampled-image/sampler capacities and retirement semantics below.

## Context

The third deep scan found four remaining implementation blockers:

```text
GpuShaderRoot.passDataIndex had no backing storage
persistent global sampled-image/sampler slot lifetime was undefined
GpuLight shape/orientation semantics were insufficient for exact ReSTIR sampling
clip/NDC/render-UV/jitter mapping was not exact
```

It also found several linked semantic gaps:

```text
indexType enum
first skinFormat
StaticRenderKey serialization
RenderObjectId batching boundaries
shader-binding/cache identity
stochastic RNG derivation
descriptor overflow
AudioVoiceId wrap
GPU presentation-time precision
directional local-light ownership
BDA alignment
```

## Decision 1 — shader root uses four addresses

The exact 32-byte shader root becomes:

```text
sceneRootAddress
frameConstantsAddress
viewConstantsAddress
passDataAddress
```

All pass-specific/draw-specific data is reached through the final address.

There is no unbacked `passDataIndex`.

## Decision 2 — persistent global bindless registry

Reference capacities are fixed for ABI v1:

```text
sampled images   65,536
samplers            256
```

Global sampled-image indices may be reused only after:

```text
asset/material references are removed
all FrameContexts that could reference the old descriptor retire
the descriptor slot retirement value is satisfied
```

Sampler indices are stable for process lifetime.

The sampler table is description-deduplicated and never reorders.

No persistent heap registry silently grows past its shader-visible ABI capacity at runtime.

## Decision 3 — shader-binding ABI hash

ADR-045 removes production Vulkan pipeline layouts. The surviving intent of this decision is represented by architecture 070's exact:

```text
ShaderBindingAbiHash256 v2
```

It includes the descriptor-heap binding model, fixed persistent capacities, 32-byte root version and heap-handle semantics and participates in `.rshader` and pipeline-binary cache identity.

## Decision 4 — exact local-light semantics

`GpuLight` supports local:

```text
Point
Spot
Rect
Disk
Line
```

The dominant sun remains the dedicated directional-light path and is not represented as a local `GpuLight`.

Every type has exact meanings for:

```text
positionRange
directionCosOuter
shape
colorIntensity
```

including enough orientation information for deterministic area-light sample reconstruction.

## Decision 5 — screen-space convention

Use a positive-height Vulkan viewport.

After perspective divide:

```text
ndc = clip.xy / clip.w

renderUV.x = ndc.x * 0.5 + 0.5
renderUV.y = ndc.y * 0.5 + 0.5
```

Thus render UV is top-left origin and +V down.

The projection builder contains the required camera-up/Y sign.

No negative-height viewport is used in the baseline.

Pixel centers:

```text
((x + 0.5) / width,
 (y + 0.5) / height)
```

Positive jitter X/Y means right/down in rendered UV.

## Decision 6 — shared index and skin baselines

```text
GpuIndexType:
    0 UInt16
    1 UInt32
```

Initial exact skin format:

```text
SkinFormat 0 = EightInfluenceU16F32
```

with eight `uint16` joint indices and eight `float32` weights per vertex.

Unused influences have zero weight.

Weights are normalized by the offline compiler.

Later compressed formats may be added without changing v1 binding/address semantics.

## Decision 7 — static key and batching

`StaticRenderKey` is an exact 32-byte BLAKE3-256 digest of a versioned little-endian source tuple.

Hash collision between distinct source tuples is a fatal asset-compiler error.

Raster draws and RT geometry may not cross a `RenderObjectId` identity-group boundary.

## Decision 8 — deterministic stochastic streams

Presentation GPU stochastic work uses counter-based:

```text
Philox4x32-10
```

with deterministic counters/keys derived from stable frame/effect/pixel/probe/entity/sample identities.

No mutable global RNG sequence depends on job/warp/wave execution order.

## Decision 9 — minor closure

- descriptor-array overflow is an explicit development/content capacity error;
- `AudioVoiceId` follows the same generation/wrap rules as `AudioEmitterId`;
- GPU presentation time uses architecture-071 split high/low floats while CPU presentation time remains double precision;
- BDA root/structured records have explicit alignment requirements.

## Consequence

After this ADR, remaining documentation work is primarily implementation sequencing, measured tuning and content-format optimization rather than missing shared shader/descriptor/screen-space policy.
