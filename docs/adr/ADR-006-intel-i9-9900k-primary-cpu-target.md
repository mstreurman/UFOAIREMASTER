# ADR-006 — Intel Core i9-9900K as Primary CPU Optimization Target

**Status:** Accepted  
**Decision type:** CPU architecture / performance optimization

## Context

The primary development system uses an Intel Core i9-9900K (Coffee Lake Refresh) with:

- 8 physical cores;
- 16 hardware threads;
- 16 MiB shared L3 cache;
- 2 MiB total L2 cache;
- 256 KiB total L1 data cache;
- x86_64 execution;
- AVX2;
- AVX;
- FMA;
- F16C;
- SSE, SSE2, SSE3, SSSE3, SSE4.1, and SSE4.2;
- BMI1 and BMI2;
- POPCNT;
- AES-NI;
- PCLMULQDQ;
- ADX;
- RDRAND and RDSEED;
- CLFLUSHOPT;
- additional Coffee Lake-class x86-64 facilities reported by CPUID.

The project intends to optimize the remaster specifically for this processor rather than restricting the implementation to a lowest-common-denominator x86-64 baseline.

The fresh 2026-09-04 10:41:03+02:00 workstation snapshot directly revalidated the processor identity, 8C/16T topology, cache totals, 5.0 GHz reported maximum frequency, and the listed AVX2/FMA/BMI/AES/PCLMUL/ADX-class facilities. It did not report AVX-512. See `reference/reference-current-development-machine-2026-09-04-104103.md`; the earlier `reference-local-development-state-2026-09-04.md` remains a historical snapshot.

## Decision

The Intel Core i9-9900K is the primary CPU architecture target for the remaster.

The project may use CPU-specific compilation, intrinsics, SIMD, instruction-specific algorithms, cache-aware data layouts, manual vectorization, and other Coffee Lake / i9-9900K-specific optimizations where profiling shows a material benefit.

The primary optimized build may use:

```text
-march=native
-mtune=native
```

when built on the reference i9-9900K system.

Architecture-specific implementations are allowed when they improve measurable performance or latency on the target CPU.

## Optimization policy

The project policy is:

> All useful i9-9900K instructions are available to the implementation, but architecture-specific code is justified by measurement rather than novelty.

The compiler-generated implementation remains a valid baseline.

Hand-written intrinsics or specialized kernels should be compared against current compiler output before being adopted.

## Preferred optimization areas

Architecture-specific optimization is especially appropriate for presentation-side workloads such as:

- animation pose processing;
- skeletal transforms;
- matrix/vector batches;
- presentation-scene transforms;
- visibility preparation;
- instance preparation;
- acceleration-structure preparation;
- particle updates;
- presentation physics support code;
- audio DSP and spatial-audio calculations;
- texture/image conversion;
- decompression and bulk data transforms;
- CPU-side denoiser/reconstruction preparation;
- cache-sensitive iteration over large presentation data sets.

## SIMD policy

AVX2 and FMA are first-class optimization tools for the target CPU.

Where useful, implementations may also exploit:

- SSE4.1 / SSE4.2;
- SSSE3;
- F16C;
- BMI1 / BMI2;
- POPCNT;
- ADX;
- AES-NI / PCLMULQDQ for suitable non-cryptographic or cryptographic workloads;
- CLFLUSHOPT and cache-management facilities where a measured use case exists.

The existence of an instruction is not by itself sufficient reason to use it.

## Canonical gameplay constraint

CPU optimization must not violate ADR-001.

Canonical gameplay must preserve its authoritative behavior and outcomes.

Optimization of canonical systems is allowed only when it preserves canonical behavior.

In particular, floating-point transformations that can alter gameplay results require special care.

## Floating-point policy

`-ffast-math` must not be enabled globally.

Aggressive floating-point transformations may be used in presentation-only subsystems when they are shown to be beneficial and their numerical behavior is acceptable.

Canonical gameplay code must not silently adopt:

- unsafe reassociation;
- approximation modes;
- altered NaN/Inf semantics;
- reciprocal approximations;
- other floating-point transformations that can change authoritative outcomes.

FMA or vectorized implementations in canonical code require behavior-preservation validation.

## Threading and topology

ADR-023 now defines the concrete i9-9900K scheduler baseline.

The target machine provides:

```text
8 physical cores
16 hardware threads
```

The scheduler uses physical cores first:

```text
1 Main physical core
1 Render physical core
6 Primary worker physical cores
5 scheduler SMT helper threads on worker-core siblings
1 AudioControl thread on the remaining worker-core SMT sibling
```

The SMT siblings of the Main/Render cores are left unused by the engine in the baseline.

ADR-023 and ADR-024 are the current topology/ownership authority. Linux logical-CPU relationships are discovered from actual topology rather than assumed from CPU numbering.

Frame-critical AVX2/Jolt work is `PrimaryOnly`; the five scheduler SMT helpers are reserved mainly for suitable presentation/background throughput, while the sixth worker-core sibling is reserved for `AudioControl`.

Canonical simulation ordering and determinism requirements take precedence over parallelization.

## Cache-aware optimization

The i9-9900K cache hierarchy is an explicit optimization consideration.

Data-oriented layouts, batching, working-set sizing, and task partitioning should be evaluated against:

- private per-core L1 data cache;
- private per-core L2 cache;
- shared 16 MiB L3 cache.

Cache locality is considered part of CPU architecture design rather than a late-stage optimization concern.


## Optimization target is not a runtime-configuration lock

The i9-9900K is the CPU on which production fast paths, worker topology, SIMD choices and frame-tail behavior are optimized and accepted. This does not imply that user-facing display/audio settings are fixed to the reference workstation.

The target-specific implementation may remain aggressively AVX2/FMA/cache/topology tuned while display resolution, refresh rate, HDR state, display selection, audio device and HRTF remain runtime-selectable presentation settings. ADR-046 owns that separation.

## Portability

A future portable CPU path may be provided.

Such a path must not prevent the primary i9-9900K build from using CPU-specific optimizations.

Where practical, architecture-specific kernels should be isolated behind narrow interfaces so that fallback implementations can coexist without contaminating higher-level architecture.

## Consequences

### Positive

- permits aggressive optimization for a known target;
- makes AVX2/FMA and Coffee Lake-specific performance work first-class;
- aligns CPU architecture decisions with the B580-specific GPU strategy;
- encourages measurable cache- and topology-aware design;
- allows the project to pursue stable 1080p60 frame times rather than generic portability first.

### Negative

- some optimized paths may not run on older CPUs;
- architecture-specific code increases testing burden;
- hand-written SIMD can reduce maintainability;
- compiler upgrades may outperform older handwritten kernels;
- future cross-platform work may require fallback implementations.

## Required validation

Before accepting a hand-optimized CPU kernel:

1. profile the existing implementation;
2. establish a representative benchmark;
3. compare compiler-generated and specialized implementations;
4. verify correctness;
5. verify canonical gameplay preservation when relevant;
6. record the performance result if the specialized path is retained.
