# M1 EmployeeId / CharacterUcn allocator and wire qualification

**Baseline:** `7bb19b74289b3ffec024835c335063fee7ba84d7`

**Date:** 2026-09-09

## Purpose

The second-pass identity audit classified `character_t::ucn` as a persistent/network correlation key and left `EmployeeId` pending until two properties were proven:

1. loaded campaign/team characters cannot cause the global UCN generator to reuse an existing identity;
2. the exact inherited tactical wire domain for UCN is known and enforced.

This slice closes those properties without changing the inherited campaign save schema or tactical protocol version.

## Source-derived findings

### Existing generation

`CL_GenerateCharacter` allocates directly from:

```cpp
chr->ucn = cls.nextUniqueCharacterNumber++;
```

`nextUniqueCharacterNumber` lives in `client_static_t`, so it is process-local allocator state rather than persisted canonical state.

### Existing save/load

`GAME_SaveCharacter` already persists `character_t::ucn`, and both campaign employee loading and standalone team-file loading route character data through `GAME_LoadCharacter`.

Before this slice, `GAME_LoadCharacter` restored `chr->ucn` but did not reconcile `cls.nextUniqueCharacterNumber`. A fresh process could therefore load existing UCNs while the allocator remained below them, allowing a later generated character to reuse an already-loaded UCN.

### Exact inherited wire domain

The tactical protocol's short helpers are signed-short semantic:

```cpp
#define LittleShort(X) (short)SDL_SwapLE16(X)
```

`NET_ReadShort` returns that signed-short result as `int`.

Therefore a nonnegative UCN that must round-trip through the preserved classic protocol is restricted to:

```text
0 .. INT16_MAX
0 .. 32767
```

A generated value `32768` would decode as `-32768` through the inherited reader semantics.

The remaster must not silently reinterpret this field as unsigned because that would create a semantic classic/remaster fork without changing the protocol bytes/version.

## Hardening in this slice

### Shared validation/reconciliation

`cl_team` gains retained-C++11 helpers:

```cpp
bool CL_IsCharacterUCNWireRepresentable(int ucn);
bool CL_ReconcileCharacterUCN(int ucn);
```

The accepted UCN domain is exactly nonnegative signed 16-bit. `CL_ReconcileCharacterUCN` advances the process-local allocator to at least `loadedUcn + 1` without lowering it.

### Generation exhaustion

`CL_GenerateCharacter` validates the allocator before assignment. If no nonnegative signed-16-bit UCN remains, generation fails closed with `ERR_DROP` rather than creating an identity classic tactical wire cannot round-trip.

`32767` is the final valid generated UCN. After allocating it, `nextUniqueCharacterNumber == 32768`, which is an exhausted sentinel.

### Load reconciliation

A character that has otherwise loaded successfully is reconciled into the allocator before `GAME_LoadCharacter` returns success.

No allocator field is added to the save format. The allocator is reconstructed from existing persisted character identities.

### Duplicate-load rejection

Reconciliation prevents future reuse but cannot make an already-duplicate input unambiguous. This slice therefore rejects duplicate UCNs while loading:

- campaign employees, before duplicate insertion into canonical employee lists;
- standalone team files, before duplicate insertion into `chrDisplayList`.

A failed standalone team-info load resets the partially loaded team.

## EmployeeId conclusion

After this slice qualifies locally:

```text
EmployeeId
  backing value:       character_t::ucn
  runtime lifetime:    employee/character lifetime
  save lifetime:       persisted in existing character XML
  load behavior:       duplicate-rejected; allocator reconciled to max+1
  wire compatibility:  nonnegative signed-16-bit (0..32767)
  presentation state:  not yet published
  mutation owners:     still pending/fail-closed
```

`EmployeeId` can then be classified as a qualified direct persisted/wire-compatible mapping while employee publication and authoritative mutation extraction remain separate work.

## Compatibility invariants

This slice deliberately keeps:

```text
SAVE_FILE_VERSION = 4
PROTOCOL_VERSION  = 18
character save UCN field unchanged
tactical short field widths/order unchanged
```

No remaster-only identity state enters savegames or tactical messages.

## Qualification

The dedicated `M1EmployeeUcnTest` fixture proves:

1. loaded UCN reconciliation is monotonic and rejects values outside `0..32767`;
2. the inherited short path round-trips `32767` and demonstrates that `32768` decodes as `-32768`.

The focused Python gate additionally audits generation guard ordering, character-load reconciliation, duplicate campaign/team rejection, save/wire version anchors, registry state, and fixture ownership.

## Remaining M1 work

This slice does **not** publish employees or bridge employee mutations. Recommended continuation after qualification:

1. `ItemId` + aircraft production-subject qualification/publication;
2. canonical `CreateProduction` owner;
3. employee/team publication and owner extraction when that authority family is reached;
4. remaining recovery/transfer/defence identity and authority work.
