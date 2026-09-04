# ADR-038 — Maximum 256-Joint Skeleton v1

**Status:** Accepted  
**Decision:** `ANIM-001`

## Decision

The v1 runtime/asset hard limit is:

```text
maximum joints per skeleton = 256
joint identifier/index storage = uint16_t
maximum influences per vertex = 8 (already fixed by architecture 063)
```

The asset compiler rejects skeletons above 256 joints. Runtime code does not silently truncate or split a skeleton to bypass the limit.

The limit is an ABI/validation ceiling, not a requirement to allocate a 256-joint palette for every asset.
