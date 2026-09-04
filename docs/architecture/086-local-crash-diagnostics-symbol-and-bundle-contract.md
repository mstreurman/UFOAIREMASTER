# Local Crash Diagnostics, Symbols and Bundle Contract

**Status:** Implementation specification baseline  
**Authority:** ADR-040, ADR-027

## 1. Privacy/default behavior

No crash report, trace, replay, hardware inventory or log is automatically uploaded. No network endpoint is part of v1 crash handling.

## 2. Build IDs and symbols

Linux executables/shared objects are linked with GNU build IDs. Release packaging separates debugging information using the Fedora-compatible build-ID/debuginfo layout while retaining enough symbol identity in the executable to match a core to symbols.

Developer builds keep symbols according to build profile.

## 3. Core dumps

Reference Fedora workflow uses `systemd-coredump` when enabled by the user's system policy. The application does not weaken system privacy/storage policy or force unlimited core dumps.

## 4. Local diagnostic bundle

When the user explicitly requests/executes diagnostic export, produce a local directory/archive containing only available data:

```text
manifest.json
application build ID/source commit
renderer/shader package IDs
Fedora/kernel/Mesa/Vulkan device summary
last structured application log
last bounded trace capture
last presentation replay/canonical regression identity where available
crash/core reference metadata, not necessarily the core itself
```

Do not include arbitrary home-directory files, environment variables, tokens, credentials or complete process memory in the convenience bundle.

The core dump itself remains under normal OS handling and is never implicitly attached.

## 5. Retention

Application-managed traces/logs use bounded rotation. Exact user-facing retention count/size is configuration/tuning, not an ABI blocker. Default behavior must prevent unbounded disk growth.

## 6. Manual submission

Documentation may instruct a user how to attach selected diagnostics to a bug report. Submission is always explicit user action.
