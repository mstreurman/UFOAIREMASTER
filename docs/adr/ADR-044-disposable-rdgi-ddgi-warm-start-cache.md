# ADR-044 — Disposable RDGI DDGI Warm-Start Cache

**Status:** Accepted  
**Decision:** `DDGI-CACHE-001`  
**Related:** ADR-019, ADR-020, ADR-039, architecture 024, architecture 057, architecture 066, architecture 085, architecture 088

## Context

DDGI irradiance/distance history is mutable presentation state. The static `.rmap` asset may describe presentation-map/DDGI placement, but it must not become a mutable runtime-history store. Rebuilding all probe history every run is correct but unnecessarily discards useful convergence work.

## Decision

Add a disposable user-cache container with magic:

```text
RDGI
```

for DDGI warm-start state.

The cache is:

```text
non-canonical
non-authoritative
not source-controlled
not required for map load
not required for deterministic canonical gameplay
safe to delete at any time
strictly identity-validated before use
```

A mismatch, unsupported version, corruption, invalid payload or unavailable cache directory causes the cache to be ignored and DDGI to rebuild/converge normally.

The exact container/chunk ABI, identity key, cache location, atomic-write rule and validation order are owned by architecture 088. Reference DDGI records remain owned by architecture 085 and shader-visible DDGI ABI remains owned by architecture 057.

## Consequences

- `.rmap` remains immutable compiled content.
- `RDGI` may improve first-frame/early-frame GI stability after a previous compatible run.
- No result from an `RDGI` cache can become gameplay authority.
- Renderer/shader ABI changes invalidate the cache rather than requiring migration.
- Content/source identity changes invalidate the cache rather than attempting partial reuse.
