# 094 — Legacy save and multiplayer compatibility contract

Status: **accepted M1 compatibility contract**

Scope: canonical campaign persistence and tactical client/server wire compatibility during the remaster migration.

## 1. Promise

Within the current compatibility epoch, a remaster build must preserve the two canonical interchange boundaries that users can carry between compatible legacy and remaster executables:

1. campaign savegames; and
2. tactical multiplayer client/server traffic.

This promise applies to the preserved project reference baseline and qualified legacy/remaster builds that remain in the same compatibility epoch. It is **not** a promise to support every historical UFO:AI release, old renderer/UI implementation, Lua/UI mod ABI, arbitrary total conversion, or source-patch mod.

Presentation implementation is intentionally outside this compatibility ABI. Vulkan, ray tracing, OpenAL, Jolt, C++26 presentation runtime state, retained/new UI state, renderer caches, frame history, runtime asset caches and other remaster-only presentation data may evolve without changing canonical persistence or gameplay transport.

## 2. Savegame contract

### 2.1 Canonical owner

`src/client/cgame/campaign/cp_save.cpp` remains the single campaign save/load owner while this compatibility epoch is active. A remaster build must not introduce a parallel remaster serializer for canonical campaign state.

The inherited format anchors are compatibility ABI:

- `SAVE_FILE_VERSION == 4`;
- extension `savx`;
- XML root node `savegame`;
- `saveFileHeader_t` field order and fixed-capacity character arrays;
- the canonical subsystem save/load path and subsystem XML semantics.

The current binary header source order is:

```text
uint32_t version
uint32_t compressed
uint32_t subsystems
uint32_t dummy[13]
char gameVersion[16]
char name[32]
char gameDate[32]
char realDate[32]
uint32_t xmlSize
```

The contract pins source field order/capacities rather than `sizeof(saveFileHeader_t)`, because compiler/platform padding is not a portable compatibility definition.

### 2.2 Remaster-only state

Presentation/runtime-only state must not be serialized into the canonical campaign save merely to preserve remaster implementation state.

In particular:

- presentation IDs are not save identities by default;
- runtime-only identities such as `ProductionId` are reconstructed after load rather than persisted;
- an identity may use an existing save field only after that field has been qualified as canonical persistent identity (for example the stored-UFO `idx` qualification);
- renderer, Vulkan, ray tracing, audio, Jolt, UI-layout, frame-history, cache and Presentation World state are outside the canonical campaign save ABI.

### 2.3 Intentional save break

An intentionally incompatible save change requires all of the following in the same change set:

1. an explicit architecture decision explaining why compatibility is being broken;
2. a new save compatibility epoch and the appropriate `SAVE_FILE_VERSION` change;
3. a migration path or a documented rejection path for older saves;
4. an updated compatibility manifest and static guards; and
5. cross-binary fixtures proving every supported migration/interchange direction.

Changing a save ABI anchor without those companion changes is a regression.

## 3. Tactical multiplayer wire contract

### 3.1 Canonical protocol owner

The remaster does not define a second gameplay protocol. The inherited client/server protocol remains authoritative.

The current wire anchors include:

- `PROTOCOL_VERSION == 18` in `src/common/common.h`;
- `svc_ops_e` opcode order;
- `clc_ops_e` opcode order;
- `event_t` event order in `src/game/q_shared.h`;
- `player_action_t` order in `src/game/q_shared.h`;
- the corresponding `pa_format[]` field layouts in `src/game/q_shared.cpp`.

Because these enums are transmitted as integer opcodes, insertion/reordering is an ABI change even when source code still compiles.

### 3.2 Remaster tactical intent lowering

Typed remaster tactical intents are a local presentation/client boundary, not a new network transport.

`src/client/presentation/tactical_intent_legacy_adapter.cpp` must lower supported intents to inherited `PA_*` requests or inherited `clc_*` messages. The authoritative server continues to receive canonical legacy protocol messages.

`EntityId` used by the tactical presentation boundary is projected from the inherited local-entity `entnum`; it is not a replacement wire identifier.

If a typed action cannot be expressed through a qualified inherited request helper, it must fail closed until that canonical request path is extracted. It must not gain a remaster-only gameplay opcode as a shortcut.

### 3.3 Intentional protocol break

An intentionally incompatible multiplayer change requires all of the following in the same change set:

1. an explicit architecture decision;
2. a protocol compatibility epoch/version change (`PROTOCOL_VERSION` or its accepted successor);
3. an updated opcode/layout manifest and static guards;
4. an explicit handshake/rejection/migration policy; and
5. live cross-binary client/server qualification for every supported direction.

Changing a wire ABI anchor without those companion changes is a regression.

## 4. Required qualification

### 4.1 Static qualification — continuous guard

`tools/remaster/test-m1-legacy-save-compatibility-contract.py` guards the save version, extension, root, binary header source layout, shared canonical serializer ownership and the absence of a remaster-specific save fork.

`tools/remaster/test-m1-legacy-wire-compatibility-contract.py` guards protocol version, `svc`/`clc` opcode order, tactical event/player-action opcode order, `pa_format[]`, and the remaster tactical intent lowering seam.

`tools/remaster/m1-legacy-compatibility-contract.tsv` is the machine-readable manifest of the current epoch.

`tools/remaster/run-m1-legacy-compatibility-qualification.sh` runs both compatibility guards and the already-established identity/publication guards that protect the presentation/canonical boundary.

### 4.2 Dynamic cross-binary qualification — release/interchange gate

Static guards prevent accidental schema/protocol drift but do not substitute for real process interoperability.

Before a release may claim completed classic/remaster interchange qualification, the following matrix must be exercised with binaries built from the frozen classic reference and the candidate remaster:

```text
classic save -> remaster load
remaster save -> classic load
classic client -> remaster server
remaster client -> classic server
```

The multiplayer cases must complete connection/handshake and execute representative tactical actions through canonical server authority. The save cases must load a representative campaign, re-save where applicable, and pass canonical-state checks.

Until reproducible cross-binary evidence exists, the project may claim **format/protocol preservation by explicit contract and static qualification**, but must not claim completed cross-binary interoperability qualification.

## 5. Content/version qualification

Wire compatibility alone is insufficient for safe multiplayer. Cross-play qualification also requires compatible canonical game/content data: maps/BSPs, script definitions, items, actors, weapons, game rules and event semantics.

Presentation-only assets may differ.

The supported claim is therefore:

> Compatible legacy and remaster builds in the same compatibility epoch, using a qualified canonical content revision, share the inherited save and gameplay-wire formats.

## 6. Relationship to other architecture

This contract strengthens, rather than replaces:

- ADR-001 canonical gameplay preservation;
- ADR-010 preserve complete tactical event protocol;
- architecture 075 canonical spatial preservation;
- architecture 078 strategic/Geoscape presentation separation;
- architecture 080 migration roadmap;
- architecture 091 implementation execution strategy;
- architecture 093 presentation action authority/intent completeness.

The governing rule is:

> **New presentation/runtime architecture may replace presentation implementation, but it may not silently redefine canonical persistence or gameplay transport.**
