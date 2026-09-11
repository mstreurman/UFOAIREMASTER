# C++26 Language, Toolchain and Canonical-Boundary Contract

**Status:** Accepted implementation contract  
**Adopted:** 2026-09-07  
**Current M1 implementation baseline:** `e29739ec2f34fb21e43f664385f57ab5eca18e53`
**Primary platform:** Fedora 44 / GCC 16.2.x / libstdc++  
**Related:** architecture 006, 075, 078, 080, 091; ADR-001, ADR-024, ADR-047  
**Purpose:** Define the language-standard ownership, compiler/toolchain baseline, ABI boundary and dependency-version hardening used while the remaster runtime is built around retained canonical UFO:AI code.

## 1. Decision

The remaster does **not** perform a flag-day conversion of the inherited UFO:AI source tree to C++26.

The language split is architectural:

```text
retained canonical / legacy UFO:AI code
    C++11 initially
        |
        | narrow C++11-compatible bridge
        | typed IDs
        | immutable owning snapshots/publications
        | typed intents
        v
new remaster presentation/runtime code
    C++26
```

New remaster-owned runtime code targets **strict C++26** from the point where it becomes an independently owned build target.

Retained canonical/legacy targets stay C++11 initially and may be migrated later only when there is a concrete benefit and preservation evidence.

This avoids forcing a language modernization of the canonical simulation merely to let new renderer/UI/audio/runtime code use the current language.

## 2. Ownership, not file-by-file exceptions

Language mode follows target/subsystem ownership rather than arbitrary source-file exceptions.

Conceptual target ownership:

```text
legacy/canonical targets
    C++11
    gameplay
    campaign
    server
    common canonical spatial services
    temporary legacy consumers

canonical-presentation bridge/adapters
    C++11
    tactical legacy projection
    strategic legacy projection
    future canonical adapters

remaster runtime targets
    C++26
    immutable publication runtime
    typed intent runtime
    SDL3 platform layer
    Vulkan renderer
    retained UI
    Presentation World
    OpenAL presentation audio
    VFX/presentation physics integration
    remaster runtime asset systems
```

Exact target names are implementation details. The ownership split is normative.

Do not compile random legacy translation units as C++26 merely because they happen to be adjacent to new code.

## 3. CMake policy

The inherited global standard mutation:

```cmake
set(CMAKE_CXX_FLAGS "... -std=c++0x")
```

is not compatible with the accepted build architecture and must be removed when the implementation slice lands.

Language mode must be target-scoped.

Modern target baseline:

```cmake
set_target_properties(ufoai_remaster_runtime PROPERTIES
    CXX_STANDARD 26
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)
```

Legacy targets must receive an explicit C++11 policy rather than depending on an inherited global flag.

The C++26-aware build requires an authoritative CMake minimum of at least **3.25**, because CMake 3.25 added awareness of `CXX_STANDARD 26` / `cxx_std_26`.

The reference workstation already uses a newer CMake; the minimum here is a project contract, not a statement about the locally installed version.

## 4. Compiler and standard-library baseline

Initial reference compiler family:

```text
GCC 16.2.x
```

Current qualified workstation compiler at adoption:

```text
GCC 16.2.1
```

Clang may be added as a secondary qualification compiler, but it does not replace the primary GCC qualification lane unless explicitly decided later.

All in-process C++11/C++26 targets must use one compatible compiler/standard-library ABI family.

Required consistency includes:

```text
same libstdc++ ABI family
same _GLIBCXX_USE_CXX11_ABI setting
compatible exception/RTTI policy
compatible fundamental type ABI
compatible sanitizer/instrumentation assumptions for a given build
```

Do not treat the C++ language standard itself as an ABI firewall.

## 5. Shared bridge-header rule

Any header included by the retained C++11 side must remain valid C++11.

The bridge may contain:

```text
fixed-width integer value types
strong typed IDs
simple enums
standard-layout/trivially-copyable records where appropriate
C++11-compatible owning snapshot classes
C++11-compatible function declarations
```

The bridge must not require C++20/23/26 syntax or library vocabulary merely because the consumer is modern.

Examples forbidden in a shared C++11-facing header unless the legacy side has first migrated:

```text
std::span
std::expected
std::jthread
concepts/requires
C++20/23/26-only language syntax
C++26-only standard-library facilities
```

The C++26 implementation is free to convert bridge values immediately into richer modern internal types.

## 6. Canonical/presentation data boundary

The M1 boundary remains authoritative:

```text
canonical state
    -> legacy adapter on canonical/Main ownership
    -> immutable owning publication
    -> modern presentation consumers

presentation input
    -> typed intent
    -> canonical validation/mutation
    -> next immutable publication
```

Raw canonical pointers do not cross into the modern runtime.

The already-qualified typed identities, tactical snapshots/events and strategic snapshots remain valid under this language policy and are not to be redesigned merely for C++26.

## 7. STL and allocator ABI across the in-process seam

The current M1 snapshots contain owning `std::vector` and `std::string` values.

That is accepted for the in-process transition because all participating targets use the same pinned compiler/libstdc++ ABI configuration.

This is **not** a promise of a stable plugin/shared-library ABI.

Rules:

```text
do not expose this seam as a third-party binary ABI
do not mix incompatible libstdc++ ABI settings
do not pass ownership through separately versioned runtimes
prefer value/snapshot ownership over live shared object graphs
keep destruction in the same compatible runtime/toolchain domain
```

A future POD/serialization/sink-style bridge may be introduced if a separately versioned binary boundary becomes useful. C++26 adoption does not require that redesign now.

## 8. Exceptions and failure semantics

Canonical/presentation bridge calls should not rely on exceptions crossing the language/ownership seam.

Prefer:

```text
validated value results
explicit status/error values
typed rejection results
canonical mutation result followed by next publication
```

Modern C++26 code may use exceptions internally if the owning subsystem policy allows them, but exceptions are not part of the canonical/remaster bridge contract.

## 9. `shared_ptr` atomic hardening

The qualified tactical publication currently uses the legacy free-function `shared_ptr` atomic API:

```cpp
std::atomic_load_explicit(&latestPublication, ...);
std::atomic_store_explicit(&latestPublication, ...);
```

GCC 16.2.1 reports these functions as deprecated and directs users to `std::atomic<std::shared_ptr<T>>`.

The free-function `shared_ptr` atomic API is not accepted in the C++26 remaster target.

Modern ownership must use:

```cpp
std::atomic<TacticalPublicationPtr> latestPublication;

return latestPublication.load(std::memory_order_acquire);

latestPublication.store(publication, std::memory_order_release);
```

The strategic publication's current mutex-protected `shared_ptr` remains valid. It may later use `std::atomic<std::shared_ptr<...>>` for consistency if qualification shows that is preferable.

No atomic-`shared_ptr` type is exposed through the C++11 bridge header.

## 10. C++26 usage policy

C++26 is the required language mode for new remaster runtime targets.

It does **not** mean every new feature must be used.

Use modern language/library facilities where they simplify ownership, safety, concurrency, expressiveness or performance and are reliable in the pinned toolchain.

Do not make architecture depend on an immature facility solely because it is new.

A feature may remain temporarily unused even though the target compiles in C++26 mode.

## 11. Mixed-standard qualification gate

Before the repository may claim that C++26 is enabled for the remaster runtime, qualification must prove all of:

```text
shared bridge headers compile under strict C++11
shared bridge headers compile when consumed by strict C++26
legacy adapter target compiles as C++11
modern remaster runtime target compiles as C++26
CXX_EXTENSIONS is disabled for the modern target
C++11 producer + C++26 consumer compile/link/run fixture passes
same compiler/libstdc++ ABI settings are recorded
tactical atomic shared_ptr free functions are removed
canonical regression remains unchanged
legacy production build passes
remaster production build passes
clean mixed-standard rebuild passes
```

The existing strict C++11 M1 contract tests remain useful; they become the lower-side boundary qualification rather than being deleted.

## 12. Dependency/version hardening policy

The project deliberately uses a current technology stack, but version numbers play different roles.

### Vulkan

Runtime graphics contract:

```text
Vulkan core API >= 1.4
```

Do not hard-pin the engine requirement to a Vulkan registry/header patch revision such as `1.4.341`, `1.4.354` or `1.4.362`.

Development headers, registry and validation tooling should track an accepted current Vulkan 1.4.x revision.

Required extensions/features remain capability-tested explicitly.

At adoption:

```text
local remaster discovery: Vulkan 1.4.341
current Khronos registry: Vulkan 1.4.362
```

Those values are evidence, not different architectural API generations.

### Slang

Shader compiler policy:

```text
Slang v2026.17
exact project-local provisioned artifact
hash verified
```

At adoption, v2026.17 remains the latest stable Slang release.

Slang updates require explicit reprovisioning and shader/descriptor-heap qualification rather than an unrecorded floating update.

### OpenAL Soft / EFX / HRTF

Core audio API contract remains:

```text
OpenAL 1.1
```

Reference implementation baseline for the new production audio runtime:

```text
OpenAL Soft >= 1.25.2
```

Required reference capabilities:

```text
ALC_EXT_EFX
ALC_SOFT_HRTF
ALC_MAX_AUXILIARY_SENDS >= 2
```

Additional OpenAL Soft extensions are runtime capability-probed; absence of an optional extension must not break correctness unless a later architecture explicitly promotes it to required.

At adoption:

```text
current workstation package/discovery: OpenAL Soft 1.24.2
latest stable upstream: OpenAL Soft 1.25.2
```

The current workstation capture remains valid historical evidence but is below the accepted implementation baseline for eventual M8 production qualification. The local package/runtime must therefore be upgraded and requalified before M8 audio closure.

Current reference-workstation state after the 2026-09-07 environment rotation:

```text
OpenAL Soft 1.25.2 installed
M0.3 environment manifest: aa42dc88f980845c94fab1d6ff992657f935f25c13ac418c16aa25f3baa5d305
```

This satisfies the implementation-version baseline itself. M8 audio closure still requires the dedicated runtime capability/device/HRTF/EFX qualification and production-audio soak; installing 1.25.2 alone does not close M8.

EFX remains the required environmental-effects interface. HRTF remains user/runtime selectable rather than hardcoded always-on.

### Jolt

Jolt remains:

```text
v5.6.0
exact vendored commit and manifest identity
```

No language-standard decision changes presentation-only physics authority.

## 13. Adoption evidence

The policy was accepted after validation of repository head:

```text
5b45c193aff9a9ff170d1aaacabaa5a786702c3d
feat: add immutable strategic publication boundary
```

Observed build/regression state:

```text
canonical test discovery: 108 enabled exposed
canonical core: 104
canonical regression pass 1: 104/104 PASS
canonical regression pass 2: 104/104 PASS
two-run trace repeatability: PASS
canonical evidence:
b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e

legacy production build: PASS
remaster dependency discovery/configuration: PASS
Slang provision: v2026.17 PASS
```

GCC 16.2.1 independently reproduced the tactical `shared_ptr` atomic deprecation warning, confirming the first source-level modernization required by the C++26 slice.

## 13.1. Implementation qualification status

The split-language boundary was implemented and qualified on 2026-09-07.

Qualified evidence:

```text
GCC 16.2.1
_GLIBCXX_USE_CXX11_ABI=1
shared bridge headers strict C++11: PASS
shared bridge headers strict C++26: PASS
C++11 producer -> C++26 consumer ABI fixture: PASS
production ufo legacy adapter ownership C++11: PASS
ufoai_remaster_publication ownership C++26: PASS
tactical publication integration: 3/3 PASS
strategic publication focused lane: PASS
canonical regression: 104/104 PASS twice
two-run trace repeatability: PASS
legacy clean production build: PASS
remaster clean production build: PASS
```

Canonical evidence identity remains:

```text
b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e
```

The permanent evidence record is `docs/reference/reference-m1-cpp26-language-boundary-2026-09-07.md`.

The later 2026-09-07 OpenAL Soft 1.25.2 reference-environment rotation intentionally resealed M0.3/M0.5 evidence without changing the canonical 104-test corpus or two-run trace. The current M0.3 environment identity is `aa42dc88f980845c94fab1d6ff992657f935f25c13ac418c16aa25f3baa5d305` and the current M0.5 evidence identity is `33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2`. The earlier `b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e` M0.5 digest remains historical evidence for the prior 1.24.2 environment.

## 14. Sequencing status

The adoption-time sequencing that established this boundary is complete. Section 13.1 records the qualified C++11/C++26 implementation; it is no longer a future prerequisite.

Current M1 work therefore proceeds through the owner-extraction/publication plan in architectures 080 and 093 rather than repeating the language-boundary slice. At implementation baseline `e29739ec2f34fb21e43f664385f57ab5eca18e53`:

```text
shared C++11/C++26 boundary:        qualified
strategic canonical-applied:        31/58
strategic fail-closed pending:       27/58
tactical server-forwarded:           13/15
tactical fail-closed pending:         2/15
CreateProduction:                    qualified
persisted EmployeeId publication:    qualified
Employee/Team six-owner batch:       qualified
```

No completed M1 spatial, identity, tactical-publication, strategic-publication or owner-extraction work is invalidated by later runtime expansion.

## 15. Future legacy modernization

C++11 on retained canonical code is a migration state, not a forever requirement.

Later migration may move canonical targets to a newer language standard when useful, but that is independent of the C++26 remaster runtime architecture and must retain canonical-preservation evidence.

The modern runtime must not be held back waiting for that migration.
