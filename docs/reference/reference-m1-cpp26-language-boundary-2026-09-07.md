# Reference — M1 C++11/C++26 Language-Boundary Qualification

**Qualified:** 2026-09-07  
**Repository lineage baseline:** `5b45c193aff9a9ff170d1aaacabaa5a786702c3d`  
**Reference workstation:** Fedora 44  
**Primary compiler:** GCC 16.2.1  
**libstdc++ dual ABI:** `_GLIBCXX_USE_CXX11_ABI=1`  
**Status:** PASS

## Purpose

This reference qualifies the first split-language production boundary used by the UFO:AI remaster.

The qualified ownership model is:

```text
retained canonical / legacy production code
    C++11
        |
        | C++11-compatible strong IDs / immutable owning snapshots
        | same GCC/libstdc++ ABI family
        v
new remaster publication runtime
    C++26
```

The test harness is intentionally excluded from being language-ownership authority because dependency requirements may raise its effective language mode. On the reference Fedora environment, GoogleTest 1.17 causes `ufotestall` to compile as C++17. This is accepted and does not change the production C++11/C++26 boundary.

## Focused language-boundary qualification

Command:

```bash
python3 tools/remaster/test-m1-cpp26-language-boundary.py
```

Result:

```text
M1 C++26 language boundary focused lane: PASS
  GCC reference compiler: 16.2.1
  libstdc++ dual ABI setting: _GLIBCXX_USE_CXX11_ABI=1
  shared headers strict C++11: PASS
  shared headers strict C++26: PASS
  tactical publication strict C++26 -Werror: PASS
  strategic publication strict C++26 -Werror: PASS
  C++11 producer -> C++26 consumer ABI fixture: PASS
  CMake publication ownership: C++26
  production ufo legacy adapter ownership: C++11
  ufotestall language mode: dependency-driven; not used as boundary evidence
  sealed src/tests/CMakeLists.txt: unchanged
```

The mixed ABI fixture crosses real M1 value types rather than a trivial scalar ABI:

```text
TacticalSnapshot
StrategicSnapshot
strong canonical IDs
std::vector
std::string
```

The C++11 producer constructs and returns these values and the C++26 consumer validates them.

## Tactical publication qualification

Command:

```bash
python3 tools/remaster/test-m1-tactical-publication.py
```

Result:

```text
M1.2 tactical publication lane: PASS
  source/ownership audit: PASS
  sealed src/tests/CMakeLists.txt: unchanged
  dedicated legacy configure: PASS
  tactical publication GoogleTests: 3/3
```

Qualified tests:

```text
ProjectsOnlyCanonicalActorValues
PublishesOrderedSnapshotAndEventAfterMirrorMutation
PublicValueTypesStayPointerFreeAndCopyable
```

The production tactical publication implementation now uses:

```cpp
std::atomic<std::shared_ptr<const TacticalPublication>>
```

with acquire/release publication semantics, replacing the legacy `shared_ptr` atomic free functions that GCC 16 reported as deprecated and that are unsuitable for the C++26 runtime target.

## Strategic publication qualification

Command:

```bash
python3 tools/remaster/test-m1-strategic-publication.py
```

Result:

```text
M1 strategic publication focused lane: PASS
  public raw-pointer/type audit: PASS
  production publication ordering audit: PASS
  legacy projection coverage audit: PASS
  legacy adapter campaign prerequisite audit: PASS
  ufotestall source-ownership audit: PASS
  strict C++11 snapshot contract: PASS
  strict C++26 publication TU compile: PASS
```

The strategic snapshot contract remains C++11-compatible while the publication implementation is compiled as C++26.

## Canonical regression qualification

Command:

```bash
python3 tools/remaster/run-m0-canonical-regression.py --verify
```

Results:

```text
canonical test build artifacts: PASS
canonical test fixtures: PASS
canonical test discovery: PASS
  108 enabled exposed
  104 core
  4 deferred asset sweeps
  1 compile-time excluded
  0 disabled excluded

canonical regression pass 1: PASS (104 tests)
canonical regression pass 2: PASS (104 tests)
canonical two-run trace repeatability: PASS

M0.5 canonical regression verification: PASS
```

Canonical evidence identity:

```text
b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e
```

This is unchanged from the sealed pre-language-split canonical baseline.

## Fresh legacy production build

Commands:

```bash
cmake --preset legacy-m0-f44 --fresh
cmake --build --preset legacy-m0-f44
```

Result:

```text
configure: PASS
generate: PASS
build: PASS
[387/387] Linking CXX executable ufoded
```

Reference compiler:

```text
GNU 16.2.1
```

## Fresh remaster production build

Commands:

```bash
python3 tools/remaster/provision-m0-slang.py
cmake --preset remaster-m0-f44 --fresh
cmake --build --preset remaster-m0-f44
```

Results:

```text
M0 Slang provisioning: PASS (existing v2026.17 cache verified)
remaster dependency discovery: PASS
configure: PASS
generate: PASS
build: PASS
[422/422] Linking CXX executable ufoded
```

Observed dependency evidence:

```text
Vulkan: 1.4.341
SDL3: 3.4.14
OpenAL: 1.24.2
Slang: 2026.17
Jolt: v5.6.0
spirv-val: found
b3sum: found
ccache: found
```

The OpenAL 1.24.2 observation remains workstation evidence only. Architecture 092 / the audio ADRs define OpenAL Soft >=1.25.2 as the reference production-audio implementation baseline for eventual M8 qualification.

## Qualified build architecture

The implementation qualifies:

```text
root build:
    CMake >= 3.25
    root project enables CXX

retained production default:
    C++11
    standard required
    GNU extensions disabled on the Fedora reference lane

ufoai_remaster_publication:
    object library
    C++26
    standard required
    GNU extensions disabled

production ufo:
    C++11-owned legacy/adapters
    consumes C++26 publication object files

ufotestall:
    qualification harness
    may use a dependency-raised language standard
    consumes the same C++26 publication objects
    not used as production language-ownership evidence
```

The inherited global `-std=c++0x` / `-std=gnu++0x` language forcing is no longer the remaster build policy.

## Conclusion

The C++ language/toolchain boundary is **qualified**.

The project may now treat:

```text
new remaster runtime code -> C++26
retained canonical/legacy code -> C++11 initially
shared bridge headers -> C++11-compatible
```

as an implemented, tested production rule rather than a documentation-only decision.

No completed M1 canonical spatial, typed identity, tactical publication or strategic publication semantics were invalidated by the transition.

## Next implementation work

With the language/toolchain boundary sealed, M1 may continue with:

```text
typed presentation intent dispatch
temporary legacy-consumer adapters where required
```

before M2 begins the SDL3/Vulkan production runtime path.
