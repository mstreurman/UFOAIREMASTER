# M0.4 Clean Canonical Legacy Build + Launch Smoke

**Status:** M0.4 implementation mechanism
**Scope:** clean canonical legacy configure/build plus real client initialization smoke

## Purpose

M0.4 proves that the canonical UFO:AI legacy presentation path remains buildable and launchable after the remaster bootstrap work. It does not enable the remaster runtime, alter canonical behavior, or replace SDL2/OpenGL production presentation.

The harness is intentionally stronger than `ufo --help` or another early-exit command. The Linux client normally calls `Qcommon_Init()` and then enters the frame loop. The accepted positive launch marker is:

```text
====== UFO Initialized ======
```

That marker is emitted by the normal common initialization path only after filesystem, system/network, server, client, menu and post-client initialization have completed. M0.4 then requires the process to remain alive for a fixed post-marker window before the harness terminates it deliberately.

## Preconditions

```text
M0.3 revision is an ancestor of HEAD
M0.3 reference environment manifest verifies
no unrelated working-tree changes are present
active WAYLAND_DISPLAY or DISPLAY is available
```

When running from the uncommitted M0.4 package overlay, only the M0.4 harness/document/evidence paths are permitted to differ from HEAD.

## Clean build gate

The harness removes the entire ignored `build-m0-legacy-f44/` binary directory before configuring. It then executes:

```text
cmake --preset legacy-m0-f44
cmake --build --preset legacy-m0-f44
```

It requires the generated cache to contain:

```text
UFOAI_REMASTER=OFF
CMAKE_BUILD_TYPE=RelWithDebInfo
```

and requires these outputs:

```text
build-m0-legacy-f44/ufo
build-m0-legacy-f44/ufoded
build-m0-legacy-f44/base/game.so
```

## Launch isolation and criterion

The real `ufo` client is launched from the repository root so the canonical source-tree data remain available. Existing user configuration is excluded by replacing `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME` and `XDG_CACHE_HOME` with fresh directories inside the ignored build tree. The live graphical-session environment is otherwise inherited.

The harness requests a non-grabbing 1024x768 window:

```text
+set vid_fullscreen 0
+set vid_grabmouse 0
+set vid_width 1024
+set vid_height 768
```

It does not force an SDL video driver, renderer backend, audio driver, or remaster feature.

PASS requires:

```text
client remains alive while initializing
"====== UFO Initialized ======" appears within 60 seconds
client remains alive for at least 5 seconds after that marker
harness then terminates the process group deliberately
```

An exit before the marker, timeout, or exit during the post-marker window is a failure.

## Evidence

On PASS the harness writes:

```text
docs/reference/reference-m0-legacy-build-launch-smoke.txt
docs/reference/reference-m0-legacy-build-launch-smoke.b3
```

The evidence is intentionally compact and excludes timestamps, hostnames, temporary paths and measured durations. It records the tested source revision, M0 environment identity, input script/preset identities, cache selection, required build artifacts, launch criterion, display-session class and result.

Raw logs remain local under the ignored build tree:

```text
build-m0-legacy-f44/m0-legacy-configure.log
build-m0-legacy-f44/m0-legacy-build.log
build-m0-legacy-f44/m0-legacy-launch-smoke.log
```

## Run

From the repository root:

```bash
python3 tools/remaster/run-m0-legacy-smoke.py
```

After PASS:

```bash
cat docs/reference/reference-m0-legacy-build-launch-smoke.txt
cat docs/reference/reference-m0-legacy-build-launch-smoke.b3
git diff --check
git status --short
```

Do not interpret M0.4 as renderer parity or a new-path validation. It is specifically the preservation gate that the legacy game can still be clean-built and genuinely initialized while the remaster bootstrap remains opt-in.
