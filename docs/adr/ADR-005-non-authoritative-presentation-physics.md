# ADR-005 — Non-Authoritative Presentation Physics

**Status:** Accepted  
**Decision type:** Simulation/presentation boundary

## Context

The remaster should support better physical presentation, including ragdolls, debris, shell casings, secondary motion, and other modern visual effects.

At the same time, canonical UFO: Alien Invasion gameplay must remain unchanged.

## Decision

Physics introduced by the remaster is presentation-only and non-authoritative.

Presentation physics may read canonical state and canonical events.

Presentation physics may not write gameplay-authoritative results back into canonical state.

## Allowed uses

Examples include:

- ragdolls after canonical death;
- debris after canonical destruction;
- shell-casing simulation;
- loose non-gameplay visual props;
- secondary animation;
- cloth-like presentation effects;
- particle collision used only for visual presentation;
- physically plausible settling and aftermath.

## Forbidden authority

Presentation physics must not determine:

- damage;
- hit/miss outcomes;
- projectile trajectory used by gameplay;
- grenade destination used by gameplay;
- movement;
- pathfinding;
- cover;
- line of sight;
- canonical collision;
- AI decisions;
- canonical destruction state;
- mission or campaign outcomes.

## Example

A grenade may produce presentation debris whose trajectories are simulated physically.

The canonical game remains solely responsible for:

- where the grenade is considered to have detonated;
- which units are affected;
- damage;
- canonical destruction;
- smoke/fire/gameplay effects.

The visual debris cannot feed back into those results.

## Current status

ADR-007 selects **Jolt Physics** as the presentation-only physics middleware.

The selection criteria in this ADR remain binding constraints on that integration:

- strong CPU performance on the reference system;
- clean integration with presentation transforms;
- ragdoll support;
- rigid-body support;
- all results remain non-authoritative;
- straightforward debugging/replay where useful;
- no restructuring of canonical gameplay around the physics library.

Exact Jolt integration details are owned by ADR-023 and architecture 033.
