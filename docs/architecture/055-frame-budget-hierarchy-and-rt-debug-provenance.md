# Frame Budget Hierarchy and RT Debug Provenance

**Status:** Exact accounting/debug specification  
**Related ADR:** ADR-027, ADR-028

## 1. Root deadline

```text
qualification refresh = 60 Hz
qualification frame-budget reference = 16.667 ms
qualification RenderExtent = 1920×1080
```

All subsystem budgets are subordinate to this deadline.

## 2. Budget terms

```text
Parent gate
    contains child work

Child target
    attribution inside a parent

Independent concurrent target
    another thread/domain, not arithmetically added to a parent path

Quality/degrade ceiling
    trigger for scaling/diagnosis
```

## 3. Main CPU hierarchy

Parent:

```text
snapshot-ready <= ~4.5 ms
```

Existing children:

```text
canonical + mirror                  <= 1.5 ms
animation + pose                    <= 1.0 ms
Jolt normal scene                   <= 1.0 ms
presentation finalization/snapshot  <= 1.0 ms
```

Main-side UI/audio preparation targets executed before publication are child attribution inside this parent and are not blindly added on top.

## 4. Render thread

Existing:

```text
snapshot consume
GPU population
Frame Graph compile
record/submit
<= 2.0 ms target
```

It may overlap Main work and is not simply added to the 4.5-ms snapshot-ready target.

Late-submit warning remains ~8 ms after frame start.

## 5. AudioControl

Existing service targets are independent/concurrent:

```text
<= 0.25 ms average
<= 0.75 ms 99p
```

OpenAL mixer/backend CPU is measured separately.

## 6. GPU accounting

Existing normal targets:

```text
core lighting RT/reconstruction   ~4.8 ms
normal VFX                        ~2.0 ms
standard UI                       <=0.30 ms
```

Existing ceilings:

```text
core lighting RT/reconstruction   ~5.5 ms provisional
VFX                               ~2.5 ms provisional
heavy UI                          <=0.50 ms
```

The remaining frame envelope contains AS, raster G-buffer, non-RT deferred work, transparency, post/output and synchronization overhead. No new arbitrary split is invented here.

## 7. RT traversal vs GPU time

Volumetric directional RT rays count in the global architecture-019 traversal ceiling.

Their GPU time remains in the VFX/volumetric budget rather than being double-counted in the core-lighting RT time gate.

## 8. RT Isolation output space

Diagnostic false color is generated in the active display-linear output space:

```text
after scene tone mapping/color transform
before PQ/sRGB transfer encoding
```

For the selected mode, non-RT is pure-red hue scaled to output reference white:

```text
NON-RT = (outputReferenceWhiteNits, 0, 0)
```

Thus:

```text
HDR = (203, 0, 0) nits
SDR = (100, 0, 0) nits
```

before transfer encoding.

It bypasses scene exposure, bloom and creative grading.

Architecture 060 is the exact output/debug-color authority.

## 9. `Current-Ray Activity`

Per-screen-pixel current-ray activity includes effects whose current-frame ray is attributable to that pixel/sample:

```text
directional shadow
local visibility/ReSTIR visibility
reflection
```

DDGI rays originate at probes and are excluded from this pixel-launched classification.

Use separate:

```text
DDGI Probe Update Activity
```

for probe provenance.

## 10. Resolved influence

`Resolved RT Influence` may include current samples, temporal history, reconstruction, reflection upsample and DDGI gathered from RT-traced probes.

## 11. Production provenance

Diagnostic builds may record:

```text
sampledThisFrame
sourceFrameIndex
sample/random identity
history weight/length
effect class
```

DDGI records relevant probe IDs/update frames.

## 12. Diagnostic re-trace

A fresh probe ray using the production ray constructor is labeled:

```text
Diagnostic Re-trace
```

It is separate from:

```text
Displayed Result Provenance
```

and is never claimed to be the historical sample behind a temporally reconstructed pixel.

## 13. Capture

`.ufoprobe`/trace captures store provenance and diagnostic re-trace separately together with frame/FrameContext/debug-mode identity.

## OutputExtent-dependent GPU work

Architecture 072 separates scene-resolution and output-resolution cost.

RenderExtent-dependent work includes:

```text
G-buffer
scene RT/reconstruction
scene VFX
scene post
```

OutputExtent-dependent work includes:

```text
SceneOutputScale
UiComposite
developer output overlays
PQ/SDR encode
swapchain output
```

When OutputExtent differs from the 1920x1080 qualification RenderExtent, output-dependent passes are measured explicitly rather than being hidden inside the qualification scene budget.
