# M0.6 presentation feature-selection / compatibility scaffold

**Status:** M0.6 implementation mechanism  
**Baseline:** landed M0.5 revision `9616ae01839a93e3938121841c1484c0f4be25b8`

## Purpose

M0.6 establishes the migration selector and rollback contract required before any production presentation implementation is replaced. It does **not** add Vulkan rendering, SDL3 production bootstrap, OpenAL production audio, retained-UI replacement, new VFX, or FFmpeg cinematic replacement.

The M0.6 rule is deliberately fail-closed:

```text
legacy remains the only selectable production implementation
remaster dependency discovery may be enabled independently
an unimplemented REMASTER selector is a configure-time error
no src/ gameplay or presentation implementation file is changed by M0.6
```

This preserves the architecture-080/091 requirement that the new seam/selection mechanism exists before a later milestone proves and selects a replacement, while avoiding a false "remaster" route that still silently executes legacy code.

## Selectors

The configure-time cache selectors are:

```text
UFOAI_PRESENTATION_PLATFORM
UFOAI_PRESENTATION_RENDERER
UFOAI_PRESENTATION_UI
UFOAI_PRESENTATION_AUDIO
UFOAI_PRESENTATION_VFX
UFOAI_PRESENTATION_CINEMATICS
```

Each selector accepts exactly:

```text
LEGACY
REMASTER
```

All six default to `LEGACY`. In M0.6, every `REMASTER` value is intentionally rejected because no owning production replacement has reached its implementation/parity gate yet.

`UFOAI_REMASTER` remains the M0 remaster bootstrap/dependency-discovery switch. It is **not** itself a production presentation selector. Therefore `UFOAI_REMASTER=ON` with all six selectors at their defaults still builds/runs legacy production presentation behavior.

## Generated contract

Configuration generates:

```text
<binary-dir>/generated/ufoai/remaster/presentation_selection.h
<binary-dir>/remaster/presentation-selection.txt
```

CMake also exposes the interface target:

```text
ufoai_remaster_presentation_selection
```

Future replacement targets can consume that interface after their owning milestone wires a real implementation. M0.6 intentionally does not link it into the legacy client, so no production source path changes merely because the scaffold exists.

For inspection, the non-default build target:

```text
remaster-presentation-selection
```

prints the generated selection manifest.

## Fail-closed behavior

M0.6 rejects:

1. unknown selector values;
2. `REMASTER` selection while `UFOAI_REMASTER=OFF`;
3. `REMASTER` selection while the requested subsystem remains unimplemented, even when `UFOAI_REMASTER=ON`.

A later subsystem milestone must explicitly replace the third guard only when a real backend exists and has applicable G0-G6 evidence. Default-switch and legacy deletion remain later, separate changes.

## Verification

Run:

```bash
python3 tools/remaster/verify-m0-feature-selection.py --capture
python3 tools/remaster/verify-m0-feature-selection.py --verify
```

The verifier creates disposable standalone CMake probes under `build-m0-feature-selection-check/`, validates both bootstrap-off and bootstrap-on defaults, exercises invalid/unimplemented fail-closed paths, verifies M0.6 has no `src/` delta from the landed M0.5 revision, and then executes the committed M0.5 canonical regression verifier.

Successful capture writes:

```text
docs/reference/reference-m0-feature-selection.txt
docs/reference/reference-m0-feature-selection.b3
```

The M0.5 canonical regression evidence identity must remain:

```text
b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e
```

M0.6 is not complete if the selector probes pass but M0.5 canonical verification changes or fails.

## Rollback

Rollback is the existing legacy behavior: all selectors remain `LEGACY`. Removing the M0.6 scaffold also restores the pre-M0.6 build configuration because no production implementation is replaced in this milestone.
