# ADR-037 — Post-Death Full-Body Ragdoll v1

**Status:** Accepted  
**Decision:** `JOLT-POLICY-001`

## Decision

v1 supports **full-body post-death ragdolls only**. Active ragdoll, partial ragdoll and physics-driven living-character locomotion are not baseline requirements.

Ragdoll state is presentation-only and cannot feed canonical actor position, hit detection, inventory, LOS, pathing, cover, mission logic or network authority.

Animation hands ownership to the ragdoll only after the authoritative death/event transition. Optional visual blending into the simulated pose is presentation state.

Architecture 082 owns body/layer/sleep/debug details.
