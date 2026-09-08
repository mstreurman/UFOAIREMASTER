# Reference — M1 Stable Production Runtime Identity

**Date:** 2026-09-08
**Baseline:** `f15ac5f85ac6aeffe757b863f4fcc04c7422e375`
**Status:** local qualification required

## Purpose

Give each active canonical production queue entry a stable runtime identity so
presentation-originated production actions can target a logical production job rather
than a mutable queue ordinal.

This is an identity/publication/transport slice. It does **not** enable production
mutation authority.

## Problem being fixed

Legacy production queues are compact arrays:

```text
production_t::idx = current queue slot
```

`PR_QueueMove` copies whole `production_t` values and rewrites `idx`.

`PR_QueueDelete` calls `REMOVE_ELEM_ADJUST_IDX`, whose `REMOVE_ELEM` implementation
`memmove`s the tail of the array and then rewrites moved `idx` values.

Therefore:

```text
(BaseId, queueIndex)
```

is a snapshot-local location, not a logical production identity.

A stale pair of intents can otherwise do this:

```text
snapshot:
    slot 2 = job A
    slot 3 = job B

intent 1 deletes slot 2
canonical compaction:
    job B moves to slot 2

intent 2 still addresses old slot 2
```

The second intent must never mutate job B when it intended job A.

## Canonical runtime identity

`production_t` gains one runtime-only metadata field:

```cpp
uint32_t runtimeId;
```

The production subsystem owns a monotonic allocator.

Successful `PR_QueueNew` calls allocate an ID only for a queue entry that is actually
accepted.

`PR_LoadXML` reconstructs each valid loaded production and assigns a **fresh** runtime
ID.

The ID is deliberately **not serialized**. Save files remain canonical and unchanged.

Presentation wraps this value as:

```text
production_t::runtimeId -> canonical::ProductionId
```

The campaign layer does not include presentation ID headers.

## Lifetime

A `ProductionId` is valid for the lifetime of that logical in-memory production job.

It remains stable when:

- the job moves up or down;
- another job before it is removed and the queue compacts;
- insufficient credits roll the active job to the bottom;
- the job produces one unit but still has remaining amount.

It ceases to exist when:

- the queue entry is deleted/stopped;
- the production finishes its final amount;
- a disassembly entry is removed with its stored UFO;
- a queue is cleared;
- campaign state is replaced by a load/restart.

Loaded jobs receive fresh IDs.

## Why the field lives in `production_t`

This is runtime identity metadata, not new gameplay state.

Using a pointer-keyed sidecar would be incorrect because queue movement/compaction
changes the address of a logical job.

Using a parallel queue array would duplicate every move/delete bookkeeping operation.

A field in the copied queue record follows the existing canonical copy/memmove
operations automatically while `idx` continues to be rewritten as the current location.

No production rule reads `runtimeId`.

## Canonical resolver

The production subsystem exposes:

```cpp
uint32_t PR_GetProductionRuntimeId(const production_t* production);

production_t* PR_GetProductionByRuntimeId(
    base_t* base,
    uint32_t runtimeId);

const production_t* PR_GetProductionByRuntimeId(
    const base_t* base,
    uint32_t runtimeId);
```

The resolver scans the current canonical queue for the requested base and returns only
the entry whose stable runtime ID matches.

The following owner-extraction slice will use this resolver.

## Publication

`StrategicProductionView` now contains both:

```cpp
canonical::ProductionId id;
int32_t queueIndex;
```

Their meanings are intentionally different:

```text
ProductionId = logical job identity
queueIndex   = current display/order location
```

Presentation must use `ProductionId` for long-lived mutation targeting.

`queueIndex` may still be used for ordering/display.

## Typed intent transport

Production submit APIs are migrated away from queue-index identity while remaining
fail-closed:

```text
submitDecreaseProduction(BaseId, ProductionId, amount)
submitMoveProductionDown(BaseId, ProductionId)
submitMoveProductionUp(BaseId, ProductionId)
submitSetProductionAmount(BaseId, ProductionId, amount)
submitStopProduction(BaseId, ProductionId)
```

`submitIncreaseProduction` also receives a `ProductionId` for the existing-job case.
An invalid/default `ProductionId` remains available for the future create-new-production
case; subject normalization is explicitly deferred.

The transport writes `StrategicIntent::production`, not `valueN` queue-index fields.

## Save/load

`PR_SaveXML` does not write runtime identity.

`PR_LoadXML` allocates a new runtime identity after a production has been validated and
reconstructed.

This means presentation state cannot reconstruct canonical campaign state and stale
pre-load `ProductionId` values are not savegame identities.

## Authority accounting

Unchanged:

```text
strategic: 18 canonical-applied / 39 fail-closed
tactical:  13 server-forwarded / 2 fail-closed
```

All six production mutation semantics remain fail-closed:

```text
DecreaseProduction
IncreaseProduction
MoveProductionDown
MoveProductionUp
SetProductionAmount
StopProduction
```

## Qualification

Focused:

```bash
python3 tools/remaster/test-m1-production-runtime-identity.py
python3 tools/remaster/test-m1-research-production-publication-map.py
python3 tools/remaster/test-m1-strategic-publication.py
python3 tools/remaster/test-m1-canonical-identity-completeness.py
python3 tools/remaster/test-m1-authoritative-intent-surface.py
python3 tools/remaster/test-m1-research-owner-extraction.py
```

Cheap compile:

```bash
cmake --build build-m0-legacy-f44 --target ufo --parallel 8
```

Canonical preservation:

```bash
python3 tools/remaster/run-m0-canonical-regression.py --verify
```

Expected digest:

```text
33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2
```

Fresh builds before landing:

```bash
rm -rf build-m0-legacy-f44
cmake --preset legacy-m0-f44
cmake --build --preset legacy-m0-f44

python3 tools/remaster/provision-m0-slang.py

rm -rf build-m0-remaster-f44
cmake --preset remaster-m0-f44
cmake --build --preset remaster-m0-f44
```

There is no project-wide CMake install target.

## Next slice

After this identity slice lands, extract canonical production owners for the
unambiguous existing-job actions:

```text
DecreaseProduction
MoveProductionUp
MoveProductionDown
StopProduction
```

They must resolve `(BaseId, ProductionId)` to the current canonical queue entry at
execution time.

`IncreaseProduction` and `SetProductionAmount` remain separate because their current
legacy semantics still need contract normalization.
