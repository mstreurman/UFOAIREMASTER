# Reference — M1 Production Contract Normalization

**Date:** 2026-09-08
**Baseline:** `2a36587bdfabe3f44d3b5abd19c166149a00e92b`
**Status:** local qualification required

## Purpose

Normalize the final ambiguous production mutation contracts instead of carrying legacy
UI callback context into the typed presentation boundary.

The legacy `prod_inc` callback contains two different semantic operations:

```text
selectedProduction != nullptr
    -> increase an existing queue job

selectedProduction == nullptr
    -> create a new queue job from selectedData
```

Those are not the same authoritative operation.

This slice therefore corrects the strict semantic inventory from 57 to 58 strategic
semantics by splitting out:

```text
IncreaseProduction   = existing ProductionId only
CreateProduction     = create a new job from a subject definition
```

`CreateProduction` is appended to the public enum as value 60 so every existing enum
value remains ABI-stable.

## Qualified operations

This slice qualifies:

```text
IncreaseProduction
SetProductionAmount
```

and leaves:

```text
CreateProduction
```

fail-closed.

## IncreaseProduction

Typed contract:

```cpp
submitIncreaseProduction(
    canonical::BaseId base,
    canonical::ProductionId production,
    int32_t amount);
```

The production owner:

```cpp
PR_TryIncreaseProduction(base, runtimeId, amount)
```

re-resolves the logical job at execution time and preserves existing canonical rules:

- amount must be positive;
- stale/missing `ProductionId` rejects;
- UFO disassembly cannot be increased;
- aircraft increase requires current hangar capacity;
- `MAX_PRODUCTION_AMOUNT` clamps the attempted increase;
- current production requirements determine how many additional units can be reserved;
- zero producible units reject;
- partial material availability applies only the producible amount;
- canonical `PR_IncreaseProduction` performs the actual amount/material mutation.

`PR_MUTATION_APPLIED_PARTIAL` distinguishes the existing legacy partial-material
behavior from a full canonical application.

The legacy selected-job branch calls this owner and retains only popup/cvar/UI refresh
feedback.

## SetProductionAmount

Typed contract remains:

```cpp
submitSetProductionAmount(
    canonical::BaseId base,
    canonical::ProductionId production,
    int32_t targetAmount);
```

Its meaning is now explicitly **absolute target amount**, not a legacy command-chain
delta.

Canonical owner:

```cpp
PR_TrySetProductionAmount(base, runtimeId, targetAmount)
```

performs:

```text
target < 0
    reject

target == current
    no-change reject

target == 0
    PR_TryStopProduction

target < current
    PR_TryDecreaseProduction(current - target)

target > current
    PR_TryIncreaseProduction(target - current)
```

The canonical result may end below a requested target when the existing max-production
limit or material availability prevents the full increase. The typed result reports the
actual canonical amount after mutation; presentation must reconcile to publication/result
state rather than optimistically assuming the requested target.

## CreateProduction semantic split

A new strict semantic is appended:

```cpp
CreateProduction = 60
```

Transport declaration:

```cpp
submitCreateProduction(
    canonical::BaseId base,
    int32_t subjectKind,
    canonical::ItemId item,
    canonical::StoredUfoId storedUfo,
    const char* aircraftDefinition,
    int32_t amount);
```

This is deliberately fail-closed in the legacy adapter.

Why it is not bridged in this slice:

- `ItemId` definition mapping is not yet qualified/published;
- `StoredUfoId` has a natural persisted `storedUFO_t::idx` candidate but still needs its
  focused save/load/publication qualification;
- aircraft definition keys are stable content keys but the presentation create-subject
  view is not yet published.

The legacy UI may continue to create jobs through its existing selectedData path until
that consumer migrates. No new presentation route is allowed to fabricate subject
identity.

## Authority accounting

After this contract correction and qualification:

```text
strategic authoritative semantics: 58
canonical-applied:                 24
fail-closed pending owners:        34

tactical semantics:                15
server-forwarded:                  13
fail-closed pending helpers:        2
```

The increase from 57 to 58 is not new gameplay. It is correction of a previously
conflated context-dependent callback semantic.

## Qualification

Focused:

```bash
python3 tools/remaster/test-m1-production-contract-normalization.py
python3 tools/remaster/test-m1-production-owner-extraction.py
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

Expected canonical digest:

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

After this lands, production existing-job mutation is complete.

The next identity-sensitive candidate should be selected from the remaining M1 families,
with preference for a small natural-ID slice before a sidecar-heavy one. Current likely
order:

1. qualify/publish `StoredUfoId` and stored-UFO/recovery owners;
2. qualify `EmployeeId -> character_t::ucn` and employee/team owners;
3. stable `FacilityId` before replacing the legacy facility-index destroy compatibility
   contract;
4. `TransferId` / transfer publication;
5. `DefenceSlotId` before defence mutation.
