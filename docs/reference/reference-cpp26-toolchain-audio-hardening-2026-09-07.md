# Reference — C++26 / Vulkan / Slang / OpenAL Hardening Decision Evidence

**Captured:** 2026-09-07  
**Repository head:** `5b45c193aff9a9ff170d1aaacabaa5a786702c3d`  
**Purpose:** Record the concrete build/runtime/version evidence that led to Architecture 092 and the updated audio/toolchain policy. This is evidence, not an ABI authority.

## Repository validation

User-executed Fedora 44 validation reported:

```text
canonical test discovery:
    108 enabled exposed
    104 core
    4 deferred asset sweeps
    1 compile-time excluded

canonical regression pass 1:
    104/104 PASS

canonical regression pass 2:
    104/104 PASS

canonical two-run trace repeatability:
    PASS

canonical evidence:
    b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e
```

Legacy production build completed successfully.

Remaster dependency discovery/configuration reported:

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

The remaster Ninja tree was already current and therefore reported:

```text
ninja: no work to do.
```

This was not treated as a forced clean rebuild.

## GCC 16 atomic `shared_ptr` finding

The tactical publication compiled successfully but GCC 16.2.1 emitted:

```text
std::atomic_load_explicit(const shared_ptr<_Tp>*, ...)
is deprecated: use 'std::atomic<std::shared_ptr<T>>' instead

std::atomic_store_explicit(shared_ptr<_Tp>*, ...)
is deprecated: use 'std::atomic<std::shared_ptr<T>>' instead
```

This matches the existing M1 tactical qualification note that deferred the cleanup until presentation-runtime concurrency/standard-library policy changed.

Architecture 092 makes the C++26 transition that policy change.

## C++ decision

Accepted direction:

```text
retained canonical/legacy code:
    C++11 initially

shared canonical/remaster bridge:
    C++11-compatible

new remaster runtime:
    C++26

initial reference compiler:
    GCC 16.2.x
```

The project will use target-scoped standards rather than a global `-std=c++0x` flag.

The C++26-aware CMake floor is at least 3.25.

## Vulkan hardening

Current Khronos Vulkan registry at capture:

```text
1.4.362
```

Local remaster discovery:

```text
1.4.341
```

Accepted contract:

```text
Vulkan core >= 1.4
current accepted 1.4.x headers/registry/validation tooling for development
explicit runtime capability tests for required extensions/features
no patch-level Vulkan 1.4.x runtime minimum
```

The patch/revision values are tooling/evidence revisions, not separate architectural API generations.

## Slang hardening

Official latest stable release at capture:

```text
v2026.17
published 2026-09-04
```

The repository already provisions and hash-verifies v2026.17.

Accepted contract:

```text
exact Slang v2026.17 project-local pin
no unrecorded floating compiler update
future update requires reprovisioning + shader/descriptor-heap qualification
```

## OpenAL Soft / EFX / HRTF hardening

Current local package/discovery:

```text
OpenAL Soft 1.24.2
```

Official latest stable upstream release at capture:

```text
OpenAL Soft 1.25.2
released 2026-05-12
```

Accepted production-audio baseline:

```text
OpenAL core API: 1.1
OpenAL Soft implementation: >= 1.25.2
required: ALC_EXT_EFX
required: ALC_SOFT_HRTF
required reference capacity: >= 2 auxiliary sends/source
optional SOFT extensions: runtime capability-probed
```

The local 1.24.2 capture remains valid evidence but does not satisfy the new implementation-version baseline for eventual M8 production qualification.

OpenAL Soft 1.25.2 is relevant to the project because it includes current SDL3/backend/device work and EFX processing improvements, but Architecture 035/037 remain the semantic authority for device ownership, EFX sends, HRTF and acoustic behavior.

## Sequencing consequence

No M1 design work is redone.

The documentation-hardening change comes first.

Next implementation slice:

```text
build: establish C++11/C++26 language boundary
```

That slice must be qualified with a clean mixed-standard build before typed intents and M2 runtime work expand.
