# Baseline 031 Deep-Audit Decision Gates

**Status:** Resolved / accepted  
**Decision baseline:** 034  
**Source baseline:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`

## 1. Purpose

Baseline 031 closed every decision identified by the Baseline 029/030 audits. A deeper Baseline 032 source/ABI consistency pass exposed three additional choices that could not be resolved honestly by mechanical normalization alone. All three were accepted by the project owner for Baseline 034.

These do **not** reopen the nine Baseline 031 decisions. They are newly discovered presentation-fidelity/persistence decisions.

## 2. `AUDIO-FIDELITY-001` — footstep listener semantics

Audited source behavior in `src/client/battlescape/events/event/world/e_event_sound.cpp` temporarily replaces `cl.cam.camorg` with the closest friendly actor origin before playing movement/footstep sounds (`step >= 0 && step < MAX_ROUTE`).

Choices:

```text
A. Preserve that closest-friendly-actor listener behavior for v1 compatibility.
B. Use the normal camera/OpenAL listener for footsteps as an intentional presentation change.
```

**Accepted: A — preserve the legacy behavior for v1.**

Reason: this can affect perceived audibility/attenuation and therefore player-facing information, even though it is not canonical game state. Preserve it during the migration; a later presentation ADR can deliberately modernize it with A/B regression evidence.

## 3. `CAMERA-FIDELITY-001` — `EV_CAMERA_APPEAR` direction

Audited source behavior in `src/client/battlescape/events/event/world/e_event_cameraappear.cpp` decodes transmitted `dir` but does not assign it before setting yaw from `le->angle`.

Choices:

```text
A. Reproduce the legacy visual discrepancy exactly.
B. Use the transmitted `dir` for the remaster camera-model yaw and document it as an intentional presentation bug fix.
```

**Accepted: B — use the transmitted direction.**

Reason: the protocol explicitly transports the direction; consuming it changes presentation only, not canonical rules/state, and avoids deliberately reproducing an apparent legacy rendering bug. A compatibility test should record the expected visual difference.

## 4. `DDGI-CACHE-001` — persisted DDGI state envelope

ADR-039/architecture 085 define reference-v1 semantic records for persisted DDGI state, but Baseline 031 did not actually define the enclosing on-disk cache identity/location/chunk topology. Architecture 031's `RMAP/DDGI` content is static placement metadata, not dynamic irradiance/distance history.

Choices:

```text
A. No disk-persisted dynamic DDGI state in production v1; rebuild/converge each run.
B. Add a disposable user-cache container for dynamic DDGI warm-start state.
```

**Accepted: B — a disposable user-cache container using the existing common container rules.**

Accepted shape:

```text
file role: generated cache, never canonical/content source
magic: RDGI
common header/chunk descriptor: architecture 066
chunks: META, VOLM, PROB, IRAD, DIST
identity key includes:
    canonical BSP/source identity
    .rmap ContentHash256
    DDGI volume descriptor bytes
    renderer/shader ABI identity
    encoding/color version
cache mismatch/corruption -> discard and rebuild, never fail canonical load
```

This gives warm starts without making DDGI cache files authoritative or source-controlled.

## 5. Deliberately not promoted to user decision gates

The deep audit also found intentionally tunable items such as auto-exposure metering implementation, adaptation rates, bloom kernel/constants, meshlet value, compression choices, Jolt presentation-collision simplification details, allocator thresholds and denoiser weights.

Those remain implementation/content/benchmark choices inside already accepted architecture and do not need a project-scope decision before implementation starts. If the project wants every quality default frozen before coding, they can be promoted later, but this audit does not misclassify them as architecture blockers.


## 6. Baseline 034 closure

```text
AUDIO-FIDELITY-001   ACCEPTED A
CAMERA-FIDELITY-001  ACCEPTED B
DDGI-CACHE-001       ACCEPTED B
```

Normative authorities after closure:

```text
AUDIO-FIDELITY-001   ADR-042, architecture 004/005/035
CAMERA-FIDELITY-001  ADR-043, architecture 004/005
DDGI-CACHE-001       ADR-044, architecture 085/088
```

This document remains as the decision-history record and is no longer an open-gate register.
