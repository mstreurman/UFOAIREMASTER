# ADR-043 — Use Transmitted Security-Camera Direction

**Status:** Accepted  
**Decision:** `CAMERA-FIDELITY-001`  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Related:** ADR-001, ADR-010, architecture 003, architecture 004, architecture 005

## Context

`EV_CAMERA_APPEAR` transports a direction value. The audited legacy callback decodes that value into `dir`, but then computes the camera-model yaw from `le->angle` without assigning `dir` to `le->angle` in that callback.

The transport therefore contains presentation information that the legacy renderer path appears not to consume correctly.

## Decision

Treat the legacy behavior as a presentation bug and use the transmitted `dir` for the remaster camera-model orientation.

The tactical event protocol remains unchanged. No server/gameplay rule changes. The presentation bridge maps the decoded direction through the same canonical direction-angle convention used elsewhere by the tactical client and publishes that yaw to the Presentation World.

If the legacy `le_t` mirror remains active during migration, its camera presentation angle may also be corrected at the bridge boundary so the old and new render paths do not intentionally disagree.

## Compatibility classification

```text
protocol compatibility:      preserved
canonical gameplay state:    unchanged
client mirror identity:      preserved
visual presentation:         intentionally corrected
```

This visual difference is expected and must be listed as an approved presentation-only legacy bug fix in regression results.

## Validation

Create a fixture covering every valid transmitted tactical direction and verify:

```text
decoded dir -> expected directionAngles mapping
legacy protocol bytes unchanged
Presentation World camera yaw matches transmitted direction
no effect on canonical visibility, interaction or tactical camera gameplay rules
```
