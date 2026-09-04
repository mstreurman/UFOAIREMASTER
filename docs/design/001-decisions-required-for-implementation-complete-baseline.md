# Implementation-Complete Decision Register

**Status:** Resolved — all Baseline 030 project decision gates accepted 2026-09-04  
**Decision baseline:** 031

## 1. Resolution rule

The project accepted all recommendations recorded by Baseline 030. This file is retained as the historical decision register; it is no longer an open-work list.

The normative consequences are owned by ADR-033 through ADR-040 and architecture 081 through 086. Earlier documents that still describe one of these subjects as open are superseded by those later authorities.

## 2. Resolved decisions

| ID | Accepted decision | Normative authority |
|---|---|---|
| `PLATFORM-001` | SDL3 owns Fedora window creation, Wayland-facing input/gamepad/text/IME normalization and Vulkan surface creation; Vulkan owns swapchain/HDR/frame lifetime | ADR-033, architecture 081 |
| `DEPS-JOLT-001` | Jolt v5.6.0 at commit `e77f175595e64cb44218cc9d9d56fc365ad0e36a`, vendored source, static project build, compute backends disabled | ADR-034, architecture 082, third-party manifest |
| `DEPS-SLANG-001` | official prebuilt Slang v2026.17 Linux x86-64 glibc-2.27 tool artifact, SHA-256 pinned; source-build fallback only | ADR-047 (supersedes compiler identity in ADR-041/ADR-034), architecture 029, third-party manifest |
| `VIDEO-001` | FFmpeg/libavformat/libavcodec primary cinematic decoder with compatibility tests for shipped RoQ/OGM behavior | ADR-035, architecture 079/083 |
| `RENDER-EDGE-001` | weighted-blended OIT; specialized forward glass/water; RT reflections only where eligible; no recursive transmissive RT v1; shared alpha-test and robust ray offset | ADR-036, architecture 084 |
| `JOLT-POLICY-001` | v1 ragdolls are full-body, post-death and presentation-only; no active/partial ragdoll baseline | ADR-037, architecture 082 |
| `ANIM-001` | maximum 256 joints/skeleton; `uint16_t` joint IDs; asset compiler rejects larger skeletons; max influences remains 8 | ADR-038, architecture 007/085 |
| `ABI-REF-001` | deterministic, inspectable reference-v1 binary layouts first; compact/quantized successors only after evidence | ADR-039, architecture 085 |
| `CRASH-001` | local diagnostics only: systemd-coredump/local cores, ELF build IDs, split debuginfo, trace/replay/probe bundles; no automatic upload/telemetry | ADR-040, architecture 086 |

## 3. Jolt qualification caveat

Jolt v5.6.0 is the accepted development pin, but production qualification requires the long-running debris/ragdoll sleep/wake finite-transform stress test defined by architecture 082. Upstream issue #2092 (`https://github.com/jrouwe/JoltPhysics/issues/2092`) reported non-finite transforms near sleep transitions on this v5.6.0 commit; it was closed before the Baseline 031 decision date, so it is retained only as a qualification signal, not as an unresolved upstream status claim. If the reference test reproduces a Jolt-side failure, v5.5.0 at `23dadd0e603f1b321142d4c74df07fce85064989` is the pre-authorized fallback candidate; changing the production pin must still be recorded in the dependency manifest and release audit.

## 4. Baseline 029/030 decision closure

All explicit Baseline 030 decision gates are resolved. This statement is scoped to that audit generation. The deeper Baseline 032 audit subsequently found additional presentation-fidelity/persistence choices; those are tracked in `002-baseline-031-deep-audit-decision-gates.md` without reopening the nine decisions recorded here.
