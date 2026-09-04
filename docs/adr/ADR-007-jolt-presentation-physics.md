# ADR-007 — Jolt Physics for Presentation Physics

**Status:** Accepted  
**Decision type:** Presentation physics runtime

## Context

The remaster requires modern physical presentation for:

- ragdolls;
- debris;
- shell casings;
- loose visual props;
- secondary rigid-body motion;
- destruction aftermath;
- other non-authoritative visual simulation.

ADR-005 already establishes that remaster physics is strictly presentation-only and cannot alter canonical gameplay state.

The primary CPU target is the Intel Core i9-9900K, and the project explicitly allows architecture-specific optimization and AVX2/FMA use where useful.

## Decision

Use **Jolt Physics** as the presentation physics engine.

Jolt will be integrated as a CPU-side presentation subsystem.

It will not become a gameplay-authoritative simulation layer.

## Primary uses

Jolt may be used for:

- ragdolls;
- death aftermath;
- debris;
- shell casings;
- physically simulated presentation props;
- limited secondary motion;
- presentation-only collision;
- non-gameplay visual reactions.

## Authority boundary

Jolt may consume canonical state and events.

Jolt may update presentation transforms.

Jolt may not determine or modify:

- damage;
- hit/miss outcomes;
- projectile impact used by gameplay;
- grenade landing position used by gameplay;
- pathfinding;
- cover;
- line of sight;
- tactical visibility;
- unit movement;
- canonical collision;
- AI decisions;
- canonical destruction state;
- mission state;
- campaign state.

The data flow is one-way:

```text
Canonical game state/events
        |
        v
Presentation World
        |
        v
Jolt Physics
        |
        v
Presentation transforms / ragdolls / debris

NO FEEDBACK INTO CANONICAL GAMEPLAY
```

## CPU target policy

Jolt should be built and benchmarked for the Intel Core i9-9900K reference system.

The project may use CPU-specific optimization flags such as:

```text
-march=native
-mtune=native
```

on the reference build.

AVX2/FMA-capable Jolt code paths are acceptable.

## Threading

Jolt should participate in the remaster's CPU job/scheduling architecture rather than creating uncontrolled parallelism.

The exact worker count and scheduling policy remain subject to i9-9900K profiling.

The target CPU provides 8 physical cores and 16 hardware threads.

## Integration rule

Jolt must not write directly into Vulkan renderer objects.

Preferred flow:

```text
Jolt body/ragdoll state
        |
        v
Presentation World
        |
        v
renderer-facing transform/skeleton data
        |
        v
Vulkan renderer
```

This preserves a clean subsystem boundary.

## Ragdoll transition

A canonical actor death may trigger:

```text
canonical death event
        |
        v
death animation / transition
        |
        v
Jolt ragdoll activation
        |
        v
visual corpse presentation
```

The ragdoll pose and resting position remain presentation-only.

## Observed implementation state — 2026-09-04

Jolt remains the accepted presentation-physics decision in this ADR.

The developer-supplied local workstation/source snapshot did not reveal a Jolt source checkout, vendored Jolt directory, git submodule, installed Jolt package, or obvious Jolt build artifact.

Therefore the current implementation state is:

```text
Jolt selected/documented: YES
Jolt source/download confirmed present: NO
Jolt integrated into current build confirmed: NO
```

This observation does not reopen the engine choice. It prevents implementation planning from incorrectly assuming that Jolt has already been fetched or wired into `build-f44/`.

See `reference/reference-local-development-state-2026-09-04.md`.

## Current status and remaining work

Resolved by later documents:

```text
animation/ragdoll data flow          architecture 007
fixed 60 Hz Jolt timestep            ADR-023 / architecture 033
Main + six Primary Jolt concurrency  ADR-023 / architecture 033
rigid-debris starting cap            ADR-025 / architecture 041
replay/instrumentation boundary      ADR-027 / architecture 047–050
```

Resolved by Baseline 031:

```text
exact Jolt pin/vendor/build method       ADR-034 / architecture 082
collision layers/body categories        architecture 082
ragdoll scope                            ADR-037 / architecture 082
sleep/qualification policy              architecture 082
physics debug rendering                  architecture 082
```

Exact blend durations, debris lifetimes and visual destruction tuning remain authored presentation values rather than architecture blockers.
