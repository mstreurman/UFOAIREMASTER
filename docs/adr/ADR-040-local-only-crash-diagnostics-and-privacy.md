# ADR-040 — Local-Only Crash Diagnostics and Privacy

**Status:** Accepted  
**Decision:** `CRASH-001`

## Decision

The baseline has **no automatic network crash upload and no automatic telemetry**.

Use Fedora/local facilities:

```text
systemd-coredump or explicitly enabled local core dump
ELF GNU build IDs
split debuginfo/debug symbols
local structured logs
local trace/replay/probe capture bundle
manual user submission when desired
```

A future remote reporting service requires a separate privacy/consent/retention/security ADR and is outside v1.

Architecture 086 owns exact bundle and packaging behavior.
