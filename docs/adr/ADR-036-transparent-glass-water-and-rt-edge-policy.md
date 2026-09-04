# ADR-036 — Transparent, Glass, Water and RT Edge Policy

**Status:** Accepted  
**Decision:** `RENDER-EDGE-001`

## Decision

Production-v1 material handling is:

```text
ordinary translucency -> weighted-blended OIT raster pass
glass               -> specialized forward transparent path with scene-color/depth refraction and eligible RT reflections
water               -> specialized forward path with authored normal/roughness reflection/refraction and scene depth/color interaction
alpha test          -> one shared cutoff/texture semantic used by raster and RT
RT transmission     -> no recursive transmissive RT in v1
ray origin          -> one shared robust world-space position-offset helper for all RT ray classes
```

These are presentation paths only and may not alter canonical collision, LOS, cover, projectile or movement results.

Architecture 084 owns exact pass and helper contracts.
