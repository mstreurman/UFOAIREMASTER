# Reference — M1 Research Owner Extraction

**Date:** 2026-09-08
**Baseline:** `0f04fbb57fb71926efa12ec9a8b636478da6d9f5`
**Status:** local qualification required

## Purpose

Extract the player-facing Research scientist-assignment mutations from legacy UI
callbacks into campaign-owned canonical helpers, while preserving existing research,
employee and laboratory-capacity behavior.

This slice qualifies exactly:

```text
AssignResearch
MaxAssignResearch
StopResearch
```

Production mutation remains fail-closed.

## Canonical identity

Research presentation already publishes:

```text
technology_t::idx -> canonical::TechnologyId
```

The legacy adapter resolves the typed `TechnologyId` with `RS_GetTechByIDX`. Presentation
does not receive or retain a raw `technology_t*`.

## Owner API

`cp_research.h/.cpp` gains:

```cpp
researchChangeResult_t RS_TryChangeScientists(
    technology_t* tech,
    base_t* base,
    int scientistDelta);

researchChangeResult_t RS_TryMaxAssignScientists(
    technology_t* tech,
    base_t* base);

researchChangeResult_t RS_TryStopResearch(
    technology_t* tech,
    base_t* base);
```

The result vocabulary distinguishes invalid identity/context, wrong-base requests,
invalid typed deltas, non-researchable topics, unavailable scientists, exhausted
laboratory space and inactive research.

## AssignResearch delta contract

Legacy `ui_research_change` historically interprets only the **sign** of its integer
argument and performs one scientist mutation per callback invocation.

The new typed intent does not silently reinterpret arbitrary magnitudes.

```text
typed scientistDelta = +1   add exactly one scientist
typed scientistDelta = -1   remove exactly one scientist
anything else               reject by canonical owner
```

The legacy callback preserves its old behavior by normalizing its command argument:

```text
positive -> +1
negative -> -1
zero     -> no mutation
```

This keeps legacy semantics while making the new typed contract unambiguous.

## Canonical mutation preservation

Assignment still uses the same existing state transitions:

```text
choose unassigned scientist
require statusResearchable
require CAP_LABSPACE > 0
tech->scientists++
tech->base = base
CAP_AddCurrent(..., +1)
employee->setAssigned(true)
tech->statusResearch = RS_RUNNING
```

Removal still uses `RS_RemoveScientist`, including capacity accounting and the existing
zero-scientist transition:

```text
tech->scientists--
CAP_AddCurrent(..., -1)

when scientists == 0:
    tech->base = nullptr
    tech->statusResearch = RS_PAUSED
```

Stop still delegates to the existing `RS_StopResearch`, which repeatedly removes
scientists using the canonical removal path.

## Presentation side effects

`CP_Popup("Not enough laboratories", ...)` is removed from `cp_research.cpp`.

The popup remains in the legacy `ui_research_change` callback and is emitted only when
the canonical owner returns `RS_CHANGE_NO_LAB_SPACE`.

Legacy UI refresh calls remain in `cp_research_callbacks.cpp`.

The typed adapter never calls:

```text
CP_Popup
UI_*
Cmd_ExecuteString
Cbuf_AddText
Cvar_Set
Cvar_SetValue
```

## Max assignment

`RS_TryMaxAssignScientists` preserves the legacy loop:

```text
while laboratory capacity remains:
    choose an unassigned scientist
    assign through the canonical low-level mutation
    stop when capacity/scientists/researchability prevents another assignment
```

The typed result is `Applied` if at least one scientist was assigned; otherwise the
canonical reason is returned and the typed intent is rejected.

## Authority accounting after qualification

```text
strategic authoritative semantics: 57
canonical-applied:                 18
fail-closed pending owners:        39

tactical semantics:                15
server-forwarded:                  13
fail-closed pending helpers:        2
```

The three newly applied strategic semantics are:

```text
AssignResearch
MaxAssignResearch
StopResearch
```

## Explicit non-goals

This slice does not:

- create or mutate `ProductionId`;
- bridge production queue mutation;
- change research timing, requirements, completion, save/load or balance;
- change scientist identity/storage;
- make presentation authoritative;
- add command/cvar fallback.

## Qualification

Focused:

```bash
python3 tools/remaster/test-m1-research-owner-extraction.py
python3 tools/remaster/test-m1-research-production-publication-map.py
python3 tools/remaster/test-m1-strategic-publication.py
python3 tools/remaster/test-m1-authoritative-intent-surface.py
python3 tools/remaster/test-m1-canonical-identity-completeness.py
```

Cheap production compile:

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

After this slice is qualified and pushed:

1. implement stable campaign-owned runtime `ProductionId` mapping;
2. migrate production mutation APIs away from queue index;
3. bridge Decrease/MoveUp/MoveDown/Stop production operations;
4. keep IncreaseProduction and SetProductionAmount separate until their subject/amount
   contracts are normalized.
