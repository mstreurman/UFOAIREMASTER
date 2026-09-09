# Reference — M1 Stored UFO Identity and Publication

**Date:** 2026-09-09  
**Baseline:** `bb2cdd1dff5459033dadbe7f8f811067aa81bcde`  
**Status:** local qualification required

## Purpose

Qualify `StoredUfoId` as a direct canonical campaign identity and publish stored UFOs as
immutable value-only strategic state.

This is an identity/publication slice only.

`CreateProduction` remains fail-closed.

## Legacy identity proof

The canonical record already contains:

```cpp
typedef struct storedUFO_s {
    int idx;
    ...
} storedUFO_t;
```

Stored UFOs live in a linked list:

```cpp
#define US_Foreach(var) LIST_Foreach(ccs.storedUFOs, storedUFO_t, var)
```

New identities are allocated by the campaign-owned monotonic statistic:

```cpp
ufo.idx = ccs.campaignStats.ufosStored++;
```

Lookup is already identity-based rather than list-position-based:

```cpp
US_GetStoredUFOByIDX(idx)
    -> scan stored UFO list
    -> compare ufo->idx == idx
```

Removal calls `LIST_Remove` and never renumbers any surviving stored UFO.

Therefore `storedUFO_t::idx` is not a mutable list ordinal.

## Save/load persistence

The canonical UFO-store save format already persists each object identity:

```cpp
XML_AddInt(... SAVE_UFORECOVERY_UFOIDX, ufo->idx)
```

and restores it directly:

```cpp
ufo.idx = XML_GetInt(... SAVE_UFORECOVERY_UFOIDX, -1)
```

The campaign statistics subsystem separately persists the monotonic allocator state:

```text
SAVE_STATS_UFOSSTORED <-> ccs.campaignStats.ufosStored
```

This means the intended legacy model is already persistent object identity plus a
persistent next-ID counter.

## Load hardening

The save subsystem currently loads `ufostores` before `stats`.

That is safe for normal canonical saves because both values are persisted consistently,
but it leaves a malformed/stale-counter edge case:

```text
loaded stored UFO IDs: 3, 7, 12
saved ufosStored counter: 4
```

Without reconciliation, the next recovery could eventually reuse an existing ID.

This slice hardens that boundary.

### Duplicate rejection

`US_LoadXML` rejects a second stored-UFO record with an already-loaded `idx`.

### Counter reconciliation

After `STATS_LoadXML` restores `ccs.campaignStats.ufosStored`, it scans the already-loaded
stored UFO list and advances the counter past every loaded identity.

The `INT_MAX` boundary is handled without signed overflow; an exhausted counter causes
future `US_StoreUFO` to reject rather than wrap/reuse identity.

These changes affect identity metadata and malformed-save robustness only. They do not
change UFO recovery timing, capacity, transfer, disassembly, research collection, or
campaign balance.

## Public projection

The immutable strategic snapshot gains:

```cpp
struct StrategicStoredUfoView {
    canonical::StoredUfoId id;
    canonical::InstallationId installation;
    int32_t status;
    float condition;
    bool disassembling;
    std::string ufoDefinition;
};
```

Semantics:

```text
id              persistent canonical StoredUfoId
installation    current UFO-yard InstallationId
status          canonical storedUFOStatus_t value
condition       canonical recovered condition
disassembling   whether canonical production currently owns this UFO
ufoDefinition   canonical stored UFO/template script key
```

No raw `storedUFO_t*`, `installation_t*`, `aircraft_t*` or `production_t*` crosses the
public snapshot boundary.

## CreateProduction

`CreateProduction` remains fail-closed.

This slice proves the stored-UFO subject identity needed by the disassembly branch, but
new item production still needs qualified `ItemId` definition mapping/publication and
aircraft creation still needs an explicit published definition-subject contract.

No partial CreateProduction bridge is introduced.

## Authority accounting

Unchanged:

```text
strategic authoritative semantics: 58
canonical-applied:                 24
fail-closed pending owners:        34

tactical semantics:                15
server-forwarded:                  13
fail-closed pending helpers:        2
```

## Qualification

Focused:

```bash
python3 tools/remaster/test-m1-stored-ufo-identity.py
python3 tools/remaster/test-m1-strategic-publication.py
python3 tools/remaster/test-m1-canonical-identity-completeness.py
python3 tools/remaster/test-m1-production-contract-normalization.py
python3 tools/remaster/test-m1-production-owner-extraction.py
python3 tools/remaster/test-m1-production-runtime-identity.py
python3 tools/remaster/test-m1-research-production-publication-map.py
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

Fresh landing builds:

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

After this slice lands:

1. qualify/publish `ItemId` as static production-subject definition identity;
2. define the aircraft production subject as its stable script/content definition key;
3. publish the complete create-production subject set;
4. extract a canonical `CreateProduction` owner without UI selected-state dependence;
5. then continue stored-UFO recovery/transfer owners and the remaining M1 families.
