# ADR-042 — Preserve Legacy Footstep Spatialization for v1

**Status:** Accepted  
**Decision:** `AUDIO-FIDELITY-001`  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`  
**Related:** ADR-001, ADR-024, architecture 004, architecture 005, architecture 035

## Context

The legacy `EV_SOUND` path distinguishes ordinary sounds from queued movement/footstep sounds by the movement-step byte. For a queued step (`step >= 0 && step < MAX_ROUTE`), the client finds the closest friendly actor to the sound origin and temporarily substitutes that actor origin for `cl.cam.camorg` while the sound is started.

The legacy mixer immediately spatializes the new channel against `cl.cam.camorg`; normal later sound-frame updates spatialize active channels against the normal camera again. This is unusual presentation behavior, but it can alter initial distance attenuation and left/right placement and therefore can alter player-perceived information.

## Decision

Preserve the legacy queued-footstep/movement spatialization behavior for v1 compatibility.

The remaster **must not** implement this by mutating the global OpenAL listener. The stable tactical listener defined by ADR-024 remains authoritative for ordinary continuous audio. Instead, a queued movement-step one-shot carries an explicit compatibility spatialization reference:

```text
LegacyStepSpatializationReference
    sourceOriginPu
    closestFriendlyActorOriginPu
    movementStep
    eventIdentity / timing identity
```

For the source-start update, AudioControl evaluates the one-shot as if the listener position were `closestFriendlyActorOriginPu`, while retaining the normal tactical listener orientation. On the next normal continuous source update, if the voice is still alive, it resumes ordinary spatialization against the stable tactical listener. This reproduces the effective legacy start/update distinction without racing or moving the process-wide OpenAL listener.

If no closest friendly actor exists, preserve the legacy behavior: the step-specific branch produces no spatialized sample for that event.

## Non-authority

This rule is presentation compatibility only. It must never feed canonical AI hearing, visibility, pathing, turn timing or combat logic.

## Validation

The migration regression set must include queued step events at multiple distances/azimuths with:

```text
closest friendly actor present
closest friendly actor absent
source near/far from closest actor
source near/far from tactical camera focus
voice surviving into a later continuous audio update
```

Compare event start audibility/attenuation and stereo/3D direction against the legacy client. A later modernization requires a new explicit presentation decision.
