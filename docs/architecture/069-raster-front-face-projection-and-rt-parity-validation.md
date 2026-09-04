# Raster Front-Face, Projection and RT Parity Validation

**Status:** Exact implementation specification  
**Related ADR:** ADR-028, ADR-030, ADR-031  
**Related architecture:** 051, 063

## 1. Semantic winding

Runtime presentation geometry remains right-handed and CCW outside-facing when viewed from outside.

Offline importers normalize to this winding. RT uses the same triangle order.

## 2. Vulkan screen convention

Keep architecture 063:

```text
positive-height viewport
renderUV (0,0) top-left
+U right
+V down
projection builder owns Vulkan Y correction
```

No negative-height viewport.

## 3. Raster state

```text
cullMode  = VK_CULL_MODE_BACK_BIT
frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE
```

## 4. Projection invariant

The accepted projection builder must map the semantic outside-facing reference triangle into framebuffer coordinates with Vulkan-equivalent signed area:

```text
area > 0
```

for intended front surfaces.

Projection sign and front-face state are a paired contract.

## 5. Required reference asset

`WindingReferenceCube`:

```text
unit cube
RH coordinates
outside faces CCW
distinct face semantic IDs
known outward normals
```

Test cameras view front, right, top and an oblique corner.

## 6. CPU reference test

Transform vertices using accepted world/view/projection, divide by W, map through accepted viewport, compute Vulkan-equivalent signed framebuffer area and assert `area > 0` for expected visible outside-facing triangles.

## 7. Vulkan raster test

Render with back-face culling and `VK_FRONT_FACE_COUNTER_CLOCKWISE`, capture face/object ID, normal and depth, and assert only expected outside faces contribute.

## 8. RT parity test

Build the same mesh into BLAS/TLAS without changing winding.

Selected raster face semantic ID, RT geometry/primitive semantic ID and outside normal orientation must agree.

## 9. Double-sided/alpha-test

Double-sided may disable culling but never redefines semantic winding.

Alpha-test uses the same front/back semantics.

## 10. Import validation

Reversed source winding is converted offline.

Do not use per-asset frontFace changes, negative object scale as implicit winding fix, or RT-only winding fixes.

Negative-determinant transforms require explicit handling preserving raster/RT semantic face parity.

## 11. Regression

Reference cube/cameras run in CPU math tests, Vulkan regression and RT Render Probe parity checks.
