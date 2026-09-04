# ADR-001 — Canonical Gameplay Preservation

**Status:** Accepted  
**Decision type:** Project scope / architecture

## Context

The project is a remaster of UFO: Alien Invasion, not a gameplay redesign.

Presentation modernization can easily become entangled with gameplay when modern rendering, physical simulation, animation, audio propagation, or other systems begin producing results that are treated as authoritative.

## Decision

The existing UFO: Alien Invasion game/simulation behavior is the canonical gameplay authority.

Remaster presentation systems may consume canonical state and events, but must not modify gameplay-authoritative state through their own simulation results.

Gameplay-affecting changes require a separate explicit decision.

## Consequences

### Positive

- preserves the identity and behavior of UFO: Alien Invasion;
- allows presentation technology to be replaced aggressively without requiring a gameplay rewrite;
- makes renderer/physics/audio experimentation safer;
- enables clear regression testing against canonical behavior.

### Negative

- some presentation behavior may intentionally differ from the canonical spatial representation;
- visually simulated objects may not participate in gameplay;
- presentation systems cannot be used as shortcuts for LOS, collision, projectile hits, pathfinding, or similar rules;
- gameplay-affecting bug fixes require explicit handling rather than being folded silently into remaster work.

## Enforcement rule

If a presentation-system result can change a canonical gameplay result, the architecture boundary has been violated unless explicitly approved by a later scope decision.
