# Current Jolt Provisioning State — 2026-09-04 12:15:47+02:00

**Status:** Current reference-workstation evidence  
**Scope:** Jolt v5.6.0 acquisition, immutable vendor identity, standalone build and upstream smoke/unit-test readiness  
**Canonical source revision:** `763173ed036ebbee32c2a7bf6aefa19748df89ff`

## Purpose

This record supersedes earlier *current-state* statements that Jolt was not yet provisioned. Those earlier timestamped captures remain historically correct for when they were taken.

It does **not** declare Jolt v5.6.0 production-qualified for the remaster. Architecture 082's project-specific >=256-body sleep/wake finite-transform stress gate remains required because upstream issue #2092 was reported against this exact v5.6.0 commit.

## Exact source identity

```text
upstream:    https://github.com/jrouwe/JoltPhysics.git
release:     v5.6.0
commit:      e77f175595e64cb44218cc9d9d56fc365ad0e36a
license:     MIT
vendor path: third_party/JoltPhysics/
method:      immutable git-archive snapshot; no submodule
patches:     none
```

The fetched tag resolved exactly to the accepted commit:

```text
requested: e77f175595e64cb44218cc9d9d56fc365ad0e36a
fetched:   e77f175595e64cb44218cc9d9d56fc365ad0e36a
result:    PASS
```

## Vendor-tree identity

The generated `third_party/JoltPhysics/UFOAI_VENDOR_MANIFEST.txt` records:

```text
upstream_url=https://github.com/jrouwe/JoltPhysics.git
release_tag=v5.6.0
commit_sha=e77f175595e64cb44218cc9d9d56fc365ad0e36a
license_identifier=MIT
sorted_file_manifest_blake3_256=ffe175b315e20631eea26419b65ef225b73e37e3788dd93b66407fb3f37a9df2
local_patch_list=none
```

The BLAKE3-256 value is the project-defined sorted-file-manifest hash from `reference-third-party-toolchain-manifest.md`; the manifest file itself is excluded from the hashed payload.

## Reference standalone build

Local build directory:

```text
build-jolt-f44/
```

Reference configuration verified in `CMakeCache.txt`:

```text
JPH_BUILD_SHARED_LIBS=OFF
OVERRIDE_CXX_FLAGS=OFF
INTERPROCEDURAL_OPTIMIZATION=OFF
DOUBLE_PRECISION=OFF
CROSS_PLATFORM_DETERMINISTIC=OFF
CPP_EXCEPTIONS_ENABLED=OFF
CPP_RTTI_ENABLED=OFF
OBJECT_LAYER_BITS=16
USE_SSE4_1=ON
USE_SSE4_2=ON
USE_AVX=ON
USE_AVX2=ON
USE_AVX512=OFF
USE_LZCNT=ON
USE_TZCNT=ON
USE_F16C=ON
USE_FMADD=ON
JPH_USE_DX12=OFF
JPH_USE_VK=OFF
JPH_USE_MTL=OFF
JPH_USE_CPU_COMPUTE=OFF
ENABLE_OBJECT_STREAM=OFF
```

The standalone readiness build also configured:

```text
CMAKE_BUILD_TYPE=Release
CMAKE_CXX_COMPILER=/usr/bin/g++
CMAKE_CXX_COMPILER_LAUNCHER=ccache
ENABLE_ALL_WARNINGS=OFF
ENABLE_INSTALL=OFF
DEBUG_RENDERER_IN_DEBUG_AND_RELEASE=OFF
DEBUG_RENDERER_IN_DISTRIBUTION=OFF
PROFILER_IN_DEBUG_AND_RELEASE=OFF
PROFILER_IN_DISTRIBUTION=OFF
TARGET_UNIT_TESTS=ON
TARGET_HELLO_WORLD=ON
TARGET_PERFORMANCE_TEST=OFF
TARGET_SAMPLES=OFF
TARGET_VIEWER=OFF
```

This is a dependency-readiness build, not yet the final remaster parent-build integration or final benchmark configuration.

## Build result

The exact targets were built successfully:

```text
Jolt
HelloWorld
UnitTests
```

Static library:

```text
build-jolt-f44/libJolt.a
result: PASS
```

## Upstream runtime smoke

Upstream `HelloWorld` ran successfully. The body fell, contacted the floor, settled at approximately `Y = 0.48`, and emitted `A body went to sleep` without a non-finite transform in that simple smoke scenario.

Result:

```text
PASS: Jolt HelloWorld
```

This simple case is useful acquisition/build evidence only. It is not sufficiently stressful to close issue-2092-related project qualification.

## Upstream unit tests

```text
Test #1: UnitTests ... Passed
100% tests passed
0 tests failed out of 1
Total Test time: 0.67 sec
```

Result:

```text
PASS: upstream Jolt unit tests
```

## Current repository observation

After provisioning:

```text
?? build-f44/
?? build-jolt-f44/
?? docs/
?? third_party/
?? tools/
```

Interpretation:

- `third_party/JoltPhysics/` is intended project source/vendor content and should become repository-owned when the remaster tree is committed;
- `build-jolt-f44/` is a local build directory and should not be committed;
- `tools/slang/` remains a project-local binary tool cache and should not be committed;
- exact ignore/ownership rules should be installed before the first remaster commit.

## Readiness classification

```text
Jolt v5.6.0 source acquisition:       READY
accepted commit verification:         READY
vendor manifest identity:             READY
reference i9-9900K CMake options:     READY
static libJolt.a build:               READY
upstream HelloWorld smoke:            PASS
upstream unit tests:                  PASS

UFO:AI PresentationWorld integration: NOT IMPLEMENTED
>=256-body sleep/wake stress harness:  NOT RUN
v5.6.0 production qualification:      PENDING
v5.5.0 fallback qualification:        NOT NEEDED unless v5.6 reproduces failure
```

## Remaining Jolt-specific work

1. integrate the vendored static Jolt target into the remaster parent build without granting it canonical gameplay authority;
2. implement the architecture-082 fixed-60-Hz presentation-physics bridge and project job-system adapter;
3. build the >=256-dynamic-body contact-heavy/ragdoll sleep/wake stress harness;
4. assert finite position, orientation, linear velocity and angular velocity every simulation tick for >=10 minutes;
5. run sanitizer variants where practical;
6. retain v5.6.0 only if the project harness remains finite and stable; use the authorized v5.5.0 fallback process only if the defect reproduces.
