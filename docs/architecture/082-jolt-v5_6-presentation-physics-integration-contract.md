# Jolt v5.6 Presentation-Physics Integration Contract

**Status:** Implementation specification baseline  
**Authority:** ADR-007, ADR-023, ADR-034, ADR-037

## 1. Exact dependency

```text
Jolt Physics v5.6.0
commit e77f175595e64cb44218cc9d9d56fc365ad0e36a
source integration: vendored immutable snapshot
linkage: static
canonical authority: none
```

The vendored snapshot records the upstream commit in a machine-readable vendor manifest. No git submodule is used.

### Reference-workstation provisioning evidence

As of the Baseline-041 2026-09-04 provisioning run, the accepted snapshot is present at `third_party/JoltPhysics/` with sorted-file-manifest BLAKE3-256:

```text
ffe175b315e20631eea26419b65ef225b73e37e3788dd93b66407fb3f37a9df2
```

The standalone reference build produces `build-jolt-f44/libJolt.a`; upstream HelloWorld and UnitTests pass. These facts close acquisition/build readiness only. Section 7 remains the production-qualification authority.

## 2. Reference CMake options

For the i9-9900K target:

```text
JPH_BUILD_SHARED_LIBS=OFF
OVERRIDE_CXX_FLAGS=OFF
INTERPROCEDURAL_OPTIMIZATION=OFF
ENABLE_ALL_WARNINGS=OFF
ENABLE_INSTALL=OFF
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
DEBUG_RENDERER_IN_DISTRIBUTION=OFF
PROFILER_IN_DISTRIBUTION=OFF
```

Project build modes decide assertions/debug renderer/profiler for development builds. Jolt must not override the remaster's global CPU-target, warning or interprocedural-optimization policy. Project targets may enable IPO/LTO deliberately at the parent build level after compatibility validation; the vendor sub-build does not enable it independently.

## 3. Object layers

Presentation layers are fixed for v1:

```text
0 StaticPresentationWorld
1 DynamicDebris
2 Ragdoll
3 PresentationTrigger
```

Collision matrix:

```text
StaticPresentationWorld <-> DynamicDebris, Ragdoll
DynamicDebris          <-> StaticPresentationWorld, DynamicDebris, Ragdoll
Ragdoll                <-> StaticPresentationWorld, DynamicDebris, Ragdoll
PresentationTrigger    -> query/sensor only; never canonical gameplay trigger authority
```

Canonical BSP/routing remains the source of gameplay collision. Static Jolt shapes are presentation mirrors produced by the asset/map pipeline.

## 4. Bodies

Baseline body classes:

```text
static mirrored world geometry: static bodies
visual debris: dynamic rigid bodies
post-death ragdoll parts: dynamic rigid bodies + constraints
living actors: no Jolt body controlling canonical transform
```

Jolt transforms may be rendered but may never be written back into canonical actor/entity/routing state.

## 5. Ragdoll handoff

On authoritative death presentation event:

```text
1 capture latest presentation skeleton world pose
2 instantiate full-body ragdoll from authored collision/constraint data
3 initialize body transforms and presentation-derived velocities
4 optionally blend rendered pose toward Jolt pose over authored presentation duration
5 simulate until sleep/lifetime/degradation policy retires it
```

No active/partial ragdoll path is required in v1.

## 6. Sleep/lifetime policy

Default:

```text
allow Jolt sleeping
sleeping ragdolls/debris remain visible until presentation lifetime/degradation removes them
never wake bodies solely for canonical simulation
explicit VFX impulses may wake presentation bodies
```

The exact aesthetic lifetime is content/quality tuning. Capacity/priority follows architecture 041.

## 7. Required production qualification for 5.6.0

Before v5.6.0 is production-qualified on the reference workstation, run a repeatable stress replay with:

```text
>= 256 dynamic presentation bodies
stacking/contact-heavy arrangements
ragdoll constraints
repeated sleep/wake cycles
>= 10 minutes continuous simulation
finite position/orientation/linear/angular velocity assertion every simulation tick
ASAN/UBSAN development pass where practical
```

Fail if any body produces NaN/Inf, disappears because of non-finite transform, corrupts ownership, or affects canonical hashes.

Upstream issue #2092 (`https://github.com/jrouwe/JoltPhysics/issues/2092`) reported non-finite transforms near sleep transitions in Jolt 5.6.0 and was later closed. We retain it as a qualification signal, not as proof of an unresolved upstream defect. This is a presentation-physics qualification risk, not a canonical-gameplay risk because Jolt is non-authoritative.

If reproduced in our harness, v5.5.0 at `23dadd0e603f1b321142d4c74df07fce85064989` is the authorized fallback candidate and must be requalified and recorded before release.

## 8. Debug rendering

Jolt debug geometry is converted to project debug-line/triangle primitives and rendered by the Vulkan debug pass. Jolt does not call OpenGL or own a graphics backend.
