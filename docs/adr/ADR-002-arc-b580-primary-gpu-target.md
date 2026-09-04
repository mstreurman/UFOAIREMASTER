# ADR-002 — Intel Arc B580 / Xe2 as Primary GPU Target

**Status:** Accepted  
**Decision type:** Graphics target

## Context

The remaster is intentionally being designed for a known primary RT architecture rather than beginning from a generic cross-vendor lowest-common-denominator renderer.

The reference development system contains an Intel Arc B580 (Battlemage BMG-G21) using the Intel `xe` kernel driver and the Mesa Intel Vulkan/OpenGL stack.

The observed reference GPU exposes:

- Vulkan 1.4-class support;
- `VK_KHR_acceleration_structure`;
- `VK_KHR_ray_tracing_pipeline`;
- `VK_KHR_ray_query`;
- hardware RT feature enablement for acceleration structures, RT pipelines, and ray query;
- 12 GiB of dedicated video memory reported by the graphics stack.

## Decision

Intel Arc B580 / Battlemage / Xe2 is the primary GPU architecture target for the remaster renderer.

Renderer architecture, RT pipeline structure, acceleration-structure organization, shader organization, scheduling, and performance work should be optimized against this hardware first.

Cross-vendor support is secondary and must not force the primary B580 path into a lowest-common-denominator architecture.

## Performance/qualification target

The primary B580 qualification profile is:

- RenderExtent 1920×1080;
- 60 Hz output target where the selected display/mode supports it;
- sustained close to 60 FPS, using 16.667 ms as the frame-budget reference;
- VESA DisplayHDR 600-class presentation when HDR is enabled.

This profile drives optimization and benchmark acceptance. It does not hardcode resolution, refresh rate, HDR state, output display, or window mode for the player. Runtime display configuration is owned by ADR-046 and architecture 072/081/090.

The renderer should spend the available B580 budget on presentation quality, especially lighting, shadows, reflections, materials, atmosphere, and RT-enhanced effects. B580-specific fast paths are permitted and preferred when they materially improve the target profile; runtime configurability does not require lowering the optimized path to a generic hardware baseline.

## Measured Vulkan RT properties on the reference system

The Arc B580 device reported:

- shader group handle size: 32 bytes;
- shader group handle alignment: 16 bytes;
- shader group base alignment: 16 bytes;
- max hit attribute size: 32 bytes;
- max ray recursion depth: 31;
- max ray dispatch invocation count: 1,073,741,824;
- minimum acceleration-structure scratch offset alignment: 64 bytes;
- minimum subgroup size: 16;
- maximum subgroup size: 32;
- default reported subgroup size: 32.

These values are capability limits, not necessarily chosen operating parameters.

In particular, a supported recursion depth of 31 does not imply that deep recursion is desirable.

## Consequences

- B580-specific benchmarks become part of renderer design, not merely late optimization.
- SIMD16 vs SIMD32 must be measured for RT-adjacent compute work.
- Ray-tracing design must be evaluated on the actual B580 rather than inferred from older Arc generations.
- Portability work follows the primary architecture instead of defining it.
