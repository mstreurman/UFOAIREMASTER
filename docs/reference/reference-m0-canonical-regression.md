# M0.5 canonical regression / reference harness

**Status:** M0.5 implementation mechanism

## Purpose

M0.5 freezes a reproducible preservation baseline for legacy UFO:AI canonical authority before presentation migration begins.

The baseline deliberately uses existing upstream assertions rather than inventing new gameplay behavior. The selected source scope covers campaign/state logic, characters, event parsing/scheduling, game rules, inventory, map-definition validation, random-map assembly (RMA), parsers, routing, scripts, shared utilities, deterministic buffers, and generic helpers. Renderer, UI/UI-level-2, and particle suites are excluded because presentation output is not canonical game state; the web API suite is excluded as external integration rather than canonical simulation authority.

The selected source scope is expected to expose 108 enabled GoogleTests on the Fedora 44 reference workstation. One additional RMA test macro (`RandomMapAssemblyTest.NewSeedlists`) exists in source but is compile-time excluded because `SEED_TEST` is defined as `0`. M0.5 splits the 108 exposed tests into two explicit lanes:

- **core canonical assertion lane:** 104 tests that can be reproduced from a clean M0 checkout using canonical runtime data plus dedicated unit-test fixtures, including six compiled `RandomMapAssemblyTest` cases;
- **production-map asset sweep lane:** `GameTest.CountSpawnpointsStatic`, `GameTest.CountSpawnpointsRMA`, `MapDefTest.MapDefsSingleplayer`, and `MapDefTest.MapDefsMultiplayer`, which load/validate the compiled production BSP corpus and are deliberately recorded as deferred rather than silently depending on workstation-prebuilt maps.

The core harness:

1. verifies the committed M0.3 reference environment manifest;
2. verifies the committed M0.4 clean-build/launch evidence identity;
3. requires Fedora `gtest-devel` as an M0.5 test-only prerequisite and records its exact NEVRA;
4. deletes and recreates `build-m0-legacy-f44/` using `legacy-m0-f44` with `UFOAI_REMASTER=OFF` and `RelWithDebInfo`;
5. preserves `DISABLE_MAPS_COMPILE=ON`, but enables only the legacy `ufo2map` test tool for this harness (`DISABLE_TOOLS=OFF`, `DISABLE_UFO2MAP=OFF`, `DISABLE_UFOMODEL=ON`);
6. replaces the configure-time `base/` copy with a stage containing only Git-tracked canonical runtime data;
7. builds `ufotestall`, `ufo2map`, and the canonical `base/game.so` dependency;
8. stages only Git-tracked `unittest/` fixture data into the clean build root;
9. compiles `unittest/maps/test_game.map` and `unittest/maps/test_routing.map` into build-local BSP fixtures with the historical `ufo2map` test flags under an isolated HOME/XDG environment;
10. derives all selected GoogleTest identities directly from the frozen test-case source scope while retaining separately declared support sources in the corpus hash;
11. verifies all 108 enabled selected tests are exposed by `ufotestall --gtest_list_tests`, and verifies the compile-time-excluded `RandomMapAssemblyTest.NewSeedlists` is not exposed;
12. executes the 104-test core lane twice from the clean build root with independently fresh HOME/XDG state for discovery, pass 1, and pass 2;
13. requires both core runs to pass and to execute the same ordered test trace;
14. fingerprints the tracked `base/` runtime-data tree and tracked `unittest/` fixture tree, and folds those identities, the explicit deferred asset-sweep identities/reasons, and dedicated test-map source list into the canonical corpus;
15. records SHA-256 identities for the two generated unit-test BSP fixtures;
16. emits deterministic reference evidence plus BLAKE3-256 identity.

## Authority boundary

The generated corpus is an assertion/reference baseline, not a screenshot or renderer baseline. A passing M0.5 run means the documented 104-test core legacy canonical-state and protocol assertion lane passes under the documented build/tool state. It does not claim presentation parity or complete production-map asset validation.

`test_events.cpp` is part of the selected scope, so existing legacy event parsing and scheduling assertions are included as protocol/event fixtures. The current M0.5 harness does not fabricate a new whole-game replay format; future seam-specific record/replay fixtures may extend the preservation corpus without changing canonical authority.

`test_shared.cpp` is explicitly classified as a support source: it contributes shared test machinery and is hashed into the canonical corpus, but it does not itself define `TEST`/`TEST_F` cases and therefore is not required to enumerate a GoogleTest identity.

## Legacy test fixture contract

The historical GNU Make `testall` target does **not** compile the complete production map corpus. It builds `ufo2map` and specifically compiles the dedicated `unittest/maps/test_game.map` and `unittest/maps/test_routing.map` BSP fixtures used by game/routing assertions.

The committed M0 preset intentionally sets both `DISABLE_TOOLS=ON` and `DISABLE_MAPS_COMPILE=ON` because the M0.4 canonical client smoke does not require developer tools or a full production-map rebuild. M0.5 therefore overrides only the test-tool portion needed to reproduce historical unit-test prerequisites while keeping production map compilation disabled.

The harness replaces the configure-time build copy of `base/` with only Git-tracked canonical runtime files, stages tracked test fixtures into `build-m0-legacy-f44/unittest/`, and runs `ufotestall` from `build-m0-legacy-f44/`. The legacy filesystem then resolves both `./base` and `./unittest` from one clean, disposable build root. This prevents ignored/untracked source-tree files or user-local game data from becoming undeclared reference inputs.

Discovery, pass 1, and pass 2 each receive a distinct fresh HOME/XDG state tree. This prevents a previous invocation's writable user data from becoming an implicit prerequisite for a later invocation.

The tracked source `base/` runtime tree and `unittest/` fixture tree are independently fingerprinted into M0.5 evidence. The two generated build-local BSP fixtures are required to exist and their SHA-256 identities are recorded. Fixture compilation runs with an isolated HOME/XDG state so `ufo2map` cannot consume workstation-local `~/.ufoai` data.

## Production-map asset sweep lane

`GameTest.CountSpawnpointsStatic`, `GameTest.CountSpawnpointsRMA`, `MapDefTest.MapDefsSingleplayer`, and `MapDefTest.MapDefsMultiplayer` are real canonical/content validation tests, but they are not valid clean-M0 core assertions without a compiled production BSP corpus. The two `MapDefTest` cases also choose a wall-clock seed unless an explicit test property supplies one, which makes them a poor fit for the deterministic core lane even after BSP availability is solved.

The first M0.5 revision-003 execution demonstrated this distinction: after fixing fixture lookup, all earlier fixture-backed failures passed, while `GameTest.CountSpawnpointsStatic` terminated through the engine debugger trap. Running that test alone under GDB with the engine `SIGTRAP` hook suppressed exposed repeated `SV_Map()` load failures beginning with `bunker` and continuing across production static maps. This is consistent with absent production BSPs, not a canonical simulation regression.

M0.5 records all four production-map sweep test identities and their prerequisite reasons in deterministic evidence instead of dropping them from the selected source scope. A separate production-map asset-completeness lane can later build/supply the full BSP corpus and execute them without changing the M0.5 core authority definition.

## GoogleTest dependency ownership

GoogleTest is intentionally **not** retroactively added to the M0.3 reference environment manifest. M0.3 and M0.4 remain immutable provenance records. `gtest-devel` is an M0.5 test-only prerequisite whose exact Fedora NEVRA is captured in M0.5 evidence.

Install it on the Fedora 44 reference workstation with:

```bash
sudo dnf install gtest-devel
```

## Generated evidence

A successful run writes:

```text
docs/reference/reference-m0-canonical-regression.txt
docs/reference/reference-m0-canonical-regression.b3
```

The evidence records the fixed canonical source revision, M0.4 baseline revision and evidence identity, M0.3 environment identity, exact test-only GoogleTest package identity, hashes of every corpus input, tracked `base/` runtime-data and `unittest/` fixture-tree fingerprints, all 108 exposed selected test identities split into 104 core tests plus four deferred production-map sweeps, plus the one source-level RMA macro that is compile-time excluded, the test-only `ufo2map` build override, isolated build-local dedicated BSP fixture compilation with generated BSP SHA-256 identities, the clean-build-root runtime contract, per-invocation state isolation, and the normalized two-run core execution trace identity.

Raw configure/build/fixture-map/list/test logs remain under the ignored `build-m0-legacy-f44/` tree.

## Revision 005 reproducibility hardening

Revision 004 produced a passing 104-test core reference, but its fixture-map compiler inherited the caller HOME. The Fedora execution log therefore showed `ufo2map` adding `~/.ufoai/2.6-dev/base` as a search path. Even though the resulting tests passed, workstation-local data was an undeclared possible input and the generated BSP bytes were not represented in evidence.

Revision 005 closes that gap without changing canonical test membership: it stages only Git-tracked `base/` runtime data into the clean build root, runs `ufo2map` with an isolated HOME/XDG environment, fingerprints the tracked runtime-data tree, and records SHA-256 for both generated unit-test BSPs. Capture and immediate `--verify` must reproduce those identities byte-for-byte through the evidence comparison.
