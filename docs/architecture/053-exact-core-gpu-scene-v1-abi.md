# Core GPU Scene v1 ABI — Superseded Record

**Status:** Superseded by architecture 059  
**Related:** architecture 051, 056, 057, 058, 059

## Purpose

Baseline 022 introduced the first exact core GPU scene layout in this document.

The Baseline-022 second deep scan found semantic fields that lacked backing arrays or conflicted with later-required temporal identity.

Baseline 023 therefore moves the current exact ABI to:

```text
architecture/059-core-gpu-scene-v1-semantic-and-skinning-abi.md
```

## Current authorities

```text
matrix/units semantics              architecture 051
shader root/descriptors/compiler    architecture 056
light/ReSTIR/DDGI temporal ABI      architecture 057
static/dynamic RenderObjectId       architecture 058
core GPU scene struct layout        architecture 059
texture/output/audio conventions    architecture 060
```

No C++ struct in this superseded document is normative.

The retained filename preserves baseline history and cross-reference continuity.
