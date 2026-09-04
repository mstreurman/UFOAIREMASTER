# ADR-039 — Reference-First Binary ABI Policy

**Status:** Accepted  
**Decision:** `ABI-REF-001`

## Decision

The first production representation for still-open persisted/runtime records is a straightforward deterministic **reference-v1** layout. It favors inspectability and exact semantics over bit-level compression.

Applies to:

```text
.ranim track storage
DDGI persisted metadata/state
particle state/material records
trace/replay/probe records
acoustic ACOU/APRT/BVH records
```

A compact/quantized representation may be introduced later only as a new version/format after benchmark and error evidence. It may not silently reinterpret v1 bytes.

Architecture 085 owns exact serialization rules and v1 records. For DDGI specifically, ADR-044/architecture 088 own the accepted disposable `RDGI` enclosing user-cache container; this does not change the reference-first payload policy.
