# Reference — M1 Authoritative Intent Surface v1 Qualification

**Date:** 2026-09-08  
**Status:** QUALIFIED AT STATED SCOPE  
**Qualified baseline lineage:** `1dd974017f25d5bda5cc5b82b48d2590e574e50f` or descendant  
**Canonical regression evidence digest:** `33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2`

## 1. Scope qualified

This qualification closes the **typed authoritative intent surface** and its fail-closed legacy adapters.

It does **not** claim that every strategic intent already reaches a canonical owner.

Qualified bridge accounting remains:

```text
strategic authoritative semantics: 57 / 57 typed
strategic canonical-applied:         3 / 57
strategic fail-closed pending:      54 / 57

tactical authoritative semantics:   15 / 15 typed
tactical server-forwarded:          13 / 15
tactical fail-closed pending:        2 / 15
```

The fail-closed entries are intentional migration state. They must not be converted to command/cvar fallback.

## 2. Public contract qualification

The authoritative intent surface lane passed:

```text
Strategic intent/publication header coexistence: C++11 PASS
Strategic authoritative semantic coverage:      57 / 57
Tactical semantic coverage:                     15 / 15
Presentation authority guard:                   PASS
Bridge-accounting audit:                        PASS
```

`StrategicPosition` is now one shared value-only public type used by intent and snapshot/publication contracts.

## 3. Historical M1 compatibility lanes

The seed intent-catalog expansion lane passed:

```text
strategic compatibility catalog: 5 entries
tactical compatibility catalog:  2 entries
strict C++11 public contracts:    PASS
strict C++26 bounded runtimes:    PASS
FIFO/capacity/reset/sequence:     PASS
strategic canonical mappings:     PASS
tactical PA_* authority mapping:  PASS
integration GoogleTests:          3 / 3
sealed src/tests/CMakeLists.txt:   unchanged
```

The strategic typed-intent dispatch lane passed:

```text
C++11 public intent contract:                 PASS
bounded C++26 intent/result runtime:          PASS
queue FIFO/capacity/reset/sequence:           PASS
Main-before-campaign-before-publication:      PASS
canonical time-lapse validation/mutation:     PASS
integration GoogleTests:                      3 / 3
sealed src/tests/CMakeLists.txt:               unchanged
```

Previously qualified publication lanes remain green.

## 4. Canonical preservation qualification

The M0 canonical regression qualification passed on the authoritative-intent tree:

```text
canonical test build artifacts: PASS
tracked fixture staging:        PASS
fixture map compilation:        PASS
enabled test discovery:         108
core regression tests:          104
deferred asset sweeps:          4

canonical regression pass 1:    104 / 104 PASS
canonical regression pass 2:    104 / 104 PASS
two-run trace repeatability:    PASS
M0.5 digest verify:             PASS
```

Verified digest:

```text
33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2
```

## 5. Fresh production builds

Fresh legacy production configure/build:

```text
GCC: 16.2.1
legacy build: [391/391] Linking CXX executable ufo
result: PASS
```

Slang provisioning:

```text
v2026.17 existing cache verified
result: PASS
```

Fresh remaster dependency discovery:

```text
Vulkan:   1.4.341
SDL3:     3.4.14
OpenAL:   1.25.2
FFmpeg:   accepted API majors
Slang:    2026.17
Jolt:     5.6.0
spirv-val found
b3sum found
ccache found
```

Fresh remaster production build:

```text
[12/12] Linking CXX executable ufo
result: PASS
```

## 6. Authority guarantees retained

The qualification preserves these architectural rules:

```text
presentation never falls back through command strings/cvars
strategic gameplay mutation belongs to campaign/Main canonical owners
tactical client boundary never claims canonical application
tactical canonical acceptance remains game-server owned
selection compatibility entries are deprecated migration bridges
presentation context is not gameplay authority
```

## 7. Next implementation phase

Classification work is complete for this surface.

The next M1 work is **canonical owner extraction / request helper completion**.

Recommended order:

```text
1. Aircraft + Geoscape
   - StartAircraft
   - StopAircraft
   - SetAircraftDestination
   - PursueUfo
   - ChangeAircraftHomebase
   - related mission launch paths

2. Bases + installations
   - build / rename / destroy
   - facility construction/destruction
   - defence target/autofire

3. Research + production
   - staffing / stop
   - production queue/configuration

4. Employees + team/equipment
   - hire/fire/rename
   - aircraft crew
   - aircraft/base-defence equipment
   - alien containment

5. Market + transfer
   - typed market transactions
   - bounded transfer manifest commit

6. UFO recovery + save/load
   - canonical UfoSaleOfferId ownership/revalidation
   - store/destroy/transfer recovered UFOs
   - save/load semantic paths

7. Remaining tactical helpers
   - Reload
   - AbortMission
```

For each owner family:

```text
legacy callback rule
    -> campaign/server-owned Try... or request helper
    -> typed adapter resolves explicit IDs/payload
    -> no UI-global dependency
    -> focused integration tests
    -> bridge accounting decreases fail-closed count
```

## 8. Exit condition for owner extraction

The authoritative intent migration is complete only when:

```text
strategic canonical-applied: 57 / 57
strategic fail-closed:        0 / 57

tactical server-forwarded:   15 / 15
tactical fail-closed:         0 / 15
```

while canonical regression, publication ordering, and production builds remain green.
