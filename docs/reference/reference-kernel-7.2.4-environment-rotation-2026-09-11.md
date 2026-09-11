# Reference — Fedora 44 Kernel 7.2.4 Environment Rotation

**Date:** 2026-09-11
**Status:** PASS / resealed
**Scope:** reference-workstation kernel/evidence rotation only; no canonical gameplay rule change

## Trigger

The Fedora 44 reference workstation booted a newer kernel while every other M0.3
captured identity remained unchanged:

```text
platform.kernel_release=7.1.12-200.fc44.x86_64
    ->
platform.kernel_release=7.2.4-200.fc44.x86_64
```

M0.3 intentionally treats the running kernel as part of the exact reference
workstation identity. The old manifest therefore failed closed as designed.

## M0.3 environment recapture

The v5 transaction generated M0.3 in a short-lived Git-ignored, repository-contained
scratch path before touching tracked source state and required the generated manifest
to differ from the committed baseline in exactly the `platform.kernel_release` line
above. It then reproduced the same capture inside the disposable qualification worktree.

```text
previous M0.3: 7adfa0c1e62c6ea2347b866fd36873e233b6c2f2bdc71f3336f0796fd9f3c57d
current  M0.3: ea6cb9ded6289b809ab22ae8fe2fb19e3ed8fb0ff8e71ec180f3c9a2710f6c35
```

`capture-m0-manifest.py --verify` passed against the rotated identity.

## M0.5 active canonical-regression reseal

Because active M0.5 evidence records the M0.3 manifest identity, the canonical
regression evidence was regenerated on the otherwise-unmodified baseline before
the UFO-recovery source transformation. The transaction required the M0.5 evidence
payload to differ from the previous committed evidence in exactly the
`environment.m0_manifest_blake3_256` line.

```text
previous M0.5: b3349db1064514536cff0ffd5cb6837cefca12b8435bc41c27220f5650da845f
current  M0.5: 8add4c8c8319111766d2ba9939e6fdcab8e08bd272fbadb068d198567bcaa218
```

After the M1 UFO-recovery owner extraction was applied in the disposable worktree,
`run-m0-canonical-regression.py --verify` had to reproduce this resealed evidence
byte-for-byte and the full canonical two-run corpus had to pass before copy-back.

## Historical evidence boundary

Historical M0.4/M0.8 evidence remains untouched. Those records describe the exact
environment under which their historical qualifications were captured; rewriting
them to the current kernel would make that provenance false.

## Gameplay compatibility conclusion

This rotation changes reference-workstation provenance only. It does not change
canonical campaign or tactical authority, save schema, or network protocol. The
UFO-recovery batch remains required to preserve save v4 and protocol 18 and to pass
both legacy and remaster production builds before this record can reach the real
checkout.
