# M0.7 R5 Jolt v5.6.0 presentation-physics stress qualification

This reference fixture qualifies the vendored Jolt Physics v5.6.0 snapshot for presentation-only use on the reference workstation.

## Contract

The fixture requires:

- exact sealed R4 baseline `d9702cc772c136124d98e7cbe384c9c6225b9c2b`;
- accepted R4 evidence `a8aa4a83dc5c3e444159bff55b94c76ea18d4c7907043a53cf3101ce7a53c07a`;
- Jolt v5.6.0 at commit `e77f175595e64cb44218cc9d9d56fc365ad0e36a`;
- accepted vendored-source manifest BLAKE3 `ffe175b315e20631eea26419b65ef225b73e37e3788dd93b66407fb3f37a9df2` with no local patches;
- static Jolt linkage with the Architecture-082 reference option set;
- exactly 256 dynamic presentation bodies, including dense contact stacks and constrained ragdoll-like chains;
- 36,000 ticks at 60 Hz, representing 600 seconds of continuous simulation;
- repeated explicit sleep/wake/impulse phases and non-zero activation/deactivation listener evidence;
- finite position, orientation, linear velocity and angular velocity checks for every dynamic body after every simulation tick;
- no physics update error, Jolt assertion, ownership loss, NaN or Inf;
- a canonical-state sentinel unchanged from start to finish.

Jolt has no canonical authority in this fixture and no production behavior is replaced.

## Sanitizer qualification

Architecture 082 requires an ASAN/UBSAN development pass where practical. R5 revision 003 performs a stronger full-workload pass: both vendored Jolt and the fixture are compiled with combined AddressSanitizer and UndefinedBehaviorSanitizer instrumentation and run for the same 36,000 ticks. Sanitizer recovery is disabled.

The qualification build explicitly forces both `PROFILER_IN_DEBUG_AND_RELEASE=OFF` and `PROFILER_IN_DISTRIBUTION=OFF`. Jolt v5.6.0 defaults the former to ON, which otherwise defines `JPH_PROFILE_ENABLED` for Release. Revision 002's UBSan run reported a null-pointer load while entering that optional profiler TLS path. Jolt's `ProfileMeasurement` code is intended to tolerate an uninstrumented thread, so this fixture does not classify that report as a physics defect; instead it removes the unintentionally enabled profiler from the qualification configuration. Profiling is outside this stress contract and must not be enabled implicitly by a vendor default. The runner verifies these cache values after every configure.

Before a sanitizer build, the runner also requires the selected C++ compiler to resolve real `libasan.so` and `libubsan.so` files. Missing host sanitizer runtimes are therefore reported as an environment failure before compilation.

Run sanitizer qualification first:

```text
python3 tools/remaster/run-m0-jolt-stress-fixture.py --sanitize-capture
python3 tools/remaster/run-m0-jolt-stress-fixture.py --sanitize-verify
```

This produces:

```text
docs/reference/reference-m0-jolt-stress-sanitizer.txt
docs/reference/reference-m0-jolt-stress-sanitizer.b3
```

The normal R5 capture refuses to run until current sanitizer evidence is present and matches the current fixture/toolchain inputs.

## Primary qualification

After sanitizer capture and immediate verification:

```text
python3 tools/remaster/run-m0-jolt-stress-fixture.py --capture
python3 tools/remaster/run-m0-jolt-stress-fixture.py --verify
```

The primary normalized evidence records `sanitizer.status=PASS` and the accepted sanitizer evidence identity. Scheduler-sensitive raw contact and activation counts remain visible in the run log but are deliberately excluded from normalized evidence.

No production install step exists for this fixture.
