# Reference — M1 Production Existing-Job Owner Extraction

**Date:** 2026-09-08
**Baseline:** `4a9c991a2ee49e95c0861b5297063791042d2aa0`
**Status:** local qualification required

## Purpose

Qualify the first production mutation owners now that logical production jobs have a
stable runtime `ProductionId`.

This slice applies exactly:

```text
DecreaseProduction
MoveProductionUp
MoveProductionDown
StopProduction
```

The remaining production mutations stay fail-closed:

```text
IncreaseProduction
SetProductionAmount
```

## Core invariant

Presentation never mutates a production by queue position.

Each owner receives `(BaseId, ProductionId)` and resolves the current canonical queue
entry at execution time through `PR_GetProductionByRuntimeId(base, runtimeId)`.

`queueIndex` remains publication/display order metadata only.

## Stale-intent rule

Given one immutable snapshot:

```text
slot 0 = A / ProductionId 100
slot 1 = B / ProductionId 101
```

and two queued intents:

```text
StopProduction(A)
MoveProductionDown(A)
```

the first removes A and canonical compaction moves B to slot 0. The second must resolve
ProductionId 100 again, find no active production, and reject. It must never mutate B
because B now occupies A's old slot.

The same rule applies after DecreaseProduction removes the final amount.

## Canonical owner API

`cp_produce.h/.cpp` gains:

```cpp
productionMutationResult_t PR_TryDecreaseProduction(base_t* base, uint32_t runtimeId, int amount);
productionMutationResult_t PR_TryMoveProductionUp(base_t* base, uint32_t runtimeId);
productionMutationResult_t PR_TryMoveProductionDown(base_t* base, uint32_t runtimeId);
productionMutationResult_t PR_TryStopProduction(base_t* base, uint32_t runtimeId);
```

## Canonical behavior preservation

Decrease preserves the legacy callback's `decrease >= amount -> stop/delete` semantic
before delegating partial changes to `PR_DecreaseProduction`. This also preserves
cancelling a one-unit UFO disassembly through decrease.

Stop delegates to `PR_QueueDelete`, preserving required-material refund, disassembly
pointer reset, queue compaction, moved-entry index repair and disassembly pointer repair.

Move validates the current boundary then delegates to `PR_QueueMove`. Existing queue
copy semantics retain `runtimeId` with the logical job while `idx` remains the current
location.

## Legacy callback migration

The corresponding callbacks call the same `PR_Try...` helpers and retain only legacy
selection/UI refresh behavior. They no longer call `PR_QueueDelete`,
`PR_DecreaseProduction` or `PR_QueueMove` directly.

## Typed adapter

The strategic adapter passes the stable runtime ID directly to the campaign owner.
After a successful decrease or move it re-resolves only to report current canonical
amount/index. Missing/stale IDs reject.

No command, cvar or UI fallback is introduced.

## Stale two-intent qualification

This slice adds:

```text
tools/remaster/m1-production-owner-stale-contract.cpp
tools/remaster/test-m1-production-owner-extraction.py
```

The C++11 contract executes delete/compaction/stale retry and verifies the neighbor is
never targeted by the stale ID. The Python lane audits the real owner source to ensure
each mutation resolves by runtime ID immediately before canonical mutation.

## Authority accounting after qualification

```text
strategic authoritative semantics: 57
canonical-applied:                 22
fail-closed pending owners:        35

tactical semantics:                15
server-forwarded:                  13
fail-closed pending helpers:        2
```

## Explicit non-goals

This slice does not change production costs, timing, requirements, completion behavior,
savegame format, or ProductionId persistence. It does not bridge `IncreaseProduction`
or `SetProductionAmount`.

## Qualification

```bash
python3 tools/remaster/test-m1-production-owner-extraction.py
python3 tools/remaster/test-m1-production-runtime-identity.py
python3 tools/remaster/test-m1-research-production-publication-map.py
python3 tools/remaster/test-m1-strategic-publication.py
python3 tools/remaster/test-m1-canonical-identity-completeness.py
python3 tools/remaster/test-m1-authoritative-intent-surface.py
python3 tools/remaster/test-m1-research-owner-extraction.py

cmake --build build-m0-legacy-f44 --target ufo --parallel 8
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

## Next work

After this lands, normalize `IncreaseProduction` into explicit existing-job increase vs
new-job creation, and define `SetProductionAmount` as an explicit absolute-target
contract instead of relying on the legacy command-chain diff behavior.
