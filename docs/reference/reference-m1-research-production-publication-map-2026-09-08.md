# Reference — M1 Research + Production Publication Map

**Date:** 2026-09-08
**Artifact baseline:** `24fba00e0d8d68befcba126fde57c1d1ee850328`
**Status:** local qualification required

## Purpose

The typed strategic catalog already contains research and production intents, but the
immutable strategic snapshot did not publish the identities/state needed for new
presentation to originate those intents safely.

This slice closes the publication-side gap only. It does not change the strategic
authority ledger.

## Technology identity

`technology_t::idx` is projected as:

```text
canonical::TechnologyId
```

The immutable view is:

```text
StrategicTechnologyView
    TechnologyId id
    BaseId base
    research status
    researchable
    collected
    scientist count
    remaining research time
    overall research time
    name
```

`base` is invalid when the technology is not currently attached to a research base.

The ID is an index-backed canonical runtime identity for the current initialized
technology tree. Presentation must not treat it as a cross-content-version persistent
database key.

## Production location mapping

Each current queue entry is projected as:

```text
(BaseId, queueIndex)
```

with immutable state:

```text
StrategicProductionView
    BaseId base
    TechnologyId technology
    queueIndex
    production type
    amount
    frame
    totalFrames
```

`TechnologyId` identifies the technology backing the item/aircraft/disassembly subject
when available.

### Important identity rule

`queueIndex` is **not a stable entity identity**.

Legacy production queues are compact arrays. `PR_QueueDelete` compacts entries and
`PR_QueueMove` changes their indices. Therefore:

```text
(BaseId, queueIndex)
```

means only "the entry at this location in this immutable snapshot".

It must not be used by a future typed mutation bridge without an additional stale-safe
identity/revision contract.

## Why ProductionId is not fabricated here

`canonical_identity.h` already defines `canonical::ProductionId`, and
`StrategicIntent` already contains a `ProductionId` field. However, the legacy
production subsystem does not currently maintain a stable per-logical-entry runtime
identity that survives queue moves/compaction.

This slice deliberately does **not** invent a `ProductionId` by hashing queue position
or subject fields. Duplicate queue subjects and compaction would make that unsafe.

The next production-mutation contract pass must establish one of:

1. a real stable runtime production identity maintained by the production subsystem; or
2. an explicit queue revision/generation carried from publication to mutation and
   rejected when stale.

Until then, production mutation intents remain fail-closed.

## Authority accounting

Unchanged by this publication-only slice:

```text
strategic: 15 canonical-applied / 42 fail-closed
tactical:  13 server-forwarded / 2 fail-closed
```

Research owner extraction can follow using published `TechnologyId`.

Production owner extraction must wait for the stale-safe production identity/revision
decision above.

## Qualification

Focused publication lanes:

```bash
python3 tools/remaster/test-m1-research-production-publication-map.py
python3 tools/remaster/test-m1-strategic-publication.py
python3 tools/remaster/test-m1-authoritative-intent-surface.py
```

Cheap production compile:

```bash
cmake --build build-m0-legacy-f44 --target ufo --parallel 8
```

Canonical preservation:

```bash
python3 tools/remaster/run-m0-canonical-regression.py --verify
```

Expected unchanged digest:

```text
33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2
```

Fresh builds:

```bash
rm -rf build-m0-legacy-f44
cmake --preset legacy-m0-f44
cmake --build --preset legacy-m0-f44

python3 tools/remaster/provision-m0-slang.py
rm -rf build-m0-remaster-f44
cmake --preset remaster-m0-f44
cmake --build --preset remaster-m0-f44
```

The project has no project-wide CMake install target; no `cmake --install` step is
applicable.
