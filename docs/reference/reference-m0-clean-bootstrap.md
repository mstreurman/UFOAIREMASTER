# M0.8 clean-checkout reproducibility qualification

This fixture proves the Architecture-091 G7 clean-bootstrap gate for the sealed M0 baseline.

## Baseline under test

```text
revision: e611ca139e38dc246535f9536b8f6c2eda77a5f3
repository: https://github.com/mstreurman/UFOAIREMASTER.git
```

The proof clones the public repository over HTTPS into an ignored disposable workspace. For that clone subprocess it disables global/system Git configuration, terminal prompting, and alternate-object variables. It does not use a Git worktree, local clone source, alternate object directory, or the development checkout's `tools/slang/` cache.

## Dependency and tool reconstruction

Slang is intentionally not committed as a binary dependency. `tools/remaster/provision-m0-slang.py` reads the authoritative Slang version/artifact/SHA-256 from `tools/remaster/m0-pins.json`, cross-checks those pins against the committed M0 environment manifest, downloads the pinned upstream release artifact, verifies the archive SHA-256 before extraction, then verifies the accepted `slangc` and `libslang.so` SHA-256 identities after extraction.

For this baseline the authoritative pin is:

```text
Slang:    v2026.17
artifact: slang-2026.17-linux-x86_64-glibc-2.28.tar.gz
SHA-256:  a5a48530e7218d79e10b633c216ef04cbe778450b8c0a7579125e630c088ca75
```

The project-local cache remains under ignored `tools/slang/v2026.17/`. No system Slang package is substituted.

Jolt remains the committed immutable source snapshot under `third_party/JoltPhysics/`; the M0.3 manifest verifier recomputes its accepted sorted-file-manifest BLAKE3 identity.

## G7 proof sequence

`tools/remaster/run-m0-clean-bootstrap.py` performs the following against a new public checkout:

1. clone the public GitHub repository and detach exactly at the sealed M0 revision;
2. require an initially clean tracked/untracked checkout and confirm no Slang binary cache came from source control;
3. verify committed M0.3/M0.4/M0.5/M0.6 and R2-R5 evidence/sidecar identities;
4. create a fresh proof-local `CCACHE_DIR`, freshly download and provision the pinned Slang artifact, then prove the Slang cache is covered by the committed ignore policy;
5. run the M0.3 environment/vendor/tool manifest verifier;
6. perform the real M0.4 clean legacy configure/build and Wayland/X11-native launch smoke;
7. save the fresh smoke evidence outside the checkout, restore the committed M0.4 reference pair, and require a clean tracked state again;
8. run the M0.6 verifier, which also reruns the full M0.5 canonical regression corpus;
9. run the R3 Slang descriptor-heap verification using the freshly provisioned compiler/API distribution;
10. remove generated build/tool-cache state and require the clean checkout to return to an empty Git status.

R2, R4 and R5 are target-machine conformance/stress qualifications already sealed with committed evidence. M0.8 validates those committed evidence identities rather than repeating the hardware descriptor-heap/RT and 600-second Jolt stress campaigns. R3 is rerun because its project-local Slang binary cache is the dependency that must be reconstructed from a fresh checkout.

## Capture and verification

```text
python3 tools/remaster/run-m0-clean-bootstrap.py --capture
python3 tools/remaster/run-m0-clean-bootstrap.py --verify
```

Both modes perform a fresh public clone and the full G7 sequence. Capture writes:

```text
docs/reference/reference-m0-clean-bootstrap.txt
docs/reference/reference-m0-clean-bootstrap.b3
```

Verification reruns the proof and byte-compares normalized evidence. Raw clone/provision/build/test/smoke logs remain in the ignored `build-m0-clean-bootstrap-f44/logs/` workspace.

## Authority and production behavior

This fixture changes no canonical or presentation runtime behavior. It is bootstrap/qualification tooling only. No production install step exists.
