# Reference — OpenAL Soft 1.25.2 Reference-Environment Rotation

**Date:** 2026-09-07  
**Status:** PASS / resealed  
**Scope:** reference workstation environment/evidence rotation only; no canonical gameplay rule change

## Change

The Fedora 44 reference workstation OpenAL Soft implementation was upgraded:

```text
OpenAL Soft 1.24.2
    ->
OpenAL Soft 1.25.2
```

The stable OpenAL core contract remains OpenAL 1.1. The remaster production-audio architecture continues to require OpenAL Soft >=1.25.2 plus the separately documented EFX/HRTF capability contract.

## M0.3 environment recapture

The deterministic environment manifest changed only in the observed OpenAL package/discovery version:

```text
pkg_config.openal.version=1.24.2
    ->
pkg_config.openal.version=1.25.2
```

Previous environment identity:

```text
4b319f96f5674b3d39108fdd327b2e04143b1f4eaeaa88469eac364071f756b5
```

Accepted current environment identity:

```text
aa42dc88f980845c94fab1d6ff992657f935f25c13ac418c16aa25f3baa5d305
```

`capture-m0-manifest.py --verify` passed against the new identity.

## M0.5 active precondition rotation

The active M0.5 canonical-regression harness was updated to accept the new M0.3 reference-environment identity.

Historical M0.4 smoke evidence remains unchanged because it truthfully records the older environment under which that historical smoke run was performed.

## Canonical regression reseal

The post-upgrade canonical corpus executes:

```text
104/104 PASS
104/104 PASS
two-run trace repeatability: PASS
```

Current M0.5 evidence identity:

```text
33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2
```

Current canonical-regression harness SHA-256 recorded by the evidence:

```text
356bc0e44f7d3b69346a09b65e45b62176bc10a561dc49e4fca4f92f8fc2dd96
```

The earlier M0.5 evidence identity:

```text
b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e
```

remains historical evidence for the pre-OpenAL-1.25.2 reference environment. A changed M0.5 BLAKE3 after this rotation is expected because the evidence payload records both the environment identity and the harness-script SHA; it is not by itself canonical gameplay drift.

## Preservation conclusion

The accepted environment changed; the canonical test corpus and two-run execution trace did not.

No OpenAL version is part of canonical simulation authority.

## Historical M0.8 clean-bootstrap exception

`tools/remaster/run-m0-clean-bootstrap.py` intentionally retains the older M0.3 and M0.5 evidence identities.

That harness checks out the sealed M0.8 baseline:

```text
e611ca139e38dc246535f9536b8f6c2eda77a5f3
```

and verifies the evidence committed in that historical checkout. Its expected sidecars therefore correctly remain:

```text
M0.3 environment: 4b319f96f5674b3d39108fdd327b2e04143b1f4eaeaa88469eac364071f756b5
M0.5 canonical:   b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e
```

Those values are not active current-workstation policy. Updating them to the 2026-09-07 OpenAL Soft 1.25.2 identities would make the M0.8 historical reproducibility proof internally inconsistent.

The current active identities remain:

```text
M0.3 environment: aa42dc88f980845c94fab1d6ff992657f935f25c13ac418c16aa25f3baa5d305
M0.5 canonical:   33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2
```

