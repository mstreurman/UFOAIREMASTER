# ADR-029 — Shader, Identity and Temporal Contract Closure

**Status:** Accepted  
**Decision type:** Implementation-contract closure  
**Primary target:** Fedora 44 / i9-9900K / Intel Arc B580  
**Related:** ADR-015, ADR-017, ADR-020, ADR-021, ADR-022, ADR-027, ADR-028

## Context

The second Baseline-022 deep scan found no project-level architectural reversal, but it found implementation gaps that would force shader/runtime authors to invent incompatible policy:

```text
Slang matrix layout was not explicitly forced
shader root / descriptor binding was ambiguous
ReSTIR light generation was missing from GpuLight
static-map secondary-hit identity was undefined
deferred structural command ordering was not deterministic
GPU scene fields referenced undefined backing arrays
GPU skinning lacked an exact input/output binding record
ReSTIR packed bits and DDGI metadata were not exact
motion-vector jitter semantics were undefined
HDR diagnostic red used unit numeric RGB in an absolute-nit buffer
output constants were HDR-named despite mandatory SDR
UV/normal-map orientation was undefined
asynchronous audio could still refer to RenderObjectId
```

## Decision 1 — Slang remains deliberately pinned

The shader compiler is deliberately pinned. Baseline 039 / ADR-047 updates the current pin to:

```text
Slang v2026.17
```

ADR-047 is the current explicit toolchain-upgrade authority; future upgrades require the same manifest/ABI/benchmark discipline.

A newer upstream release does not silently alter the project compiler.

The compiler session must explicitly select:

```text
column-major matrix layout
```

because the pinned Slang API default is row-major.

## Decision 2 — exact shader root

All production shader stages use one exact 32-byte push root containing BDA addresses for:

```text
GpuSceneRoot
FrameConstants
ViewConstants
```

plus pass/draw indices.

`GpuSceneRoot`, `FrameConstants` and each used `ViewConstants` are owned by the active FrameContext and remain immutable until that FrameContext retires.

Frame/view constants remain BDA-rooted. ADR-045 supersedes the old Set-1 representation: the FrameContext TLAS and transient resources are now referenced through descriptor-heap handles, with the TLAS index stored in `GpuSceneRoot.frameTlasHeapIndex`.

## Decision 3 — light identity

`GpuLight` carries:

```text
lightId
lightGeneration
```

A Main-owned deterministic light registry owns slot allocation/reuse.

Reusing a light slot increments generation.

ReSTIR reservoir history validates both.

## Decision 4 — stable static hit identity

Static presentation geometry receives `RenderObjectId` values before dynamic presentation objects.

The map compiler emits deterministic static render-identity keys.

Runtime allocates static IDs in sorted key order.

Raster G4 and RT secondary-hit reconstruction use the same static identity.

RT geometry may override the containing TLAS instance's `RenderObjectId`.

## Decision 5 — deterministic structural commit

Deferred structural commands carry a Main-issued deterministic ordering stamp.

Main lexicographically sorts/merges commands by that stamp before mutation and before allocating:

```text
Presentation EntityId
RenderObjectId
LightId
other stable presentation identities
```

Worker completion order is never an ordering input.

## Decision 6 — exact semantic GPU backing

The core GPU root now includes explicit backing arrays for:

```text
GpuBounds
GpuSkinningJob
DDGI volume metadata
DDGI probe metadata
```

Orphan fields are removed or assigned exact targets.

## Decision 7 — temporal conventions

G3 motion vectors include the current/previous projection jitter:

```text
velocity = previousJitteredUV - currentJitteredUV
previousUV = currentUV + velocity
```

Temporal passes do not add jitter delta a second time.

## Decision 8 — runtime texture orientation

Runtime texture coordinates are normalized to:

```text
(0,0) = top-left
+U = right
+V = down
```

Tangent-space normal maps use:

```text
+X along T
+Y along B
+Z along N
```

Importers flip image orientation and/or normal-map green as necessary.

Runtime sampling performs no hidden source-format flip.

## Decision 9 — diagnostic red luminance

The RT Isolation invariant is a pure-red **hue**, scaled to output reference white.

```text
HDR non-RT = (203, 0, 0) nits
SDR non-RT = (100, 0, 0) nits
```

More generally:

```text
nonRt = (outputReferenceWhiteNits, 0, 0)
```

before PQ/sRGB transfer encoding.

## Decision 10 — audio identity

Asynchronous AudioCommandQueue commands use `AudioEmitterId` / `AudioVoiceId`, not `RenderObjectId`.

`RenderObjectId` may appear in continuous debug/state mapping, but it is not the lifetime key of an asynchronous audio command.

## Consequences

The documentation is now suitable to generate the first shader ABI/root declarations without relying on Slang defaults or inventing identity/temporal conventions.
