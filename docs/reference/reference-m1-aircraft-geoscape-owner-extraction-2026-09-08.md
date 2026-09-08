# Reference — M1 Aircraft + Geoscape canonical-owner extraction

**Date:** 2026-09-08  
**Artifact baseline:** `ead94fa21f572925c71b96ed02dbd6aa747dbd68`  
**Scope:** first strategic canonical-owner extraction slice

## Result

This slice extracts five callback/geoscape-owned strategic actions into canonical campaign ownership in `cp_aircraft.cpp`:

```text
StartAircraft
StopAircraft
SetAircraftDestination
PursueUfo
ChangeAircraftHomebase
```

After this slice the authoritative strategic bridge ledger is:

```text
strategic authoritative semantics: 57 / 57 typed
strategic canonical-applied:         8 / 57
strategic fail-closed pending:      49 / 57
```

No command-string or cvar fallback is introduced.

## Canonical owner rules

`AIR_TryStartAircraft` owns the existing Command Centre gate, pilot requirement, in-base weapon reload, canonical “Aircraft started” message, and transition to `AIR_IDLE`. The legacy callback now only selects the current base aircraft, translates canonical rejection reasons to UI feedback, updates presentation selection, and closes UI windows.

`AIR_TryStopAircraft` owns the legacy order-clear mutation (`AIR_IDLE`). The callback resolves its command argument and calls the owner.

`AIR_TrySetAircraftDestination` owns the legacy `GEO_Click` checks/mutation: aircraft must be on the geoscape, fuel must be sufficient, route is calculated, status becomes `AIR_TRANSIT`, the aircraft target is cleared, and route time/point are reset. `GEO_Click` is now only a presentation/input caller.

`AIR_TryPursueUFO` owns the popup's Command Centre validation and delegates the actual chase/fuel/intercept behavior to the existing `AIR_SendAircraftPursuingUFO` campaign helper. Legacy popup UI only renders the Command Centre rejection message.

`AIR_TryChangeHomebase` owns same-base rejection, delegates capacity/building validation to `AIR_CheckMoveIntoNewHomebase`, and delegates canonical transfer/mutation to `AIR_MoveAircraftIntoNewHomebase`.

## Typed adapter rules

The strategic adapter only resolves typed IDs and bounded payloads before calling the owners:

```text
PHALANX AircraftId: high UFO bit rejected; bounded before legacy lookup
UFO AircraftId: high UFO bit required; low index checked against ccs.numUFOs before UFO_GetByIDX
BaseId: bounded before B_GetFoundedBaseByIDX
StrategicPosition: finite longitude/latitude/altitude; longitude [-180,180], latitude [-90,90]
```

The adapter does not duplicate campaign fuel, hangar, pilot, Command Centre, route, pursuit, or homebase rules.

## Mission-launch analysis

`StartMission` deliberately remains fail-closed in this slice. `CP_StartSelectedMission` still relies on `GEO_GetMissionAircraft()` / selected-mission globals and then performs mission-result reset, mission/team checks, retry teardown, battle parameter setup, and battlescape launch. Extracting it safely requires an explicit-ID campaign owner and is not a low-risk extension of the aircraft movement slice.

The legacy popup mission intercept branch also keeps its existing Command Centre gate until that mission-launch family is extracted. This avoids silently changing the already-qualified `SendAircraftToMission` contract while working on the five targeted actions.

## Qualification expectations

Focused static owner-extraction lane:

```bash
python3 tools/remaster/test-m1-aircraft-geoscape-owner-extraction.py
python3 tools/remaster/test-m1-authoritative-intent-surface.py
```

Required preservation gates remain the M0.5 canonical regression verification and fresh legacy/remaster production builds.
