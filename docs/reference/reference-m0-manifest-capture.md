# M0.3 Reference Environment Manifest Capture

**Status:** M0.3 implementation mechanism
**Scope:** Fedora 44 x86_64 reference workstation tool/RPM/vendor identity
**Manifest hash:** BLAKE3-256 over exact UTF-8 manifest bytes

## Purpose

M0.3 freezes the exact reference environment used to qualify the remaster bootstrap. The capture is designed to answer two different questions without conflating them:

```text
What dependency/tool/vendor identity has the project accepted?
What exact identity is installed/observed on the reference workstation?
```

The generated manifest intentionally excludes capture timestamp, hostname, username and checkout-absolute paths. For a fixed reference workstation state, rerunning the capture therefore produces byte-identical output and the same BLAKE3-256.

## Committed inputs

```text
tools/remaster/m0-pins.json
    machine-readable canonical source, Slang and Jolt accepted identities

tools/remaster/m0-reference-rpms.txt
    direct Fedora reference RPM scope

tools/remaster/capture-m0-manifest.py
    deterministic capture/verification implementation
```

Tool-owner RPMs are additionally derived from the exact executable files used for GCC/G++, linker, CMake, Ninja, ccache, Git, Python, pkg-config, SPIR-V Tools, b3sum and optional shader utilities.

## Generated reference outputs

```text
docs/reference/reference-m0-environment-manifest.txt
docs/reference/reference-m0-environment-manifest.b3
```

The manifest includes:

```text
Fedora release, architecture and running kernel
reference CPU identity and display-class PCI identities
exact direct reference RPM NEVRAs with normalized epoch
compiler/linker/build-tool versions and owning RPMs
normal PATH resolution for gcc/g++ and ccache-enabled preset identity
Vulkan / SDL3 / OpenAL / FFmpeg RPM identities
Mesa Vulkan/DRI driver RPM identities
pkg-config API versions used by the M0 dependency gate
accepted Slang release/artifact/hash/license identity
observed slangc and libslang.so SHA-256 identities
accepted Jolt release/commit/license/vendor BLAKE3 identity
independently recomputed Jolt sorted-file-manifest BLAKE3-256
SHA-256 identities of the capture inputs themselves
```

## Capture

From the repository root, after the accepted Slang cache and Jolt vendor snapshot are present:

```bash
python3 tools/remaster/capture-m0-manifest.py
```

A successful run ends with:

```text
M0.3 reference manifest capture: PASS
```

Review the generated manifest before committing it.

## Verify

After the generated manifest and sidecar have been committed, verify that the current reference environment still matches them with:

```bash
python3 tools/remaster/capture-m0-manifest.py --verify
```

A successful verification reports the committed BLAKE3-256. Any package, tool, kernel, Slang binary/library, Jolt vendor identity, pkg-config API version, capture-input or relevant hardware identity drift causes a non-zero exit and a readable diff or identity error.

## Identity rules

### RPM NEVRA

RPM identities are recorded as:

```text
name-epoch:version-release.arch
```

Missing RPM epoch is normalized to `0` so the identity is unambiguous.

### Slang

The manifest records both the accepted release-artifact pin and the observed extracted compiler identities. The accepted artifact remains a bootstrap/provisioning contract; the extracted `slangc` and `libslang.so` hashes prove what is actually being used locally.

### Jolt

The capture independently recomputes the documented project vendor-tree identity. For every non-manifest regular file in bytewise UTF-8 path order, the BLAKE3 stream is:

```text
path
NUL
unsigned decimal file length
NUL
exact file bytes
NUL
```

The result must equal the accepted `sorted_file_manifest_blake3_256` marker before capture succeeds.

## M0 relationship

M0.3 does not replace any production presentation path. It supplies reproducibility evidence for later M0 smoke/reference work and for the G7 clean-bootstrap gate. Benchmark, replay and qualification artifacts may reference the committed M0 manifest BLAKE3-256.

## Slang reference-artifact supersession

M0.3 freezes the Fedora 44 reference cache to the official upstream x86_64 glibc-2.28 v2026.17 archive:

```text
slang-2026.17-linux-x86_64-glibc-2.28.tar.gz
SHA-256 a5a48530e7218d79e10b633c216ef04cbe778450b8c0a7579125e630c088ca75
```

This supersedes the earlier accepted-manifest selection of the v2026.17 x86_64 glibc-2.27 archive. Historical readiness captures remain historical evidence and are not rewritten; the current accepted dependency identity is updated in `reference-third-party-toolchain-manifest.md` by the M0.3 patch.
