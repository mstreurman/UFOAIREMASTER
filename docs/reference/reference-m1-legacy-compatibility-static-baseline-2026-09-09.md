# M1 legacy compatibility static baseline — 2026-09-09

Baseline repository commit:

```text
cefabf0ef5686b76921f10418dcb19a02152ade3
feat: qualify M1 stored UFO identity
```

## Qualified source anchors

This reference records the static compatibility anchors observed at the baseline before the contract hardening slice is applied.

### Campaign save

- `src/client/cgame/campaign/cp_save.h`
  - `SAVE_FILE_VERSION 4`
  - `SAVEGAME_EXTENSION "savx"`
  - inherited `saveFileHeader_t` layout
- `src/client/cgame/campaign/save/save.h`
  - `SAVE_ROOTNODE "savegame"`
- `src/client/cgame/campaign/cp_save.cpp`
  - one shared canonical campaign serializer/loader
  - uses `SAVE_FILE_VERSION`, `SAVEGAME_EXTENSION` and `SAVE_ROOTNODE`
  - no remaster-specific save branch

### Tactical wire

- `src/common/common.h`
  - `PROTOCOL_VERSION 18`
  - inherited `svc_ops_e` and `clc_ops_e`
- `src/game/q_shared.h`
  - inherited `event_t`
  - inherited `player_action_t`
- `src/game/q_shared.cpp`
  - inherited `pa_format[]`
- `src/client/presentation/tactical_intent_legacy_adapter.cpp`
  - typed remaster intents lower to inherited `MSG_Write_PA(PA_...)` calls
  - end-turn lowers to inherited `clc_endround`
  - Reload and AbortMission remain fail-closed until qualified request helpers exist

## Qualification level

This artifact adds continuous static guards for the anchors above.

It does **not** claim that the four-direction cross-binary matrix has already been executed. That remains a separate dynamic qualification task:

```text
classic save -> remaster load
remaster save -> classic load
classic client -> remaster server
remaster client -> classic server
```

This distinction is intentional: source/ABI preservation is now mechanically guarded, while real executable interoperability must still be demonstrated before release claims are made.
