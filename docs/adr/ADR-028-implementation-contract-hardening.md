# ADR-028 — Implementation Contract Hardening

**Status:** Accepted  
**Decision type:** Cross-cutting implementation contract hardening  
**Primary target:** Fedora 44 / i9-9900K / Intel Arc B580  
**Related:** ADR-008, ADR-011, ADR-015, ADR-017, ADR-021, ADR-023, ADR-024, ADR-026, ADR-027

## Context

The Baseline-021 deep scan found no project-level architectural retcon, but it identified several cross-document contracts that were still too implicit for implementation:

```text
per-FrameContext TLAS descriptor ownership
RenderObjectId allocation/lifetime/reuse
world-space/units/matrix/winding conventions
per-queue FrameContext completion values
single RenderSnapshot semantic authority
exact v1 core GPU scene ABI
legacy Lua -> .rui migration
budget hierarchy
RT diagnostic provenance/output-space semantics
post-audit map-entity presentation baking
```

These are implementation hardening decisions, not a redesign of canonical gameplay or the renderer.

## Decision 1 — TLAS is a frame resource

The production TLAS remains FrameContext-owned. ADR-045 supersedes the earlier Set-1 descriptor-buffer representation: the active TLAS is now published through the descriptor heap and referenced by `GpuSceneRoot.frameTlasHeapIndex`.

Two Frames in Flight retain independent TLAS storage and transient heap lifetime; one FrameContext never overwrites the other before retirement.

## Decision 2 — RenderObjectId

```text
uint32
0xffffffff = permanently invalid/background
0x00000000 .. 0xfffffffe = valid
```

Allocation is monotonic during a Presentation World lifetime. IDs are stable across frames, never frame-local, and never reused while that Presentation World exists.

The namespace resets only after the Presentation World is destroyed, all GPU FrameContexts retire, temporal histories are invalidated, and dependent decal/debug mappings are gone.

## Decision 3 — world coordinates and physical scale

Canonical legacy coordinates are unchanged.

Presentation World preserves legacy numerical axes:

```text
+X = legacy +X
+Y = legacy +Y
+Z = up
right-handed
```

Locked physical conversion:

```text
32 presentation units = 1 meter
1 presentation unit   = 0.03125 meter
UNIT_SIZE 32          = 1 meter
UNIT_HEIGHT 64        = 2 meters
```

Jolt and OpenAL-facing spatial data convert at subsystem boundaries. No Jolt/audio result becomes canonical state.

## Decision 4 — transforms, matrices and geometry

Generic project transform semantics:

```text
column vectors
p_world = worldFromObject * p_object
column-major generic CPU/Slang matrix storage
```

Explicit packed affine GPU records may use named rows and are not raw aliases of generic matrices.

`VkTransformMatrixKHR` is filled explicitly.

Runtime presentation geometry is normalized offline to:

```text
counter-clockwise outside-facing front faces
B = tangentSign * cross(N, T)
```

## Decision 5 — legacy UI Lua compatibility

Lua remains only as a legacy UI compatibility mechanism during migration.

Legacy `.rui` may contain symbolic `LegacyActionId` references in `LEGC`.

It may not serialize function pointers, Lua VM pointers or Lua registry handles.

Newly modernized screens must use `BIND`/`ACTN` and typed `UiIntent` and may not add new Lua UI callbacks.

This decision does not remove or redefine Lua outside the legacy UI compatibility path.

## Decision 6 — audited map-entity presentation baking

The canonical merged entity string remains authoritative.

Because the entity audit is source-complete, `.rmap` may bake the audited presentation-only/presentation-readable subset for rendering/audio/VFX convenience.

It never replaces canonical door, trigger, damage, mission, routing, collision, LOS or gameplay behavior.

## Decision 7 — RT diagnostic truth

RT Isolation colors are generated in the active display-linear output space after scene tone mapping/color transform and before PQ/sRGB transfer encoding.

For the selected isolation mode the non-RT color remains a pure-red hue.

ADR-029/architecture 060 define the final absolute-luminance form as:

```text
(outputReferenceWhiteNits, 0, 0)
```

Render Probe distinguishes actual displayed-result production provenance from an optional fresh `Diagnostic Re-trace`.

## Consequences

The accepted architecture now has explicit contracts for in-flight TLAS binding, temporal renderer identity, cross-system units/transforms, shader ABI, compatibility scripting, map presentation baking and RT diagnostic provenance.
